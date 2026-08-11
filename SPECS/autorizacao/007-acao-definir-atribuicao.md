---
spec: autorizacao/007
versao: v2
atualizado_em: 2026-08-11
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a ação vira estrutural — quem a exerce é o titular da unidade (SPEC titularidade/001), e a
    seed de bootstrap deixa de existir; o menu de administrador passa a ser declarado aqui; o
    catálogo oferecido exclui as ações estruturais
---

# SPEC autorizacao/007 — Definir atribuição: a competência da unidade, e a primeira ação do registro

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como titular de unidade da DIMAP, quero definir quais ações a minha unidade e as unidades abaixo
dela exercem, para que uma competência nova entre em vigor sem ninguém mexer no banco — e para que
os diretores tenham o que distribuir entre os cargos.

## Critérios de aceite
- [ ] Quem abre a tela é **o titular da unidade** (SPEC `titularidade/001`), sem depender de
      atribuição ou concessão gravada; quem não é titular recebe 403 mesmo com concessão da ação.
- [ ] A tela oferece como alvo **a unidade do perfil e as unidades abaixo dela** no organograma;
      unidade superior, irmã ou de outro ramo não aparece — e é recusada se vier no request.
- [ ] O catálogo oferecido traz **apenas as ações ativas e não estruturais** que a unidade-alvo ainda
      **não** tem.
- [ ] Atribuir e remover acontecem **sem recarregar a página**, trocando só o trecho afetado.
- [ ] Remover atribuição que tem concessões **exige confirmação** e diz **quantos cargos** perdem a
      competência; confirmada, as concessões vão junto.
- [ ] Atribuir e remover são **atos registrados** (SPEC 004), distinguíveis pela operação e com o
      alvo identificando unidade e ação.
- [ ] O **menu de administrador** é declarado em código e resolvido pelo router (SPEC 005): mostra
      esta ação a quem pode executá-la e some para quem não pode.
- [ ] O design foi **aprovado no mock** antes de qualquer código de aplicação.
- [ ] As peças novas estão renderizadas no styleguide e suas classes migraram para o CSS base.

## Mock de validação
`SPECS/autorizacao/007-mock-definir-atribuicao.html` — a tela nos seus estados: unidade com
atribuições, unidade sem nenhuma, o seletor da unidade-alvo com a subárvore do perfil, o item da ação
no menu de administrador, o **modal do catálogo** (com ações restantes e com o catálogo esgotado) e o
**modal de confirmação** da remoção que leva concessões junto.

Servir com root na **raiz do projeto** (Live Server). Via `file://` o fetch do tema é bloqueado.

## Contexto e decisões de arquitetura

É o **nível 1** do modelo da SPEC 002 virando ato administrativo: a competência institucional da
unidade deixa de ser linha criada no admin e passa a ser ação com contrato, rota protegida e
registro. O nível 2 — distribuir entre os cargos — é a SPEC 008. Nenhum model novo: a 002 já entregou
as duas tabelas.

**Esta é a primeira ação inscrita no registro**, não a de conceder: a 008 pressupõe atribuição
existente, e quem cria atribuição precisa vir antes.

**Esta ação é estrutural, e é isso que dispensa qualquer seed.** Administrar a competência de uma
unidade é atributo de quem a dirige, não algo que alguém precise conceder. Marcada `estrutural`
(SPEC 001), ela é liberada pela titularidade (SPEC 003 + `titularidade/001`) sem atribuição nem
concessão gravada — e some com isso o ovo-e-galinha que a versão anterior desta SPEC resolvia por
seed: não há primeiro estado a instalar, porque a competência não mora no banco de competências.

O bootstrap do sistema passa a ser um só, e fica no `user_admin`: marcar os titulares. O
superusuário continua passando pelo atalho do `PermissionsMixin` (SPEC 003), agora como ferramenta
de emergência e não como caminho de instalação.

**O Secretário não é caso especial.** Ele é titular da unidade-raiz, e a subárvore da raiz é o
organograma inteiro: o alcance máximo cai fora da mesma regra, sem exceção escrita para a alta
administração.

**Ação estrutural não se atribui.** Oferecê-la no catálogo criaria linha que não libera ninguém —
quem a exerce é o titular. O catálogo filtra pela coluna `estrutural` projetada na SPEC 002, não por
lista de slugs, para que a próxima ação estrutural não precise lembrar de se excluir.

**Unidade nova nasce com a competência, porque nasce com titular.** O organograma cresce em runtime e
a titularidade acompanha, sem carga nenhuma. Enquanto a unidade nova não tem titular, quem a alcança
é o titular do nível acima — é a razão prática de o alcance passar da própria unidade.

**`has_perm` abre a tela; a subárvore é regra do domínio.** A SPEC 003 responde competência na
unidade **do perfil** e nada mais; alcançar as unidades abaixo não é pergunta de autorização, é regra
desta ação. São duas barreiras distintas: o decorator da SPEC 004 barra quem não é titular, e o
domínio recusa unidade-alvo fora da subárvore — é a segunda que impede o POST forjado com unidade de
outro ramo.

**O menu de administrador é declarado aqui.** A SPEC 005 entrega os tipos e manda o registro do menu
viver no app que o tem; como as ações administrativas são todas de `competencias`, o registro fica
nele, e a área administrativa do `user_admin` apenas renderiza o que o router devolveu. A SPEC 008
acrescenta seu item a este mesmo menu — a ação não se inscreve, é o menu que a pinça.

**As duas ações administrativas moram no app de competências, e isso é exceção declarada.** O §3.5
manda cada ação ser um app próprio para que um processo novo da DIMAP não engorde o núcleo — a
dependência que ele evita é a da busca com as ações. Estas duas não são processos da DIMAP: são a
administração da própria competência, operam sobre os models desta SPEC e não existem sem eles. App
separado só faria o par importar `competencias` inteiro para não ganhar nada.

**O alcance é calculado sem banco.** A view carrega os pares `(unidade, pai)` numa consulta e o
domínio caminha a árvore. Manter a regra fora do ORM é o que a torna testável sem banco (§3.3), e o
organograma é pequeno o bastante para que a consulta única seja mais barata que recursão em SQL.

**Alcançar não é herdar.** A subárvore diz sobre **quem pode editar**, não sobre quem exerce: atribuir
uma ação à unidade-mãe não a dá às filhas — a SPEC 002 já decidiu unidade exata, sem herança.

**Autoatribuição é aceita.** O titular atribui à própria unidade, inclusive ação que ele mesmo
passará a exercer. Quem dirige a unidade responde pelo que ela faz; o controle é o registro do ato
(SPEC 004), não uma segunda aprovação.

**A remoção cascateia, por isso pergunta.** `Concessao` cai por CASCADE (SPEC 002): num clique só o
diretor apagaria a distribuição inteira sem ver. A confirmação com a contagem é o único lugar em que
esse efeito fica visível antes de acontecer.

**Uma peça nova só: o cartão da atribuição.** O catálogo do modal é uma grade de `.card-acao` (SPEC
006) e o resto são átomos existentes; o que não existe é o cartão da atribuição já posta,
`.card-atribuicao`. Ele é a **mesma classe** da SPEC 008, aqui no estado sem chips — quem implementar
primeiro a leva ao CSS base e ao styleguide; a outra confere e compõe.

## Peças de referência a compor
- `@apps/competencias/models` (SPEC 002) → `Acao`, `AtribuicaoUnidade`, `Concessao`: a tela cria e
  remove atribuição; a concessão ela só conta.
- `@apps/competencias/utils.py` (SPEC 001) → `instanciar_acao`, e `@apps/competencias/registro.py` →
  `_construir_registro`: esta ação é a primeira inscrita.
- `@apps/competencias/protecao.py` (SPEC 004) → `acao_protegida` e `registrar_ato`.
- `@apps/competencias/menus.py` (SPEC 005) → `ItemDeMenu`, `ContratoMenu` e `RoteadorMenu`: o menu de
  administrador é composto com esses tipos; a ação não se inscreve nele.
- `@apps/user_admin/models` → `Unidade` (`pai`/`filhas`): a árvore que o alcance percorre, sem
  alteração.
- `@apps/user_admin/models/user.py` → `Perfil.e_titular` (SPEC `titularidade/001`): é o que a SPEC
  003 transforma em competência para esta ação.
- `@templates/user_admin/servidores_list.html` → a área administrativa onde o organismo de menu é
  renderizado.
- SPEC 006 → `.card-acao`, `.card-acao-nome`, `.card-acao-descricao`, `.icone-acao`: o cartão
  explicativo é o item do catálogo, sem redesenho.
- Skill `componentes-frontend` → `.card-well`, `.glass-panel`, `.modal-glass` + `.modal-box-glass`,
  `.select-onsen` (SPEC user_admin/011), `.btn-onsen`, `.btn-glass`, `.text-overline`,
  `.dot-unidade`, badges.
- Skill `pydantic-validation-errors`: a view monta o DTO e deixa o middleware tratar — sem
  `try/except`.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/competencias/acoes_declaradas.py
ACAO_DEFINIR_ATRIBUICAO = instanciar_acao(
    slug="competencias.definir_atribuicao",
    nome="Definir atribuições da unidade",
    nome_curto="Atribuições",
    tooltip="Define quais ações a unidade exerce.",
    url_name="competencias:definir_atribuicao",
    partial="competencias/partials/_item_menu_definir_atribuicao.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Quem a exerce é o titular da unidade: não passa por atribuição nem concessão.
    estrutural=True,
)
```

```python
# apps/competencias/menus_declarados.py — o menu pinça a ação; a ação não se inscreve.
MENU_ADMINISTRADOR = ContratoMenu(
    slug="competencias.administrador",
    nome="Administração",
    itens=(
        ItemDeMenu(
            acao=ACAO_DEFINIR_ATRIBUICAO,
            variante_icone=VarianteIcone.PEQUENO,
            forma=FormaItem.LINHA,
        ),
    ),
)
```

```python
# services/domain/autorizacao/alcance.py — mesmo submódulo do avaliador (SPEC 003), não um novo.
class ParUnidade(BaseModel):
    unidade_id: int
    pai_id: int | None


class AlcanceDeUnidades:
    """A unidade de origem e tudo abaixo dela. Recebe os pares por DTO: a regra é testável sem
    banco, e a árvore da DIMAP cabe numa consulta só."""

    def __call__(self, comando: ComandoAlcance) -> frozenset[int]: ...
```

```python
# apps/competencias/views.py
@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def definir_atribuicao(request: HttpRequest) -> HttpResponse:
    # A unidade-alvo é validada contra a subárvore do perfil: sem isso um POST forjado atribui
    # competência em ramo alheio.
    comando = ComandoAtribuicao(
        unidade_origem_id=request.user.unidade_id,
        unidade_alvo_id=request.POST["unidade"],
        acao_slug=request.POST["acao"],
    )
    ...
```

## Fora de escopo
- Distribuir a atribuição entre os cargos: é a SPEC 008.
- Herança de competência pelo organograma — alcançar a unidade filha para editar não é exercer
  (SPEC 002).
- Criar, mover ou renomear unidade, e **marcar quem é titular**: são do `user_admin` (SPEC
  `titularidade/001`).
- Concessão nominal a um servidor, concessão por natureza de cargo, impedimento e substituição.
- Tela de consulta do histórico de execuções.
- Demais ações da plataforma: esta SPEC inscreve uma só.

## Porte obrigatório após a aprovação do mock
As classes novas migram **tal e qual** para `static/src/tema-dimap.dev.css` (fonte única, SPEC
design/004), e cada peça nova é renderizada em
`.claude/skills/componentes-frontend/examples/design_system.html`, na seção da sua camada. A SPEC não
está implementada enquanto os dois portes não tiverem sido feitos. `.card-acao` (SPEC 006) e
`.card-atribuicao` (compartilhada com a SPEC 008) são portadas por quem chegar primeiro — a outra
SPEC confere em vez de reescrever.

## Testes (TDD)
Carregam o marker `banco`, menos o do alcance, que é domínio puro e roda na suíte padrão.

- `test_alcance_cobre_a_subarvore_e_para_no_ramo` — a partir de uma unidade, devolve ela e todas as
  descendentes; nunca a superior, a irmã ou outro ramo. Sem banco.
- `test_tela_abre_para_titular_e_nega_o_resto` — o titular entra sem concessão nenhuma gravada; o
  não-titular da mesma unidade recebe 403 mesmo com concessão da ação.
- `test_catalogo_oferece_so_o_que_falta_e_nao_oferece_estrutural` — a ação já atribuída, a inativa e
  a estrutural ficam fora da oferta.
- `test_atribuir_recusa_unidade_fora_do_alcance` — POST com unidade existente mas de outro ramo é
  recusado mesmo com id válido.
- `test_remover_com_concessoes_exige_confirmacao` — sem confirmação nada é apagado; confirmada, a
  atribuição e as concessões dependentes somem juntas.
- `test_atribuir_e_remover_ficam_registrados_com_alvo` — as duas operações geram execução registrada
  distinguível pela operação, identificando unidade e ação.
- `test_menu_administrador_mostra_a_acao_so_para_quem_pode` — o item aparece para o titular e some
  para quem não é.

## Patches

_Nenhum patch registrado até o momento._
