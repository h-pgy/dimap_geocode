---
name: wms-fetcher
description: Como usar o integrador WMS (services/integrations/wms) do DIMAP GeoCoder para obter tiles/imagens da camada base (mapa e ortofoto do GeoSampa). Use ao configurar a camada base do mapa, escrever código que monte requisições WMS (GetMap/GetCapabilities) ou depurar erros de requisição ao geoserver — nunca monte URLs WMS à mão.
---

> **RASCUNHO — validar contra o código antes de promover a `.claude/skills/`.**
> Estrutura espelhada na skill irmã `wfs-fetcher`. Itens `TODO` exigem leitura de
> `services/integrations/wms/` e da SPEC `SPECS/ingestao_dados/002-wms-fetcher.md`.

# WMS Fetcher — `services.integrations.wms`

Cliente WMS reutilizável, tipado e agnóstico de Django, para as camadas base do mapa
(GeoSampa hoje, MDSF depois).

## Regras de fronteira (não violar)

- **O domínio nunca lê settings.** Config de conexão chega por DTOs injetados; quem lê
  `settings` é a orquestração (view/command). Mesmo padrão do `wfs-fetcher`.
- **Importe sempre pelo nível superior** `services.integrations.wms` — nunca submódulos internos.
- **Não monte URLs/params WMS à mão.** TODO: confirmar o DTO de request exposto.

## O que é exportado

```python
# TODO: confirmar no __init__.py real
from services.integrations.wms import (...)
```

## Uso básico

TODO: exemplo mínimo real (config de conexão + request + chamada), espelhando o `wfs-fetcher`.

## Bordas conhecidas (documentar a partir do histórico)

- **Ortofoto barrando a requisição:** houve correção real no fluxo WMS da ortofoto
  (commit `cbc2483` — "arrumando problema na requisicao pro geosampa - tanto no wms para a
  ortofoto que tava barrando..."). TODO: registrar aqui **qual era o problema e qual o formato
  correto da requisição**, para o erro não voltar. Esta é a principal razão de existir desta
  skill.
- TODO: relação com o partial do mapa — o que vem do settings (`WMS_*`?) e chega ao Leaflet via
  contexto (`apps/mapping/context.py`), conforme a skill `leaflet-map` ("URL e layers vêm do
  servidor").

## Erros e resiliência

TODO: exceções próprias expostas (equivalentes a `WfsHttpError` etc.?) e política de
timeout/retry, se houver.

## Notas de teste

TODO: espelhar o padrão da `wfs-fetcher` (mockar `requests.get`; nunca bater na rede).
