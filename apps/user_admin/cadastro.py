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

from apps.core.entrega_email import entregar_email_de_acesso
from apps.core.erros_formulario import de_validation_error
from apps.user_admin.administrador import recusa_de_auto_revogacao
from apps.user_admin.formularios import (
    ler_edicao_servidor,
    ler_novo_servidor,
    traduzir_recusa,
)
from apps.user_admin.foto import conferir_foto
from apps.user_admin.models import Perfil
from apps.user_admin.schemas import EdicaoServidor, NovoServidor
from services.domain.email import EmailAcessoInput
from services.utils.erros_formulario import ErroBruto, RecusaDeFormulario
from services.utils.senha import gerar_senha_temporaria
from services.utils.smtp import SmtpEnvioError

DOMINIOS_INSTITUCIONAIS = ("prefeitura.sp.gov.br", "sf.prefeitura.sp.gov.br")
ERRO_DOMINIO = (
    "O e-mail precisa ser institucional: @" + ", @".join(DOMINIOS_INSTITUCIONAIS) + "."
)
ERRO_ENVIO = (
    "Cadastro não concluído: não foi possível entregar a senha temporária em {email}."
)
# SPEC user_admin/022.
ERRO_SEM_CANETA = "Só um administrador pode cadastrar outro administrador."
ERRO_SEM_CANETA_EDICAO = (
    "Só um administrador pode tornar outro servidor administrador do sistema."
)


@dataclass(frozen=True)
class DesfechoCadastro:
    """Recado do ato para a view. Não é DTO de domínio: não cruza fronteira de serviço e carrega o
    próprio model gravado — mesma natureza do `_RegistroAto` da SPEC autorizacao/004."""

    perfil: Perfil | None
    # Não opcional: `perfil is None` já é a etiqueta do desfecho, e uma recusa sempre-presente
    # poupa quem lê de desembrulhar um Optional que o sucesso nunca preenche.
    recusa: RecusaDeFormulario = RecusaDeFormulario()
    # SPEC user_admin/022 v3: a edição que mexe na caneta não é o mesmo ato que a edição comum, e é
    # a view que precisa saber disso para nomear a operação registrada.
    marca_alterada: bool = False
    # SPEC criacao_usuarios/007: preenchido SÓ quando a senha não saiu por e-mail — `None` é a
    # etiqueta de "foi entregue", e é ela que a tela lê para decidir tudo.
    senha_a_exibir: SecretStr | None = None


def criar_servidor(
    valores: Mapping[str, Any],
    foto: UploadedFile | None = None,
    administrador_permitido: bool = False,
) -> DesfechoCadastro:
    """Quem fica cadastrado é quem recebeu como entrar: o envio acontece dentro da transação, e a
    falha dele derruba a gravação junto.

    Recebe o formulário cru e delega a leitura ao `LeitorDeFormulario`: construir o DTO na view
    entregaria a recusa ao `PydanticValidationMiddleware`, cuja resposta, no alvo do form, apaga o
    formulário inteiro (SPEC formularios/001). O `try` do banco e do SMTP mora aqui pelo mesmo
    motivo de sempre: é este módulo que sabe o que cada falha significa para o cadastro.

    `administrador_permitido` (SPEC user_admin/022) é resolvido pela orquestração — quem pode
    armar a marca é conferido aqui dentro, e não no decorator, que só conhece a ação que protege
    a rota de cadastro."""
    leitura = ler_novo_servidor(valores)
    novo = leitura.dto
    if novo is None:
        # Sem DTO a leitura traz a recusa; o `or` é só o que o tipo pede, não um caso real.
        return DesfechoCadastro(
            perfil=None, recusa=leitura.recusa or RecusaDeFormulario()
        )
    if novo.administrador and not administrador_permitido:
        # Recusa, e não 403: o controle existe na tela e a marca veio de um formulário — quem
        # preencheu tem que ver o motivo no lugar em que ele nasceu. Nada é gravado, nem o
        # cadastro.
        return DesfechoCadastro(perfil=None, recusa=_recusa_sem_caneta(ERRO_SEM_CANETA))
    politica = _recusa_de_politica(novo.email, foto)
    if politica is not None:
        return DesfechoCadastro(perfil=None, recusa=politica)
    senha = gerar_senha_temporaria()
    try:
        with transaction.atomic():
            perfil = _gravar(novo, senha, foto)
            entregue = _entregar_senha(perfil, senha, novo.url_acesso)
    except ValidationError as recusa:
        # RF e e-mail repetidos chegam aqui pelo full_clean: conferir antes com um SELECT abriria
        # janela entre a consulta e o INSERT, e a unicidade é do banco. A ponte de `apps/core`
        # preserva o `code`, que é o que faz a mensagem do model chegar realçada no campo certo.
        return DesfechoCadastro(
            perfil=None, recusa=traduzir_recusa(de_validation_error(recusa))
        )
    except SmtpEnvioError:
        return DesfechoCadastro(perfil=None, recusa=_recusa_da_entrega(novo.email))
    # A senha só escapa do ato por este caminho, e só depois de a transação ter fechado: cadastro
    # recusado sai pelos `except` acima, que devolvem desfecho sem perfil e sem senha (SPEC 007).
    senha_a_exibir = None if entregue else senha
    return DesfechoCadastro(perfil=perfil, senha_a_exibir=senha_a_exibir)


def _recusa_de_politica(
    email: str, foto: UploadedFile | None
) -> RecusaDeFormulario | None:
    """O que o DTO não pode conferir: o domínio institucional depende de settings, e a foto é um
    objeto de upload do Django. Nenhum dos dois desce para o model — gravar pelo shell, pelo
    `createsuperuser` ou por um comando continua livre (SPEC criacao_usuarios/006)."""
    erros = tuple(
        erro
        for erro in (_erro_de_dominio(email), conferir_foto(foto))
        if erro is not None
    )
    return traduzir_recusa(erros) if erros else None


def _erro_de_dominio(email: str) -> ErroBruto | None:
    # Recusa que não vem de fonte nenhuma: é política desta rota, e o controle a realçar é o
    # e-mail, porque é o endereço que precisa mudar. `tipo` fora de REGRAS_PADRAO é de propósito —
    # a mensagem já vem escrita e vence a do catálogo; do tipo só se aproveita o tom, que é erro.
    if not _dominio_recusado(email):
        return None
    return ErroBruto(controle="email", tipo="dominio", mensagem=ERRO_DOMINIO)


def _recusa_da_entrega(email: str) -> RecusaDeFormulario:
    return traduzir_recusa(
        (
            ErroBruto(
                controle="email",
                tipo="entrega",
                mensagem=ERRO_ENVIO.format(email=email),
            ),
        )
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
        # SPEC user_admin/022: nasce administrador no mesmo POST do cadastro. `is_staff` fica de
        # fora de propósito — o /admin do Django não abre por aqui (SPEC, §4).
        is_superuser=novo.administrador,
    )
    # A senha nasce hasheada: nem o banco, nem o log, nem um traceback guardam o texto claro.
    perfil.set_password(senha.get_secret_value())
    perfil.senha_provisoria = True
    perfil.full_clean(exclude=["password"])
    perfil.save()
    return perfil


def _entregar_senha(perfil: Perfil, senha: SecretStr, url_acesso: HttpUrl) -> bool:
    """Devolve True quando a mensagem foi de fato entregue ao SMTP (SPEC criacao_usuarios/007) —
    a guarda de `EMAIL_ENVIO_HABILITADO` mora em `entregar_email`, e é essa a ÚNICA leitura dela em
    todo o caminho até a tela."""
    return entregar_email_de_acesso(
        EmailAcessoInput(
            nome=perfil.nome,
            rf=perfil.rf,
            destinatario=perfil.email,
            senha_temporaria=senha,
            url_acesso=url_acesso,
        )
    )


def editar_servidor(
    valores: Mapping[str, Any],
    autor_id: int,
    foto: UploadedFile | None = None,
    administrador_permitido: bool = False,
) -> DesfechoCadastro:
    """Um ato só: ou o cadastro inteiro passa pela validação do model, ou nada muda — e isso passou
    a valer também para a condição de administrador do sistema (SPEC user_admin/022 v3), escrita
    aqui, no fim,
    e não por um ato à parte que gravava mesmo com o formulário recusado.

    Recebe o formulário cru e delega a leitura ao `LeitorDeFormulario`, como o `criar_servidor`. O
    `try` mora aqui, e não na view, pelo mesmo motivo: é este módulo que sabe o que a recusa
    significa para o cadastro (SPEC criacao_usuarios/005)."""
    leitura = ler_edicao_servidor(valores)
    edicao = leitura.dto
    if edicao is None:
        # O `or` é só o que o tipo pede, não um caso real.
        return DesfechoCadastro(
            perfil=None, recusa=leitura.recusa or RecusaDeFormulario()
        )
    # A MESMA linha da criação: é a ausência dela aqui que deixava a edição gravar @gmail.com.
    politica = _recusa_de_politica(edicao.email, foto)
    if politica is not None:
        return DesfechoCadastro(perfil=None, recusa=politica)
    perfil = get_object_or_404(Perfil, pk=edicao.servidor_id)
    if edicao.administrador and not administrador_permitido:
        return DesfechoCadastro(
            perfil=None, recusa=_recusa_sem_caneta(ERRO_SEM_CANETA_EDICAO)
        )
    marca = _marca_pretendida(perfil, edicao, administrador_permitido)
    alterou_marca = marca != perfil.is_superuser
    if alterou_marca:
        recusa_da_marca = recusa_de_auto_revogacao(edicao.servidor_id, autor_id, marca)
        if recusa_da_marca is not None:
            return DesfechoCadastro(perfil=None, recusa=recusa_da_marca)
    _aplicar(perfil, edicao, foto)
    perfil.is_superuser = marca
    try:
        perfil.full_clean(exclude=["password"])
        perfil.save()
    except ValidationError as recusa:
        # RF e e-mail já usados por outro, e o titular cujo cargo não titulariza a unidade de
        # destino: as três recusas são do model, e chegam juntas por aqui. A ponte de `apps/core`
        # preserva o `code`, que é o que faz o RF e o e-mail realçarem o controle certo; a do
        # titular nomeia `e_titular`, que não é controle desta tela, e por isso cai na tarja.
        return DesfechoCadastro(
            perfil=None, recusa=traduzir_recusa(de_validation_error(recusa))
        )
    return DesfechoCadastro(perfil=perfil, marca_alterada=alterou_marca)


def _marca_pretendida(
    perfil: Perfil,
    edicao: EdicaoServidor,
    administrador_permitido: bool,
) -> bool:
    """Sem o controle na tela o POST não manda a marca, e ler essa ausência como "revogar" tiraria
    a caneta de um administrador a cada edição feita por quem apenas edita servidor."""
    return edicao.administrador if administrador_permitido else perfil.is_superuser


def _recusa_sem_caneta(mensagem: str) -> RecusaDeFormulario:
    # Recusa, e não 403: o controle existe na tela e a marca veio de um formulário — quem preencheu
    # tem que ver o motivo no lugar em que ele nasceu. Nada é gravado, nem o resto do cadastro.
    return traduzir_recusa(
        (ErroBruto(controle="administrador", tipo="sem_caneta", mensagem=mensagem),)
    )


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
