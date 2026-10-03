from django.contrib.gis.geos import LineString, Point

from .models import Lado

# Meio comprimento do trecho do eixo que dá o sentido local, em metros.
PASSO_M = 1.0


def lado_do_ponto(linha: LineString, ponto: Point) -> Lado:
    """`linha` já no sentido em que a numeração cresce; os dois no mesmo CRS métrico."""
    # O sentido que vale é o do trecho onde o ponto se projeta, não o da corda entre as pontas.
    posicao = linha.project(ponto)
    posicao_antes = max(posicao - PASSO_M, 0.0)
    posicao_depois = min(posicao + PASSO_M, linha.length)
    antes = linha.interpolate(posicao_antes)
    depois = linha.interpolate(posicao_depois)
    eixo_x = depois.x - antes.x
    eixo_y = depois.y - antes.y
    ponto_x = ponto.x - antes.x
    ponto_y = ponto.y - antes.y
    # Produto vetorial positivo: o ponto gira no sentido anti-horário a partir do eixo.
    giro = eixo_x * ponto_y - eixo_y * ponto_x
    return Lado.ESQUERDA if giro > 0 else Lado.DIREITA
