---
spec: geocodificacao_externa/001
versao: v1
atualizado_em: 2026-09-27
testes_tdd: false
implementado: false
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
---

# SPEC geocodificacao_externa/001 — Integração com o Google Geocoding

## 1 · User story
**Requisito não-funcional** — a plataforma passa a consultar o Google Geocoding por um cliente cujo
token nunca aparece em mensagem, `repr` ou cadeia de exceção.

## 2 · Condições de pronto
- [ ] Um endereço consultado devolve os resultados do Google **como o Google os entrega**, tipados:
      coordenadas, `location_type`, componentes do endereço e `partial_match`.
- [ ] `ZERO_RESULTS` devolve lista vazia, sem erro.
- [ ] Os status de erro que o Google responde com HTTP 200 (`REQUEST_DENIED`, `OVER_QUERY_LIMIT`…)
      levantam exceção da integração que carrega o status.
- [ ] Corpo fora do contrato (não é JSON, ou traz valor que o espelho não conhece) levanta exceção da
      integração, nunca `ValidationError` nem erro do `requests`.
- [ ] **O token não aparece** na mensagem, no `repr` nem na cadeia (`__cause__`/`__context__`) de
      nenhuma exceção da integração — em falha de rede, de HTTP, de status ou de corpo.
- [ ] Sem token no ambiente, a integração não monta cliente.
- [ ] Erro do `requests` que não é de rede nem de status (redirect em excesso, URL inválida) sai do
      utilitário HTTP como exceção própria, sem nova tentativa — para qualquer consumidor dele.

## 3 · Domínio
O domínio desta SPEC é o **protocolo do provedor**, espelhado sem tradução: os nomes são os do
Google, e quem os traduz para o vocabulário da DIMAP é a SPEC
[002](002-geocodificador-externo-agnostico.md).

**`services/utils/segredo/token.py`** — o token de API como tipo: só se abre por `revelar()`.

```python
MASCARA = "***"


class Token(BaseModel):
    model_config = ConfigDict(frozen=True)

    valor: SecretStr  # mascarado em repr, str e traceback

    @field_validator("valor")
    @classmethod
    def _nao_vazio(cls, valor: SecretStr) -> SecretStr:
        if not valor.get_secret_value():
            raise ValueError("token vazio")
        return valor
```

**`services/integrations/geocodificador_externo/base.py`** — o que todo cliente de provedor é.

```python
class ClienteGeocodificacao[Req: BaseModel, Resp: BaseModel](ABC):
    def __init__(self, token: Token, fetcher: HttpFetcher) -> None:
        self.token = token        # cada provedor decide como o envia
        self._fetcher = fetcher

    @abstractmethod
    def __call__(self, requisicao: Req) -> Resp: ...
```

**`services/integrations/geocodificador_externo/google/models.py`** — o espelho da API.

```python
StatusGoogle = Literal[
    "OK",
    "ZERO_RESULTS",
    "OVER_DAILY_LIMIT",
    "OVER_QUERY_LIMIT",
    "REQUEST_DENIED",
    "INVALID_REQUEST",
    "UNKNOWN_ERROR",
]
LocationTypeGoogle = Literal["ROOFTOP", "RANGE_INTERPOLATED", "GEOMETRIC_CENTER", "APPROXIMATE"]


class GoogleGeocodeRequest(BaseModel):
    address: str = Field(min_length=1)
    components: dict[str, str] = Field(default_factory=dict)  # {"country": "BR", ...}
    language: str | None = None
    region: str | None = None


class GoogleLatLng(BaseModel):
    lat: float
    lng: float


class GoogleGeometry(BaseModel):
    location: GoogleLatLng
    location_type: LocationTypeGoogle


class GoogleAddressComponent(BaseModel):
    long_name: str
    short_name: str
    types: list[str]


class GoogleGeocodeResult(BaseModel):
    formatted_address: str
    geometry: GoogleGeometry
    address_components: list[GoogleAddressComponent]
    types: list[str]
    place_id: str
    partial_match: bool = False


class GoogleGeocodeResponse(BaseModel):
    status: StatusGoogle
    results: list[GoogleGeocodeResult] = Field(default_factory=list)
    error_message: str | None = None
```

## 4 · Fora de escopo
- Tradução para o domínio (precisão normalizada, política, recorte do município) — SPEC 002.
- Outros provedores (Azure etc.) — sem dono ainda.
- Nova tentativa por status do corpo (`OVER_QUERY_LIMIT`, `UNKNOWN_ERROR`) — sem dono ainda.
- `bounds` e `extra_computations` na requisição — sem dono ainda.

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

**`services/utils/segredo/token.py`** — a sanitização reutilizável: qualquer texto sai sem o valor,
cru ou codificado para URL.

```python
class Token(BaseModel):
    ...

    def revelar(self) -> str:
        # o único ponto do sistema que abre o segredo
        return self.valor.get_secret_value()

    def sanitizar(self, texto: str) -> str:
        # a URL do requests leva o valor codificado; a mensagem do provedor, o valor cru
        cru = self.revelar()
        for forma in (cru, quote(cru, safe="")):
            texto = texto.replace(forma, MASCARA)
        return texto
```

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
            raise HttpFetchError(f"{url}: {exc!r}") from exc

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
URL_GEOCODING = "https://maps.googleapis.com/maps/api/geocode/json"
CRS_GOOGLE: int = 4326  # a API responde sempre em WGS84
STATUS_SEM_ERRO: tuple[StatusGoogle, ...] = ("OK", "ZERO_RESULTS")

# chamada síncrona dentro da busca: timeout curto e uma única repetição
RETRY_GOOGLE = HttpRetryPolicy(
    request_timeout_seconds=10.0,
    max_retries=1,
    status_para_retry=(500, 502, 503, 504),
)


class GoogleGeocodeRequest(BaseModel):
    ...

    def to_query_params(self) -> dict[str, str]:
        # o token NÃO entra aqui: a requisição pode ser logada ou representada sem risco
        params = {"address": self.address}
        if self.components:
            params["components"] = "|".join(f"{k}:{v}" for k, v in self.components.items())
        if self.language:
            params["language"] = self.language
        if self.region:
            params["region"] = self.region
        return params
```

**`services/integrations/geocodificador_externo/google/exceptions.py`**

```python
class GoogleGeocodingError(Exception):
    """Raiz: para fora deste pacote não sai exceção do requests nem do utilitário HTTP."""


class GoogleTransporteError(GoogleGeocodingError):
    """Rede ou HTTP falharam depois de esgotada a política de retry."""


class GoogleRespostaInvalidaError(GoogleGeocodingError):
    """O corpo não é o contrato espelhado em models.py."""


class GoogleStatusError(GoogleGeocodingError):
    """O Google respondeu HTTP 200 com status de erro no corpo."""

    def __init__(self, status: str, mensagem: str) -> None:
        super().__init__(f"{status}: {mensagem}")
        self.status = status
```

**`services/integrations/geocodificador_externo/google/client.py`** — toda exceção sai sanitizada e
**levantada fora do `except`**, sem cadeia.

```python
class ClienteGoogle(ClienteGeocodificacao[GoogleGeocodeRequest, GoogleGeocodeResponse]):
    def __call__(self, requisicao: GoogleGeocodeRequest) -> GoogleGeocodeResponse:
        return self.pipeline(requisicao)

    def pipeline(self, requisicao: GoogleGeocodeRequest) -> GoogleGeocodeResponse:
        http = self._buscar(requisicao)
        resposta = self._validar(http)
        self._conferir_status(resposta)
        return resposta

    def _buscar(self, requisicao: GoogleGeocodeRequest) -> Response:
        # o Google só aceita a chave na query string: é aqui, e só aqui, que ela é aberta
        params = requisicao.to_query_params() | {"key": self.token.revelar()}
        try:
            return self._fetcher(URL_GEOCODING, params=params)
        except HttpFetchError as exc:
            motivo = self.token.sanitizar(f"{type(exc).__name__}: {exc}")
        # fora do except: nenhum __context__ aponta para a exceção crua, que carrega a URL com a chave
        raise GoogleTransporteError(motivo)

    def _validar(self, http: Response) -> GoogleGeocodeResponse:
        try:
            return GoogleGeocodeResponse.model_validate_json(http.content)
        except ValidationError as exc:
            motivo = self.token.sanitizar(str(exc))
        raise GoogleRespostaInvalidaError(motivo)

    def _conferir_status(self, resposta: GoogleGeocodeResponse) -> None:
        if resposta.status in STATUS_SEM_ERRO:
            return
        # o error_message é texto do provedor: passa pela sanitização como qualquer outro
        raise GoogleStatusError(resposta.status, self.token.sanitizar(resposta.error_message or ""))
```

**`services/integrations/geocodificador_externo/google/utils.py`** — sem token não há cliente; sem
`verbose`, porque o `HttpFetcher` verboso imprime a URL.

```python
class GoogleSettingsLike(Protocol):
    GOOGLE_GEOCODING_TOKEN: SecretStr


def build_cliente_google(source: GoogleSettingsLike) -> ClienteGoogle | None:
    if not source.GOOGLE_GEOCODING_TOKEN.get_secret_value():
        return None
    return ClienteGoogle(
        token=Token(valor=source.GOOGLE_GEOCODING_TOKEN),
        fetcher=HttpFetcher(RETRY_GOOGLE),
    )
```

**`services/integrations/geocodificador_externo/__init__.py`** — expõe os clientes dos provedores.

```python
from .base import ClienteGeocodificacao
from .google import (
    ClienteGoogle,
    GoogleGeocodeRequest,
    GoogleGeocodeResponse,
    GoogleGeocodingError,
    build_cliente_google,
    ...
)
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
O token viaja na query string, único meio que o Geocoding aceita. Por isso toda exceção da integração
é sanitizada e levantada fora do `except`, já que as exceções do `requests` (e o `repr` delas, que o
`HttpFetcher` repassa) carregam a URL completa. O custo é que a ABC só garante que o token é um
`Token`: o cuidado com a URL é de cada provedor, e o teste de não-vazamento cobre só o Google.

O `HttpFetcher`, entregue pela ingestao_dados/008, passa a traduzir todo `RequestException` em
`HttpFetchError`. A 008 já proibia `requests` de escapar do utilitário, e redirect em excesso ou URL
inválida escapavam, na ITBI inclusive. O custo é mexer num utilitário já entregue, e a 008 ganha uma
linha `[bugfix]` no `changelog` quando esta SPEC for implementada.

O cliente usa o `HttpFetcher` sempre sem `verbose`, e não há variável de ambiente para ligá-lo. No
modo verboso o utilitário imprime URL e `repr` de exceção, o que exporia a chave. O custo é não haver
log de depuração das chamadas ao Google.

`status` e `location_type` são `Literal` fechados no espelho. Valor novo do Google é mudança de
contrato e deve aparecer como erro, não passar calado até o domínio. O custo é a geocodificação
externa ficar indisponível até o espelho ser atualizado.

O teste de integração consulta a API real. É o único que prova o espelho contra a resposta de verdade.
O custo é exigir `GOOGLE_GEOCODING_TOKEN` no ambiente de quem roda o gate e consumir uma requisição da
cota a cada execução.

## 8 · Testes (TDD)
- `test_token_mascara_repr_e_sanitiza_texto` — `Token`, e um model que o carrega, nunca exibem o valor
  em `repr`/`str`; `sanitizar` troca o valor cru e o `quote`-ado por `***`.
- `test_http_fetcher_traduz_erro_do_requests_sem_repetir` — em `tests/services/utils/http/`: uma
  `Session` dublê que levanta `TooManyRedirects` é chamada uma vez só e resulta em `HttpFetchError`.
- `test_cliente_envia_parametros_e_o_token_como_key` — a `Session` dublê recebe a URL do Geocoding,
  `address`, `components` no formato `k:v|k:v`, `language`, `region` e `key` igual ao token.
- `test_resposta_ok_vira_espelho_tipado` — fixture JSON no formato real do Google vira
  `GoogleGeocodeResponse` com `location_type`, componentes e `partial_match`.
- `test_zero_results_devolve_lista_vazia` — status `ZERO_RESULTS` devolve resposta sem resultados e
  sem exceção.
- `test_status_de_erro_com_http_200_levanta_erro_com_o_status` — `REQUEST_DENIED` no corpo de um 200
  levanta `GoogleStatusError` com `status == "REQUEST_DENIED"`.
- `test_corpo_fora_do_contrato_levanta_resposta_invalida` — HTML no lugar de JSON e `location_type`
  desconhecido levantam `GoogleRespostaInvalidaError`.
- `test_nenhuma_excecao_da_integracao_vaza_o_token` — parametrizado sobre falha de rede (mensagem com
  a URL e a chave), HTTP definitivo, redirect em excesso, status no corpo com `error_message` ecoando a chave e corpo inválido ecoando a chave: o token não
  está em `str` nem `repr`, e `__cause__` e `__context__` são `None`.
- `test_build_sem_token_nao_monta_cliente` — `GOOGLE_GEOCODING_TOKEN` vazio devolve `None`.
- `test_geocoding_real_do_google` — endereço conhecido de São Paulo devolve `OK` com ao menos um
  resultado que o espelho aceita *(marker `integration`)*.
