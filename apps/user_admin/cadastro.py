"""
O ato de cadastrar servidor (SPEC criacao_usuarios/004): gravar e entregar a senha temporária são
a mesma transação — falha na entrega desfaz o cadastro, e envio desligado por configuração o
conclui (Caveats). A política de e-mail institucional é conferida antes de gerar senha ou abrir
conversa com o SMTP; o banco não a conhece.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.shortcuts import get_object_or_404
from pydantic import HttpUrl, SecretStr

from apps.core.erros_formulario import de_validation_error
from apps.user_admin.formularios import ler_edicao_servidor, ler_novo_servidor, traduzir_recusa
from apps.user_admin.models import Perfil
from apps.user_admin.schemas import EdicaoServidor, NovoServidor
from services.domain.email import EmailAcessoInput, montar_email_acesso, montar_mensagem
from services.utils.erros_formulario import ErroBruto, RecusaDeFormulario
from services.utils.senha import gerar_senha_temporaria
from services.utils.smtp import EnviadorSmtp, SmtpEnvioError, build_smtp_config, build_smtp_retry_policy

DOMINIOS_INSTITUCIONAIS = ("prefeitura.sp.gov.br", "sf.prefeitura.sp.gov.br")
ERRO_DOMINIO = "O e-mail precisa ser institucional: @" + ", @".join(DOMINIOS_INSTITUCIONAIS) + "."
ERRO_ENVIO = "Cadastro não concluído: não foi possível entregar a senha temporária em {email}."


@dataclass(frozen=True)
class DesfechoCadastro:
    """Recado do ato para a view. Não é DTO de domínio: não cruza fronteira de serviço e carrega o
    próprio model gravado — mesma natureza do `_RegistroAto` da SPEC autorizacao/004."""

    perfil: Perfil | None
    # Não opcional: `perfil is None` já é a etiqueta do desfecho, e uma recusa sempre-presente
    # poupa quem lê de desembrulhar um Optional que o sucesso nunca preenche.
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def criar_servidor(
    valores: Mapping[str, Any],
    foto: UploadedFile | None = None,
) -> DesfechoCadastro:
    """Quem fica cadastrado é quem recebeu como entrar: o envio acontece dentro da transação, e a
    falha dele derruba a gravação junto.

    Recebe o formulário cru e delega a leitura ao `LeitorDeFormulario`: construir o DTO na view
    entregaria a recusa ao `PydanticValidationMiddleware`, cuja resposta, no alvo do form, apaga o
    formulário inteiro (SPEC formularios/001). O `try` do banco e do SMTP mora aqui pelo mesmo
    motivo de sempre: é este módulo que sabe o que cada falha significa para o cadastro."""
    leitura = ler_novo_servidor(valores)
    novo = leitura.dto
    if novo is None:
        # Sem DTO a leitura traz a recusa; o `or` é só o que o tipo pede, não um caso real.
        return DesfechoCadastro(perfil=None, recusa=leitura.recusa or RecusaDeFormulario())
    if _dominio_recusado(novo.email):
        return DesfechoCadastro(perfil=None, recusa=_recusa_do_dominio())
    senha = gerar_senha_temporaria()
    try:
        with transaction.atomic():
            perfil = _gravar(novo, senha, foto)
            _entregar_senha(perfil, senha, novo.url_acesso)
    except ValidationError as recusa:
        # RF e e-mail repetidos chegam aqui pelo full_clean: conferir antes com um SELECT abriria
        # janela entre a consulta e o INSERT, e a unicidade é do banco. A ponte de `apps/core`
        # preserva o `code`, que é o que faz a mensagem do model chegar realçada no campo certo.
        return DesfechoCadastro(perfil=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    except SmtpEnvioError:
        return DesfechoCadastro(perfil=None, recusa=_recusa_da_entrega(novo.email))
    return DesfechoCadastro(perfil=perfil)


def _recusa_do_dominio() -> RecusaDeFormulario:
    # Recusa que não vem de fonte nenhuma: é política desta rota, e o controle a realçar é o
    # e-mail, porque é o endereço que precisa mudar. `tipo` fora de REGRAS_PADRAO é de propósito —
    # a mensagem já vem escrita e vence a do catálogo; do tipo só se aproveita o tom, que é erro.
    return traduzir_recusa((ErroBruto(controle="email", tipo="dominio", mensagem=ERRO_DOMINIO),))


def _recusa_da_entrega(email: str) -> RecusaDeFormulario:
    return traduzir_recusa(
        (ErroBruto(controle="email", tipo="entrega", mensagem=ERRO_ENVIO.format(email=email)),)
    )


def _gravar(novo: NovoServidor, senha: SecretStr, foto: UploadedFile | None) -> Perfil:
    perfil = Perfil(
        rf=novo.rf,
        nome=novo.nome,
        sobrenome=novo.sobrenome,
        email=novo.email,
        unidade_id=novo.unidade_id,
        cargo_base_id=novo.cargo_base_id,
        cargo_comissao_id=novo.cargo_comissao_id,
        foto=foto,
    )
    # A senha nasce hasheada: nem o banco, nem o log, nem um traceback guardam o texto claro.
    perfil.set_password(senha.get_secret_value())
    perfil.senha_provisoria = True
    perfil.full_clean(exclude=["password"])
    perfil.save()
    return perfil


def _entregar_senha(perfil: Perfil, senha: SecretStr, url_acesso: HttpUrl) -> None:
    """Recusa do destinatário e queda do servidor são o mesmo desfecho para o cadastro — a senha
    não chegou —, e por isso viram a mesma exceção. Envio DESLIGADO por configuração não entra
    aqui: a mensagem foi montada e impressa, e o cadastro de desenvolvimento segue."""
    conteudo = montar_email_acesso(
        EmailAcessoInput(
            nome=perfil.nome,
            rf=perfil.rf,
            destinatario=perfil.email,
            senha_temporaria=senha,
            url_acesso=url_acesso,
        )
    )
    mensagem = montar_mensagem(conteudo, destinatarios=(perfil.email,))
    enviador = EnviadorSmtp(build_smtp_config(settings), build_smtp_retry_policy(settings))
    resultado = enviador(mensagem)
    if resultado.destinatarios_recusados:
        raise SmtpEnvioError(f"Destinatário recusado: {perfil.email}.")


def editar_servidor(
    valores: Mapping[str, Any],
    foto: UploadedFile | None = None,
) -> DesfechoCadastro:
    """Um ato só: ou o cadastro inteiro passa pela validação do model, ou nada muda.

    Recebe o formulário cru e delega a leitura ao `LeitorDeFormulario`, como o `criar_servidor`. O
    `try` mora aqui, e não na view, pelo mesmo motivo: é este módulo que sabe o que a recusa
    significa para o cadastro (SPEC criacao_usuarios/005)."""
    leitura = ler_edicao_servidor(valores)
    edicao = leitura.dto
    if edicao is None:
        # O `or` é só o que o tipo pede, não um caso real.
        return DesfechoCadastro(perfil=None, recusa=leitura.recusa or RecusaDeFormulario())
    perfil = get_object_or_404(Perfil, pk=edicao.servidor_id)
    _aplicar(perfil, edicao, foto)
    try:
        perfil.full_clean(exclude=["password"])
        perfil.save()
    except ValidationError as recusa:
        # RF e e-mail já usados por outro, e o titular cujo cargo não titulariza a unidade de
        # destino: as três recusas são do model, e chegam juntas por aqui. A ponte de `apps/core`
        # preserva o `code`, que é o que faz o RF e o e-mail realçarem o controle certo; a do
        # titular nomeia `e_titular`, que não é controle desta tela, e por isso cai na tarja.
        return DesfechoCadastro(perfil=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoCadastro(perfil=perfil)


def _aplicar(perfil: Perfil, edicao: EdicaoServidor, foto: UploadedFile | None) -> None:
    """Foto sem arquivo novo é campo não tocado, não foto apagada: o formulário manda o `input`
    vazio a cada gravação, e sobrescrever com ele limparia o que já está lá."""
    perfil.rf = edicao.rf
    perfil.nome = edicao.nome
    perfil.sobrenome = edicao.sobrenome
    perfil.email = edicao.email
    perfil.unidade_id = edicao.unidade_id
    perfil.cargo_base_id = edicao.cargo_base_id
    perfil.cargo_comissao_id = edicao.cargo_comissao_id
    if foto is not None:
        perfil.foto = foto


def _dominio_recusado(email: str) -> bool:
    """Igualdade sobre o domínio, e não `endswith`: `sp.gov.br.exemplo.com` e
    `falsaprefeitura.sp.gov.br` terminam parecido e não são a prefeitura.

    Lê `settings` porque este módulo é a camada de aplicação e já lê para o SMTP — o que ele NÃO
    faz é levar a regra para o model: gravar direto pelo shell, pelo `createsuperuser` ou por um
    comando continua livre, e é para isso que a regra mora aqui (§7)."""
    if not settings.ENFORCE_PREFEITURA_EMAIL:
        return False
    _, _, dominio = email.rpartition("@")
    return dominio.lower() not in DOMINIOS_INSTITUCIONAIS

