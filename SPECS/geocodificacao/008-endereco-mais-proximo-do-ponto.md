---
spec: geocodificacao/008
versao: v5
atualizado_em: 2026-10-09
testes_tdd: true
implementado: true
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
  - v2: renumerada de 007 para 008 — o nome completo nas sugestões vem antes e passa a ser a 007.
  - v3: a faixa `0–0` conta como lado sem numeração, também na geocodificação da busca, e o `EnderecoAttributes` vigente passa a ser o da SPEC 006.
  - v4: o teste de integração marca o ponto na pista par da Av. Paulista em frente ao MASP, e não na calçada.
  - v5: com a gaveta inferior aberta ou recolhida, a consulta deixa de responder (SPEC design/021)
---

# SPEC geocodificacao/008 — Endereço mais próximo de um ponto desenhado

## 1 · User story
Quem usa o mapa marca um ponto desenhado e pede o endereço mais próximo dele, no contexto de um local
que conhece só pela posição no mapa, para chegar ao endereço oficial e às ações que partem dele.

## 2 · Condições de pronto
- [ ] Com um **ponto selecionado** na gaveta dos desenhos, o poço de pontos traz a ação **"Endereço
      mais próximo"**, depois de "Logradouro mais próximo", inclusive para quem não fez login.
- [ ] Acionar a ação desenha no mapa o **ponto do endereço**, sobre o eixo do logradouro, e troca a
      gaveta dos desenhos pela **gaveta do endereço da busca** — logradouro, codlog, número, faixa do
      segmento e o poço de ações dela. Vale o ponto como está no mapa naquele momento, inclusive
      depois de arrastado.
- [ ] O logradouro é o do **segmento com numeração mais próximo** do ponto, dentro do raio configurado;
      segmento sem numeração não concorre, mesmo sendo o mais perto.
- [ ] O **número** acompanha a posição do ponto ao longo do segmento, dentro da faixa do lado em que
      ele está, e tem a paridade desse lado; nunca é zero.
- [ ] O lado é **par à direita e ímpar à esquerda** de quem segue o logradouro no sentido em que a
      numeração cresce; o mesmo ponto, espelhado para o outro lado do eixo, troca a paridade e a
      faixa. Segmento com um lado só numerado devolve a paridade dele.
- [ ] O ponto do endereço é o que a geocodificação da busca dá para aquele número naquele segmento.
- [ ] Sem segmento com numeração no raio, o mapa fica como estava, o aviso do mapa diz isso em
      português, **citando o raio**, e a gaveta dos desenhos recolhe para o aviso ficar à vista.
- [ ] Desenho que não é ponto é recusado sem consultar o WFS.
- [ ] O design da ação no poço de pontos e do resultado no mapa foi aprovado no mock, e o ícone foi
      gravado antes de qualquer template da aplicação usá-lo.

## 3 · Domínio
O resultado é o [EnderecoFeature](003-address-geocod-ponto.md) da geocodificação, com os
[EnderecoAttributes](006-gaveta-do-logradouro.md#3--domínio) vigentes; a
pergunta desta SPEC a ele é a inversa da busca: "que endereço é este ponto?". Os candidatos são os
[SegmentoProximo](005-logradouro-mais-proximo-do-ponto.md#3--domínio) da SPEC 005, a quem se pergunta
"qual é o mais perto que tem numeração?".

**`services/domain/address_geocod/models.py`**

```python
class Lado(StrEnum):
    """De que lado do eixo o ponto está, para quem segue o segmento no sentido em que a numeração cresce."""

    DIREITA = "direita"
    ESQUERDA = "esquerda"


# A convenção de numeração do município: é ela que traduz lado em paridade.
PARIDADE_POR_LADO = {
    Lado.DIREITA: Paridade.PAR,
    Lado.ESQUERDA: Paridade.IMPAR,
}
```

**Mock:** [008-mock-endereco-mais-proximo-do-ponto.html](008-mock-endereco-mais-proximo-do-ponto.html)
— leia a skill `mock`.

## 4 · Fora de escopo
- Devolver o logradouro, sem número, quando o segmento mais próximo não tem numeração — é a consulta
  da SPEC [geocodificacao/005](005-logradouro-mais-proximo-do-ponto.md); oferecê-la como saída desta,
  sem dono ainda.
- Mostrar na gaveta de que lado do logradouro o ponto caiu — sem dono ainda.
- Refazer a consulta sozinha quando o ponto é arrastado depois dela — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/logradouro_geocod` → `SegmentosNoRaio`, `SegmentosNoRaioInput`, `SegmentoProximo` (SPEC 005): os segmentos perto do ponto, já ordenados e no CRS métrico.
- `@services/domain/logradouro_geocod` → `LogradouroGeocoder`: os segmentos do codlog, vizinhos do escolhido.
- `@services/domain/address_geocod/orientacao.py` → `SolverOrientacaoSegmento`: o segmento como linha GEOS, no sentido em que a numeração cresce.
- `@services/domain/address_geocod/interpolacao.py` → `InterpoladorSegmento`: o ponto de um número sobre o segmento, já no CRS de saída.
- `@services/domain/address_geocod/numeracao.py` → `Paridade`, `intervalo_numeracao`, `limite_inicial`, `limite_final`: a faixa de cada lado.
- `@services/domain/geometry` → `reprojetar`, `para_geos`: o ponto desenhado no CRS métrico.
- `@apps/address_geocoder/views.py` → `renderizar_endereco`: a resposta do endereço — payload do mapa e gaveta.
- `@apps/mapping` → `ConsultaSobrePonto` (SPEC 005), `ConsultaSobreDesenho`, `REGISTRO_DESENHO`, `contexto_aviso`, `_recusa_acao.html`.
- Skills: `acao-sobre-desenho`, `painel`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/address_geocod/numeracao.py`** — o predicado que o `AddressGeocoder` escreve inline
ganha nome, com a faixa `0–0` contada como lado vazio, e os dois callables o usam.

```python
def tem_numeracao(attrs: SegmentoLogradouroAttributes, paridade: Paridade) -> bool:
    inicial, final = intervalo_numeracao(attrs, paridade)
    # A camada marca o lado vazio com None ou com 0–0. A faixa par que começa em zero (0–42) é
    # numeração de verdade: o que denuncia o lado vazio é o final zero.
    return inicial is not None and final is not None and final > 0
```

**`services/domain/address_geocod/geocoder.py`** — a montagem da feature sai do método e vira função de
módulo: quem interpola e quem inverte a interpolação devolvem o mesmo endereço.

```python
def montar_endereco(
    ponto: Point,
    segmento: SegmentoLogradouroFeature,
    numero: int,
    paridade: Paridade,
    output_crs: int,
) -> EnderecoFeature:
    ...   # ALTERADO: o corpo de AddressGeocoder._montar_feature, sem mudança de regra
```

**`services/domain/address_geocod/lado.py`** — o lado é relativo ao segmento, não ao norte. O eixo é um
vetor que aponta para onde a numeração cresce; o ponto é outro vetor, saindo da mesma origem. O sinal
do produto vetorial dos dois diz para que lado o segundo gira em relação ao primeiro, qualquer que
seja a direção da rua no mapa.

```python
PASSO_M = 1.0   # meio comprimento do trecho do eixo que dá o sentido local


def lado_do_ponto(linha: LineString, ponto: Point) -> Lado:
    """`linha` já no sentido em que a numeração cresce; os dois no mesmo CRS métrico."""
    # O segmento tem vértices: o sentido que vale é o do trecho onde o ponto se projeta,
    # não o da corda entre as pontas.
    posicao = linha.project(ponto)                      # metros ao longo da linha até o pé da perpendicular
    posicao_antes = max(posicao - PASSO_M, 0.0)
    posicao_depois = min(posicao + PASSO_M, linha.length)
    antes = linha.interpolate(posicao_antes)
    depois = linha.interpolate(posicao_depois)
    eixo_x = depois.x - antes.x
    eixo_y = depois.y - antes.y
    ponto_x = ponto.x - antes.x
    ponto_y = ponto.y - antes.y
    # Positivo: do eixo ao ponto gira-se no sentido anti-horário — o ponto está à esquerda.
    giro = eixo_x * ponto_y - eixo_y * ponto_x
    return Lado.ESQUERDA if giro > 0 else Lado.DIREITA   # sobre o eixo (zero) conta como direita
```

**`services/domain/address_geocod/mais_proximo.py`**

```python
# Contrato da dependência injetada: o SegmentosNoRaio da SPEC 005 satisfaz esta assinatura.
SegmentosDoPonto = Callable[[SegmentosNoRaioInput], tuple[SegmentoProximo, ...]]


class EnderecoMaisProximoInput(BaseModel):
    consulta: SegmentosNoRaioInput   # o ponto, o raio e a camada: a mesma pergunta da SPEC 005
    output_crs: int


class NenhumSegmentoNumeradoNoRaioError(Exception):
    """Nenhum segmento com numeração dentro do raio consultado."""


class EnderecoMaisProximo:
    def __init__(
        self,
        segmentos_no_raio: SegmentosDoPonto,
        logradouro_geocoder: SegmentosDeCodlog,
    ) -> None:
        self._segmentos_no_raio = segmentos_no_raio
        self._segmentos = logradouro_geocoder
        self._corrigir_orientacao = SolverOrientacaoSegmento()
        self._interpolar = InterpoladorSegmento()

    def __call__(self, entrada: EnderecoMaisProximoInput) -> EnderecoFeature:
        return self.pipeline(entrada)

    def pipeline(self, entrada: EnderecoMaisProximoInput) -> EnderecoFeature:
        proximos = self._segmentos_no_raio(entrada.consulta)       # do mais perto ao mais longe
        escolhido = self._primeiro_numerado(proximos, entrada.consulta.raio_m)
        lados = self._lados_numerados(escolhido)                   # ao menos um: é o critério da escolha
        # O solver precisa de UMA paridade para achar o vizinho; o sentido que ele devolve é o do
        # segmento, e vale para os dois lados.
        referencia = lados[0]
        vizinhos = self._vizinhos_com_numeracao(escolhido, referencia, entrada.consulta)
        linha = self._corrigir_orientacao(escolhido, vizinhos, referencia)
        ponto = self._ponto_metrico(entrada.consulta)              # reprojetar + para_geos
        paridade = self._paridade_do_ponto(lados, linha, ponto)
        numero = self._numero_do_ponto(linha, escolhido, ponto, paridade)
        # Reinterpola o número já arredondado: o ponto do endereço é o que a busca daria para ele.
        ponto_endereco = self._interpolar(linha, escolhido, numero, paridade, entrada.output_crs)
        return montar_endereco(ponto_endereco, escolhido, numero, paridade, entrada.output_crs)

    def _primeiro_numerado(
        self,
        proximos: tuple[SegmentoProximo, ...],
        raio_m: float,
    ) -> SegmentoLogradouroFeature:
        # Segmento sem numeração (viaduto, viela, praça) não vira endereço: não concorre.
        for proximo in proximos:
            if self._lados_numerados(proximo.segmento):
                return proximo.segmento
        raise NenhumSegmentoNumeradoNoRaioError(raio_m)

    def _lados_numerados(self, segmento: SegmentoLogradouroFeature) -> list[Paridade]:
        return [paridade for paridade in Paridade if tem_numeracao(segmento.attributes, paridade)]

    def _vizinhos_com_numeracao(
        self,
        escolhido: SegmentoLogradouroFeature,
        referencia: Paridade,
        consulta: SegmentosNoRaioInput,
    ) -> list[SegmentoLogradouroFeature]:
        # A segunda ida ao WFS: o vizinho que orienta o segmento pode estar fora do raio.
        do_codlog = LogradouroGeocodInput(
            codlog=escolhido.attributes.codlog,
            layer_name=consulta.layer_name,
            output_crs=consulta.crs_metrico,
        )
        segmentos = self._segmentos(do_codlog)
        return [s for s in segmentos if tem_numeracao(s.attributes, referencia)]

    def _paridade_do_ponto(self, lados: list[Paridade], linha: LineString, ponto: Point) -> Paridade:
        # Pista de avenida: o segmento é de um lado só, e estar mais perto dele já é estar desse lado.
        if len(lados) == 1:
            return lados[0]
        lado = lado_do_ponto(linha, ponto)
        return PARIDADE_POR_LADO[lado]

    def _numero_do_ponto(
        self,
        linha: LineString,
        escolhido: SegmentoLogradouroFeature,
        ponto: Point,
        paridade: Paridade,
    ) -> int:
        # A inversa do InterpoladorSegmento: da posição ao longo da linha para o número na faixa.
        inicial = limite_inicial(escolhido.attributes, paridade)
        final = limite_final(escolhido.attributes, paridade)
        fracao = linha.project_normalized(ponto)        # 0 no início da numeração, 1 no fim
        bruto = inicial + fracao * (final - inicial)
        resto = 0 if paridade is Paridade.PAR else 1
        numero = 2 * round((bruto - resto) / 2) + resto   # o inteiro mais perto COM a paridade do lado
        primeiro = 2 - resto                              # faixa par que começa em 0 não devolve o número 0
        piso = max(inicial, primeiro)
        return max(min(numero, final), piso)
```

**`apps/endereco_mais_proximo/desenho_declarado.py`** — app novo, montado em `endereco-mais-proximo/`.

```python
CONSULTA_ENDERECO_MAIS_PROXIMO = ConsultaSobreDesenho(
    slug="endereco_mais_proximo.do_ponto",
    nome="Endereço mais próximo",
    tooltip="Endereço oficial do logradouro mais perto do ponto marcado.",
    url_name="endereco_mais_proximo:do_ponto",
    tipos=frozenset({TipoDesenho.PONTO}),
)
```

O ícone é `static/src/acoes/endereco_mais_proximo/do_ponto/icones/pequeno.svg`.

**`apps/mapping/registro_desenho.py`**

```python
itens=(
    CONSULTA_LOTES_INTERSECTADOS,
    CONSULTA_LOGRADOURO_MAIS_PROXIMO,
    CONSULTA_ENDERECO_MAIS_PROXIMO,   # NOVO
),
```

**`apps/endereco_mais_proximo/views.py`** — rota aberta: lê a camada pública de segmentos.

```python
MSG_SEM_ENDERECO_NO_RAIO = (
    "Nenhum logradouro com numeração foi encontrado a {raio_m:.0f} metros do ponto."
)


@require_POST
def do_ponto(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaSobrePonto.model_validate(request.POST.dict())
    entrada = EnderecoMaisProximoInput(
        consulta=SegmentosNoRaioInput(
            ponto=consulta.desenho,
            crs_ponto=MAP_OUTPUT_CRS,
            raio_m=MAIS_PROXIMO_RAIO_LIMITE_M,   # o mesmo raio da SPEC 005
            layer_name=WFS_LAYER_LOGRADOUROS,
            campo_geometria=WFS_LOGRADOUROS_CAMPO_GEOMETRIA,
            crs_metrico=MAP_INTERPOLATION_CRS,
        ),
        output_crs=MAP_OUTPUT_CRS,
    )
    fetcher = build_fetcher(settings)
    segmentos_no_raio = SegmentosNoRaio(fetcher)
    segmentos_do_codlog = LogradouroGeocoder(fetcher)
    buscar_endereco = EnderecoMaisProximo(segmentos_no_raio, segmentos_do_codlog)
    try:
        endereco = buscar_endereco(entrada)
    except NenhumSegmentoNumeradoNoRaioError:
        mensagem = MSG_SEM_ENDERECO_NO_RAIO.format(raio_m=MAIS_PROXIMO_RAIO_LIMITE_M)
        return render(request, TEMPLATE_RECUSA_ACAO, contexto_aviso(mensagem))
    # A mesma resposta do endereço escolhido na busca: o payload do mapa e a gaveta, que ocupa o
    # #gaveta-entidade no lugar da gaveta dos desenhos.
    return renderizar_endereco(request, endereco)
```

## 7 · Caveats
A consulta mora em `address_geocod`, e não num submódulo próprio da ação (§6.3 do CLAUDE.md). Ela é a
função inversa da interpolação e compõe as peças internas dela — orientação, interpolador, numeração.
O custo é o submódulo passar a ter duas portas de entrada, a da busca e a do desenho.

A resposta é a do endereço da busca, e não a base `mapping/_resultado_acao.html`. O resultado é uma
entidade só, que já tem gaveta lateral, e não uma coleção a tabular na gaveta inferior. O custo é o
ponto sair na cor do endereço e não na cor única dos resultados de ação, o app da ação importar
`renderizar_endereco` do app de busca, e a volta à bancada — clicar no ponto desenhado — ser JavaScript
já existente, sem teste automatizado.

O lado sai de um produto vetorial escrito sobre coordenadas (§7.2 do CLAUDE.md veda cálculo manual).
O GeoDjango não expõe predicado de lado, e as coordenadas do cálculo são pontos que o próprio GEOS
interpolou. O custo é uma conta de geometria fora da biblioteca, e o ponto exatamente sobre o eixo
contar como direita, por convenção.

A regra "par à direita, ímpar à esquerda" está em código como convenção do município, conferida em
dado real num trecho da Av. Paulista. É a única forma de escolher entre as duas faixas de um segmento
de rua comum. O custo é o logradouro numerado fora da regra sair do lado trocado, e a via de segmento
único, que o solver não tem como orientar, poder sair com lado e número invertidos.

O sentido do segmento é apurado com uma paridade de referência e vale para os dois lados. O solver
precisa de uma faixa para achar o vizinho, e a paridade do ponto só se conhece depois de orientar. O
custo é o segmento cujas faixas par e ímpar crescem em sentidos opostos sair errado no lado que não é
o de referência.

Cada acionamento vai duas vezes ao WFS: os segmentos no raio e os do codlog escolhido. O vizinho que
orienta o segmento pode estar fora do raio. O custo é o dobro de rede por clique.

Segmento sem numeração não concorre. Dele não se monta endereço. O custo é um ponto marcado numa viela
sem numeração devolver o endereço da rua ao lado, sem dizer que havia logradouro mais perto.

A faixa `0–0` conta como lado sem numeração no predicado que esta consulta e a geocodificação da busca
compartilham. A camada marca o lado vazio com `None` e, em 533 lados, com `0–0`, e só o final zero o
separa da faixa par que começa em zero. O custo é a geocodificação da busca mudar junto: o segmento
`0–0` deixa de entrar entre os vizinhos que orientam o segmento escolhido.

Segmento com um lado só numerado devolve a paridade dele, sem olhar o lado do ponto. Nas avenidas de
pistas separadas, cada pista é um segmento com a faixa de um lado, e o segmento do outro lado concorre
pela distância. O custo é o ponto marcado no canteiro central, ou mais perto da pista oposta, sair com
a paridade dela.

O número sai do segmento mais próximo mesmo quando outro segmento do codlog tem faixa que o contém. A
busca, para o mesmo número, usa o primeiro segmento cuja faixa o contém. O custo é que, em logradouro
com faixas sobrepostas, digitar na busca o endereço devolvido pode cair noutro ponto.

Túnel e viaduto com numeração concorrem pela distância em planta, como na SPEC 005. A camada não
separa o que passa por baixo ou por cima da rua. O custo é o ponto na calçada do MASP devolver um
endereço no túnel que passa sob ele, e não na Av. Paulista.

## 8 · Testes (TDD)
- `test_escolhe_o_numerado_mais_perto` — entre três segmentos no raio, o endereço sai do mais próximo
  que tem numeração, e não dos dois sem numeração que estão mais perto: um com as faixas em `None` e
  outro com as faixas em `0–0`.
- `test_numero_acompanha_a_posicao_no_segmento` — ponto a 30% do comprimento de um segmento com
  faixa par 100–200 devolve 130, com a faixa 100–200; a 30,6% devolve 130, e não 131; no início de uma
  faixa par 0–42 devolve 2, não 0.
- `test_lado_do_ponto_decide_a_paridade` — num segmento com as duas faixas, o ponto à direita do
  sentido crescente devolve número par e a faixa par, e o mesmo ponto espelhado devolve ímpar e a
  faixa ímpar; repetido com o segmento apontando para o sul e para o oeste, a resposta não muda.
- `test_segmento_contra_a_numeracao_e_invertido_antes_do_lado` — segmento cuja geometria vem do número
  maior para o menor, com vizinho que o denuncia e um segmento `0–0` do mesmo codlog: número e
  paridade saem como se a geometria viesse no sentido certo.
- `test_segmento_de_um_lado_so_devolve_a_paridade_dele` — segmento só com faixa ímpar e ponto à
  direita devolve número ímpar, com o lado par vazio em `None` e em `0–0`.
- `test_ida_e_volta_com_a_geocodificacao` — o endereço devolvido, entregue ao `AddressGeocoder` com os
  mesmos segmentos, cai no mesmo ponto.
- `test_sem_segmento_numerado_no_raio_levanta_erro_proprio` — sem segmentos, ou só com segmentos sem
  numeração, levanta `NenhumSegmentoNumeradoNoRaioError`, e os segmentos do codlog não são consultados.
- `test_gaveta_anonima_traz_as_duas_consultas_no_poco_de_pontos` — POST anônimo com um ponto
  selecionado devolve, no poço de pontos, o botão de `logradouro_mais_proximo:do_ponto` seguido do de
  `endereco_mais_proximo:do_ponto`, os dois com `hx-include=".linha-desenho__marca:checked"`.
- `test_do_ponto_devolve_mapa_e_gaveta_do_endereco` — POST anônimo com `desenho` de ponto devolve o
  payload do mapa com o ponto do endereço e o OOB do `#gaveta-entidade` com a gaveta do endereço:
  logradouro, codlog, número e faixa do lado. POST sem segmento numerado no raio devolve o aviso com o
  raio e o toggle da gaveta dos desenhos desmarcado, sem payload de mapa; POST com `desenho` de
  polígono é recusado pela validação, sem consultar o WFS.
- `test_endereco_mais_proximo_no_geosampa` — ponto sobre a pista par da Av. Paulista em frente ao MASP
  devolve Av. Paulista, codlog 156566, com número par entre 1576 e 1590 *(marker `integration`)*.
