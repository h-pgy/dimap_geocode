---
spec: geocodificacao_externa/002
versao: v2
atualizado_em: 2026-09-28
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
  - v2: provedor Google traduz a v4 do Geocoding e o endereço externo perde `parcial`
---

# SPEC geocodificacao_externa/002 — Geocodificador externo agnóstico de provedor

## 1 · User story
**Requisito não-funcional** — o resultado de qualquer provedor externo chega ao sistema num contrato
único da DIMAP, com as mesmas regras de aceite, e trocar de provedor é implementar a porta, inscrevê-la
na factory e mudar uma variável de ambiente.

## 2 · Condições de pronto
- [ ] Um resultado do Google chega ao sistema como **endereço externo**: provedor, precisão normalizada,
      endereço formatado e componentes (logradouro, número, bairro, município, UF, CEP). Nenhum
      consumidor vê o formato do Google.
- [ ] Resultado com precisão **abaixo da mínima** da política é descartado; por padrão só entram
      *imóvel* e *interpolada*.
- [ ] Resultado **fora do município e da UF** da política é descartado, mesmo que o provedor o
      devolva; resultado sem município declarado também.
- [ ] Entre os aceitos, entrega-se o de **maior precisão**; no empate, o que o provedor pôs primeiro.
- [ ] Nenhum resultado aceito levanta erro próprio; falha do provedor (rede, cota, acesso negado,
      resposta fora do contrato) levanta erro próprio **agnóstico**, sem o tipo do Google.
- [ ] Idioma, país, UF, município e precisão mínima vêm do ambiente quando definidos, e valem o padrão
      quando não.
- [ ] O provedor em uso é escolhido pelo ambiente (Google por padrão); nome desconhecido é recusado
      com a lista dos que existem.
- [ ] Um provedor qualquer que implemente a porta passa pelas **mesmas** regras de aceite.

## 3 · Domínio
O Google chega pelo espelho da SPEC [001](001-integracao-google-geocoding.md#3--domínio); a pergunta
que esta SPEC faz a ele é "o que você encontrou, onde e com que certeza?". O ponto é o
[PointGeometry](../geocodificacao/003-address-geocod-ponto.md) envelopado em `GeoFeature`, como o
endereço interpolado.

**`services/domain/geocodificador_externo/models.py`**

```python
class Provedor(StrEnum):
    GOOGLE = "google"


class Precisao(StrEnum):
    # declarados do menos ao mais preciso: a ordem de declaração é o nível
    APROXIMADA = "aproximada"    # uma região: bairro, CEP, município
    LOGRADOURO = "logradouro"    # o centro da via, sem o número
    INTERPOLADA = "interpolada"  # o número estimado entre dois pontos conhecidos da via
    IMOVEL = "imovel"            # o próprio imóvel

    @property
    def nivel(self) -> int:
        return list(Precisao).index(self)


class EnderecoExternoAttributes(BaseModel):
    """O endereço como um provedor externo o encontrou."""

    endereco_formatado: str
    logradouro: str | None = None
    numero: str | None = None      # como o provedor escreve: "100", "100-A"
    bairro: str | None = None
    municipio: str | None = None
    uf: str | None = None
    cep: str | None = None
    provedor: Provedor
    precisao: Precisao


EnderecoExternoFeature = GeoFeature[PointGeometry, EnderecoExternoAttributes]


class PoliticaGeocodificacao(BaseModel):
    """O recorte de toda consulta externa: cada provedor o traduz na sua requisição."""

    model_config = ConfigDict(frozen=True)

    idioma: str = "pt-BR"
    pais: str = "BR"
    uf: str = "SP"
    municipio: str = "São Paulo"
    precisao_minima: Precisao = Precisao.INTERPOLADA


class ConsultaGeocodificacao(BaseModel):
    texto: str = Field(min_length=1)  # o endereço como a pessoa digitou
```

**`services/domain/geocodificador_externo/porta.py`** — a interface que todo provedor implementa.

```python
class ProvedorGeocodificacao(ABC):
    provedor: ClassVar[Provedor]

    def __init__(self, politica: PoliticaGeocodificacao) -> None:
        self.politica = politica

    @abstractmethod
    def __call__(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        """Os resultados na ordem do provedor, no CRS do provedor (declarado em cada feature)."""
```

## 4 · Fora de escopo
- Provedor Azure (ou qualquer segundo provedor) — sem dono ainda.
- Oferecer mais de um resultado para a pessoa escolher — sem dono ainda.
- Conferir o município pela geometria, em vez do nome — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/integrations/geocodificador_externo` → `google.Cliente`, `google.build_cliente`, o espelho e `ClienteGeocodificacaoError` (SPEC 001).
- `@services/domain/geometry` → `GeoFeature`, `PointGeometry`, `reprojetar`: o envelope e a reprojeção centralizada.
- `@services/utils/normalization` → `normalize_text`: comparação do município e da UF.
- `@services/domain/documento_oficial/config.py` → `_definidos`: só o que o ambiente definiu sobrepõe
  o default do model. Promovido a `services/utils/ambiente/`, e o `documento_oficial` passa a importá-lo de lá.
- Skills: `ontologia`, `normalize-text`, `escrever-testes`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/geocodificador_externo/exceptions.py`**

```python
class ProvedorIndisponivelError(Exception):
    """O provedor não respondeu dentro do contrato: rede, cota, acesso negado ou corpo inesperado."""


class SemResultadoAceitoError(Exception):
    """O provedor respondeu, mas nenhum resultado cabe na política."""


class ProvedorDesconhecidoError(Exception):
    """O ambiente nomeia um provedor que não está inscrito na factory."""
```

**`services/domain/geocodificador_externo/geocodificador.py`** — as regras de aceite moram aqui, uma
vez, e valem para qualquer provedor.

```python
class GeocodificacaoExternaInput(BaseModel):
    consulta: ConsultaGeocodificacao
    output_crs: int  # CRS do mapa, vindo da orquestração


class GeocodificadorExterno:
    def __init__(self, provedor: ProvedorGeocodificacao) -> None:
        self._provedor = provedor

    @property
    def provedor(self) -> Provedor:
        return self._provedor.provedor

    def __call__(self, entrada: GeocodificacaoExternaInput) -> EnderecoExternoFeature:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GeocodificacaoExternaInput) -> EnderecoExternoFeature:
        candidatos = self._provedor(entrada.consulta)
        aceitos = [c for c in candidatos if self._no_recorte(c) and self._precisao_suficiente(c)]
        if not aceitos:
            raise SemResultadoAceitoError(entrada.consulta.texto)
        # max devolve o primeiro entre os empatados: a ordem do provedor desempata
        escolhido = max(aceitos, key=lambda c: c.attributes.precisao.nivel)
        return self._no_crs(escolhido, entrada.output_crs)

    def _no_recorte(self, candidato: EnderecoExternoFeature) -> bool:
        # o filtro de município do provedor pode ser só um viés: confere-se aqui, pelo texto normalizado
        politica = self._provedor.politica
        a = candidato.attributes
        if a.municipio is None or a.uf is None:
            return False
        return (
            normalize_text(a.municipio) == normalize_text(politica.municipio)
            and normalize_text(a.uf) == normalize_text(politica.uf)
        )

    def _precisao_suficiente(self, candidato: EnderecoExternoFeature) -> bool:
        return candidato.attributes.precisao.nivel >= self._provedor.politica.precisao_minima.nivel

    def _no_crs(self, escolhido: EnderecoExternoFeature, output_crs: int) -> EnderecoExternoFeature:
        if escolhido.crs == output_crs:
            return escolhido
        ponto = reprojetar(escolhido.geometry, escolhido.crs, output_crs)
        return escolhido.model_copy(update={"geometry": ponto, "crs": output_crs})
```

**`services/domain/geocodificador_externo/provedores/google.py`** — a tradução nos dois sentidos:
política → requisição do Google, resposta do Google → endereço externo.

```python
# o erro é comum a todos os provedores; o Google entra como namespace
from services.integrations.geocodificador_externo import ClienteGeocodificacaoError, google

PRECISAO_POR_GRANULARITY: dict[google.Granularity, Precisao] = {
    "ROOFTOP": Precisao.IMOVEL,
    "RANGE_INTERPOLATED": Precisao.INTERPOLADA,
    "GEOMETRIC_CENTER": Precisao.LOGRADOURO,
    "APPROXIMATE": Precisao.APROXIMADA,
    "GRANULARITY_UNSPECIFIED": Precisao.APROXIMADA,  # sem granularidade declarada, a menor certeza
}

# tipos de componente do Google por atributo; vence o primeiro tipo presente no resultado
TIPOS_LOGRADOURO = ("route",)
TIPOS_NUMERO = ("street_number",)
TIPOS_BAIRRO = ("sublocality_level_1", "sublocality", "neighborhood")
TIPOS_MUNICIPIO = ("administrative_area_level_2", "locality")
TIPOS_UF = ("administrative_area_level_1",)
TIPOS_CEP = ("postal_code",)

ClienteLike = Callable[[google.GeocodeRequest], google.GeocodeResponse]


class ProvedorGoogle(ProvedorGeocodificacao):
    provedor = Provedor.GOOGLE

    def __init__(self, politica: PoliticaGeocodificacao, cliente: ClienteLike) -> None:
        super().__init__(politica)
        self._cliente = cliente

    def __call__(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        return self.pipeline(consulta)

    def pipeline(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        requisicao = self._montar_requisicao(consulta)
        resposta = self._consultar(requisicao)
        return [self._resultado_para_endereco(r) for r in resposta.results]

    def _montar_requisicao(self, consulta: ConsultaGeocodificacao) -> google.GeocodeRequest:
        # a v4 não filtra por componente: o recorte da política vai no endereço estruturado
        p = self.politica
        return google.GeocodeRequest(
            address=google.PostalAddress(
                address_lines=[consulta.texto],
                locality=p.municipio,
                administrative_area=p.uf,
                region_code=p.pais,
            ),
            language_code=p.idioma,
            region_code=p.pais.lower(),  # ccTLD
        )

    def _consultar(self, requisicao: google.GeocodeRequest) -> google.GeocodeResponse:
        try:
            return self._cliente(requisicao)
        except ClienteGeocodificacaoError as exc:
            raise ProvedorIndisponivelError(str(exc)) from exc

    def _resultado_para_endereco(self, r: google.GeocodeResult) -> EnderecoExternoFeature:
        return EnderecoExternoFeature(
            geometry=PointGeometry(
                type="Point",
                coordinates=[r.location.longitude, r.location.latitude],
            ),
            attributes=EnderecoExternoAttributes(
                endereco_formatado=r.formatted_address,
                logradouro=self._componente(r, TIPOS_LOGRADOURO),
                numero=self._componente(r, TIPOS_NUMERO),
                bairro=self._componente(r, TIPOS_BAIRRO),
                municipio=self._componente(r, TIPOS_MUNICIPIO),
                uf=self._componente(r, TIPOS_UF, curto=True),  # "SP", não "São Paulo"
                cep=self._componente(r, TIPOS_CEP),
                provedor=self.provedor,
                precisao=PRECISAO_POR_GRANULARITY[r.granularity],
            ),
            crs=google.CRS,
        )

    def _componente(
        self,
        r: google.GeocodeResult,
        tipos: tuple[str, ...],
        curto: bool = False,
    ) -> str | None:
        for tipo in tipos:
            for componente in r.address_components:
                if tipo in componente.types:
                    return componente.short_text if curto else componente.long_text
        return None
```

**`services/utils/ambiente/definidos.py`** — `_definidos` do `documento_oficial`, promovido sem mudar.

```python
def definidos[M: BaseModel](modelo: type[M], valores: Mapping[str, object]) -> M:
    # só o que o ambiente DEFINIU é repassado: campo ausente deixa o default do model valer
    return modelo(**{chave: valor for chave, valor in valores.items() if valor is not None})
```

**`services/domain/geocodificador_externo/factory.py`** — o ambiente escolhe o provedor; provedor novo
é uma entrada a mais em `CONSTRUTORES`.

```python
PROVEDOR_PADRAO = Provedor.GOOGLE


class GeocodificacaoSettingsLike(google.SettingsLike, Protocol):
    GEOCODIFICACAO_EXTERNA_PROVEDOR: str | None
    GEOCODIFICACAO_EXTERNA_IDIOMA: str | None
    GEOCODIFICACAO_EXTERNA_PAIS: str | None
    GEOCODIFICACAO_EXTERNA_UF: str | None
    GEOCODIFICACAO_EXTERNA_MUNICIPIO: str | None
    GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA: str | None


def build_politica(source: GeocodificacaoSettingsLike) -> PoliticaGeocodificacao:
    return definidos(
        PoliticaGeocodificacao,
        {
            "idioma": source.GEOCODIFICACAO_EXTERNA_IDIOMA,
            "pais": source.GEOCODIFICACAO_EXTERNA_PAIS,
            "uf": source.GEOCODIFICACAO_EXTERNA_UF,
            "municipio": source.GEOCODIFICACAO_EXTERNA_MUNICIPIO,
            "precisao_minima": source.GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA,
        },
    )


def _provedor_google(
    source: GeocodificacaoSettingsLike,
    politica: PoliticaGeocodificacao,
) -> ProvedorGeocodificacao | None:
    cliente = google.build_cliente(source)
    return None if cliente is None else ProvedorGoogle(politica, cliente)


# cada construtor devolve None quando o provedor dele não está configurado (sem token)
CONSTRUTORES: dict[Provedor, Callable[[GeocodificacaoSettingsLike, PoliticaGeocodificacao], ProvedorGeocodificacao | None]] = {
    Provedor.GOOGLE: _provedor_google,
}


def escolher_provedor(source: GeocodificacaoSettingsLike) -> Provedor:
    nome = source.GEOCODIFICACAO_EXTERNA_PROVEDOR
    if nome is None:
        return PROVEDOR_PADRAO
    try:
        return Provedor(nome)
    except ValueError:
        conhecidos = ", ".join(p.value for p in Provedor)
        raise ProvedorDesconhecidoError(f"{nome!r} não é um provedor; use um de: {conhecidos}") from None


def build_geocodificador_externo(source: GeocodificacaoSettingsLike) -> GeocodificadorExterno | None:
    # None = provedor escolhido sem configuração; quem consome decide o que oferecer sem ele
    construir = CONSTRUTORES[escolher_provedor(source)]
    provedor = construir(source, build_politica(source))
    return None if provedor is None else GeocodificadorExterno(provedor)
```

**`config/settings.py`** — todos opcionais: o padrão mora na `PoliticaGeocodificacao` e no
`PROVEDOR_PADRAO`.

```python
    geocodificacao_externa_provedor: str | None = Field(
        default=None, alias="GEOCODIFICACAO_EXTERNA_PROVEDOR"
    )
    geocodificacao_externa_idioma: str | None = Field(default=None, alias="GEOCODIFICACAO_EXTERNA_IDIOMA")
    geocodificacao_externa_pais: str | None = Field(default=None, alias="GEOCODIFICACAO_EXTERNA_PAIS")
    geocodificacao_externa_uf: str | None = Field(default=None, alias="GEOCODIFICACAO_EXTERNA_UF")
    geocodificacao_externa_municipio: str | None = Field(
        default=None, alias="GEOCODIFICACAO_EXTERNA_MUNICIPIO"
    )
    geocodificacao_externa_precisao_minima: str | None = Field(
        default=None, alias="GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA"
    )
```

## 7 · Caveats
O município e a UF do resultado são conferidos no domínio, pelo texto normalizado. A v4 do Google não
filtra por componente (o endereço estruturado e o `regionCode` só enviesam a busca), e o projeto não
tem o polígono do município para conferir pela geometria. O custo é que um provedor que
grafe o município de outro jeito tem resultado bom descartado, e que resultados fora do recorte gastam
cota antes de serem descartados.

`GEOMETRIC_CENTER` vira `LOGRADOURO`, embora o Google o use para o centro de qualquer feição, via ou
área. A escala normalizada tem quatro níveis e o centro geométrico fica abaixo da precisão mínima
padrão. O custo é que, se alguém baixar a mínima para `logradouro` no ambiente, o centro de um bairro
pode ser aceito como centro de via.

O nome do provedor no ambiente é validado quando a factory roda, não quando o settings carrega. O
settings não importa o domínio, e é o domínio que sabe quais provedores existem. O custo é que um
nome errado no `.env` só aparece na primeira geocodificação externa, e não na subida do processo.

`_definidos` sai do `documento_oficial` para `services/utils/ambiente/`, e o `documento_oficial` passa
a importá-lo de lá. A mesma regra ("só o definido sobrepõe o default") ganharia uma segunda cópia na
política. O custo é mexer num módulo já entregue, sem mudança de comportamento.

## 8 · Testes (TDD)
- `test_parser_google_mapeia_granularity_para_precisao` — parametrizado: `ROOFTOP` → imóvel,
  `RANGE_INTERPOLATED` → interpolada, `GEOMETRIC_CENTER` → logradouro, `APPROXIMATE` e
  `GRANULARITY_UNSPECIFIED` → aproximada.
- `test_parser_google_extrai_componentes_e_declara_o_crs_do_provedor` — um resultado com `route`,
  `street_number`, `sublocality_level_1`, `administrative_area_level_2`, `administrative_area_level_1`
  e `postal_code` vira endereço externo com UF curta (`SP`) e `crs` 4326.
- `test_provedor_google_traduz_a_politica_na_requisicao` — o cliente dublê recebe o texto em
  `address_lines` e o município, a UF e o país da política no endereço estruturado, com
  `language_code` e `region_code`.
- `test_falha_do_cliente_google_vira_provedor_indisponivel` — `TransporteError` do cliente dublê
  sai como `ProvedorIndisponivelError`.
- `test_geocodificador_descarta_resultado_fora_da_politica` — com um provedor dublê que implementa a
  porta, parametrizado: precisão *logradouro*, município de outra cidade, UF de outro estado e
  município ausente caem; *interpolada* em `Sao Paulo` sem acento fica.
- `test_geocodificador_escolhe_a_maior_precisao_e_desempata_pela_ordem` — de *interpolada*, *imóvel*,
  *imóvel*, vence o primeiro *imóvel*.
- `test_sem_resultado_aceito_levanta_erro_proprio` — lista vazia ou só descartados levantam
  `SemResultadoAceitoError`.
- `test_geocodificador_entrega_no_crs_pedido` — resultado em 4326 pedido em 31983 sai reprojetado, com
  `crs` 31983.
- `test_politica_do_ambiente_so_sobrepoe_o_definido` — settings dublê só com
  `GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA="imovel"` produz política com essa mínima e os demais
  campos no padrão.
- `test_factory_escolhe_o_provedor_pelo_ambiente` — sem `GEOCODIFICACAO_EXTERNA_PROVEDOR` monta o
  Google; `"google"` também; `"azure"` levanta `ProvedorDesconhecidoError` listando `google`.
