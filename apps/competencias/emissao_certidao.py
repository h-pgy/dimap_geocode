from django.conf import settings
from django.utils import timezone

from apps.competencias.acoes_declaradas import ACAO_EMITIR_CERTIDAO_ATOS
from apps.competencias.historico import atos_proprios
from apps.competencias.registro import REGISTRO
from apps.documentos.acervo import guardar_documento
from apps.documentos.models import DocumentoEmitido
from apps.user_admin.exercicio import substituicao_que_exerce
from apps.user_admin.models import Perfil
from services.domain.certidao_atos_administrativos import (
    BuscaAtosProprios,
    CertidaoAtos,
    CertidaoAtosInput,
    RecorteDeclarado,
)
from services.domain.documento_oficial import (
    SeloConfig,
    build_marcacao_config,
    build_tema_config,
    montar_tema,
)
from services.domain.documento_selado import (
    AlvoDoAto,
    AutorDoAto,
    EnvelopeAto,
    gerar_codigo,
    montar_envelope,
)
from services.utils.assinatura import SelarInput, selar_documento


def emitir_certidao_atos(
    autor: Perfil,
    busca: BuscaAtosProprios,
    recorte: RecorteDeclarado,
    base_url: str,
) -> DocumentoEmitido:
    envelope = _envelope(autor, recorte)
    gerar_certidao = _tipo_certidao()
    renderizado = gerar_certidao(
        CertidaoAtosInput(
            envelope=envelope,
            recorte=recorte,
            atos=tuple(atos_proprios(busca)),
            base_url=base_url,
        )
    )
    selado = selar_documento(
        SelarInput(
            pdf=renderizado.pdf,
            dados=montar_envelope(envelope),
            campos_publicos=envelope.campos_publicos,
            segredo=settings.ASSINATURA_SEGREDO,
            id_chave=settings.ASSINATURA_ID_CHAVE,
        )
    )
    return guardar_documento(selado, envelope, execucao=None)


def _tipo_certidao() -> CertidaoAtos:
    tema = montar_tema(build_tema_config(settings))
    config = build_marcacao_config(settings)
    selo_config = SeloConfig()
    return CertidaoAtos(tema=tema, config=config, selo_config=selo_config)


def _envelope(perfil: Perfil, recorte: RecorteDeclarado) -> EnvelopeAto:
    return EnvelopeAto(
        codigo=gerar_codigo(),
        acao=ACAO_EMITIR_CERTIDAO_ATOS.acao.slug,
        operacao="emitir",
        autor=AutorDoAto(
            nome=f"{perfil.nome} {perfil.sobrenome}",
            unidade=perfil.unidade.sigla,
            cargo_base=perfil.cargo_base.nome,
            cargo_comissao=perfil.cargo_comissao.nome if perfil.cargo_comissao else None,
            substituindo=_cargo_substituido(perfil),
        ),
        alvo=AlvoDoAto(tipo="servidor", identificador=perfil.rf),
        emitido_em=timezone.localtime(),
        campos_publicos=("periodo", "tipos"),
        extras={
            "periodo": f"{recorte.inicio:%d/%m/%Y} a {recorte.fim:%d/%m/%Y}",
            "tipos": ", ".join(recorte.tipos) or "todos",
        },
    )


def recorte_declarado(busca: BuscaAtosProprios) -> RecorteDeclarado:
    return RecorteDeclarado(
        inicio=busca.inicio,
        fim=busca.fim,
        tipos=tuple(
            sorted(
                acao.acao.nome
                for slug in busca.acoes
                if (acao := REGISTRO.por_slug(slug))
            )
        ),
    )


def _cargo_substituido(perfil: Perfil) -> str | None:
    substituicao = substituicao_que_exerce(perfil)
    if substituicao is None:
        return None
    coberto = substituicao.impedimento.perfil
    return coberto.cargo_comissao.nome if coberto.cargo_comissao else coberto.cargo_base.nome
