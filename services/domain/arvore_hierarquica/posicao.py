"""Regra do domínio (SPEC user_admin/018): a posição de uma unidade no organograma."""

from collections.abc import Mapping

from .models import ComandoPosicao, NoHierarquia, ParHierarquia, PosicaoHierarquica


class ArvoreHierarquica:
    """A hierarquia percorrida a partir de uma unidade. Recebe as arestas por DTO: a regra é
    testável sem banco, e o organograma cabe numa consulta só."""

    def __call__(self, comando: ComandoPosicao) -> PosicaoHierarquica:
        return self.pipeline(comando)

    def pipeline(self, comando: ComandoPosicao) -> PosicaoHierarquica:
        # Os dois índices são as duas direções de leitura da mesma aresta.
        pai_de = self._indexar_pais(comando.pares)
        filhas_de = self._indexar_filhas(comando.pares)
        return PosicaoHierarquica(
            acima=self._subir_ate_o_topo(comando.unidade_id, pai_de),
            ego=self._descer(comando.unidade_id, filhas_de, visitados=set()),
        )

    def _indexar_pais(self, pares: tuple[ParHierarquia, ...]) -> Mapping[int, int | None]:
        return {par.unidade_id: par.pai_id for par in pares}

    def _indexar_filhas(self, pares: tuple[ParHierarquia, ...]) -> Mapping[int, tuple[int, ...]]:
        filhas_de: dict[int, list[int]] = {}
        for par in pares:
            if par.pai_id is not None:
                filhas_de.setdefault(par.pai_id, []).append(par.unidade_id)
        return {pai_id: tuple(filhas) for pai_id, filhas in filhas_de.items()}

    def _subir_ate_o_topo(
        self,
        unidade_id: int,
        pai_de: Mapping[int, int | None],
    ) -> tuple[int, ...]:
        """Um pai por unidade, então subir é um caminho, não uma busca. Sai do topo para o pai
        porque é essa a ordem em que o organograma se lê."""
        trilha: list[int] = []
        atual = pai_de.get(unidade_id)
        # `not in trilha` é a guarda do ciclo longo: o banco só barra a unidade que é pai de si
        # mesma (SPEC 003), e A→B→A subiria para sempre.
        while atual is not None and atual not in trilha:
            trilha.append(atual)
            atual = pai_de.get(atual)
        return tuple(reversed(trilha))

    def _descer(
        self,
        unidade_id: int,
        filhas_de: Mapping[int, tuple[int, ...]],
        visitados: set[int],
    ) -> NoHierarquia:
        # A mesma guarda, do outro lado: sem o conjunto de visitados, A→B→A recursiona até estourar
        # a pilha.
        visitados.add(unidade_id)
        return NoHierarquia(
            unidade_id=unidade_id,
            filhas=tuple(
                self._descer(filha, filhas_de, visitados)
                for filha in filhas_de.get(unidade_id, ())
                if filha not in visitados
            ),
        )
