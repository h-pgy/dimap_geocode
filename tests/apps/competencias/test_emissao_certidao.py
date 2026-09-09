"""Testes de apps/competencias/emissao_certidao.py (SPEC documentos_oficiais/009):
orquestração da emissão de certidão de atos — rastro, envelope, render, selagem e guarda no acervo.
"""

from itertools import count

from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone
import pytest

from apps.cargos.models import CargoBase
from apps.competencias.models import Acao, ExecucaoAcao
from apps.documentos.models import DocumentoEmitido
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil
from services.utils.assinatura import ConferirInput, EstadoSelo, conferir_selo

banco = pytest.mark.banco
_SIGLAS = count(200)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade() -> TipoUnidade:
    return TipoUnidade.objects.create(
        nome="Tipo Emissão",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )


def _unidade(sigla: str = "EMIS-1") -> Unidade:
    return Unidade.objects.create(
        nome=f"Unidade {sigla}",
        sigla=sigla,
        tipo=_tipo_unidade(),
    )


def _cargo_base(nome: str = "Analista de Emissão") -> CargoBase:
    numero = next(_SIGLAS)
    return CargoBase.objects.create(nome=f"{nome} {numero}", sigla=f"CE{numero}")


def _perfil(unidade: Unidade | None = None, rf: str = "870001") -> Perfil:
    if unidade is None:
        unidade = _unidade()
    perfil = Perfil(
        rf=rf,
        nome="Marina",
        sobrenome="Salgado",
        cargo_base=_cargo_base(),
        unidade=unidade,
    )
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _acao(slug: str = "competencias.acao_emitida") -> Acao:
    return Acao.objects.create(slug=slug, nome=f"Ação {slug}", tooltip="tt", ativa=True)


# ---------------------------------------------------------------------------
# Testes de comportamento (SPEC 009 §8)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_certidao_emitida_sai_selada_e_confere() -> None:
    from apps.competencias.emissao_certidao import emitir_certidao_atos, recorte_declarado
    from services.domain.certidao_atos_administrativos.models import BuscaAtosProprios

    unidade = _unidade("EMIS-CONF")
    servidor = _perfil(unidade, "870010")
    acao = _acao("competencias.acao_confere")
    hoje = timezone.localdate()

    ExecucaoAcao.objects.create(
        acao=acao,
        perfil=servidor,
        unidade=unidade,
        cargo_base=servidor.cargo_base,
        autorizado=True,
    )

    busca = BuscaAtosProprios(perfil_id=servidor.pk, inicio=hoje, fim=hoje)
    recorte = recorte_declarado(busca)

    documento = emitir_certidao_atos(
        autor=servidor,
        busca=busca,
        recorte=recorte,
        base_url="https://geocoder.dimap.pmsp/",
    )

    # O documento foi persistido no acervo
    linha = DocumentoEmitido.objects.get(codigo=documento.codigo)
    assert linha.codigo == documento.codigo

    # Os bytes emitidos passam em conferir_selo como INTEGRO
    conferencia = conferir_selo(
        ConferirInput(pdf=bytes(linha.arquivo), segredo=settings.ASSINATURA_SEGREDO)
    )
    assert conferencia.estado == EstadoSelo.INTEGRO

    # O código do envelope bate com o salvo
    assert conferencia.envelope is not None
    assert conferencia.envelope["codigo"] == documento.codigo

    # O alvo do ato é a própria pessoa
    assert conferencia.envelope["alvo"]["tipo"] == "servidor"
    assert conferencia.envelope["alvo"]["identificador"] == servidor.rf


@banco
@pytest.mark.django_db
def test_certidao_emitida_entra_no_acervo_inteira(client: Client) -> None:
    from apps.competencias.emissao_certidao import emitir_certidao_atos, recorte_declarado
    from services.domain.certidao_atos_administrativos.models import BuscaAtosProprios

    unidade = _unidade("EMIS-ACERVO")
    servidor = _perfil(unidade, "870020")
    hoje = timezone.localdate()

    busca = BuscaAtosProprios(perfil_id=servidor.pk, inicio=hoje, fim=hoje)
    recorte = recorte_declarado(busca)

    documento = emitir_certidao_atos(
        autor=servidor,
        busca=busca,
        recorte=recorte,
        base_url="https://geocoder.dimap.pmsp/",
    )

    # A linha guardada tem os mesmos bytes
    linha = DocumentoEmitido.objects.get(codigo=documento.codigo)
    bytes_emitidos = bytes(linha.arquivo)

    # A rota de segunda via devolve os mesmos bytes para quem está logado
    client.force_login(servidor)
    resposta = client.get(reverse("documentos:segunda_via", kwargs={"codigo": documento.codigo}))

    assert resposta.status_code == 200
    assert resposta.content == bytes_emitidos
