---
spec: roteamento-busca/001
versao: v4
atualizado_em: 2026-06-24
changelog:
  - v1: versão inicial
  - v2: (1) aplica normalize_text no input; (2) parses ricos (setor/quadra/lote/DV;
        codlog 5+DV; tipo_logradouro/nome/numero) com placeholders de cálculo de DV;
        (3) parseamento parcial com flag de completude por atributo e por identificador;
        (4) status do resultado em enum, incluindo IMPOSSIVEL e VAZIO; (5) match exato é
        UNICO (não-candidato); (6) ponto de extensão de regras de validação além do regex.
  - v3: remove TODA normalização de texto deste módulo (delegada ao matcher a jusante) e
        remove a separação tipo_logradouro/nome — o texto do logradouro fica inteiro, como
        digitado, e o matcher resolve. Códigos desambiguam por `.`/`-` + nº de dígitos sobre
        o texto bruto. Demais decisões de v2 (parses ricos, parcial, status, único,
        extensão) mantidas.
  - v4: o domínio VOLTA a separar tipo_logradouro de nome (parse estrutural, SEM normalizar),
        inclusive identificando input só com nome (ex.: "paulista"); LOGRADOURO só é completo
        com tipo + nome. Exige tornar opcional o split do LogradouroMatcher (flag fazer_split)
        e ampliar LogradouroMatchQuery com tipo_logradouro/nome já separados. Adiciona a
        máscara do codlog no parser (`\d{5}-\d{1}` quando há DV).
  - v5: EnderecoParse passa a COMPOR um LogradouroParse (endereço "contém" um logradouro);
        endereço só é completo com tipo + nome + número.
  - v6: RoteamentoQuery ganha `finished_typing`; quando True, o tipo de logradouro deixa de ser
        obrigatório para LOGRADOURO/ENDERECO serem completos (ex.: "paulista" + Enter = nome de rua
        completo sem tipo). Threaded como `entrada_finalizada` no LogradouroParse. Códigos não são
        afetados (completude por nº de dígitos).
  - v7: remove a camada de wrappers `Candidato*` (eram redundantes — `formato_completo` era sempre
        `parse.completo`). O discriminador `tipo` passa para o próprio `*Parse`: cada parse É o
        candidato. `Candidato` vira a união discriminada dos parses; usa-se `.completo` (não mais
        `formato_completo`).
---

# SPEC roteamento-busca/001 — Roteador de Entrada (classifica o texto da barra única)

## User story

Como usuário, quero digitar **qualquer coisa** na barra de pesquisa única — número de
contribuinte, codlog, nome de rua ou endereço completo, do jeito que eu souber escrever — e que o
sistema **descubra sozinho** o que eu quis dizer, para que ele acione a busca certa (lote, logradouro
ou geocodificação) sem eu precisar dizer qual é o tipo.

Como a barra também aciona **sugestões em tempo real** enquanto eu digito (com um *delay*), quero
que, mesmo com a entrada **incompleta**, o sistema me diga **quais tipos ainda são plausíveis** e o
que já deu para parsear — por exemplo, ao digitar só `20`, que ele entenda que pode ser um
contribuinte cujo **setor** começa com 20 **ou** um codlog que começa com 20 (mas nunca uma rua,
pois rua não começa com dígito); e ao digitar `rua itat`, que entenda que é busca por logradouro
(sugerir ruas que começam com "itat"), e não um endereço. E quando o que digitei **fecha 100%** um
único tipo, quero que o resultado diga claramente que é **aquilo**, sem ambiguidade.

## Critérios de aceite

- [ ] Código implementado num submódulo de domínio em `services/domain/` (sugestão:
      `services/domain/roteamento_busca`), **sem nenhum import de Django** (§3.3, §7.3).
- [ ] O `__init__.py` expõe apenas a **instância callable** do orquestrador, os **enums** e os
      **DTOs** de entrada/saída; submódulos internos (identificadores) não são alcançados de fora.
- [ ] O orquestrador é uma **classe callable** que recebe um DTO Pydantic com o texto e devolve um
      DTO Pydantic com o resultado.
- [ ] Existem **quatro identificadores**, cada um numa **classe callable em arquivo `.py` próprio**:
      contribuinte, codlog, logradouro (nome de rua) e endereço. O orquestrador os integra por
      **composição** (§10.4) — chama cada um e agrega os candidatos.
- [ ] **Nenhuma normalização de texto neste módulo.** O roteador **não** chama `normalize_text` nem
      reimplementa limpeza/normalização. Os textos seguem para o resultado **como digitados**
      (casing/acentos preservados); quem normaliza para matching é o `logradouros_match` a jusante
      (§7.1, §11). Para **códigos**, remover `.`/`-`/espaços é **parsing estrutural de código
      numérico**, não normalização de texto. **Separar tipo↔nome é parsing estrutural** (quebra por
      espaço), também não é normalização.
- [ ] **Separa tipo de logradouro do nome (parse estrutural).** Tanto em LOGRADOURO quanto em
      ENDERECO, o texto do logradouro é quebrado no **primeiro espaço**: 1º token = `tipo_logradouro`,
      o resto = `nome` (espelha a lógica de `LogradouroMatcher._split`, **sem normalizar**). Quando o
      usuário digita **só o nome** (um único token, ex.: `paulista`), `tipo_logradouro` fica vazio e o
      token vira `nome`.
- [ ] **LOGRADOURO só é completo com `tipo_logradouro` E `nome`** — **exceto** quando a entrada foi
      finalizada (ver `finished_typing`). Input só com nome (ex.: `paulista`) **sem** finalizar é
      LOGRADOURO **parcial** (`completo=False`); `avenida paulista` é completo.
- [ ] **`finished_typing` (vem da DTO de input).** Quando `True`, o roteador conclui que a entrada
      está fechada e o **tipo de logradouro deixa de ser obrigatório**: `paulista` + finalizado é
      LOGRADOURO **completo** (nome de rua sem tipo); `paulista, 300` + finalizado é ENDERECO
      **completo**. Como o módulo chega a esse `True` (Enter no front etc.) **não importa** aqui.
      **Códigos não são afetados** (completude continua por nº de dígitos).
- [ ] **Parses fazem o parse de verdade**, em campos estruturados:
      - **Contribuinte:** `setor` (3 díg.), `quadra` (3), `lote` (4) e `dv` (2 díg. verificadores,
        **opcionais**), com `mascara` (`001.001.0004-01`). Placeholder `calcular_dv()` para o DV.
      - **Codlog:** `codlog` (5 díg.) e `digito_verificador` (1 díg., **opcional**), com `mascara`
        (`16321-0` quando há DV; `16321` quando não). Placeholder `calcular_dv()` para o DV.
      - **Logradouro:** `tipo_logradouro` e `nome` (como digitados).
      - **Endereço:** **compõe** um `LogradouroParse` (campo `logradouro`) **+** `numero` — o
        endereço *contém* um logradouro (§10.4).
- [ ] **Parseamento parcial com flags de completude.** Cada parse expõe completude **por atributo**
      (ex.: `setor_completo`, `lote_completo`) **e** uma flag agregada `completo` ("fechou 100%").
      Digitar `20` produz um contribuinte com `setor="20"` (`setor_completo=False`, `completo=False`)
      e um codlog com `codlog="20"` (`completo=False`).
- [ ] **Status do resultado em enum**, incluindo o caso **impossível**: `RoteamentoStatus` com
      `UNICO` (1 interpretação), `AMBIGUO` (2+), `IMPOSSIVEL` (texto não-vazio que não casa com nada —
      ex.: 25 dígitos) e `VAZIO` (entrada vazia/só espaços).
- [ ] **Match exato é único, não candidato.** Quando o input determina **um só** tipo, o status é
      `UNICO` e o acessor `match` devolve essa única interpretação. Endereço, rua, contribuinte e
      codlog **não se confundem** quando exatos; a ambiguidade só ocorre em **prefixo de código**.
- [ ] **Extensível além do regex.** Cada identificador tem um **ponto de extensão de regras de
      validação** (sequência componível) aplicado **depois** do parse estrutural, para lógica de
      domínio futura (ex.: "não existe setor começando com dígito > 4 ⇒ se começa com 5 não é
      contribuinte, é codlog"). Na entrega as regras vêm vazias/placeholder.
- [ ] **Mudança no matcher a jusante (`logradouros_match`).** Como o roteador já entrega
      `tipo_logradouro` e `nome` **separados**, o `LogradouroMatcher` não deve repetir o split. Para
      não remover `_split` de vez (a busca detalhada e outros chamadores ainda passam texto único), a
      decisão de splitar vira **flag** no input: `LogradouroMatchQuery` ganha `tipo_logradouro` e
      `nome` (já separados) e uma flag `fazer_split` — quando `False`, o matcher usa os campos
      separados e **pula** `_split`; quando `True`, mantém o comportamento atual sobre `texto`.
      (`001.001.0004`, `001.001.0004-01`, `0010010004`, `001001000401`, `001 001 0004`) → mesmos
      dígitos canônicos. `completo` quando há 10 dígitos (núcleo); DV (2) opcional/derivável. Acima
      de 12 dígitos é rejeitado. A presença de **ponto** confirma contribuinte; o traço na posição de
      DV de codlog (`\d{1,5}-\d`, ex.: `16321-0`) **não** é contribuinte.
- [ ] **Codlog** é reconhecido como `163210` ou `16321-0` → mesmos 5 dígitos + DV. `completo` aos 5
      dígitos de codlog; DV (1) opcional/derivável. **Ponto** rejeita (é contribuinte) e mais de 6
      dígitos rejeita (é contribuinte).
- [ ] Entrada **só de dígitos** pode produzir **dois candidatos** (contribuinte **e** codlog) quando
      é prefixo ambíguo (≤ 6 dígitos sem ponto). De 7 a 12 dígitos ⇒ só contribuinte. Acima ⇒ nada.
- [ ] Texto que **começa por letra** e **não tem número de imóvel** ⇒ **LOGRADOURO**. Com número de
      imóvel ⇒ **ENDERECO** (`logradouro` + `numero`), **descartando** tudo após o número
      (bairro/cidade). **LOGRADOURO e ENDERECO são mutuamente exclusivos**.
- [ ] Entrada que **começa por dígito nunca** produz LOGRADOURO/ENDERECO. Nomes de rua que **contêm**
      números mas **não têm** número de imóvel (ex.: `rua 25 de março`) permanecem **LOGRADOURO**.
- [ ] Tipagem integral; `mypy` limpo.

## Contexto e decisões de arquitetura

**Camada.** Mexe **exclusivamente** no domínio (`services/domain/`). É o "regex de roteamento" do §9
que decide o **tipo** da entrada antes de despachar ao matcher correspondente. Não toca views,
models, management commands nem integrações.

**Responsabilidade única (§10.1) e composição (§10.4).** Cada tipo de entrada é um domínio de
reconhecimento distinto → um **identificador próprio** (classe callable, um arquivo). O
**orquestrador** não reimplementa regra: **compõe** os quatro identificadores e agrega o resultado.
Estilo de pipeline segmentado, como `LogradouroMatcher`/`TextNormalizer`.

**Parseia a estrutura, mas não normaliza (decisão v4).** A fronteira deste módulo:

- **Não normaliza texto.** `normalize_text` faria upper/sem-acento **e colapsaria `.`, `-` e `,`
   em espaço** — destruindo justamente os separadores que distinguem um codlog (`16321-0`) de um
   contribuinte (`001.001...`) e a vírgula que separa o número do complemento no endereço. Além
   disso, o `logradouros_match` **já normaliza** a query internamente (via `fuzzy_match`). Portanto o
   roteador trabalha sobre o **texto bruto** e entrega os textos **como digitados**; a normalização
   acontece **uma vez**, no matcher (§7.1, §11). (Remover `.`/`-`/espaços para extrair os dígitos de
   um **código** não é normalização de texto — é parsing do código.)
- **Separa tipo do nome do logradouro (parse estrutural, sem normalizar).** O roteador quebra o
   texto do logradouro no **primeiro espaço** (1º token = `tipo_logradouro`, resto = `nome`),
   identificando inclusive quando o usuário digitou **só o nome** (`tipo_logradouro` vazio). É a mesma
   regra hoje embutida em `LogradouroMatcher._split`, agora feita **uma vez** no roteador e entregue
   pronta. **Consequência:** o matcher passa a **não** splitar quando recebe os campos já separados —
   ver "Mudança necessária no matcher" abaixo. A **resolução** do tipo (fuzzy) continua no matcher;
   o roteador só faz a **quebra estrutural**.

**LOGRADOURO completo = tipo + nome.** Como a quebra é estrutural, "só o nome" (ex.: `paulista`) é um
LOGRADOURO **parcial** (`completo=False`) — sinaliza ao consumidor que ainda falta o tipo para fechar
a entrada. Com tipo + nome (`avenida paulista`), `completo=True`.

**ENDERECO contém um LOGRADOURO.** Modelado por **composição** (§10.4): `EnderecoParse` carrega um
`LogradouroParse` (campo `logradouro`) + `numero`. Logo, o endereço só é **completo** quando o
logradouro está completo **e** há número — `completo = logradouro.completo and bool(numero)`. Assim,
`paulista 3` (sem tipo) é ENDERECO **parcial**; `avenida paulista 3` é completo.

**`finished_typing` relaxa a exigência de tipo.** O flag vem na `RoteamentoQuery` e é threaded para o
`LogradouroParse` como `entrada_finalizada`. A regra de completude do logradouro vira: `nome`
presente **e** (`tipo_logradouro` presente **ou** entrada finalizada). Ou seja, com a digitação
fechada, "só o nome" basta (`paulista` + Enter = nome de rua completo, sem tipo), e o endereço herda
isso automaticamente (o `LogradouroParse` interno carrega o flag). Sem finalizar, mantém-se a
exigência de tipo + nome — útil para sugestões em tempo real, em que ainda não se sabe se o usuário
vai digitar o tipo. **Os códigos ignoram** `finished_typing`: 8 dígitos seguem parciais com ou sem
Enter, pois lá a completude é estrutural (nº de dígitos). A decisão de roteamento (quantos candidatos,
status) **não** muda com o flag — ele só afeta a flag de completude.

**Códigos — desambiguação por separador + nº de dígitos (sobre o bruto):**

- **Ponto** presente ⇒ é **contribuinte** (codlog não tem ponto).
- **Traço na posição de DV de codlog** (`\d{1,5}-\d`, ex.: `16321-0`) ⇒ é **codlog** (não
  contribuinte).
- Removidos `.`/`-`/espaços, sobra a string de **dígitos**: `≤ 6` ⇒ pode ser **ambos** (codlog e
  contribuinte parcial); `7..12` ⇒ só **contribuinte**; `> 12` ⇒ **nada**. Para codlog, `> 6` díg.
  rejeita.

O parse fatia os dígitos por posição (contribuinte `setor=[0:3] quadra=[3:6] lote=[6:10] dv=[10:12]`;
codlog `[0:5]` + DV `[5:6]`), o que dá o **parcial** de graça e a **completude por atributo**. Os
**dígitos verificadores** são **opcionais/deriváveis**: cada parse de código traz um **placeholder**
`calcular_dv()` (`NotImplementedError`) para o algoritmo futuro.

**Status: único, ambíguo, impossível, vazio.** O resultado sempre carrega a lista de candidatos, mas
expõe um **enum de status** com o desfecho: `UNICO` (tipo determinado — match "exato" de roteamento;
o valor pode ainda ser parcial, ex.: contribuinte de 8 dígitos; acessor `match` devolve o único),
`AMBIGUO` (2+, sempre prefixo de código), `IMPOSSIVEL` (não-vazio sem nenhuma interpretação),
`VAZIO` (vazio/só espaços). Isso atende ao "quando é exato, é uma coisa só, não candidato":
rua/endereço/contribuinte/codlog não se confundem quando exatos.

**Extensão além do regex.** Cada identificador segue **parse estrutural → regras de validação →
monta candidato**. As "regras" são uma sequência **componível** (`tuple` de callables que recebem o
parse e devolvem `bool`), injetável no construtor, com default numa constante do módulo (hoje
vazia). É o gancho para regras de domínio futuras — ex.: uma regra do contribuinte "setor não começa
com dígito > 4" que, ao reprovar, faz o contribuinte **não** disparar, sobrando só o codlog na
desambiguação. Como operam sobre o **parse estruturado**, a lógica fica expressiva e desacoplada do
regex.

**Logradouro × Endereço — exclusão mútua via composição.** Compartilham um **único** extrator
`(logradouro, numero) | None` sobre o bruto: ENDERECO dispara quando há número; LOGRADOURO quando
**não** há (e começa por letra). Sem duplicar heurística e sem disparo duplo.

**Heurística do número de imóvel (sobre o bruto):**
1. Quebra no **primeiro** `,` em `head` e `resto`.
2. Se o **último token** de `head` for número (`\d+[A-Za-z]?`) e houver nome antes → é o `numero`;
   o texto do logradouro = `head` sem o último token.
3. Senão, se o **primeiro token** de `resto` for número → é o `numero`; o texto do logradouro = `head`.
4. Senão → **não há** número de imóvel (LOGRADOURO).

Acerta `avenida paulista 3`, `avenida paulista, 3`, `avenida paulista, 3, consolação, são paulo`
(descarta o resto) e protege ruas numeradas: `rua 25 de março` (LOGRADOURO) vs `rua 25 de março, 100`
e `rua 25 de março 100` (ENDERECO). O **texto do logradouro** assim obtido (ou o input inteiro, no
caso LOGRADOURO) passa pela quebra estrutural `tipo_logradouro` ↔ `nome` (1º espaço).

**Mudança necessária no matcher (`logradouros_match`).** O `LogradouroMatcher` hoje recebe um texto
único e faz a quebra tipo↔nome em `_split`. Como o roteador passa a entregar esses campos **já
separados**, o matcher não deve repetir a quebra. Em vez de **remover** `_split` (a **busca
detalhada** e outros chamadores ainda mandam texto único), a quebra vira **opcional via flag**:

- `LogradouroMatchQuery` ganha os campos `tipo_logradouro: str | None` e `nome: str | None` (já
  separados) e uma flag `fazer_split: bool` (default `True`, preservando o comportamento atual).
- No pipeline do matcher, quando `fazer_split=False`, usa-se `tipo_logradouro`/`nome` diretamente e
  **pula-se** `_split`; quando `True`, mantém-se o split sobre `texto`. (Tratar `tipo_logradouro`
  vazio/`None` como o caminho *fast-forward* "sem tipo", igual hoje.)
- A **busca detalhada** (campos segmentados) também passa a montar a query com `fazer_split=False`,
  reaproveitando o mesmo caminho — daí manter o `_split`, e não removê-lo, valer a pena.

> Esta mudança toca a SPEC `match-logradouros/004`; ao implementar, registrar lá o *patch*
> correspondente (input DTO + flag de split).

**Regex/parsers compartilhados.** As constantes de regex de cada **código** ficam no arquivo do seu
identificador (§10.3, fonte única do formato — §10.1). Os **helpers de texto** compartilhados por
LOGRADOURO e ENDERECO (detecção de número e quebra tipo↔nome) ficam num pequeno módulo interno do
submódulo (evita import circular entre `logradouro.py` e `endereco.py`).

**Contratos (§3.3, §10.4).** Entrada/saída do orquestrador são DTOs Pydantic; a lista `candidatos` é
uma **união discriminada** por `tipo` cujos membros são os **próprios `*Parse`** — cada parse carrega
seu discriminador `tipo` e **é** o candidato (sem camada de wrapper). A completude de cada candidato é
o seu `.completo`.

## Peças de referência a compor

- `@services/domain/logradouros_match` → `match_logradouro` / `LogradouroMatchQuery` /
  `LogradouroMatcher._split`: **consumidor** dos candidatos LOGRADOURO/ENDERECO e alvo da **mudança**
  desta SPEC (input DTO com `tipo_logradouro`/`nome`/`fazer_split`). É ele quem **normaliza** e
  **resolve** o tipo por fuzzy (por isso o roteador faz só a quebra estrutural, sem normalizar). A
  lógica de `_split` é a **referência** para a quebra feita aqui.
- `@services/utils/normalization` → `normalize_text`: **não** é usada aqui — citada só para deixar
  explícito que a normalização é **delegada ao matcher**, mantendo normalização única (§7.1, §11).

## Snippets sugeridos

Organização sugerida (direção, adaptável sem violar §3/§10): `models.py` (enums + DTOs),
`contribuinte.py`, `codlog.py`, `endereco.py`, `logradouro.py`, `parsing.py` (helpers de texto
compartilhados), `router.py`, `__init__.py`.

DTOs e enums (`models.py`):

```python
from enum import StrEnum
from typing import Annotated, Literal
from pydantic import BaseModel, Field, computed_field


class TipoEntrada(StrEnum):
    CONTRIBUINTE = "contribuinte"
    CODLOG = "codlog"
    LOGRADOURO = "logradouro"
    ENDERECO = "endereco"


class RoteamentoStatus(StrEnum):
    UNICO = "unico"            # 1 interpretação (tipo determinado)
    AMBIGUO = "ambiguo"        # 2+ interpretações (prefixo de código)
    IMPOSSIVEL = "impossivel"  # texto não-vazio que não casa com nada
    VAZIO = "vazio"            # entrada vazia / só espaços


# ---- parses (fazem o parse de verdade; cada um carrega o discriminador `tipo` e É o candidato) ----
class ContribuinteParse(BaseModel):
    tipo: Literal[TipoEntrada.CONTRIBUINTE] = TipoEntrada.CONTRIBUINTE
    setor: str          # até 3 dígitos
    quadra: str         # até 3
    lote: str           # até 4
    dv: str             # até 2 (verificadores; "" quando ausente)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def setor_completo(self) -> bool: return len(self.setor) == 3
    @computed_field  # type: ignore[prop-decorator]
    @property
    def quadra_completo(self) -> bool: return len(self.quadra) == 3
    @computed_field  # type: ignore[prop-decorator]
    @property
    def lote_completo(self) -> bool: return len(self.lote) == 4
    @computed_field  # type: ignore[prop-decorator]
    @property
    def dv_completo(self) -> bool: return len(self.dv) == 2

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completo(self) -> bool:           # "fechou 100%" o núcleo (DV é derivável)
        return self.setor_completo and self.quadra_completo and self.lote_completo

    @property
    def digitos(self) -> str:
        return f"{self.setor}{self.quadra}{self.lote}{self.dv}"

    @property
    def mascara(self) -> str:             # display progressivo: "001.001.0004-01"
        base = ".".join(p for p in (self.setor, self.quadra, self.lote) if p)
        return f"{base}-{self.dv}" if self.dv else base

    def calcular_dv(self) -> str:         # placeholder p/ algoritmo futuro do DV
        raise NotImplementedError("DV do contribuinte: algoritmo a definir.")


class CodlogParse(BaseModel):
    tipo: Literal[TipoEntrada.CODLOG] = TipoEntrada.CODLOG
    codlog: str                 # até 5 dígitos (o codlog em si)
    digito_verificador: str     # até 1 dígito ("" quando ausente)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def codlog_completo(self) -> bool: return len(self.codlog) == 5
    @computed_field  # type: ignore[prop-decorator]
    @property
    def dv_completo(self) -> bool: return len(self.digito_verificador) == 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completo(self) -> bool:           # DV é derivável
        return self.codlog_completo

    @property
    def mascara(self) -> str:             # "16321-0" com DV; "16321" sem (ou prefixo parcial)
        return f"{self.codlog}-{self.digito_verificador}" if self.digito_verificador else self.codlog

    def calcular_dv(self) -> str:         # placeholder p/ algoritmo futuro do DV
        raise NotImplementedError("DV do codlog: algoritmo a definir.")


class LogradouroParse(BaseModel):
    tipo: Literal[TipoEntrada.LOGRADOURO] = TipoEntrada.LOGRADOURO   # discriminador (≠ tipo_logradouro)
    tipo_logradouro: str        # 1º token, como digitado ("" quando o usuário digitou só o nome)
    nome: str                   # resto, como digitado
    entrada_finalizada: bool = False   # = finished_typing: torna o tipo opcional

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tipo_completo(self) -> bool: return bool(self.tipo_logradouro)
    @computed_field  # type: ignore[prop-decorator]
    @property
    def nome_completo(self) -> bool: return bool(self.nome)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completo(self) -> bool:           # nome + (tipo OU entrada finalizada)
        return self.nome_completo and (self.tipo_completo or self.entrada_finalizada)


class EnderecoParse(BaseModel):
    tipo: Literal[TipoEntrada.ENDERECO] = TipoEntrada.ENDERECO
    logradouro: LogradouroParse   # endereço CONTÉM um logradouro (tipo + nome)
    numero: str                   # número do imóvel ("3", "100", "100A")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completo(self) -> bool:   # completo só com logradouro completo (tipo+nome) E número
        return self.logradouro.completo and bool(self.numero)


# ---- candidato = união discriminada dos próprios parses (sem camada de wrapper) ----
# O discriminador `tipo` em cada parse dá narrowing estático (mypy) e desserialização correta da
# lista heterogênea. A completude é o `.completo` de cada parse (não há `formato_completo` separado).
Candidato = Annotated[
    ContribuinteParse | CodlogParse | LogradouroParse | EnderecoParse,
    Field(discriminator="tipo"),
]


class RoteamentoQuery(BaseModel):
    texto: str
    finished_typing: bool = False   # usuário sinalizou fim da digitação (ex.: Enter no front);
                                     # como se chegou nisso não importa a este módulo


class RoteamentoResult(BaseModel):
    texto: str                      # entrada original (como digitada)
    candidatos: list[Candidato]     # 0, 1 ou 2

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> RoteamentoStatus:
        if not self.candidatos:
            return RoteamentoStatus.VAZIO if not self.texto.strip() else RoteamentoStatus.IMPOSSIVEL
        return RoteamentoStatus.UNICO if len(self.candidatos) == 1 else RoteamentoStatus.AMBIGUO

    @property
    def match(self) -> Candidato | None:    # o único, quando UNICO
        return self.candidatos[0] if len(self.candidatos) == 1 else None

    @property
    def tipos(self) -> list[TipoEntrada]:
        return [c.tipo for c in self.candidatos]
```

Identificador de contribuinte com ponto de extensão de regras (`contribuinte.py`):

```python
import re
from typing import Protocol
from .models import ContribuinteParse

SEPARADORES = re.compile(r"[.\-\s]")
DASH_CODLOG = re.compile(r"\d{1,5}-\d")   # forma "16321-0" -> é codlog, não contribuinte
COMP_LOTE = 10                            # setor(3)+quadra(3)+lote(4)
COMP_COM_DV = 12                          # +DV(2)


class RegraContribuinte(Protocol):
    def __call__(self, parse: ContribuinteParse) -> bool: ...


# ponto de extensão (§6) — vazio por ora.
# Ex. futuro: lambda p: not p.setor or int(p.setor[0]) <= 4   # setor não começa com >4
REGRAS_CONTRIBUINTE: tuple[RegraContribuinte, ...] = ()


class ContribuinteIdentifier:
    def __init__(self, regras: tuple[RegraContribuinte, ...] = REGRAS_CONTRIBUINTE) -> None:
        self._regras = regras

    def __call__(self, texto: str, finished_typing: bool) -> ContribuinteParse | None:
        # finished_typing não afeta códigos (completude é por nº de dígitos)
        bruto = texto.strip()
        if "." not in bruto and DASH_CODLOG.fullmatch(bruto):
            return None                          # forma de codlog -> não é contribuinte
        digitos = SEPARADORES.sub("", bruto)
        if not digitos or not digitos.isdigit() or len(digitos) > COMP_COM_DV:
            return None
        parse = ContribuinteParse(
            setor=digitos[0:3], quadra=digitos[3:6], lote=digitos[6:10], dv=digitos[10:12]
        )
        if not all(regra(parse) for regra in self._regras):
            return None
        return parse
```

Identificador de codlog (`codlog.py`) — mesma forma (regras + parse):

```python
import re
from typing import Protocol
from .models import CodlogParse

DASH_CODLOG = re.compile(r"\d{1,5}-\d")   # "16321-0"
COMP_CODLOG = 6                           # codlog(5) + DV(1)


class RegraCodlog(Protocol):
    def __call__(self, parse: CodlogParse) -> bool: ...


REGRAS_CODLOG: tuple[RegraCodlog, ...] = ()   # ponto de extensão (§6) — vazio por ora


class CodlogIdentifier:
    def __init__(self, regras: tuple[RegraCodlog, ...] = REGRAS_CODLOG) -> None:
        self._regras = regras

    def __call__(self, texto: str, finished_typing: bool) -> CodlogParse | None:
        # finished_typing não afeta códigos (completude é por nº de dígitos)
        bruto = texto.strip()
        if "." in bruto:
            return None                          # ponto -> é contribuinte
        if "-" in bruto and not DASH_CODLOG.fullmatch(bruto):
            return None                          # dash fora da posição de DV de codlog
        digitos = bruto.replace("-", "").replace(" ", "")
        if not digitos or not digitos.isdigit() or len(digitos) > COMP_CODLOG:
            return None                          # >6 -> é contribuinte
        parse = CodlogParse(codlog=digitos[0:5], digito_verificador=digitos[5:6])
        if not all(regra(parse) for regra in self._regras):
            return None
        return parse
```

Helpers de texto compartilhados (`parsing.py`) — detecção de número e quebra tipo↔nome, sem
normalizar (módulo neutro p/ evitar import circular entre `endereco.py` e `logradouro.py`):

```python
import re

COMECA_COM_LETRA = re.compile(r"[^\W\d_]", re.UNICODE)   # 1º char é letra (não dígito)
NUMERO = re.compile(r"\d+[A-Za-z]?")                     # token de número de imóvel


def separar_numero(texto: str) -> tuple[str, str] | None:
    """(texto_do_logradouro, numero) como digitados, ou None se não há nº de imóvel."""
    limpo = texto.strip()
    if not COMECA_COM_LETRA.match(limpo):
        return None
    head, _, resto = limpo.partition(",")
    tokens = head.split()
    if len(tokens) > 1 and NUMERO.fullmatch(tokens[-1]):
        return " ".join(tokens[:-1]), tokens[-1]
    resto_tokens = resto.split()
    if resto_tokens and NUMERO.fullmatch(resto_tokens[0]):
        return head.strip(), resto_tokens[0]
    return None


def split_tipo_nome(texto: str) -> tuple[str, str]:
    """Quebra no 1º espaço: (tipo_logradouro, nome). Token único -> ('', nome). Sem normalizar."""
    partes = texto.strip().split(" ", 1)
    if len(partes) < 2:
        return "", (partes[0] if partes else "")
    return partes[0], partes[1]
```

Identificador de endereço (`endereco.py`) — separa número, quebra tipo↔nome e **compõe** o logradouro:

```python
from .models import EnderecoParse, LogradouroParse
from .parsing import separar_numero, split_tipo_nome


class EnderecoIdentifier:
    def __call__(self, texto: str, finished_typing: bool) -> EnderecoParse | None:
        partes = separar_numero(texto)
        if partes is None:
            return None
        logradouro_txt, numero = partes
        tipo, nome = split_tipo_nome(logradouro_txt)
        return EnderecoParse(
            logradouro=LogradouroParse(
                tipo_logradouro=tipo, nome=nome, entrada_finalizada=finished_typing
            ),
            numero=numero,
        )
```

Identificador de logradouro (`logradouro.py`) — compõe os mesmos helpers:

```python
from .models import LogradouroParse
from .parsing import COMECA_COM_LETRA, separar_numero, split_tipo_nome


class LogradouroIdentifier:
    def __call__(self, texto: str, finished_typing: bool) -> LogradouroParse | None:
        limpo = texto.strip()
        if not COMECA_COM_LETRA.match(limpo):
            return None                              # começa com dígito -> não é rua
        if separar_numero(limpo) is not None:
            return None                              # tem nº de imóvel -> é endereço
        tipo, nome = split_tipo_nome(limpo.rstrip(","))
        if not tipo and not nome:
            return None
        return LogradouroParse(tipo_logradouro=tipo, nome=nome, entrada_finalizada=finished_typing)
```

Orquestrador (`router.py`) — sem normalização; passa o texto bruto a cada identificador:

```python
from typing import Protocol
from .codlog import CodlogIdentifier
from .contribuinte import ContribuinteIdentifier
from .endereco import EnderecoIdentifier
from .logradouro import LogradouroIdentifier
from .models import Candidato, RoteamentoQuery, RoteamentoResult


class Identifier(Protocol):
    def __call__(self, texto: str, finished_typing: bool) -> Candidato | None: ...


class EntradaRouter:
    def __init__(self, identifiers: tuple[Identifier, ...] | None = None) -> None:
        self._identifiers: tuple[Identifier, ...] = identifiers or (
            ContribuinteIdentifier(),
            CodlogIdentifier(),
            LogradouroIdentifier(),
            EnderecoIdentifier(),
        )

    def __call__(self, query: RoteamentoQuery) -> RoteamentoResult:
        bruto = query.texto.strip()
        candidatos = [
            c
            for ident in self._identifiers
            if (c := ident(bruto, query.finished_typing)) is not None
        ]
        return RoteamentoResult(texto=query.texto, candidatos=candidatos)


rotear_entrada = EntradaRouter()
```

Exposição (`__init__.py`):

```python
from .models import (
    Candidato, CodlogParse, ContribuinteParse, EnderecoParse, LogradouroParse,
    RoteamentoQuery, RoteamentoResult, RoteamentoStatus, TipoEntrada,
)
from .router import EntradaRouter, rotear_entrada

__all__ = [
    "rotear_entrada", "EntradaRouter",
    "RoteamentoQuery", "RoteamentoResult", "RoteamentoStatus", "TipoEntrada",
    "Candidato",
    "ContribuinteParse", "CodlogParse", "LogradouroParse", "EnderecoParse",
]
```

Mudança no matcher a jusante (`services/domain/logradouros_match`) — input DTO + flag de split.
Direção sugerida (registrar como *patch* na SPEC `match-logradouros/004`):

```python
# models.py — LogradouroMatchQuery ganha campos separados + flag
class LogradouroMatchQuery(BaseModel):
    texto: str | None = None              # usado quando fazer_split=True
    tipo_logradouro: str | None = None    # já separado (quando fazer_split=False)
    nome: str | None = None               # já separado (quando fazer_split=False)
    fazer_split: bool = True              # default preserva comportamento atual
    limite: int = 5

# matcher.py — pipeline decide se splita
def _pipeline(self, query: LogradouroMatchQuery) -> LogradouroMatchResult:
    if query.fazer_split:
        tipo_token, nome_token = self._split(query.texto or "")
    else:
        tipo_token = query.tipo_logradouro or None   # vazio/None -> fast-forward "sem tipo"
        nome_token = query.nome or ""
    ...  # daqui pra frente, inalterado
```

O roteador (e a busca detalhada) monta a query com `fazer_split=False`, passando o
`tipo_logradouro`/`nome` do parse. `_split` permanece para os chamadores de texto único.

## Fora de escopo

- **Normalização de texto** — delegada ao `logradouros_match` a jusante (decisão v3/v4).
- **Resolução do tipo de logradouro por fuzzy** — é do matcher; aqui só a **quebra estrutural**
  tipo↔nome.
- **Buscar as sugestões** (consultar contribuintes/codlogs por prefixo, ruas por fuzzy). O roteador
  só **classifica e parseia**.
- Resolver a **geometria** de cada tipo.
- O **algoritmo do dígito verificador** (contribuinte e codlog): só placeholders.
- As **regras de validação de domínio** concretas do ponto (6): só o **gancho** existe.
- Views, *partials* HTMX, *management commands*, persistência; **busca detalhada** (tipo já dado).
- Refinamentos de número de imóvel (`s/n`, faixas, `KM`); migração de cache para Redis; testes.

## Notas de teste

Texto preservado + quebra tipo↔nome (sem normalizar):

- `"Avenida Paulista"` → `UNICO` LOGRADOURO, `tipo_logradouro=="Avenida"`, `nome=="Paulista"`
  (casing/acentos como digitados), `completo==True`.
- `"paulista"` (só nome, `finished_typing=False`) → `UNICO` LOGRADOURO, `tipo_logradouro==""`,
  `nome=="paulista"`, `completo==False`.
- `"  Avenida Paulista , 3 "` → `UNICO` ENDERECO, `logradouro.tipo_logradouro=="Avenida"`,
  `logradouro.nome=="Paulista"`, `numero=="3"`, `completo==True`.

Códigos (desambiguação por separador + nº de dígitos; status; máscaras):

- `"20"` → `AMBIGUO`: CONTRIBUINTE (`setor=="20"`, `setor_completo==False`, `completo==False`) **e**
  CODLOG (`codlog=="20"`, `mascara=="20"`, `completo==False`).
- `"163210"` → `AMBIGUO`: CODLOG completo (`codlog=="16321"`, `digito_verificador=="0"`,
  `mascara=="16321-0"`) **e** CONTRIBUINTE parcial (núcleo 6/10).
- `"16321-0"` → `UNICO` CODLOG (`codlog=="16321"`, `digito_verificador=="0"`, `mascara=="16321-0"`);
  contribuinte rejeita.
- `"001.001"` → `UNICO` CONTRIBUINTE parcial (`setor=="001"`, `quadra=="001"`, `mascara=="001.001"`);
  codlog rejeita (tem ponto).
- `"001.001.0004"` → `UNICO` CONTRIBUINTE, `lote=="0004"`, `dv==""`, `completo==True`.
- `"001.001.0004-01"` / `"001001000401"` → `UNICO` CONTRIBUINTE, `dv=="01"`, `dv_completo==True`.
- `"0010010004"` → `UNICO` CONTRIBUINTE completo (codlog rejeita, >6).
- `"00100100"` (8 díg.) → `UNICO` CONTRIBUINTE **parcial** (`lote_completo==False`).
- `"0010010004001"` (13 díg.) → `IMPOSSIVEL`.
- `"abc!@#"` → `UNICO` LOGRADOURO (começa por letra; validação de conteúdo não é concern deste módulo).
- `""` / `"   "` → `VAZIO`.

Texto (exclusão mútua; ruas numeradas; só-nome vs tipo+nome):

- `"rua itat"` → `UNICO` LOGRADOURO, `tipo_logradouro=="rua"`, `nome=="itat"`, `completo==True`.
- `"avenida paulista 3"`, `"avenida paulista, 3, consolação, são paulo"` → `UNICO` ENDERECO,
  `logradouro.tipo_logradouro=="avenida"`, `logradouro.nome=="paulista"`, `numero=="3"`,
  `completo==True`, complemento descartado.
- `"paulista 3"` (nome + número, sem tipo) → `UNICO` ENDERECO **parcial**:
  `logradouro.tipo_logradouro==""`, `logradouro.nome=="paulista"`, `numero=="3"`, `completo==False`
  (endereço exige tipo + nome + número).
- `"rua 25 de março"` → `UNICO` LOGRADOURO, `tipo_logradouro=="rua"`, `nome=="25 de março"`.
- `"rua 25 de março, 100"` / `"rua 25 de março 100"` → `UNICO` ENDERECO,
  `logradouro.tipo_logradouro=="rua"`, `logradouro.nome=="25 de março"`, `numero=="100"`.

`finished_typing` (relaxa o tipo do logradouro; não afeta códigos):

- `"paulista"` com `finished_typing=True` → `UNICO` LOGRADOURO **completo** (`tipo_logradouro==""`,
  `nome=="paulista"`, `completo==True`).
- `"paulista, 300"` com `finished_typing=True` → `UNICO` ENDERECO **completo**
  (`logradouro.tipo_logradouro==""`, `logradouro.nome=="paulista"`, `numero=="300"`, `completo==True`).
- `"paulista 300"` com `finished_typing=False` → `UNICO` ENDERECO **parcial** (`completo==False`).
- `"avenida paulista"` → `completo==True` com ou sem `finished_typing` (já tem tipo + nome).
- `"00100100"` (8 díg.) com `finished_typing=True` → ainda `UNICO` CONTRIBUINTE **parcial**
  (`completo==False`): o flag não afeta códigos.

Extensão (6) — quando uma `RegraContribuinte` "setor[0] <= 4" for plugada: `"5"` deixa de produzir
candidato CONTRIBUINTE e o resultado de `"5"` vira `UNICO` CODLOG (sem a regra, é `AMBIGUO`).

Contrato:

- `status`, `match`, `tipos` refletem a lista; união serializa pelo discriminador `tipo` (Pydantic v2).
- `calcular_dv()` levanta `NotImplementedError` nesta fase.

## Patches

- 2026-06-24 (v7): remove a camada de wrappers `Candidato*`. Eram redundantes — `formato_completo`
  era sempre igual a `parse.completo`. O discriminador `tipo` passou para dentro de cada `*Parse`,
  que agora é, ele mesmo, o candidato; `Candidato` virou a união discriminada dos parses. Consome-se
  `.completo` no lugar de `formato_completo`. Implementação validada (`mypy --strict`, `ruff`,
  round-trip de serialização da união discriminada).
