from pathlib import Path

from pydantic import BaseModel


class EnderecosFiscaisRequest(BaseModel):
    layer_name: str


class EnderecoFiscal(BaseModel):
    cd_identificador: str
    cd_setor_fiscal: str | None = None
    cd_tipo_quadra: str | None = None
    cd_quadra_fiscal: str | None = None
    cd_condominio: str | None = None
    cd_tipo_lote: str | None = None
    cd_lote: str | None = None
    cd_digito_sql: str | None = None
    cd_logradouro: str | None = None
    nm_logradouro_completo: str | None = None
    cd_numero_porta: str | None = None
    tx_complemento_endereco: str | None = None


class EnderecosFiscaisResult(BaseModel):
    total_records: int
    output_path: Path
