"""TF-IDF em Python puro, sem scikit-learn.

Pure-Python TF-IDF, no scikit-learn.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

#: Palavras vazias em portugues que nao carregam significado de busca.
STOPWORDS = frozenset(
    """
    a o e de da do das dos em no na nos nas um uma uns umas para por com sem
    que se ao aos as os ou mas como quando onde qual quais ser ter estar
    foi sao tem tem-se este esta estes estas esse essa esses essas
    ao aos as os the of and or to in on for with without is are was were
    """.split()
)

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenizar(texto: str) -> list[str]:
    """Quebra um texto em tokens normalizados.

    Split text into normalized tokens.

    Acentos sao preservados como estao; a comparacao e feita em minusculas e
    sem pontuacao, que e o suficiente para a base de conhecimento em portugues.

    Args:
        texto: O texto de entrada.

    Returns:
        Lista de tokens, sem palavra vazia e sem token de 1 caractere.
    """
    minusculo = texto.lower()
    bruto = _TOKEN.findall(minusculo)
    return [t for t in bruto if len(t) > 1 and t not in STOPWORDS]


@dataclass
class Indice:
    """Indice TF-IDF de uma colecao de documentos.

    TF-IDF index of a document collection.

    Atributos:
        documentos: Texto de cada documento, na ordem de entrada.
        ids: Identificador de cada documento.
    """

    documentos: list[str] = field(default_factory=list)
    ids: list[str] = field(default_factory=list)
    _freqs: list[Counter] = field(default_factory=list, repr=False)
    _df: Counter = field(default_factory=Counter, repr=False)
    _idf: dict[str, float] = field(default_factory=dict, repr=False)

    def adicionar(self, doc_id: str, texto: str) -> None:
        """Adiciona um documento ao indice.

        Add a document to the index.

        Args:
            doc_id: Identificador do documento.
            texto: Texto a indexar.
        """
        tokens = tokenizar(texto)
        self.ids.append(doc_id)
        self.documentos.append(texto)
        self._freqs.append(Counter(tokens))
        for termo in set(tokens):
            self._df[termo] += 1
        self._idf = {}

    def construir(self) -> None:
        """Calcula o IDF de todos os termos.

        Compute the IDF of every term.

        O IDF usa a forma suavizada ``ln((N + 1) / (df + 1)) + 1``. A suavizacao
        importa: sem o ``+ 1`` do log, um termo que aparece em **todos** os
        documentos recebe IDF zero, e some da busca. Artigos de base de
        conhecimento repetem palavras ("cabo", "camera") em quase toda entrada, e
        sem a suavizacao esses termos - que bemiquely nao distinguem nada -
        dominariam o ranking.
        """
        n = len(self._freqs)
        if n == 0:
            self._idf = {}
            return
        self._idf = {
            termo: math.log((n + 1) / (df + 1)) + 1.0
            for termo, df in self._df.items()
        }

    @property
    def idf(self) -> dict[str, float]:
        """Pesos IDF calculados.

        Computed IDF weights.
        """
        if not self._idf and self._freqs:
            self.construir()
        return self._idf

    def vetor(self, indice_doc: int) -> dict[str, float]:
        """Vetor TF-IDF normalizado de um documento.

        Normalised TF-IDF vector of a document.

        Args:
            indice_doc: Posicao do documento na colecao.

        Returns:
        Dicionario termo -> peso, ja normalizado para norma 1.

        Raises:
            IndexError: Se a posicao nao existir.
        """
        if not 0 <= indice_doc < len(self._freqs):
            raise IndexError(f"Documento fora da faixa / index out of range: {indice_doc}")

        idf = self.idf
        freq = self._freqs[indice_doc]
        total = sum(freq.values())
        if total == 0:
            return {}

        pesos = {
            termo: (contagem / total) * idf.get(termo, 0.0)
            for termo, contagem in freq.items()
        }
        return _normalizar(pesos)

    def vetor_consulta(self, consulta: str) -> dict[str, float]:
        """Vetor TF-IDF de uma consulta, usando o IDF da colecao.

        TF-IDF vector of a query, using the collection IDF.

        Termo que nao aparece em nenhum documento recebe peso zero e e
        descartado: manteria peso na soma sem participa da similaridade, e
        ainda Diluiria o resultado.

        Args:
            consulta: Texto digitado pelo tecnico.

        Returns:
        Dicionario termo -> peso, normalizado.
        """
        freq = Counter(tokenizar(consulta))
        total = sum(freq.values())
        if total == 0:
            return {}
        idf = self.idf
        pesos = {
            termo: (contagem / total) * idf.get(termo, 0.0)
            for termo, contagem in freq.items()
        }
        pesos = {t: p for t, p in pesos.items() if p > 0.0}
        return _normalizar(pesos)

    def __len__(self) -> int:
        return len(self._freqs)


def _normalizar(vetor: dict[str, float]) -> dict[str, float]:
    """Normaliza um vetor para norma euclidiana 1.

    Normalise a vector to unit euclidean norm.
    """
    norma = math.sqrt(sum(v * v for v in vetor.values()))
    if norma == 0.0:
        return {k: 0.0 for k in vetor}
    return {k: v / norma for k, v in vetor.items()}


def similaridade(
    a: dict[str, float], b: dict[str, float]
) -> float:
    """Similaridade de cosseno entre dois vetores normalizados.

    Cosine similarity between two normalised vectors.

    Implementado a mao, sem numpy, porque o objetivo do projeto e mostrar a
    conta e nao chamar uma biblioteca.

    **Pre-condicao:** ambos os vetores devem vir normalizados, como o
    :class:`Indice` produz. Aqui o cosseno degenera em produto escalar, entao
    um vetor nao normalizado devolve valor fora do intervalo 0..1. Quem chama
    direto e responsavel por normalizar antes.

    Args:
        a: Primeiro vetor, ja normalizado.
        b: Segundo vetor, ja normalizado.

    Returns:
        Valor entre 0.0 e 1.0 para vetores normalizados.
    """
    if not a or not b:
        return 0.0
    termos = set(a) & set(b)
    return sum(a[t] * b[t] for t in termos)