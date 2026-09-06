import re

from pydantic import HttpUrl

from services.domain.email import (
    ESCRITORES,
    TEMA_EMAIL,
    Bloco,
    Botao,
    Destaque,
    Divisor,
    Imagem,
    Otp,
    Paragrafo,
    Subtitulo,
    Tabela,
    Titulo,
)


def _todos_os_blocos() -> tuple[Bloco, ...]:
    return (
        Titulo(texto="O envio de e-mail está funcionando"),
        Subtitulo(texto="Dados do disparo"),
        Paragrafo(texto="Mensagem disparada para provar a configuração de envio."),
        Destaque(rotulo="Ambiente", valor="producao"),
        Tabela(cabecalho=("Campo", "Valor"), linhas=(("Ambiente", "producao"),)),
        Imagem(
            url=HttpUrl("https://geocoder.dimap.local/selo.png"),
            alternativo="Selo da DIMAP",
        ),
        Botao(rotulo="Entrar", url=HttpUrl("https://geocoder.dimap.local/entrar")),
        Divisor(),
    )


def _escrever(bloco: Bloco) -> str:
    return ESCRITORES[bloco.tipo](bloco)


def _estilos(html: str) -> set[str]:
    return set(re.findall(r'style="([^"]*)"', html))


def _celulas(html: str) -> list[str]:
    return re.findall(r'<td style="[^"]*">(.*?)</td>', html)


# ---------------------------------------------------------------------------
# O estilo de cada bloco vem do tema, e só dele
# ---------------------------------------------------------------------------


def test_cada_tipo_de_bloco_sai_com_o_estilo_do_tema() -> None:
    esperado: dict[str, set[str]] = {
        "titulo": {TEMA_EMAIL["titulo"]},
        "subtitulo": {TEMA_EMAIL["subtitulo"]},
        "paragrafo": {TEMA_EMAIL["paragrafo"]},
        "destaque": {TEMA_EMAIL["poco"], TEMA_EMAIL["overline"], TEMA_EMAIL["valor"]},
        "tabela": {TEMA_EMAIL["celula_cabecalho"], TEMA_EMAIL["celula"]},
        "imagem": {TEMA_EMAIL["imagem"]},
        "botao": {TEMA_EMAIL["botao"]},
        "divisor": {TEMA_EMAIL["divisor"]},
    }

    for bloco in _todos_os_blocos():
        assert _estilos(_escrever(bloco)) == esperado[bloco.tipo], bloco.tipo

    mono = Destaque(rotulo="Senha temporária", valor="k7Qm-2af9", monoespacado=True)
    assert TEMA_EMAIL["valor_mono"] in _estilos(_escrever(mono))


# ---------------------------------------------------------------------------
# Escape do que vem de fora
# ---------------------------------------------------------------------------


def test_texto_de_bloco_e_escapado() -> None:
    paragrafo = _escrever(Paragrafo(texto="Lote <b>A</b> & anexo"))
    assert "<b>" not in paragrafo
    assert "&lt;b&gt;" in paragrafo
    assert "&amp;" in paragrafo

    destaque = _escrever(
        Destaque(rotulo="Unidade & cargo", valor="<script>alert(1)</script>")
    )
    assert "<script>" not in destaque
    assert "&lt;script&gt;" in destaque

    tabela = _escrever(Tabela(linhas=(("<td>solta</td>",),)))
    assert _celulas(tabela) == ["&lt;td&gt;solta&lt;/td&gt;"]


# ---------------------------------------------------------------------------
# Tabela: ordem das células, cabeçalho opcional e célula sem valor
# ---------------------------------------------------------------------------


def test_tabela_escreve_cabecalho_e_linhas_na_ordem() -> None:
    com_cabecalho = _escrever(
        Tabela(
            cabecalho=("Campo", "Valor"),
            linhas=(("Ambiente", "producao"), ("Momento", "21/08/2026 14:30:05")),
        )
    )
    assert _celulas(com_cabecalho) == [
        "Campo",
        "Valor",
        "Ambiente",
        "producao",
        "Momento",
        "21/08/2026 14:30:05",
    ]
    assert com_cabecalho.count(TEMA_EMAIL["celula_cabecalho"]) == 2

    sem_cabecalho = _escrever(Tabela(linhas=(("Ambiente", "producao"),)))
    assert _celulas(sem_cabecalho) == ["Ambiente", "producao"]
    assert TEMA_EMAIL["celula_cabecalho"] not in sem_cabecalho

    # model_validate porque o campo é tipado como texto: o None entra pela fronteira de dados.
    com_celula_vazia = Tabela.model_validate(
        {"cabecalho": ("Campo", "Valor"), "linhas": [["Momento", None]]}
    )
    assert _celulas(_escrever(com_celula_vazia)) == ["Campo", "Valor", "Momento", ""]


# ---------------------------------------------------------------------------
# Otp: uma caixa por caractere, na ordem
# ---------------------------------------------------------------------------


def test_otp_escreve_uma_caixa_por_caractere() -> None:
    html = _escrever(Otp(rotulo="Senha temporária", valor="8271k9af"))

    caixas = re.findall(rf'<td style="{re.escape(TEMA_EMAIL["otp_caixa"])}">(.*?)</td>', html)
    assert caixas == list("8271k9af")
    assert TEMA_EMAIL["overline"] in html
