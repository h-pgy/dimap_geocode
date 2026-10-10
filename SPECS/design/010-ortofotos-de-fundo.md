---
spec: design/010
versao: v10
atualizado_em: 2026-10-09
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: o fundo ganha controle de quem olha — troca, rodízio de um minuto, liga/desliga e velocidade
  - v3: Pico do Jaraguá entra no catálogo padrão
  - v4: a busca passa pelo WmsFetcher e o enquadramento troca zoom por metros por pixel
  - v5: a requisição declara o CRS explicitamente, em vez de depender do default da conexão
  - v6: a conexão do comando declara o timeout do GetMap
  - v7: a troca ganha crossfade — o `transition:true` nativo não estava suavizando, então o fade
    passa a ser manual, via as classes que o próprio HTMX aplica no swap (sem JS)
  - v8: fim do flash branco ao navegar — rocha sempre por baixo, carga da página sem fade, a
    ortofoto em tela mantida entre telas e view transition entre documentos
  - v9: a subida gera as ortofotos que faltam, e o GeoSampa fora do ar vira aviso no stdout em
    vez de erro
  - v10: as views do app `mapping` viram pacote, e a do fundo passa a `apps/mapping/views/fundo.py` (SPEC design/021)
---

# SPEC design/010 — Ortofotos de fundo pré-geradas

## 1 · User story
O servidor da DIMAP percorre as telas da área administrativa no uso diário para obter cada tela já
com o fundo montado, sem esperar o carregamento do mapa a cada navegação.

## 2 · Condições de pronto
- [ ] A área administrativa **não faz nenhuma requisição ao GeoSampa** em tempo de request, e uma
      ortofoto já vista **não é rebuscada**.
- [ ] A primeira tela entra num **ponto sorteado**, a navegação **mantém o que está em tela** sem
      flash, e o fundo **troca sozinho a cada minuto**.
- [ ] O servidor **troca o fundo na hora**, **desliga** e **ajusta a velocidade** da deriva.
- [ ] Desligar o fundo ou mudar a velocidade **permanece** na tela seguinte e na sessão seguinte.
- [ ] A deriva **nunca descobre a borda da imagem**, em qualquer proporção de tela.
- [ ] A deriva **para** sob `prefers-reduced-motion: reduce`.
- [ ] Sem **nenhuma ortofoto disponível**, as telas administrativas continuam respondendo e a lente
      cai só no gradiente.
- [ ] Reexecutar a geração **não busca nada na rede**; acrescentar um ponto ao catálogo faz **só
      aquele ponto** ser buscado.
- [ ] Um ponto com coordenada **fora do município de São Paulo** é recusado no boot.
- [ ] **Subir o sistema gera as ortofotos que faltam** no disco, e o stdout **anuncia o download**
      antes de ele começar e a cada ortofoto.
- [ ] Com o **GeoSampa fora do ar** — sem conexão ou sem resposta no prazo —, a geração **não pede
      nenhuma ortofoto**: termina com saída zero e **aviso no stdout** nomeando os pontos que
      ficaram sem imagem.
- [ ] **Qualquer outro erro** da geração termina em erro, e na subida **derruba o web**.
- [ ] O design foi aprovado no **mock**, e as peças foram portadas para
      `static/src/tema-dimap.dev.css` e para o styleguide.

## 3 · Domínio
Iteração de infraestrutura visual: nenhum model, nenhuma migração. A ontologia é o catálogo dos
pontos que enquadram cada ortofoto — a chave é o nome do arquivo gerado.

A lente que cobre a imagem é a de [user_admin/007](../user_admin/007-design-area-administrativa.md),
e a pergunta que esta SPEC faz a ela é: **o que da lente é do material e o que era compensação do
canvas do Leaflet?** O `grayscale` era compensação — sai da lente, porque a ortofoto passa a ser
gravada em tons de cinza. `brightness` e `contrast` são do material e ficam.

**`config/pontos_fundo.py`**
```python
class PontoFundo(BaseModel):
    """Ponto do território paulistano que enquadra uma ortofoto de fundo."""

    descricao: str
    lat: float = Field(ge=LAT_MINIMA, le=LAT_MAXIMA)
    lng: float = Field(ge=LNG_MINIMA, le=LNG_MAXIMA)


class CatalogoPontosFundo(RootModel[dict[str, PontoFundo]]):
    """A chave é o nome do arquivo .png — é ela que liga o catálogo ao disco."""

    @field_validator("root")
    @classmethod
    def _catalogo_nao_vazio(cls, pontos: dict[str, PontoFundo]) -> dict[str, PontoFundo]:
        if not pontos:
            raise ValueError("o catálogo de pontos de fundo não pode ser vazio")
        return pontos
```

A rota que serve o fundo é **aberta**: a tela de login é anônima e mostra o mesmo fundo. Ela não
pratica ato administrativo — devolve o nome de um arquivo estático — e por isso é a exceção do §3.5
do CLAUDE.md, declarada aqui.

**Mock:** [010-mock-ortofotos-de-fundo.html](010-mock-ortofotos-de-fundo.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Ortofoto do mapa principal da busca, que segue vindo do WMS em tempo real — sem dono ainda.
- Regeneração automática quando a camada oficial mudar de ano (`ORTO_RGB_2020` → seguinte) — sem
  dono ainda.
- Escolha de um ponto específico pelo servidor: o controle troca, não seleciona — sem dono ainda.

## 5 · Peças de referência a compor
- `@config/settings.py` → leitura de `paleta_ds.json`: JSON versionado lido no boot, falhando alto.
- `@services/integrations/wms` → `WmsFetcher`, `WmsMapRequest`, `BoundingBox`: o GetMap ao raster
  do GeoSampa, com erro de rede e ServiceException já encapsulados.
- `@services/integrations/wms` → `WmsConnectionError`, `WmsTimeoutError`: o GeoSampa fora do ar;
  `WmsError`: a base de todo erro do WMS ([ingestao_dados/002](../ingestao_dados/002-wms-fetcher.md)).
- `@docker/entrypoint.sh` → o roteiro da subida do web, sob `set -e`.
- `@tests/docker/test_entrypoint.py` → entrypoint exercitado por subprocesso com `python` falso.
- `@services/scripts/contrato.py` → `ScriptRunner`: contrato de entrada de todo script.
- `@apps/core/management/commands/atualizar_dados.py` → comando fino: parsing, chamada e stdout.
- `@templates/mapping/_mapa_admin.html` → as quatro camadas da lente sobre o fundo.
- `@static/src/tema-dimap.dev.css` → `.toggle-onsen`: o vocabulário poço + disco gravado do
  `.range-onsen`; `.btn-etched` + `.etched`: a gravação em repouso.
- `@templates/partials/_filtros_gravacao.html` → defs `#etched-onsen`, sem os quais nada grava.
- Skills: `mock`, `componentes-frontend`, `management-commands`, `escrever-testes`, `htmx`.

## 6 · Snippets

O catálogo é JSON versionado ao lado da paleta, lido no boot pelo mesmo padrão, e sobrescrevível
pelo `.env` para quem quiser outro recorte sem tocar no repositório.

**`config/pontos_fundo.json`**
```json
{
  "anhangabau":  {"descricao": "Vale do Anhangabaú — Centro",       "lat": -23.5450, "lng": -46.6390},
  "ibirapuera":  {"descricao": "Parque Ibirapuera — Zona Sul",      "lat": -23.5874, "lng": -46.6576},
  "butanta":     {"descricao": "Cidade Universitária — Zona Oeste", "lat": -23.5595, "lng": -46.7313},
  "itaquera":    {"descricao": "Arena Corinthians — Zona Leste",    "lat": -23.5453, "lng": -46.4742},
  "anhembi":     {"descricao": "Campo de Marte — Zona Norte",       "lat": -23.5145, "lng": -46.6370},
  "cantareira":  {"descricao": "Serra da Cantareira — Zona Norte",  "lat": -23.4585, "lng": -46.6300},
  "jaragua":     {"descricao": "Pico do Jaraguá — Zona Noroeste",   "lat": -23.4570, "lng": -46.7660},
  "interlagos":  {"descricao": "Autódromo de Interlagos — Sul",     "lat": -23.7010, "lng": -46.6975}
}
```

**`config/settings.py`**
```python
# Mesmo padrão da paleta: falha alto no boot se o arquivo sumir ou o ponto cair fora do município.
# O .env vence o arquivo — é o que permite trocar o recorte sem editar o repositório.
_PONTOS_FUNDO_PADRAO = (BASE_DIR / "config" / "pontos_fundo.json").read_text()
MAP_FUNDO_PONTOS = CatalogoPontosFundo.model_validate_json(
    _env.map_fundo_pontos or _PONTOS_FUNDO_PADRAO
).root
MAP_FUNDO_DIR = BASE_DIR / "static" / "src" / "img" / "ortofotos_fundo"
MAP_FUNDO_LARGURA_PX = 2000
MAP_FUNDO_ALTURA_PX = 1250
# Resolução do recorte, em metros de terreno por pixel (31983 é métrico de verdade).
MAP_FUNDO_METROS_POR_PIXEL = 4.4
```

O enquadramento é a única conta da SPEC, e em 31983 ela é aritmética de metros: a reprojeção é do
GeoDjango e o recorte sai no `BoundingBox` que o `WmsFetcher` consome.

**`services/scripts/ortofotos_fundo/enquadramento.py`**
```python
def enquadrar(ponto: PontoFundo, config: OrtofotoConfig) -> BoundingBox:
    centro = Point(ponto.lng, ponto.lat, srid=config.crs_entrada)
    centro.transform(config.crs_saida)
    meia_largura = config.largura_px / 2 * config.metros_por_pixel
    meia_altura = config.altura_px / 2 * config.metros_por_pixel
    return BoundingBox(
        minx=centro.x - meia_largura,
        miny=centro.y - meia_altura,
        maxx=centro.x + meia_largura,
        maxy=centro.y + meia_altura,
        crs=f"EPSG:{config.crs_saida}",
    )
```

O gerador é a classe callable do §7.1: `__call__` fino, `pipeline` orquestrando os passos. A
idempotência é o `exists()` — quem já está no disco não vira requisição. Antes da primeira ortofoto
vai uma sonda: um GetMap de poucos pixels na mesma camada, que responde se o GeoSampa está no ar sem
custar o recorte inteiro. Quem imprime é o comando: o gerador recebe por composição a função que
anuncia o progresso.

**`services/scripts/ortofotos_fundo/gerador.py`**
```python
SONDA_LADO_PX = 16
# Só o GeoSampa fora do ar vira pendência: status de erro e ServiceException sobem como erro.
ERROS_DE_INDISPONIBILIDADE = (WmsConnectionError, WmsTimeoutError)


def _calado(mensagem: str) -> None:
    return None


class GeradorOrtofotosFundo:
    def __init__(self, avisar: Callable[[str], None] = _calado) -> None:
        self.avisar = avisar

    def __call__(self, config: OrtofotoConfig, *, verbose: bool = False, manual: bool = True) -> OrtofotoResultado:
        return self.pipeline(config)

    def pipeline(self, config: OrtofotoConfig) -> OrtofotoResultado:
        faltantes = self._faltantes(config)
        geradas: list[str] = []
        indisponibilidade: str | None = None
        # Catálogo inteiro no disco: nem a sonda vai à rede.
        if faltantes:
            # Antes da sonda: se o GeoSampa demorar, quem olha o log já sabe o que a subida espera.
            self.avisar(f"Baixando {len(faltantes)} ortofoto(s) de fundo do GeoSampa...")
            try:
                self._sondar(next(iter(faltantes.values())), config)
                for ordem, (chave, ponto) in enumerate(faltantes.items(), start=1):
                    self.avisar(f"[{ordem}/{len(faltantes)}] {chave}")
                    self._gravar(self._buscar(ponto, config), config.destino / f"{chave}.png")
                    geradas.append(chave)
            # Um except só para a sonda e para o laço: GeoSampa que cai no meio para a geração do
            # mesmo jeito, e o que já foi gravado fica no disco e em `geradas`.
            except ERROS_DE_INDISPONIBILIDADE as exc:
                indisponibilidade = str(exc)
        return OrtofotoResultado(
            geradas=geradas,
            puladas=[chave for chave in config.pontos if chave not in faltantes],
            pendentes=[chave for chave in faltantes if chave not in geradas],
            indisponibilidade=indisponibilidade,
        )

    def _faltantes(self, config: OrtofotoConfig) -> dict[str, PontoFundo]:
        # A chave é o nome do arquivo: ponto novo no catálogo é o único que vai à rede.
        return {
            chave: ponto
            for chave, ponto in config.pontos.items()
            if config.forcar or not (config.destino / f"{chave}.png").exists()
        }

    def _sondar(self, ponto: PontoFundo, config: OrtofotoConfig) -> None:
        # A mesma requisição da ortofoto, encolhida: o enquadramento sai do config, então
        # 16 × 16 px são ~70 m de lado em vez de 8,8 km.
        sonda = config.model_copy(update={"largura_px": SONDA_LADO_PX, "altura_px": SONDA_LADO_PX})
        self._buscar(ponto, sonda)

    def _buscar(self, ponto: PontoFundo, config: OrtofotoConfig) -> bytes:
        # raster=True escolhe o WMS de raster: a ortofoto não é servida pelo WMS geral do GeoSampa.
        requisicao = WmsMapRequest(
            layer=config.camada,
            bbox=enquadrar(ponto, config),
            crs=f"EPSG:{config.crs_saida}",
            width=config.largura_px,
            height=config.altura_px,
            raster=True,
            transparent=False,
            image_format="image/png",
        )
        return WmsFetcher(config.conexao)(requisicao).content

    def _gravar(self, bruto: bytes, destino: Path) -> None:
        # Cinza no disco, não no CSS: a lente descartaria os outros dois canais de qualquer jeito,
        # e o PNG colorido custa três vezes o mesmo pixel renderizado.
        imagem = Image.open(BytesIO(bruto)).convert("L")
        destino.parent.mkdir(parents=True, exist_ok=True)
        imagem.save(destino, format="PNG", optimize=True)
```

**`services/scripts/ortofotos_fundo/contrato.py`**
```python
class OrtofotoConfig(BaseModel):
    pontos: dict[str, PontoFundo]      # o catálogo do §3, envelopado
    conexao: WmsConnectionConfig       # a config da integration, envelopada
    destino: Path
    camada: str
    metros_por_pixel: float
    largura_px: int
    altura_px: int
    crs_entrada: int
    crs_saida: int
    forcar: bool = False


class OrtofotoResultado(BaseModel):
    geradas: list[str]
    puladas: list[str]
    # Pontos que seguem sem PNG porque o GeoSampa não respondeu.
    pendentes: list[str] = []
    # O erro do WMS que interrompeu a geração; None = nada a interrompeu.
    indisponibilidade: str | None = None
```

O comando é a fronteira de erro: GeoSampa fora do ar chega pronto no DTO e sai como aviso, com
código de saída zero; o resto do `WmsError` vira `CommandError`, e o que não é WMS sobe cru.

**`apps/core/management/commands/gerar_ortofotos_fundo.py`**
```python
class Command(BaseCommand):
    help = "Gera as ortofotos de fundo da área administrativa que ainda não estão em disco."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--forcar", action="store_true", help="rebusca mesmo o que já existe.")

    def handle(self, *args: object, **options: object) -> None:
        # Todo o parsing de settings acontece aqui: o script recebe um DTO pronto.
        config = OrtofotoConfig(
            pontos=MAP_FUNDO_PONTOS,
            conexao=WmsConnectionConfig(
                vector_url=WMS_URL,
                raster_url=WMS_RASTER_URL,
                version=WMS_VERSION,
                request_timeout_seconds=WMS_REQUEST_TIMEOUT_SECONDS,
            ),
            destino=MAP_FUNDO_DIR,
            camada=WMS_LAYER_ORTOFOTO,
            metros_por_pixel=MAP_FUNDO_METROS_POR_PIXEL,
            largura_px=MAP_FUNDO_LARGURA_PX,
            altura_px=MAP_FUNDO_ALTURA_PX,
            crs_entrada=MAP_OUTPUT_CRS,
            crs_saida=MAP_INTERPOLATION_CRS,
            forcar=bool(options["forcar"]),
        )
        try:
            resultado = GeradorOrtofotosFundo(avisar=self.stdout.write)(config)
        except WmsError as exc:
            raise CommandError(f"geração abortada: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(resultado.geradas)} gerada(s), {len(resultado.puladas)} já em disco."
            )
        )
        # stdout, e não stderr nem CommandError: é a linha que aparece no log do container sem
        # derrubar o `set -e` do entrypoint.
        if resultado.pendentes:
            self.stdout.write(
                self.style.WARNING(
                    f"AVISO: GeoSampa indisponível ({resultado.indisponibilidade}). "
                    f"{len(resultado.pendentes)} ortofoto(s) de fundo sem gerar: "
                    f"{', '.join(resultado.pendentes)}. "
                    "Rode `manage.py gerar_ortofotos_fundo` quando o serviço voltar."
                )
            )
```

A subida chama o comando depois da migração e fora do bloco dela: a geração não toca o banco.

**`docker/entrypoint.sh`** — antes do `exec "$@"`:
```sh
if [ -f manage.py ]; then
    echo "==> Gerando ortofotos de fundo que faltam..."
    # Sem `||`: o comando já sai zero com o GeoSampa fora do ar, e o que sobra é erro de verdade,
    # que o `set -e` não deve engolir.
    python manage.py gerar_ortofotos_fundo
fi
```

O sorteio nunca devolve o que já está na tela — é o que faz o rodízio e o botão Trocar mudarem
alguma coisa a cada acionamento.

**`services/utils/sorteio/__init__.py`**
```python
def sortear_diferente(opcoes: Sequence[str], atual: str | None) -> str:
    """Sorteia entre as opções, evitando `atual`. Com uma única opção, devolve ela."""
    alternativas = [opcao for opcao in opcoes if opcao != atual] or list(opcoes)
    return random.choice(alternativas)
```

A troca é hipermídia, não estado no cliente: o canvas se repõe sozinho pelo `hx-trigger`, e o botão
dispara a mesma rota. Quem sabe qual ortofoto está na tela é o HTML que a mostra.

**`apps/mapping/views.py`**
```python
def fundo_ortofoto(request: HttpRequest) -> HttpResponse:
    """Rota aberta (§3): a tela de login é anônima e mostra o mesmo fundo."""
    disponiveis = ortofotos_disponiveis()
    escolhida = sortear_diferente(disponiveis, request.GET.get("atual")) if disponiveis else None
    return render(request, "mapping/_fundo_ortofoto.html", {"ortofoto_fundo": escolhida})
```

**`apps/mapping/context.py`**
```python
@cache
def ortofotos_disponiveis() -> tuple[str, ...]:
    """Interseção do catálogo com o disco: ponto sem PNG gerado não entra no sorteio."""
    return tuple(chave for chave in MAP_FUNDO_PONTOS if (MAP_FUNDO_DIR / f"{chave}.png").exists())


def ortofoto_do_fundo(em_tela: str | None) -> str | None:
    disponiveis = ortofotos_disponiveis()
    if not disponiveis:
        return None
    if em_tela in disponiveis:
        return em_tela
    return sortear_diferente(disponiveis, None)
```

**`apps/mapping/context_processors.py`** — toda tela lê a ortofoto que já estava em tela (cookie
`ortofoto_fundo`, escrito pelo `fundo_ortofoto.js` ao revelar cada camada), em vez de sortear outra.
```python
def fundo_admin(request: HttpRequest) -> dict[str, Any]:
    return {"ortofoto_fundo": ortofoto_do_fundo(request.COOKIES.get(COOKIE_ORTOFOTO_FUNDO))}
```

A rocha fica sempre por baixo da ortofoto: a lente nunca tinge o branco da página enquanto a foto
decodifica. A camada da carga da página nasce visível, sem fade — o fade de rocha para foto a cada
navegação era ele mesmo o flash; só o rodízio (design/011) faz crossfade. O `<img>` pede
`decoding="sync"` para o primeiro quadro esperar a foto em cache, e a navegação entre telas usa
`@view-transition { navigation: auto; }`: a página antiga só sai quando a nova está pintada.
**`templates/mapping/_fundo_ortofoto.html`**
```django
<div class="fundo-ortofoto" id="fundo-ortofoto"
     hx-get="{% url 'mapping:fundo_ortofoto' %}?atual={{ ortofoto_fundo }}"
     hx-trigger="every 60s, click from:[data-trocar]"
     hx-target="this" hx-swap="outerHTML swap:250ms">
  {% if ortofoto_fundo %}
  <div class="fundo-ortofoto__deriva">
    <div class="fundo-ortofoto__imagem"
         style="--fundo-ortofoto: url('{% static ortofoto_fundo %}')"></div>
  </div>
  {% endif %}
</div>
```

A contenção da deriva não depende do tamanho do PNG: o elemento é maior que a viewport por
`--deriva-margem` em cada lado, e nenhuma das duas animações translada mais que isso.

**`static/src/tema-dimap.dev.css`**
```css
:root {
  --deriva-margem: 200px;
  --deriva-periodo: 150s;
}

/* Crossfade da troca (v7), sem JS: classes que o próprio HTMX aplica e tira sozinho. */
.fundo-ortofoto {
  opacity: 1;
  transition: opacity 350ms ease-in;
}
.fundo-ortofoto.htmx-swapping {
  opacity: 0;
  transition: opacity 250ms ease-out;
}
.fundo-ortofoto.htmx-added {
  opacity: 0;
}

/* |translate| ≤ margem em cada eixo ⇒ a borda do elemento nunca entra na viewport, em qualquer
   proporção de tela. `cover` cuida da proporção do PNG, que por isso não entra na conta. */
.fundo-ortofoto__deriva {
  position: absolute;
  inset: calc(-1 * var(--deriva-margem));
  filter: brightness(1.1) contrast(0.75);
  animation-name: deriva-vertical;
  animation-duration: calc(var(--deriva-periodo) / 2);
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
  animation-direction: alternate;
}

/* Lissajous 1:2: o eixo horizontal oscila no dobro da frequência e na metade da amplitude, então a
   volta nunca repete o mesmo traço. `alternate` dobra a duração declarada — daí as durações serem
   metade do período pretendido. Longhand porque o shorthand com calc(var()) não parseia. */
.fundo-ortofoto__imagem {
  position: absolute;
  inset: 0;
  background-image: var(--fundo-ortofoto);
  background-size: cover;
  background-position: center;
  animation-name: deriva-horizontal;
  animation-duration: calc(var(--deriva-periodo) / 4);
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
  animation-direction: alternate;
}

@keyframes deriva-vertical {
  from { transform: translateY(calc(-1 * var(--deriva-margem))); }
  to   { transform: translateY(var(--deriva-margem)); }
}

@keyframes deriva-horizontal {
  from { transform: translateX(calc(var(--deriva-margem) / -2)); }
  to   { transform: translateX(calc(var(--deriva-margem) / 2)); }
}

@media (prefers-reduced-motion: reduce) {
  .fundo-ortofoto__deriva,
  .fundo-ortofoto__imagem { animation: none; }
}

/* Fundo desligado: não há imagem a trocar nem velocidade a ajustar. */
.fundo-controle:has(.toggle-onsen:not(:checked)) .fundo-controle__corpo {
  @apply opacity-35 pointer-events-none;
}
```

A preferência de quem olha é a única coisa que o cliente guarda, e é lida antes do primeiro quadro
para o fundo não piscar ligado antes de ser desligado.

**`static/src/js/ui/controle_fundo.js`**
```javascript
const PERIODOS = ["300s", "220s", "150s", "90s", "50s"];  // o centro é o padrão

function aplicarNivel(nivel) {
  document.documentElement.style.setProperty("--deriva-periodo", PERIODOS[nivel]);
  lembrar(CHAVE_NIVEL, nivel);
}
```

## 7 · Caveats

O liga/desliga e a velocidade da deriva ficam em `localStorage`, e não no servidor como manda o
§3.1 do CLAUDE.md. Nenhum dos dois é estado da aplicação — são preferências de quem está olhando,
que não valem para o mesmo servidor em outra máquina, e uma ida ao servidor a cada clique no `+`
pagaria uma requisição por um ajuste decorativo. O custo é que a preferência não acompanha o
usuário entre dispositivos e some quando ele limpa o navegador.

A ortofoto continua sendo do servidor enquanto a preferência é do cliente, então o fundo tem dois
donos. A imagem é sorteada e trocada por rota, porque é ela que o catálogo governa e que o disco
limita. O custo é que quem for depurar o fundo precisa olhar em dois lugares.

Com rodízio de um minuto, o navegador acaba baixando o catálogo inteiro — hoje ~16 MB, oito
ortofotos. É um teto conhecido e pago uma única vez por navegador, contra os ~9 MB por página que a
área administrativa gasta hoje. O custo cai na primeira meia hora de uso: o sorteio não segue ciclo
fixo, então ver as oito leva ~22 trocas, e cada estreia é um download.

Cada aba administrativa aberta faz uma requisição por minuto à rota do fundo. A resposta é um
partial de poucas linhas e o uso é interno, de dezenas de pessoas. O custo é tráfego perpétuo
enquanto houver aba aberta, inclusive esquecida.

Os PNGs ficam fora do git e a subida do web roda o comando, que só busca o que falta no disco.
Versioná-los custaria ~2 MB por ponto no histórico a cada regeneração, e a entrega não precisa
deles prontos para subir. O custo é que a idempotência depende do diretório sobreviver entre
entregas: em filesystem efêmero, toda subida rebusca o catálogo inteiro, e o web só atende depois
de o download terminar.

A geração sai com código zero quando o GeoSampa não conecta ou não responde no prazo. O fundo é
decorativo e o GeoSampa é serviço de terceiro, então a indisponibilidade dele não pode decidir se o
sistema sobe. O custo é que só uma linha de aviso no log do container diz que a área administrativa
subiu sem ortofoto, e quem encadear o comando pelo código de saída não percebe a falha.

Só conexão e timeout contam como GeoSampa fora do ar. Status de erro e ServiceException são tratados
como defeito a consertar, que aviso nenhum deveria esconder. O custo é que um GeoSampa respondendo
502 ou 503 derruba a subida do web, tal como disco sem permissão de escrita.

A sonda usa o timeout da conexão, o mesmo do GetMap inteiro. Um timeout próprio seria mais uma
variável de ambiente para um caso só. O custo é que, com o GeoSampa pendurado em vez de recusando,
a subida espera `WMS_REQUEST_TIMEOUT_SECONDS` antes de seguir.

Ninguém tenta de novo depois da subida. A geração roda uma vez por boot do container, porque
repetir em segundo plano pediria um agendador para um fundo decorativo. O custo é que um GeoSampa
fora do ar na subida deixa o fundo sem ortofoto até alguém rodar o comando ou reiniciar o web.

No compose de desenvolvimento os PNGs nascem pelo container do web, sobre o bind mount do código. O
web roda como root, porque é o usuário da imagem e a migração já roda assim. O custo é que a pasta
`static/src/img/ortofotos_fundo/` passa a pertencer a root na máquina de quem desenvolve.

`ortofotos_disponiveis()` é memoizado no processo. O disco só muda quando o comando roda, e ler
sete `exists()` a cada requisição do rodízio seria IO por nada. O custo é que gerar um ponto novo
com o servidor de pé não o coloca no sorteio até o processo reiniciar.

O catálogo passa a existir em dois lugares que podem divergir — as chaves do
`config/pontos_fundo.json` e os arquivos em `static/src/img/ortofotos_fundo/`. O comando só
acrescenta, nunca apaga, então remover um ponto do JSON deixa o PNG órfão no disco. A interseção do
`ortofotos_disponiveis()` cobre o lado que importa, mas ninguém limpa o órfão.

`.btn-etched-mini` nasce como variante em vez de o `.btn-etched` encolher. O átomo base está
implementado e é usado pelas telas de autenticação e pela lista de unidades, que o §3.4 protege de
alteração sem aval. O custo é mais uma classe onde um parâmetro de tamanho bastaria.

## 8 · Testes (TDD)
- `test_enquadramento_centra_no_ponto` — a bbox gerada tem o ponto no centro e largura igual a
  `largura_px × metros_por_pixel`, em 31983.
- `test_geracao_pula_ortofoto_existente` — com o arquivo já no disco, o buscador não é chamado.
- `test_geracao_forcada_rebusca` — com `forcar=True`, o ponto é regerado mesmo com arquivo no disco.
- `test_geosampa_fora_do_ar_nao_pede_ortofoto` — com a sonda levantando `WmsConnectionError`,
  nenhuma requisição no tamanho da ortofoto é feita, nada é gravado e o resultado traz todos os
  faltantes em `pendentes`, com a indisponibilidade.
- `test_queda_no_meio_preserva_as_geradas` — `WmsTimeoutError` no segundo ponto: o primeiro fica no
  disco e em `geradas`, os demais em `pendentes`.
- `test_erro_que_nao_e_indisponibilidade_propaga` — `WmsHttpError` na sonda sai do gerador como
  exceção, sem virar pendência.
- `test_download_e_anunciado_antes_de_comecar` — havendo ponto faltante, o anúncio do download chega
  a quem avisa antes da primeira requisição; com tudo no disco, nada é anunciado.
- `test_comando_com_geosampa_fora_do_ar_sai_zero_com_aviso` — com o gerador devolvendo pendentes, o
  comando não levanta e o stdout traz o aviso nomeando cada ponto pendente.
- `test_entrypoint_gera_ortofotos_antes_do_processo_final` — a subida chama `gerar_ortofotos_fundo`,
  e o comando saindo em erro impede o processo final de rodar.
- `test_ortofoto_gravada_em_tons_de_cinza` — o PNG salvo tem um único canal.
- `test_ponto_fora_do_municipio_e_recusado` — coordenada fora da faixa de São Paulo derruba a
  validação do catálogo.
- `test_catalogo_vazio_e_recusado` — catálogo sem nenhum ponto derruba a validação.
- `test_sorteio_nunca_devolve_a_atual` — com a atual entre as opções, ela nunca é o resultado.
- `test_sorteio_com_opcao_unica_devolve_ela` — quando excluir a atual esvazia a lista, o sorteio
  ainda devolve algo.
- `test_rota_do_fundo_devolve_ortofoto_diferente` — `GET` com `?atual=` devolve o partial com outra
  ortofoto disponível.
- `test_pagina_administrativa_sem_ortofoto_disponivel` — sem nenhum PNG, o login responde 200 e o
  HTML não traz o elemento de imagem. *(marker `banco`)*
