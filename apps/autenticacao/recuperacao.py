"""
A emissão e o consumo do link de uso único de recuperação de senha (SPEC autenticacao/003).
"""

from dataclasses import dataclass
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from pydantic import HttpUrl

from apps.autenticacao.janela_envio import armar_janela, espera_do_reenvio
from apps.autenticacao.schemas import (
    ConsultaRfInput,
    DestinoRecuperacaoOutput,
    LinkRecuperacaoInput,
    PedidoRecuperacaoInput,
)
from apps.core.entrega_email import entregar_email
from apps.user_admin.models import Perfil
from services.domain.email import (
    EmailRecuperacaoInput,
    montar_email_recuperacao,
    montar_mensagem,
)
from services.utils.erros_formulario import (
    ErroBruto,
    Formulario,
    RecusaDeFormulario,
    TradutorDeRecusa,
)
from services.utils.smtp import SmtpEnvioError

# O gerador do contrib.auth deriva o token de pk + hash da senha + `last_login` + e-mail + carimbo
# de tempo. É `last_login` que faz o uso único: o consumo do link autentica o servidor, o
# `last_login` muda e o mesmo token deixa de conferir (Caveats).
SESSAO_SENHA_SEM_ATUAL = "recuperacao_dispensa_senha_atual"
ERRO_ENTREGA = (
    "Não foi possível enviar o link para {email}. Tente novamente em instantes."
)

# Sem controle nesta tela para realçar: o pedido nasce de um botão, não de um campo — a recusa vira
# tarja, e não realce de input.
traduzir_recusa_recuperacao = TradutorDeRecusa(Formulario(campos=()))

CHAVE_TOKEN = "recuperacao_senha:{pk}"


@dataclass(frozen=True)
class DesfechoRecuperacao:
    """Recado do ato para a view, no molde do `DesfechoCadastro`: não é DTO de domínio e não cruza
    fronteira de serviço."""

    email: str
    enviado: bool = False
    recusa: RecusaDeFormulario = RecusaDeFormulario()
    # Segundos que faltam para o próximo envio. Maior que zero é a etiqueta de "nada saiu agora
    # porque a mensagem anterior acabou de sair" — e é o número que a tela mostra.
    espera_segundos: int = 0
    # Preenchido SÓ quando o envio está desligado — `None` é a etiqueta de "foi entregue", e é ela
    # que a tela lê para decidir se mostra o link (SPEC criacao_usuarios/007).
    link_a_exibir: str | None = None


def _token_vigente(perfil: Perfil) -> str | None:
    """O cache é palpite, não autoridade: quem diz se o link ainda vale é o gerador, que já sabe da
    senha trocada e do link consumido. Entrada perdida (reinício, outro processo) só custa um link
    novo — e o primeiro consumo mata todos eles de uma vez."""
    guardado = cache.get(CHAVE_TOKEN.format(pk=perfil.pk))
    if guardado is None or not default_token_generator.check_token(perfil, guardado):
        return None
    return str(guardado)


def _token_do_pedido(perfil: Perfil) -> str:
    """Enquanto o link anterior vale, o pedido repetido reenvia o MESMO — o token embute o próprio
    carimbo de tempo, então reemitir é a única forma de gerar outro, e cada reemissão deixaria mais
    um link de portador vivo na caixa de entrada."""
    vigente = _token_vigente(perfil)
    if vigente is not None:
        return vigente
    token = default_token_generator.make_token(perfil)
    # O TTL é a validade do próprio link: entrada que sobrevive ao token só devolveria um link morto
    # para o `check_token` recusar no pedido seguinte.
    cache.set(
        CHAVE_TOKEN.format(pk=perfil.pk), token, timeout=settings.PASSWORD_RESET_TIMEOUT
    )
    return token


def ha_pedido_em_aberto(perfil: Perfil) -> bool:
    """A pergunta da tela de login. Só leitura: perguntar não pode ter como efeito colateral a
    emissão de um link."""
    return _token_vigente(perfil) is not None


def montar_link_recuperacao(perfil: Perfil, base_url: HttpUrl) -> str:
    caminho = reverse(
        "autenticacao:recuperar_senha",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(perfil.pk)),
            "token": _token_do_pedido(perfil),
        },
    )
    return urljoin(str(base_url), caminho)


def _perfil_recuperavel(rf: str) -> Perfil | None:
    """`senha_provisoria=False` é a metade que importa da regra: quem está em primeiro acesso já tem
    uma credencial de uso único esperando na caixa de entrada, e emitir uma segunda porta para o
    mesmo estado é dobrar a superfície de entrada sem dobrar a garantia."""
    return Perfil.objects.filter(rf=rf, is_active=True, senha_provisoria=False).first()


def _recusa_da_entrega(email: str) -> RecusaDeFormulario:
    return traduzir_recusa_recuperacao(
        (
            ErroBruto(
                controle="email",
                tipo="entrega",
                mensagem=ERRO_ENTREGA.format(email=email),
            ),
        )
    )


def enviar_link_recuperacao(pedido: PedidoRecuperacaoInput) -> DesfechoRecuperacao:
    perfil = _perfil_recuperavel(pedido.rf)
    if perfil is None:
        # Conta inexistente, inativa ou em primeiro acesso: nenhuma delas monta e-mail ou gera link.
        # A tela já disse qual é o caso antes do POST; aqui o que importa é não emitir nada.
        return DesfechoRecuperacao(email="")
    espera = espera_do_reenvio(perfil)
    if espera:
        # Sai antes de montar link, conteúdo e mensagem: dentro da janela o pedido não produz nada,
        # nem trabalho nem token.
        return DesfechoRecuperacao(
            email=perfil.email, enviado=True, espera_segundos=espera
        )
    link = montar_link_recuperacao(perfil, pedido.base_url)
    conteudo = montar_email_recuperacao(
        EmailRecuperacaoInput(
            nome=perfil.nome,
            destinatario=perfil.email,
            url_recuperacao=HttpUrl(link),
            validade_horas=pedido.validade_horas,
        )
    )
    try:
        entregue = entregar_email(
            montar_mensagem(conteudo, destinatarios=(perfil.email,))
        )
    except SmtpEnvioError:
        return DesfechoRecuperacao(
            email=perfil.email, recusa=_recusa_da_entrega(perfil.email)
        )
    if entregue:
        armar_janela(perfil)
    return DesfechoRecuperacao(
        email=perfil.email,
        enviado=entregue,
        link_a_exibir=None if entregue else link,
    )


def resolver_destino_recuperacao(consulta: ConsultaRfInput) -> DestinoRecuperacaoOutput:
    """O que a tela de recuperação mostra antes do POST — os três estados de `DestinoRecuperacaoOutput`."""
    try:
        perfil = Perfil.objects.get(rf=consulta.rf, is_active=True)
    except Perfil.DoesNotExist:
        return DestinoRecuperacaoOutput(rf=consulta.rf, estado="sem_conta")
    if perfil.senha_provisoria:
        return DestinoRecuperacaoOutput(
            rf=consulta.rf,
            nome=perfil.nome,
            email=perfil.email,
            estado="primeiro_acesso",
        )
    return DestinoRecuperacaoOutput(
        rf=consulta.rf, nome=perfil.nome, email=perfil.email, estado="recuperavel"
    )


def resolver_perfil_do_link(link: LinkRecuperacaoInput) -> Perfil | None:
    """Link vencido, já consumido, adulterado, de servidor inativo ou de servidor que voltou ao
    primeiro acesso: todos devolvem None. Quem distingue o motivo é o log, não a tela — a tela
    oferece pedir outro.

    A mesma regra de emissão vale no consumo: o estado da conta pode ter mudado entre um e outro, e
    quem decide é a rota que executa, não a que ofereceu."""
    try:
        pk = urlsafe_base64_decode(link.uidb64).decode()
        perfil = Perfil.objects.get(pk=pk, is_active=True, senha_provisoria=False)
    except ValueError, TypeError, Perfil.DoesNotExist:
        return None
    if not default_token_generator.check_token(perfil, link.token):
        return None
    return perfil
