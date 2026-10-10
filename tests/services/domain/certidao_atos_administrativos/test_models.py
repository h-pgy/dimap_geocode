from datetime import date, timedelta

from pydantic import ValidationError
import pytest

from services.domain.documento_selado import AlvoDoAto, AutorDoAto, EnvelopeAto
from services.domain.listagem_gestao import LinhaExecucao


def _envelope(**overrides: object) -> EnvelopeAto:
    defaults: dict[str, object] = {
        "codigo": "TESTE1234567",
        "acao": "competencias.emitir_certidao_atos",
        "operacao": "emitir",
        "autor": AutorDoAto(
            nome="Servidor Teste",
            unidade="DIMAP-1",
            cargo_base="Analista",
        ),
        "alvo": AlvoDoAto(tipo="servidor", identificador="1234567"),
        "emitido_em": "2026-09-09T10:00:00Z",
        "campos_publicos": ("periodo", "tipos"),
        "extras": {"periodo": "01/08/2026 a 31/08/2026", "tipos": "todos"},
    }
    return EnvelopeAto(**(defaults | overrides))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Validação do contrato BuscaAtosProprios (SPEC 009 §3)
# ---------------------------------------------------------------------------


def test_busca_atos_proprios_periodo_valido() -> None:
    from services.domain.certidao_atos_administrativos.models import BuscaAtosProprios

    inicio = date(2026, 8, 1)
    fim = date(2026, 8, 31)
    busca = BuscaAtosProprios(perfil_id=1, inicio=inicio, fim=fim)

    assert busca.perfil_id == 1
    assert busca.inicio == inicio
    assert busca.fim == fim
    assert busca.acoes == frozenset()


def test_busca_atos_proprios_rejeita_fim_anterior_ao_inicio() -> None:
    from services.domain.certidao_atos_administrativos.models import BuscaAtosProprios

    inicio = date(2026, 8, 31)
    fim = date(2026, 8, 1)

    with pytest.raises(ValidationError) as exc_info:
        BuscaAtosProprios(perfil_id=1, inicio=inicio, fim=fim)

    assert "A data final do período não pode ser anterior à inicial." in str(exc_info.value)


def test_busca_atos_proprios_rejeita_janela_maior_que_teto() -> None:
    from services.domain.certidao_atos_administrativos.models import (
        JANELA_MAXIMA_DIAS,
        BuscaAtosProprios,
    )

    inicio = date(2025, 1, 1)
    fim = inicio + timedelta(days=JANELA_MAXIMA_DIAS + 1)

    with pytest.raises(ValidationError) as exc_info:
        BuscaAtosProprios(perfil_id=1, inicio=inicio, fim=fim)

    assert f"O período da certidão não pode passar de {JANELA_MAXIMA_DIAS} dias." in str(exc_info.value)


# ---------------------------------------------------------------------------
# Contratos RecorteDeclarado e CertidaoAtosInput
# ---------------------------------------------------------------------------


def test_recorte_declarado_imutavel() -> None:
    from services.domain.certidao_atos_administrativos.models import RecorteDeclarado

    recorte = RecorteDeclarado(
        inicio=date(2026, 8, 1),
        fim=date(2026, 8, 31),
        tipos=("Ação 1", "Ação 2"),
    )

    assert recorte.tipos == ("Ação 1", "Ação 2")
    with pytest.raises(ValidationError):
        recorte.inicio = date(2026, 9, 1)  # type: ignore[misc]


def test_certidao_atos_input_imutavel() -> None:
    from services.domain.certidao_atos_administrativos.models import (
        CertidaoAtosInput,
        RecorteDeclarado,
    )

    recorte = RecorteDeclarado(inicio=date(2026, 8, 1), fim=date(2026, 8, 31))
    envelope = _envelope()
    linha = LinhaExecucao(
        pk=1,
        momento="09/09/2026 10:00",
        servidor="Servidor Teste",
        servidor_pk=1,
        unidade="DIMAP-1",
        unidade_pk=1,
        cor_unidade="#003366",
        cargo="Analista",
        comissao="—",
        acao="Definir atribuições",
        operacao="atribuir",
        alvo="unidade: DIMAP-1",
        autorizado=True,
    )
    pedido = CertidaoAtosInput(
        envelope=envelope,
        recorte=recorte,
        atos=(linha,),
        base_url="https://geocoder.dimap.pmsp/",
    )

    assert len(pedido.atos) == 1
    assert pedido.base_url == "https://geocoder.dimap.pmsp/"
    with pytest.raises(ValidationError):
        pedido.base_url = "http://outro"  # type: ignore[misc]
