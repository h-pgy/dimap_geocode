---
spec: documentos_oficiais/011
versao: v2
atualizado_em: 2026-09-23
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: planta desenhada com Pillow, e falha do WMS deixa de virar fundo neutro
---

# SPEC documentos_oficiais/011 — Planta de localização

## 1 · User story
**Requisito não-funcional** — um documento oficial passa a poder mostrar onde fica o objeto dele: as
geometrias plotadas sobre a ortofoto, numa imagem gerada no momento da emissão.

## 2 · Condições de pronto
- [x] Dadas uma ou mais camadas de polígonos, a planta sai como **PNG** com a ortofoto do GeoSampa ao
      fundo e os polígonos desenhados por cima.
- [x] O enquadramento cobre **todas** as geometrias com a **folga** configurada (15 m por padrão) de
      cada lado, é **quadrado** e fica centrado nelas.
- [x] Geometria em **destaque** sai por cima das de **contexto**, com traço mais forte, qualquer que
      seja a ordem em que as camadas foram declaradas.
- [x] Um documento oficial aceita a planta como **bloco de imagem raster**, que ocupa a largura pedida
      em milímetros sem distorcer a proporção.
- [x] Ortofoto indisponível **interrompe** a geração: o erro do WMS chega a quem encomendou a planta.

## 3 · Domínio
A planta é um **produto derivado** de geometrias e de uma ortofoto; ela não sabe se o polígono é
lote, desenho ou quadra. Quem decide o que é destaque e o que é contexto é o documento que a
encomenda — nas SPECs [certidao_lancamento/001](../certidao_lancamento/001-certidao-de-um-lote.md) e
[002](../certidao_lancamento/002-certidao-do-conjunto.md). O bloco novo entra no vocabulário da
SPEC [003](003-documento-oficial-timbrado.md) ao lado do `Imagem` vetorial.

**`services/domain/planta_localizacao/models.py`**

```python
class EstiloGeometria(StrEnum):
    DESTAQUE = "destaque"   # o objeto do documento
    CONTEXTO = "contexto"   # o que ajuda a ler o objeto


class CamadaPlanta(BaseModel):
    model_config = ConfigDict(frozen=True)

    geometrias: tuple[PolygonGeometry, ...] = Field(min_length=1)
    estilo: EstiloGeometria


class PaletaPlanta(BaseModel):
    """Os traços da planta. Defaults do domínio; o ambiente sobrepõe como no tema do documento."""

    model_config = ConfigDict(frozen=True)

    cor_destaque: str = "#D84F7F"      # sakura-500: o rosa que não tem par na ortofoto
    cor_contexto: str = "#CAF0F8"      # agua-100: claro o bastante para não competir com o destaque
    espessura_destaque_pt: float = 3.0
    espessura_contexto_pt: float = 1.2
    alfa_preenchimento_destaque: float = Field(default=0.15, ge=0, le=1)


class PlantaConfig(BaseModel):
    """O que é do processo: onde buscar a ortofoto, o tamanho e o CRS métrico das geometrias."""

    model_config = ConfigDict(frozen=True)

    camada_ortofoto: str
    crs: int
    folga_m: float = Field(default=15.0, ge=0)
    lado_px: int = Field(default=1600, gt=0)
    paleta: PaletaPlanta = PaletaPlanta()


class PlantaLocalizacaoInput(BaseModel):
    camadas: tuple[CamadaPlanta, ...] = Field(min_length=1)   # geometrias no CRS da config
    config: PlantaConfig


class PlantaLocalizacao(BaseModel):
    png: bytes
    enquadramento: BoundingBox
```

**`services/domain/documento_oficial/models/blocos.py`** — bloco novo, na união `Bloco`.

```python
class ImagemRaster(BlocoDocumento):
    """Imagem que só existe como pixel — a planta. Os bytes vêm prontos: o bloco não busca nada."""

    tipo: Literal["imagem_raster"] = "imagem_raster"
    conteudo: bytes = Field(min_length=1)
    largura_mm: float = Field(gt=0)
```

## 4 · Fora de escopo
- Amostra de conferência da planta e o `integration` contra o WMS real do GeoSampa — sem dono ainda.
- Escala gráfica, seta de norte e legenda na planta — sem dono ainda.
- Rótulos (SQL, número) sobre os polígonos — sem dono ainda.
- Base diferente da ortofoto (mapa base político, cadastro) — sem dono ainda.
- Cache da ortofoto entre emissões do mesmo lugar — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/integrations/wms` → `WmsFetcher`, `WmsMapRequest`, `BoundingBox`: GetMap da ortofoto.
- `@apps/core/management/commands/gerar_ortofotos_fundo.py` → como a `WmsConnectionConfig` é montada dos settings.
- `@services/domain/documento_oficial/escritores.py` → `EscritorImagem`, `montar_escritores`.
- `@services/domain/documento_oficial/amostra.py` → `MontarDocumentoAmostra`: onde a planta entra para conferência.
- `@services/utils/pdf` → a costura única com o reportlab.
- `@tests/conftest.py` → `publicar_artefato`.
- Skills: `documento-oficial`, `escrever-testes`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/integrations/wms/utils.py`** — espelho do `build_fetcher` do WFS.

```python
def build_wms_fetcher(source: WmsSettingsLike) -> WmsFetcher:
    return WmsFetcher(WmsConnectionConfig(
        vector_url=source.WMS_URL,
        raster_url=source.WMS_RASTER_URL,
        version=source.WMS_VERSION,
        request_timeout_seconds=source.WMS_REQUEST_TIMEOUT_SECONDS,
    ))
```

**`services/domain/planta_localizacao/planta.py`**

```python
OrtofotoDoEnquadramento = Callable[[WmsMapRequest], WmsImage]
DPI = 200


class GerarPlantaLocalizacao:
    def __init__(self, ortofoto: OrtofotoDoEnquadramento) -> None:
        self._ortofoto = ortofoto

    def __call__(self, entrada: PlantaLocalizacaoInput) -> PlantaLocalizacao:
        return self.pipeline(entrada)

    def pipeline(self, entrada: PlantaLocalizacaoInput) -> PlantaLocalizacao:
        enquadramento = self._enquadrar(entrada)
        # Sem try/except: documento oficial com planta falsa é pior que documento não emitido.
        fundo = self._ortofoto(self._request(enquadramento, entrada.config))
        png = self._desenhar(fundo, enquadramento, entrada)
        return PlantaLocalizacao(png=png, enquadramento=enquadramento)

    def _enquadrar(self, entrada: PlantaLocalizacaoInput) -> BoundingBox:
        # Extensão de TODAS as geometrias, folga dos quatro lados, e o lado menor esticado até o
        # maior: a imagem é quadrada, e bbox não quadrado com width == height distorceria a ortofoto.
        uniao = reduce(operator.or_, (para_geos(g, crs) for g in todas_as_geometrias))
        minx, miny, maxx, maxy = _com_folga(uniao.extent, entrada.config.folga_m)
        return _quadrado_centrado(minx, miny, maxx, maxy, f"EPSG:{entrada.config.crs}")

    def _request(self, enquadramento: BoundingBox, config: PlantaConfig) -> WmsMapRequest:
        return WmsMapRequest(
            layer=config.camada_ortofoto,
            bbox=enquadramento,
            crs=enquadramento.crs,
            width=config.lado_px,
            height=config.lado_px,
            raster=True,
            transparent=False,
            image_format="image/png",
        )

    def _desenhar(self, fundo: WmsImage, enquadramento: BoundingBox, entrada: PlantaLocalizacaoInput) -> bytes:
        # A ortofoto é a base; os traços vão numa camada RGBA à parte e entram por alpha_composite,
        # que é o que deixa o preenchimento do destaque semitransparente sobre a foto.
        base = self._base(fundo, entrada.config.lado_px)
        composta = PILImage.alpha_composite(base, self._sobrepor(enquadramento, entrada))
        saida = BytesIO()
        composta.convert("RGB").save(saida, format="PNG")
        return saida.getvalue()

    def _sobrepor(self, enquadramento: BoundingBox, entrada: PlantaLocalizacaoInput) -> PILImage.Image:
        sobreposicao = PILImage.new("RGBA", (entrada.config.lado_px,) * 2, (0, 0, 0, 0))
        pincel = ImageDraw.Draw(sobreposicao)
        # O contexto primeiro e o destaque por último, não a ordem declarada: é o que põe o objeto
        # do documento por cima dos vizinhos.
        for camada in sorted(entrada.camadas, key=lambda c: c.estilo == EstiloGeometria.DESTAQUE):
            self._plotar(pincel, camada, enquadramento, entrada.config)
        return sobreposicao
```

**`services/utils/pdf/raster.py`** — o reportlab continua entrando só por `services/utils/pdf`.

```python
def imagem_raster(conteudo: bytes, largura_mm: float) -> Flowable:
    leitor = ImageReader(BytesIO(conteudo))
    largura_px, altura_px = leitor.getSize()
    # A altura sai da proporção dos pixels: quem pede só a largura nunca distorce a planta.
    return Image(BytesIO(conteudo), width=largura_mm * mm, height=largura_mm * mm * altura_px / largura_px)
```

**`services/domain/documento_oficial/escritores.py`**

```python
class EscritorImagemRaster:
    def __call__(self, bloco: ImagemRaster) -> Flowable:
        return self.pipeline(bloco)

    def pipeline(self, bloco: ImagemRaster) -> Flowable:
        imagem = imagem_raster(bloco.conteudo, bloco.largura_mm)
        imagem.hAlign = "CENTER"
        return imagem
```

## 7 · Caveats
A planta usa **Pillow**, já presente no projeto para o pipeline de ortofotos de fundo. O custo é
desenhar anel, traço e preenchimento à mão, em vez de herdar o plot pronto de uma biblioteca de
gráficos.

`ImagemRaster` guarda os **bytes** da planta dentro do bloco. A planta é gerada na emissão e não
existe em disco, e o bloco `Imagem` guarda caminho porque o SVG é ativo do repositório. O custo é
que o `ConteudoDocumento` passa a carregar alguns centenas de kB em memória até o render.

A cor da planta tem default em hex no domínio (`PaletaPlanta`), fora dos tokens CSS do design system.
A planta é pixel dentro de um PDF, e o CSS não chega lá, como já acontece com a `PaletaDocumento`. O
custo é que mudar o `sakura-500` do tema não muda a planta sozinho.

Cada emissão faz uma requisição GetMap de `lado_px` × `lado_px` ao WMS de raster, e a falha dela
interrompe a emissão. O GeoSampa não publica limite de tamanho, e nenhum teste desta SPEC confirma
que 1600 px é servido. O custo é que a emissão fica tão lenta e tão disponível quanto o WMS de
raster, sem cache.

## 8 · Testes (TDD)
- `test_planta_desenha_sobre_a_ortofoto_recebida` — o PNG sai no `lado_px` pedido, com os pixels da
  ortofoto preservados sob os traços.
- `test_planta_propaga_erro_do_wms` — ortofoto indisponível levanta o erro em vez de devolver fundo
  neutro.
- `test_enquadramento_une_camadas_e_soma_folga` — duas camadas afastadas cabem inteiras, num bbox
  quadrado centrado nelas, com a folga a mais em cada lado, e o GetMap sai raster no CRS da config.
- `test_escritor_imagem_raster_respeita_largura_e_proporcao` — PNG 2:1 com 100 mm vira flowable de
  100 × 50 mm.
- `test_imagem_raster_recusa_conteudo_vazio` — bytes vazios falham na construção do bloco.
