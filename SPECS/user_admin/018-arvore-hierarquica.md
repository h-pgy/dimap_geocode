---
spec: user_admin/018
versao: v3
atualizado_em: 2026-08-17
testes_tdd: true
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a regra passa a responder a posição de uma unidade só — acima, ao lado e abaixo — e o
        organograma inteiro ganha página própria
  - v3: a seção passa a ser o organograma inteiro com o caminho marcado pelo servidor, abrir e
        fechar viram JS de estado visual, e `ao_lado` sai do domínio junto com a rota do partial
---

# SPEC user_admin/018 — Árvore hierárquica: o caminho até uma unidade, e o organograma inteiro

## 1 · User story
O servidor da DIMAP situa a unidade no organograma a partir da página dela, percorrendo dali para baixo
e para os lados até a unidade que procura, para chegar nela sem voltar à listagem e adivinhar a sigla.

## 2 · Condições de pronto
- [ ] A página da unidade ganha uma seção de **hierarquia**, depois da Direção, que abre mostrando
      **só o caminho** do topo até a unidade da página — nem as subordinadas dela, nem as irmãs de
      ninguém.
- [ ] Cada unidade é um **card com a sigla sob o ponto na cor dela**; o **nome inteiro** aparece no
      card em foco, nas subordinadas diretas dele e no tooltip de todos.
- [ ] O **caminho percorrido** se distingue do resto do organograma, e a unidade **em foco** se
      distingue do caminho.
- [ ] **Clicar num card** o põe em foco e desce um nível nele, **sem recarregar a página**; clicar no
      card em foco recolhe o nível.
- [ ] Todo card do caminho oferece **dois caminhos distintos**: descer nele, e **abrir a página** da
      sua unidade.
- [ ] Dá para **chamar as irmãs** de qualquer unidade do caminho, e recolhê-las de volta.
- [ ] Unidade **sem subordinadas** em foco diz que não há nenhuma, em vez de abrir um nível vazio.
- [ ] **Voltar** devolve a seção ao estado de partida: foco na unidade da página e o resto recolhido.
- [ ] Existe uma **página da árvore hierárquica**, em rota aberta de leitura, com o organograma
      inteiro; ela abre no topo e tem **"ver toda a árvore"**, que expande todos os níveis de uma vez.
- [ ] O design foi aprovado no **mock**, e as peças novas foram portadas para
      `static/src/tema-dimap.dev.css` e renderizadas no styleguide antes de qualquer template da
      aplicação usá-las.

## 3 · Domínio
A hierarquia já está persistida em `Unidade.pai` desde a SPEC 003; o que nasce aqui é a **regra** sobre
ela: onde **uma** unidade está no organograma. A saída tem as duas direções que a unidade vê de si — o
caminho que sobe até o topo e a subárvore que pende dela — e a de baixo é uma **árvore**, não um
conjunto: é a forma que o desenho precisa, e o conjunto de ids se lê dela.

A regra não sabe **por que** se pergunta a posição. Ela recebe a unidade; quem a escolhe é o
consumidor, e é isso que permite a mesma peça responder três perguntas: qual caminho nasce aberto na
página da unidade, qual é o organograma inteiro — a posição da raiz — e o que pende das unidades
dirigidas por um perfil, na SPEC `autorizacao/004`.

**Irmandade não é campo da posição.** As irmãs de uma unidade são as outras filhas do pai dela, e o
template as tem em mãos porque desenha a árvore inteira; um campo próprio seria o mesmo dado numa
segunda forma.

**`services/domain/arvore_hierarquica/models.py`**
```python
class ParHierarquia(BaseModel):
    """Uma aresta do organograma, achatada. O domínio recebe a hierarquia inteira assim porque não lê
    banco."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    # Exatamente um pai, e só o topo do organograma não tem nenhum.
    pai_id: int | None


class NoHierarquia(BaseModel):
    """Uma unidade e o que pende dela, em qualquer profundidade. Sem filhas em qualquer nível: alto na
    hierarquia não implica ter subordinada."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    filhas: tuple["NoHierarquia", ...] = ()

    @computed_field
    @property
    def ids(self) -> frozenset[int]:
        """Derivado: a conferência de alvo pergunta pertinência, e guardar o conjunto ao lado da
        árvore seria o mesmo dado em dois campos livres para divergir."""
        return frozenset({self.unidade_id}).union(*(filha.ids for filha in self.filhas))


class PosicaoHierarquica(BaseModel):
    """Onde uma unidade está no organograma, vista dela mesma."""

    model_config = ConfigDict(frozen=True)

    # Do topo até o pai, nessa ordem; vazia quando o ego é o topo.
    acima: tuple[int, ...]
    ego: NoHierarquia


class ComandoPosicao(BaseModel):
    model_config = ConfigDict(frozen=True)

    unidade_id: int
    pares: tuple[ParHierarquia, ...]
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`Unidade.pai`](003-hierarquia-unidades.md) — "quem pende de quem?"; a árvore persistida, sem
  alteração.
- [`Unidade.cor`](005-cor-da-unidade.md) — "de que cor é o ponto deste card?".
- [a página da unidade](016-pagina-da-unidade.md) — "onde a seção entra, e como o contexto dela é
  montado?".

**Mock:** [018-mock-arvore-hierarquica.html](018-mock-arvore-hierarquica.html) — leia a skill `mock`.

## 4 · Fora de escopo
- **União das subárvores de várias unidades dirigidas** por um perfil — SPEC `autorizacao/004`, que
  compõe a posição de cada uma; a regra aqui responde por uma unidade só.
- Guardar na URL qual nó está aberto, para recarga e botão "voltar" do navegador — sem dono ainda (§7).
- Filtrar ou buscar unidade dentro do organograma — sem dono ainda.
- Mover unidade arrastando o card — a edição segue nos modais da SPEC 016.
- Ler no card a competência de cada unidade — SPECs `autorizacao/007` e `008`.

## 5 · Peças de referência a compor
- `@apps/user_admin/models/unidade.py` → `Unidade.pai` / `filhas`: a árvore persistida.
- `@apps/user_admin/context.py` (SPEC 016) → `contexto_unidade`: a montagem do contexto da página.
- `@apps/user_admin/paleta.py` → `hex_da_cor`: o slug da cor vira o hex do ponto.
- `@templates/user_admin/unidade.html` (SPEC 016) → a página que recebe a seção.
- `@services/domain/servidores_listagem/__init__.py` → o padrão de reexport dos contratos do submódulo.
- `@static/src/tema-dimap.dev.css` → `.card-well`, `.glass-panel`, `.dot-unidade`, `.etched-line`,
  `.etched-deeper`, `.icon-glow`, `.text-overline`.
- `@templates/partials/_filtros_gravacao.html` → os `defs` sem os quais a gravação não desenha.
- Skills: `componentes-frontend`, `daisyui`, `mock`, `ontologia`, `escrever-testes`,
  `test-django-views`.

## 6 · Snippets

**`services/domain/arvore_hierarquica/posicao.py`** — só a regra; os DTOs ficam em `models.py`, como
nos demais submódulos.
```python
class ArvoreHierarquica:
    """A hierarquia percorrida a partir de uma unidade. Recebe as arestas por DTO: a regra é testável
    sem banco, e o organograma cabe numa consulta só."""

    def __call__(self, comando: ComandoPosicao) -> PosicaoHierarquica:
        return self.pipeline(comando)

    def pipeline(self, comando: ComandoPosicao) -> PosicaoHierarquica:
        # Os dois índices são as duas direções de leitura da mesma aresta.
        pai_de = self._indexar_pais(comando.pares)
        filhas_de = self._indexar_filhas(comando.pares)
        return PosicaoHierarquica(
            acima=self._subir_ate_o_topo(comando.unidade_id, pai_de),
            ego=self._descer(comando.unidade_id, filhas_de, visitados=set()),
        )

    def _subir_ate_o_topo(
        self,
        unidade_id: int,
        pai_de: Mapping[int, int | None],
    ) -> tuple[int, ...]:
        """Um pai por unidade, então subir é um caminho, não uma busca. Sai do topo para o pai porque
        é essa a ordem em que o organograma se lê."""
        trilha: list[int] = []
        atual = pai_de.get(unidade_id)
        # `not in trilha` é a guarda do ciclo longo: o banco só barra a unidade que é pai de si
        # mesma (SPEC 003), e A→B→A subiria para sempre.
        while atual is not None and atual not in trilha:
            trilha.append(atual)
            atual = pai_de.get(atual)
        return tuple(reversed(trilha))

    def _descer(
        self,
        unidade_id: int,
        filhas_de: Mapping[int, tuple[int, ...]],
        visitados: set[int],
    ) -> NoHierarquia:
        # A mesma guarda, do outro lado: sem o conjunto de visitados, A→B→A recursiona até estourar
        # a pilha.
        visitados.add(unidade_id)
        return NoHierarquia(
            unidade_id=unidade_id,
            filhas=tuple(
                self._descer(filha, filhas_de, visitados)
                for filha in filhas_de.get(unidade_id, ())
                if filha not in visitados
            ),
        )
```

**`apps/user_admin/consulta.py`** — a borda: banco → DTO, numa consulta só.
```python
def posicao_de(unidade_id: int) -> PosicaoHierarquica:
    """Duas colunas de um organograma de dezenas de linhas: ler tudo custa menos que uma recursão em
    SQL, e mantém a regra fora do ORM."""
    pares = tuple(
        ParHierarquia(unidade_id=pk, pai_id=pai_id)
        for pk, pai_id in Unidade.objects.values_list("id", "pai_id")
    )
    return ArvoreHierarquica()(ComandoPosicao(unidade_id=unidade_id, pares=pares))
```

**`apps/user_admin/context.py`** — a mesma regra, duas perguntas: a árvore inteira sai da posição da
raiz, e o caminho que nasce aberto sai da posição da unidade da página.
```python
def contexto_organograma(unidade_em_foco: Unidade | None) -> dict[str, Any]:
    # A regra devolve ids; o template precisa de unidades. Casar as duas coisas aqui é o que impede o
    # domínio de conhecer `Unidade` e o template de conhecer id solto.
    raizes = Unidade.objects.filter(pai__isnull=True).order_by("sigla")
    arvores = [posicao_de(raiz.pk).ego for raiz in raizes]
    caminho = frozenset(posicao_de(unidade_em_foco.pk).acima) if unidade_em_foco else frozenset()
    por_id = Unidade.objects.in_bulk(
        frozenset(unidade_id for arvore in arvores for unidade_id in arvore.ids)
    )
    return {
        "ramos": [_ramo(arvore, por_id, caminho, unidade_em_foco) for arvore in arvores],
        "unidade_em_foco": unidade_em_foco,
    }


def _ramo(
    no: NoHierarquia,
    por_id: Mapping[int, Unidade],
    caminho: frozenset[int],
    em_foco: Unidade | None,
) -> dict[str, Any]:
    """O card sai daqui já sabendo o que é: fora do caminho, no caminho, ou em foco. Quem decide o
    estado inicial é o servidor; o JS só o move a partir dali."""
    unidade = por_id[no.unidade_id]
    return {
        "unidade": unidade,
        "cor_hex": hex_da_cor(unidade.cor),
        "no_caminho": no.unidade_id in caminho,
        "em_foco": em_foco is not None and no.unidade_id == em_foco.pk,
        "filhas": [_ramo(filha, por_id, caminho, em_foco) for filha in no.filhas],
    }
```

**`apps/user_admin/views.py`** — a seção nasce com a página; percorrer não vai ao servidor.
```python
def arvore_de_unidades(request: HttpRequest) -> HttpResponse:
    """Rota de leitura, como a página da unidade (SPEC 016). Sem unidade em foco: a página do
    organograma abre no topo."""
    return render(request, TEMPLATE_ARVORE, contexto_organograma(None))
```

**`templates/user_admin/partials/_no_arvore.html`** — a recursão vive no template, que se inclui a si
mesmo por nível.
```html
{# As classes de estado são o contrato com o JS: `no-arvore-caminho` e `no-arvore-ego` dizem o que
   está escavado, e é sobre elas que o CSS revela nível, nome e elo. #}
<div class="no-arvore {% if forloop.first %}no-arvore-primeiro{% endif %}
            {% if no.no_caminho %}no-arvore-caminho{% endif %}
            {% if no.em_foco %}no-arvore-ego{% endif %}"
     {% if no.em_foco %}data-ego-inicial{% endif %}>
  <span class="etched-line no-arvore-barra"></span>
  <div class="card-unidade {% if no.no_caminho or no.em_foco %}card-unidade-poco{% else %}glass-panel{% endif %}">…</div>
  {% if no.filhas %}
    <div class="no-arvore-filhas">
      {% for filha in no.filhas %}
        {% include "user_admin/partials/_no_arvore.html" with no=filha %}
      {% endfor %}
    </div>
  {% else %}
    <p class="no-arvore-vazio">Nenhuma unidade subordinada.</p>
  {% endif %}
</div>
```

**`static/src/js/ui/arvore_hierarquica.js`** — o único estado que o cliente guarda é qual card está
escavado; nada de domínio.
```javascript
function moverEgo(organograma, alvo, alternar = true) {
  const jaEraEgo = alvo.classList.contains("no-arvore-ego");
  const caminho = new Set();
  for (let no = alvo; no; no = paiDoNo(no)) caminho.add(no);
  organograma.querySelectorAll(".no-arvore").forEach((no) => {
    no.classList.remove("no-arvore-caminho", "no-arvore-ego");
    // Ramo abandonado se fecha; o caminho mantém aberto o que já estava.
    if (!caminho.has(no)) no.classList.remove("no-arvore-aberto");
  });
  ...
}

document.querySelectorAll(".organograma .no-arvore").forEach(vestir);
```

## 7 · Caveats
**Abrir e fechar a árvore é JavaScript**, com o organograma inteiro renderizado pelo servidor e o CSS
revelando nível, nome e elo a partir de duas classes de estado. O §3.1 do CLAUDE.md veda estado de
domínio no cliente, não estado visual de controle, e o usuário aprovou este caso; a alternativa era uma
ida ao servidor por passo do grafo. Custo: quem desliga o JavaScript vê a árvore no estado que o
servidor entregou e não a percorre.

**A seção da página da unidade carrega o organograma inteiro**, e não só o caminho até ela. Sem todos
os nós no DOM não há o que revelar no clique, e o mesmo partial serve às duas telas. Custo: a página da
unidade transporta todas as unidades da Secretaria a cada carga, e isso deixa de ser barato se a árvore
crescer para além da DIMAP.

**A regra devolve a subárvore inteira, e a seção desenha um nível por vez.** A mesma saída serve ao
organograma, ao caminho que nasce aberto e à conferência de alvo da SPEC `autorizacao/004`, que
pergunta só pertinência — e derivar as três de uma só é o que impede elas divergirem. Custo: quem quer
só pertinência paga a montagem da árvore inteira antes.

**A árvore é montada em Python, sobre todos os pares `(unidade, pai)` carregados numa consulta.**
Manter a regra fora do ORM é o que a torna testável sem banco (§3.3), e o organograma da DIMAP é menor
que o custo de uma recursão em SQL. Custo: o contexto pergunta a posição uma vez por raiz e mais uma
para o caminho, e cada pergunta recarrega os pares.

**O ciclo longo é contornado na montagem, não barrado no banco.** A SPEC 003 recusa a unidade que é pai
de si mesma e nada mais, e uma recursão sem guarda estouraria a pilha em `A→B→A`. Custo: o ciclo passa
a ser tolerado silenciosamente — a subida e a descida param, mas ninguém é avisado de que o organograma
está torto.

**O card escavado não usa o `.card-well` do tema, e sim a profundidade do sulco do `.scroll-etched`.**
O poço do tema é calibrado para superfície de seção e não se lê num card de 6rem. Custo: passa a haver
duas profundidades de poço no design system, e quem criar peça pequena precisa saber qual escolher.

**O contexto casa ids com unidades numa segunda consulta.** Sem ela o domínio conheceria `Unidade` para
já devolver sigla e cor. Custo: duas consultas por seção, e a de `in_bulk` traz a unidade inteira quando
o card usa três campos.

**O que está aberto não vai para a URL.** Empurrar o estado do organograma para a barra de endereço
faria a página da unidade ter duas identidades — a unidade e o ponto onde alguém parou de navegar.
Custo: recarregar devolve a árvore ao caminho da unidade da página, e o "voltar" do navegador não
desfaz um passo do percurso.

## 8 · Testes (TDD)
Os cinco primeiros são domínio puro e rodam na suíte padrão; os três últimos exercitam as páginas e
carregam o marker `banco`.

- `test_posicao_traz_o_caminho_e_a_subarvore` — a partir de uma unidade no meio, `acima` sai do topo
  até o pai e `ego` desce em todos os níveis; nenhum outro ramo entra.
- `test_posicao_do_topo_nao_tem_caminho` — a unidade sem pai devolve `acima` vazio, e `ego` é o
  organograma inteiro.
- `test_posicao_de_folha_tem_ego_sem_filhas` — unidade sem subordinadas devolve `ego` sem filhas, não
  árvore vazia, e o caminho segue preenchido.
- `test_ids_leem_a_propria_arvore` — `ids` traz o nó e todas as descendentes em qualquer profundidade,
  e nenhuma unidade acima.
- `test_posicao_nao_trava_em_ciclo` — par que fecha ciclo não recursiona sem fim, na subida nem na
  descida, e não repete nó.
- `test_secao_traz_o_organograma_inteiro_com_o_caminho_marcado` — a seção da página da unidade traz
  todas as unidades, com as do caminho marcadas como escavadas e a da página como a em foco.
  *(marker `banco`)*
- `test_cada_card_leva_a_pagina_da_sua_unidade` — cada card do organograma carrega o caminho para a
  página da unidade que representa. *(marker `banco`)*
- `test_pagina_da_arvore_abre_no_topo` — a página do organograma traz todas as unidades e nenhuma
  unidade em foco. *(marker `banco`)*
