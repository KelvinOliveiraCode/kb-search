"""kbsearch - busca por similaridade em base de conhecimento local.

TF-IDF e similaridade de cosseno implementados em Python puro, sem
scikit-learn e sem modelo de embedding. O objetivo e mostrar a conta e
funcionar offline, sem download de centenas de MB.

TF-IDF and cosine similarity implemented in pure Python, without
scikit-learn and without an embedding model. The point is to show the
arithmetic and to run offline, with no large download.
"""

from .busca import Artigo, BaseConhecimento, Resultado, carregar_base
from .indexador import Indice, similaridade, tokenizar
from .normalizacao import Normalizador, carregar_sinonimos, padraes_padrao

__all__ = [
    "Artigo",
    "BaseConhecimento",
    "Resultado",
    "carregar_base",
    "Indice",
    "similaridade",
    "tokenizar",
    "Normalizador",
    "carregar_sinonimos",
    "padraes_padrao",
]

__version__ = "1.0.0"