from pydantic import BaseModel

from services.domain.geometry import reprojetar
from services.utils.normalization import normalize_text

from .exceptions import SemResultadoAceitoError
from .models import ConsultaGeocodificacao, EnderecoExternoFeature, Provedor
from .porta import ProvedorGeocodificacao


class GeocodificacaoExternaInput(BaseModel):
    consulta: ConsultaGeocodificacao
    output_crs: int


class GeocodificadorExterno:
    def __init__(self, provedor: ProvedorGeocodificacao) -> None:
        self._provedor = provedor

    @property
    def provedor(self) -> Provedor:
        return self._provedor.provedor

    def __call__(self, entrada: GeocodificacaoExternaInput) -> EnderecoExternoFeature:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GeocodificacaoExternaInput) -> EnderecoExternoFeature:
        candidatos = self._provedor(entrada.consulta)
        aceitos = [c for c in candidatos if self._no_recorte(c) and self._precisao_suficiente(c)]
        if not aceitos:
            raise SemResultadoAceitoError(entrada.consulta.texto)
        # max devolve o primeiro entre os empatados: a ordem do provedor desempata
        escolhido = max(aceitos, key=lambda c: c.attributes.precisao.nivel)
        return self._no_crs(escolhido, entrada.output_crs)

    def _no_recorte(self, candidato: EnderecoExternoFeature) -> bool:
        # o filtro de município do provedor pode ser só um viés: confere-se aqui
        politica = self._provedor.politica
        a = candidato.attributes
        if a.municipio is None or a.uf is None:
            return False
        return (
            normalize_text(a.municipio) == normalize_text(politica.municipio)
            and normalize_text(a.uf) == normalize_text(politica.uf)
        )

    def _precisao_suficiente(self, candidato: EnderecoExternoFeature) -> bool:
        return candidato.attributes.precisao.nivel >= self._provedor.politica.precisao_minima.nivel

    def _no_crs(self, escolhido: EnderecoExternoFeature, output_crs: int) -> EnderecoExternoFeature:
        if escolhido.crs == output_crs:
            return escolhido
        ponto = reprojetar(escolhido.geometry, escolhido.crs, output_crs)
        return escolhido.model_copy(update={"geometry": ponto, "crs": output_crs})
