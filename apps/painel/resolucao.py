"""A cascata do painel (SPEC painel/001): o item filtra pela caneta — só o ato, nunca a view
livre —, o grupo some sem nenhum item visível, e a aba some sem nenhum grupo visível, salvo a
básica.
"""

from django.urls import reverse

from pydantic import BaseModel, ConfigDict

from .estrutura import (
    Aba,
    ContratoPainel,
    Grupo,
    ItemAcao,
    ItemLivre,
    ItemResolvido,
    AbaResolvida,
    GrupoResolvido,
    PainelResolvido,
)


class MontagemPainel(BaseModel):
    model_config = ConfigDict(frozen=True)

    painel: ContratoPainel
    # O router recebe o CONJUNTO, não o usuário: é o que o mantém puro e testável sem banco.
    slugs_liberados: frozenset[str]
    perfil_id: int


class ResolvedorPainel:
    """A regra inteira do painel está aqui: quem não tem caneta não vê o ato, o que é livre nunca
    some, e o que ficou vazio desaparece."""

    def __call__(self, montagem: MontagemPainel) -> PainelResolvido:
        return self.pipeline(montagem)

    def pipeline(self, montagem: MontagemPainel) -> PainelResolvido:
        abas = (self._aba(aba, montagem) for aba in montagem.painel.abas)
        # A aba básica sobrevive por ser básica, não por ter sobrado item: é ela que impede o
        # painel de abrir vazio — e é o mesmo campo que o template lê para abri-la por padrão.
        return PainelResolvido(abas=tuple(aba for aba in abas if not aba.vazia() or aba.basica))

    def _aba(self, aba: Aba, montagem: MontagemPainel) -> AbaResolvida:
        grupos = (self._grupo(grupo, montagem) for grupo in aba.grupos)
        return AbaResolvida(
            slug=aba.slug,
            rotulo=aba.rotulo,
            titulo=aba.titulo,
            descricao=aba.descricao,
            # O avulso passa pelo MESMO filtro: estar fora de poço é posição na página, não
            # dispensa.
            itens_acima=self._itens(aba.itens_acima, aba.partial_padrao, montagem),
            grupos=tuple(grupo for grupo in grupos if grupo.itens),
            itens_abaixo=self._itens(aba.itens_abaixo, aba.partial_padrao, montagem),
            basica=aba.basica,
        )

    def _grupo(self, grupo: Grupo, montagem: MontagemPainel) -> GrupoResolvido:
        return GrupoResolvido(
            rotulo=grupo.rotulo,
            itens=self._itens(grupo.itens, grupo.partial_padrao, montagem),
        )

    def _itens(
        self,
        itens: tuple[ItemAcao | ItemLivre, ...],
        partial_padrao: str,
        montagem: MontagemPainel,
    ) -> tuple[ItemResolvido, ...]:
        return tuple(
            self._item(item, partial_padrao, montagem.perfil_id)
            for item in itens
            if self._visivel(item, montagem.slugs_liberados)
        )

    def _visivel(self, item: ItemAcao | ItemLivre, slugs_liberados: frozenset[str]) -> bool:
        # O livre não é ato: não há caneta que o libere, e por isso não há caneta que o esconda.
        if isinstance(item, ItemLivre):
            return True
        return item.acao.acao.slug in slugs_liberados

    def _item(self, item: ItemAcao | ItemLivre, partial_padrao: str, perfil_id: int) -> ItemResolvido:
        # As duas naturezas convergem para o MESMO resolvido: o template desenha um card só, e o
        # padrão do continente só cede quando o item traz o seu.
        partial = item.partial or partial_padrao
        if isinstance(item, ItemLivre):
            argumentos = {item.argumento_perfil: perfil_id} if item.argumento_perfil else {}
            return ItemResolvido(
                partial=partial,
                url=reverse(item.url_name, kwargs=argumentos),
                nome=item.nome,
                tooltip=item.tooltip,
                slug=item.slug,
                variante_icone=item.variante_icone,
            )
        acao = item.acao.acao
        return ItemResolvido(
            partial=partial,
            url=reverse(item.acao.url_name),
            nome=acao.nome,
            tooltip=acao.tooltip,
            slug=acao.slug,
            variante_icone=item.variante_icone,
        )
