from services.utils.normalization import normalize_text

from .models import AvatarIniciaisInput, AvatarIniciaisOutput

# dy="0.35em" em vez de dominant-baseline: rasterizadores de PDF ignoram a segunda.
GABARITO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"'
    ' role="img" aria-label="{iniciais}">'
    '<circle cx="50" cy="50" r="50" fill="{cor_fundo}"/>'
    '<text x="50" y="50" dy="0.35em" text-anchor="middle"'
    ' font-family="Roboto, ui-sans-serif, system-ui, sans-serif"'
    ' font-size="42" font-weight="700" fill="{cor_tinta}">{iniciais}</text>'
    "</svg>"
)


class AvatarIniciaisSvg:
    def __call__(self, entrada: AvatarIniciaisInput) -> AvatarIniciaisOutput:
        return self.pipeline(entrada)

    def pipeline(self, entrada: AvatarIniciaisInput) -> AvatarIniciaisOutput:
        iniciais = self._extrair_iniciais(entrada.nome, entrada.sobrenome)
        svg = GABARITO_SVG.format(
            iniciais=iniciais,
            cor_fundo=entrada.cor_fundo,
            cor_tinta=entrada.cor_tinta,
        )
        return AvatarIniciaisOutput(
            iniciais=iniciais,
            svg=svg,
        )

    def _extrair_iniciais(self, nome: str, sobrenome: str) -> str:
        primeiro = self._primeira_letra(self._termos(nome)[:1])
        ultimo = self._primeira_letra(self._termos(sobrenome)[-1:])
        return f"{primeiro}{ultimo}"

    def _termos(self, texto: str) -> list[str]:
        # Só termos alfabéticos: fecha a porta de injeção de markup no gabarito.
        # Termo de uma letra é resíduo de partícula elidida ("d'Angelo" -> "D ANGELO"), não nome.
        return [
            termo
            for termo in normalize_text(texto).split()
            if termo.isalpha() and len(termo) > 1
        ]

    def _primeira_letra(self, termos: list[str]) -> str:
        return termos[0][0].upper() if termos else ""
