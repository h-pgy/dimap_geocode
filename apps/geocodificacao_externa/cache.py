from typing import Any

from services.domain.geocodificador_externo import (
    ConsultaGeocodificacao,
    EnderecoExternoAttributes,
    EnderecoExternoFeature,
    GeocodificacaoExterna,
    Precisao,
    Provedor,
)
from services.domain.geometry import PointGeometry, de_geos, para_geos

from .models import SRID_PONTO, GeocodificacaoGuardada


class CacheEmBanco:
    def buscar(self, consulta: ConsultaGeocodificacao) -> GeocodificacaoExterna | None:
        linha = GeocodificacaoGuardada.objects.filter(chave=consulta.chave).first()
        return None if linha is None else self._para_dominio(linha)

    def guardar(self, geocodificacao: GeocodificacaoExterna) -> None:
        GeocodificacaoGuardada.objects.update_or_create(
            chave=geocodificacao.consulta.chave,
            defaults=self._para_colunas(geocodificacao),
        )

    def _para_colunas(self, geocodificacao: GeocodificacaoExterna) -> dict[str, Any]:
        endereco = geocodificacao.endereco
        a = endereco.attributes
        return {
            "consulta": geocodificacao.consulta.texto,
            "provedor": a.provedor.value,
            "consultado_em": geocodificacao.consultado_em,
            "ponto": para_geos(endereco.geometry, endereco.crs),
            "endereco_formatado": a.endereco_formatado,
            "logradouro": a.logradouro,
            "numero": a.numero,
            "bairro": a.bairro,
            "municipio": a.municipio,
            "uf": a.uf,
            "cep": a.cep,
            "precisao": a.precisao.value,
        }

    def _para_dominio(self, linha: GeocodificacaoGuardada) -> GeocodificacaoExterna:
        return GeocodificacaoExterna(
            consulta=ConsultaGeocodificacao(texto=linha.consulta),
            endereco=EnderecoExternoFeature(
                geometry=de_geos(linha.ponto, PointGeometry),
                attributes=EnderecoExternoAttributes(
                    endereco_formatado=linha.endereco_formatado,
                    logradouro=linha.logradouro,
                    numero=linha.numero,
                    bairro=linha.bairro,
                    municipio=linha.municipio,
                    uf=linha.uf,
                    cep=linha.cep,
                    # o provedor que encontrou, não o que está em uso
                    provedor=Provedor(linha.provedor),
                    precisao=Precisao(linha.precisao),
                ),
                # srid é opcional no GEOS; ponto lido desta coluna só pode estar no SRID dela
                crs=linha.ponto.srid or SRID_PONTO,
            ),
            consultado_em=linha.consultado_em,
        )
