"""
Servidores fictícios (SPEC user_admin/013): o andaime que torna a listagem exercitável no sistema
enquanto gravar perfil não existe. Não é seed — seed é catálogo versionado de que a aplicação
depende para funcionar —, por isso não vive em `data/seed/` nem em `apps/user_admin/seeds/`.

Eles ocupam uma FAIXA DE RF RESERVADA, e é ela que torna a remoção segura: apagar por faixa nunca
vira um `Perfil.objects.all().delete()` executado no banco errado. Nascem sem senha utilizável —
dado de desenvolvimento não deve criar credencial que funcione.

Mexe em persistência e orquestração, não em domínio: por isso vive no app, não em `services/`.
"""

from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from pydantic import BaseModel

from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Impedimento,
    Perfil,
    TipoImpedimento,
    Unidade,
)
from apps.user_admin.models.titularidade import cargo_titulariza
from apps.user_admin.titularidade import definir_titular

# Longe de qualquer RF real: seis dígitos altos que a Prefeitura não emite.
RF_INICIAL_FICTICIO = 999900
QUANTIDADE_FICTICIOS = 20
FAIXA_RF_FICTICIA = [
    str(rf)
    for rf in range(RF_INICIAL_FICTICIO, RF_INICIAL_FICTICIO + QUANTIDADE_FICTICIOS)
]
# Um impedimento que começou ontem e não terminou: vigente hoje, sem depender do relógio do teste.
DIAS_DESDE_O_INICIO = 1
# Ritmos diferentes de propósito: as quatro combinações de situação × cargo em comissão aparecem.
PASSO_IMPEDIMENTO = 2
PASSO_COMISSAO = 3
# Uma unidade elegível fica de fora: a vaga é o estado que a tela da SPEC 016 existe para acusar.
UNIDADES_SEM_TITULAR = 1
ERRO_SEM_CATALOGO = (
    "sem unidades, cargos ou tipos de impedimento cadastrados: rode as seeds antes "
    "(seed_unidades, seed_cargos, seed_tipos_impedimento)."
)

NOMES_FICTICIOS = [
    ("Marina", "Salles"),
    ("João", "Cavalcanti"),
    ("Antônia", "Nóbrega"),
    ("Ricardo", "Aparício"),
    ("Célia", "Gonçalves"),
    ("Paulo", "Assunção"),
    ("Íris", "Sant'Anna"),
    ("Fernando", "Mendonça"),
    ("Beatriz", "Camargo"),
    ("Otávio", "Bandeira"),
    ("Luísa", "Rezende"),
    ("Gustavo", "Peixoto"),
    ("Helena", "Vasconcelos"),
    ("Sérgio", "Almeida"),
    ("Tereza", "D'Ávila"),
    ("Murilo", "Tanaka"),
    ("Cecília", "Bittencourt"),
    ("Rodrigo", "Furtado"),
    ("Vanessa", "Queiroz"),
    ("Anselmo", "São Thiago"),
]


class ContagemFicticios(BaseModel):
    criados: int
    impedidos: int
    com_comissao: int
    titulares: int


class RemocaoFicticios(BaseModel):
    removidos: int


class CriadorServidoresFicticios:
    """Grava os perfis da faixa reservada e os impedimentos vigentes de metade deles."""

    def __call__(self) -> ContagemFicticios:
        return self.pipeline()

    def pipeline(self) -> ContagemFicticios:
        unidades = list(Unidade.objects.order_by("sigla"))
        cargos_base = list(CargoBase.objects.order_by("nome"))
        cargos_comissao = list(CargoComissao.objects.order_by("nome"))
        tipos_impedimento = list(TipoImpedimento.objects.order_by("nome"))
        self._checar_catalogos(
            unidades, cargos_base, cargos_comissao, tipos_impedimento
        )
        # A carga anterior sai antes: sem isso, rodar de novo acumularia impedimentos em quem já os
        # tinha e o "sem impedimento" da vez passada continuaria impedido.
        self._limpar_impedimentos()
        impedidos = 0
        com_comissao = 0
        perfis = []
        for indice, rf in enumerate(FAIXA_RF_FICTICIA):
            tem_comissao = indice % PASSO_COMISSAO == 0
            perfil = self._gravar_perfil(
                indice=indice,
                rf=rf,
                unidade=unidades[indice % len(unidades)],
                cargo_base=cargos_base[indice % len(cargos_base)],
                cargo_comissao=(
                    cargos_comissao[indice % len(cargos_comissao)]
                    if tem_comissao
                    else None
                ),
            )
            perfis.append(perfil)
            com_comissao += int(tem_comissao)
            if indice % PASSO_IMPEDIMENTO == 0:
                self._impedir(
                    perfil, tipos_impedimento[indice % len(tipos_impedimento)]
                )
                impedidos += 1
        titulares = self._titularizar(perfis, cargos_comissao)
        return ContagemFicticios(
            criados=len(FAIXA_RF_FICTICIA),
            impedidos=impedidos,
            com_comissao=com_comissao,
            titulares=titulares,
        )

    def _checar_catalogos(
        self,
        unidades: list[Unidade],
        cargos_base: list[CargoBase],
        cargos_comissao: list[CargoComissao],
        tipos_impedimento: list[TipoImpedimento],
    ) -> None:
        # Os fictícios se distribuem pelo catálogo que as seeds gravam; não inventam catálogo.
        if not (unidades and cargos_base and cargos_comissao and tipos_impedimento):
            raise ObjectDoesNotExist(ERRO_SEM_CATALOGO)

    def _limpar_impedimentos(self) -> None:
        Impedimento.objects.filter(perfil__rf__in=FAIXA_RF_FICTICIA).delete()

    def _gravar_perfil(
        self,
        indice: int,
        rf: str,
        unidade: Unidade,
        cargo_base: CargoBase,
        cargo_comissao: CargoComissao | None,
    ) -> Perfil:
        nome, sobrenome = NOMES_FICTICIOS[indice]
        perfil, _ = Perfil.objects.update_or_create(
            rf=rf,
            defaults={
                "nome": nome,
                "sobrenome": sobrenome,
                "unidade": unidade,
                "cargo_base": cargo_base,
                "cargo_comissao": cargo_comissao,
            },
        )
        perfil.set_unusable_password()
        perfil.save(update_fields=["password"])
        return perfil

    def _impedir(self, perfil: Perfil, tipo: TipoImpedimento) -> None:
        # Sem data de fim: impedimento vigente hoje e amanhã, sem manutenção de datas no andaime.
        Impedimento.objects.create(
            perfil=perfil,
            tipo=tipo,
            data_inicio=timezone.localdate() - timedelta(days=DIAS_DESDE_O_INICIO),
            data_fim=None,
        )

    def _titularizar(
        self,
        perfis: list[Perfil],
        cargos_comissao: list[CargoComissao],
    ) -> int:
        # Uma unidade elegível fica de fora: a vaga é o estado que a tela da SPEC 016 acusa.
        titulaveis = self._um_por_unidade(perfis)[:-UNIDADES_SEM_TITULAR]
        titularizados = 0
        for perfil in titulaveis:
            cargo = self._cargo_que_titulariza(perfil.unidade, cargos_comissao)
            if cargo is None:
                continue
            # O cargo vem do porte da unidade, não do rodízio: senão o clean recusaria a marca.
            perfil.cargo_comissao = cargo
            perfil.save(update_fields=["cargo_comissao"])
            definir_titular(perfil)
            titularizados += 1
        return titularizados

    def _um_por_unidade(self, perfis: list[Perfil]) -> list[Perfil]:
        escolhidos: dict[int, Perfil] = {}
        for perfil in perfis:
            escolhidos.setdefault(perfil.unidade_id, perfil)
        return list(escolhidos.values())

    def _cargo_que_titulariza(
        self,
        unidade: Unidade,
        cargos_comissao: list[CargoComissao],
    ) -> CargoComissao | None:
        tipo = unidade.tipo
        return next(
            (
                cargo
                for cargo in cargos_comissao
                if cargo_titulariza(
                    cargo,
                    exige_alta_administracao=tipo.exige_alta_administracao,
                    nivel_minimo=tipo.nivel_minimo_titular,
                )
            ),
            None,
        )


def criar_servidores_ficticios() -> ContagemFicticios:
    with transaction.atomic():
        return CriadorServidoresFicticios()()


def remover_servidores_ficticios() -> RemocaoFicticios:
    # Por faixa, e só por ela: é esta linha que protege o banco de quem rodar o comando distraído.
    ficticios = Perfil.objects.filter(rf__in=FAIXA_RF_FICTICIA)
    with transaction.atomic():
        removidos = ficticios.count()
        ficticios.delete()
    return RemocaoFicticios(removidos=removidos)
