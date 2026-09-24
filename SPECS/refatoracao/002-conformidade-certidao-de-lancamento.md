---
spec: refatoracao/002
versao: v2
atualizado_em: 2026-09-23
testes_tdd: true
implementado: true
markers_obrigatorios: [banco, artefato]
changelog:
  - v1: versão inicial
  - v2: tarja de recusa ganha tom, e a amostra de conferência passa a sair do pipeline real
---

# SPEC refatoracao/002 — Conformidade da Certidão de Existência de Lançamento

## 1 · User story
**Refatoração** — a certidão de lançamento e a planta de localização passam a compor com as peças que
já existem, e o que hoje falha em silêncio passa a recusar.

## 2 · Condições de pronto
- [x] O cabeçalho do modal exibe o endereço do lote.
- [x] Processo e interessado inválidos no mesmo envio devolvem **as duas** mensagens, com **os dois**
      campos realçados.
- [x] Ortofoto indisponível **recusa a emissão**: o modal volta com o aviso e nada entra no acervo.
- [x] `CertidaoLancamentoInput` recusa planta que não seja uma `PlantaLocalizacao`.
- [x] O rodapé da certidão declara que ela foi emitida **de forma automatizada**, com o instante da
      consulta cadastral.
- [x] Os templates da certidão não desenham SVG próprio: o alerta vem da tarja de recusa e os ícones,
      do sprite de glifos.
- [x] Lote que não admite certidão aparece em **âmbar** (estado que não vale hoje), e ato que falhou,
      em **vermelho** — a mesma leitura de cor do resto do sistema.
- [x] A amostra de conferência traz a planta **gerada pelo pipeline real**, com o lote em destaque e
      os vizinhos em contexto sobre a ortofoto.

## 3 · Domínio
A ontologia não muda. Esta SPEC pergunta ao
[CertidaoLancamentoInput](../certidao_lancamento/001-certidao-de-um-lote.md#3--domínio) que a planta
seja tipada de verdade, e à [planta](../documentos_oficiais/011-planta-de-localizacao.md) que o erro
do WMS chegue a quem emite.

O desfecho da emissão ganha o envelope que o resto do projeto já usa para separar o que saiu do que
foi recusado.

**`apps/certidao_lancamento/emissao.py`**

```python
class DesfechoEmissao(BaseModel):
    """Ou o documento, ou a recusa — o mesmo contrato de `DesfechoUnidade` e `DesfechoCargo`."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    documento: DocumentoEmitido | None = None
    recusa: RecusaDeFormulario = RecusaDeFormulario()
```

## 4 · Fora de escopo
- Os testes da §8 da SPEC [documentos_oficiais/011](../documentos_oficiais/011-planta-de-localizacao.md)
  que não entram aqui — amostra sobre ortofoto real e o `integration` contra o GeoSampa — sem dono ainda.
- Cache da ortofoto entre emissões do mesmo lugar — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/geometry` → `para_geos`: GeoJSON do domínio vira `GEOSGeometry` com SRID.
- `@templates/partials/_tarja_recusa.html` → a tarja que lê `recusa.mensagens`.
- `@static/src/tema-dimap.dev.css` → `.tarja-vinculo-pendente` / `-critica`: os dois tons já no tema.
- `@services/utils/erros_formulario` → `RecusaDeFormulario.realce` / `.mensagens`.
- `@templates/documentos/partials/_glifos_documento.html` → `#glifo-selo`, `#glifo-baixar`.
- `@services/integrations/wms` → `WmsError`: a exceção que o domínio deixa subir.
- Skills: `erros-de-formulario`, `componentes-frontend`, `escrever-testes`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/planta_localizacao/planta.py`** — o enquadramento sai do GEOS, e o erro do WMS sobe.

```python
def pipeline(self, entrada: PlantaLocalizacaoInput) -> PlantaLocalizacao:
    enquadramento = self._enquadrar(entrada)
    # Sem try/except: certidão com planta falsa é pior que certidão não emitida.
    fundo = self._ortofoto(self._request(enquadramento, entrada.config))
    png = self._desenhar(fundo, enquadramento, entrada)
    return PlantaLocalizacao(png=png, enquadramento=enquadramento)


def _enquadrar(self, entrada: PlantaLocalizacaoInput) -> BoundingBox:
    # A extensão vem do GEOS, não de varrer anéis à mão (CLAUDE.md §7.2).
    uniao = reduce(
        operator.or_,
        (
            para_geos(geom, entrada.config.crs)
            for camada in entrada.camadas
            for geom in camada.geometrias
        ),
    )
    minx, miny, maxx, maxy = _com_folga(uniao.extent, entrada.config.folga_m)
    return _quadrado_centrado(minx, miny, maxx, maxy, f"EPSG:{entrada.config.crs}")
```

**`apps/certidao_lancamento/emissao.py`** — a orquestração traduz a falha do WMS em recusa.

```python
MOTIVO_SEM_ORTOFOTO = (
    "Não foi possível obter a imagem de localização do imóvel agora. Tente novamente em instantes."
)


def emitir_certidao_lancamento(...) -> DesfechoEmissao:
    try:
        planta = GerarPlantaLocalizacao(build_wms_fetcher(settings))(...)
    except WmsError:
        # A view não conhece WMS; ela lê o desfecho, como nas demais telas de formulário.
        return DesfechoEmissao(recusa=RecusaDeFormulario(gerais=(MOTIVO_SEM_ORTOFOTO,)))
    ...
    return DesfechoEmissao(documento=guardar_documento(selado, envelope, execucao=None))
```

**`apps/certidao_lancamento/views.py`** — a recusa inteira desce ao template; nada de `campos[0]`.

```python
@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_POST
def emitir(request: HttpRequest) -> HttpResponse:
    leitura = ler_pedido_certidao(request.POST)
    lote = ler_lote(request.POST.get("id", ""))
    if leitura.dto is None or lote is None or not lote.pode_certificar:
        return _modal_recusado(request, lote, request.POST, leitura.recusa)
    desfecho = emitir_certidao_lancamento(...)
    if desfecho.documento is None:
        return _modal_recusado(request, lote, request.POST, desfecho.recusa)
    registrar_ato(request, operacao="emitir", alvo_tipo="documento",
                  alvo_identificador=desfecho.documento.codigo)
    return render(request, TEMPLATE_CERTIDAO_EMITIDA, {"codigo": desfecho.documento.codigo})
```

**`templates/certidao_lancamento/_modal.html`** — a tarja e o realce já existem; o modal só os compõe.

```html
{% include "partials/_tarja_recusa.html" with erros=recusa.mensagens titulo="Não foi possível emitir a certidão" %}

<input type="text" name="processo" value="{{ valores.processo }}"
       data-mascara="0000.0000/0000000-0"
       class="input input-glass input-sm w-full font-mono {{ recusa.realce.processo }}">
```

## 7 · Caveats
Esta SPEC não tem mock. Nenhuma peça nova nasce aqui: a tarja de recusa, os dois tons de
`.tarja-vinculo` e os glifos do sprite já existem no tema, e o modal passa a compô-los no lugar de
marcação própria. O custo é que a troca do alerta pela tarja muda o desenho do modal sem passar por
aprovação visual.

`_tarja_recusa.html` passa a ler um `tom` opcional, e sem ele segue crítica. A molécula é usada por
vinte telas, e um irmão só para o âmbar duplicaria a marcação inteira. O custo é uma molécula
implementada alterada, ainda que nenhuma das vinte mude de saída.

`DesfechoEmissao` faz `emissao.py` capturar `WmsError`, que é exceção de integração. A alternativa
seria a view fazer `try/except`, vedado pelo §7.2 do CLAUDE.md. O custo é que a orquestração passa a
conhecer a exceção do WMS, como `apps/unidades/cadastro.py` já conhece as suas.

A SPEC [documentos_oficiais/011](../documentos_oficiais/011-planta-de-localizacao.md) vai a v2 nesta
entrega: passa a descrever a planta em Pillow e a §8 dela encolhe para os testes que existem de fato.
Sem isso o front-matter dela seguiria dizendo `implementado: false` sobre código já em produção. O
custo é uma SPEC de outro épico alterada por esta.

## 8 · Testes (TDD)
- `test_modal_mostra_endereco_do_lote` — o cabeçalho traz o logradouro e o número do lote lido
  *(marker `banco`)*.
- `test_formulario_com_dois_campos_invalidos_realca_os_dois` — processo fora do padrão **e**
  interessado em branco devolvem duas mensagens e dois `campo-realce-erro` *(marker `banco`)*.
- `test_emissao_recusa_quando_ortofoto_indisponivel` — `WmsError` no fetcher devolve 422 com o aviso,
  e nenhum `DocumentoEmitido` é gravado *(marker `banco`)*.
- `test_certidao_input_recusa_planta_de_outro_tipo` — `planta="qualquer coisa"` falha na construção.
- `test_planta_propaga_erro_do_wms` — o `WmsError` do fetcher atravessa `GerarPlantaLocalizacao`.
- `test_amostra_certidao_de_lancamento` — o PDF de conferência sai com a planta do pipeline real,
  destaque e contexto sobre a ortofoto *(marker `artefato`)*.
- `test_enquadramento_une_camadas_e_soma_folga` — duas camadas afastadas cabem inteiras, quadradas e
  centradas, com a folga a mais em cada lado.
- `test_rodape_declara_emissao_automatizada_e_instante_da_consulta` — o texto do PDF renderizado traz
  "de forma automatizada" e a data/hora de `consultado_em` *(marker `artefato`)*.
