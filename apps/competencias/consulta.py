"""
A borda que traduz banco → DTO do avaliador de competência (SPEC autorizacao/003): monta as
canetas do perfil, as concessões das unidades delas e os slugs estruturais, numa passagem só —
custo fixo, independente de quantas ações serão perguntadas depois (SPEC autorizacao/003, Caveats).
"""

from django.db.models import Q
from django.utils import timezone

from apps.competencias.models import Concessao
from apps.competencias.registro import REGISTRO
from apps.unidades.consulta import posicao_de
from apps.unidades.direcao import estado_da_direcao
from apps.unidades.models import Unidade
from apps.user_admin.models import Perfil
from apps.user_admin.substituicao import substituicao_que_exerce, substituicao_vigente
from services.domain.arvore_hierarquica import NoHierarquia
from services.domain.autorizacao import (
    AvaliacaoCompetenciaInput,
    Caneta,
    ConcessaoVigente,
    DelegacaoVigente,
    PerfilCompetencia,
    avaliar_competencia,
)
from services.domain.titularidade import Direcao, avaliar_direcao


def montar_avaliacao(perfil: Perfil) -> AvaliacaoCompetenciaInput:
    """Canetas do perfil, concessões das unidades dessas canetas, slugs estruturais e delegações nominais vigentes."""
    canetas = canetas_do_perfil(perfil)
    unidades_das_canetas = frozenset(caneta.unidade_id for caneta in canetas)
    concessoes = tuple(
        ConcessaoVigente(
            acao_slug=concessao.atribuicao.acao.slug,
            acao_ativa=concessao.atribuicao.acao.ativa,
            unidade_id=concessao.atribuicao.unidade_id,
            cargo_base_id=concessao.cargo_base_id,
            cargo_comissao_id=concessao.cargo_comissao_id,
        )
        for concessao in Concessao.objects.filter(
            atribuicao__unidade_id__in=unidades_das_canetas,
            # Competência de unidade extinta não é competência de ninguém (SPEC user_admin/025).
            extinta_em__isnull=True,
        ).select_related("atribuicao__acao")
    )
    hoje = timezone.localdate()
    from apps.competencias.models.delegacao import Delegacao

    delegacoes = tuple(
        DelegacaoVigente(
            acao_slug=d.acao.slug,
            acao_ativa=d.acao.ativa,
            unidade_id=d.unidade_id,
            delegado_id=d.delegado_id,
        )
        for d in Delegacao.objects.filter(
            delegado=perfil,
            data_inicio__lte=hoje,
        )
        .filter(Q(data_fim__isnull=True) | Q(data_fim__gte=hoje))
        .select_related("acao")
    )
    return AvaliacaoCompetenciaInput(
        perfil=PerfilCompetencia(em_exercicio=perfil.em_exercicio, canetas=canetas),
        concessoes=concessoes,
        slugs_estruturais=_slugs_estruturais(),
        slugs_exclusivos=slugs_exclusivos(),
        delegacoes=delegacoes,
    )


def canetas_do_perfil(perfil: Perfil) -> tuple[Caneta, ...]:
    """A própria mais a coberta. A cobertura entra com a unidade e os cargos do SUBSTITUÍDO, que é
    quem tem a competência emprestada."""
    canetas = [_caneta_de(quem_exerce=perfil, dono_do_cargo=perfil)]
    substituicao = substituicao_que_exerce(perfil)
    if substituicao is not None:
        canetas.append(
            _caneta_de(quem_exerce=perfil, dono_do_cargo=substituicao.impedimento.perfil)
        )
    return tuple(canetas)


def dirige(perfil: Perfil, unidade: Unidade) -> bool:
    """Confere se quem `avaliar_direcao` aponta é este perfil — titular ou substituto dele. A regra
    de direção não é reescrita aqui, e o estado é o mesmo que a página da unidade monta."""
    titular = unidade.titular
    substituicao = substituicao_vigente(titular) if titular else None
    substituto = substituicao.substituto if substituicao else None
    direcao = avaliar_direcao(estado_da_direcao(titular, substituto))
    if direcao == Direcao.TITULAR:
        return titular is not None and titular.pk == perfil.pk
    if direcao == Direcao.SUBSTITUTO:
        return substituto is not None and substituto.pk == perfil.pk
    return False


def unidades_dirigidas(perfil: Perfil) -> frozenset[int]:
    """As unidades das canetas que dirigem — pode ser mais de uma, quando alguém cobre o titular de
    outra unidade. É daqui que a SPEC 004 parte para calcular o alcance."""
    return frozenset(
        caneta.unidade_id for caneta in canetas_do_perfil(perfil) if caneta.dirige_a_unidade
    )


def _caneta_de(quem_exerce: Perfil, dono_do_cargo: Perfil) -> Caneta:
    return Caneta(
        unidade_id=dono_do_cargo.unidade_id,
        cargo_base_id=dono_do_cargo.cargo_base_id,
        cargo_comissao_id=dono_do_cargo.cargo_comissao_id,
        dirige_a_unidade=dirige(quem_exerce, dono_do_cargo.unidade),
    )


def unidades_delegadas(perfil: Perfil) -> frozenset[int]:
    return avaliar_competencia(montar_avaliacao(perfil)).unidades_delegadas


def partidas_do_alcance(perfil: Perfil) -> frozenset[int]:
    """As unidades de onde o alcance parte: as dirigidas e as recebidas por delegação. Extraída de
    `ramos_do_alcance`, que já a calculava para descartar o ramo contido (SPEC user_admin/025)."""
    return unidades_dirigidas(perfil) | unidades_delegadas(perfil)


def ramos_do_alcance(perfil: Perfil, com_extintas: bool = False) -> tuple[NoHierarquia, ...]:
    """As subárvores que o perfil alcança — uma por unidade dirigida que não pende de outra dirigida.
    Cobrir o titular de uma subordinada é dirigir duas unidades do mesmo ramo: a de baixo já está
    dentro da de cima, e mantê-la seria percorrer e desenhar duas vezes a parte comum.

    `com_extintas` (SPEC user_admin/025) desce até QUEM LÊ O BANCO, e desce pelos dois ramos da
    função — o do superusuário monta as raízes por conta própria e ficaria com o organograma
    vigente enquanto o outro via as extintas."""
    if perfil.is_superuser:
        # O organograma inteiro, na MESMA forma que o recorte já devolve (SPEC user_admin/020):
        # assim `alcance_do_perfil`, a árvore da tela e os selects ficam certos de uma vez, sem
        # `is_superuser` espalhado em cada um.
        gerente = Unidade.todas if com_extintas else Unidade.objects
        return tuple(
            posicao_de(raiz.pk, com_extintas=com_extintas).ego
            for raiz in gerente.filter(pai__isnull=True)
        )
    partidas = partidas_do_alcance(perfil)
    arvores = {
        partida: posicao_de(partida, com_extintas=com_extintas).ego for partida in partidas
    }
    return tuple(
        arvore
        for partida, arvore in arvores.items()
        if not any(outra != partida and partida in arvores[outra].ids for outra in arvores)
    )


def alcance_do_perfil(perfil: Perfil, com_extintas: bool = False) -> frozenset[int]:
    """"Unidades subordinadas" não é conceito, é esta projeção: os ramos alcançados reduzidos a ids.
    Descartar o ramo contido não muda o conjunto — ele já está inteiro dentro do outro.

    O default `False` (SPEC user_admin/025) é o que mantém as outras ações intocadas: só
    `UnidadesEstritamenteSubordinadas` pede `True`, e pede por um motivo só — sem ele a unidade
    recém-extinta sai do alcance de quem a extinguiu e ninguém consegue reativá-la."""
    return frozenset[int]().union(
        *(ramo.ids for ramo in ramos_do_alcance(perfil, com_extintas))
    )


def alcance_de_leitura(perfil: Perfil) -> frozenset[int]:
    """Até onde este perfil PODE ler o registro (SPEC painel/002): a própria unidade sempre, mais a
    subárvore de cada unidade que dirige.

    Sem `if` para nenhum dos dois papéis, e é isso que a expressão mostra. Quem não dirige nada cai
    no caso base — `alcance_do_perfil` devolve conjunto vazio e sobra a lotação. O superusuário
    recebe o organograma inteiro pelo mesmo caminho: `ramos_do_alcance` já o trata na origem, para
    não espalhar `is_superuser` por quem a consulta.

    `com_extintas=True` porque o registro é histórico: unidade extinta ontem praticou atos que
    continuam sendo dela, e sumir com eles do alcance de quem a dirigia apagaria justamente o
    período que se quer auditar.
    """
    return frozenset({perfil.unidade_id}) | alcance_do_perfil(perfil, com_extintas=True)


def unidades_lidas(perfil: Perfil, unidade_escolhida: int | None) -> frozenset[int]:
    """O que a tela lê AGORA (SPEC painel/002): a subárvore da unidade de onde se parte, contida no
    alcance.

    A unidade nunca é ausência — quem não escolhe parte da própria, e é essa escolha implícita que
    faz a página nascer no ramo do leitor em vez de no registro inteiro.

    A interseção é a regra toda, e ela resolve os dois papéis de uma vez: para quem não dirige, o
    alcance é uma unidade só e a subárvore da própria lotação encolhe para ela; para quem dirige,
    a subárvore é o ramo e o alcance a deixa passar inteira. Fora do alcance nem se pergunta à
    árvore — é vazio, e não 403, porque aqui o alcance recorta o resultado, não barra a entrada.
    """
    alcance = alcance_de_leitura(perfil)
    partida = unidade_escolhida or perfil.unidade_id
    if partida not in alcance:
        return frozenset()
    return frozenset(posicao_de(partida, com_extintas=True).ego.ids) & alcance


def _slugs_estruturais() -> frozenset[str]:
    return frozenset(
        implementada.acao.slug for implementada in REGISTRO.todas() if implementada.acao.estrutural
    )


def slugs_exclusivos() -> frozenset[str]:
    """Público (SPEC user_admin/022): o MESMO conjunto que o avaliador subtrai é o que recorta o
    catálogo de atribuir — um segundo lugar computando "quais são as exclusivas" seria a
    divergência esperando para acontecer."""
    return frozenset(
        implementada.acao.slug
        for implementada in REGISTRO.todas()
        if implementada.acao.exclusiva_superusuario
    )
