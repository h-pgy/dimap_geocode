"""
O ato de gravar a senha definitiva do servidor (SPEC autenticacao/002): o primeiro acesso e a
redefinição voluntária compartilham a mesma validação — divergência de confirmação, senha atual
incorreta fora do primeiro login e a política de senha forte.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from apps.autenticacao.formularios import (
    ler_definicao_senha,
    ler_redefinicao_senha,
    traduzir_recusa_senha,
)
from apps.autenticacao.schemas import RedefinicaoSenhaInput
from apps.user_admin.models import Perfil
from services.domain.autenticacao import (
    ERRO_SENHA_ATUAL_INCORRETA,
    ERRO_SENHAS_DIVERGENTES,
    validar_complexidade_senha,
)
from services.utils.erros_formulario import ErroBruto, RecusaDeFormulario


@dataclass(frozen=True)
class DesfechoGravacaoSenha:
    """Recado do ato para a view. Não é DTO de domínio: carrega a recusa já traduzida, e uma
    recusa sempre-presente poupa quem lê de desembrulhar um Optional que o sucesso nunca preenche."""

    sucesso: bool
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def gravar_senha(
    perfil: Perfil,
    dispensa_senha_atual: bool,
    valores: Mapping[str, Any],
) -> DesfechoGravacaoSenha:
    """Valida e grava a nova senha do servidor autenticado. Recebe o formulário cru e delega a
    leitura ao `LeitorDeFormulario` — construir o DTO na view entregaria a recusa ao
    `PydanticValidationMiddleware`, cuja resposta apaga o `<form>` inteiro (skill
    `erros-de-formulario`).

    `dispensa_senha_atual` tem duas causas (SPEC autenticacao/003): a senha provisória do primeiro
    acesso e a sessão aberta pelo consumo do link de recuperação — nos dois casos não existe senha
    atual que o servidor consiga informar."""
    leitura = (
        ler_definicao_senha(valores) if dispensa_senha_atual else ler_redefinicao_senha(valores)
    )
    dto = leitura.dto
    if dto is None:
        return DesfechoGravacaoSenha(sucesso=False, recusa=leitura.recusa or RecusaDeFormulario())

    if isinstance(dto, RedefinicaoSenhaInput) and not perfil.check_password(
        dto.senha_atual.get_secret_value()
    ):
        recusa = traduzir_recusa_senha(
            (ErroBruto(controle="senha_atual", tipo="invalido", mensagem=ERRO_SENHA_ATUAL_INCORRETA),)
        )
        return DesfechoGravacaoSenha(sucesso=False, recusa=recusa)

    nova_senha = dto.nova_senha.get_secret_value()
    if nova_senha != dto.confirmacao_senha.get_secret_value():
        recusa = traduzir_recusa_senha((
            ErroBruto(controle="nova_senha", tipo="divergente", mensagem=ERRO_SENHAS_DIVERGENTES),
            ErroBruto(controle="confirmacao_senha", tipo="divergente", mensagem=ERRO_SENHAS_DIVERGENTES),
        ))
        return DesfechoGravacaoSenha(sucesso=False, recusa=recusa)

    erros_complexidade = validar_complexidade_senha(nova_senha)
    if erros_complexidade:
        recusa = traduzir_recusa_senha(
            (ErroBruto(controle="nova_senha", tipo="complexidade", mensagem=erros_complexidade[0]),)
        )
        return DesfechoGravacaoSenha(sucesso=False, recusa=recusa)

    perfil.set_password(nova_senha)
    if dispensa_senha_atual:
        perfil.senha_provisoria = False
        perfil.save(update_fields=["password", "senha_provisoria"])
    else:
        perfil.save(update_fields=["password"])
    return DesfechoGravacaoSenha(sucesso=True)
