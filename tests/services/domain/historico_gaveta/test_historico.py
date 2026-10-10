"""Testes da SPEC design/021: a regra do histórico da gaveta lateral."""

from services.domain.historico_gaveta import (
    AberturaInput,
    AbrirNoHistorico,
    Cena,
    Etiqueta,
    HistoricoGaveta,
    ItemHistorico,
    TipoGaveta,
)

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _item(chave: str, gaveta: str = "<div>gaveta</div>") -> ItemHistorico:
    etiqueta = Etiqueta(chave=chave, tipo=TipoGaveta.LOTE, resumo=f"SQL {chave}")
    cena = Cena(gaveta=gaveta, mapa={"cor": "#D84F7F"})
    return ItemHistorico(etiqueta=etiqueta, cena=cena)


def _abrir(historico: HistoricoGaveta, item: ItemHistorico) -> HistoricoGaveta:
    abrir = AbrirNoHistorico()
    return abrir(AberturaInput(historico=historico, item=item))


def _chaves(historico: HistoricoGaveta) -> list[str]:
    return [item.etiqueta.chave for item in historico.itens]


# ---------------------------------------------------------------------------
# Abrir uma gaveta
# ---------------------------------------------------------------------------


def test_abrir_poe_no_topo_sem_repetir_e_guarda_cinco() -> None:
    historico = HistoricoGaveta()
    for numero in range(1, 7):
        historico = _abrir(historico, _item(f"lote-{numero}"))

    assert _chaves(historico) == ["lote-6", "lote-5", "lote-4", "lote-3", "lote-2"]

    reaberta = _abrir(historico, _item("lote-3", gaveta="<div>cena nova</div>"))

    assert _chaves(reaberta) == ["lote-3", "lote-6", "lote-5", "lote-4", "lote-2"]
    topo = reaberta.itens[0]
    assert topo.cena is not None
    assert topo.cena.gaveta == "<div>cena nova</div>"
