"""
Testes do artefato de CSS que o build do Tailwind/daisyUI produz (SPEC infraestrutura/004).

Rodam sobre `static/dist/output.css`, que é gerado pelo serviço `tailwind` do compose — por isso
levam o marker `integration`: dependem de um artefato real, não de dado sintético.
"""

from pathlib import Path
import re

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CSS_COMPILADO = REPO_ROOT / "static" / "dist" / "output.css"

PASTAS_VARRIDAS = (
    "templates",
    "apps",
)

STYLEGUIDE = "templates/core/design_system.html"

SINTAXE_DJANGO = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")
ATRIBUTO_CLASS = re.compile(r'class="([^"]*)"')
# O lookbehind descarta fração decimal de valor CSS (`1.25rem`), sem descartar a segunda classe de
# um seletor encadeado (`.checklist-item.atendido`); exigir letra no início cobre `rgba(0,0,0,.5)`.
SELETOR_DE_CLASSE = re.compile(r"(?<![\d.#%])\.((?:[a-zA-Z_-]|\\.)(?:[\w-]|\\.)*)")
ESCAPE_DO_TAILWIND = re.compile(r"\\(.)")
TEMA_DIMAP = re.compile(r'data-theme\s*=\s*"?dimap"?')

# Nomes que aparecem em `class=` mas não são estilo: ganchos que o JS consulta por seletor e o
# resíduo morto que a SPEC infraestrutura/004 recortou para depois (§4).
CLASSES_SEM_ESTILO = frozenset(
    {
        "icone-olho-aberto",
        "icone-olho-fechado",
        "form-control",
        "btn-delegar",
        "link-interno",
        "tarja-vinculo-info",
        "bg-agua-50/70",
    }
)

COMPONENTES_DAISYUI = ("btn", "input", "select", "modal", "table", "menu")

DECLARACAO_DE_CAMADA = re.compile(r"@layer ([a-zA-Z0-9_., ]+);")

# Fontes que o `@source` do input.css declara. Procurar o nome da classe no texto inteiro delas
# (e não só em `class=`) é o que separa "usada pela aplicação" de "só existe em mock".
FONTES_DECLARADAS = (
    "templates",
    "apps",
    "static/src/js",
    "services/utils/erros_formulario",
    "static/src/tema-dimap.dev.css",
)
EXTENSOES_DAS_FONTES = frozenset({".html", ".js", ".py", ".css"})

PASTAS_FORA_DA_APLICACAO = (
    ".claude/skills/**/examples/*.html",
    "wireframes/*.html",
    "SPECS/**/*.html",
)

# O daisyUI emite estes junto do componente a que pertencem (`dropdown`, `tooltip`), que a
# aplicação usa: aparecem no CSS sem que nada de fora tenha sido varrido.
ESTADOS_EMPACOTADOS_PELO_DAISYUI = frozenset({"dropdown-open", "tooltip-open"})


def _seletores_emitidos() -> set[str]:
    css = CSS_COMPILADO.read_text(encoding="utf-8")
    return {
        ESCAPE_DO_TAILWIND.sub(r"\1", bruto) for bruto in SELETOR_DE_CLASSE.findall(css)
    }


def _classes_literais_dos_templates() -> dict[str, str]:
    """Classe → primeiro template onde aparece. Trechos de sintaxe Django saem antes do split:
    o que sobra é literal, a única coisa que o `@source` consegue descobrir."""
    encontradas: dict[str, str] = {}
    for pasta in PASTAS_VARRIDAS:
        for template in sorted((REPO_ROOT / pasta).rglob("*.html")):
            texto = template.read_text(encoding="utf-8")
            for atributo in ATRIBUTO_CLASS.findall(texto):
                for classe in SINTAXE_DJANGO.sub(" ", atributo).split():
                    # Sobra do recorte da interpolação (`alert-{{ tags }}` deixa `alert-`).
                    if classe.endswith("-"):
                        continue
                    if classe in CLASSES_SEM_ESTILO:
                        continue
                    encontradas.setdefault(classe, str(template.relative_to(REPO_ROOT)))
    return encontradas


def _texto_das_fontes_declaradas() -> str:
    partes: list[str] = []
    for fonte in FONTES_DECLARADAS:
        caminho = REPO_ROOT / fonte
        arquivos = (
            [caminho]
            if caminho.is_file()
            else [
                a
                for a in caminho.rglob("*")
                if a.is_file() and a.suffix in EXTENSOES_DAS_FONTES
            ]
        )
        partes += [a.read_text(encoding="utf-8", errors="ignore") for a in arquivos]
    return "\n".join(partes)


def _classes_exclusivas_de_fora_da_aplicacao() -> set[str]:
    """Classes usadas em mock, wireframe ou SPEC cujo nome não aparece em nenhuma fonte declarada."""
    fontes = _texto_das_fontes_declaradas()
    de_fora: set[str] = set()
    for padrao in PASTAS_FORA_DA_APLICACAO:
        for arquivo in REPO_ROOT.glob(padrao):
            texto = arquivo.read_text(encoding="utf-8", errors="ignore")
            for atributo in ATRIBUTO_CLASS.findall(texto):
                for classe in SINTAXE_DJANGO.sub(" ", atributo).split():
                    if not classe.endswith("-"):
                        de_fora.add(classe)
    return {classe for classe in de_fora if classe not in fontes}


# ---------------------------------------------------------------------------
# Cobertura: o que os templates usam precisa existir no artefato
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_toda_classe_literal_dos_templates_esta_no_css_compilado() -> None:
    emitidos = _seletores_emitidos()

    ausentes = {
        classe: origem
        for classe, origem in _classes_literais_dos_templates().items()
        if classe not in emitidos
    }

    assert not ausentes, f"classes usadas nos templates e ausentes do CSS: {ausentes}"


@pytest.mark.integration
def test_css_compilado_ignora_pastas_fora_da_aplicacao() -> None:
    """Sem `source(none)` no input.css o Tailwind varre a raiz inteira e passa a emitir classe que
    só existe em mock, SPEC ou wireframe — e o CSS de desenvolvimento vira um superconjunto do que
    produção assa."""
    exclusivas = _classes_exclusivas_de_fora_da_aplicacao()

    assert exclusivas, (
        "nenhuma classe exclusiva encontrada: o teste perdeu o significado"
    )

    vazadas = (exclusivas & _seletores_emitidos()) - ESTADOS_EMPACOTADOS_PELO_DAISYUI

    assert not vazadas, f"classe de fora da aplicação emitida no CSS: {sorted(vazadas)}"


# ---------------------------------------------------------------------------
# Integridade: tema e plugin presentes no artefato
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_css_compilado_traz_o_tema_dimap_e_os_componentes_daisyui() -> None:
    """O modo como este build falha em silêncio é sair completo em tamanho e vazio em aparência:
    o `@plugin` não resolve, ou o tema não entra, e o CSS ainda assim é gerado."""
    css = CSS_COMPILADO.read_text(encoding="utf-8")
    emitidos = _seletores_emitidos()

    assert TEMA_DIMAP.search(css), "tema dimap ausente do CSS compilado"
    assert "--color-agua-500" in css, "escala de cor do design system ausente"

    faltando = [nome for nome in COMPONENTES_DAISYUI if nome not in emitidos]
    assert not faltando, f"componentes daisyUI ausentes do CSS: {faltando}"


# ---------------------------------------------------------------------------
# Cascata: o design system precisa vencer o daisyUI
# ---------------------------------------------------------------------------


def _ordem_das_camadas() -> list[str]:
    """As camadas na ordem de primeira aparição, que é o que define a precedência entre elas."""
    css = CSS_COMPILADO.read_text(encoding="utf-8")
    ordem: list[str] = []
    for declaracao in DECLARACAO_DE_CAMADA.findall(css):
        for nome in (parte.strip() for parte in declaracao.split(",")):
            if nome not in ordem:
                ordem.append(nome)
    return ordem


@pytest.mark.integration
def test_design_system_vence_o_daisyui_na_cascata() -> None:
    """O daisyUI emite os componentes dele dentro de `utilities` e o design system vive em
    `components`. Na ordem padrão do Tailwind `components` vem antes, e o daisyUI ganha: o modal
    fica opaco, o foco perde o halo e os avisos perdem a cor — tudo isso sem erro nenhum."""
    ordem = _ordem_das_camadas()

    assert "components" in ordem and "utilities" in ordem
    assert ordem.index("components") > ordem.index("utilities"), (
        f"daisyUI vence o design system na cascata; ordem declarada: {ordem}"
    )


@pytest.mark.integration
def test_toda_classe_do_styleguide_esta_no_css_compilado() -> None:
    """O styleguide é o contrato visual: peça exibida ali é peça que a aplicação tem. Como ele é
    uma página varrida pelo `@source`, classe que ele usa e o CSS não emite é contradição."""
    texto = (REPO_ROOT / STYLEGUIDE).read_text(encoding="utf-8")
    usadas = {
        classe
        for atributo in ATRIBUTO_CLASS.findall(texto)
        for classe in SINTAXE_DJANGO.sub(" ", atributo).split()
        if not classe.endswith("-") and classe not in CLASSES_SEM_ESTILO
    }

    ausentes = usadas - _seletores_emitidos()

    assert not ausentes, (
        f"styleguide exibe classe que o CSS não tem: {sorted(ausentes)}"
    )
