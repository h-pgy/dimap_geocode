---
spec: autorizacao/005
versao: v1
atualizado_em: 2026-08-07
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC autorizacao/005 — Contrato de menu e router de ações

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como desenvolvedor da plataforma, quero declarar quais ações compõem cada menu e receber, para o
usuário da vez, só as que ele pode executar — já com o caminho do partial de cada uma —, para que
montar um menu novo seja compor peças existentes em vez de escrever autorização de novo.

## Critérios de aceite
- [ ] Cada menu declara **em código** quais ações contém; a ação **não sabe** em que menu aparece.
- [ ] O router devolve **apenas os itens liberados** para o perfil, na **ordem declarada** pelo menu.
- [ ] Menu sem nenhum item liberado devolve coleção **vazia**, sem erro — o menu decide o que fazer
      com isso.
- [ ] **Superusuário** recebe todos os itens do menu.
- [ ] O item devolvido carrega o que a renderização precisa: caminho do partial, URL resolvida,
      rótulo, tooltip e **a variante de ícone escolhida pelo menu**.
- [ ] O router é **puro** e testável sem banco.

## Contexto e decisões de arquitetura

Esta SPEC entrega a montagem do menu; quem desenha o resultado é a SPEC 006.

**O menu pinça a ação.** O registro de itens vive no app do menu, não no contrato da ação — a
dependência anda numa direção só. É isso que permite a mesma ação aparecer em dois menus com
apresentação diferente, e que impede a busca de conhecer ação alguma (§3.5).

**Tipos no lugar central, registros nos apps.** `ContratoMenu` e `ItemDeMenu` moram junto do
catálogo; cada app declara os seus menus usando esses tipos. Sem app de menu, porque não há
comportamento comum a extrair — só vocabulário.

**`ItemDeMenu` é onde mora a apresentação.** É ele que escolhe a variante de ícone, a **forma**
(linha compacta ou cartão explicativo, SPEC 006) e a ordem. A ação declara *quais* variantes possui
(SPEC 001); qual usar e em que forma é decisão de quem exibe. Ordem é a de declaração: campo de
ordenação seria um segundo lugar para dizer a mesma coisa.

**O router recebe o conjunto de slugs liberados, não o usuário.** Isso o mantém puro e testável sem
banco: quem traduz usuário → conjunto é um resolvedor fino na borda, que consulta o backend da SPEC
003 uma vez só. Passar o usuário para dentro do router acoplaria a montagem do menu ao ciclo de
request e obrigaria banco em todo teste de composição.

**Superusuário precisa de tratamento explícito no resolvedor.** O atalho do `PermissionsMixin` vale
para `has_perm`, não para "liste tudo que ele pode" — sem essa linha, o superusuário veria menu
vazio enquanto conseguiria executar tudo pela URL. É o tipo de divergência entre UX e autorização
que o §3.5 manda evitar.

## Peças de referência a compor
- `@apps/competencias/declaracao.py` (SPEC 001) → `AcaoImplementada` e `VarianteIcone`: o item
  referencia a ação declarada, não a redescreve.
- `@apps/competencias/backends.py` (SPEC 003): o resolvedor pergunta ao backend, com o cache por
  instância de usuário que ele já mantém.
- `@apps/search/views.py` → `REGISTRO_SECOES`: precedente de registro tipado por app; os menus
  seguem a mesma natureza.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/competencias/menus.py — os TIPOS; os registros vivem nos apps que têm menu.
class FormaItem(StrEnum):
    LINHA = "linha"
    CARTAO = "cartao"


class ItemDeMenu(BaseModel):
    model_config = ConfigDict(frozen=True)

    acao: AcaoImplementada
    # Quem exibe escolhe o tamanho do glifo; a ação só declara os que possui.
    variante_icone: VarianteIcone
    # Linha compacta ou cartão explicativo (SPEC 006): também é escolha de quem exibe.
    forma: FormaItem


class ContratoMenu(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    nome: str
    # Ordem de exibição é a de declaração: campo de ordenação seria um segundo lugar para o mesmo.
    itens: tuple[ItemDeMenu, ...]


class MontagemMenu(BaseModel):
    model_config = ConfigDict(frozen=True)

    menu: ContratoMenu
    slugs_liberados: frozenset[str]


class ItemRenderizavel(BaseModel):
    model_config = ConfigDict(frozen=True)

    partial: str
    url: str
    rotulo: str
    tooltip: str
    slug: str
    variante_icone: VarianteIcone


class MenuResolvido(BaseModel):
    model_config = ConfigDict(frozen=True)

    itens: tuple[ItemRenderizavel, ...]


class RoteadorMenu:
    def __call__(self, montagem: MontagemMenu) -> MenuResolvido: ...
```

```python
# apps/competencias/resolucao.py
def slugs_liberados(usuario: AbstractBaseUser | AnonymousUser) -> frozenset[str]:
    """Borda entre o request e o router. Superusuário recebe o catálogo inteiro: o atalho do
    PermissionsMixin cobre has_perm, não a enumeração."""
    ...
```

## Fora de escopo
- Renderizar o menu: átomo de ícone, molécula do item e organismo do menu são a SPEC 006.
- Agrupamento e separadores dentro do menu.
- Gaveta da entidade territorial — depende dos tipos de entidade do épico de busca.
- Menu que muda conforme o tipo de entidade: aqui o menu é uma declaração fixa; a gaveta escolherá
  qual contrato usar quando existir.

## Testes (TDD)
Os três primeiros são puros e rodam na suíte padrão. O último exercita o resolvedor com `Perfil`
gravado e carrega o marker `banco`.

- `test_router_devolve_apenas_liberados_na_ordem_declarada` — item sem slug liberado some; os que
  ficam preservam a ordem do contrato.
- `test_router_devolve_vazio_sem_nenhum_liberado` — menu sem item liberado resolve para coleção
  vazia, sem erro.
- `test_item_carrega_a_variante_de_icone_do_menu` — dois menus com a mesma ação e variantes
  diferentes produzem itens diferentes: a apresentação é do menu, não da ação.
- `test_resolvedor_libera_o_catalogo_inteiro_para_superusuario` — superusuário recebe todos os slugs;
  anônimo recebe conjunto vazio. *(marker `banco`)*

## Patches

_Nenhum patch registrado até o momento._
