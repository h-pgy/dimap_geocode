from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle

from services.utils.pdf import EstiloTabela, EstiloTexto, FundoDoCabecalho, GradeDeLinhas, Respiro

from .models import Tema, TemaConfig


class MontarTema:
    """Callable: os valores declarados viram os estilos que escritores e marcas usam."""

    def __call__(self, config: TemaConfig) -> Tema:
        return self.pipeline(config)

    def pipeline(self, config: TemaConfig) -> Tema:
        tinta = colors.HexColor(config.paleta.tinta)
        estilos = self._estilos(config, tinta)
        return Tema(
            estilos=estilos,
            estilo_tabela=self._tabela(config, estilos),
            estilo_cabecalho_marca=EstiloTexto(
                fonte=config.tipografia.fonte,
                corpo_pt=config.tipografia.corpo_cabecalho_marca_pt,
                cor=tinta,
            ),
            estilo_rodape_marca=EstiloTexto(
                fonte=config.tipografia.fonte,
                corpo_pt=config.tipografia.corpo_rodape_marca_pt,
                cor=colors.HexColor(config.paleta.tinta_secundaria),
            ),
            entrelinha_marca_mm=config.tipografia.entrelinha_marca_mm,
        )

    def _estilos(self, config: TemaConfig, tinta: Color) -> dict[str, ParagraphStyle]:
        tipo = config.tipografia
        estilos = {
            "titulo": self._estilo(
                "titulo",
                config,
                tinta,
                tipo.corpo_titulo_pt,
                tipo.fonte_negrito,
                alignment=TA_CENTER,
                spaceAfter=12,
            ),
            # O espaço entre parágrafos é do ESTILO, não de um Spacer entre blocos: assim o
            # escritor devolve um flowable só, e a quebra de página nunca deixa espaçador órfão.
            "paragrafo": self._estilo(
                "paragrafo",
                config,
                tinta,
                tipo.corpo_paragrafo_pt,
                tipo.fonte,
                alignment=TA_JUSTIFY,
                firstLineIndent=12,
                spaceAfter=8,
            ),
            "paragrafo_recuado": self._estilo(
                "paragrafo_recuado",
                config,
                tinta,
                tipo.corpo_paragrafo_recuado_pt,
                tipo.fonte,
                alignment=TA_JUSTIFY,
                leftIndent=28,
                rightIndent=14,
                spaceAfter=8,
            ),
            "item": self._estilo("item", config, tinta, tipo.corpo_paragrafo_pt, tipo.fonte),
            "celula": self._estilo("celula", config, tinta, tipo.corpo_celula_pt, tipo.fonte),
            "cabecalho_tabela": self._estilo(
                "cabecalho_tabela", config, tinta, tipo.corpo_celula_pt, tipo.fonte_negrito
            ),
        }
        # Um estilo por nível, nomeado pelo número: é a chave que o escritor de subtítulo monta a
        # partir do bloco, e é o que faz acrescentar nível ser acrescentar corpo na tupla.
        for nivel, corpo_pt in enumerate(tipo.corpo_subtitulo_pt, start=1):
            estilos[f"subtitulo_{nivel}"] = self._estilo(
                f"subtitulo_{nivel}", config, tinta, corpo_pt, tipo.fonte_negrito, spaceAfter=6
            )
        return estilos

    def _estilo(
        self,
        nome: str,
        config: TemaConfig,
        cor: Color,
        corpo_pt: float,
        fonte: str,
        **extras: object,
    ) -> ParagraphStyle:
        # A entrelinha SEMPRE sai do fator: nenhum estilo do documento a declara solta, e é isso
        # que impede um corpo trocado no ambiente sair com o texto apertado.
        return ParagraphStyle(
            nome,
            fontName=fonte,
            fontSize=corpo_pt,
            leading=corpo_pt * config.tipografia.fator_entrelinha,
            textColor=cor,
            **extras,
        )

    def _tabela(self, config: TemaConfig, estilos: dict[str, ParagraphStyle]) -> EstiloTabela:
        horizontal_mm, vertical_mm = config.tipografia.respiro_celula_mm
        # Sem `ZebraDoCorpo`: fundo de linha é opaco e apagaria a marca d'água — ver Caveats.
        return EstiloTabela(
            celula=estilos["celula"],
            cabecalho=estilos["cabecalho_tabela"],
            regras=(
                FundoDoCabecalho(colors.HexColor(config.paleta.fundo_cabecalho_tabela)),
                GradeDeLinhas(
                    colors.HexColor(config.paleta.traco_tabela),
                    config.tipografia.espessura_traco_tabela_pt,
                ),
                Respiro(horizontal_mm=horizontal_mm, vertical_mm=vertical_mm),
            ),
        )


montar_tema = MontarTema()
