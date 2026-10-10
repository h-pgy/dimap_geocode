from pydantic import AwareDatetime, BaseModel

from services.domain.geometry import reprojetar

from .cache import CacheGeocodificacaoLike, SemCache
from .exceptions import SemResultadoAceitoError
from .models import ConsultaGeocodificacao, GeocodificacaoExterna, Provedor
from .porta import ProvedorGeocodificacao
from .validador import ValidacaoGeocodificacaoInput, ValidadorGeocodificacao


class GeocodificacaoExternaInput(BaseModel):
    consulta: ConsultaGeocodificacao
    output_crs: int
    agora: AwareDatetime


class GeocodificacaoExternaOutput(BaseModel):
    geocodificacao: GeocodificacaoExterna
    cacheada: bool


class GeocodificadorExterno:
    def __init__(
        self,
        provedor: ProvedorGeocodificacao,
        cache: CacheGeocodificacaoLike | None = None,
        validador: ValidadorGeocodificacao | None = None,
    ) -> None:
        self._provedor = provedor
        self._cache = cache or SemCache()
        self._validador = validador or ValidadorGeocodificacao(provedor.politica)

    @property
    def provedor(self) -> Provedor:
        return self._provedor.provedor

    def __call__(self, entrada: GeocodificacaoExternaInput) -> GeocodificacaoExternaOutput:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GeocodificacaoExternaInput) -> GeocodificacaoExternaOutput:
        guardada = self._do_cache(entrada)
        geocodificacao = guardada or self._do_provedor(entrada)
        return GeocodificacaoExternaOutput(
            geocodificacao=geocodificacao,
            cacheada=guardada is not None,
        )

    def _do_cache(self, entrada: GeocodificacaoExternaInput) -> GeocodificacaoExterna | None:
        # sem filtro de provedor: serve o que qualquer um guardou, desde que o validador aceite
        guardada = self._cache.buscar(entrada.consulta)
        if guardada is None or not self._vale(guardada, entrada):
            return None
        # o guardado já está no CRS do mapa: só reprojeta se esse CRS mudou desde então
        return self._no_crs(guardada, entrada.output_crs)

    def _do_provedor(self, entrada: GeocodificacaoExternaInput) -> GeocodificacaoExterna:
        candidatas = [
            GeocodificacaoExterna(
                consulta=entrada.consulta,
                endereco=endereco,
                consultado_em=entrada.agora,
            )
            for endereco in self._provedor(entrada.consulta)
        ]
        validas = [c for c in candidatas if self._vale(c, entrada)]
        if not validas:
            raise SemResultadoAceitoError(entrada.consulta.texto)
        # max devolve a primeira entre as empatadas: a ordem do provedor desempata
        melhor = max(validas, key=lambda c: c.endereco.attributes.precisao.nivel)
        # reprojeta antes de guardar: o cache serve no CRS pedido sem reprojetar na leitura
        escolhida = self._no_crs(melhor, entrada.output_crs)
        self._cache.guardar(escolhida)
        return escolhida

    def _vale(
        self,
        geocodificacao: GeocodificacaoExterna,
        entrada: GeocodificacaoExternaInput,
    ) -> bool:
        return self._validador(
            ValidacaoGeocodificacaoInput(geocodificacao=geocodificacao, agora=entrada.agora)
        )

    def _no_crs(
        self,
        geocodificacao: GeocodificacaoExterna,
        output_crs: int,
    ) -> GeocodificacaoExterna:
        endereco = geocodificacao.endereco
        if endereco.crs == output_crs:
            return geocodificacao
        ponto = reprojetar(endereco.geometry, endereco.crs, output_crs)
        reprojetado = endereco.model_copy(update={"geometry": ponto, "crs": output_crs})
        return geocodificacao.model_copy(update={"endereco": reprojetado})
