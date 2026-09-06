---
name: seeds
description: Padrão de carga de catálogos versionados (cargos, unidades, tipos de impedimento, ...) do DIMAP GeoCoder. Use ao criar ou alterar uma seed — arquivo em data/seed/, submódulo apps/<app>/seeds/ e o management command que a dispara.
---

# Seeds — carga de catálogo versionado em `data/seed/`

## O padrão, em 3 peças

1. **`data/seed/<nome>.json`** — o dado, versionado no git. Nunca em `services/`: dado ≠ código (§5).
2. **`apps/<app>/seeds/<nome>.py`** — a carga. DTOs Pydantic validam o arquivo
   (`ArquivoSeed...`), função pública `carregar_seed_<nome>(*, dry_run: bool = False) -> ContagemSeed`.
   `apps/<app>/seeds/__init__.py` **só reexporta**.
3. **`apps/<app>/management/commands/seed_<nome>.py`** — comando fino que chama a carga.

## Por que a carga vive no `app`, não em `services/`

`services/` **não depende do Django** (§3.3) — mas a carga grava direto nos models do app, que é
persistência pura. Se a única regra em jogo já está no `clean()`/constraint do model, não há
domínio a isolar: é orquestração + persistência, e fica em `apps/<app>/seeds/`, importando os
models do próprio app livremente.

Se a carga precisar de lógica de domínio de verdade (geocodificação, matching, geometria), essa
lógica é de `services/domain/` como qualquer outra — a seed só a chama e persiste o resultado.

## Idempotência (obrigatória): a seed **só cria o que falta**

Toda seed roda contra **chave natural** (`sigla`, `nome`) e pode ser reexecutada à vontade — o
container roda as seeds a cada subida. Registro que já existe é **deixado intacto**: a seed nunca
reescreve campo, nem religa vínculo, nem apaga.

*Por quê:* a seed é bootstrap, não sincronização. Depois da primeira carga a fonte de verdade do
catálogo é o banco — o cadastro edita, transfere e extingue pela tela —, e uma seed que atualizasse
o registro existente desfaria isso a cada `docker compose up`. Corolário assumido: **editar o JSON
não propaga para banco já carregado**; mudar registro que existe é ato administrativo, feito na
tela.

- Sem validação em jogo: `if Model.objects.filter(chave=valor).exists(): continue`, depois
  `Model.objects.create(...)`.
- Com `full_clean()` em jogo: **nunca** `create`/`get_or_create` direto — grava antes da validação
  rodar. Pule o que existe, monte em memória e só então valide:
  ```python
  if Model.objects.filter(chave=valor).exists():
      continue
  obj = Model(
      chave=valor,
      campo=novo_valor,
  )
  obj.full_clean()
  obj.save()
  ```
- **Exclusão lógica muda a busca.** Se o model tem manager padrão que filtra o registro apagado
  (`Unidade.objects` esconde as extintas), a checagem de existência **tem** que usar o manager sem
  filtro (`Unidade.todas`) — senão o apagado parece ausente, a seed tenta recriá-lo e o `unique`
  derruba a subida inteira do container.
- Se houver hierarquia (pai/filho, veda de tipos), grave tudo **sem** o vínculo primeiro e ligue
  numa segunda passada — a ordem do arquivo deixa de importar. A segunda passada percorre **só o
  que a primeira criou**: religar registro preexistente o arrastaria de volta para o arquivo.
- A `ContagemSeed` devolvida conta o que foi **criado**, não o tamanho do arquivo — é o número que
  diz se a carga fez algo.

Toda a carga — **as duas passadas incluídas** — roda dentro de um único `transaction.atomic()`.
Isso é o que garante a idempotência: se a segunda passada encontrar uma veda/vínculo inválido
(ex. pai por sigla inexistente, tipo-filho vedado), a exceção estoura **depois** da primeira
passada já ter gravado registros novos — sem o `atomic()` envolvendo as duas, esses registros
ficariam persistidos e a carga já não seria mais idempotente (reexecutar não devolveria o banco ao
mesmo estado). O rollback é automático — `atomic()` desfaz tudo ao propagar a exceção; a seed não
faz `try/except` para isso. `dry_run=True` usa o mesmo mecanismo, só que força o rollback mesmo
sem erro (`transaction.set_rollback(True)` no fim) — o caminho de validação é idêntico ao da carga
real, nada persiste.

## O management command: erros semânticos

O comando (skill `management-commands`) só faz parsing, chama a função de carga e formata o
stdout — mas aqui ele também é a fronteira de erro: captura as exceções de validação da carga
(`ValidationError`, e `ObjectDoesNotExist` quando a seed referencia chave inexistente, ex. pai por
sigla) e as relança como `CommandError("carga abortada: ...")`. Quem roda o comando no terminal
nunca vê traceback — vê por que a carga parou.

```python
try:
    resultado = carregar_seed_x(dry_run=dry_run)
except (ObjectDoesNotExist, ValidationError) as exc:
    raise CommandError(f"carga abortada: {exc}") from exc
```

Expõe `--dry-run` sempre.

## Testes

Alvo: `tests/apps/<app>/test_seed_<nome>.py`, exercitando `carregar_seed_<nome>` diretamente
(nunca o management command — comando fino não tem comportamento próprio a fixar, skill
`management-commands`).

**Marcadores:** `@pytest.mark.banco` + `@pytest.mark.django_db` em todo teste. A idempotência e as
validações que a carga protege moram no `clean()`/constraint do model — não dá pra fixar esse
comportamento sem persistir de verdade, então o teste roda contra o **banco de teste do
pytest-django**: um PostGIS descartável, criado e migrado para a suíte e apagado no fim, isolado
da base de desenvolvimento/produção. `banco` é deselecionado por padrão (`pyproject.toml`) porque
exige esse banco de pé — rode com `pytest -m banco` (ou sem o `-m 'not banco'` do `addopts`).

**Setup:** cada teste escreve seu próprio JSON de seed, não lê o de `data/seed/`:
```python
write_json_to_folder(subpasta_de_data("seed"), "<nome>.json", {...})
```
O fixture `autouse` de `tests/conftest.py` redireciona `data_dir()` para um diretório temporário
por teste — isso já acontece sozinho, o teste não precisa (nem deve) mockar nada para não tocar no
`data/seed/` real.

**Os quatro casos essenciais** (§9 — nem mais, nem menos, cada um fixa uma garantia distinta do
padrão):

1. **Carga cria os registros do arquivo** — o caso feliz: escreve o JSON, chama
   `carregar_seed_<nome>()`, confere os campos gravados.
2. **Carga não toca registro existente** — chama `carregar_seed_<nome>()`, reescreve o JSON com
   dado **alterado** nas mesmas chaves naturais, chama de novo. Confere que a contagem final de
   registros não dobrou (nada duplicou) e que os campos seguem os da **primeira** escrita (o
   registro foi ignorado, não atualizado). Se o model tiver exclusão lógica, um caso a mais: o
   registro apagado sobrevive à carga seguinte, sem duplicar, sem estourar o `unique` e sem
   reviver.
3. **Registro inválido aborta sem gravar nada** — escreve um JSON em que algum registro fura a
   validação do model (ou, se houver segunda passada de vínculo, um vínculo para chave
   inexistente). Chama a carga esperando a exceção (`pytest.raises`) e confere que **nenhum**
   registro do arquivo foi persistido — inclusive os que vieram *antes* do inválido na primeira
   passada. É este teste que teste a garantia do `transaction.atomic()` único cobrindo as duas
   passadas, discutida acima.
4. **`dry_run=True` não persiste** — mesmo JSON válido do caso 1, mas chamando com
   `dry_run=True`; confere que nenhum registro foi gravado.
