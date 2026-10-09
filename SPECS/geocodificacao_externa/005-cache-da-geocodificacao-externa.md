---
spec: geocodificacao_externa/005
versao: v1
atualizado_em: 2026-10-09
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC geocodificacao_externa/005 — Cache da geocodificação externa

## 1 · User story
O servidor logado na plataforma geocodifica pelo provedor externo um endereço que já foi geocodificado
antes, no contexto de buscas que se repetem entre pessoas e dias, para ver o mesmo ponto sem gastar a
cota paga do provedor.

## 2 · Condições de pronto
- [ ] Geocodificar de novo um endereço já geocodificado, dentro da validade, **não chama o provedor**
      e devolve o mesmo ponto, o mesmo endereço, o mesmo provedor e a mesma precisão — pelo clique na
      sugestão e pelo Enter.
- [ ] "O mesmo endereço" é o texto igual depois de desconsiderados caixa, acento, pontuação e espaços
      repetidos: `Rua Augusta, 100` e `rua augusta 100` usam a mesma geocodificação cacheada;
      `rua augusta, 101` chama o provedor.
- [ ] Geocodificação guardada há **30 dias ou mais** (prazo definível no ambiente) não é servida: o
      provedor é chamado e o resultado novo toma o lugar do antigo.
- [ ] Geocodificação guardada que **deixou de caber na política** — precisão abaixo da mínima,
      município ou UF fora do recorte — não é servida: o provedor é chamado.
- [ ] Sem resultado aceito e provedor indisponível **não são guardados**: repetir a busca chama o
      provedor de novo.
- [ ] Texto com mais de 500 caracteres não é geocodificado externamente: a resposta é o erro de
      validação, e o provedor não é chamado.
- [ ] A gaveta do endereço externo mostra **o provedor que encontrou o endereço** e **quando ele foi
      consultado**; num resultado cacheado, são o provedor e o momento da consulta original.
- [ ] Resultado cacheado traz na gaveta o selo **Cacheado**; resultado que acabou de vir do provedor
      não traz.
- [ ] O design da gaveta com o momento da consulta e o selo **Cacheado** foi aprovado no mock e as
      peças novas portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O endereço é o [EnderecoExternoFeature](002-geocodificador-externo-agnostico.md#3--domínio), com o
provedor e a precisão que ele já declara; a pergunta que esta SPEC faz a ele é "isto, que foi
encontrado antes, ainda vale para esta consulta?". À gaveta da SPEC
[003](003-endereco-externo-no-mapa-e-na-gaveta.md) ela pergunta "quem encontrou isto, quando, e veio do
cache?".

**`services/domain/geocodificador_externo/models.py`** — `ConsultaGeocodificacao` e
`PoliticaGeocodificacao` inteiras.

```python
# o índice único da chave tem teto de tamanho no banco: o tipo recusa antes
TAMANHO_MAX_CONSULTA = 500


class ConsultaGeocodificacao(BaseModel):
    texto: str = Field(min_length=1, max_length=TAMANHO_MAX_CONSULTA)  # ALTERADO nesta SPEC: teto

    @property
    def chave(self) -> str:  # ALTERADO nesta SPEC: derivado novo
        """Duas consultas com a mesma chave são a mesma consulta."""
        return normalize_text(self.texto)


class GeocodificacaoExterna(BaseModel):  # NOVO
    """O vínculo entre o que a pessoa digitou e o endereço que um provedor encontrou para aquilo."""

    consulta: ConsultaGeocodificacao
    endereco: EnderecoExternoFeature  # o provedor e a precisão são dele: não se repetem aqui
    consultado_em: AwareDatetime      # quando o provedor foi chamado; servir do cache não o muda


class PoliticaGeocodificacao(BaseModel):
    """O recorte de toda consulta externa: cada provedor o traduz na sua requisição."""

    model_config = ConfigDict(frozen=True)

    idioma: str = "pt-BR"
    pais: str = "BR"
    uf: str = "SP"
    municipio: str = "São Paulo"
    precisao_minima: Precisao = Precisao.INTERPOLADA
    validade_dias: int = Field(default=30, gt=0)  # ALTERADO nesta SPEC: até quando o guardado vale
```

**`services/domain/geocodificador_externo/cache.py`** — o que o geocodificador espera de um cache.
Quem o satisfaz não herda dele.

```python
class CacheGeocodificacaoLike(Protocol):
    """Onde as geocodificações ficam guardadas: no máximo uma por chave, seja de que provedor for."""

    def buscar(self, consulta: ConsultaGeocodificacao) -> GeocodificacaoExterna | None:
        """A guardada para a chave, vencida ou não, no CRS em que foi guardada."""
        ...

    def guardar(self, geocodificacao: GeocodificacaoExterna) -> None:
        """Guarda, tomando o lugar da que houver para a mesma chave."""
        ...
```

**Mock:** [005-mock-cache-da-geocodificacao-externa.html](005-mock-cache-da-geocodificacao-externa.html)
— leia a skill `mock`.

## 4 · Fora de escopo
- Guardar a consulta que o provedor não resolveu (sem resultado aceito) — sem dono ainda.
- Apagar as geocodificações vencidas que ninguém refez — sem dono ainda.
- Servir do cache uma consulta parecida, por semelhança de texto — sem dono ainda.
- Validade própria de cada provedor — sem dono ainda.
- Percentual de certeza além da precisão que o provedor declara — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/geocodificador_externo/geocodificador.py` → `_no_recorte`, `_precisao_suficiente`: as regras de aceite, que mudam de casa para o validador sem mudar de regra; `_no_crs`: a reprojeção (SPEC 002).
- `@services/domain/geocodificador_externo/factory.py` → `_provedor_google`, `CONSTRUTORES`, `PROVEDOR_PADRAO`: mudam de arquivo para `provedores/` sem mudar de regra; `build_politica`, `escolher_provedor`: ficam (SPEC 002).
- `@services/domain/exercicio/designacao.py` → `AvaliadorDesignacao`: o molde do validador callable, com um método-passo por critério.
- `@services/utils/normalization` → `normalize_text`: a chave da consulta.
- `@services/utils/ambiente` → `definidos`: a validade do ambiente sobre o padrão da política.
- `@services/domain/geometry` → `reprojetar`: a reprojeção única, antes de guardar; `para_geos`: do ponto do contrato para o ponto da coluna.
- `@apps/documentos/acervo.py` → o molde da persistência ao lado do model, convertendo linha em objeto do domínio.
- `@apps/geocodificacao_externa/views.py` → `geocodificador_externo`, `geocodificar_externo`: o caminho único do clique e do Enter (SPECs 003 e 004).
- Skills: `ontologia`, `normalize-text`, `escrever-testes`, `mock`, `componentes-frontend`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/geocodificador_externo/cache.py`** — o cache de quem não tem cache: o geocodificador
não pergunta se há um.

```python
class SemCache:
    def buscar(self, consulta: ConsultaGeocodificacao) -> GeocodificacaoExterna | None:
        return None

    def guardar(self, geocodificacao: GeocodificacaoExterna) -> None:
        return None
```

**`services/domain/geocodificador_externo/validador.py`** — os critérios numa classe só, sempre pelo
`__call__`. Vale para a geocodificação que acabou de chegar do provedor e para a cacheada.

```python
class ValidacaoGeocodificacaoInput(BaseModel):
    geocodificacao: GeocodificacaoExterna
    agora: AwareDatetime


class ValidadorGeocodificacao:
    def __init__(self, politica: PoliticaGeocodificacao) -> None:
        self._politica = politica

    def __call__(self, entrada: ValidacaoGeocodificacaoInput) -> bool:
        return self.pipeline(entrada)

    def pipeline(self, entrada: ValidacaoGeocodificacaoInput) -> bool:
        # critério novo é um método-passo a mais nesta cadeia: quem chama o validador não muda
        endereco = entrada.geocodificacao.endereco
        return (
            self._na_validade(entrada)
            and self._no_recorte(endereco)
            and self._precisao_suficiente(endereco)
        )

    def _na_validade(self, entrada: ValidacaoGeocodificacaoInput) -> bool:
        validade = timedelta(days=self._politica.validade_dias)
        return entrada.agora - entrada.geocodificacao.consultado_em < validade  # no dia 30 já não vale

    def _no_recorte(self, endereco: EnderecoExternoFeature) -> bool:
        ...  # como hoje no GeocodificadorExterno: muda de casa, não de regra

    def _precisao_suficiente(self, endereco: EnderecoExternoFeature) -> bool:
        ...  # idem
```

**`services/domain/geocodificador_externo/geocodificador.py`** — `GeocodificacaoExternaInput` e
`GeocodificadorExterno` inteiros. Ele só orquestra: pergunta ao cache, pergunta ao validador, chama o
provedor e manda guardar. O cache vem antes do provedor, e a reprojeção acontece uma vez, antes de
guardar: o que está no cache já está no CRS em que é servido.

```python
class GeocodificacaoExternaInput(BaseModel):
    consulta: ConsultaGeocodificacao
    output_crs: int
    agora: AwareDatetime  # ALTERADO nesta SPEC: o relógio vem da orquestração, como o CRS


class GeocodificacaoExternaOutput(BaseModel):  # NOVO
    geocodificacao: GeocodificacaoExterna
    cacheada: bool  # veio do cache: nesta operação o provedor não foi chamado


class GeocodificadorExterno:
    def __init__(
        self,
        provedor: ProvedorGeocodificacao,
        cache: CacheGeocodificacaoLike | None = None,      # ALTERADO nesta SPEC
        validador: ValidadorGeocodificacao | None = None,  # ALTERADO nesta SPEC
    ) -> None:
        self._provedor = provedor
        self._cache = cache or SemCache()
        # sem validador explícito, vale o da política do próprio provedor
        self._validador = validador or ValidadorGeocodificacao(provedor.politica)

    @property
    def provedor(self) -> Provedor:
        return self._provedor.provedor

    # ALTERADO nesta SPEC: devolve o vínculo e de onde ele veio, não só o endereço
    def __call__(self, entrada: GeocodificacaoExternaInput) -> GeocodificacaoExternaOutput:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GeocodificacaoExternaInput) -> GeocodificacaoExternaOutput:
        guardada = self._do_cache(entrada)
        geocodificacao = guardada or self._do_provedor(entrada)
        return GeocodificacaoExternaOutput(
            geocodificacao=geocodificacao,
            # "veio do cache" é fato desta operação, não do vínculo: não é guardado em lugar nenhum
            cacheada=guardada is not None,
        )

    def _do_cache(self, entrada: GeocodificacaoExternaInput) -> GeocodificacaoExterna | None:
        # sem filtro de provedor: serve o que qualquer um guardou, desde que o validador aceite
        guardada = self._cache.buscar(entrada.consulta)
        if guardada is None or not self._vale(guardada, entrada):
            return None  # recusada pelo validador é como se não houvesse: o provedor a refaz
        # já está no CRS pedido: o `_no_crs` aqui não reprojeta, só garante a saída se o CRS do mapa mudar
        return self._no_crs(guardada, entrada.output_crs)

    def _do_provedor(self, entrada: GeocodificacaoExternaInput) -> GeocodificacaoExterna:
        # cada endereço do provedor já nasce como vínculo: é o que o validador sabe julgar
        candidatas = [
            GeocodificacaoExterna(
                consulta=entrada.consulta,
                endereco=endereco,
                consultado_em=entrada.agora,
            )
            for endereco in self._provedor(entrada.consulta)  # indisponível levanta aqui: nada é guardado
        ]
        validas = [c for c in candidatas if self._vale(c, entrada)]
        if not validas:
            raise SemResultadoAceitoError(entrada.consulta.texto)  # idem: falha não entra no cache
        # max devolve a primeira entre as empatadas: a ordem do provedor desempata
        melhor = max(validas, key=lambda c: c.endereco.attributes.precisao.nivel)
        # a única reprojeção: do CRS do provedor para o pedido, ANTES de guardar
        escolhida = self._no_crs(melhor, entrada.output_crs)
        self._cache.guardar(escolhida)
        return escolhida

    def _vale(
        self,
        geocodificacao: GeocodificacaoExterna,
        entrada: GeocodificacaoExternaInput,
    ) -> bool:
        # o único caminho de validação, para a cacheada e para a recém-chegada
        return self._validador(
            ValidacaoGeocodificacaoInput(geocodificacao=geocodificacao, agora=entrada.agora)
        )

    def _no_crs(
        self,
        geocodificacao: GeocodificacaoExterna,
        output_crs: int,
    ) -> GeocodificacaoExterna:
        endereco = geocodificacao.endereco
        if endereco.crs == output_crs:
            return geocodificacao
        ponto = reprojetar(endereco.geometry, endereco.crs, output_crs)
        reprojetado = endereco.model_copy(update={"geometry": ponto, "crs": output_crs})
        return geocodificacao.model_copy(update={"endereco": reprojetado})
```

**`services/domain/geocodificador_externo/provedores/google.py`** — o construtor do Google vem de
`factory.py` para o lado do `ProvedorGoogle`: é este módulo que conhece a integração do Google.

```python
def build_provedor_google(
    source: google.SettingsLike,  # só o que o Google lê do ambiente: o token
    politica: PoliticaGeocodificacao,
) -> ProvedorGoogle | None:
    # None = sem token no ambiente
    cliente = google.build_cliente(source)
    return None if cliente is None else ProvedorGoogle(politica, cliente)
```

**`services/domain/geocodificador_externo/provedores/registro.py`** — NOVO: o único módulo que sabe
quais provedores concretos existem. Provedor novo é uma base a mais no protocolo e uma entrada a mais
no registro, sem tocar na factory.

```python
PROVEDOR_PADRAO = Provedor.GOOGLE


class ProvedoresSettingsLike(google.SettingsLike, Protocol):
    """O que os provedores inscritos leem do ambiente."""


# devolve None quando o provedor não está configurado (sem token)
ConstrutorProvedor = Callable[
    [ProvedoresSettingsLike, PoliticaGeocodificacao],
    ProvedorGeocodificacao | None,
]

CONSTRUTORES: dict[Provedor, ConstrutorProvedor] = {
    Provedor.GOOGLE: build_provedor_google,
}
```

**`services/domain/geocodificador_externo/factory.py`** — inteiro. Não importa integração nenhuma nem
nomeia provedor: lê o settings geral, escolhe pelo nome e compõe provedor, cache e validador.

```python
from .provedores import CONSTRUTORES, PROVEDOR_PADRAO, ProvedoresSettingsLike


class GeocodificacaoSettingsLike(Protocol):  # ALTERADO nesta SPEC: geral, sem herdar de provedor
    GEOCODIFICACAO_EXTERNA_PROVEDOR: str | None
    GEOCODIFICACAO_EXTERNA_IDIOMA: str | None
    GEOCODIFICACAO_EXTERNA_PAIS: str | None
    GEOCODIFICACAO_EXTERNA_UF: str | None
    GEOCODIFICACAO_EXTERNA_MUNICIPIO: str | None
    GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA: str | None
    GEOCODIFICACAO_EXTERNA_VALIDADE_DIAS: int | None  # ALTERADO nesta SPEC


class ComposicaoSettingsLike(GeocodificacaoSettingsLike, ProvedoresSettingsLike, Protocol):  # NOVO
    """O ambiente de quem compõe: o geral mais o que os provedores inscritos leem, sem nomeá-los."""


def build_politica(source: GeocodificacaoSettingsLike) -> PoliticaGeocodificacao:
    return definidos(
        PoliticaGeocodificacao,
        {
            ...,  # como hoje
            "validade_dias": source.GEOCODIFICACAO_EXTERNA_VALIDADE_DIAS,  # ALTERADO nesta SPEC
        },
    )


def escolher_provedor(source: GeocodificacaoSettingsLike) -> Provedor:
    ...  # como hoje


def build_geocodificador_externo(
    source: ComposicaoSettingsLike,                # ALTERADO nesta SPEC: só a composição pede os dois
    cache: CacheGeocodificacaoLike | None = None,  # ALTERADO nesta SPEC
) -> GeocodificadorExterno | None:
    construir = CONSTRUTORES[escolher_provedor(source)]
    politica = build_politica(source)
    provedor = construir(source, politica)
    if provedor is None:
        return None
    # a mesma política para quem consulta e para quem valida
    return GeocodificadorExterno(provedor, cache, ValidadorGeocodificacao(politica))
```

**`services/domain/geometry/conversao.py`** — o inverso do `para_geos`, ao lado dele.

```python
def de_geos[G: (PointGeometry, LineGeometry, PolygonGeometry)](
    geos: GEOSGeometry,
    tipo: type[G],
) -> G:
    return tipo.model_validate_json(geos.geojson)
```

**`apps/geocodificacao_externa/models.py`** — a linha é o contrato em colunas, independente de
provedor. Só persistência.

```python
from django.conf import settings
from django.contrib.gis.db import models

# a coluna tem o CRS do mapa: o ponto é guardado na projeção em que é servido
SRID_PONTO: int = settings.MAP_OUTPUT_CRS


class GeocodificacaoGuardada(models.Model):
    chave = models.TextField()     # a chave da consulta: é o que a busca compara
    consulta = models.TextField()  # o texto como digitado por quem encheu a linha
    provedor = models.CharField(max_length=20)  # quem encontrou: dado da linha, não critério da busca
    consultado_em = models.DateTimeField()
    ponto = models.PointField(srid=SRID_PONTO)
    endereco_formatado = models.TextField()
    logradouro = models.TextField(null=True)
    numero = models.TextField(null=True)
    bairro = models.TextField(null=True)
    municipio = models.TextField(null=True)
    uf = models.TextField(null=True)
    cep = models.TextField(null=True)
    precisao = models.CharField(max_length=20)

    class Meta:
        constraints = [
            # a unicidade JÁ É o índice da busca: a chave é exatamente o que `buscar` filtra
            models.UniqueConstraint(
                fields=["chave"],
                name="geocodificacao_guardada_unica",
            ),
        ]
```

**`apps/geocodificacao_externa/cache.py`** — o adaptador: traduz entre a linha e o vínculo, e mais nada.

```python
# satisfaz o CacheGeocodificacaoLike sem herdar dele: o mypy confere onde ele é injetado
class CacheEmBanco:
    def buscar(self, consulta: ConsultaGeocodificacao) -> GeocodificacaoExterna | None:
        linha = GeocodificacaoGuardada.objects.filter(chave=consulta.chave).first()
        return None if linha is None else self._para_dominio(linha)

    def guardar(self, geocodificacao: GeocodificacaoExterna) -> None:
        # update_or_create: refazer uma vencida sobrescreve a linha em vez de criar outra
        GeocodificacaoGuardada.objects.update_or_create(
            chave=geocodificacao.consulta.chave,
            defaults=self._para_colunas(geocodificacao),
        )

    def _para_colunas(self, geocodificacao: GeocodificacaoExterna) -> dict[str, Any]:
        endereco = geocodificacao.endereco
        return {
            "consulta": geocodificacao.consulta.texto,
            "provedor": endereco.attributes.provedor.value,  # quem encontrou, guardado com a linha
            "consultado_em": geocodificacao.consultado_em,
            # chega do domínio já no CRS do mapa, que é o da coluna: o adaptador não reprojeta
            "ponto": para_geos(endereco.geometry, endereco.crs),
            ...,  # os demais atributos do endereço, um por coluna
        }

    def _para_dominio(self, linha: GeocodificacaoGuardada) -> GeocodificacaoExterna:
        return GeocodificacaoExterna(
            consulta=ConsultaGeocodificacao(texto=linha.consulta),
            endereco=EnderecoExternoFeature(
                geometry=de_geos(linha.ponto, PointGeometry),
                attributes=EnderecoExternoAttributes(
                    provedor=Provedor(linha.provedor),  # o provedor original, não o em uso
                    ...,  # as demais colunas, uma por atributo
                ),
                crs=linha.ponto.srid,  # o CRS que o ponto guardado diz ter
            ),
            consultado_em=linha.consultado_em,
        )
```

**`apps/geocodificacao_externa/views.py`** — a view escolhe o cache e o relógio; `_aviso` e
`_aviso_fallback` seguem como hoje.

```python
def geocodificador_externo() -> GeocodificadorExterno | None:
    return build_geocodificador_externo(settings, CacheEmBanco())  # ALTERADO nesta SPEC


def geocodificar_externo(
    request: HttpRequest,
    geocodificador: GeocodificadorExterno,
    texto: str,
    falha: FalhaBaseOficial | None = None,
) -> HttpResponse:
    entrada = GeocodificacaoExternaInput(
        consulta=ConsultaGeocodificacao(texto=texto),  # acima do teto: o middleware responde o 422
        output_crs=MAP_OUTPUT_CRS,
        agora=timezone.now(),  # ALTERADO nesta SPEC
    )
    try:
        saida = geocodificador(entrada)
    except ProvedorIndisponivelError:
        return _aviso(request, MSG_INDISPONIVEL, falha, tom="error")
    except SemResultadoAceitoError:
        return _aviso(request, MSG_SEM_RESULTADO, falha, tom="warning")
    aviso = _aviso_fallback(falha, saida.geocodificacao.endereco)
    contexto = _contexto_externo(saida) | {"aviso_fallback": aviso}
    return render(request, TEMPLATE_RESULTADO_EXTERNO, contexto)


def _contexto_externo(saida: GeocodificacaoExternaOutput) -> dict[str, Any]:
    endereco = saida.geocodificacao.endereco
    ...  # geojson como hoje, a partir de `endereco`
    return contexto_mapa(geojson, MAP_COR_PONTO) | {
        ...,
        # como hoje: o rótulo sai do próprio endereço — no cacheado, é o provedor original
        "provedor": endereco.attributes.provedor.rotulo,
        "consultado_em": saida.geocodificacao.consultado_em,  # ALTERADO nesta SPEC
        "cacheada": saida.cacheada,                           # ALTERADO nesta SPEC
    }
```

**`config/settings.py`** — opcional, como os demais: o padrão mora na `PoliticaGeocodificacao`.

```python
    geocodificacao_externa_validade_dias: int | None = Field(
        default=None, alias="GEOCODIFICACAO_EXTERNA_VALIDADE_DIAS"
    )
```

## 7 · Caveats
Geocodificação vencida deixa de ser servida, mas só sai da tabela quando a mesma busca é refeita e a
sobrescreve. A reconsulta já substitui a linha, e uma rotina de limpeza seria mais uma peça a operar. O
custo é que a tabela só cresce: a geocodificação vencida que ninguém refaz fica guardada sem prazo.

A consulta que o provedor não resolve não é guardada. A linha é o contrato do endereço encontrado, e
"não encontrado" não cabe nele. O custo é que um endereço sem resultado aceito gasta cota a cada
repetição.

A `chave` é derivada do texto e mesmo assim vira coluna. O índice único precisa de uma coluna para
comparar. O custo é que mudar uma etapa do `normalize_text` deixa órfãs as linhas já guardadas: elas
param de ser encontradas, e cada busca paga a chamada de novo.

A política não entra na chave do cache. Precisão mínima, município e UF são reconferidos a cada vez que
o cache é servido, o que cobre as mudanças que tornariam o guardado errado. O custo é que idioma e país
não são reconferidos: trocar o idioma no ambiente só aparece nas gavetas quando a validade vence.

O cache não distingue provedor: o que qualquer um guardou é servido, se couber na política e na
validade. O endereço já foi pago e aceito pelos mesmos critérios, e a gaveta declara quem o encontrou.
O custo é que, trocado o provedor no ambiente, a sugestão diz "via" o provedor em uso e a gaveta pode
declarar outro, até a validade do guardado vencer.

O ponto é guardado no CRS do mapa: a coluna tem o SRID de `MAP_OUTPUT_CRS`, e o geocodificador
reprojeta uma vez, antes de guardar. O que está guardado é o que se serve, sem reprojeção na leitura e
sem CRS fixo no model. O custo é que mudar o CRS do mapa no settings passa a exigir migração da
coluna, com as geocodificações já guardadas reprojetadas ou apagadas.

`GeocodificadorExterno` passa a devolver `GeocodificacaoExternaOutput`, a entrada ganha `agora`, a
factory recebe o cache e as regras de aceite saem dele para o `ValidadorGeocodificacao`. O momento da
consulta e o selo de cacheado precisam chegar à gaveta junto do endereço, e os critérios precisam de
uma casa só para o que chega do provedor e para o que sai do cache. O custo é editar os testes das
SPECs 002, 003 e 004 que constroem a entrada, leem o resultado ou substituem a factory, sem mudar o
que eles fixam.

A SPEC do cache carrega também a reorganização da inscrição dos provedores: o construtor do Google, o
registro e o provedor padrão saem de `factory.py` para `provedores/`, e o settings geral deixa de
herdar o do Google. `factory.py` já é editado aqui, e mantê-lo conhecendo o Google faria o settings
geral crescer por herança a cada provedor novo. O custo é uma SPEC com dois assuntos, código da SPEC
002 movido de arquivo sem teste novo que o fixe, e um protocolo que ainda junta os settings dos
provedores, agora só em `provedores/registro.py`.

## 8 · Testes (TDD)
Os testes de domínio usam um cache dublê em memória que satisfaz o `CacheGeocodificacaoLike` e um
provedor dublê que
conta as chamadas. A reorganização dos provedores não muda comportamento: quem a fixa são os testes de
`test_factory.py` da SPEC 002, que seguem passando pela API pública.

- `test_consulta_repetida_dentro_da_validade_nao_chama_o_provedor` — parametrizado no intervalo (mesmo
  instante, 29 dias depois): a primeira consulta sai com `cacheada` falso; a segunda devolve a
  geocodificação da primeira, com o `consultado_em` dela e `cacheada` verdadeiro, e o provedor
  conta uma chamada.
- `test_cache_casa_pela_chave_e_nao_pelo_texto_literal` — parametrizado: depois de `Rua Augusta, 100`,
  `rua augusta 100` e `RUA  AUGUSTA,100` não chamam o provedor; `rua augusta, 101` chama.
- `test_guardada_que_nao_vale_mais_eh_refeita_e_sobrescrita` — parametrizado: 30 dias depois, 7 dias
  depois com a validade da política em 7, precisão abaixo da mínima e município fora do recorte chamam
  o provedor, e o cache passa a ter a geocodificação nova.
- `test_falha_do_provedor_nao_eh_guardada` — parametrizado: sem resultado aceito e provedor
  indisponível deixam o cache vazio, e repetir a consulta chama o provedor de novo.
- `test_geocodificacao_eh_guardada_ja_no_crs_pedido` — com o provedor respondendo em 4326 e o pedido em
  31983, o resultado sai com `crs` 31983 e o que está no cache também; a consulta repetida devolve o
  mesmo ponto.
- `test_geocodificador_obedece_ao_validador_que_recebe` — com um validador dublê que recusa tudo, a
  cacheada dentro da validade não é servida, o provedor é chamado e o resultado dele levanta
  `SemResultadoAceitoError`, sem nada guardado.
- `test_cache_em_banco_devolve_o_que_guardou` — guardar e buscar devolve a mesma geocodificação: ponto,
  atributos (os ausentes inclusive), texto da consulta e `consultado_em`. *(marker `banco`)*
- `test_cache_em_banco_guarda_uma_por_chave` — guardar duas vezes a mesma chave deixa uma linha, com
  os dados da segunda. *(marker `banco`)*
- `test_gaveta_declara_provedor_momento_e_selo_de_cacheado` — parametrizado: com o cache dublê trazendo
  uma geocodificação de 02/10/2026, a gaveta traz o provedor dela, essa data e o selo "Cacheado", e o
  provedor não é chamado; com o cache vazio, traz o provedor e o momento de agora, sem o selo.
- `test_texto_acima_do_teto_eh_recusado_sem_chamar_o_provedor` — `geocodificar_externo` com 501
  caracteres levanta `ValidationError`, e o provedor conta zero chamadas.
