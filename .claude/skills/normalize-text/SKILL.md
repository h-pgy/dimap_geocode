---
name: normalize-text
description: Como usar a função de normalização de texto do DIMAP GeoCoder (services.utils.normalization). Use esta skill SEMPRE que o código precisar limpar, normalizar ou preparar texto para matching/comparação — nunca crie uma função nova para isso.
---

# Normalização de texto — `services.utils.normalization`

## Regra inegociável

**Nunca escreva uma função de limpeza ou normalização de texto.** A função já existe e deve ser
reutilizada em qualquer ponto do sistema — tanto na **preparação dos dados** (scripts de ingestão,
geração de variações) quanto no **momento da consulta** (matching, comparação de strings).

Isso é crítico: se a preparação e a consulta usarem normalizações diferentes, o matching quebra
silenciosamente.

## O que é exportado

```python
from services.utils.normalization import normalize_text
```

`normalize_text` é uma instância callable de `TextNormalizer`. Recebe `str`, devolve `str`.

## O que ela faz 

Execute funções pré-definidas de normalização de texto como:
- Remover acentos
- Remover caracteres especiais
- Remover pontuação
- Deixar tudo upper case

```python
normalize_text("Av. João Pessoa, 123")  # → "AV JOAO PESSOA 123"
normalize_text("rua ação")              # → "RUA ACAO"
normalize_text("R. Barão D'Ávila")     # → "R BARAO D AVILA"
```

## Uso

```python
from services.utils.normalization import normalize_text

# ao preparar uma chave de lookup
chave = normalize_text(nome_oficial)

# ao receber input do usuário
entrada = normalize_text(texto_digitado)

# comparação - exemplo simples com ==, normalmente será um regex ou fuzzy
if normalize_text(a) == normalize_text(b):
    ...
```

Importe **sempre pelo nível superior** `services.utils.normalization` — não alcance
`services.utils.normalization.normalizer` diretamente.
