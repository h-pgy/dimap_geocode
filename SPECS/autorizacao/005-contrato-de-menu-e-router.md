---
spec: autorizacao/005
versao: v5
atualizado_em: 2026-08-17
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: o item renderizável leva nome e nome curto (as duas formas da SPEC 006 nomeiam a ação de
    jeitos diferentes); o item recusa variante de ícone que a ação não declara; o superusuário
    recebe os slugs do registro em código
  - v3: sem mudança de escopo — a SPEC foi reescrita no formato de seções numeradas da skill
    `specs`, com a justificativa toda concentrada em Caveats
  - v4: o campo `ItemDeMenu.acao` passa a se chamar `acao_implementada` — o tipo já é
    `AcaoImplementada`, e o nome curto escondia que `.acao.acao` atravessa duas camadas
    (envelope → contrato)
  - v5: testes da §8 escritos (`tests/apps/competencias/test_menus.py` e `test_resolucao.py`) e
    falhando por ausência dos módulos — `testes_tdd: true`
---

# SPEC autorizacao/005 — Contrato de menu e router de ações

## 1 · User story
**Requisito não-funcional** — declarar quais ações compõem um menu passa a ser compor peças existentes,
e o que chega à renderização já é só o que o usuário da vez pode executar, com o caminho do partial de
cada item.

## 2 · Condições de pronto
- [ ] Cada menu declara **em código** quais ações contém; a ação **não sabe** em que menu aparece.
- [ ] O router devolve **apenas os itens liberados** para o perfil, na **ordem declarada** pelo menu.
- [ ] Menu sem nenhum item liberado devolve coleção **vazia**, sem erro — o menu decide o que fazer com
      isso.
- [ ] **Superusuário** recebe todos os itens do menu — e nenhum de ação que saiu do código.
- [ ] O item devolvido carrega o que a renderização precisa: caminho do partial, URL resolvida, **nome e
      nome curto**, tooltip e **a variante de ícone escolhida pelo menu**.
- [ ] Menu que escolhe uma variante de ícone que a ação **não declara** é recusado na construção do
      contrato, não no render.
- [ ] O router é **puro** e testável sem banco.

## 3 · Domínio
O menu **pinça** a ação: a declaração vive no app que tem menu, e a ação não sabe onde aparece. A mesma
ação pode compor dois menus com apresentação diferente.

**`apps/competencias/menus.py`** — os tipos; os registros vivem nos apps que têm menu.
```python
class FormaItem(StrEnum):
    LINHA = "linha"
    CARTAO = "cartao"


class ItemDeMenu(BaseModel):
    """A apresentação de uma ação DENTRO de um menu. É aqui que ela mora, não no contrato da ação."""

    model_config = ConfigDict(frozen=True)

    # Nome não é "acao": o valor é o envelope de implementação, não o contrato (SPEC 001).
    acao_implementada: AcaoImplementada
    # Entre as que a ação declara possuir: pedir uma que ela não tem é erro de declaração.
    variante_icone: VarianteIcone
    # Linha compacta ou cartão explicativo (SPEC 006): também é escolha de quem exibe.
    forma: FormaItem


class ContratoMenu(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    nome: str
    # Ordem de exibição é a de declaração: campo de ordenação seria um segundo lugar para o mesmo.
    itens: tuple[ItemDeMenu, ...]
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`AcaoImplementada` e `VarianteIcone`](001-catalogo-de-acoes-em-codigo.md) — "o que esta ação é, como
  ela está montada na interface, e quais variantes de ícone ela possui?".
- [`RegistroAcoes`](001-catalogo-de-acoes-em-codigo.md) — "quais ações existem hoje?", que é o conjunto
  do superusuário.
- [`CompetenciaPermissionBackend`](003-avaliador-e-backend-de-autorizacao.md) — "quais slugs este perfil pode
  executar?", com o cache por instância de usuário que ele já mantém.

## 4 · Fora de escopo
- Renderizar o menu: átomo de ícone, molécula do item e organismo do menu — SPEC 006.
- Agrupamento e separadores dentro do menu — sem dono ainda.
- Gaveta da entidade territorial — épico de busca, quando os tipos de entidade existirem.
- Menu que muda conforme o tipo de entidade — aqui o menu é declaração fixa; a gaveta escolherá qual
  contrato usar.

## 5 · Peças de referência a compor
- `@apps/competencias/schemas.py` (SPEC 001) → `AcaoImplementada`, e `@services/domain/autorizacao` →
  `VarianteIcone`.
- `@apps/competencias/registro.py` (SPEC 001) → `REGISTRO`: a enumeração do superusuário sai daqui.
- `@apps/competencias/backends.py` (SPEC 003): o resolvedor pergunta ao backend.
- `@apps/search/views.py` → `REGISTRO_SECOES`: precedente de registro tipado por app.
- Skills: `escrever-testes`.

## 6 · Snippets

**`apps/competencias/menus.py`** — a validação da variante acontece ao construir o item, não no render.
```python
class ItemDeMenu(BaseModel):
    ...

    @model_validator(mode="after")
    def _variante_declarada(self) -> "ItemDeMenu":
        # O fallback da SPEC 006 existe para arquivo faltando em runtime, não para esconder erro de
        # declaração. Como o item já compõe a ação, a checagem é local — dispensa system check.
        if self.variante_icone not in self.acao_implementada.acao.variantes_icone:
            raise ValueError(...)
        return self
```

**`apps/competencias/menus.py`** — o que entra e o que sai do router.
```python
class MontagemMenu(BaseModel):
    model_config = ConfigDict(frozen=True)

    menu: ContratoMenu
    # O router recebe o CONJUNTO, não o usuário: é o que o mantém puro e testável sem banco.
    slugs_liberados: frozenset[str]


class ItemRenderizavel(BaseModel):
    model_config = ConfigDict(frozen=True)

    partial: str
    url: str
    # A linha compacta usa o curto; o cartão nomeia por extenso e usa o tooltip como descrição.
    nome: str
    nome_curto: str
    tooltip: str
    slug: str
    variante_icone: VarianteIcone
    forma: FormaItem


class MenuResolvido(BaseModel):
    model_config = ConfigDict(frozen=True)

    itens: tuple[ItemRenderizavel, ...]
```

**`apps/competencias/menus.py`** — o router: filtra e resolve, sem decidir competência.
```python
class RoteadorMenu:
    def __call__(self, montagem: MontagemMenu) -> MenuResolvido:
        # A ordem é a da declaração, e o menu vazio é resposta válida: quem decide o que fazer com
        # nenhum item é a tela (SPEC 006), não o router.
        return MenuResolvido(
            itens=tuple(
                self._renderizavel(item)
                for item in montagem.menu.itens
                if item.acao_implementada.acao.slug in montagem.slugs_liberados
            ),
        )

    def _renderizavel(self, item: ItemDeMenu) -> ItemRenderizavel:
        # nome_curto é opcional na ação (SPEC 001): a forma compacta cai no nome quando falta.
        ...
```

**`apps/competencias/resolucao.py`** — a borda entre o request e o router.
```python
def slugs_liberados(usuario: AbstractBaseUser | AnonymousUser) -> frozenset[str]:
    """Superusuário recebe o registro inteiro: o atalho do PermissionsMixin cobre `has_perm`, não a
    enumeração — sem esta linha ele veria menu vazio e executaria tudo pela URL."""
    if getattr(usuario, "is_superuser", False):
        # Do registro em código, não da tabela projetada: o registro é, por construção, só o que
        # existe hoje, e ler dali dispensa filtrar por `ativa`.
        return frozenset(item.acao.slug for item in REGISTRO.todas())
    ...
```

## 7 · Caveats
**Os tipos moram no app `competencias` e os registros de menu, nos apps que têm menu.** Não há app de
menu porque não há comportamento comum a extrair — só vocabulário. Custo: todo app que declarar um menu
passa a importar `competencias`, o que amarra a ordem de import e faz um erro de declaração derrubar a
subida em vez de aparecer no render.

**O router recebe o conjunto de slugs, não o usuário.** É o que o mantém puro e testável sem banco;
passar o usuário para dentro acoplaria a montagem do menu ao ciclo de request. Custo: quem chama precisa
lembrar de resolver o conjunto antes, e o resolvedor é mais um ponto entre a tela e a autorização.

**O superusuário é enumerado a partir do registro em código, não da tabela projetada.** O registro é, por
construção, só o que existe hoje, e ler dali dispensa filtrar por `ativa`. Custo: o menu do superusuário
e as telas que consultam a projeção (SPEC 002) podem discordar entre uma subida e outra do serviço.

**O item de menu não é revalidado quando a ação muda.** A variante é conferida na construção, que
acontece no import do módulo de menus. Custo: ação que perde uma variante de ícone em runtime — o que só
acontece com recarga de código — deixa o item apontando para um glifo que não existe mais, e quem cobre
isso é o fallback da SPEC 006.

## 8 · Testes (TDD)
Os quatro primeiros são puros e rodam na suíte padrão. O último exercita o resolvedor com `Perfil`
gravado e carrega o marker `banco`.

- `test_router_devolve_apenas_liberados_na_ordem_declarada` — item sem slug liberado some; os que ficam
  preservam a ordem do contrato.
- `test_router_devolve_vazio_sem_nenhum_liberado` — menu sem item liberado resolve para coleção vazia,
  sem erro.
- `test_item_carrega_a_variante_de_icone_do_menu` — dois menus com a mesma ação e variantes diferentes
  produzem itens diferentes: a apresentação é do menu, não da ação.
- `test_item_recusa_variante_que_a_acao_nao_declara` — pedir um glifo que a ação não possui é recusado ao
  construir o item.
- `test_resolvedor_libera_o_catalogo_inteiro_para_superusuario` — superusuário recebe todos os slugs;
  anônimo recebe conjunto vazio. *(marker `banco`)*
