from .normalizer import TextNormalizer
from .numero_porta import chave_numero_porta
from .sem_numero import SemNumeroNormalizer

normalize_text = TextNormalizer()
normalize_sem_numero = SemNumeroNormalizer()

__all__ = ["normalize_text", "normalize_sem_numero", "chave_numero_porta"]
