---
name: leaflet-eventos
description: Como capturar e tratar eventos do mapa Leaflet no DIMAP GeoCoder (click, moveend, desenho de geometrias) respeitando a regra de JS restrito — o JS só serializa a geometria/coordenada e dispara HTMX para o backend; validação e regra de negócio ficam sempre no servidor. Use ao implementar interação com o mapa além da renderização (que é a skill leaflet-map).
---

> **PLACEHOLDER — skill prometida pela própria `leaflet-map`** ("Fora do escopo: capturar
> eventos do mapa — skill futura"). Materializar quando o épico correspondente começar
> (Fase 2: digitalização manual no mapa; ou antes, se algum fluxo precisar de `map.on(...)`).
> Escrever a SPEC do épico primeiro; esta skill nasce da implementação, não antes dela.

# Leaflet — eventos do mapa (escopo planejado)

## O que esta skill vai cobrir

1. **Handlers de evento do mapa** (`map.on('click', ...)`, `moveend`, eventos de layer) — como
   registrá-los sem vazar regra de negócio para o JS.
2. **Ponte evento → HTMX:** o handler serializa o dado mínimo (latlng, bounds, GeoJSON
   desenhado) e dispara um POST HTMX (`htmx.ajax` ou form oculto — decidir e padronizar);
   o backend valida com DTO Pydantic e responde partial.
3. **Desenho de geometrias (modo projeto, Fase 2):** plugin de desenho (decidir qual —
   Leaflet.draw? Geoman?), extração do GeoJSON e envio ao backend, que valida a homogeneidade
   do layer no domínio e persiste via GeoDjango.
4. **Limpeza de handlers** em swaps HTMX (evitar handlers duplicados quando o partial do mapa
   re-renderiza — amarrar em `htmx:beforeSwap`/`htmx:afterSwap`).

## Restrições já conhecidas (do CLAUDE.md e da leaflet-map)

- JS puro, sem frameworks; só callbacks HTMX + utilitários Leaflet.
- JS **nunca** reprojeta (tudo chega/sai em EPSG:4326) e nunca monta UI a partir de JSON.
- Nada hardcoded: qualquer config de comportamento vem do servidor via `json_script`.
- Validação e persistência sempre no servidor.
