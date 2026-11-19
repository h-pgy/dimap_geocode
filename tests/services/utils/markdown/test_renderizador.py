"""Renderização do markdown da resposta da FAQ (SPEC faq/001): segurança e cobertura do editor."""

import pytest

from services.utils.markdown import RenderizadorMarkdown

renderizar = RenderizadorMarkdown()

AMOSTRA_DO_EDITOR = """\
# Título 1
## Título 2
### Título 3
#### Título 4
##### Título 5
###### Título 6

Texto com **negrito**, *itálico*, ~~riscado~~, `codigo` e [link](https://www.prefeitura.sp.gov.br/).

- item
- item com sublista
  - subitem

1. primeiro
2. segundo

- [x] tarefa feita
- [ ] tarefa por fazer

> Citação.

| Entrada | Resultado |
|---|---|
| codlog | linha |

---

```
bloco de código
```
"""


def test_markdown_nao_executa_html_embutido() -> None:
    html = renderizar(
        '<script>alert(1)</script> <b onclick="x()">z</b> [x](javascript:alert(1))\n\n'
        "**negrito**\n\n- a\n- b\n\n| a | b |\n|---|---|\n| 1 | 2 |",
    )

    assert "<script" not in html
    assert "<b " not in html
    assert "onclick=" not in html.replace("&lt;b onclick", "")
    assert 'href="javascript' not in html
    assert "<strong>negrito</strong>" in html
    assert "<li>a</li>" in html
    assert "<table>" in html


def test_renderizador_cobre_o_markdown_do_editor() -> None:
    html = renderizar(AMOSTRA_DO_EDITOR)

    # Nenhuma sintaxe crua sobrevive.
    for cru in ("# ", "~~", "**", "- [", "|---", "```", "&gt; "):
        assert cru not in html
    # `#` e `##` descem para h3, porque a página já usa h1 e h2.
    assert html.count("<h3>") == 3
    assert html.count("<h4>") == 3
    assert "<h1" not in html
    assert "<h2" not in html
    assert "<s>riscado</s>" in html
    assert "<hr>" in html
    assert "<blockquote>" in html
    assert "<pre><code>" in html
    assert "<table>" in html
    assert 'rel="noopener noreferrer"' in html


@pytest.mark.parametrize(
    ("trecho", "marcado"),
    [("- [x] feita", True), ("- [ ] por fazer", False)],
)
def test_checkbox_da_lista_de_tarefas_sai_desabilitado(
    trecho: str, marcado: bool
) -> None:
    html = renderizar(trecho)

    assert 'type="checkbox"' in html
    assert 'disabled="disabled"' in html
    assert ("checked" in html) is marcado
