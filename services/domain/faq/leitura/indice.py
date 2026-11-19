from services.domain.faq.conteudo import Faq
from services.domain.faq.taxonomia import Tema

from .models import (
    IndiceFaq,
    ItemIndice,
    MontagemIndiceInput,
    SecaoSubtema,
    SecaoTema,
)
from .visibilidade import eh_visivel


def _chave_tema(tema: Tema) -> tuple[int, str]:
    return (tema.ordem, tema.nome.casefold())


def _chave_item(item: ItemIndice) -> str:
    return item.faq.pergunta.chave


class MontarIndice:
    def __call__(self, entrada: MontagemIndiceInput) -> IndiceFaq:
        return self.pipeline(entrada)

    def pipeline(self, entrada: MontagemIndiceInput) -> IndiceFaq:
        visiveis = self._visiveis(entrada)
        por_id = {f.id: f for f in visiveis}
        itens = [self._item(f, por_id) for f in visiveis]
        return IndiceFaq(secoes=self._agrupar(itens))

    def _visiveis(self, entrada: MontagemIndiceInput) -> list[Faq]:
        # Defesa em profundidade: o índice não confia que a query já filtrou.
        return [f for f in entrada.faqs if eh_visivel(f, entrada.leitor)]

    def _item(self, faq: Faq, por_id: dict[int | None, Faq]) -> ItemIndice:
        # Relacionada fora de `por_id` é rascunho ou interna para este leitor: some sem rastro.
        relacionadas = [por_id[i] for i in faq.relacionadas if i in por_id]
        return ItemIndice(faq=faq, relacionadas=relacionadas)

    def _agrupar(self, itens: list[ItemIndice]) -> list[SecaoTema]:
        diretos: dict[tuple[str, ...], list[ItemIndice]] = {}
        subtemas: dict[tuple[str, ...], dict[str, list[ItemIndice]]] = {}
        raizes: dict[tuple[str, ...], Tema] = {}
        subs: dict[tuple[str, str], Tema] = {}

        for item in itens:
            tema = item.faq.tema
            raiz = tema.pai if tema.pai is not None else tema
            chave_raiz: tuple[str, ...] = (raiz.nome,)
            raizes[chave_raiz] = raiz
            if tema.pai is None:
                diretos.setdefault(chave_raiz, []).append(item)
            else:
                subs[(raiz.nome, tema.nome)] = tema
                subtemas.setdefault(chave_raiz, {}).setdefault(tema.nome, []).append(
                    item
                )

        secoes: list[SecaoTema] = []
        for chave_raiz in sorted(raizes, key=lambda c: _chave_tema(raizes[c])):
            raiz = raizes[chave_raiz]
            por_subtema = subtemas.get(chave_raiz, {})
            secoes_subtema = [
                SecaoSubtema(
                    subtema=subs[(raiz.nome, nome)],
                    itens=sorted(lista, key=_chave_item),
                )
                for nome, lista in sorted(
                    por_subtema.items(),
                    key=lambda par: _chave_tema(subs[(raiz.nome, par[0])]),
                )
            ]
            secoes.append(
                SecaoTema(
                    tema=raiz,
                    itens=sorted(diretos.get(chave_raiz, []), key=_chave_item),
                    subtemas=secoes_subtema,
                ),
            )
        return secoes
