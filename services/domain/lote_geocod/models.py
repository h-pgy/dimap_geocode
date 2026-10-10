from pydantic import BaseModel, Field, computed_field, field_validator

from services.domain.geometry import GeoFeature, PolygonGeometry

SITUACAO_ATIVA = "ATIVO"


class LoteGeocodInput(BaseModel):
    setor: str = Field(pattern=r"^\d{3}$")
    quadra: str = Field(pattern=r"^\d{3}$")
    lote: str = Field(pattern=r"^\d{4}$")
    tipo_lote: str
    layer_name: str
    cod_condominio: str | None = None

    @field_validator("tipo_lote", mode="before")
    @classmethod
    def _upper_tipo_lote(cls, v: object) -> str:
        return str(v).upper()
    output_crs: int


class LoteAttributes(BaseModel):
    """Atributos do lote (camada `attributes` da feature)."""
    id_poligono: str
    setor: str
    quadra: str
    lote: str
    tipo_lote: str
    digito: str | None = None          # cd_digito_sql; None = lote sem contribuinte
    codlog: str | None = None          # cd_logradouro (opcional, como os demais de origem)
    nome_logradouro: str = ""          # nm_logradouro_completo (str; '' quando ausente/None)
    numero_porta: str = ""             # cd_numero_porta ORIGINAL (str; '' quando ausente/None)
    complemento: str | None = None     # tx_complemento_endereco; None = não informado
    tipo_quadra: str | None = None
    condominio: str | None = None
    situacao: str | None = None        # tx_situ_lote
    uso: str | None = None             # dc_tipo_uso_imovel
    area_terreno_m2: float | None = None      # qt_area_terreno
    area_construida_m2: float | None = None   # qt_area_construida
    cib: str | None = None             # cd_cib

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_condominio(self) -> bool:
        """True quando o lote pertence a um condomínio (cd_condominio diferente de '00')."""
        return self.condominio is not None and self.condominio != "00"

    @field_validator("nome_logradouro", "numero_porta", mode="before")
    @classmethod
    def _none_para_vazio(cls, v: object) -> str:
        return "" if v is None else str(v)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def endereco(self) -> str:
        """Endereço por extenso da base oficial: nome do logradouro + número de porta."""
        partes = [p for p in (self.nome_logradouro, self.numero_porta) if p]
        return ", ".join(partes)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def endereco_completo(self) -> str:
        """O endereço inteiro, como a gaveta o lê: `endereco` + complemento em coluna própria."""
        partes = [p for p in (self.endereco, self.complemento) if p]
        return " — ".join(partes)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sql(self) -> str | None:
        """O número de contribuinte só existe com dígito."""
        if self.digito is None:
            return None
        return f"{self.setor}.{self.quadra}.{self.lote}-{self.digito}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def possui_lancamento(self) -> bool:
        """Possui lançamento é o lote ATIVO no cadastro, com contribuinte."""
        return self.sql is not None and self.situacao == SITUACAO_ATIVA


LoteFeature = GeoFeature[PolygonGeometry, LoteAttributes]


class LotePorIdentificadorInput(BaseModel):
    id_poligono: str = Field(pattern=r"^\d+$")
    layer_name: str
    output_crs: int
