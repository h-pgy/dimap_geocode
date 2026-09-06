"""
O reenvio da senha de uso único do primeiro acesso (SPEC autenticacao/004): reenviar a mesma senha
enquanto ela valer, emitir outra quando não houver cópia guardada, e a janela de reenvio
compartilhada com a recuperação de senha (`apps.autenticacao.janela_envio`).
"""

from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.db import transaction

from pydantic import SecretStr

from apps.autenticacao.janela_envio import armar_janela, espera_do_reenvio
from apps.autenticacao.schemas import ReenvioSenhaInput
from apps.core.entrega_email import entregar_email_de_acesso
from apps.user_admin.models import Perfil
from services.domain.email import EmailAcessoInput
from services.utils.erros_formulario import (
    ErroBruto,
    Formulario,
    RecusaDeFormulario,
    TradutorDeRecusa,
)
from services.utils.senha import gerar_senha_temporaria
from services.utils.smtp import SmtpEnvioError

ERRO_ENTREGA = (
    "Não foi possível enviar a senha para {email}. Tente novamente em instantes."
)

CHAVE_SENHA = "senha_uso_unico:{pk}"
CHAVE_SENHA_ANTERIOR = "senha_uso_unico_anterior:{pk}"
# Por quanto tempo o pedido seguinte reenvia a MESMA senha em vez de emitir outra. Não é prazo de
# validade: a senha provisória autentica até ser substituída ou usada (SPEC criacao_usuarios/004),
# e o que expira aqui é só a cópia em texto claro que permite reenviá-la.
PRAZO_MESMA_SENHA_SEGUNDOS = settings.PRAZO_MESMA_SENHA_SEGUNDOS
# O hash substituído sobrevive muito mais: a mensagem que a pessoa tem aberta na caixa de entrada
# pode ser de ontem, e é ela que a tela do código precisa reconhecer.
PRAZO_SENHA_ANTERIOR_SEGUNDOS = settings.PRAZO_SENHA_ANTERIOR_SEGUNDOS

# Sem controle nesta tela para realçar: o pedido nasce de um botão, não de um campo.
traduzir_recusa_reenvio = TradutorDeRecusa(Formulario(campos=()))


@dataclass(frozen=True)
class DesfechoReenvio:
    """Recado do ato para a view, no molde do `DesfechoRecuperacao`: não é DTO de domínio, não cruza
    fronteira de serviço e carrega o próprio model, que é de quem o modal mostra o RF."""

    perfil: Perfil | None = None
    email: str = ""
    enviado: bool = False
    recusa: RecusaDeFormulario = RecusaDeFormulario()
    # Segundos que faltam para o próximo envio; maior que zero é a etiqueta de "nada saiu agora
    # porque a mensagem anterior acabou de sair".
    espera_segundos: int = 0
    # Preenchido SÓ quando a senha não saiu por e-mail — `None` é a etiqueta de "foi entregue", e é
    # ela que a tela lê para decidir se abre o modal (SPEC criacao_usuarios/007).
    senha_a_exibir: SecretStr | None = None


def _perfil_com_senha_a_reenviar(rf: str) -> Perfil | None:
    """`senha_provisoria=True` é a metade que importa da regra: quem já tem senha definitiva entra
    pela recuperação, que é a porta do outro estado da conta. Sem e-mail não há para onde mandar, e
    o desfecho é o mesmo do RF que não existe."""
    return (
        Perfil.objects.filter(rf=rf, is_active=True, senha_provisoria=True)
        .exclude(email="")
        .first()
    )


def reenviar_senha_uso_unico(pedido: ReenvioSenhaInput) -> DesfechoReenvio:
    """Reenviar é o caso comum, e emitir é a exceção: enquanto a senha guardada ainda for a
    credencial da conta, o pedido repete a mesma mensagem — trocar a cada clique deixaria na caixa
    de entrada uma pilha de códigos em que só o último funciona.

    A senha nova só passa a valer se chegou: a gravação e a entrega são a mesma transação — a mesma
    regra do cadastro (SPEC criacao_usuarios/004), pelo motivo inverso. Lá, servidor gravado sem
    receber a senha é conta que ninguém usa; aqui, senha trocada sem chegar tira do servidor a que
    ele ainda tinha na caixa de entrada."""
    perfil = _perfil_com_senha_a_reenviar(pedido.rf)
    if perfil is None:
        return DesfechoReenvio()
    espera = espera_do_reenvio(perfil)
    if espera:
        # Sai antes de sortear: dentro da janela o pedido não produz nada — nem mensagem, nem
        # senha nova, nem a troca da que está valendo.
        return DesfechoReenvio(
            perfil=perfil, email=perfil.email, enviado=True, espera_segundos=espera
        )
    guardada = _copia_guardada(perfil)
    senha = guardada or gerar_senha_temporaria()
    try:
        with transaction.atomic():
            # Repetir a cópia guardada não escreve no cadastro: só a emissão grava.
            if guardada is None:
                _gravar_senha(perfil, senha)
            entregue = entregar_email_de_acesso(
                EmailAcessoInput(
                    nome=perfil.nome,
                    rf=perfil.rf,
                    destinatario=perfil.email,
                    senha_temporaria=senha,
                    url_acesso=pedido.url_acesso,
                )
            )
    except SmtpEnvioError:
        return DesfechoReenvio(
            perfil=perfil, email=perfil.email, recusa=_recusa_da_entrega(perfil.email)
        )
    # Depois do commit, e nunca antes: o cache não participa da transação, e uma entrada gravada
    # sobre uma troca desfeita ofereceria para sempre uma senha que não autentica.
    _guardar_senha(perfil, senha)
    if entregue:
        armar_janela(perfil)
    # A senha só escapa do ato por este caminho, e só depois de a transação ter fechado.
    return DesfechoReenvio(
        perfil=perfil,
        email=perfil.email,
        enviado=entregue,
        senha_a_exibir=None if entregue else senha,
    )


def _copia_guardada(perfil: Perfil) -> SecretStr | None:
    """O cache é palpite, não autoridade: quem diz se a cópia guardada ainda é a credencial da
    conta é o hash do próprio servidor. A senha de uso único não vence — não há carimbo a conferir,
    e o que o cache perde por reinício, por outro processo ou pelo próprio prazo é a cópia, não a
    credencial: some a chance de repetir a mesma, e o pedido seguinte emite outra."""
    guardada = cache.get(CHAVE_SENHA.format(pk=perfil.pk))
    if guardada is None or not perfil.check_password(guardada):
        return None
    return SecretStr(guardada)


def _guardar_senha(perfil: Perfil, senha: SecretStr) -> None:
    cache.set(
        CHAVE_SENHA.format(pk=perfil.pk),
        senha.get_secret_value(),
        timeout=PRAZO_MESMA_SENHA_SEGUNDOS,
    )


def _guardar_hash_anterior(perfil: Perfil) -> None:
    """O hash que sai de cena, guardado antes de ser sobrescrito — é hash, não senha, e é o mesmo
    valor que estava no banco um instante atrás. Transação desfeita deixa aqui o hash que continua
    valendo, o que é inofensivo: código que casasse com ele já teria autenticado."""
    cache.set(
        CHAVE_SENHA_ANTERIOR.format(pk=perfil.pk),
        perfil.password,
        timeout=PRAZO_SENHA_ANTERIOR_SEGUNDOS,
    )


def codigo_foi_substituido(rf: str, codigo: SecretStr) -> bool:
    """A pergunta que a tela do código faz depois de o `check_password` recusar: o que a pessoa
    digitou é a senha ANTERIOR desta conta? Para o hash em vigor, código de mensagem antiga e erro
    de digitação são a mesma recusa — quem os separa é o hash guardado pelo reenvio."""
    perfil = Perfil.objects.filter(rf=rf, is_active=True, senha_provisoria=True).first()
    if perfil is None:
        return False
    anterior = cache.get(CHAVE_SENHA_ANTERIOR.format(pk=perfil.pk))
    return anterior is not None and check_password(codigo.get_secret_value(), anterior)


def _gravar_senha(perfil: Perfil, senha: SecretStr) -> None:
    """`update_fields` porque este ato mexe numa coisa só: a credencial. `senha_provisoria` já está
    ligada — é o que autorizou o pedido — e nada mais do cadastro é reescrito por um pedido feito
    por quem não está autenticado."""
    _guardar_hash_anterior(perfil)
    perfil.set_password(senha.get_secret_value())
    perfil.save(update_fields=["password"])


def _recusa_da_entrega(email: str) -> RecusaDeFormulario:
    return traduzir_recusa_reenvio(
        (
            ErroBruto(
                controle="email",
                tipo="entrega",
                mensagem=ERRO_ENTREGA.format(email=email),
            ),
        )
    )
