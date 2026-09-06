from collections.abc import Sequence

from .models import (
    CampoDeFormulario,
    CampoRecusado,
    ErroBruto,
    Formulario,
    RecusaDeFormulario,
    RegraDeErro,
)
from .regras import REGRA_DESCONHECIDA, REGRAS_PADRAO


class TradutorDeRecusa:
    """Callable: erros crus → o que a tela mostra. O catálogo é do formulário e não muda entre
    requisições, então ele é do construtor; o que varia é a recusa."""

    def __init__(self, formulario: Formulario) -> None:
        self.formulario = formulario

    def __call__(self, erros: Sequence[ErroBruto]) -> RecusaDeFormulario:
        return self.pipeline(erros)

    def pipeline(self, erros: Sequence[ErroBruto]) -> RecusaDeFormulario:
        catalogo = self.formulario.por_controle
        recusados = [erro for erro in erros if erro.controle in catalogo]
        soltos = [erro for erro in erros if erro.controle not in catalogo]
        return RecusaDeFormulario(
            campos=tuple(
                self._recusar(erro, catalogo[erro.controle]) for erro in recusados
            ),
            # Erro que não bate com controle algum — o `__all__` do Django, ou um campo do DTO que
            # não tem input (a `url_acesso` resolvida na orquestração) — não realça nada: não há o
            # que destacar, e inventar um controle apontaria o dedo para o campo errado.
            gerais=tuple(erro.mensagem for erro in soltos if erro.mensagem),
        )

    def _recusar(self, erro: ErroBruto, campo: CampoDeFormulario) -> CampoRecusado:
        regra = self._regra(erro, campo)
        # A mensagem da fonte vence a do catálogo: quem já fala português é o model, e o texto da
        # unicidade mora junto da constraint que a define.
        mensagem = erro.mensagem or regra.mensagem.format(rotulo=campo.rotulo)
        return CampoRecusado(controle=campo.controle, mensagem=mensagem, tom=regra.tom)

    def _regra(self, erro: ErroBruto, campo: CampoDeFormulario) -> RegraDeErro:
        if erro.tipo in campo.regras:
            return campo.regras[erro.tipo]
        return REGRAS_PADRAO.get(erro.tipo, REGRA_DESCONHECIDA)
