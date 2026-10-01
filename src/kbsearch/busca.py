"""Busca por similaridade sobre a base de conhecimento.

Similarity search over the knowledge base.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .indexador import Indice, similaridade, tokenizar
from .normalizacao import Normalizador, carregar_sinonimos


@dataclass
class Artigo:
    """Artigo da base de conhecimento.

    A knowledge base article.

    Atributos:
        id: Identificador unico.
        titulo: Titulo do artigo.
        categoria: ``rede``, ``energia``, ``cftv``, ``hardware`` ou ``software``.
        sintoma: O que o usuario observa, em linguagem natural.
        solucao: O procedimento.
    """

    id: str
    titulo: str
    categoria: str
    sintoma: str
    solucao: str
    prioridade: int = 2

    @property
    def texto(self) -> str:
        """Todo o texto indexado do artigo.

        The full indexed text of the article.
        """
        return (
            f"{self.titulo}. {self.categoria}. {self.sintoma}. {self.solucao}"
        )


@dataclass
class Resultado:
    """Um resultado de busca.

    A search result.

    Atributos:
        artigo: O artigo encontrado.
        score: Similaridade de cosseno, entre 0.0 e 1.0.
        trecho: Trecho do artigo que casa com a consulta.
    """

    artigo: Artigo
    score: float
    trecho: str = ""


@dataclass
class BaseConhecimento:
    """Base de conhecimento com indice TF-IDF pronto.

    Knowledge base with a ready TF-IDF index.

    Atributos:
        artigos: Todos os artigos carregados.
        indice: Indice construido sobre eles.
        normalizador: Mapa de sinonimos aplicado.
    """

    artigos: list[Artigo] = field(default_factory=list)
    indice: Indice = field(default_factory=Indice)
    normalizador: Normalizador = field(default_factory=Normalizador)

    def construir(self) -> None:
        """Indexa todos os artigos.

        Index every article.

        Cada documento passa pelo mesmo normalizador da consulta: sinonimos
        viram termo canonico. Sem isso o indice fica bilingue - o artigo escrito
        com "travando" vira vizinho do artigo escrito com "trava", e a busca
        por sinonimo funciona por acidente, nao por desenho.
        """
        self.indice = Indice()
        for artigo in self.artigos:
            tokens = tokenizar(artigo.texto)
            canonicos = self.normalizador.aplicar(tokens)
            expandidos = self.normalizador.expandir(canonicos)
            texto_normalizado = " ".join(canonicos + expandidos)
            self.indice.adicionar(artigo.id, texto_normalizado)
        self.indice.construir()

    def buscar(
        self, consulta: str, top: int = 5, categoria: str | None = None
    ) -> list[Resultado]:
        """Busca por similaridade de cosseno.

        Search by cosine similarity.

        A consulta passa por dois periodos: primeiro cada token e mapeado para
        o termo canonico (``travando`` vira ``travamento``), depois o vetor
        canonico e expandido com os sinonimos. Sem a expansao, um artigo escrito
        com "travamento" nao seria encontrado por quem digita "travando" - e vice
        versa. Os dois passos sao necessarios porque o problema e de vocabulario
        nos dois sentidos.

        Args:
            consulta: Texto digitado pelo tecnico.
            top: Quantos resultados devolver.
            categoria: Filtro opcional de categoria.

        Returns:
            Lista de :class:`Resultado`, do mais para o menos semelhante.
        """
        tokens = tokenizar(consulta)
        canonicos = self.normalizador.aplicar(tokens)
        expandidos = self.normalizador.expandir(canonicos)

        if not expandidos:
            return []

        # O termo digitado pesa mais que os sinonimos gerados. Sem isso,
        # expandir "travando" para oito termos dilui a consulta: um artigo que
        # traz "travando" no titulo perde para outro que menciona "travou" numa
        # frase de passagem, que e o oposto do que a busca precisa fazer.
        #
        # O peso sai da repeticao, porque repetir o token equivale a multiplicar
        # o TF - e e no TF que o peso entra. Os termos que o usuario NAO digitou
        # recebem peso 1; o canonico de cada palavra digitada recebe peso 4.
        # Um termo canonico digitado vale 4 porque o usuario pediu sinônimo;
        # um que so apareceu por expansao vale 1 porque so e variacao.
        digitados = set(tokens)
        canonicos_do_usuario = set(canonicos)

        termos_ponderados: list[str] = []
        for token in expandidos:
            if token in canonicos_do_usuario:
                peso = 4
            elif token in digitados:
                peso = 2
            else:
                peso = 1
            termos_ponderados.extend([token] * peso)

        consulta_normalizada = " ".join(termos_ponderados)
        vetor = self.indice.vetor_consulta(consulta_normalizada)
        if not vetor:
            return []

        resultados: list[Resultado] = []
        for i, artigo in enumerate(self.artigos):
            if categoria and artigo.categoria != categoria:
                continue
            score = similaridade(vetor, self.indice.vetor(i))
            if score > 0.0:
                resultados.append(
                    Resultado(
                        artigo=artigo,
                        score=round(score, 4),
                        trecho=self._trecho(artigo, set(expandidos)),
                    )
                )

        # Desempate por prioridade: artigo de hardware ganha de artigo de rede
        # quando os dois tem a mesma similaridade.
        resultados.sort(key=lambda r: (-r.score, r.artigo.prioridade, r.artigo.id))
        return resultados[:top]

    def _trecho(self, artigo: Artigo, termos: set[str]) -> str:
        """Recorta o trecho que casa com a consulta.

        Extract the snippet that matches the query.

        Args:
            artigo: O artigo a recortar.
            termos: Tokens da consulta normalizada.

        Returns:
            A primeira frase do sintoma que contem um dos termos, ou o inicio
            do sintoma quando nenhum casa.
        """
        for frase in artigo.sintoma.replace(";", ".").split("."):
            tokens_frase = set(tokenizar(frase))
            if tokens_frase & termos:
                return frase.strip()
        return artigo.sintoma[:120].strip()


def carregar_base(
    caminho: str | Path, sinonimos: str | Path | None = None
) -> BaseConhecimento:
    """Carrega a base de conhecimento e constroi o indice.

    Load the knowledge base and build the index.

    Args:
        caminho: Caminho do JSON com os artigos.
        sinonimos: Caminho opcional do YAML de sinonimos.

    Returns:
        A base pronta para buscar.

    Raises:
        ValueError: Se o JSON nao for uma lista de artigos.
    """
    with open(caminho, "r", encoding="utf-8") as fh:
        dados = json.load(fh)

    if isinstance(dados, dict):
        dados = dados.get("artigos")
    if not isinstance(dados, list):
        raise ValueError(
            "Esperado uma lista de artigos, ou um mapa com a chave 'artigos' "
            "/ expected a list of articles, or a map with the 'artigos' key"
        )

    artigos = [
        Artigo(
            id=str(a["id"]),
            titulo=str(a["titulo"]),
            categoria=str(a.get("categoria", "geral")),
            sintoma=str(a.get("sintoma", "")),
            solucao=str(a.get("solucao", "")),
            prioridade=int(a.get("prioridade", 2)),
        )
        for a in dados
    ]

    mapa = carregar_sinonimos(sinonimos) if sinonimos else {}
    base = BaseConhecimento(
        artigos=artigos, normalizador=Normalizador(mapa)
    )
    base.construir()
    return base