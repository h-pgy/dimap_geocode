"""Leitura de exibição do campo achatado `LinhaExecucao.alvo` (SPEC painel/002): o par
"tipo: identificador" chega em um campo só — é por ele que o cabeçalho filtra de uma vez —, e estes
filtros só o abrem de volta para o `<td>` desenhar o tipo como legenda."""

from django import template

register = template.Library()

SEPARADOR = ": "


@register.filter
def alvo_tipo(alvo: str) -> str:
    return alvo.split(SEPARADOR, 1)[0] if alvo else ""


@register.filter
def alvo_identificador(alvo: str) -> str:
    partes = alvo.split(SEPARADOR, 1)
    return partes[1] if len(partes) == 2 else alvo
