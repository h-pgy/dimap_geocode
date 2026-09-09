"""Testes de services/domain/certidao_atos_administrativos/certidao.py (SPEC documentos_oficiais/009):
a composição do documento oficial, o recorte declarado no texto, a certidão negativa e a emissão selada.
"""

from datetime import date
from pathlib import Path
from typing import Callable

import pytest

from services.domain.documento_oficial import (
    MarcacaoConfig,
    Paragrafo,
    SeloConfig,
    SeloDeFecho,
    Tabela,
    Titulo,
    montar_tema,
)
from services.domain.documento_oficial.models import TemaConfig
from services.domain.documento_selado import (
    AlvoDoAto,
    AutorDoAto,
    EnvelopeAto,
    SeloImpresso,
    SeloImpressoInput,
    montar_selo_impresso,
)
from services.domain.listagem_gestao import LinhaExecucao

artefato = pytest.mark.artefato


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _envelope(**overrides: object) -> EnvelopeAto:
    defaults: dict[str, object] = {
        "codigo": "7K9M2X4P8QRT",
        "acao": "competencias.emitir_certidao_atos",
        "operacao": "emitir",
        "autor": AutorDoAto(
            nome="Marina Salgado de Almeida",
            unidade="DIMAP-1",
            cargo_base="Analista de Ordenamento Territorial",
            cargo_comissao="Diretora de Divisão",
        ),
        "alvo": AlvoDoAto(tipo="servidor", identificador="900001"),
        "emitido_em": "2026-09-09T14:30:00Z",
        "campos_publicos": ("periodo", "tipos"),
        "extras": {
            "periodo": "01/08/2026 a 31/08/2026",
            "tipos": "todos",
        },
    }
    return EnvelopeAto(**(defaults | overrides))  # type: ignore[arg-type]


def _linha(
    pk: int = 1,
    momento: str = "15/08/2026 11:20",
    acao: str = "Conceder competência",
    operacao: str = "conceder",
    alvo: str = "ação: competencias.definir_atribuicao",
    unidade: str = "DIMAP-1",
) -> LinhaExecucao:
    return LinhaExecucao(
        pk=pk,
        momento=momento,
        servidor="Marina Salgado de Almeida",
        servidor_pk=1,
        unidade=unidade,
        unidade_pk=1,
        cor_unidade="#003366",
        cargo="Analista de Ordenamento Territorial",
        comissao="Diretora de Divisão",
        acao=acao,
        operacao=operacao,
        alvo=alvo,
        autorizado=True,
    )


def _selo(envelope: EnvelopeAto, base_url: str = "https://geocoder.dimap.pmsp/") -> SeloImpresso:
    return montar_selo_impresso(SeloImpressoInput(envelope=envelope, base_url=base_url))


# ---------------------------------------------------------------------------
# Testes de comportamento (SPEC 009 §8)
# ---------------------------------------------------------------------------


def test_filtro_por_tipo_restringe_e_o_recorte_sai_declarado() -> None:
    from services.domain.certidao_atos_administrativos.certidao import (
        MontarCertidaoAtos,
        MontarCertidaoInput,
    )
    from services.domain.certidao_atos_administrativos.models import (
        CertidaoAtosInput,
        RecorteDeclarado,
    )

    linha_conceder = _linha(pk=1, acao="Conceder competência", operacao="conceder")
    linha_atribuir = _linha(pk=2, acao="Definir atribuições da unidade", operacao="atribuir")

    # Com dois tipos especificados, o parágrafo de critérios nomeia o período e os tipos
    envelope = _envelope()
    recorte_com_tipos = RecorteDeclarado(
        inicio=date(2026, 8, 1),
        fim=date(2026, 8, 31),
        tipos=("Conceder competência", "Definir atribuições da unidade"),
    )
    pedido_com_tipos = MontarCertidaoInput(
        certidao=CertidaoAtosInput(
            envelope=envelope,
            recorte=recorte_com_tipos,
            atos=(linha_conceder, linha_atribuir),
            base_url="https://geocoder.dimap.pmsp/",
        ),
        selo=_selo(envelope),
        quadro=SeloConfig().fecho,
    )
    montador = MontarCertidaoAtos()
    conteudo = montador(pedido_com_tipos)

    paragrafos = [b.texto for b in conteudo.blocos if isinstance(b, Paragrafo)]
    assert any(
        "Período de 01/08/2026 a 31/08/2026. Tipos considerados: Conceder competência, Definir atribuições da unidade."
        in texto
        for texto in paragrafos
    )

    tabelas = [b for b in conteudo.blocos if isinstance(b, Tabela)]
    assert len(tabelas) == 1
    tabela = tabelas[0]
    assert tabela.cabecalho == ("Data e hora", "Ato praticado", "Sobre o quê", "Unidade")
    assert len(tabela.linhas) == 2

    # Sem tipos escolhidos (em branco), o texto declara todos os tipos
    recorte_todos = RecorteDeclarado(inicio=date(2026, 8, 1), fim=date(2026, 8, 31), tipos=())
    pedido_todos = MontarCertidaoInput(
        certidao=CertidaoAtosInput(
            envelope=envelope,
            recorte=recorte_todos,
            atos=(linha_conceder,),
            base_url="https://geocoder.dimap.pmsp/",
        ),
        selo=_selo(envelope),
        quadro=SeloConfig().fecho,
    )
    conteudo_todos = montador(pedido_todos)
    paragrafos_todos = [b.texto for b in conteudo_todos.blocos if isinstance(b, Paragrafo)]
    assert any(
        "Período de 01/08/2026 a 31/08/2026. Tipos considerados: todos os tipos de ato." in texto
        for texto in paragrafos_todos
    )


def test_periodo_sem_ato_emite_certidao_negativa() -> None:
    from services.domain.certidao_atos_administrativos.certidao import (
        MontarCertidaoAtos,
        MontarCertidaoInput,
    )
    from services.domain.certidao_atos_administrativos.models import (
        CertidaoAtosInput,
        RecorteDeclarado,
    )

    envelope = _envelope()
    recorte = RecorteDeclarado(inicio=date(2026, 8, 1), fim=date(2026, 8, 31))
    pedido = MontarCertidaoInput(
        certidao=CertidaoAtosInput(
            envelope=envelope,
            recorte=recorte,
            atos=(),
            base_url="https://geocoder.dimap.pmsp/",
        ),
        selo=_selo(envelope),
        quadro=SeloConfig().fecho,
    )
    montador = MontarCertidaoAtos()
    conteudo = montador(pedido)

    # Não deve ter tabela
    tabelas = [b for b in conteudo.blocos if isinstance(b, Tabela)]
    assert len(tabelas) == 0

    # Deve ter parágrafo afirmando expressamente que nada foi praticado
    paragrafos = [b.texto for b in conteudo.blocos if isinstance(b, Paragrafo)]
    assert any("NÃO CONSTA" in texto or "não consta" in texto.lower() for texto in paragrafos)

    # Mantém título e fecho selado idênticos
    assert any(isinstance(b, Titulo) for b in conteudo.blocos)
    assert any(isinstance(b, SeloDeFecho) for b in conteudo.blocos)


@artefato
def test_amostra_da_certidao_para_conferencia(
    publicar_artefato: Callable[[str, bytes], Path],
) -> None:
    from services.domain.certidao_atos_administrativos.certidao import CertidaoAtos
    from services.domain.certidao_atos_administrativos.models import (
        CertidaoAtosInput,
        RecorteDeclarado,
    )

    tema = montar_tema(TemaConfig())
    config = MarcacaoConfig(
        logo_horizontal=Path("static/src/img/sec_fazenda_horizontal.svg"),
        logo_vertical=Path("static/src/img/sec_fazenda_vertical.svg"),
    )
    selo_config = SeloConfig()
    tipo = CertidaoAtos(tema=tema, config=config, selo_config=selo_config)

    envelope = _envelope()
    recorte = RecorteDeclarado(
        inicio=date(2026, 8, 1),
        fim=date(2026, 8, 31),
        tipos=("Conceder competência", "Definir atribuições da unidade"),
    )
    atos = (
        _linha(pk=1, momento="05/08/2026 09:15", acao="Conceder competência", operacao="conceder"),
        _linha(pk=2, momento="12/08/2026 14:30", acao="Definir atribuições", operacao="atribuir"),
        _linha(pk=3, momento="20/08/2026 16:45", acao="Conceder competência", operacao="revogar"),
    )
    pedido = CertidaoAtosInput(
        envelope=envelope,
        recorte=recorte,
        atos=atos,
        base_url="https://geocoder.dimap.pmsp/",
    )

    renderizado = tipo(pedido)
    caminho = publicar_artefato("certidao_atos_amostra.pdf", renderizado.pdf)

    assert caminho.exists()
    assert caminho.stat().st_size > 0
