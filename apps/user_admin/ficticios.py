"""
Servidores fictícios (SPEC user_admin/013): o andaime que torna a listagem exercitável no sistema
enquanto gravar perfil não existe. Não é seed — seed é catálogo versionado de que a aplicação
depende para funcionar —, por isso não vive em `data/seed/` nem em `apps/user_admin/seeds/`.

Eles ocupam uma FAIXA DE RF RESERVADA, e é ela que torna a remoção segura: apagar por faixa nunca
vira um `Perfil.objects.all().delete()` executado no banco errado. Nascem sem senha utilizável —
dado de desenvolvimento não deve criar credencial que funcione.

Mexe em persistência e orquestração, não em domínio: por isso vive no app, não em `services/`.
"""

from collections.abc import Iterator
from datetime import date, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from pydantic import BaseModel

from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Impedimento,
    Perfil,
    TipoImpedimento,
    Unidade,
)
from apps.user_admin.models.titularidade import cargo_titulariza
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento
from apps.user_admin.titularidade import definir_titular

# Longe de qualquer RF real: sete dígitos altos que a Prefeitura não emite.
RF_INICIAL_FICTICIO = 9999000
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
# O roteiro dos estados de exercício (SPEC user_admin/015), em dias em torno de hoje. Datas
# relativas, e não fixas: o andaime é rodado em qualquer dia e os estados têm que valer no dia em
# que se olha para a tela.
DIAS_AFASTAMENTO_LONGO = 20
DIAS_COBERTURA_ENCERRADA = 11
DIAS_COBERTURA_VIGENTE = 5
DIAS_ATE_O_AFASTAMENTO_FUTURO = 30
DIAS_DO_AFASTAMENTO_FUTURO = 40
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
    """Grava os perfis da faixa reservada e encena neles os estados de exercício da SPEC 015."""

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
        # A carga anterior sai antes: sem isso, rodar de novo acumularia afastamento em quem já o
        # tinha e o "sem impedimento" da vez passada continuaria impedido.
        self._limpar_exercicio()
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
        # Titularizar antes de afastar: é a titularidade que diz quais afastamentos deixam uma
        # unidade sem direção, e é ela que decide o cargo em comissão de quem dirige.
        titulares = self._titularizar(perfis, cargos_comissao)
        impedidos = self._encenar_exercicio(perfis, titulares, tipos_impedimento)
        return ContagemFicticios(
            criados=len(FAIXA_RF_FICTICIA),
            impedidos=impedidos,
            com_comissao=com_comissao,
            titulares=len(titulares),
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

    def _limpar_exercicio(self) -> None:
        # As substituições caem junto com os impedimentos, pela relação; a reativação desfaz a
        # exoneração que esta mesma carga encenou.
        ficticios = Perfil.objects.filter(rf__in=FAIXA_RF_FICTICIA)
        Impedimento.objects.filter(perfil__in=ficticios).delete()
        ficticios.update(is_active=True)

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

    def _encenar_exercicio(
        self,
        perfis: list[Perfil],
        titulares: list[Perfil],
        tipos: list[TipoImpedimento],
    ) -> int:
        """Os seis estados que a seção de exercício precisa deixar exercitáveis. Cada papel é
        escalado uma vez só, e o que sobra vira substituto — quem cobre não precisa de cargo."""
        escalados: list[Perfil] = []
        comissionados = [p for p in perfis if p.cargo_comissao_id is not None]
        papeis = {
            papel: self._escalar(candidatos, escalados)
            for papel, candidatos in (
                ("titular_coberto", titulares),
                ("titular_descoberto", titulares),
                ("sequencia", comissionados),
                ("fora_do_ar", comissionados),
                ("futuro", comissionados),
                ("exonerado", perfis),
            )
        }
        substitutos = iter([p for p in perfis if p not in escalados])
        self._exonerar(papeis["exonerado"])
        return sum(
            (
                self._afastar_coberto(papeis["titular_coberto"], substitutos, tipos),
                self._afastar_descoberto(papeis["titular_descoberto"], tipos),
                self._afastar_em_sequencia(papeis["sequencia"], substitutos, tipos),
                self._afastar_fora_do_ar(papeis["fora_do_ar"], substitutos, tipos),
                self._marcar_afastamento_futuro(papeis["futuro"], substitutos, tipos),
            )
        )

    def _escalar(
        self,
        candidatos: list[Perfil],
        escalados: list[Perfil],
    ) -> Perfil | None:
        # Sem candidato livre o papel simplesmente não é encenado: o andaime roda com o catálogo
        # que houver, e uma unidade só não produz titular nenhum.
        livre = next((c for c in candidatos if c not in escalados), None)
        if livre is not None:
            escalados.append(livre)
        return livre

    def _afastar_coberto(
        self,
        perfil: Perfil | None,
        substitutos: Iterator[Perfil],
        tipos: list[TipoImpedimento],
    ) -> int:
        substituto = next(substitutos, None)
        if perfil is None or substituto is None:
            return 0
        inicio = timezone.localdate() - timedelta(days=DIAS_DESDE_O_INICIO)
        impedimento = self._impedir(perfil, tipos[0], inicio, None)
        self._designar(impedimento, substituto)
        return 1

    def _afastar_descoberto(
        self,
        perfil: Perfil | None,
        tipos: list[TipoImpedimento],
    ) -> int:
        # Titular afastado e ninguém cobrindo: é o alarme de unidade sem direção (SPEC 016).
        if perfil is None:
            return 0
        inicio = timezone.localdate() - timedelta(days=DIAS_DESDE_O_INICIO)
        self._impedir(perfil, tipos[0], inicio, None)
        return 1

    def _afastar_em_sequencia(
        self,
        perfil: Perfil | None,
        substitutos: Iterator[Perfil],
        tipos: list[TipoImpedimento],
    ) -> int:
        """Uma encerrada, uma vigente e uma por vir — é deste cartão que sai o histórico."""
        elenco = [next(substitutos, None) for _ in range(3)]
        if perfil is None or any(s is None for s in elenco):
            return 0
        hoje = timezone.localdate()
        impedimento = self._impedir(
            perfil,
            tipos[-1],
            hoje - timedelta(days=DIAS_AFASTAMENTO_LONGO),
            hoje + timedelta(days=DIAS_AFASTAMENTO_LONGO),
        )
        self._designar(
            impedimento,
            elenco[0],
            hoje - timedelta(days=DIAS_AFASTAMENTO_LONGO),
            hoje - timedelta(days=DIAS_COBERTURA_ENCERRADA),
        )
        self._designar(
            impedimento,
            elenco[1],
            hoje - timedelta(days=DIAS_COBERTURA_ENCERRADA - 1),
            hoje + timedelta(days=DIAS_COBERTURA_VIGENTE),
        )
        self._designar(
            impedimento,
            elenco[2],
            hoje + timedelta(days=DIAS_COBERTURA_VIGENTE + 1),
            hoje + timedelta(days=DIAS_AFASTAMENTO_LONGO),
        )
        return 1

    def _afastar_fora_do_ar(
        self,
        perfil: Perfil | None,
        substitutos: Iterator[Perfil],
        tipos: list[TipoImpedimento],
    ) -> int:
        """A cobertura existe, gravada, e terminou antes do afastamento: hoje ninguém responde."""
        substituto = next(substitutos, None)
        if perfil is None or substituto is None:
            return 0
        hoje = timezone.localdate()
        impedimento = self._impedir(
            perfil,
            tipos[0],
            hoje - timedelta(days=DIAS_AFASTAMENTO_LONGO),
            hoje + timedelta(days=DIAS_AFASTAMENTO_LONGO),
        )
        self._designar(
            impedimento,
            substituto,
            hoje - timedelta(days=DIAS_AFASTAMENTO_LONGO),
            hoje - timedelta(days=DIAS_COBERTURA_ENCERRADA),
        )
        return 1

    def _marcar_afastamento_futuro(
        self,
        perfil: Perfil | None,
        substitutos: Iterator[Perfil],
        tipos: list[TipoImpedimento],
    ) -> int:
        """Designar antes de o afastamento começar: a pessoa segue na cadeira até a data chegar."""
        substituto = next(substitutos, None)
        if perfil is None or substituto is None:
            return 0
        hoje = timezone.localdate()
        impedimento = self._impedir(
            perfil,
            tipos[-1],
            hoje + timedelta(days=DIAS_ATE_O_AFASTAMENTO_FUTURO),
            hoje + timedelta(days=DIAS_DO_AFASTAMENTO_FUTURO),
        )
        self._designar(impedimento, substituto)
        return 1

    def _exonerar(self, perfil: Perfil | None) -> None:
        if perfil is None:
            return
        perfil.is_active = False
        perfil.save(update_fields=["is_active"])

    def _impedir(
        self,
        perfil: Perfil,
        tipo: TipoImpedimento,
        inicio: date,
        fim: date | None,
    ) -> Impedimento:
        # Pela mesma porta da tela: quando a criação passar a validar e registrar o ato (épico
        # autorizacao), o andaime não pode ser o caminho que escapa.
        return registrar_impedimento(
            perfil,
            NovoImpedimento(tipo=tipo.pk, data_inicio=inicio, data_fim=fim),
        )

    def _designar(
        self,
        impedimento: Impedimento,
        substituto: Perfil | None,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> None:
        if substituto is None:
            return
        designar_substituto(
            impedimento,
            NovaSubstituicao(substituto=substituto.pk, data_inicio=inicio, data_fim=fim),
        )

    def _titularizar(
        self,
        perfis: list[Perfil],
        cargos_comissao: list[CargoComissao],
    ) -> list[Perfil]:
        # Uma unidade elegível fica de fora: a vaga é o estado que a tela da SPEC 016 acusa.
        titulaveis = self._um_por_unidade(perfis)[:-UNIDADES_SEM_TITULAR]
        titularizados = []
        for perfil in titulaveis:
            cargo = self._cargo_que_titulariza(perfil.unidade, cargos_comissao)
            if cargo is None:
                continue
            # O cargo vem do porte da unidade, não do rodízio: senão o clean recusaria a marca.
            perfil.cargo_comissao = cargo
            perfil.save(update_fields=["cargo_comissao"])
            definir_titular(perfil)
            titularizados.append(perfil)
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
        # Os impedimentos saem primeiro: a substituição protege o substituto (PROTECT), e apagar a
        # pessoa antes do vínculo esbarraria nela mesma cobrindo outro fictício.
        Impedimento.objects.filter(perfil__in=ficticios).delete()
        ficticios.delete()
    return RemocaoFicticios(removidos=removidos)
