---
spec: faq/002
versao: v5
atualizado_em: 2026-11-17
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: upload de imagem inline no editor e vínculo de vídeos (MP4 e YouTube)
  - v3: separa entrada do YouTube de imagens/MP4 e abre modal de metadados no drag-and-drop
  - v4: adapta snippets ao modelo Resposta e renomeia autores para usuarios_upload
  - v5: extrai upload de imagens e vídeos para faq/004, mantendo aqui apenas edição textual
---

# SPEC faq/002 — Edição da FAQ pelo administrador

## 1 · User story
O administrador do sistema (superusuário) escreve, revisa e publica FAQs, no contexto de uma área
própria, para manter a FAQ em dia sem depender de deploy nem de desenvolvedor.

## 2 · Condições de pronto
- [ ] O design da área de edição foi aprovado no mock e as peças foram portadas para o tema e o
      styleguide antes de o template da aplicação usá-las.
- [ ] Só superusuário entra nas telas de edição. Servidor logado sem a marca recebe 403, e anônimo é
      levado ao login.
- [ ] O administrador vê e edita só as FAQs **que ele criou** e as **FAQs do sistema** (carregadas pela
      seed). A FAQ de outro administrador não aparece na lista e não abre nem pelo id na URL.
- [ ] A FAQ é escrita num editor visual (negrito, listas, links, títulos) e é gravada como markdown.
      Reaberta, aparece exatamente como foi escrita.
- [ ] A FAQ nova nasce em **rascunho** e **pública**. Publicar faz a FAQ aparecer na página de FAQ, e
      despublicar a devolve a rascunho e a tira da página.
- [ ] Pergunta ou variação já usada por outra FAQ devolve o formulário com a mensagem em português no
      campo exato, e nada é gravado.
- [ ] Editar a FAQ trocando a pergunta principal por uma de suas próprias variações é aceito.
- [ ] O administrador cria tema e subtema e renomeia temas existentes pela própria área de edição.
- [ ] Excluir uma FAQ a tira da página e libera as perguntas dela para uso em outra FAQ.

## 3 · Domínio

A ontologia da FAQ e da `Resposta` é a de [faq/001 §3](001-pagina-de-faq.md#3--domínio). Esta SPEC
pergunta a ela quem pode alterar uma FAQ e como uma FAQ existente é regravada.

```python
class Editor(BaseModel):
    """O superusuário que está editando. A marca de superusuário é conferida na view."""
    perfil_id: int


class Edicao(BaseModel):
    """Pedido de regravação de uma FAQ existente, pelo editor."""
    faq: Faq                              # com `id` preenchido; `autor_id` é ignorado na regravação
    editor: Editor
```

**Mock:** [002-mock-edicao-de-faq.html](002-mock-edicao-de-faq.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Anexos documentais (PDF/DOCX) com extração de texto na edição — faq/003.
- Envio de imagens no editor, upload/importação de vídeos MP4 e modal de metadados — faq/004.
- Vínculo da FAQ às telas do sistema — faq/006.
- Excluir ou mover tema — sem dono ainda; hoje tema com FAQ é protegido (`PROTECT`).
- Histórico de versões da FAQ — sem dono ainda.
- Transferir a autoria de uma FAQ para outro administrador — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/faq/cadastro.py` → `gravar_faq` (faq/001): a criação; esta SPEC acrescenta a regravação ao lado.
- `@services/utils/markdown` → `RenderizadorMarkdown` (faq/001): a FAQ editada é exibida por ele.
- `@services/utils/erros_formulario` → o erro de formulário com o campo destacado.
- `@middleware de validação Pydantic` (SPEC infraestrutura/001): `ValidationError` na fronteira.
- Skills: `erros-de-formulario`, `pydantic-validation-errors`, `componentes-frontend`, `daisyui`,
  `htmx-skill`, `mock`, `painel`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`services/domain/faq/autoria.py`** — a regra de quem altera o quê. É pura, e o app a usa tanto para
filtrar a lista quanto para recusar o id forjado.

```python
def pode_editar(autor_id: int | None, editor: Editor) -> bool:
    # FAQ do sistema (sem autor) é de todos os administradores; a dos outros, de ninguém além do autor.
    return autor_id is None or autor_id == editor.perfil_id
```

**`apps/faq/acesso.py`** — o portão das rotas de edição.

```python
def superusuario_requerido(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @wraps(view)
    @login_required
    def _protegida(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return _protegida
```

**`apps/faq/consulta.py`** — a FAQ alheia some com 404, e não com 403: a existência dela não é
informação para quem não é o autor.

```python
def faq_editavel(faq_id: int, editor: Editor) -> FaqModel:
    registro = get_object_or_404(FaqModel, pk=faq_id)
    if not pode_editar(registro.autor_id, editor):
        raise Http404
    return registro


def faqs_editaveis(editor: Editor) -> QuerySet[FaqModel]:
    return FaqModel.objects.filter(Q(autor__isnull=True) | Q(autor_id=editor.perfil_id))
```

**`apps/faq/cadastro.py`** — a regravação. As formulações antigas saem antes de as novas entrarem, na
mesma transação. Assim, promover uma variação a pergunta principal não colide com ela mesma no UNIQUE.

```python
@transaction.atomic
def regravar_faq(edicao: Edicao) -> None:
    registro = faq_editavel(edicao.faq.id, edicao.editor)
    _conferir_formulacoes_livres(edicao.faq)          # mensagem por campo antes do IntegrityError
    registro.formulacoes.all().delete()
    registro.links.all().delete()
    _aplicar_campos(registro, edicao.faq)             # resposta_markdown, tema, palavras-chave, visibilidade, situação
    _gravar_formulacoes(registro, edicao.faq)
    _gravar_links(registro, edicao.faq.resposta.links)
    registro.relacionadas.set(edicao.faq.relacionadas)


def _conferir_formulacoes_livres(faq: Faq) -> None:
    # Pré-checagem para devolver o erro no campo certo (skill erros-de-formulario). O UNIQUE do banco
    # continua sendo a garantia: duas gravações simultâneas passam daqui e uma morre no IntegrityError.
    chaves = {f.chave: campo for campo, f in _formulacoes_com_campo(faq)}
    ocupadas = (
        FormulacaoModel.objects.filter(chave__in=chaves)
        .exclude(faq_id=faq.id)
        .values_list("chave", flat=True)
    )
    if ocupadas:
        raise FormulacaoOcupada(campos=[chaves[c] for c in ocupadas])
```

`gravar_faq` (faq/001) passa a chamar a mesma `_conferir_formulacoes_livres` antes de criar.

**Publicar e despublicar** são o mesmo POST que troca `situacao`, protegido por `faq_editavel`. Não há
estado intermediário.

**`static/src/js/editor_markdown.js`** — o editor é **Milkdown (Crepe)**, empacotado pelo `esbuild` no
estágio de build do front-end (`package.json`), sem CDN. O JS só espelha o markdown num `<textarea>`
oculto do `<form>`. Validação e gravação são do servidor.

```javascript
// Estado visual do controle (CLAUDE.md §7.2), aprovado nesta SPEC: o editor é a única peça de JS.
const crepe = new Crepe({ root: alvo, defaultValue: campo.value });
crepe.on((ouvinte) => ouvinte.markdownUpdated((_ctx, markdown) => { campo.value = markdown; }));
await crepe.create();
```

**Rotas** — todas protegidas por `superusuario_requerido`:

| Rota | O que faz |
|---|---|
| `faq:admin_lista` | lista das FAQs editáveis, por situação e tema |
| `faq:admin_nova` | formulário de criação |
| `faq:admin_editar` | formulário de edição |
| `faq:admin_situacao` | publicar / despublicar (POST) |
| `faq:admin_excluir` | exclusão, com confirmação (POST) |
| `faq:admin_tema_novo` / `faq:admin_tema_renomear` | temas e subtemas |

A entrada da área no painel (aba, grupo, glifo) é perguntada ao usuário na retomada, pela skill `painel`.

## 7 · Caveats

**A edição da FAQ não é ação administrativa (CLAUDE.md §3.5).** A FAQ documenta o uso do sistema, não
um processo da DIMAP, e a competência é só "ser superusuário". Por isso a execução **não é registrada**
em `ExecucaoAcao`, e quem mudou o quê se sabe só por `autor` e `atualizado_em`.

**Uma terceira peça de JavaScript entra no projeto: o editor Milkdown, com etapa de bundle.** Escrever
markdown à mão afastaria quem mantém a FAQ, e um editor visual não sai de HTMX. O custo é uma
dependência de front-end mantida por terceiros e um passo de build a mais no container do CSS.

**A pré-checagem revela que uma pergunta já existe, mesmo quando ela está no rascunho de outro
administrador.** A unicidade é global, e esconder a colisão deixaria o administrador sem saber por que
a gravação falhou. O que vaza é só que a formulação está ocupada, não a FAQ nem o autor.

**Regravar apaga e recria formulações e links.** É o jeito mais simples de manter o UNIQUE consistente
quando uma variação vira pergunta principal. Os ids dessas linhas não são estáveis, e nada pode apontar
para eles.

**A FAQ do sistema é editável por qualquer superusuário e continua sem autor depois da edição.** Ela é
bootstrap compartilhado, não obra de alguém. Duas edições simultâneas sobre a mesma FAQ do sistema
seguem a regra "a última gravação vence", sem aviso.

## 8 · Testes (TDD)
- `test_rotas_de_edicao_exigem_superusuario` — parametrizado sobre as rotas: anônimo → login, logado
  sem marca → 403. *(marker `banco`)*
- `test_faq_de_outro_admin_nao_aparece_nem_abre` — some da lista, e GET/POST com o id forjado dá 404.
  *(marker `banco`)*
- `test_faq_do_sistema_eh_editavel_por_qualquer_superusuario` — dois administradores editam a mesma
  FAQ sem autor, e ela continua sem autor. *(marker `banco`)*
- `test_pergunta_ocupada_volta_com_erro_no_campo` — POST com variação igual à pergunta de outra FAQ
  devolve o `<form>` com a mensagem em português no controle daquela variação, e nada muda no banco.
  *(marker `banco`)*
- `test_promover_variacao_a_pergunta_principal` — trocar pergunta e variação de lugar regrava sem
  colisão. *(marker `banco`)*
- `test_publicar_e_despublicar_mudam_a_pagina` — publicada aparece em `/faq/`, e despublicada some.
  *(marker `banco`)*
- `test_faq_nova_nasce_rascunho_e_publica` — criada sem tocar nos dois controles, não aparece na
  página até ser publicada, e publicada aparece para anônimo. *(marker `banco`)*
- `test_markdown_editado_volta_identico` — o markdown enviado é o mesmo que reabre no formulário,
  byte a byte. *(marker `banco`)*
- `test_excluir_libera_as_perguntas` — depois da exclusão, outra FAQ grava a mesma pergunta.
  *(marker `banco`)*
- `test_subtema_novo_sob_subtema_eh_recusado_no_formulario` — erro em português no campo `pai`.
  *(marker `banco`)*
