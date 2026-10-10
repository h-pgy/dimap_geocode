---
spec: documentos_oficiais/005
versao: v1
atualizado_em: 2026-09-07
testes_tdd: true
implementado: true
markers_obrigatorios: [artefato]
changelog:
  - v1: versão inicial
---

# SPEC documentos_oficiais/005 — Marcas lado a lado e moldura

## 1 · User story
**Requisito não-funcional** — o motor reparte uma faixa entre marcas ombro a ombro e traça contorno,
sem que o papel timbrado escreva a repartição à mão.

## 2 · Condições de pronto
- [ ] Marcas agrupadas lado a lado ocupam **uma faixa só**, cuja altura é a da mais alta — nunca a
      soma delas.
- [ ] A marca declara sua largura em milímetros; a que **não** declara recebe o que sobra da faixa,
      descontadas as declaradas e os respiros entre elas.
- [ ] Grupo com **mais de uma** marca sem largura declarada é recusado na construção, e grupo vazio
      também.
- [ ] Larguras declaradas que não cabem na faixa são recusadas ao pintar, **dizendo quanto falta** —
      em vez de saírem sobrepostas no papel.
- [ ] A folha traça **retângulo de contorno** em milímetros, com cor e espessura declaradas, no mesmo
      eixo das demais primitivas: `y` medido do alto.
- [ ] O papel timbrado atual sai **inalterado**: mesmo pé, mesmas margens, mesmo conteúdo em toda
      página.

## 3 · Domínio
Esta SPEC não introduz domínio: ela amplia o vocabulário do motor da SPEC
[documentos_oficiais/001](001-motor-de-pdf.md), que hoje só sabe empilhar marcas verticalmente
(`MarcasEmpilhadas`, SPEC [documentos_oficiais/004](004-qr-code.md)). A pergunta que ela faz ao motor
é como duas marcas de larguras diferentes dividem **a mesma** faixa, e como se traça o retângulo que
as cerca.

## 4 · Fora de escopo
- Alinhamento declarativo de marca estreita dentro da própria faixa, sem grupo ao lado — sem dono ainda.
- Marca posicionada por coordenada livre, fora de faixa, pintada **sobre** o corpo — sem dono ainda.
- `RodapeComQr` passar a compor o grupo lado a lado em vez da repartição própria — sem dono ainda.
- Preenchimento de fundo do retângulo, e cantos arredondados — sem dono ainda.
- Alinhamento vertical dentro do grupo: as marcas encostam no topo da faixa — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/pdf/marcacao.py` → `MarcasEmpilhadas`: o compositor vertical, cujo espelho
  horizontal é o desta SPEC.
- `@services/utils/pdf/marcacao.py` → `Marcacao._faixas`: quem recorta a faixa de cada marca.
- `@services/utils/pdf/folha.py` → `Folha`: a página sendo pintada e a inversão do eixo `y`.
- `@services/utils/pdf/models/pagina.py` → `Faixa`: o retângulo que pertence a uma marca.
- `@services/utils/pdf/models/texto.py` → `EstiloTexto`: a forma de um estilo do motor, que o traço
  espelha.
- `@services/domain/documento_oficial/marcas.py` → `RodapeComQr`: a repartição horizontal escrita à
  mão que esta SPEC generaliza.
- `@tests/conftest.py` → `publicar_artefato`: grava o artefato fora do repositório e imprime o caminho.
- Skills: `escrever-testes`, `documento-oficial`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/utils/pdf/marcacao.py`** — a `Marca` inteira, com o campo novo, e o compositor horizontal
ao lado do vertical.
```python
class Marca(ABC):
    """O que se pinta em toda página, fora do fluxo do corpo."""

    posicao: Posicao
    altura_mm: float
    # ALTERADO nesta SPEC: campo novo. `None` é "a faixa inteira", que é o que toda marca recebia
    # antes de existir grupo horizontal — por isso o default preserva o comportamento atual.
    largura_mm: float | None = None

    @abstractmethod
    def __call__(self, faixa: Faixa, folha: Folha) -> None: ...


class MarcasLadoALado(Marca):
    """Marcas ombro a ombro dentro de UMA faixa, na ordem declarada, encostadas no topo dela. O
    espelho horizontal de `MarcasEmpilhadas`: soltas na `Marcacao`, cada uma reservaria a sua faixa
    e o pé comeria a página."""

    def __init__(self, marcas: tuple[Marca, ...], posicao: Posicao, respiro_mm: float) -> None:
        if not marcas:
            raise ValueError("Grupo lado a lado precisa de ao menos uma marca.")
        # Duas marcas elásticas não têm repartição definida: quem sobra é UMA, e a recusa acontece
        # na construção do papel timbrado, não na página impressa.
        elasticas = sum(1 for marca in marcas if marca.largura_mm is None)
        if elasticas > 1:
            raise ValueError(
                f"{elasticas} marcas sem largura declarada no mesmo grupo: no máximo uma recebe a sobra."
            )
        self._marcas = marcas
        self._respiro_mm = respiro_mm
        self.posicao = posicao
        # A MAIS ALTA, não a soma: é isso que faz o grupo custar uma faixa em vez de N.
        self.altura_mm = max(marca.altura_mm for marca in marcas)

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        esquerda = faixa.esquerda_mm
        for marca, largura in self._repartir(faixa):
            marca(self._faixa_da(faixa, esquerda, largura, marca), folha)
            esquerda += largura + self._respiro_mm

    def _repartir(self, faixa: Faixa) -> tuple[tuple[Marca, float], ...]:
        respiros = self._respiro_mm * (len(self._marcas) - 1)
        declarada = sum(marca.largura_mm or 0.0 for marca in self._marcas)
        sobra = faixa.largura_mm - declarada - respiros
        # Recusar aqui, e não deixar passar: largura negativa sairia como marcas sobrepostas, que é
        # um defeito que só aparece no papel e depois de impresso.
        if sobra < 0:
            raise ValueError(
                f"As marcas do grupo pedem {declarada + respiros:.1f} mm numa faixa de "
                f"{faixa.largura_mm:.1f} mm: faltam {-sobra:.1f} mm."
            )
        return tuple(
            (marca, sobra if marca.largura_mm is None else marca.largura_mm)
            for marca in self._marcas
        )

    def _faixa_da(self, faixa: Faixa, esquerda_mm: float, largura_mm: float, marca: Marca) -> Faixa:
        # A altura é a da MARCA, não a do grupo: o que é mais baixo que o vizinho encosta no topo da
        # faixa, e não flutua no meio dela.
        return faixa.model_copy(
            update={
                "esquerda_mm": esquerda_mm,
                "largura_mm": largura_mm,
                "altura_mm": marca.altura_mm,
            }
        )
```

**`services/utils/pdf/models/traco.py`** — o estilo do contorno, espelhando `EstiloTexto`: o que a
`Folha` precisa para traçar, vindo de quem chama.
```python
class EstiloTraco(BaseModel):
    """O que a `Folha` precisa para traçar uma linha fechada. Sem preenchimento: o selo cerca o que
    está dentro dele, não pinta por cima."""

    # `Color` é do reportlab e não tem schema Pydantic — ver Caveats da SPEC documentos_oficiais/001.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    cor: Color
    espessura_mm: float
```

**`services/utils/pdf/folha.py`** — a primitiva nova, ao lado de `texto` e `vetor`, com a mesma
convenção de eixo das duas.
```python
    def retangulo(
        self,
        x_mm: float,
        y_mm: float,
        largura_mm: float,
        altura_mm: float,
        estilo: EstiloTraco,
    ) -> None:
        self._canvas.setStrokeColor(estilo.cor)
        self._canvas.setLineWidth(estilo.espessura_mm * mm)
        # `y_mm` é o TOPO, como em `texto` e `vetor`; o reportlab recebe o canto inferior, e a altura
        # entra na conta uma vez só, aqui.
        self._canvas.rect(
            x_mm * mm,
            self._y(y_mm) - altura_mm * mm,
            largura_mm * mm,
            altura_mm * mm,
            stroke=1,
            fill=0,
        )
```

**`services/utils/pdf/models/__init__.py`** e **`services/utils/pdf/__init__.py`** — passam a
reexportar o estilo de traço e o compositor horizontal, como já fazem com os demais.
```python
from .marcacao import MarcasLadoALado
from .models import EstiloTraco
```

## 7 · Caveats
`Marca` ganha `largura_mm` no ABC, alterando peça entregue pela SPEC 001. É o que permite ao grupo
repartir a faixa sem perguntar a cada marca o que ela é, e o default `None` preserva o comportamento
de toda marca existente. O custo é que a assinatura descrita na SPEC 001 deixa de ser a vigente, e
duas marcas hoje declaram `largura_mm` como atributo de instância, que passa a sobrescrever o do ABC.

`RodapeComQr` continua com a repartição horizontal própria, agora duplicada pelo compositor genérico.
Reescrevê-lo tocaria peça implementada e o pé de todo documento já emitido, sem entregar nada de novo.
O custo é haver duas formas de pôr marcas lado a lado, e quem ler `marcas.py` primeiro encontrará a
específica.

A recusa por largura que não cabe acontece **ao pintar**, e não na construção: a largura da faixa vem
do tamanho da página, que a marca só conhece na hora. O custo é que um papel timbrado mal dimensionado
só falha quando alguém emite um documento, e não quando o compõe.

## 8 · Testes (TDD)
- `test_grupo_lado_a_lado_ocupa_uma_faixa_com_a_altura_da_mais_alta` — três marcas de alturas
  diferentes num grupo reservam a altura da maior, e não a soma; a margem inferior da página reflete
  isso.
- `test_marca_sem_largura_recebe_a_sobra_da_faixa` — a elástica recebe a faixa menos as declaradas e
  menos os respiros; as declaradas recebem exatamente o que pediram.
- `test_grupo_reparte_da_esquerda_para_a_direita_com_respiro` — a segunda marca começa onde a
  primeira termina, mais o respiro, e a última encosta na borda direita da faixa.
- `test_grupo_com_duas_elasticas_ou_vazio_eh_recusado` — dois `largura_mm=None` levantam na
  construção, e tupla vazia também.
- `test_larguras_que_nao_cabem_sao_recusadas_dizendo_quanto_falta` — faixa menor que a soma levanta
  ao pintar, com o número de milímetros faltantes na mensagem.
- `test_marcas_do_grupo_encostam_no_topo_da_faixa` — a mais baixa recebe faixa de altura própria com
  o mesmo `topo_mm` da mais alta.
- `test_retangulo_traca_no_eixo_do_topo_com_espessura_declarada` — o contorno sai no `y` medido do
  alto da folha, com a espessura pedida e sem preenchimento.
- `test_papel_timbrado_atual_permanece_identico` — a marcação `fazenda_dimap` produz as mesmas
  margens e o mesmo número de faixas de antes da mudança do ABC.
- `test_amostra_com_grupo_lado_a_lado_e_moldura` — grava o PDF de conferência com um grupo de três
  marcas cercado por moldura e imprime o caminho. *(marker `artefato`)*
