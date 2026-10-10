from datetime import timedelta

from pydantic import AwareDatetime, BaseModel

from services.utils.normalization import normalize_text

from .models import EnderecoExternoFeature, GeocodificacaoExterna, PoliticaGeocodificacao


class ValidacaoGeocodificacaoInput(BaseModel):
    geocodificacao: GeocodificacaoExterna
    agora: AwareDatetime


class ValidadorGeocodificacao:
    def __init__(self, politica: PoliticaGeocodificacao) -> None:
        self._politica = politica

    def __call__(self, entrada: ValidacaoGeocodificacaoInput) -> bool:
        return self.pipeline(entrada)

    def pipeline(self, entrada: ValidacaoGeocodificacaoInput) -> bool:
        endereco = entrada.geocodificacao.endereco
        return (
            self._na_validade(entrada)
            and self._no_recorte(endereco)
            and self._precisao_suficiente(endereco)
        )

    def _na_validade(self, entrada: ValidacaoGeocodificacaoInput) -> bool:
        validade = timedelta(days=self._politica.validade_dias)
        return entrada.agora - entrada.geocodificacao.consultado_em < validade

    def _no_recorte(self, endereco: EnderecoExternoFeature) -> bool:
        # o filtro de município do provedor pode ser só um viés: confere-se aqui
        a = endereco.attributes
        if a.municipio is None or a.uf is None:
            return False
        return (
            normalize_text(a.municipio) == normalize_text(self._politica.municipio)
            and normalize_text(a.uf) == normalize_text(self._politica.uf)
        )

    def _precisao_suficiente(self, endereco: EnderecoExternoFeature) -> bool:
        return endereco.attributes.precisao.nivel >= self._politica.precisao_minima.nivel
