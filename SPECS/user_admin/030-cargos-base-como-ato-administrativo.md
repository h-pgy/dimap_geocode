---
spec: user_admin/030
versao: v2
atualizado_em: 2026-09-05
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: implementado — os 14 testes da SPEC passam; migração gerada e pendente de aplicação pelo
    usuário. O teste de listagem virou `test_corpo_sempre_traz_os_extintos_marcados`, no molde
    final de user_admin/029 (Caveats): a listagem nasce direto com o toggle 100% client-side, sem
    passar pela versão que fala com o servidor — o §8 tinha ficado com o nome antigo
    (`test_listagem_esconde_extintos_sem_o_toggle`) de antes dessa correção existir.
---

# SPEC user_admin/030 — Cargos base como ato administrativo

## 1 · User story
O administrador do sistema cria, edita, extingue e reativa cargos base no catálogo da DIMAP para
que a estrutura de cargos acompanhe as alterações do quadro sem que ninguém seja nomeado num cargo
em extinção.

## 2 · Condições de pronto
- [ ] **Qualquer servidor autenticado** abre a lista de cargos base na tabela-onsen, com o toggle
      **Mostrar cargos extintos** e, por linha, o lápis e a lixeira — que abrem os modais de editar
      e de extinguir **já com o cargo da linha escolhido**; os mesmos modais, abertos pelos cards do
      painel, vêm sem cargo escolhido.
- [ ] Criar, editar, extinguir e reativar são **exclusivos do administrador do sistema**: para os
      demais os cards não aparecem, e as rotas recusam mesmo com concessão gravada.
- [ ] Editar cargo base **nunca recusa nome nem sigla**, ocupado ou extinto — cargo base não tem
      nível, natureza nem alta administração, e não há nada a travar.
- [ ] Extinguir **data** o cargo e o tira das opções de nomeação do cadastro e da edição de servidor
      — **menos para quem já o ocupa**, que continua vendo o seu marcado e selecionado.
- [ ] Cargo base extinto **continua sendo avaliado normalmente**: quem o ocupa segue exercendo as
      competências dele e podendo receber concessão nova.
- [ ] Em toda tela em que um cargo base aparece, o extinto vem com **o mesmo rótulo** (`nome`) **em
      tom de warning e o tooltip "Cargo Extinto"** — nenhum texto a mais; reativar devolve o cargo à
      nomeação e retira a cor e o tooltip.
- [ ] Os quatro atos ficam **registrados** com a operação (`criar`, `editar`, `extinguir`,
      `reativar`), `alvo_tipo="cargo_base"` e o **nome do cargo**.
- [ ] A aba **Administração do Sistema** ganha, ao lado do grupo "Cargos em Comissão", o grupo
      **"Cargos Base"**, com a **lista** e os quatro cards. Como a lista é leitura aberta, quem não
      administra o sistema segue vendo os dois catálogos e nada mais.
- [ ] O design foi aprovado no mock, e as peças novas foram portadas para o tema e o styleguide
      antes de qualquer template da aplicação usá-las.

## 3 · Domínio

`CargoBase` ganha a mesma data de extinção de
[`CargoComissao`](029-cargos-em-comissao-como-ato-administrativo.md#3--domínio), sem os campos de
natureza — que ela nunca teve.

**`apps/cargos/models/cargos.py`**

```python
class CargoBase(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    sigla = models.CharField(max_length=20, unique=True)
    # NOVO: mesma forma de `CargoComissao.extinto_em` — nula é cargo vigente.
    extinto_em = models.DateField(null=True, blank=True)

    @property
    def extinto(self) -> bool:
        return self.extinto_em is not None
```

`CargoBase.objects` **continua devolvendo os extintos**, pelo mesmo motivo de `CargoComissao`: quem
filtra é a nomeação (§6), não o gerente do model.

**`services/domain/cargos/models.py`** — os dois catálogos vivem no mesmo submódulo; estes DTOs
entram ao lado dos de `CargoComissao`, sem os reaproveitar: `IdentidadeCargo` carrega `padrao`, que
cargo base não tem.

```python
class IdentidadeCargoBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo_id: int
    nome: str


class PreviaDaExtincaoCargoBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo: IdentidadeCargoBase
    ocupantes: int
    ja_extinto: bool = False


class PreviaDaReativacaoCargoBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo: IdentidadeCargoBase
    ja_vigente: bool = False
```

Consumido de SPECs anteriores, sem recópia:

- [`Veredito`](029-cargos-em-comissao-como-ato-administrativo.md#3--domínio) — esta SPEC pergunta se
  o veredito de ato repetido serve aos dois catálogos: serve, o tipo só carrega `pode`/`motivo`.
- [`ocupantes_no_quadro`](029-cargos-em-comissao-como-ato-administrativo.md#6--snippets) — esta SPEC
  pergunta se a contagem aceita `CargoBase` além de `CargoComissao`: aceita, os dois expõem `.perfis`
  pelo mesmo `related_name` e o filtro (`is_active`, sem exoneração) é idêntico.
- [`Acao` e `AcaoImplementada`](../autorizacao/001-catalogo-de-acoes-em-codigo.md) e a
  [proteção de rota com registro](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) —
  esta SPEC pergunta a eles como mais quatro atos sem alcance e exclusivos do superusuário se
  inscrevem e se registram.
- [`ABA_ADMINISTRACAO`](029-cargos-em-comissao-como-ato-administrativo.md#6--snippets) — esta SPEC
  pergunta onde o grupo novo entra: ao lado de "Cargos em Comissão", na mesma aba.

**Mock:** [030-mock-cargos-base.html](030-mock-cargos-base.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Histórico de alterações do cargo base além do registro de execução — sem dono ainda.
- Página própria do cargo base, com os servidores que já o ocuparam — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/cargos/extincao.py` → `extinguir_cargo`/`reativar_cargo` — forma do ato reversível com
  prévia, veredito e desfecho.
- `@apps/cargos/consulta.py` → `cargos_nomeaveis`/`ocupantes_no_quadro` — mesmo predicado, outro
  catálogo.
- `@apps/cargos/views.py` → `gravar_extincao` — o molde HTTP das quatro gravações.
- `@templates/unidades/partials/_tabela_unidades.html`, `_corpo_unidades.html`,
  `_barra_acoes_unidades.html` → tabela-onsen com coluna do lápis, coluna da lixeira, toggle de
  extintas e barra de ações.
- `@templates/cargos/partials/_rotulo_cargo.html` → a marca de cor + tooltip do cargo extinto.
- `@apps/competencias/utils.py` → `instanciar_acao`.
- `@apps/competencias/protecao.py` → `acao_protegida`, `registrar_ato`.
- Skills: `acao-administrativa`, `painel`, `componentes-frontend`, `mock`, `ontologia`,
  `escrever-testes`.

## 6 · Snippets

**`services/domain/cargos/avaliador.py`** — a mesma regra de ato repetido, para o outro catálogo.

```python
class AvaliadorExtincaoCargoBase:
    def __call__(self, previa: PreviaDaExtincaoCargoBase) -> Veredito:
        if previa.ja_extinto:
            return Veredito(pode=False, motivo="Este cargo já está extinto.")
        return Veredito(pode=True)


class AvaliadorReativacaoCargoBase:
    def __call__(self, previa: PreviaDaReativacaoCargoBase) -> Veredito:
        if previa.ja_vigente:
            return Veredito(pode=False, motivo="Este cargo não está extinto.")
        return Veredito(pode=True)
```

**`apps/cargos/consulta.py`**

```python
def cargos_base_nomeaveis(cargo_atual_id: int | None = None) -> QuerySet[CargoBase]:
    """Mesmo predicado de `cargos_nomeaveis`, sobre o outro catálogo."""
    nomeaveis = Q(extinto_em__isnull=True)
    if cargo_atual_id is not None:
        nomeaveis |= Q(pk=cargo_atual_id)
    return CargoBase.objects.filter(nomeaveis).order_by("nome")


# ALTERADO nesta SPEC: aceita os dois catálogos — ambos expõem `.perfis` pelo mesmo related_name.
def ocupantes_no_quadro(cargo: CargoBase | CargoComissao) -> int:
    return cargo.perfis.filter(is_active=True, exonerado_em__isnull=True).count()
```

**`apps/cargos/cadastro.py`** — sem travas: cargo base não tem campo que a ocupação proteja.

```python
def editar_cargo_base(cargo: CargoBase, valores: Mapping[str, Any]) -> DesfechoCargoBase:
    leitura = ler_cargo_base(valores)
    if leitura.dto is None:
        return DesfechoCargoBase(cargo=None, recusa=leitura.recusa or RecusaDeFormulario())
    cargo.nome = leitura.dto.nome
    cargo.sigla = leitura.dto.sigla
    try:
        with transaction.atomic():
            cargo.full_clean()
            cargo.save()
    except ValidationError as recusa:
        return DesfechoCargoBase(cargo=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoCargoBase(cargo=cargo)
```

**`apps/cargos/extincao.py`** — mesma forma de `extinguir_cargo`/`reativar_cargo`, outro model.

```python
def extinguir_cargo_base(cargo: CargoBase, hoje: date) -> DesfechoCargoBase:
    veredito = avaliar_extincao_cargo_base(previa_da_extincao_base(cargo))
    if not veredito.pode:
        return DesfechoCargoBase(cargo=None, recusa=recusa_do_veredito(veredito.motivo))
    cargo.extinto_em = hoje
    cargo.save(update_fields=["extinto_em"])
    return DesfechoCargoBase(cargo=cargo)
```

**`apps/user_admin/context.py`** — o cadastro/edição de servidor deixa de ofertar cargo base
extinto, salvo para quem já o ocupa.

```python
def _catalogos_de_lotacao(
    ids_permitidos: Collection[int] | None = None,
    cargo_base_atual: int | None = None,
    cargo_comissao_atual: int | None = None,
) -> dict[str, Any]:
    return catalogo_de_unidades(ids_permitidos) | {
        "cargos_base": cargos_base_nomeaveis(cargo_base_atual),
        "cargos_comissao": cargos_nomeaveis(cargo_comissao_atual),
    }
```

**`templates/cargos/partials/_rotulo_cargo_base.html`** — a mesma marca, sem o `padrão ·` que
cargo base não tem.

```django
<span class="rotulo-cargo{% if cargo.extinto %} rotulo-cargo-extinto{% endif %}"
      {% if cargo.extinto %}title="Cargo Extinto"{% endif %}>{{ cargo.nome }}</span>
```

**`apps/painel/abas_declaradas.py`**

```python
# ABA_ADMINISTRACAO (029) ganha um segundo grupo, ao lado de "Cargos em Comissão" — mesmo molde,
# outro catálogo.
Grupo(
    rotulo="Cargos Base",
    itens=(
        ItemLivre(
            slug="painel.lista_cargos_base",
            nome="Cargos base",
            tooltip="O catálogo de cargos base da DIMAP e quem os ocupa.",
            url_name="cargos:listar_cargos_base",
        ),
        ItemAcao(acao=ACAO_CRIAR_CARGO_BASE, partial=PARTIAL_CARTAO_MODAL),
        ItemAcao(acao=ACAO_EDITAR_CARGO_BASE, partial=PARTIAL_CARTAO_MODAL),
        ItemAcao(acao=ACAO_EXTINGUIR_CARGO_BASE, partial=PARTIAL_CARTAO_MODAL),
        ItemAcao(acao=ACAO_REATIVAR_CARGO_BASE, partial=PARTIAL_CARTAO_MODAL),
    ),
),
```

## 7 · Caveats

**O veredito de ato repetido se duplica entre os dois catálogos.** `AvaliadorExtincaoCargoBase` e
`AvaliadorReativacaoCargoBase` repetem, linha a linha, a regra de `AvaliadorExtincaoCargo` e
`AvaliadorReativacaoCargo`. Generalizar exigiria uma identidade de cargo comum aos dois catálogos,
acoplando cargo base ao `padrao` que só `CargoComissao` tem. O custo é mudar a mesma regra em dois
lugares se ela mudar.

**`CargoBase.objects` continua trazendo os extintos**, pelo mesmo motivo de `CargoComissao`: o
único ponto que filtra é `cargos_base_nomeaveis`. O custo é o mesmo — um ponto novo de nomeação que
esqueça o filtro nomeia em cargo extinto em silêncio.

**Renomear pela tela briga com a seed.** `seed_cargos` usa o `nome` do cargo base como chave natural
e só cria o que falta, então um cargo renomeado pela tela é **recriado** com o nome antigo na
próxima carga. Aceito enquanto a seed for bootstrap.

**Oito ações exclusivas do superusuário para dois catálogos que não compram granularidade nenhuma.**
Criar, editar, extinguir e reativar cargo base somam-se às quatro de `CargoComissao` (029) só para o
rastro distinguir os atos. O custo são mais quatro pastas de ícone, quatro cards e quatro linhas no
registro.

## 8 · Testes (TDD)

**Comportamento**

- `test_extinguir_data_o_cargo_base_e_o_tira_da_nomeacao` — depois do ato, `extinto_em` está
  preenchido e `cargos_base_nomeaveis()` não devolve o cargo. *(marker `banco`)*
- `test_cargo_base_extinto_segue_ofertado_a_quem_ja_o_ocupa` —
  `cargos_base_nomeaveis(cargo_atual_id=...)` devolve o extinto do próprio servidor, e só ele.
  *(marker `banco`)*
- `test_reativar_devolve_o_cargo_base_a_nomeacao` — `extinto_em` volta a ser nulo e o cargo
  reaparece na oferta. *(marker `banco`)*
- `test_cargo_base_extinto_continua_exercendo_competencia` — perfil com cargo base extinto e
  concessão gravada segue com `has_perm` verdadeiro. *(marker `banco`)*
- `test_edicao_altera_nome_e_sigla_de_cargo_base_ocupado_e_extinto` — a mesma tela grava nome e
  sigla, ocupado ou extinto, sem recusa nenhuma. *(marker `banco`)*
- `test_veredito_recusa_ato_repetido_cargo_base` — extinguir o já extinto e reativar o vigente são
  recusados com motivo; domínio puro, sem banco.
- `test_corpo_sempre_traz_os_extintos_marcados` — o servidor sempre manda o extinto, com
  `class="linha-extinta"`; esconder é 100% client-side (`filtro_linha_extinta.js`, mesmo módulo de
  user_admin/029), fora do alcance deste teste. *(marker `banco`)*
- `test_listagem_aberta_a_qualquer_autenticado` — servidor sem caneta alguma recebe 200 na lista, e
  ela não traz os gestos de ato. *(marker `banco`)*

**Segurança da ação** (skill `acao-administrativa`; fora do teto)

- `test_anonimo_vai_ao_login_sem_registrar` — as quatro rotas redirecionam e não deixam linha.
  *(marker `banco`)*
- `test_autenticado_sem_competencia_recebe_403_e_fica_registrado` — a negativa aparece no histórico.
  *(marker `banco`)*
- `test_concessao_gravada_nao_abre_acao_exclusiva_de_superusuario` — nem concessão nem direção de
  unidade liberam os quatro atos. *(marker `banco`)*
- `test_ato_grava_quem_cargo_unidade_operacao_e_alvo` — a linha registra a lotação do momento e o
  nome do cargo base alvo. *(marker `banco`)*
- `test_extinguir_e_reativar_ficam_distinguiveis_no_registro` — as operações opostas não se
  confundem no rastro. *(marker `banco`)*
- `test_gravacao_so_por_post` — as rotas de gravação recusam GET, e abrir o modal não pratica ato.
  *(marker `banco`)*
