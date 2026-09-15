---
spec: documentos_oficiais/011
versao: v1
atualizado_em: 2026-09-15
testes_tdd: false
implementado: false
markers_obrigatorios: [artefato, integration]
changelog:
  - v1: versão inicial
---

# SPEC documentos_oficiais/011 — Planta de localização

## 1 · User story
**Requisito não-funcional** — um documento oficial passa a poder mostrar onde fica o objeto dele: as
geometrias plotadas sobre a ortofoto, numa imagem gerada no momento da emissão.

## 2 · Condições de pronto
- [ ] Dadas uma ou mais camadas de polígonos, a planta sai como **PNG** com a ortofoto do GeoSampa ao
      fundo e os polígonos desenhados por cima.
- [ ] O enquadramento cobre **todas** as geometrias com a **folga** configurada (15 m por padrão) de
      cada lado, é **quadrado** e fica centrado nelas.
- [ ] Geometria em **destaque** sai por cima das de **contexto**, com traço mais forte, qualquer que
      seja a ordem em que as camadas foram declaradas.
- [ ] Um documento oficial aceita a planta como **bloco de imagem raster**, que ocupa a largura pedida
      em milímetros sem distorcer a proporção.
- [ ] A amostra de conferência (`-m artefato`) traz uma planta sobre ortofoto real, conferível a olho.

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
        fundo = self._ortofoto(self._request(enquadramento, entrada.config))
        png = self._desenhar(fundo, enquadramento, entrada)
        return PlantaLocalizacao(png=png, enquadramento=enquadramento)

    def _enquadrar(self, entrada: PlantaLocalizacaoInput) -> BoundingBox:
        # Extensão de TODAS as geometrias, folga dos quatro lados, e o lado menor esticado até o
        # maior: a imagem é quadrada, e bbox não quadrado com width == height distorceria a ortofoto.
        uniao = GEOSGeometry(...).extent   # união das geometrias de todas as camadas
        minx, miny, maxx, maxy = _com_folga(uniao, entrada.config.folga_m)
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
        # Figure + FigureCanvasAgg, nunca pyplot: pyplot guarda estado global, e o processo web
        # emite certidões em threads concorrentes.
        figura = Figure(figsize=(entrada.config.lado_px / DPI,) * 2, dpi=DPI)
        FigureCanvasAgg(figura)
        eixo = figura.add_axes((0, 0, 1, 1))
        extensao = (
            enquadramento.minx,
            enquadramento.maxx,
            enquadramento.miny,
            enquadramento.maxy,
        )
        eixo.imshow(_imagem(fundo), extent=extensao)
        # O contexto primeiro e o destaque por último, não a ordem declarada: é o que põe o objeto
        # do documento por cima dos vizinhos.
        for camada in sorted(entrada.camadas, key=lambda c: c.estilo == EstiloGeometria.DESTAQUE):
            self._plotar(eixo, camada, entrada.config.paleta)
        eixo.set_axis_off()
        saida = BytesIO()
        figura.savefig(saida, format="png", dpi=DPI)
        return saida.getvalue()
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
A planta usa **matplotlib**, uma dependência nova e pesada. Desenhar polígono com furo, traço e
preenchimento com transparência sobre raster é o que ela faz de forma direta, e a escolha foi
pedida explicitamente. O custo é o tamanho da imagem Docker e o tempo de import no primeiro uso.

`ImagemRaster` guarda os **bytes** da planta dentro do bloco. A planta é gerada na emissão e não
existe em disco, e o bloco `Imagem` guarda caminho porque o SVG é ativo do repositório. O custo é
que o `ConteudoDocumento` passa a carregar alguns centenas de kB em memória até o render.

A cor da planta tem default em hex no domínio (`PaletaPlanta`), fora dos tokens CSS do design system.
A planta é pixel dentro de um PDF, e o CSS não chega lá, como já acontece com a `PaletaDocumento`. O
custo é que mudar o `sakura-500` do tema não muda a planta sozinho.

Cada emissão faz uma requisição GetMap de `lado_px` × `lado_px` ao WMS de raster. O GeoSampa não
publica limite de tamanho, e quem confirma que 1600 px é servido é o teste `integration` desta SPEC.
O custo é que a emissão fica tão lenta quanto o WMS de raster, sem cache.

## 8 · Testes (TDD)
- `test_enquadramento_une_camadas_e_soma_folga` — duas camadas afastadas cabem inteiras, com a folga
  a mais em cada lado.
- `test_enquadramento_e_quadrado_e_centrado` — geometria alongada produz bbox quadrado com o mesmo
  centro.
- `test_pede_ortofoto_raster_no_crs_e_tamanho_da_config` — o `WmsMapRequest` capturado pelo fake é
  raster, opaco, com o CRS e o `lado_px` da config.
- `test_camada_sem_geometria_recusada` — `CamadaPlanta(geometrias=())` falha na construção.
- `test_planta_devolve_png_do_tamanho_pedido` — os bytes começam com a assinatura PNG e medem
  `lado_px` × `lado_px`.
- `test_escritor_imagem_raster_respeita_largura_e_proporcao` — PNG 2:1 com 100 mm vira flowable de
  100 × 50 mm.
- `test_imagem_raster_recusa_conteudo_vazio` — bytes vazios falham na construção do bloco.
- `test_amostra_com_planta_sobre_ortofoto_ficticia` — o PDF de amostra traz a planta com destaque e
  contexto *(marker `artefato`)*.
- `test_planta_sobre_ortofoto_real` — lote real conhecido sobre o WMS do GeoSampa, publicado como PNG
  *(markers `integration`, `artefato`)*.
