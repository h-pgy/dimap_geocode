---
spec: formularios/001
versao: v1
atualizado_em: 2026-08-22
testes_tdd: true
implementado: false
changelog:
  - v1: versão inicial
---

# SPEC formularios/001 — Erros de formulário: mensagem semântica e realce do controle

## 1 · User story
Quem preenche um formulário da plataforma recebe, na recusa, o formulário de volta com o motivo em
português e **o controle errado destacado**, para corrigir o que falhou sem adivinhar qual campo era.

## 2 · Condições de pronto
- [ ] A recusa chega ao template como **mensagem em português** e **classe de realce por controle**:
      `{{ realce.<controle> }}` devolve a tonalidade do erro, e **string vazia** para o controle que
      não foi recusado.
- [ ] Um formulário **declara em código** o mapeamento `controle × tipo de erro → mensagem + tom`, e a
      regra declarada vence a regra padrão do tipo.
- [ ] Recusa vinda do **Pydantic** e recusa vinda do **model do Django** produzem a mesma estrutura: a
      mensagem que a fonte já dá em português é preservada, e a que vem em inglês é substituída pela do
      catálogo.
- [ ] Recusa que **não nomeia controle algum** aparece na tarja e não realça nada; controle recusado
      que não está no catálogo é traduzido pelo próprio nome, sem quebrar a tradução.
- [ ] O sufixo `_id` do DTO e o `name=` do controle chegam ao **mesmo** realce: `unidade_id` e
      `unidade` são o mesmo campo na tela.
- [ ] Ler o formulário devolve **ou o DTO ou a recusa**, num resultado único — nenhuma view e nenhum
      ato escreve `try/except` para isso.
- [ ] `services/utils/erros_formulario` **não importa Django**: a ponte para o `ValidationError` do
      model mora em `apps/core`.
- [ ] A skill `erros-de-formulario` documenta o contrato, o catálogo, o padrão da view que devolve o
      próprio formulário em 422 e a aplicação do realce no template; a skill
      `pydantic-validation-errors` passa a remeter a ela e declara que o partial genérico não serve a
      formulário cujo alvo HTMX é ele mesmo.
- [ ] **Nenhuma peça visual nasce aqui**: os quatro `.campo-realce-*` já estão no tema e no styleguide,
      e esta SPEC define quem os veste.

## 3 · Domínio
Uma recusa de formulário tem duas pontas: a **fonte**, que sabe qual campo e que tipo de erro, e a
**tela**, que precisa de uma frase e de uma cor. O catálogo é o que liga uma à outra, e é declarado
junto do formulário que o usa.

**`services/utils/erros_formulario/models.py`**
```python
class TomDeRealce(StrEnum):
    """As quatro tonalidades do átomo `.campo-realce-*`. O valor É a classe: o template recebe a
    string pronta e nenhum filtro monta nome de classe por concatenação."""

    ERRO = "campo-realce-erro"
    ALERTA = "campo-realce-alerta"
    INFO = "campo-realce-info"
    SUCESSO = "campo-realce-sucesso"


class RegraDeErro(BaseModel):
    """O que uma recusa vira na tela. `mensagem` aceita `{rotulo}`."""

    model_config = ConfigDict(frozen=True)

    mensagem: str
    tom: TomDeRealce = TomDeRealce.ERRO


class CampoDeFormulario(BaseModel):
    """Um controle. `controle` é o `name=` do input — o mesmo nome que o template pergunta ao realce."""

    model_config = ConfigDict(frozen=True)

    controle: str
    rotulo: str
    # Por tipo de erro; vence REGRAS_PADRAO. Vazio significa "as padrão bastam".
    regras: Mapping[str, RegraDeErro] = Field(default_factory=dict)


class Formulario(BaseModel):
    """O catálogo: os controles que existem e como cada recusa se diz para quem preencheu."""

    model_config = ConfigDict(frozen=True)

    campos: tuple[CampoDeFormulario, ...]

    @property
    def por_controle(self) -> Mapping[str, CampoDeFormulario]:
        return {campo.controle: campo for campo in self.campos}


class ErroBruto(BaseModel):
    """A recusa como a fonte a entrega, antes de virar frase. `mensagem` preenchida é a fonte já
    falando português — o Django fala; o Pydantic, não."""

    model_config = ConfigDict(frozen=True)

    controle: str
    tipo: str
    mensagem: str | None = None


class CampoRecusado(BaseModel):
    model_config = ConfigDict(frozen=True)

    controle: str
    mensagem: str
    tom: TomDeRealce


class RecusaDeFormulario(BaseModel):
    """O que a view leva ao template."""

    model_config = ConfigDict(frozen=True)

    campos: tuple[CampoRecusado, ...] = ()
    # Recusa que não nomeia controle: o `__all__` do Django, a regra que cruza dois campos.
    gerais: tuple[str, ...] = ()

    @property
    def mensagens(self) -> tuple[str, ...]:
        return tuple(campo.mensagem for campo in self.campos) + self.gerais

    @property
    def realce(self) -> Mapping[str, str]:
        """`{{ realce.email }}` devolve a classe; chave ausente já rende string vazia no Django."""
        return {campo.controle: campo.tom.value for campo in self.campos}


class LeituraDeFormulario[T: BaseModel](BaseModel):
    """Ou o DTO, ou a recusa — nunca os dois, nunca nenhum. É o que dispensa o `try/except` de quem
    lê um formulário."""

    model_config = ConfigDict(frozen=True)

    dto: T | None = None
    recusa: RecusaDeFormulario | None = None
```

O átomo `.campo-realce-*` que o `TomDeRealce` nomeia foi aprovado no mock de
[criacao_usuarios/004](../criacao_usuarios/004-mock-criar-servidor.html) e está portado no tema e no
styleguide; esta SPEC não desenha peça alguma, só declara quem a aplica.

## 4 · Fora de escopo
- Aplicar o contrato nos formulários já existentes — unidade, impedimento, exercício: cada um na SPEC
  do seu épico.
- O consumo pela criação de servidor — SPEC [criacao_usuarios/004](../criacao_usuarios/004-criar-servidor.md);
  pela edição — SPEC [criacao_usuarios/005](../criacao_usuarios/005-editar-servidor.md).
- Realce nos tons **alerta**, **info** e **sucesso** com consumidor real — sem dono ainda.
- Validação no cliente, antes do POST — sem dono ainda.
- Reescrever `templates/partials/erro_validacao.html`: ele segue servindo às rotas que não são
  formulário — sem dono ainda.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.campo-realce-erro`, `-alerta`, `-info`, `-sucesso`: o átomo,
  portado e renderizado no styleguide.
- `@apps/core/middleware.py` → `PydanticValidationMiddleware`: o tratamento genérico, que segue
  valendo fora de formulário.
- `@services/utils/html` → o molde de pacote de `services/utils/`: `models.py`, a peça, e um
  `__init__.py` que só reexporta.
- `pydantic` → `ErrorDetails`: o tipo já pronto do `ValidationError.errors()`.
- `django.core.exceptions.ValidationError` → `error_dict`: o dicionário que preserva o `code` de cada
  recusa, ao contrário do `message_dict`.
- Skills: `ontologia`, `componentes-frontend`, `htmx`, `pydantic-validation-errors`,
  `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/utils/erros_formulario/regras.py`** — o que vale quando o formulário não declara nada.
```python
# O Pydantic classifica por tipo; é aqui que cada tipo vira frase. Formulário nenhum precisa
# redeclarar "preencha o campo" — só o que for particular dele.
REGRAS_PADRAO: Mapping[str, RegraDeErro] = {
    "missing": RegraDeErro(mensagem="Preencha o campo {rotulo}."),
    "string_too_short": RegraDeErro(mensagem="Preencha o campo {rotulo} com a quantidade mínima de caracteres."),
    "string_too_long": RegraDeErro(mensagem="{rotulo}: texto longo demais."),
    "int_parsing": RegraDeErro(mensagem="{rotulo}: escolha uma opção da lista."),
    "value_error": RegraDeErro(mensagem="{rotulo}: valor inválido."),
}
REGRA_DESCONHECIDA = RegraDeErro(mensagem="{rotulo}: valor inválido.")
```

**`services/utils/erros_formulario/tradutor.py`** — o catálogo aplicado.
```python
class TradutorDeRecusa:
    """Callable: erros crus → o que a tela mostra. O catálogo é do formulário e não muda entre
    requisições, então ele é do construtor; o que varia é a recusa."""

    def __init__(self, formulario: Formulario) -> None:
        self.formulario = formulario

    def __call__(self, erros: Sequence[ErroBruto]) -> RecusaDeFormulario:
        return self.pipeline(erros)

    def pipeline(self, erros: Sequence[ErroBruto]) -> RecusaDeFormulario:
        catalogo = self.formulario.por_controle
        recusados = [erro for erro in erros if erro.controle in catalogo]
        soltos = [erro for erro in erros if erro.controle not in catalogo]
        return RecusaDeFormulario(
            campos=tuple(self._recusar(erro, catalogo[erro.controle]) for erro in recusados),
            # Erro que não bate com controle algum — o `__all__` do Django, ou um campo do DTO que
            # não tem input (a `url_acesso` resolvida na orquestração) — não realça nada: não há o
            # que destacar, e inventar um controle apontaria o dedo para o campo errado.
            gerais=tuple(erro.mensagem for erro in soltos if erro.mensagem),
        )

    def _recusar(self, erro: ErroBruto, campo: CampoDeFormulario) -> CampoRecusado:
        regra = self._regra(erro, campo)
        # A mensagem da fonte vence a do catálogo: quem já fala português é o model, e o texto da
        # unicidade mora junto da constraint que a define.
        mensagem = erro.mensagem or regra.mensagem.format(rotulo=campo.rotulo)
        return CampoRecusado(controle=campo.controle, mensagem=mensagem, tom=regra.tom)

    def _regra(self, erro: ErroBruto, campo: CampoDeFormulario) -> RegraDeErro:
        if erro.tipo in campo.regras:
            return campo.regras[erro.tipo]
        return REGRAS_PADRAO.get(erro.tipo, REGRA_DESCONHECIDA)
```

**`services/utils/erros_formulario/leitor.py`** — o `try` que ninguém mais escreve.
```python
class LeitorDeFormulario[T: BaseModel]:
    """Callable: o POST cru vira o DTO do formulário, ou a recusa traduzida. É esta peça que tira o
    `ValidationError` do caminho do `PydanticValidationMiddleware` — ver Caveats."""

    def __init__(self, dto: type[T], formulario: Formulario) -> None:
        self.dto = dto
        self.tradutor = TradutorDeRecusa(formulario)

    def __call__(self, valores: Mapping[str, Any]) -> LeituraDeFormulario[T]:
        try:
            return LeituraDeFormulario(dto=self.dto.model_validate(valores))
        except ValidationError as recusa:
            return LeituraDeFormulario(recusa=self.tradutor(de_pydantic(recusa.errors())))


def de_pydantic(erros: Sequence[ErrorDetails]) -> tuple[ErroBruto, ...]:
    # `mensagem` fica vazia de propósito: o Pydantic escreve em inglês e por tipo, e quem traduz é
    # o catálogo.
    return tuple(
        ErroBruto(controle=controle_do_campo(str(erro["loc"][0])), tipo=erro["type"])
        for erro in erros
    )


def controle_do_campo(campo: str) -> str:
    """O model diz `unidade`, o DTO diz `unidade_id`, o `<select>` se chama `unidade`: o sufixo cai
    para os três virarem um nome só."""
    return campo.removesuffix("_id")
```

**`apps/core/erros_formulario.py`** — a ponte do Django, e o único módulo desta SPEC que o importa.
```python
def de_validation_error(recusa: ValidationError) -> tuple[ErroBruto, ...]:
    """`error_dict`, e não `message_dict`: só ele preserva o `code` de cada recusa, que é o tipo do
    erro. A mensagem vem junto porque o Django já a escreve em português — e, no caso da unicidade,
    é o próprio model quem a define."""
    return tuple(
        ErroBruto(
            controle=controle_do_campo(campo),
            tipo=erro.code or TIPO_SEM_CODIGO,
            mensagem=mensagem,
        )
        for campo, erros in recusa.error_dict.items()
        for erro in erros
        for mensagem in erro.messages
    )
```

**`apps/<app>/formularios.py`** — como um formulário se declara. O catálogo é código, ao lado do app
que renderiza a tela.
```python
FORMULARIO_SERVIDOR = Formulario(
    campos=(
        CampoDeFormulario(controle="rf", rotulo="RF"),
        CampoDeFormulario(controle="nome", rotulo="Nome"),
        CampoDeFormulario(controle="sobrenome", rotulo="Sobrenome"),
        CampoDeFormulario(
            controle="email",
            rotulo="E-mail",
            # A regra particular deste formulário: e-mail torto merece frase melhor que a genérica.
            regras={"value_error": RegraDeErro(mensagem="E-mail inválido: confira o endereço.")},
        ),
        CampoDeFormulario(controle="unidade", rotulo="Unidade"),
        CampoDeFormulario(controle="cargo_base", rotulo="Cargo base"),
        CampoDeFormulario(controle="cargo_comissao", rotulo="Cargo em comissão"),
    )
)

ler_novo_servidor = LeitorDeFormulario(NovoServidor, FORMULARIO_SERVIDOR)
```

**A view que devolve o próprio formulário** — o padrão que o partial genérico não atende.
```python
@require_POST
def gravar(request: HttpRequest) -> HttpResponse:
    # O DTO é montado pelo leitor, e não com `NovoServidor(...)` direto: construído na view, o
    # ValidationError subiria ao PydanticValidationMiddleware, cuja resposta o HTMX troca NO ALVO
    # da requisição — que aqui é o próprio <form>, com outerHTML. A tela sumiria.
    leitura = ler_novo_servidor(valores)
    if leitura.recusa is not None:
        return render(request, TEMPLATE_FORMULARIO, contexto(valores, leitura.recusa), status=422)
```

**`templates/**/_secao_*.html`** — o realce aplicado. Um controle pergunta pelo próprio nome.
```html
{# O realce é do CONTROLE, não do `.form-field`: o rótulo fora dele mantém a linha alinhada com os #}
{# vizinhos da grade. Controle sem recusa devolve string vazia e a classe some.                    #}
<input type="text" name="rf" value="{{ valores.rf|default:'' }}"
       class="input input-glass {{ realce.rf }}" />
<select name="unidade" class="select select-glass {{ realce.unidade }}" data-select-onsen>
```

**`.claude/skills/erros-de-formulario/SKILL.md`** — entregável desta SPEC, não subproduto. Cobre:
declarar o catálogo; ler o formulário pelo leitor em vez de construir o DTO na view; devolver o
formulário em 422; aplicar `{{ realce.<controle> }}`; e **quando o `PydanticValidationMiddleware`
ainda vale** — toda rota que não é formulário, onde o alvo do swap não é a tela que o usuário
preenche.

## 7 · Caveats
**Esta SPEC não traz mock, embora entregue efeito visual.** Os quatro `.campo-realce-*` foram
aprovados no mock de `criacao_usuarios/004` e já estão no tema e no styleguide; o que falta não é
desenho, é a regra de quem os veste. Custo: a única prova visual do contrato é o mock de outra SPEC,
e quem revisar esta aqui precisa abrir aquele.

**O contrato vive em `services/utils/`, mas a ponte do Django vive em `apps/core/`.** O domínio não
importa objeto de interface do Django (CLAUDE.md §3.3), e `ValidationError` é um; `ErroBruto` é a
forma neutra que atravessa a fronteira. Custo: a peça fica partida em dois lugares, e quem procurar
"tradução de erro" acha metade dela de cada lado.

**Formulário cujo alvo HTMX é ele mesmo não usa o `PydanticValidationMiddleware`** — exceção declarada
à skill `pydantic-validation-errors`, que hoje diz "nunca `try/except` na view" sem ressalva. O
middleware responde 422 com um partial que o HTMX troca no alvo da requisição, e o alvo aqui é o
`<form>` com `outerHTML`: um campo em branco apagaria a tela e deixaria uma lista de erros em inglês,
sem nada para corrigir. Custo: passam a existir dois caminhos para o mesmo tipo de exceção, e escolher
o errado só aparece em tela.

**Três dos quatro tons nascem sem consumidor.** Recusa de formulário é erro, e alerta, info e sucesso
só ganham uso quando alguma tela precisar sinalizar sem recusar. Custo: parte do enum não é exercida
por teste nenhum, e pode envelhecer sem que se note.

**O catálogo repete o `name=` do template.** Ele é código para ser revisável em code review, e não há
como derivá-lo do HTML sem parsear template. Custo: renomear um controle no template sem renomear no
catálogo tira o realce daquele campo, calado — o formulário segue funcionando e só o destaque some.

**A mensagem da fonte vence a regra do catálogo.** Quem já escreve em português é o model, e o texto
da unicidade pertence à constraint que a define, não à tela. Custo: para mudar a frase de um erro de
banco é preciso mexer no model — e no `error_messages` dele —, não no catálogo do formulário.

## 8 · Testes (TDD)
- `test_regra_declarada_vence_a_padrao` — o formulário que declara regra para um tipo recebe a frase e
  o tom dela; o tipo não declarado cai na regra padrão.
- `test_realce_traz_a_classe_por_controle` — `realce` devolve a classe do tom para o controle recusado
  e **nada** para os demais, e o template renderiza string vazia na chave ausente.
- `test_tipo_desconhecido_nao_quebra_a_traducao` — erro de tipo fora das regras padrão vira a frase
  genérica, com o rótulo do campo.
- `test_mensagem_da_fonte_e_preservada` — `ErroBruto` com mensagem própria chega intacto à tela; sem
  mensagem, quem escreve é o catálogo.
- `test_erro_sem_controle_vai_para_a_tarja_sem_realce` — recusa cujo campo não está no catálogo entra
  em `gerais` e não realça controle algum.
- `test_sufixo_id_vira_o_nome_do_controle` — `unidade_id` do DTO e `unidade` do model produzem o mesmo
  realce.
- `test_leitor_devolve_o_dto_ou_a_recusa` — entrada válida devolve o DTO e recusa vazia; entrada
  inválida devolve recusa e nenhum DTO, sem levantar exceção.
- `test_ponte_do_django_preserva_o_codigo` — `ValidationError` com `code="unique"` chega como tipo
  `unique`, com a mensagem que o model definiu.
