"""
Os dois atos que mantêm o organograma (SPEC user_admin/020): criar grava abaixo da unidade
escolhida, editar altera identificação, hierarquia e cor — e, quando o pai muda, exige confirmação
antes de gravar a transferência.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from apps.core.erros_formulario import de_validation_error
from apps.unidades.formularios import (
    AVISO_TRANSFERENCIA,
    ERRO_NAO_VIRA_RAIZ,
    ler_edicao_unidade,
    ler_nova_unidade,
    traduzir_recusa,
)
from apps.unidades.models import Unidade
from apps.unidades.schemas import EdicaoUnidade
from services.utils.erros_formulario import ErroBruto, RecusaDeFormulario


@dataclass(frozen=True)
class DesfechoUnidade:
    """Três desfechos em dois campos: gravou (`unidade`), recusou (`recusa`) e falta confirmar
    (`exige_confirmacao`, com o aviso na MESMA forma da recusa — mensagem e realce).

    Dataclass, e não Pydantic, pelo mesmo motivo do `DesfechoCadastro`: recado do ato para a view,
    que carrega o model gravado e não cruza fronteira de serviço — validar `Unidade` no Pydantic
    exigiria `arbitrary_types_allowed` para não validar nada."""

    unidade: Unidade | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()
    exige_confirmacao: bool = False


def cadastrar_unidade(valores: Mapping[str, Any], raiz_permitida: bool = False) -> DesfechoUnidade:
    """`raiz_permitida` é a ROTA, não o perfil: quem pode criar raiz está declarado no contrato
    da ação (`exclusiva_superusuario`), e só a rota da raiz passa `True`. O ato não pergunta quem
    assina — recebe o que aquela porta permite (§3.3)."""
    leitura = ler_nova_unidade(valores)
    nova = leitura.dto
    if nova is None:
        return DesfechoUnidade(unidade=None, recusa=leitura.recusa or RecusaDeFormulario())
    if nova.pai_id is None and not raiz_permitida:
        return DesfechoUnidade(unidade=None, recusa=_recusa_de_raiz())
    unidade = Unidade(
        nome=nova.nome,
        sigla=nova.sigla,
        tipo_id=nova.tipo_id,
        pai_id=nova.pai_id,
        cor=nova.cor,
    )
    return _gravar(unidade)


def alterar_unidade(
    valores: Mapping[str, Any],
    transferencia_confirmada: bool = False,
) -> DesfechoUnidade:
    """A ordem importa: valida ANTES de pedir confirmação, para nunca pedir que se confirme uma
    transferência que a hierarquia vai recusar depois."""
    leitura = ler_edicao_unidade(valores)
    edicao = leitura.dto
    if edicao is None:
        return DesfechoUnidade(unidade=None, recusa=leitura.recusa or RecusaDeFormulario())
    unidade = get_object_or_404(Unidade, pk=edicao.unidade_id)
    destino_anterior = unidade.pai_id
    if edicao.pai_id is None and destino_anterior is not None:
        # Transferir para DEBAIXO da raiz é transferência comum; virar raiz não é edição de
        # ninguém, superusuário incluído — raiz é quem nasce raiz. O select nem oferece a opção, e
        # é aqui que a regra decide, não lá.
        return DesfechoUnidade(unidade=None, recusa=_recusa_de_raiz())
    _aplicar(unidade, edicao)
    try:
        unidade.full_clean()
    except ValidationError as recusa:
        return DesfechoUnidade(unidade=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    if edicao.pai_id != destino_anterior and not transferencia_confirmada:
        return DesfechoUnidade(
            unidade=None,
            recusa=_aviso_de_transferencia(unidade),
            exige_confirmacao=True,
        )
    unidade.save()
    return DesfechoUnidade(unidade=unidade)


def _aplicar(unidade: Unidade, edicao: EdicaoUnidade) -> None:
    unidade.nome = edicao.nome
    unidade.sigla = edicao.sigla
    unidade.tipo_id = edicao.tipo_id
    unidade.cor = edicao.cor
    unidade.pai_id = edicao.pai_id


def _recusa_de_raiz() -> RecusaDeFormulario:
    return traduzir_recusa((ErroBruto(controle="pai", tipo="raiz", mensagem=ERRO_NAO_VIRA_RAIZ),))


def _aviso_de_transferencia(unidade: Unidade) -> RecusaDeFormulario:
    # A mensagem já vem escrita e vence a do catálogo; do catálogo se aproveita o TOM, que é
    # alerta: não há o que corrigir, há o que confirmar.
    destino = unidade.pai.sigla if unidade.pai else "nenhuma unidade superior (raiz)"
    return traduzir_recusa(
        (
            ErroBruto(
                controle="pai",
                tipo="transferencia",
                mensagem=AVISO_TRANSFERENCIA.format(sigla=unidade.sigla, destino=destino),
            ),
        )
    )


def _gravar(unidade: Unidade) -> DesfechoUnidade:
    try:
        unidade.full_clean()
        unidade.save()
    except ValidationError as recusa:
        # Nome e sigla repetidos, nível que não subordina, tipo vedado e titular incompatível:
        # todas são do model e chegam juntas por aqui, já nomeando os controles `nome`, `sigla`,
        # `pai` e `tipo`.
        return DesfechoUnidade(unidade=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoUnidade(unidade=unidade)
