---
spec: user_admin/019
versao: v2
atualizado_em: 2026-08-18
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v2: navegação a partir de unidade selecionada via query param '?foco=<pk>' pré-renderizando nó ativo e linha em destaque no topo
  - v1: versão inicial implementada
---

# SPEC user_admin/019 — Lista de unidades com organograma integrado

## 1 · User story
O servidor da DIMAP consulta e filtra as unidades da Secretaria na tabela com o organograma visual integrado para localizar rapidamente a posição hierárquica, o titular e as relações de subordinação de qualquer unidade.

## 2 · Condições de pronto
- [x] A rota `/gestao/unidades/` exibe a **página de unidades** contendo o organograma hierárquico no topo e a tabela de unidades filtrável e ordenável no poço inferior.
- [x] A rota `/gestao/unidades/arvore/` redireciona para `/gestao/unidades/`, e o botão "Organograma inteiro" na página de detalhes da unidade aponta para a nova listagem com parâmetro `?foco={{ unidade.pk }}`.
- [x] Ao acessar `/gestao/unidades/?foco=<pk>`, o organograma nasce com o nó correspondente marcado como `ego` (com caminho aberto até o topo) e a linha da respectiva unidade é colocada na 1ª posição da tabela com destaque ativo ciano (`data-ativo="true"`).
- [x] A tabela exibe as colunas na ordem exata: **Sigla**, **Nome da unidade**, **Tipo**, **Alta administração**, **Cor**, **Titular**, **Unidade pai** e **Ações**.
- [x] O texto do **Nome da unidade** quebra linha na célula (`break-words`) para preservar a largura compacta da tabela.
- [x] As colunas **Sigla**, **Nome**, **Tipo**, **Titular** e **Unidade pai** filtram por texto com normalização canônica (sem diferenciar acentos ou maiúsculas) e ordenam de forma ascendente e descendente.
- [x] As colunas **Sigla** e **Unidade pai** contêm links para a página da respectiva unidade; a coluna **Titular** contém link para a página de perfil do servidor titular quando houver.
- [x] O corpo da tabela atualiza via HTMX em `/gestao/unidades/corpo/` conforme filtros ou ordenação mudam, sem reconstruir o cabeçalho nem o organograma.
- [x] **Clicar no corpo de uma linha da tabela** (fora de links diretos) ativa o nó correspondente na árvore superior via `moverEgo` (abrindo o caminho até o topo) e rola suavemente a árvore até o nó.
- [x] **Clicar em um nó do organograma** move a linha correspondente para a primeira posição da tabela, aplica o destaque ciano ativo e rola a tabela até o topo.
- [x] O design foi aprovado no **mock**, e as peças novas foram portadas para `static/src/tema-dimap.dev.css` e renderizadas no styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
A listagem de unidades consome a hierarquia já modelada em `Unidade` ([user_admin/003](003-hierarquia-unidades.md)), a cor de identidade ([user_admin/005](005-cor-da-unidade.md)), a titularidade ([user_admin/014](014-titular-da-unidade.md)) e a árvore hierárquica ([user_admin/018](018-arvore-hierarquica.md)).

O motor de filtragem e ordenação em memória passa a ser unificado no domínio `services/domain/listagem_gestao/`, servindo com o mesmo algoritmo genérico as listagens de servidores e unidades a partir de DTOs tipados.

**`services/domain/listagem_gestao/models/consulta.py`**
```python
from collections.abc import Mapping
from enum import StrEnum
from typing import Generic, Self, TypeVar
from pydantic import BaseModel

ColunaT = TypeVar("ColunaT", bound=StrEnum)


class FiltroColuna(BaseModel, Generic[ColunaT]):
    """Um filtro textual ativo aplicado a uma coluna específica."""
    coluna: ColunaT
    termo: str


class ConsultaListagem(BaseModel, Generic[ColunaT]):
    """Consulta estruturada com filtros cumulativos e ordenação opcional."""
    filtros: list[FiltroColuna[ColunaT]] = []
    ordenar_por: ColunaT | None = None
    descendente: bool = False

    @classmethod
    def de_parametros(
        cls,
        parametros: Mapping[str, str],
        enum_coluna: type[ColunaT],
    ) -> Self:
        """Constrói o DTO de consulta a partir do dicionário plano da query string."""
        filtros = [
            FiltroColuna[ColunaT](coluna=coluna, termo=parametros[coluna.value])
            for coluna in enum_coluna
            if parametros.get(coluna.value, "").strip()
        ]
        return cls.model_validate(
            {
                "filtros": filtros,
                "ordenar_por": parametros.get("ordenar_por") or None,
                "descendente": parametros.get("descendente") in ("1", "true", "True", True),
            }
        )
```

**`services/domain/listagem_gestao/models/servidores.py`**
```python
from enum import StrEnum
from pydantic import BaseModel
from services.domain.listagem_gestao.models.consulta import ConsultaListagem


class ColunaServidor(StrEnum):
    NOME = "nome"
    RF = "rf"
    UNIDADE = "unidade"
    CARGO = "cargo"
    COMISSAO = "comissao"


class LinhaServidor(BaseModel):
    pk: int
    nome: str
    rf: str
    unidade: str
    unidade_pk: int
    cor_unidade: str
    cargo: str
    comissao: str
    impedido: bool


ConsultaServidores = ConsultaListagem[ColunaServidor]
```

**`services/domain/listagem_gestao/models/unidades.py`**
```python
from enum import StrEnum
from pydantic import BaseModel
from services.domain.listagem_gestao.models.consulta import ConsultaListagem


class ColunaUnidade(StrEnum):
    SIGLA = "sigla"
    NOME = "nome"
    TIPO = "tipo"
    TITULAR = "titular"
    PAI = "pai"


class LinhaUnidade(BaseModel):
    """Uma linha já materializada da tabela de unidades."""
    pk: int
    sigla: str
    nome: str
    tipo: str
    exige_alta_administracao: bool
    cor_hex: str
    titular_pk: int | None = None
    titular_nome: str | None = None
    pai_pk: int | None = None
    pai_sigla: str | None = None


ConsultaUnidades = ConsultaListagem[ColunaUnidade]
```

**`services/domain/listagem_gestao/models/__init__.py`**
```python
from .consulta import ColunaT, ConsultaListagem, FiltroColuna
from .servidores import ColunaServidor, ConsultaServidores, LinhaServidor
from .unidades import ColunaUnidade, ConsultaUnidades, LinhaUnidade

__all__ = [
    "ColunaT",
    "FiltroColuna",
    "ConsultaListagem",
    "ColunaServidor",
    "LinhaServidor",
    "ConsultaServidores",
    "ColunaUnidade",
    "LinhaUnidade",
    "ConsultaUnidades",
]
```

**Mock:** [019-mock-lista-de-unidades.html](019-mock-lista-de-unidades.html) (Aprovado).

### Tokens de Design System adicionados
- `.td-nome-unidade`: Quebra de linha responsiva (`break-words`) com cor suave de texto sobre a placa.
- `.link-tabela-onsen`: Tipografia destacada em madeira (`font-medium text-madeira-700`) e micro-interação de afordância no hover (`scale-[1.06] hover:text-agua-700`), padronizada para sigla, titular e unidades relacionadas.

## 4 · Fora de escopo
- Edição ou criação inline de unidades na própria tabela — [user_admin/012](012-design-formulario-unidade.md) (modal de unidade).
- Paginação no banco de dados para unidades — sem dono ainda (o volume da Secretaria cabe com folga em memória).

## 5 · Peças de referência a compor
- `@services/utils/normalization` → `normalize_text`: normalização única para casamento textual sem acentos nem caixa.
- `@services/domain/arvore_hierarquica` → `NoHierarquia` e `posicao_de`: cálculo de nós e ramos do organograma.
- `@templates/user_admin/partials/_no_arvore.html` → partial recursivo do nó do organograma (reusado sem duplicação).
- `@apps/user_admin/paleta` → `hex_da_cor`: conversão do slug da cor da unidade em código hex.
- `@static/src/js/ui/arvore_hierarquica.js` → `moverEgo`: ativação e percurso de nós no organograma DOM.
- `@static/src/js/ui/tabela_onsen.js` → `montarTabelasOnsen`: controle de ordenação e limpeza de filtros.
- Skills: `componentes-frontend`, `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

**`services/domain/listagem_gestao/listagem.py`**
```python
from collections.abc import Sequence
from typing import Generic, TypeVar
from pydantic import BaseModel
from services.domain.listagem_gestao.models import (
    ColunaServidor,
    ColunaUnidade,
    ConsultaListagem,
    ConsultaServidores,
    ConsultaUnidades,
    FiltroColuna,
    LinhaServidor,
    LinhaUnidade,
)
from services.utils.normalization import normalize_text

LinhaT = TypeVar("LinhaT", bound=BaseModel)
ColunaT = TypeVar("ColunaT")


class ListadorTabela(Generic[LinhaT, ColunaT]):
    """Filtra e ordena linhas em memória usando a normalização canônica do sistema."""

    def __call__(
        self,
        linhas: Sequence[LinhaT],
        consulta: ConsultaListagem[ColunaT],
    ) -> list[LinhaT]:
        return self.pipeline(linhas, consulta)

    def pipeline(
        self,
        linhas: Sequence[LinhaT],
        consulta: ConsultaListagem[ColunaT],
    ) -> list[LinhaT]:
        filtradas = self._filtrar(linhas, consulta.filtros)
        return self._ordenar(filtradas, consulta.ordenar_por, consulta.descendente)

    def _filtrar(
        self,
        linhas: Sequence[LinhaT],
        filtros: list[FiltroColuna[ColunaT]],
    ) -> list[LinhaT]:
        return [
            linha
            for linha in linhas
            if all(self._atende(linha, filtro) for filtro in filtros)
        ]

    def _atende(self, linha: LinhaT, filtro: FiltroColuna[ColunaT]) -> bool:
        termo_normalizado = normalize_text(filtro.termo)
        chave_normalizada = self._chave(linha, filtro.coluna)
        return termo_normalizado in chave_normalizada

    def _ordenar(
        self,
        linhas: list[LinhaT],
        coluna: ColunaT | None,
        descendente: bool,
    ) -> list[LinhaT]:
        if coluna is None:
            return linhas
        return sorted(
            linhas,
            key=lambda linha: self._chave(linha, coluna),
            reverse=descendente,
        )

    def _chave(self, linha: LinhaT, coluna: ColunaT) -> str:
        campo = getattr(coluna, "value", str(coluna))
        valor = getattr(linha, campo, "")
        return normalize_text(str(valor or ""))


listar_servidores = ListadorTabela[LinhaServidor, ColunaServidor]()
listar_unidades = ListadorTabela[LinhaUnidade, ColunaUnidade]()
```

**`apps/user_admin/context.py`**
```python
from typing import Any
from apps.mapping.context import contexto_fundo_admin
from apps.user_admin.context import contexto_organograma
from apps.user_admin.models import Unidade
from apps.user_admin.paleta import hex_da_cor
from services.domain.listagem_gestao import (
    ColunaUnidade,
    ConsultaUnidades,
    LinhaUnidade,
    listar_unidades,
)

ROTULO_COLUNAS_UNIDADE = {
    ColunaUnidade.SIGLA: "Sigla",
    ColunaUnidade.NOME: "Unidade",
    ColunaUnidade.TIPO: "Tipo",
    ColunaUnidade.TITULAR: "Titular",
    ColunaUnidade.PAI: "Subordinação",
}


def contexto_listagem_unidades(consulta: ConsultaUnidades) -> dict[str, Any]:
    """Contexto completo da página: fundo, organograma no topo, tabela e ordenação."""
    return (
        contexto_fundo_admin()
        | contexto_organograma(None)
        | contexto_corpo_unidades(consulta)
        | {
            "colunas": _colunas_unidade(consulta),
            "ordenar_por": consulta.ordenar_por or "",
            "descendente": "1" if consulta.descendente else "0",
        }
    )


def contexto_corpo_unidades(consulta: ConsultaUnidades) -> dict[str, Any]:
    """Contexto exclusivo para o swap HTMX do tbody da tabela de unidades."""
    linhas = _linhas_de_unidades()
    return {
        "linhas": listar_unidades(linhas, consulta),
        "total_unidades": len(linhas),
    }


def _linhas_de_unidades() -> list[LinhaUnidade]:
    """Materializa as unidades do banco em DTOs com titularidade resolvida."""
    unidades = Unidade.objects.select_related("tipo", "pai").prefetch_related("perfis")
    linhas: list[LinhaUnidade] = []
    for unidade in unidades:
        titular = unidade.titular
        linhas.append(
            LinhaUnidade(
                pk=unidade.pk,
                sigla=unidade.sigla,
                nome=unidade.nome,
                tipo=unidade.tipo.nome,
                exige_alta_administracao=unidade.tipo.exige_alta_administracao,
                cor_hex=hex_da_cor(unidade.cor),
                titular_pk=titular.pk if titular else None,
                titular_nome=titular.nome if titular else None,
                pai_pk=unidade.pai.pk if unidade.pai else None,
                pai_sigla=unidade.pai.sigla if unidade.pai else None,
            )
        )
    return linhas
```

**`apps/user_admin/views.py`**
```python
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from apps.user_admin.context import (
    contexto_corpo_unidades,
    contexto_listagem_unidades,
)
from services.domain.listagem_gestao import ColunaUnidade, ConsultaUnidades

TEMPLATE_LISTAGEM_UNIDADES = "user_admin/unidades_list.html"
TEMPLATE_CORPO_UNIDADES = "user_admin/partials/_corpo_unidades.html"


def listar_unidades(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaUnidades.de_parametros(request.GET.dict(), ColunaUnidade)
    return render(request, TEMPLATE_LISTAGEM_UNIDADES, contexto_listagem_unidades(consulta))


def corpo_unidades(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaUnidades.de_parametros(request.GET.dict(), ColunaUnidade)
    return render(request, TEMPLATE_CORPO_UNIDADES, contexto_corpo_unidades(consulta))


def redirecionar_arvore_unidades(request: HttpRequest) -> HttpResponse:
    return redirect("user_admin:listar_unidades")
```

## 7 · Caveats
Duas fontes de navegação sobre a mesma base de unidades coexistem na mesma tela (a árvore e a tabela). A complementaridade entre a visão estrutural e a busca tabular é o valor central da tela. O JavaScript de interface coordena a sincronia de nós e linhas no DOM sem disparar requisições ao servidor.

A rota `/gestao/unidades/arvore/` é redirecionada para `/gestao/unidades/`. A visualização isolada deixa de existir ao ser incorporada no topo da listagem completa. Clientes que requisitarem a URL anterior recebem um redirect 302.

## 8 · Testes (TDD)
- `test_filtrar_unidades_por_sigla_normalizada` — filtro encontra sigla independente de acentuação ou caixa alta.
- `test_filtrar_unidades_por_tipo_e_titular` — múltiplos filtros combinados aplicam regra cumulativa (AND).
- `test_ordenar_unidades_descendente` — ordenação alfabética reversa preserva a normalização correta.
- `test_consulta_de_unidades_com_coluna_invalida` — schema rejeita parâmetro de coluna desconhecida gerando `ValidationError`.
- `test_view_listar_unidades_renderiza_arvore_e_tabela` — rota `/gestao/unidades/` devolve status 200 com contexto de ramos e linhas *(marker `banco`)*.
- `test_view_corpo_unidades_devolve_tbody_filtrado` — rota parcial `/gestao/unidades/corpo/` devolve status 200 com fragmento HTML *(marker `banco`)*.
- `test_view_arvore_antiga_redireciona_para_listagem` — rota `/gestao/unidades/arvore/` responde com status 302 para `user_admin:listar_unidades` *(marker `banco`)*.
