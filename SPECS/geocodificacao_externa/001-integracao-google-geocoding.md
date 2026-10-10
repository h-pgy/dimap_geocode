---
spec: geocodificacao_externa/001
versao: v2
atualizado_em: 2026-09-28
testes_tdd: true
implementado: true
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
  - v2: migra para a v4 do Geocoding, com a chave no header
---

# SPEC geocodificacao_externa/001 — Integração com o Google Geocoding

## 1 · User story
**Requisito não-funcional** — a plataforma passa a consultar o Google Geocoding v4 por um cliente cujo
token só viaja no header e nunca aparece em URL, mensagem, `repr` ou cadeia de exceção.

## 2 · Condições de pronto
- [ ] Um endereço consultado devolve os resultados do Google **como o Google os entrega**, tipados:
      coordenadas, `granularity`, endereço formatado e componentes do endereço.
- [ ] Endereço sem resultado devolve lista vazia, sem erro.
- [ ] Falha de rede, ou status HTTP de erro do Google (chave inválida, acesso negado, cota), levanta
      exceção da integração com o código HTTP na mensagem.
- [ ] Corpo fora do contrato (não é JSON, ou traz valor que o espelho não conhece) levanta exceção da
      integração, nunca `ValidationError` nem erro do `requests`.
- [ ] **O token viaja só no header** `X-Goog-Api-Key`: não aparece na URL, nem na mensagem, no `repr`
      ou na cadeia (`__cause__`/`__context__`) de nenhuma exceção da integração.
- [ ] Sem token no ambiente, a integração não monta cliente.
- [ ] Erro do `requests` que não é de rede nem de status (redirect em excesso, URL inválida) sai do
      utilitário HTTP como exceção própria, sem nova tentativa — para qualquer consumidor dele.

## 3 · Domínio
O domínio desta SPEC é o **protocolo do provedor** — o método `geocodeAddress` da v4 —, espelhado sem
tradução: os nomes são os do Google, em snake_case; o camelCase da API volta como alias na resposta e
como nome de parâmetro na requisição. Quem os traduz para o vocabulário da DIMAP é a SPEC
[002](002-geocodificador-externo-agnostico.md).

**`services/integrations/geocodificador_externo/base.py`** — o que todo cliente de provedor é.

```python
class ClienteGeocodificacao[Req: BaseModel, Resp: BaseModel](ABC):
    def __init__(self, token: SecretStr, fetcher: HttpFetcher) -> None:
        self.token = token        # cada provedor decide como o envia
        self._fetcher = fetcher

    @abstractmethod
    def __call__(self, requisicao: Req) -> Resp:
        """A resposta do provedor, tipada; toda falha sai como `ClienteGeocodificacaoError`."""
```

**`services/integrations/geocodificador_externo/google/models.py`** — o espelho da API.

```python
Granularity = Literal[
    "GRANULARITY_UNSPECIFIED",
    "ROOFTOP",
    "RANGE_INTERPOLATED",
    "GEOMETRIC_CENTER",
    "APPROXIMATE",
]


# o JSON da resposta é camelCase; no Python os campos seguem snake_case e aceitam os dois nomes
CAMEL_CASE = ConfigDict(alias_generator=to_camel, validate_by_name=True)


class PostalAddress(BaseModel):
    """O `PostalAddress` da requisição: só os campos que a DIMAP preenche."""

    address_lines: list[str] = Field(min_length=1)
    locality: str | None = None
    administrative_area: str | None = None
    region_code: str | None = None      # CLDR: "BR"


class GeocodeRequest(BaseModel):
    address: PostalAddress              # a forma estruturada do endereço
    language_code: str | None = None
    region_code: str | None = None      # ccTLD: "br"


class LatLng(BaseModel):
    model_config = CAMEL_CASE

    latitude: float
    longitude: float


class AddressComponent(BaseModel):
    model_config = CAMEL_CASE

    long_text: str
    short_text: str | None = None       # a API só o manda quando há abreviação
    types: list[str]


class GeocodeResult(BaseModel):
    model_config = CAMEL_CASE

    formatted_address: str
    location: LatLng
    granularity: Granularity = "GRANULARITY_UNSPECIFIED"  # o JSON omite o valor padrão do enum
    address_components: list[AddressComponent] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)


class GeocodeResponse(BaseModel):
    model_config = CAMEL_CASE

    results: list[GeocodeResult] = Field(default_factory=list)  # sem resultado, pode vir omitida
```

## 4 · Fora de escopo
- Tradução para o domínio (precisão normalizada, política, recorte do município) — SPEC 002.
- Outros provedores (Azure etc.) — sem dono ainda.
- Nova tentativa por cota esgotada (HTTP 429) — sem dono ainda.
- Endereço não estruturado (`addressQuery`) e `locationBias` na requisição — sem dono ainda.
- Máscara de campos (`X-Goog-FieldMask`) — sem dono ainda.
- OAuth no lugar da chave — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/http` → `HttpFetcher`, `HttpRetryPolicy`, `HttpFetchError`: GET com retry e erro
  próprio. O `HttpFetcher` passa a traduzir todo `RequestException` (§6).
- `@services/integrations/itbi` → molde de integração sobre o `HttpFetcher`: `models.py`, `exceptions.py`,
  `build_fetcher`, `__init__.py` que só reexporta.
- `@services/utils/smtp/config.py` → `SmtpSettingsLike`: o `Protocol` que o builder recebe no lugar do settings.
- `@config/settings.py` → `ASSINATURA_SEGREDO`: segredo lido do `.env` e exposto como `SecretStr`.
- Skills: `escrever-testes`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/utils/http/fetcher.py`** — `_tentar` da SPEC
[ingestao_dados/008](../ingestao_dados/008-scraper-itbi.md) inteiro: nenhum erro do `requests` escapa
do utilitário.

```python
    def _tentar(self, url: str, tentativa: int, **kwargs: Any) -> Response | None:
        try:
            resposta = self._session.get(url, **kwargs)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            self._esperar_ou_desistir(url, repr(exc), tentativa)
            return None
        except requests.exceptions.RequestException as exc:  # ALTERADO nesta SPEC
            # redirect em excesso, URL inválida: definitivo, repetir não ajuda
            raise HttpFetchError(f"{url}: {repr(exc)}") from exc

        if resposta.status_code in self._policy.status_para_retry:
            self._esperar_ou_desistir(url, f"HTTP {resposta.status_code}", tentativa)
            return None

        try:
            resposta.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise HttpStatusError(f"{url}: HTTP {resposta.status_code}") from exc
        return resposta
```

**`services/integrations/geocodificador_externo/google/models.py`** — o que é fato do protocolo do
Google, e não configuração.

```python
URL_GEOCODING = "https://geocode.googleapis.com/v4/geocode/address"
CABECALHO_CHAVE = "X-Goog-Api-Key"
CRS: int = 4326  # a API responde sempre em WGS84

# chamada síncrona dentro da busca: timeout curto e uma única repetição
RETRY = HttpRetryPolicy(
    request_timeout_seconds=10.0,
    max_retries=1,
    status_para_retry=(500, 502, 503, 504),
)


class GeocodeRequest(BaseModel):
    ...  # campos no §3

    def to_query_params(self) -> dict[str, str | list[str]]:
        # o token NÃO entra aqui: vai no header, e a requisição pode ser logada ou representada sem risco
        # cada chave é o nome do parâmetro na documentação da v4; o PostalAddress vai achatado em
        # "address.<campo>", que é como a API recebe um objeto numa query string
        todos: dict[str, str | list[str] | None] = {
            "address.addressLines": self.address.address_lines,  # lista: o parâmetro se repete por linha
            "address.locality": self.address.locality,
            "address.administrativeArea": self.address.administrative_area,
            "address.regionCode": self.address.region_code,
            "languageCode": self.language_code,
            "regionCode": self.region_code,
        }
        # campo não preenchido não vai à query: parâmetro vazio é diferente de parâmetro ausente
        return {nome: valor for nome, valor in todos.items() if valor is not None}
```

Com a política padrão da SPEC 002, `rua augusta, 100` vira:

```python
GeocodeRequest(
    address=PostalAddress(
        address_lines=["rua augusta, 100"],
        locality="São Paulo",
        administrative_area="SP",
        region_code="BR",
    ),
    language_code="pt-BR",
    region_code="br",
).to_query_params()
# {
#     "address.addressLines": ["rua augusta, 100"],
#     "address.locality": "São Paulo",
#     "address.administrativeArea": "SP",
#     "address.regionCode": "BR",
#     "languageCode": "pt-BR",
#     "regionCode": "br",
# }
#
# e o requests monta a URL (sem a chave, que vai no header):
# https://geocode.googleapis.com/v4/geocode/address?address.addressLines=rua+augusta%2C+100
#     &address.locality=S%C3%A3o+Paulo&address.administrativeArea=SP&address.regionCode=BR
#     &languageCode=pt-BR&regionCode=br
```

**`services/integrations/geocodificador_externo/exceptions.py`** — o contrato de falha do
`ClienteGeocodificacao`, comum a todos os provedores.

```python
class ClienteGeocodificacaoError(Exception):
    """Raiz: para fora de um cliente de provedor não sai exceção do requests nem do utilitário HTTP."""


class TransporteError(ClienteGeocodificacaoError):
    """Rede ou HTTP falharam — status de erro do provedor incluído — depois de esgotada a política de retry."""


class RespostaInvalidaError(ClienteGeocodificacaoError):
    """O corpo não é o contrato espelhado nos models do provedor."""
```

**`services/integrations/geocodificador_externo/google/client.py`** — levanta as exceções do pacote
pai.

```python
class Cliente(ClienteGeocodificacao[GeocodeRequest, GeocodeResponse]):
    def __call__(self, requisicao: GeocodeRequest) -> GeocodeResponse:
        return self.pipeline(requisicao)

    def pipeline(self, requisicao: GeocodeRequest) -> GeocodeResponse:
        http = self._buscar(requisicao)
        return self._validar(http)

    def _buscar(self, requisicao: GeocodeRequest) -> Response:
        # é aqui, e só aqui, que a chave é aberta — e ela vai no header, nunca na URL
        cabecalho = {CABECALHO_CHAVE: self.token.get_secret_value()}
        try:
            return self._fetcher(
                URL_GEOCODING,
                params=requisicao.to_query_params(),
                headers=cabecalho,
            )
        except HttpFetchError as exc:
            # a mensagem do utilitário traz a URL e o código HTTP: nenhum dos dois carrega a chave
            raise TransporteError(str(exc)) from exc

    def _validar(self, http: Response) -> GeocodeResponse:
        try:
            return GeocodeResponse.model_validate_json(http.content)
        except ValidationError as exc:
            raise RespostaInvalidaError(str(exc)) from exc
```

**`services/integrations/geocodificador_externo/google/utils.py`** — sem token não há cliente.

```python
class SettingsLike(Protocol):
    GOOGLE_GEOCODING_TOKEN: SecretStr


def build_cliente(source: SettingsLike) -> Cliente | None:
    if not source.GOOGLE_GEOCODING_TOKEN.get_secret_value():
        return None
    return Cliente(
        token=source.GOOGLE_GEOCODING_TOKEN,
        fetcher=HttpFetcher(RETRY),
    )
```

**`services/integrations/geocodificador_externo/__init__.py`** — o que é comum sai solto; cada
provedor sai como namespace: quem consome escreve `google.Cliente`, `google.GeocodeResult`.

```python
# os nomes dentro de cada provedor se repetiriam entre provedores: reexportá-los soltos colidiria
from . import google
from .base import ClienteGeocodificacao
from .exceptions import ClienteGeocodificacaoError, RespostaInvalidaError, TransporteError

__all__ = [
    "ClienteGeocodificacao",
    "ClienteGeocodificacaoError",
    "TransporteError",
    "RespostaInvalidaError",
    "google",
]
```

**`services/integrations/geocodificador_externo/google/__init__.py`**

```python
from .client import Cliente
from .models import CRS, GeocodeRequest, GeocodeResponse, GeocodeResult, Granularity, PostalAddress
from .utils import SettingsLike, build_cliente

__all__ = [...]
```

**`config/settings.py`** — o `.env.example` ganha `GOOGLE_GEOCODING_TOKEN=` vazio, comentado como
segredo.

```python
    google_geocoding_token: str = Field(default="", alias="GOOGLE_GEOCODING_TOKEN")
```

```python
# SecretStr para o token não vazar em log nem traceback; vazio desliga a geocodificação externa.
GOOGLE_GEOCODING_TOKEN = SecretStr(_env.google_geocoding_token)
```

## 7 · Caveats
A ABC só garante que o token é um `SecretStr`, e onde ele viaja é decisão de cada provedor. Cada API
recebe a chave de um jeito (header, query string, OAuth), e a ABC não tem como impor o header. O custo
é que o teste de não-vazamento cobre só o Google.

O `HttpFetcher`, entregue pela ingestao_dados/008, passa a traduzir todo `RequestException` em
`HttpFetchError`. A 008 já proibia `requests` de escapar do utilitário, e redirect em excesso ou URL
inválida escapavam, na ITBI inclusive. O custo é mexer num utilitário já entregue, e a 008 ganha uma
linha `[bugfix]` no `changelog` quando esta SPEC for implementada.

Status HTTP de erro vira `TransporteError` com o código, sem ler o corpo de erro do Google. O
`HttpFetcher` não devolve a resposta de erro, e o domínio trata toda falha como provedor indisponível.
O custo é que, num `400`, o log não distingue chave inválida de requisição malformada.

`granularity` é `Literal` fechado no espelho. Valor novo do Google é mudança de contrato e deve
aparecer como erro, não passar calado até o domínio. O custo é a geocodificação externa ficar
indisponível até o espelho ser atualizado.

O teste de integração consulta a API real. É o único que prova o espelho contra a resposta de verdade,
inclusive o corpo sem resultado, que a documentação da v4 não mostra. O custo é exigir
`GOOGLE_GEOCODING_TOKEN` no ambiente de quem roda o gate e consumir duas requisições da cota a cada
execução.

## 8 · Testes (TDD)
- `test_http_fetcher_traduz_erro_do_requests_sem_repetir` — em `tests/services/utils/http/`: uma
  `Session` dublê que levanta `TooManyRedirects` é chamada uma vez só e resulta em `HttpFetchError`.
- `test_cliente_envia_endereco_estruturado_e_o_token_so_no_header` — a `Session` dublê recebe a URL da
  v4, `address.addressLines`, `address.locality`, `address.administrativeArea`, `address.regionCode`,
  `languageCode` e `regionCode`, e o header `X-Goog-Api-Key` igual ao token; a chave não está na URL
  nem nos parâmetros.
- `test_resposta_vira_espelho_tipado` — fixture JSON no formato real da v4 vira `GeocodeResponse`
  com coordenadas, `granularity` e componentes com `longText`/`shortText`.
- `test_resposta_sem_resultados_devolve_lista_vazia` — `{}` e `{"results": []}` devolvem resposta sem
  resultados e sem exceção.
- `test_falha_de_transporte_levanta_erro_da_integracao` — parametrizado: rede esgotada e HTTP 403
  levantam `TransporteError`, e o do HTTP traz `403` na mensagem.
- `test_corpo_fora_do_contrato_levanta_resposta_invalida` — HTML no lugar de JSON e `granularity`
  desconhecida levantam `RespostaInvalidaError`.
- `test_nenhuma_excecao_da_integracao_vaza_o_token` — parametrizado sobre falha de rede, HTTP
  definitivo, redirect em excesso e corpo inválido: o token não está em `str` nem `repr` de nenhuma
  exceção da cadeia (`__cause__`/`__context__`).
- `test_build_sem_token_nao_monta_cliente` — `GOOGLE_GEOCODING_TOKEN` vazio devolve `None`.
- `test_geocoding_real_do_google` — endereço conhecido de São Paulo devolve ao menos um resultado que o
  espelho aceita, e um endereço inexistente devolve lista vazia sem exceção *(marker `integration`)*.
