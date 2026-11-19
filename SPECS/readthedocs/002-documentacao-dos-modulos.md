---
spec: readthedocs/002
versao: v1
atualizado_em: 2026-11-19
testes_tdd: false
implementado: false
markers_obrigatorios: [documentacao]
changelog:
  - v1: versão inicial
---

# SPEC readthedocs/002 — Documentação dos módulos

## 1 · User story

**Requisito não-funcional** — todo pacote de primeiro nível tem `README.md` num padrão único por
camada, e toda classe pública de `services/` tem docstring no padrão. A primeira leva é escrita pelo
Claude na sessão principal, que pergunta ao usuário o que o código e as SPECs não respondem. A suíte
de testes mantém o padrão daí em diante.

## 2 · Condições de pronto

- [ ] Todo pacote de primeiro nível de `services/domain`, `services/integrations`, `services/utils`,
      `services/scripts` e `apps` tem `README.md` no padrão da sua camada: título igual ao nome do
      pacote, frase-resumo e seções obrigatórias na ordem.
- [ ] Um pacote novo sem `README.md`, ou com README fora do padrão, faz a suíte padrão falhar,
      **nomeando o pacote e o problema**.
- [ ] Toda classe pública de nível de módulo em `services/` tem docstring cuja primeira linha é uma
      frase terminada em ponto. Uma classe nova sem docstring faz a suíte padrão falhar.
- [ ] Um README que cita classe, função ou pacote por referência (`[Nome][caminho.de.import]`)
      **derruba o build da documentação** quando o alvo deixa de existir.
- [ ] Ao fim de cada rodada, a conferência acusa qualquer mudança em `.py` que não seja
      docstring de classe.
- [ ] O site compila em modo estrito com todos os READMEs, e cada página de módulo abre com o README
      do pacote.

## 3 · Domínio

Consome de [readthedocs/001](001-documentacao-tecnica.md#3--domínio) o `Camada` e o
`ModuloDocumentado`. A pergunta que esta SPEC faz a eles é: *o README deste módulo está no padrão da
camada dele?*

```python
class SecaoReadme(StrEnum):
    """Seção de README de módulo. A ordem do enum é a ordem em que as seções aparecem."""

    PAPEL = "Papel no sistema"
    CONCEITOS = "Conceitos de domínio"
    FONTE_EXTERNA = "Fonte externa"
    PIPELINE = "Pipeline"
    ROTAS = "Rotas"
    PORTAS = "Portas de entrada"
    REGRAS = "Regras e invariantes"
    DEPENDENCIAS = "Dependências"
    REFERENCIAS = "Referências"


class PadraoReadme(BaseModel):
    """As seções que o README de um pacote precisa ter, conforme a camada dele."""

    camada: Camada
    obrigatorias: tuple[SecaoReadme, ...]  # todas presentes
    opcionais: frozenset[SecaoReadme] = frozenset()  # podem faltar; nenhuma outra é admitida


class TipoClasse(StrEnum):
    """O que uma classe pública de services/ é, para escolher o que a docstring dela diz."""

    ONTOLOGIA = "ontologia"  # BaseModel que é entidade ou atributo do domínio
    CONTRATO = "contrato"  # BaseModel de I/O de uma operação (...Input, ...Output, ...Config)
    ENUMERACAO = "enumeracao"
    PORTA = "porta"  # classe callable: tem __call__
    INTERFACE = "interface"  # ABC ou Protocol
    EXCECAO = "excecao"
    OUTRA = "outra"
```

| Camada | Obrigatórias (nesta ordem) | Opcionais |
|---|---|---|
| `services/domain` | Papel no sistema · Conceitos de domínio · Portas de entrada · Dependências · Referências | Regras e invariantes |
| `services/integrations` | Papel no sistema · Fonte externa · Portas de entrada · Dependências · Referências | Regras e invariantes |
| `services/utils` | Papel no sistema · Portas de entrada · Dependências · Referências | Regras e invariantes |
| `services/scripts` | Papel no sistema · Pipeline · Portas de entrada · Dependências · Referências | Regras e invariantes |
| `apps` | Papel no sistema · Rotas · Dependências · Referências | Conceitos de domínio · Regras e invariantes |

| `TipoClasse` | A primeira linha da docstring diz |
|---|---|
| `ONTOLOGIA` | o que a entidade **é** no domínio da DIMAP, nunca como é produzida |
| `CONTRATO` | a operação que ele alimenta ou devolve, e o que de processo carrega |
| `ENUMERACAO` | o que o conjunto classifica |
| `PORTA` | o que ela faz, em termos de domínio, no presente (*"Resolve…"*, *"Monta…"*) |
| `INTERFACE` | o papel que as implementações cumprem |
| `EXCECAO` | quando é levantada |
| `OUTRA` | o que a classe é |

Subpacote não tem README próprio: entra no README do pacote pai. Docstring de **módulo** e de
**função** não fazem parte do padrão.

## 4 · Fora de escopo

- Docstrings de funções públicas de `services/`: sem dono ainda.
- Docstrings das classes de `apps/` (models Django, formulários, views): sem dono ainda.
- A frase-resumo de cada README listada na página de índice da camada no site: sem dono ainda.
- Revisar o conteúdo dos READMEs a cada mudança de código: sem dono. Os testes conferem a forma, e o
  build estrito confere as referências.

## 5 · Peças de referência a compor

- `@services/scripts/documentacao/descoberta.py` → `DescobrirModulos` (readthedocs/001): a lista de
  pacotes de primeiro nível, para os testes e para montar as rodadas.
- `@services/scripts/documentacao/paginas.py` → `MontarPaginaModulo` (readthedocs/001): a página do
  site já abre com o README e tira o H1 dele.
- `@documentacao/mkdocs.yml` → build `--strict` com mkdocstrings (readthedocs/001): é ele que resolve
  e valida as referências `[Nome][caminho]`.
- `@CLAUDE.md` → §1 a §3 e §5: o contexto de projeto e de arquitetura da escrita, já carregado na
  sessão principal.
- `@services/domain/lote_geocod/gaveta.py` → `DivergenciaArea` e `GavetaLote`: docstrings que já
  estão no padrão.
- Skills: `ontologia` (a frase por modelo vira a docstring), `specs`, `escrever-testes`.

## 6 · Snippets

> Os comentários abaixo são didáticos e **não são portados** para o código (CLAUDE.md §7.2).

### 6.1 O padrão em código

**`services/scripts/documentacao/padrao.py`**
```python
class ViolacaoPadrao(BaseModel):
    """Um desvio do padrão de documentação, apontado onde ele está."""

    alvo: str  # "services.domain.lote_geocod" ou "services/domain/lote_geocod/models.py:LoteAttributes"
    problema: str


PADROES: dict[Camada, PadraoReadme] = {
    Camada.DOMINIO: PadraoReadme(
        camada=Camada.DOMINIO,
        obrigatorias=(
            SecaoReadme.PAPEL,
            SecaoReadme.CONCEITOS,
            SecaoReadme.PORTAS,
            SecaoReadme.DEPENDENCIAS,
            SecaoReadme.REFERENCIAS,
        ),
        opcionais=frozenset({SecaoReadme.REGRAS}),
    ),
    # ... INTEGRACOES, UTILITARIOS, SCRIPTS e APPS conforme a tabela do §3 ...
}

ABERTURA = re.compile(r"\A# (?P<nome>\S+)\n\n(?P<resumo>[^#\n][^\n]*)\n")
SECAO = re.compile(r"^## (?P<titulo>.+?)\s*$", re.MULTILINE)
BLOCO_DE_CODIGO = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


class ConferirReadme:
    def __call__(self, modulo: ModuloDocumentado) -> list[ViolacaoPadrao]:
        return self.pipeline(modulo)

    def pipeline(self, modulo: ModuloDocumentado) -> list[ViolacaoPadrao]:
        if modulo.readme is None:
            return [self._violacao(modulo, "sem README.md")]
        return [
            *self._abertura(modulo, modulo.readme),
            *self._secoes(modulo, modulo.readme),
        ]

    def _abertura(self, modulo: ModuloDocumentado, readme: str) -> list[ViolacaoPadrao]:
        # O título é o nome do pacote, e a linha seguinte é UMA frase: é ela que resume o módulo.
        achado = ABERTURA.match(readme)
        if achado is None:
            return [self._violacao(modulo, "não abre com '# <pacote>' seguido da frase-resumo")]
        violacoes = []
        if achado["nome"] != modulo.nome:
            violacoes.append(self._violacao(modulo, f"título '{achado['nome']}' não é o nome do pacote"))
        if not achado["resumo"].endswith("."):
            violacoes.append(self._violacao(modulo, "a frase-resumo não termina em ponto"))
        return violacoes

    def _secoes(self, modulo: ModuloDocumentado, readme: str) -> list[ViolacaoPadrao]:
        padrao = PADROES[modulo.camada]
        # "## " dentro de bloco de código (comentário de shell, exemplo) não é seção.
        titulos = [achado["titulo"] for achado in SECAO.finditer(BLOCO_DE_CODIGO.sub("", readme))]
        admitidas = {secao.value for secao in (*padrao.obrigatorias, *padrao.opcionais)}
        violacoes = [
            self._violacao(modulo, f"seção '{titulo}' não existe no padrão da camada")
            for titulo in titulos
            if titulo not in admitidas
        ]
        violacoes += [
            self._violacao(modulo, f"falta a seção '{secao.value}'")
            for secao in padrao.obrigatorias
            if secao.value not in titulos
        ]
        # A ordem do enum é a ordem do README: as seções presentes têm de estar em ordem crescente.
        posicoes = [list(SecaoReadme).index(SecaoReadme(t)) for t in titulos if t in admitidas]
        if posicoes != sorted(posicoes):
            violacoes.append(self._violacao(modulo, "seções fora da ordem do padrão"))
        return violacoes

    def _violacao(self, modulo: ModuloDocumentado, problema: str) -> ViolacaoPadrao:
        return ViolacaoPadrao(alvo=modulo.caminho_import, problema=problema)


conferir_readme = ConferirReadme()
```

**`services/scripts/documentacao/docstrings.py`**
```python
class ArquivoPython(BaseModel):
    caminho: PurePosixPath  # relativo à raiz do repositório
    fonte: str  # "" quando o arquivo não existe daquele lado (criado ou apagado)


class ConferirDocstrings:
    """Acusa classe pública de nível de módulo sem docstring, ou com primeira linha fora do padrão."""

    def __call__(self, arquivo: ArquivoPython) -> list[ViolacaoPadrao]:
        return self.pipeline(arquivo)

    def pipeline(self, arquivo: ArquivoPython) -> list[ViolacaoPadrao]:
        # Só o nível de módulo: classe aninhada (Meta, Config) e privada (_X) ficam de fora.
        classes = [
            no
            for no in ast.parse(arquivo.fonte).body
            if isinstance(no, ast.ClassDef) and not no.name.startswith("_")
        ]
        return [
            ViolacaoPadrao(alvo=f"{arquivo.caminho}:{classe.name}", problema=problema)
            for classe in classes
            if (problema := self._problema(classe)) is not None
        ]

    def _problema(self, classe: ast.ClassDef) -> str | None:
        docstring = ast.get_docstring(classe)
        if docstring is None:
            return "sem docstring"
        primeira = docstring.splitlines()[0]
        if not primeira.endswith("."):
            return "a primeira linha da docstring não é uma frase terminada em ponto"
        # Docstring que abre repetindo o nome da classe é paráfrase do nome, não descrição.
        if primeira.split()[0].strip("`") == classe.name:
            return "a docstring abre repetindo o nome da classe"
        return None


class ConferirSoDocstrings:
    """Acusa arquivo em que algo além de docstring de classe mudou entre duas versões."""

    def __call__(self, antes: ArquivoPython, depois: ArquivoPython) -> list[ViolacaoPadrao]:
        if self._esqueleto(antes) == self._esqueleto(depois):
            return []
        return [ViolacaoPadrao(alvo=str(depois.caminho), problema="mudança fora de docstring de classe")]

    def _esqueleto(self, arquivo: ArquivoPython) -> str:
        # Tira a docstring de cada classe e compara as árvores. O ast.dump ignora linha, coluna e
        # comentário: sobra só o código. Docstring de módulo e de função NÃO é tirada, então mexer
        # nelas também acusa.
        arvore = ast.parse(arquivo.fonte)
        for no in ast.walk(arvore):
            if isinstance(no, ast.ClassDef) and ast.get_docstring(no, clean=False) is not None:
                no.body = no.body[1:] or [ast.Pass()]
        return ast.dump(arvore)


conferir_docstrings = ConferirDocstrings()
conferir_so_docstrings = ConferirSoDocstrings()
```

**`services/scripts/documentacao/conferir.py`** — a conferência do fim de cada rodada. Porta de entrada fina: só ela fala com o `git` (só leitura).
```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Confere a documentação dos pacotes de uma rodada.")
    parser.add_argument("pacotes", nargs="+", type=PurePosixPath)  # ex.: services/domain/lote_geocod
    argumentos = parser.parse_args()
    violacoes = [
        violacao
        for pacote in argumentos.pacotes
        for violacao in (*_readme(pacote), *_docstrings(pacote), *_so_docstrings(pacote))
    ]
    for violacao in violacoes:
        print(f"{violacao.alvo}: {violacao.problema}")
    raise SystemExit(1 if violacoes else 0)


def _so_docstrings(pacote: PurePosixPath) -> list[ViolacaoPadrao]:
    # Compara cada .py alterado do pacote contra o HEAD. No pathspec do git o "*" atravessa
    # subpastas. O arquivo não rastreado não aparece no diff, e por isso entra pelo ls-files.
    alterados = [
        *_git("diff", "--name-only", "HEAD", "--", f"{pacote}/*.py"),
        *_git("ls-files", "--others", "--exclude-standard", "--", f"{pacote}/*.py"),
    ]
    return [
        violacao
        for caminho in alterados
        for violacao in conferir_so_docstrings(_no_head(caminho), _na_arvore(caminho))
    ]


def _git(*argumentos: str) -> list[str]:
    saida = subprocess.run(
        ["git", *argumentos],
        capture_output=True,
        text=True,
        check=True,
    )
    return saida.stdout.split()

# _readme usa DescobrirModulos + conferir_readme; _docstrings só olha pacotes de services/;
# _no_head roda `git show HEAD:<caminho>` (fonte vazia se o arquivo é novo).


if __name__ == "__main__":
    main()
```

### 6.2 A skill do padrão

**`.claude/skills/documentar-modulo/SKILL.md`** — o padrão vira skill, porque todo pacote e toda
classe pública nova seguem o mesmo molde. O conteúdo é este bloco e o README de exemplo do §6.3. O
`.agents/skills` já aponta para `.claude/skills`.

````markdown
---
name: documentar-modulo
description: "Padrão de documentação de módulo do DIMAP GeoCoder: o README.md de pacote de primeiro nível (seções por camada, frase-resumo, referências verificadas ao código) e a docstring de classe pública de services/. Use SEMPRE que criar um pacote novo, criar ou alterar classe pública em services/, ou escrever/revisar um README de módulo."
---

# Skill: Documentar módulo — DIMAP GeoCoder

## O README de módulo

O README de um pacote de primeiro nível é a página dele em `/docs/`. Quem lê não tem o código
aberto: o README explica **o que o módulo é no sistema e como se compõe com ele**, e a referência
gerada logo abaixo mostra assinaturas, campos e código. O README não repete a referência.

### Molde

```markdown
# <nome_do_pacote>

<Uma frase numa linha só: o que o módulo é ou faz no sistema, terminada em ponto.>

## Papel no sistema
<Um parágrafo: a camada, a pergunta do domínio que o módulo responde e onde ele entra no fluxo
localização → entidade → gaveta → ação. Se for matcher ou geocoder, diga qual dos dois.>

## Conceitos de domínio            ← domain (obrigatória) · apps (opcional)
- **<Termo>** ([<Classe>][<caminho.de.import.Classe>]) — <o que é, em uma linha>.

## Fonte externa                   ← só integrations
<Serviço, protocolo, camadas ou endpoints, settings que configuram, exceções que encapsulam os erros.>

## Pipeline                        ← só scripts
<Comando que dispara, entrada, saída em data/, posição em cargas → variações → cache, quem agenda.>

## Rotas                           ← só apps
| Rota | View | Devolve | Proteção |
|---|---|---|---|
| `<url>` | `<view>` | <partial ou página> | aberta · login · ação `<slug>` |

## Portas de entrada               ← todas, exceto apps
| Porta | Entrada → Saída | Para quê |
|---|---|---|
| [<Classe>][<caminho>] | [<Input>][<caminho>] → [<Output>][<caminho>] | <uma linha> |

## Regras e invariantes            ← opcional
- <Regra que o tipo não diz: limiar, desempate, descarte, fallback — com a constante que a carrega.>

## Dependências
**Consome:** [<pacote>][<caminho.do.pacote>] — <para quê>.
**É consumido por:** [<pacote>][<caminho.do.pacote>] — <para quê>.

## Referências
- SPECs: `<épico>/<nº>` — <o que ela define aqui>.
- Skills: `<skill>`.
```

### Regras

- **Seções na ordem do molde**, só as da camada (tabela em `services/scripts/documentacao/padrao.py`).
  Seção obrigatória sem conteúdo diz isso numa linha ("Nenhuma.") — não some.
- **Referência a código é sempre `[Nome][caminho.de.import]`**: classe, função ou pacote. O build
  estrito valida o caminho, então README desatualizado quebra o build em vez de mentir.
- **SPEC se cita como código** (`localizacao_lote/002`), nunca como link: as SPECs não são publicadas
  no site, e link para fora dele derruba o build estrito. Só SPEC com `implementado: true`.
- **Fato de domínio só com fonte**: código, SPEC implementada, CLAUDE.md ou README da raiz. O que não
  tem fonte não se escreve.
- **Prosa curta**: alvo de 40 a 120 linhas. Não parafrasear a referência (lista de campos,
  assinatura), não narrar histórico, não justificar decisão de arquitetura — isso é das SPECs.
- **Português**, termos de domínio como o código os escreve (`codlog`, `contribuinte`, `gaveta`).

## A docstring de classe

Obrigatória em toda classe pública de nível de módulo em `services/`. É a frase que abre o bloco da
classe na referência do site.

- **Primeira linha: uma frase terminada em ponto**, no máximo ~100 caracteres. O que ela diz depende do
  tipo da classe:

| Tipo | A primeira linha diz | Exemplo |
|---|---|---|
| ontologia | o que a entidade é no domínio | `"""O lote como a gaveta o apresenta: os atributos do cadastro e o que se mede no polígono."""` |
| contrato | a operação que alimenta ou devolve | `"""Entrada do LoteGeocoder: a identificação fiscal do lote e o CRS em que a geometria volta."""` |
| enumeração | o que o conjunto classifica | `"""Quanto a área do polígono se afasta da área de terreno declarada no cadastro."""` |
| porta | o que faz, no presente | `"""Busca na camada de lotes do GeoSampa os polígonos de um lote fiscal."""` |
| interface | o papel das implementações | `"""Provedor de geocodificação externa: recebe um endereço e devolve candidatos."""` |
| exceção | quando é levantada | `"""O GeoSampa respondeu fora do protocolo WFS esperado."""` |

- **Parágrafo extra só para regra que o tipo não diz**, em até três linhas.
- **Não**: abrir com "Classe…", "Esta classe…" ou com o próprio nome; listar campos (a referência
  mostra, com tipos); seções `Args:`/`Returns:` (os tipos dizem); citar SPEC ou histórico.
- **Docstring de módulo não se cria** (CLAUDE.md §7.2): o README do pacote cumpre esse papel.
- O significado de um campo continua em comentário de uma linha ao lado dele (skill `ontologia`).

## Como documentar um pacote

1. **Portas**: leia o `__init__.py` e o `__all__`. É o que o README chama de portas de entrada.
2. **Código**: os models primeiro, depois as classes callables.
3. **SPECs**: `grep -rl "<camada>/<pacote>\|<pacote>" SPECS/ --include=*.md`. Leia §1, §3 e §7 só das
   que têm `implementado: true`, porque SPEC não implementada não descreve o código.
4. **Consumidores**: `grep -rn "<caminho.de.import.do.pacote>" apps services --include=*.py`.
5. **Skill do tema**, se houver uma em `.claude/skills/`.
6. **Com dúvida, pergunte ao usuário e espere a resposta. Sem dúvida, escreva e siga para o
   próximo pacote.**
7. **Escreva** o `README.md` e as docstrings que faltam. Corrija uma docstring existente só se ela
   contradiz o código ou foge da primeira linha do padrão.

### Quando perguntar

Pergunte quando a resposta não está no código, numa SPEC implementada, no CLAUDE.md nem no README da
raiz:
- o que um termo de domínio significa, ou que processo da DIMAP usa o módulo;
- a razão de uma regra que o README precisa enunciar (limiar, desempate, descarte);
- código e SPEC que se contradizem;
- módulo que parece legado, duplicado ou sem consumidor.

Não pergunte o que a leitura do pacote responde.

### Como perguntar

- **Em lote, por pacote**: todas as dúvidas do pacote numa mensagem só, numeradas, no máximo cinco.
- **Com a evidência**: cada pergunta cita o `arquivo:linha` e diz o que você entendeu, para o usuário
  só confirmar ou corrigir.
- **Em texto corrido.** A ferramenta de múltipla escolha só entra quando a resposta é escolher entre
  alternativas que você já achou no código.
- **Espere a resposta** antes de escrever o README do pacote.
- A resposta do usuário é fonte: entra no README como qualquer fato do código.
- A resposta que revela bug ou pede mudança de código **não vira edição**: anote como pendência no
  resumo da rodada, porque é caso de SPEC.

### Glossário mínimo

Termo fora daqui, do CLAUDE.md ou do código só entra com fonte ou com a resposta do usuário.
- **codlog**: código do logradouro no cadastro da Prefeitura.
- **lote fiscal**: unidade do cadastro do IPTU (setor, quadra, lote e tipo de lote).
- **número de contribuinte (`sql`)**: a identificação fiscal do lote com o dígito.
- **endereço fiscal**: o endereço do imóvel no cadastro do IPTU.
- **GeoSampa**: o geoserver da Prefeitura (WFS para feições, WMS para o mapa).
- **perfil, cargo, unidade, competência**: quem pode o quê. A competência nasce do cargo na unidade.

### Proibido

- Mexer em qualquer coisa além de `README.md` e docstring de classe: código, comentário, import,
  formatação, docstring de módulo ou de função.
- Escrever fato sem fonte.
- `git commit`, `git add`, `migrate` ou qualquer escrita no banco ou no git.
````

### 6.3 README de exemplo

O molde preenchido para `services/domain/lote_geocod`. Os fatos foram conferidos no código. É exemplo
da skill, não entrega: a rodada escreve o README real e confere cada linha de novo.

**`services/domain/lote_geocod/README.md`** (exemplo)
```markdown
# lote_geocod

Resolve o polígono do lote fiscal no GeoSampa e monta a leitura do lote para a gaveta.

## Papel no sistema

Pacote de domínio do lado *geocoder*: recebe um lote já identificado pela sua identificação fiscal
(setor, quadra, lote e tipo de lote) e devolve a geometria. É o que pinta o **polígono** quando a busca
resolve um número de contribuinte ou um endereço que bate com um endereço fiscal. A identificação vem
dos matchers; este pacote não interpreta texto digitado.

## Conceitos de domínio

- **Lote fiscal** ([LoteAttributes][services.domain.lote_geocod.LoteAttributes]) — a unidade do
  cadastro do IPTU, identificada por setor, quadra, lote e tipo de lote.
- **Polígono do lote** ([LoteFeature][services.domain.lote_geocod.LoteFeature]) — a feição da camada de
  lotes: geometria e atributos do cadastro, num CRS.
- **Lote condominial** — lote cujo código de condomínio é diferente de `00`.
- **Número de contribuinte** — o `sql` do lote; só existe quando o cadastro traz o dígito.
- **Divergência de área** ([DivergenciaArea][services.domain.lote_geocod.DivergenciaArea]) — quanto a
  área medida no polígono se afasta da área de terreno declarada no cadastro.

## Portas de entrada

| Porta | Entrada → Saída | Para quê |
|---|---|---|
| [LoteGeocoder][services.domain.lote_geocod.LoteGeocoder] | [LoteGeocodInput][services.domain.lote_geocod.LoteGeocodInput] → `list[LoteFeature]` | os polígonos de um lote fiscal, filtrados pelo condomínio quando ele é dado |
| [LotePorIdentificador][services.domain.lote_geocod.LotePorIdentificador] | [LotePorIdentificadorInput][services.domain.lote_geocod.LotePorIdentificadorInput] → `LoteFeature \| None` | um polígono pelo identificador; `None` quando ele saiu da camada |
| [MontarGavetaLote][services.domain.lote_geocod.MontarGavetaLote] | [GavetaLoteInput][services.domain.lote_geocod.GavetaLoteInput] → [GavetaLote][services.domain.lote_geocod.GavetaLote] | o lote como a gaveta o lê, com a área medida no CRS métrico |
| [feature_para_lote][services.domain.lote_geocod.feature_para_lote] | feição WFS → `LoteFeature \| None` | a conversão da feição crua, reusada por quem consulta a mesma camada |

As duas buscas recebem o *fetcher* WFS por injeção (`WfsBatches`): o pacote não abre conexão.

## Regras e invariantes

- Divergência de área: até 2% é tolerável, acima de 2% é alerta e acima de 5% é erro
  (`LIMITE_ALERTA_PCT`, `LIMITE_ERRO_PCT`). A base é a área declarada; sem ela, não há divergência.
- Feição sem geometria, ou sem identificador, setor, quadra, lote ou tipo, é descartada em silêncio.
- O lote só **possui lançamento** quando está `ATIVO` no cadastro e tem número de contribuinte.

## Dependências

**Consome:** [wfs][services.integrations.wfs] — filtros CQL e o pedido de feições;
[geometry][services.domain.geometry] — geometria de polígono e reprojeção.
**É consumido por:** [lotes_mais_proximos][services.domain.lotes_mais_proximos],
[certidao_lancamento][services.domain.certidao_lancamento] e os apps `lote_geocoder`,
`lotes_mais_proximos` e `certidao_lancamento`.

## Referências

- SPECs: `localizacao_lote/001` — os dados do lote na gaveta; `localizacao_lote/002` — o reuso de
  `feature_para_lote`; `roteamento_busca/012` — o filtro de condomínio.
- Skills: `wfs-fetcher`.
```

### 6.4 As rodadas

Quem escreve é a **sessão principal do Claude Code**, e não um subagente: a dúvida chega ao usuário na
conversa, e a resposta volta para o mesmo contexto. Cada pacote segue o roteiro da skill
`documentar-modulo` (§6.2). Com dúvida, o Claude pergunta e espera; sem dúvida, escreve e segue.

Uma rodada tem até 8 pacotes de uma camada, em ordem alfabética, listados pelo `DescobrirModulos` na
hora em que ela começa. Ela começa a pedido do usuário e termina com a conferência e um resumo, e o
usuário revisa o diff antes da rodada seguinte. A ordem das camadas é de baixo para cima, para que os
READMEs das dependências existam quando os consumidores forem escritos:

| Camada | Pacotes hoje | Rodadas |
|---|---|---|
| `services/utils` | 15 | 2 |
| `services/integrations` | 4 | 1 |
| `services/domain` | 34 | 5 |
| `services/scripts` | 7 | 1 |
| `apps` | 24 | 3 |

Uma camada por conversa mantém o contexto enxuto, e as respostas das anteriores já estão nos READMEs.

Ao fim de cada rodada, a entrega só sai com tudo limpo. Como a conferência garante que só docstring de
classe mudou, ruff e mypy não têm o que acusar. Quem valida as referências dos READMEs é o build
estrito:
```bash
uv run python -m services.scripts.documentacao.conferir <pacote> <pacote> ...
uv run --group docs python -m services.scripts.documentacao . documentacao/paginas
uv run --group docs zensical build --strict -f documentacao/mkdocs.yml
```

O resumo da rodada sai na conversa:
```markdown
## Rodada <n> — <camada>
| Pacote | README | Docstrings escritas | Perguntas feitas |
|---|---|---|---|
| <pacote> | <n> linhas | <n> | <n> |

### Pendências para SPEC
- <pacote>: <bug ou mudança de código que uma resposta revelou>
```

Depois da última rodada: tirar o `xfail` dos dois testes de repositório (ver Caveats) e rodar
`uv run --group docs pytest -m documentacao`.

### 6.5 CLAUDE.md

- **§5**, ao fim de "`apps/` × `services/`": *"Todo pacote de primeiro nível tem `README.md` no padrão
  da skill `documentar-modulo`: é a página dele em `/docs/`."*
- **§7.2**, novo item: *"**Docstring de classe pública em `services/` é obrigatória**: uma frase que
  diz o que a classe é, no padrão da skill `documentar-modulo`. Ela é lida no site, longe do código, e
  por isso diz o quê; o comentário segue dizendo só o porquê."*
- **§10**, novo item: *"- [ ] Pacote novo tem README e classe pública nova tem docstring, no padrão da
  skill `documentar-modulo`?"*

## 7 · Caveats

A primeira leva de READMEs e docstrings é escrita pelo Claude, que pergunta só o que o código e as
SPECs não respondem, e os testes conferem a forma, não a verdade. São cerca de 84 READMEs e 270
docstrings, e escrever à mão travaria o épico. O custo é que a revisão do diff de cada rodada continua
sendo o filtro do conteúdo: um fato errado e plausível, que não gerou dúvida, só a revisão pega.

Os testes de repositório entram na suíte padrão: um pacote ou uma classe nova sem documentação quebra
o `uv run pytest`. A documentação se mantém pela mesma porta que mantém o código. O custo é atrito em
toda feature nova, porque README e docstring passam a fazer parte do pronto.

Entre a escrita dos testes e a última rodada, os dois testes de repositório ficam com
`xfail(strict=True)`. Sem isso, a suíte padrão ficaria vermelha durante dias para quem trabalha em
outro épico. O custo é que, nesse intervalo, a guarda não guarda nada, e o `strict` obriga a tirar a
marca quando o último pacote ficar em dia.

A docstring de classe diz **o quê** a classe é, o que tensiona o CLAUDE.md §7.2 ("comentário explica o
porquê, nunca o quê"). A docstring é lida no site, na referência, por quem não tem a linha na frente,
diferente do comentário. O custo é o risco de docstring que parafraseia o nome: a conferência barra
só o caso grosseiro (abrir com o próprio nome), e o resto fica com a revisão.

A conferência só-docstring compara a árvore sintática contra o `HEAD`. Ela pega mudança de código,
mas não pega mudança de comentário ou de formatação, que o `ast` descarta, e acusa como da rodada
qualquer mudança pendente que já existisse nos `.py` da rodada. O custo é que a rodada só começa com
os `.py` dos seus pacotes sem mudança pendente, e comentário alterado só aparece no diff.

As referências `[Nome][caminho]` acoplam o README ao caminho de import, e uma referência quebrada
derruba o build da imagem docs. É isso que impede o README de citar classe que não existe mais. O
custo é que renomear ou mover uma classe exige corrigir os READMEs no mesmo commit, senão o deploy da
documentação para.

## 8 · Testes (TDD)

Padrão — `tests/services/scripts/documentacao/`, suíte padrão, sobre textos e repositórios falsos:

- `test_readme_no_padrao_passa` — um README com título, frase-resumo e as seções obrigatórias da
  camada, na ordem, não gera violação. Uma seção opcional presente também não.
- `test_readme_fora_do_padrao_aponta_o_problema` — falta seção obrigatória, seção fora da ordem,
  seção estranha à camada, título diferente do pacote, resumo sem ponto e README ausente. Cada caso
  gera uma violação que nomeia o pacote e o problema. Um `## ` dentro de bloco de código não conta.
- `test_classe_publica_sem_docstring_e_acusada` — classe pública sem docstring, com primeira linha sem
  ponto ou abrindo com o próprio nome é acusada. Classe `_privada` e classe aninhada não.
- `test_so_docstring_de_classe_passa_na_conferencia` — duas versões que diferem só na docstring de
  uma classe (acrescentada ou reescrita) não geram violação.
- `test_mudanca_fora_de_docstring_de_classe_e_acusada` — linha de código alterada, docstring de módulo
  acrescentada, docstring de função alterada e arquivo novo geram violação.

Repositório — suíte padrão, com `xfail(strict=True)` até a última rodada:

- `test_todo_modulo_do_repositorio_tem_readme_no_padrao` — o `DescobrirModulos` sobre a raiz real
  mais o `ConferirReadme` não devolvem violação.
- `test_toda_classe_publica_de_services_tem_docstring` — o `ConferirDocstrings` sobre todo `.py` de
  `services/` não devolve violação.

Site compilado — *(marker `documentacao`)*:

- `test_referencia_quebrada_no_readme_derruba_o_build` — num repositório falso, um README com
  `[X][services.domain.exemplo.NaoExiste]` faz o `zensical build --strict` falhar. Com o caminho certo,
  o build passa e a referência vira link.
- `test_site_do_repositorio_compila_em_modo_estrito` (readthedocs/001) — passa com todos os READMEs.
