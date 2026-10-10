import json

from pydantic import BaseModel, field_validator

from services.domain.geometry import para_geos, reprojetar

from .models import (
    Coordenada,
    Desenho,
    DesenhoMedido,
    Eixo,
    GavetaDesenhos,
    Grandeza,
    Medida,
    PocoDesenhos,
    Posicao,
    TipoDesenho,
)


class GavetaDesenhosInput(BaseModel):
    desenhos: tuple[Desenho, ...]
    id_selecionado: str | None = None
    crs_mapa: int
    crs_metrico: int
    crs_geografico: int

    @field_validator("desenhos", mode="before")
    @classmethod
    def _do_json(cls, valor: object) -> object:
        # O formulário manda texto: JSON malformado vira ValidationError e cai no middleware.
        return json.loads(valor) if isinstance(valor, str) else valor


GRANDEZA_POR_TIPO = {
    TipoDesenho.LINHA: Grandeza.COMPRIMENTO,
    TipoDesenho.POLIGONO: Grandeza.AREA,
}


class MontarGavetaDesenhos:
    def __call__(self, entrada: GavetaDesenhosInput) -> GavetaDesenhos:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GavetaDesenhosInput) -> GavetaDesenhos:
        medidos = tuple(self._medir(desenho, entrada) for desenho in entrada.desenhos)
        # A ordem dos poços é a do enum — ponto, linha, polígono —, e tipo sem desenho não vira poço.
        pocos = tuple(
            PocoDesenhos(tipo=tipo, desenhos=do_tipo)
            for tipo in TipoDesenho
            if (do_tipo := tuple(m for m in medidos if m.desenho.tipo is tipo))
        )
        return GavetaDesenhos(pocos=pocos, id_selecionado=self._selecionado(entrada))

    def _medir(self, desenho: Desenho, entrada: GavetaDesenhosInput) -> DesenhoMedido:
        grandeza = GRANDEZA_POR_TIPO.get(desenho.tipo)
        if grandeza is None:
            return DesenhoMedido(desenho=desenho, posicao=self._localizar(desenho, entrada))
        projetado = reprojetar(  # type: ignore[type-var]
            desenho.geometria, entrada.crs_mapa, entrada.crs_metrico
        )
        geos = para_geos(projetado, entrada.crs_metrico)
        valor = geos.area if grandeza is Grandeza.AREA else geos.length
        return DesenhoMedido(desenho=desenho, medida=Medida(grandeza=grandeza, valor=valor))

    def _localizar(self, desenho: Desenho, entrada: GavetaDesenhosInput) -> Posicao:
        # GeoJSON é (x, y): longitude primeiro.
        longitude, latitude = reprojetar(  # type: ignore[type-var]
            desenho.geometria, entrada.crs_mapa, entrada.crs_geografico
        ).coordinates
        return Posicao(
            latitude=Coordenada(eixo=Eixo.LATITUDE, graus_decimais=latitude),
            longitude=Coordenada(eixo=Eixo.LONGITUDE, graus_decimais=longitude),
        )

    def _selecionado(self, entrada: GavetaDesenhosInput) -> str | None:
        # Apagado o escolhido, ninguém assume: sem seleção, nenhum poço oferece ação.
        existentes = {desenho.id_bancada for desenho in entrada.desenhos}
        return entrada.id_selecionado if entrada.id_selecionado in existentes else None
