"""
Projeção do catálogo de ações em código (SPEC autorizacao/002): upsert por slug, desativação do que
sumiu do registro, reativação de quem volta a ele.
"""

from django.db import transaction
from pydantic import BaseModel

from .models import Acao
from .schemas import RegistroAcoes


class ContagemSync(BaseModel):
    """Feedback do comando — e o que o teste de idempotência lê para saber que a 2ª rodada não
    mexeu em nada."""

    criadas: int
    atualizadas: int
    desativadas: int
    reativadas: int


def sincronizar_acoes(registro: RegistroAcoes) -> ContagemSync:
    """Recebe o registro por argumento para o teste não depender do global."""
    slugs_no_codigo = {implementada.acao.slug for implementada in registro.todas()}
    # Lido ANTES do upsert: depois dele toda linha do código já está ativa e a reativação seria
    # indistinguível de uma linha que nunca saiu.
    reativados = set(
        Acao.objects.filter(ativa=False, slug__in=slugs_no_codigo).values_list("slug", flat=True)
    )
    criadas = 0
    with transaction.atomic():
        for implementada in registro.todas():
            contrato = implementada.acao
            _, criada = Acao.objects.update_or_create(
                slug=contrato.slug,
                defaults={
                    "nome": contrato.nome,
                    # O contrato admite None; a coluna é `blank=True`, não anulável.
                    "nome_curto": contrato.nome_curto or "",
                    "tooltip": contrato.tooltip,
                    "estrutural": contrato.estrutural,
                    # Voltar ao registro reativa a linha — e ela reencontra as atribuições e
                    # concessões que continuaram penduradas nela enquanto esteve inativa.
                    "ativa": True,
                },
            )
            criadas += int(criada)
        # Apagar a linha da ação removida do código cascatearia atribuições e concessões reais: o
        # que sai do registro é desativado. Filtrar por `ativa=True` é o que faz a 2ª rodada contar
        # zero em vez de reescrever as mesmas linhas.
        desativadas = (
            Acao.objects.filter(ativa=True).exclude(slug__in=slugs_no_codigo).update(ativa=False)
        )
    return ContagemSync(
        criadas=criadas,
        atualizadas=len(slugs_no_codigo) - criadas,
        desativadas=desativadas,
        reativadas=len(reativados),
    )
