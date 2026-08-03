---
name: geo-crs
description: "Como o DIMAP GeoCoder lida com projeção cartográfica (CRS/SRID): quais CRS existem e para quê, como o CRS chega ao domínio pela orquestração, a diferença entre rotular (`geom.srid = X`) e reprojetar (`geom.transform(X)`), e por que cálculo métrico exige CRS projetado. Use SEMPRE que o código criar, converter, interpolar, medir, reprojetar ou serializar geometria — nunca reprojete manualmente nem escreva um código EPSG dentro do domínio."
---

> **RASCUNHO — pronto para promover.** Diferente dos outros rascunhos desta pasta, este foi
> **escrito lendo o código** (`services/domain/geometry/`, `services/domain/address_geocod/`,
> `services/domain/{logradouro,lote}_geocod/`, `config/settings.py`, views dos apps `*_geocoder`).
> Assinaturas e citações `arquivo:linha` conferem em 2026-07-31.

# Projeção e CRS — DIMAP GeoCoder

Toda geometria do sistema carrega um CRS, e quase todo bug geoespacial é um CRS errado passando
despercebido: as coordenadas continuam sendo números plausíveis, o mapa continua renderizando, e o
ponto aparece no lugar errado — ou a conta métrica sai em graus. Esta skill fixa as três regras que
evitam isso.

---

## 1. Os dois CRS do projeto

| CRS | O que é | Papel |
|---|---|---|
| **31983** | SIRGAS 2000 / UTM 23S — **projetado**, unidade em **metros** | Nativo do GeoSampa. É o CRS em que se **calcula** (interpolar, medir, comparar distância). |
| **4326** | WGS84 — **geográfico**, unidade em **graus** | É o CRS de **saída**. O Leaflet só aceita este. |

Ambos vivem em `config/settings.py`, nunca no domínio:

```python
MAP_OUTPUT_CRS = 4326          # saída para o Leaflet
MAP_INTERPOLATION_CRS = 31983  # CRS métrico para interpolar o número sobre o segmento
```

**Regra:** cálculo métrico em CRS **projetado**; saída sempre em **4326**.
*Por quê:* em 4326 a unidade é o grau, e um grau não tem tamanho constante — interpolação,
`length` e distância dão resultado errado. Não é aproximação ruim: é conta na unidade errada.

---

## 2. O CRS vem da orquestração — nunca do domínio

O domínio **não decide** em que CRS trabalha; ele **recebe**. A view reextrai a setting para
constante de módulo e a passa no DTO de entrada:

```python
# apps/logradouro_geocoder/views.py
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS          # constante local (CLAUDE.md §7.1)
...
entrada = LogradouroGeocodInput(codlog=..., layer_name=..., output_crs=MAP_OUTPUT_CRS)
```

```python
# services/domain/logradouro_geocod/models.py
class LogradouroGeocodInput(BaseModel):
    ...
    output_crs: int
```

O fluxo de endereço recebe **dois**, porque calcula num e devolve no outro
(`services/domain/address_geocod/models.py`):

```python
interpolation_crs: int   # CRS projetado p/ interpolar (31983), via orquestração
output_crs: int          # CRS de saída (4326), via orquestração
```

**Nunca** escreva `31983` ou `4326` dentro de `services/`. Se um número EPSG aparece no domínio, o
desenho está errado.

### O envelope de domínio carrega o CRS

`GeoFeature` (`services/domain/geometry/models.py`) tem o campo `crs: int`. Toda feature que
circula pelo domínio **sabe em que CRS está** — é isso que permite rotular a geometria corretamente
mais adiante, sem adivinhação.

---

## 3. A primeira escolha não é reprojetar — é pedir na projeção certa

Antes de pensar em `transform()`, veja se dá para pedir o dado já no CRS desejado. Os geocoders
fazem isso no próprio request WFS:

```python
# services/domain/logradouro_geocod/geocoder.py  (idem lote_geocod)
srs_name=f"EPSG:{entrada.output_crs}"
```

E o `AddressGeocoder` compõe o `LogradouroGeocoder` pedindo os segmentos **já no CRS de
interpolação**, não no de saída:

```python
# services/domain/address_geocod/geocoder.py
segmentos = self._segmentos(LogradouroGeocodInput(
    codlog=entrada.codlog,
    layer_name=entrada.layer_name,
    output_crs=entrada.interpolation_crs,   # métrico: é onde a conta vai acontecer
))
```

Reprojeção é o que sobra quando não dá para pedir na projeção certa — como no ponto interpolado,
que **nasce** em 31983 porque foi calculado ali.

---

## 4. Rotular ≠ reprojetar (a armadilha nº 1)

Duas operações que se parecem e fazem coisas opostas:

| Operação | O que faz | Quando usar |
|---|---|---|
| `geom.srid = X` | **Rotula**: declara em que CRS as coordenadas **já estão**. Não mexe nas coordenadas. | Logo após construir a geometria a partir de coordenadas cruas. |
| `geom.transform(X)` | **Reprojeta**: converte as coordenadas para o CRS X. | Quando a geometria precisa mudar de CRS de fato. |

Trocar um pelo outro **não levanta erro** — só produz coordenadas erradas em silêncio.

### O caso do GeoJSON (por que o `srid` vem depois da construção)

`GEOSGeometry`, ao desserializar GeoJSON, **assume SRID 4326** (RFC 7946) e **rejeita** um `srid=`
explícito que destoe disso. Por isso o SRID é atribuído **depois** de construir:

```python
# services/domain/address_geocod/orientacao.py — linha_geos()
geom = GEOSGeometry(json.dumps({"type": line.type, "coordinates": line.coordinates}))
geom.srid = feature.crs     # rotula com o CRS em que a feature realmente veio; NÃO reprojeta
```

Passar `srid=feature.crs` no construtor quebra; rotular depois é o padrão do projeto.

### A reprojeção real, quando acontece

```python
# services/domain/address_geocod/interpolacao.py
ponto: Point = linha.interpolate_normalized(proporcao)
ponto.srid = linha.srid       # rotula: o ponto nasceu no CRS da linha (31983)
ponto.transform(output_crs)   # reprojeta de fato para 4326
```

Ler essas duas linhas na ordem é o melhor resumo da skill.

### Ao reconstruir uma geometria, repasse o SRID

```python
# services/domain/address_geocod/orientacao.py
return LineString(list(linha.coords)[::-1], srid=linha.srid)
```

Construir a partir de coordenadas de outra geometria **perde o rótulo** se o `srid` não for
repassado — e a próxima operação passa a trabalhar com um SRID default errado.

---

## 5. Saída para o mapa

`to_geojson_feature_collection` (`services/domain/geometry/serializers.py`) monta a
`FeatureCollection` que o Leaflet consome. Ela é **agnóstica ao tipo de geometria** e pressupõe que
as features já chegaram em **4326** — a serialização **não reprojeta**. Garantir o CRS de saída é
responsabilidade de quem produz a feature.

Renderizar isso no mapa é assunto da skill `leaflet-map`.

---

## 6. Conversão de coordenadas → objeto geométrico

Existe **um** ponto de conversão para o fluxo de segmentos: `linha_geos()` em
`address_geocod/orientacao.py`. Além de rotular o SRID, ela resolve `MultiLineString`: funde
(`merged`) quando as partes são contíguas, senão toma a parte mais longa. Não escreva outra
conversão coords → GEOS para segmentos — componha essa.

---

## 7. Regras inegociáveis

- **Nenhum código EPSG dentro de `services/`.** O CRS chega por DTO, vindo da orquestração.
- **Reprojeção só via GeoDjango** (`transform()`, objetos GEOS/GDAL). Nada de fórmula manual de
  conversão de coordenadas.
- **Cálculo métrico em CRS projetado** (31983); **saída em 4326**.
- **Rotular ≠ reprojetar** — ver §4.
- **Nada de parsing manual de WKT/coordenadas** fora do caminho GeoDjango.

### Quando a persistência de geometria entrar (épico de projetos)

Ainda **não existe** model com campo geométrico. Quando existir, define-se um **CRS canônico de
armazenamento como constante única**, e a reprojeção de saída (para 4326) passa a acontecer na
borda, via `Transform` do `django.contrib.gis.db.models.functions`. Até lá, o CRS é só um valor que
transita nos DTOs.

---

## Checklist antes de mexer em geometria

- [ ] O CRS veio da orquestração (DTO), e não de um literal no domínio?
- [ ] A conta métrica (interpolar, medir, comparar distância) acontece em **31983**, não em 4326?
- [ ] Onde eu escrevi `srid =`, eu queria mesmo **rotular** — e onde escrevi `transform()`, queria
      mesmo **reprojetar**?
- [ ] Geometria construída a partir de GeoJSON teve o SRID atribuído **depois** da construção?
- [ ] Geometria reconstruída (inversão, recorte) repassou o `srid`?
- [ ] O que vai para o serializer/Leaflet está em **4326**?
- [ ] Dava para **pedir** o dado já no CRS certo (`srs_name`) em vez de reprojetar?

---

## Fora de escopo

- **Renderizar** geometria no mapa → skill `leaflet-map`.
- **Buscar** features no geoserver → skill `wfs-fetcher`.
- Operações espaciais sobre dados persistidos (interseção, filtro por área) — não existem ainda;
  entram com o épico de projetos.
