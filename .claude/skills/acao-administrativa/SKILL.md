---
name: acao-administrativa
description: Como criar uma ação administrativa no DIMAP GeoCoder — o contrato em código, a inscrição no registro, os ícones, a rota protegida, o alcance do alvo, o registro da execução e o menu. Use SEMPRE que a tarefa introduzir uma rotina que exige login e autorização por perfil (cargo × unidade), ao alterar uma ação existente, ou ao escrever a SPEC de uma. Traz também as perguntas a fazer ao usuário antes de escrever e a bateria de checagens de segurança que os testes TDD precisam fixar.
---

# Ação administrativa — contrato, registro, rota protegida e rastro

Ação é **ato administrativo**: recebe uma entidade (territorial ou de cadastro) como input, exige
autenticação, é autorizada por competência (cargo × unidade) e tem a execução **registrada**. O épico
`SPECS/autorizacao/` entregou toda a maquinaria; esta skill é como se pendura uma ação nova nela.

## 1 · O que é ação — e o que não é

| É ação | Não é ação |
|---|---|
| Emitir certidão de lançamento | Ver a ontologia pública de um lote |
| Disparar amostragem de ofertas | Abrir o mapa, buscar um logradouro |
| Definir atribuição da unidade, conceder competência | Ver o próprio perfil |
| Cadastrar servidor, alterar cadastro | Listar servidores, abrir a página de uma unidade |

**Rota que só exige login não é ação.** O registro é curado justamente para manter essa distinção
visível (CLAUDE.md §3.5): entra nele só o que precisa de concessão de competência. Se a rotina não
tem um perfil que possa **não** poder executá-la, ela não é ação — e inscrevê-la só polui o catálogo
e as telas de concessão.

**A busca nunca conhece ação alguma.** A dependência é de mão única: a ação consome o resultado da
busca por DTO. Se você se pegou importando algo de uma ação dentro do núcleo de busca, pare.

## 2 · Antes de escrever: o que perguntar ao usuário

Estas seis coisas mudam o código e **não** se deduzem do pedido. Se a SPEC ou o pedido não disserem,
**pergunte** — em bloco, de uma vez. Se o usuário não responder alguma, siga o default e **diga qual
adotou**.

| Pergunta | Opções | Default se não vier resposta |
|---|---|---|
| **Estrutural ou concedida?** | `estrutural=True`: quem **responde pela direção** da unidade já a exerce, sem atribuição nem concessão gravada. `False`: só exerce quem recebeu concessão para o seu cargo naquela unidade. | `False` — a estrutural é exceção, e hoje só as duas ações de administração de competência a usam. |
| **Tem alcance? Qual?** | Nenhum (a ação não incide sobre unidade — é o caso das que recebem entidade territorial); `UnidadesSubordinadas` (o alvo é uma unidade que o request escolhe). | Sem alcance. Declarar alcance que ninguém confere é pior que não declarar. |
| **O ato altera estado?** | Escrita (POST/PUT/PATCH/DELETE) — registra sozinho. Leitura que **é** o ato (emitir documento) — só registra se a view chamar `registrar_ato`. | Escrita. |
| **Qual a operação e o alvo?** | A `operacao` distingue atos opostos da mesma ação (`atribuir`/`remover`, `conceder`/`revogar`). O alvo é `alvo_tipo` + `alvo_identificador`, texto livre. | Perguntar sempre: sem isso o histórico não diz o que foi feito nem sobre o quê. |
| **Em que app mora?** | App próprio é a regra (§3.5). Exceção só quando a ação administra o próprio domínio do app em que já vive (é o caso de `competencias`), e a exceção vai **declarada em Caveat da SPEC**. | App próprio. |
| **Entra em algum menu?** | Qual menu, qual `VarianteIcone` e qual `FormaItem`. A ação **não** se inscreve em menu: é o menu que a pinça. | Nenhum menu. |

Duas mais, quando couber: **rota aberta** (exceção que só existe declarada na SPEC — o default é
protegida) e **assíncrona** (o default é síncrona; fila só se a SPEC justificar).

## 3 · Os seis passos

### 3.1 Declarar o contrato

O contrato conceitual (`services/domain/autorizacao` → `Acao`) diz **o que a ação é**; o de aplicação
(`apps/competencias/schemas.py` → `AcaoImplementada`) diz **como ela está montada no Django**.
`instanciar_acao` achata os dois no ponto de escrita — o app escreve plano, o contrato guarda
aninhado. **Nunca construa `Acao`/`AcaoImplementada` na mão.**

```python
# apps/<app>/acoes_declaradas.py — ponto único de declaração do app.
from apps.competencias.utils import instanciar_acao
from services.domain.autorizacao import UnidadesSubordinadas, VarianteIcone

ACAO_EMITIR_CERTIDAO = instanciar_acao(
    slug="certidoes.emitir_lancamento",
    nome="Emitir certidão de lançamento",
    nome_curto="Certidão",
    tooltip="Emite o PDF que atesta o lançamento do imóvel no IPTU.",
    url_name="certidoes:emitir",
    # O item genérico da SPEC autorizacao/006: a linha do menu é a mesma para todas as ações.
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    alcance=None,
)
```

Restrições que o contrato cobra na construção (`services/domain/autorizacao/contratos.py` é a fonte):

- **slug `<app>.<nome>`**, `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$` — mesmo formato do
  `app_label.codename` do Django, para o `has_perm` cair na convenção. O prefixo tem que ser um app
  **instalado**.
- **Limites de tamanho** espelhando a projeção no banco: slug 120, nome 120, nome curto 60,
  tooltip 255.
- O slug é chave em **três lugares**: registro em código, tabela projetada e caminho dos ícones.
  Renomear é mover pasta e desativar/recriar a linha no banco — escolha o nome uma vez.

### 3.2 Inscrever no registro

```python
# apps/competencias/registro.py — o ÚNICO módulo que importa os apps de ação.
def _construir_registro() -> RegistroAcoes:
    return RegistroAcoes(acoes=(ACAO_DEFINIR_ATRIBUICAO, ACAO_CONCEDER, ACAO_EMITIR_CERTIDAO))
```

Não existe `autodiscover`, e isso é deliberado: descoberta automática apagaria a distinção que o §1
existe para manter. O preço é lembrar desta linha — e o system check é o que torna o esquecimento
barulhento.

### 3.3 Desenhar os ícones

Uma pasta por ação, dois níveis a partir do slug:

```
static/src/acoes/<app>/<nome>/icones/pequeno.svg
static/src/acoes/<app>/<nome>/icones/grande.svg
```

Só as variantes **declaradas** em `variantes_icone` são cobradas. O SVG entra inline e herda a cor do
texto (`stroke: currentColor`) — não escreva cor dentro dele. Declarar variante sem arquivo derruba a
subida (`competencias.E003`).

### 3.4 A rota, protegida

```python
# apps/<app>/urls.py
app_name = "certidoes"

urlpatterns = [
    path("certidoes/", views.emitir, name="emitir"),
    # Leitura e escrita em rotas separadas: é essa separação, e não uma flag no formulário, que faz
    # "abrir a tela não pratica o ato" ser estrutural.
    path("certidoes/emitir/", views.gravar, name="gravar"),
]
```

**O `url_name` declarado precisa resolver sem argumentos.** O check `competencias.E004` faz
`reverse(url_name)` cru; rota que recebe id no caminho (`<int:pk>`) hoje **não passa** — aponte o
contrato para a rota sem argumento (a tela) ou estenda o check antes, na SPEC que precisar disso.

### 3.5 A view

```python
@acao_protegida(ACAO_EMITIR_CERTIDAO)
@require_POST
def gravar(request: HttpRequest) -> HttpResponse:
    # DTO na fronteira; malformado morre no PydanticValidationMiddleware. Sem try/except na view.
    comando = ComandoEmitirCertidao(contribuinte=request.POST["contribuinte"])
    certidao = emitir_certidao(comando)
    # A view NUNCA chama gravar_execucao: deixa o recado e quem persiste é o decorator, no return.
    registrar_ato(
        request,
        operacao="emitir",
        alvo_tipo="lote",
        alvo_identificador=certidao.contribuinte,
    )
    return render(request, TEMPLATE, contexto(certidao))
```

O que o decorator já fez quando a view começa a rodar, e que ela **não repete**:

1. anônimo → redireciona ao login, **sem gravar linha**;
2. autenticado sem competência → `PermissionDenied` (403) **e linha de negativa**;
3. alvo fora do alcance declarado → 403 **e linha de negativa**, antes de a view rodar;
4. depois do `return`: grava a execução se o método altera estado **ou** se a view deixou recado.

### 3.6 Projetar no banco

A tabela `Acao` é projeção do registro, mantida por `manage.py sincronizar_acoes`, que o
`docker/entrypoint.sh` roda a cada subida do web. **O agente não roda o comando** — ele toca banco
com estado real, e isso é do usuário (CLAUDE.md §4). Relate que falta rodar.

Ação que sai do registro é **desativada**, nunca apagada; de volta, reativa com atribuições e
concessões intactas.

## 4 · Alcance — até onde a ação incide

Competência responde **em que unidade** o perfil exerce; alcance responde **sobre qual unidade** ele
pode incidir. São conferências distintas, e as duas vivem no decorator.

- `alcance=None` — a ação não incide sobre unidade. Nada a conferir.
- `alcance=UnidadesSubordinadas()` — o alvo é uma unidade, nomeada por um parâmetro do request
  (`parametro_id_unidade_alvo`, hoje `"unidade"`), e precisa estar entre as que o perfil **dirige**
  ou abaixo delas (`alcance_do_perfil`, em `apps/competencias/consulta.py`).

Três regras que valem para qualquer alcance:

- **O alvo derivado de um objeto nunca vem do request.** Se a unidade a conferir é a de um servidor,
  de um lote ou de um processo, ela é **lida no banco** a partir do id do objeto. Aceitar a unidade
  vinda do cliente é abrir a ação inteira: basta mandar a própria.
- **Requisição que altera estado é obrigada a trazer o parâmetro** — ausente, é 400. Em leitura, a
  ausência é a tela ainda sem alvo escolhido e passa.
- **Alcance novo é subtipo de `TipoAlcance`** mais um ramo no `isinstance` de `conferir_alvo`. O
  `else` levanta `NotImplementedError` de propósito: é o ponto de extensão, e ele não deixa passar
  batido. Não coloque a regra num método do subtipo — o contrato Pydantic mora em `services/domain/`
  e não pode depender de `apps/` (§3.3).

E a consequência que se esquece: **quem dirige a unidade-raiz alcança o organograma inteiro.** O que
o contém é o registro do ato, não uma segunda barreira.

## 5 · Menu e botão — o router filtra, a rota decide

O menu **pinça** a ação; a ação não sabe em que menu aparece.

```python
# apps/<app>/menus_declarados.py
MENU_X = ContratoMenu(
    slug="<app>.<menu>",
    nome="…",
    itens=(ItemDeMenu(acao_implementada=ACAO_X, variante_icone=VarianteIcone.PEQUENO, forma=FormaItem.LINHA),),
)
```

`RoteadorMenu` devolve só os itens liberados, na ordem declarada, e `slugs_liberados`
(`apps/competencias/resolucao.py`) resolve o conjunto — superusuário recebe o registro inteiro.
Para um botão solto, `{% if perms.<app>.<nome> %}` já responde pela competência, servido pelo backend
de autorização.

**Esconder o botão é UX, não segurança.** A barreira é o `acao_protegida` da rota, sempre. E um botão
que depende também de **alcance** precisa do alcance resolvido na view — `perms` sozinho não sabe
sobre qual objeto você está.

## 6 · Checagens de segurança nos testes TDD

Toda ação nova carrega esta bateria. Não é cobertura: é o conjunto de situações em que a autorização
falha silenciosamente e ninguém percebe até alguém praticar um ato que não podia. Escolha os que se
aplicam (os marcados **sempre** se aplicam a qualquer ação) e escreva-os **antes** do código.

**Eles não entram no teto de 10 testes da §8 da SPEC** (skill `specs`). O teto existe para conter
teste de comportamento que engessa refactor; estes fixam **quem pode praticar o ato**, e cortar um
deles para caber na conta é escolher não testar uma porta. Na §8, liste os dois grupos separados —
o comportamento da ação primeiro, a bateria de segurança depois.

| # | O que fixar | Falha que ele pega |
|---|---|---|
| 1 | **sempre** — anônimo é mandado ao login, não recebe 403, e **não deixa linha** | rota esquecida sem `@acao_protegida` |
| 2 | **sempre** — autenticado sem competência recebe **403** e a tentativa **fica registrada** | negativa silenciosa, invisível no histórico |
| 3 | **sempre** — quem tem a concessão **em outra unidade** não passa | herança de competência pelo organograma, que não existe |
| 4 | **sempre** — perfil **fora de exercício** (impedido ou exonerado) não exerce nada, nem a estrutural — **mas os dois desfechos HTTP são diferentes**: impedido continua autenticado e recebe **403** (`has_perm` nega por `em_exercicio`); exonerado (`is_active=False`) já não está autenticado — o `ModelBackend` do Django recusa resolver a sessão dele a cada request (`is_active=False` é "inclusive não entrar", desde a SPEC user_admin/001), então ele chega ao decorator como anônimo e recebe **302** para o login, sem linha de negativa. Não force os dois a esperar 403 no mesmo teste HTTP. | afastado que continua assinando; ou o teste que espera 403 do exonerado e nunca é satisfeito, porque o Django já o desautenticou antes do decorator rodar |
| 5 | ação com alcance — alvo de **outro ramo** é recusado com 403 **com id válido**, sem a view conferir nada | conferência que ficou só na tela |
| 6 | ação com alcance — **POST sem o parâmetro** do alvo é recusado com 400 | request forjado que escapa da conferência inteira |
| 7 | alvo derivado de objeto — mandar a **própria unidade** no request não abre o objeto de outro ramo | a origem lida do cliente em vez do banco |
| 8 | ação estrutural — quem **responde pela direção** entra sem concessão gravada; quem não dirige e não tem concessão, não | a estrutural virando concessão comum, ou o contrário |
| 9 | substituição — o substituto exerce a competência do **cargo do substituído, na unidade dele**, e o registro diz **por quem respondia** | ato descrito pelo cargo errado no histórico |
| 10 | **sempre** — o ato autorizado grava **quem, cargo e unidade do momento**, operação e alvo; mudar a lotação depois não altera a linha | histórico que se reescreve com o cadastro |
| 11 | operações opostas da mesma ação ficam **distinguíveis** pela operação gravada | `atribuir` e `remover` indistinguíveis no rastro |
| 12 | leitura autorizada **não** vira linha; a mesma leitura negada, sim | histórico afogado em GET de navegação |
| 13 | ação inativa (fora do registro) não libera ninguém, mesmo com concessão gravada | ação removida do código que segue executável |
| 14 | segredo que o ato manipula (senha, token) **não aparece** na resposta nem no registro | credencial vazando em HTML ou em log |
| 15 | escrita só por `POST` (`@require_POST`), e rota de confirmação **não** altera nada | apagar por GET, que qualquer prefetch dispara |

Onde eles moram: `tests/apps/<app>/test_views.py` para o contrato HTTP, `tests/apps/competencias/`
para o que é da maquinaria. Praticamente todos exigem `Perfil` gravado — carregam o marker `banco`,
que vai declarado em `markers_obrigatorios` da SPEC e precisa rodar verde
(`uv run pytest -m banco`) antes de `implementado: true`.

Um teste de domínio puro sempre cabe junto: a regra do ato em si (o que ele calcula, emite ou grava)
mora em `services/` ou no módulo do app e se testa sem HTTP.

## 7 · Erros comuns

- **Conferir alcance dentro da view.** A declaração no contrato existe para que ninguém repita — e
  esqueça — a segunda conferência. Se o decorator não alcança o seu caso, estenda o `TipoAlcance`.
- **Chamar `gravar_execucao` da view.** A ponte é `registrar_ato`; quem persiste é o decorator,
  depois do `return`.
- **`try/except` na view** para validação — construa o DTO e deixe o `PydanticValidationMiddleware`
  interceptar. `try/except` de regra vive no módulo do ato, não na view.
- **Registrar no catálogo uma rotina que só exige login.** Polui o catálogo e as telas de concessão.
- **Esconder o botão e achar que protegeu.** UX não é barreira.
- **Inscrever a ação e esquecer o ícone** (ou o inverso): os dois são cobrados pelo check no boot,
  então isso quebra a subida — o que é o comportamento desejado, mas descubra rodando
  `uv run python manage.py check` antes de entregar.
- **Rodar `sincronizar_acoes` ou `migrate`.** Banco é do usuário.
