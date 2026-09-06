"""
O avaliador de competência (SPEC autorizacao/003): decide, em Python, sobre as linhas já
carregadas — nenhuma consulta aqui, nenhum conhecimento de titularidade ou de registro de ações.
"""

from services.domain.autorizacao.models import (
    AvaliacaoCompetenciaInput,
    AvaliacaoCompetenciaOutput,
    Caneta,
    ConcessaoVigente,
    DelegacaoVigente,
)


class AvaliadorCompetencia:
    def __call__(self, entrada: AvaliacaoCompetenciaInput) -> AvaliacaoCompetenciaOutput:
        # Pré-condição, não terceira fonte: competência é do cargo exercido.
        if not entrada.perfil.em_exercicio:
            return AvaliacaoCompetenciaOutput(slugs_liberados=frozenset())

        concessoes_batidas = self._concessoes_que_batem(entrada)
        delegacoes_batidas = self._delegacoes_que_batem(entrada)

        slugs_concedidos = frozenset(c.acao_slug for c in concessoes_batidas)
        slugs_delegados = frozenset(d.acao_slug for d in delegacoes_batidas)
        slugs_direcao = self._por_direcao(entrada)

        return AvaliacaoCompetenciaOutput(
            # Subtrair no fim, e não filtrar cada fonte: quem chega aqui NUNCA é superusuário — o
            # `PermissionsMixin.has_perm` responde True antes de consultar backend algum —, então
            # tirar o slug do conjunto é exatamente dizer "só ele exerce" (SPEC user_admin/020).
            slugs_liberados=(slugs_concedidos | slugs_delegados | slugs_direcao)
            - entrada.slugs_exclusivos,
            unidades_delegadas=frozenset(d.unidade_id for d in delegacoes_batidas),
        )

    def _concessoes_que_batem(
        self, entrada: AvaliacaoCompetenciaInput
    ) -> tuple[ConcessaoVigente, ...]:
        return tuple(
            c
            for c in entrada.concessoes
            if c.acao_ativa
            and any(self._caneta_bate(caneta, c) for caneta in entrada.perfil.canetas)
        )

    def _delegacoes_que_batem(
        self, entrada: AvaliacaoCompetenciaInput
    ) -> tuple[DelegacaoVigente, ...]:
        return tuple(d for d in entrada.delegacoes if d.acao_ativa)

    def _por_direcao(self, entrada: AvaliacaoCompetenciaInput) -> frozenset[str]:
        """O atalho de quem responde pela direção: `dirige_a_unidade` é o campo que só a caneta
        tem, e ele libera as estruturais sem consultar concessão nenhuma.

        Não há filtro de ação inativa aqui: os slugs vêm do registro em código, e ação inativa é
        justamente a que saiu de lá."""
        if not any(caneta.dirige_a_unidade for caneta in entrada.perfil.canetas):
            return frozenset()
        return entrada.slugs_estruturais

    def _caneta_bate(self, caneta: Caneta, concessao: ConcessaoVigente) -> bool:
        """A conferência que dá sentido às duas listas: mesma unidade E mesmo cargo.

        O cargo é comparado DENTRO da caneta — o cargo do coberto vale na unidade dele, não na do
        substituto, e cruzar os dois liberaria competência em unidade alheia."""
        if caneta.unidade_id != concessao.unidade_id:
            return False
        # A concessão nomeia exatamente um cargo (XOR do `CheckConstraint`, SPEC 002): o ramo
        # preenchido é o que se compara, e o `None` do outro lado nunca casa por acidente.
        if concessao.cargo_base_id is not None:
            return concessao.cargo_base_id == caneta.cargo_base_id
        return concessao.cargo_comissao_id == caneta.cargo_comissao_id


def avaliar_competencia(entrada: AvaliacaoCompetenciaInput) -> AvaliacaoCompetenciaOutput:
    return AvaliadorCompetencia()(entrada)
