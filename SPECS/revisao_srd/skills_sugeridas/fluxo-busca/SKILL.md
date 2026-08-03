---
name: fluxo-busca
description: O padrão arquitetural do fluxo de busca única do DIMAP GeoCoder — filtro regex de roteamento, view roteadora, seções de sugestão por tipo de entrada e partials de resultado. Use SEMPRE que for adicionar um novo tipo de entrada reconhecida, alterar o roteamento, criar/alterar uma seção de sugestões ou entender por que uma entrada cai num fluxo e não noutro.
---

> **RASCUNHO — validar contra o código antes de promover a `.claude/skills/`.**
> Fontes: `services/domain/roteamento_busca/`, `apps/search/` (views + `secoes.py`),
> `apps/lote_matcher/secoes.py` e as 14 SPECs de `SPECS/roteamento_busca/`.

# Fluxo da busca única — o padrão "filtro → roteador → seção → partial"

A barra única aciona um pipeline com papéis fixos. Estender a busca (novo tipo de entrada, nova
regra de sugestão) é **compor uma peça nova em cada papel**, nunca inventar outro desenho.

## O desenho

```
keyup (HTMX, delay/changed)
  → view roteadora (apps/search)
      → services.domain.roteamento_busca: FILTROS regex identificam o tipo da entrada
          (contribuinte / codlog / nome de logradouro / endereço com número / endereço de lote)
      → SEÇÃO de sugestão do tipo identificado (secoes.py do app dono do domínio)
          → domínio consulta o catálogo cacheado (skill catalogos-lookup)
          → partial de sugestões renderizado
  → clique na sugestão OU commit (Enter) sem seleção
      → match exato (códigos) ou fuzzy fallback (texto — skill fuzzy-matcher)
      → app geocoder correspondente resolve a geometria
      → partial do mapa (skill leaflet-map)
```

TODO: confirmar nomes reais dos papéis (filtro? seção? roteador?) e a ordem de precedência
entre filtros (uma entrada que casa dois filtros vai para qual?).

## Onde vive cada papel

| Papel | Onde | Regra |
|---|---|---|
| Filtro de tipo (regex) | `services/domain/roteamento_busca/` (TODO: confirmar) | padrões regex em `services/utils`? TODO |
| View roteadora | `apps/search/views.py` | só orquestra: DTO → domínio → partial |
| Seção de sugestão | `secoes.py` do app do domínio (`apps/search/secoes.py`, `apps/lote_matcher/secoes.py`) | TODO: contrato exato de uma "seção" |
| Sugestões | catálogos cacheados | nunca ORM/parquet direto |
| Fuzzy fallback no commit | TODO (SPECs 013/014) | só para texto livre; códigos são exatos |

## Como adicionar um novo tipo de entrada (checklist)

1. TODO: escrever o passo a passo real observando como as SPECs 002 (filtro-contribuinte) →
   006 (secao-contribuinte) compõem as peças — é o exemplo canônico de ponta a ponta.
2. Regra que já se sabe: o filtro novo **não** decide sozinho o desenho — escreva a SPEC antes
   (CLAUDE.md §4) e reutilize seção/partials existentes por composição.

## Casos especiais já resolvidos (não reinventar)

- **Endereço fiscal exato** → pop-up ponto vs. polígono (SPECs `roteamento_busca/009`/`010`).
- **Info de condomínio nas sugestões** (SPECs 011/012).
- **Feedback de seleção no Enter rápido** (SPEC `design/002`).
- **Fuzzy fallback no commit** para endereço e endereço de lote (SPECs 013/014).

TODO: para cada caso, uma frase sobre onde a decisão mora no código.
