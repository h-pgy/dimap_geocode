"""
O ato de cadastrar servidor (SPEC criacao_usuarios/004): gravar e entregar a senha temporária são
a mesma transação — falha na entrega desfaz o cadastro, e envio desligado por configuração o
conclui (Caveats). A política de e-mail institucional é conferida antes de gerar senha ou abrir
conversa com o SMTP; o banco não a conhece.
"""

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from pydantic import HttpUrl, SecretStr

from apps.user_admin.models import Perfil
from apps.user_admin.schemas import NovoServidor
from services.domain.email import EmailAcessoInput, montar_email_acesso, montar_mensagem
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
    erros: tuple[str, ...] = ()


def criar_servidor(novo: NovoServidor, foto: UploadedFile | None = None) -> DesfechoCadastro:
    """Quem fica cadastrado é quem recebeu como entrar: o envio acontece dentro da transação, e a
    falha dele derruba a gravação junto.

    O `try` mora aqui, e não na view: é este módulo que sabe o que cada falha significa para o
    cadastro."""
    if _dominio_recusado(novo.email):
        return DesfechoCadastro(perfil=None, erros=(ERRO_DOMINIO,))
    senha = gerar_senha_temporaria()
    try:
        with transaction.atomic():
            perfil = _gravar(novo, senha, foto)
            _entregar_senha(perfil, senha, novo.url_acesso)
    except ValidationError as recusa:
        # RF e e-mail repetidos chegam aqui pelo full_clean: conferir antes com um SELECT abriria
        # janela entre a consulta e o INSERT, e a unicidade é do banco.
        return DesfechoCadastro(perfil=None, erros=_mensagens(recusa))
    except SmtpEnvioError:
        return DesfechoCadastro(perfil=None, erros=(ERRO_ENVIO.format(email=novo.email),))
    return DesfechoCadastro(perfil=perfil)


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


def _mensagens(recusa: ValidationError) -> tuple[str, ...]:
    return tuple(
        mensagem
        for mensagens_do_campo in recusa.message_dict.values()
        for mensagem in mensagens_do_campo
    )
