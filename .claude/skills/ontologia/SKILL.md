---
name: ontologia
description: "Como modelar um domínio como ontologia em Pydantic no DIMAP GeoCoder — entidades, atributos e relações como tipos. Use SEMPRE que for escrever ou revisar models de domínio (o §3 Domínio de uma SPEC, ou os models de services/domain/), decidir entre herança e composição, entre enum e subtipo, ou entre campo guardado e atributo derivado. Complementar à skill specs."
---

# Skill: Escrever ontologia — DIMAP GeoCoder

**Ontologia é o domínio dito em tipos:** quais entidades existem, o que cada uma tem e como elas se
relacionam. O tipo é a especificação — campo ausente é decisão declarada, campo opcional diz o que
pode faltar, enum diz quantas respostas existem. O que o tipo consegue dizer **não se escreve em
prosa**.

---

## 1 · A ontologia é o domínio, não o transporte

Três coisas parecidas que não são a mesma:

| | O que é | Muda quando |
|---|---|---|
| **Ontologia** | o que a entidade **é** no domínio | o domínio muda |
| **Contrato de I/O** | o que entra e sai de uma operação (`...Input` / `...Output`) | a operação muda |
| **Model de persistência** | como aquilo é gravado | o schema muda |

Um DTO de entrada de um serviço **não é** a entidade, mesmo quando tem os mesmos campos: se ele ganha
`output_crs` ou `layer_name`, ele já está falando do processo, não do domínio. Misturar os três produz
o model que muda por três razões diferentes — o oposto da responsabilidade única (CLAUDE.md §7.1).

**Por isso o DTO envelopa a entidade, nunca recopia os campos dela.** Ao lado do objeto entra só o que
é do processo:

```python
class LoteGeocodInput(BaseModel):
    lote: Lote                   # a entidade inteira, não setor/quadra/lote soltos
    output_crs: int              # e só então o que é do processo
```

Campo de entidade solto dentro de DTO é a ontologia duplicada, livre para divergir dela — e quem lê o
DTO deixa de saber que aquilo era uma entidade.

---

## 2 · As três relações

**"é um" → herança.** Quando o domínio tem **tipos de** algo: o abstrato define o que todos são, os
concretos especializam.

**"tem um" → composição.** Atributo, simples ou lista.

**Relação direcionada → entidade própria**, com **as duas pontas**. Só quando o vínculo tem **nome,
papel ou atributos próprios** — se é só "aponta para", é campo, e virar grafo só acrescenta indireção.

```python
class Genitor(BaseModel): ...        # abstrato: o que todo genitor é
class Pai(Genitor): ...              # concretos: tipos de genitor
class Mae(Genitor): ...

class Filiacao(BaseModel):           # a relação: duas pontas + atributos do vínculo
    genitor: Genitor
    descendente: "Pessoa"

class Pessoa(BaseModel):
    nome: str
    familia: list[Filiacao] = []     # composição sobre a relação, não sobre a ponta
```

Modelada a aresta, **relação derivada sai de graça**: irmandade não precisa de entidade nova — é a
filiação do irmão, que entra na mesma lista por compartilhar o genitor.

```python
ana = Pessoa(nome="Ana")
bruno = Pessoa(nome="Bruno")
pai = Pai(nome="João")

ana.familia = [
    Filiacao(genitor=pai, descendente=ana),
    Filiacao(genitor=pai, descendente=bruno),   # o irmão: mesmo genitor, outra ponta
]
```

> Herança aqui é de **ontologia**. A restrição do CLAUDE.md §7.1 ("herança é exceção rara") vale para
> classes de comportamento em `services/`, não para a modelagem do domínio.

---

## 3 · Derivado nunca é campo

Se o valor **decorre** de outros dados, ele é `@computed_field` / `@property` — não coluna, não campo
guardado. Campo redundante é um terceiro valor livre para discordar dos dois que o produzem, e alguém
passa a ter de vigiar essa discordância.

```python
class Periodo(BaseModel):
    inicio: date
    fim: date | None = None          # None = indeterminado

    @computed_field
    @property
    def vigente(self) -> bool:
        return self.inicio <= date.today() and (self.fim is None or date.today() <= self.fim)
```

Guardar só se o valor **não for reconstituível** — porque depende de algo que não está no modelo, ou
porque o domínio precisa do valor **do dia em que foi apurado**, e não do de hoje.

---

## 4 · O tipo carrega a regra

- **Obrigatório × opcional** é invariante: `str` diz "sempre existe"; `str | None` diz "pode faltar", e
  o que o `None` significa vai em comentário de uma linha, não em parágrafo.
- **Enum quando as respostas são contáveis.** Três estados num par de booleanos são quatro
  combinações, duas delas impossíveis — e alguém vai construí-las.
- **Campos pareados** que só fazem sentido juntos nascem juntos e são validados juntos: ausência de um
  não pode significar a regra mais restritiva de todas, calada.
- **Cardinalidade se modela no atributo**, pelo tipo dele — nunca em prosa. É a regra de negócio dita
  pela assinatura:

  ```python
  genitor: Genitor                 # exatamente um
  conjuge: Pessoa | None = None    # zero ou um
  familia: list[Filiacao] = []     # zero ou vários
  pais: list[Genitor]              # vários, e ao menos um (sem default)
  ```
- **Validação de forma na fronteira** (`Field(pattern=...)`, `field_validator`) — é o tipo recusando
  o que o domínio não admite.

---

## 5 · Enum × subtipo

| Situação | Modelagem |
|---|---|
| Os tipos diferem só por **rótulo** | **enum** |
| Os tipos têm **atributos ou regras próprias** | **herança** |
| O conjunto **cresce sem código novo** | enum de catálogo, ou entidade de catálogo |

Enum que ganha um `if` por valor espalhado pelo domínio está pedindo para virar subtipo. Subtipo sem
nenhum campo ou regra própria está pedindo para virar enum.

---

## 6 · Nomes

- **Termo de domínio na língua do domínio, estrutura em inglês** (CLAUDE.md §7.1). Não se "traduz"
  nome de domínio.
- A entidade tem o nome que o **domínio** dá a ela — nunca o do processo que a produz. `Lote` é
  entidade; `ResultadoDaBuscaDeLote` é contrato de I/O.
- O nome da relação é o **vínculo**, não a concatenação das pontas: `Filiacao`, não `PessoaGenitor`.

---

## 7 · Antipadrões

- **Booleano que devia ser enum** — e o segundo booleano que anda sempre junto do primeiro.
- **Relação como id solto** (`genitor_id: str`) quando o vínculo tem papel ou atributos.
- **Campo derivado guardado** — ver §3.
- **Atributo do processo dentro da entidade** — CRS, nome de camada, paginação.
- **God-model** que junta o que três operações diferentes precisam.
- **Prosa dizendo o que o tipo já diz** ("o campo é opcional porque pode não haver…").

---

## 8 · Perguntas ao usuário

**Pergunte antes de escrever o model, não depois.** A lista abaixo é **repertório, não questionário**:
pergunte só o que ficou **em dúvida** depois do briefing do usuário — o que ele já disse não se
re-pergunta, e o resto não se percorre por obrigação.

E **não varra o repositório atrás da resposta**: leia só o **estritamente relevante** — o módulo em
questão e a SPEC da vez. Perguntar é mais barato que ler o código inteiro. Pergunte **em lote**, não
uma de cada vez.

**Identidade** — Isso é entidade ou atributo de outra? Que nome o domínio dá a ela? O que distingue
duas instâncias: dois com os mesmos atributos são a mesma coisa?

**Tipos** — Existem "tipos de" isso? Quais são **todos**? A lista fecha, ou cresce com o tempo? Eles
diferem só por rótulo, ou cada um tem atributo e regra próprios?

**Relação** — O vínculo tem nome no domínio? Tem atributos próprios — período, papel, quem autorizou?
As duas pontas têm papéis diferentes? Um pode ter vários ao mesmo tempo? Pode ter **zero**? O que
acontece com o vínculo quando uma ponta desaparece?

**Derivado × guardado** — Esse valor é sempre reconstituível do resto? **Se ele mudar de resposta
sozinho amanhã, isso está certo ou errado?** Preciso do valor de hoje, ou do valor do dia em que o ato
foi praticado?

**Opcionalidade** — Pode faltar? Faltando, significa "não sei", "não se aplica" ou "nenhum" — que são
três coisas diferentes? A entidade pode nascer incompleta?

**Tempo** — Isso tem vigência? Período em aberto é possível? Sobreposição é permitida ou proibida?
Interessa o histórico ou só o estado de hoje?

---

## Checklist

- [ ] Cada relação foi classificada: **é um** (herança), **tem um** (composição) ou **vínculo com
      nome/papel/atributos** (entidade com as duas pontas).
- [ ] Nenhum campo guardado é derivável de outros.
- [ ] Estados contáveis estão em **enum**, não em combinação de booleanos.
- [ ] Obrigatório × opcional reflete a invariante real, e o significado do `None` está claro.
- [ ] Nomes vêm do domínio, não do processo; relação nomeada pelo vínculo.
- [ ] A ontologia não carrega atributo de transporte nem de persistência.
- [ ] Nada de prosa repetindo o que o tipo diz.
