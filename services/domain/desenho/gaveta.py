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
    ids_selecionados: tuple[str, ...] = ()
    crs_mapa: int
    crs_metrico: int
    crs_geografico: int

    @field_validator("desenhos", "ids_selecionados", mode="before")
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
            self._poco(tipo, do_tipo, entrada.ids_selecionados)
            for tipo in TipoDesenho
            if (do_tipo := tuple(m for m in medidos if m.desenho.tipo is tipo))
        )
        return GavetaDesenhos(pocos=pocos)

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

    def _poco(
        self,
        tipo: TipoDesenho,
        do_tipo: tuple[DesenhoMedido, ...],
        escolhidos: tuple[str, ...],
    ) -> PocoDesenhos:
        # A escolha do usuário vale enquanto o desenho existir; caindo ele, o último desenhado
        # daquele tipo assume — e é por isso que desenhar um ponto não desmarca o polígono.
        escolhido = next(
            (m.desenho.id_bancada for m in do_tipo if m.desenho.id_bancada in escolhidos),
            do_tipo[-1].desenho.id_bancada,
        )
        return PocoDesenhos(tipo=tipo, desenhos=do_tipo, id_selecionado=escolhido)
