from collections.abc import Mapping

from services.utils.pdf.marcacao import Marcacao
from services.utils.pdf.models import Margens, Orientacao, TamanhoPagina


class MarcacaoDocumento:
    """A principal é obrigatória e vale onde nenhuma outra reivindica a página."""

    def __init__(
        self,
        principal: Marcacao,
        primeira: Marcacao | None = None,
        ultima: Marcacao | None = None,
        *,
        # Keyword-only porque é o parâmetro de exceção: quem o usa está nomeando página por
        # número, e o nome no ponto de chamada é o que impede trocá-lo de posição sem perceber.
        marcacoes_especificas: Mapping[int, Marcacao] | None = None,
    ) -> None:
        self._principal = principal
        self._primeira = primeira
        self._ultima = ultima
        self._especificas = dict(marcacoes_especificas or {})
        self._validar()

    def para(self, pagina: int, total: int) -> Marcacao:
        # A ordem é a da especificidade: número exato vence extremo, e extremo vence a principal.
        # `primeira` antes de `ultima` decide o documento de UMA página, em que a mesma folha é
        # as duas coisas — e a primeira é a que o autor tinha em mente.
        if (especifica := self._especificas.get(pagina)) is not None:
            return especifica
        if pagina == 1 and self._primeira is not None:
            return self._primeira
        if pagina == total and self._ultima is not None:
            return self._ultima
        return self._principal

    def margens(self, tamanho: TamanhoPagina) -> Margens:
        # O MAIOR de cada borda, entre todas as marcações. A moldura do corpo é fixada antes de
        # existir página alguma, então ela precisa caber a marcação mais alta — é o que permite
        # capa com timbre grande e miolo com timbre compacto sem a paginação mudar.
        todas = [m.margens(tamanho) for m in self._todas()]
        return Margens(
            esquerda_mm=max(m.esquerda_mm for m in todas),
            direita_mm=max(m.direita_mm for m in todas),
            superior_mm=max(m.superior_mm for m in todas),
            inferior_mm=max(m.inferior_mm for m in todas),
        )

    def orientacao(self) -> Orientacao:
        return self._principal.orientacao

    def _validar(self) -> None:
        # Uma orientação por documento: o `pagesize` do reportlab é do documento inteiro, e
        # misturar orientações exigiria PageTemplates — ver Fora de escopo da SPEC.
        divergentes = {m.orientacao for m in self._todas()}
        if len(divergentes) > 1:
            raise ValueError(f"Marcações de orientações diferentes no mesmo documento: {divergentes}")
        # Página 0 ou negativa é erro de quem chama, e silenciá-la deixaria a marcação sumir.
        if invalidas := [n for n in self._especificas if n < 1]:
            raise ValueError(f"Página específica precisa ser 1-based: {sorted(invalidas)}")

    def _todas(self) -> tuple[Marcacao, ...]:
        opcionais = (self._primeira, self._ultima, *self._especificas.values())
        return (self._principal, *(m for m in opcionais if m is not None))
