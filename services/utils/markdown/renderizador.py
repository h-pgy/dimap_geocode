import nh3
from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from mdit_py_plugins.tasklists import tasklists_plugin

TAGS_PERMITIDAS = frozenset(
    {
        "p",
        "br",
        "hr",
        "strong",
        "em",
        "s",
        "code",
        "pre",
        "blockquote",
        "ul",
        "ol",
        "li",
        "input",
        "a",
        "h3",
        "h4",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    }
)
ESQUEMAS_PERMITIDOS = frozenset({"http", "https", "mailto"})


class RenderizadorMarkdown:
    def __init__(self) -> None:
        # html=False: HTML cru dentro do markdown sai escapado, e não interpretado.
        self._md = (
            MarkdownIt("commonmark", {"html": False})
            .enable(["table", "strikethrough"])
            .use(tasklists_plugin)
        )
        self._md.core.ruler.push("nivelar_titulos", _nivelar_titulos)

    def __call__(self, texto: str) -> str:
        return self.pipeline(texto)

    def pipeline(self, texto: str) -> str:
        html = self._md.render(texto)
        # Segunda barreira: mesmo que o parser deixe passar algo, o nh3 corta pela allowlist.
        return nh3.clean(
            html,
            tags=set(TAGS_PERMITIDAS),
            attributes={
                "a": {"href", "title"},
                "input": {"type", "checked", "disabled"},
            },
            # O único <input> que sobrevive é o checkbox da lista de tarefas, sempre só de leitura.
            set_tag_attribute_values={
                "input": {"type": "checkbox", "disabled": "disabled"}
            },
            url_schemes=set(ESQUEMAS_PERMITIDOS),
            link_rel="noopener noreferrer",
        )


def _nivelar_titulos(state: StateCore) -> None:
    # A página já usa h1 e h2: o título da resposta desce para h3/h4, seja qual for o nível escrito.
    for token in state.tokens:
        if token.type in ("heading_open", "heading_close"):
            token.tag = "h3" if token.tag in ("h1", "h2", "h3") else "h4"
