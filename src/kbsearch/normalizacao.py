"""Normalizacao de sinonimos e termos tecnicos.

Synonym and technical term normalisation.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .indexador import STOPWORDS


def carregar_sinonimos(caminho: str | Path) -> dict[str, str]:
    """Le o mapa de sinonimos de um YAML.

    Read the synonym map from a YAML file.

    O arquivo tem a forma ``termo_de_busca: termo_canonico``. O mapeamento e
    aplicado na normalizacao da consulta, para que "travando" e "congelou"
    virem o mesmo token e caiam no mesmo artigo.

    Args:
        caminho: Caminho do ``.yaml``.

    Returns:
        Dicionario de sinonimo para termo canonico.
    """
    with open(caminho, "r", encoding="utf-8") as fh:
        dados = yaml.safe_load(fh)
    if not isinstance(dados, dict):
        raise ValueError(
            "Esperado um mapeamento de sinonimos / expected a synonym mapping"
        )

    mapa: dict[str, str] = {}
    for grupo in dados.values():
        if isinstance(grupo, dict):
            canonico = str(grupo.get("canonico", ""))
            for sinonimo in grupo.get("sinonimos", []) or []:
                if canonico:
                    mapa[str(sinonimo).lower()] = canonico.lower()
        elif isinstance(grupo, list) and grupo:
            # Formato compacto: [canonico, sinonimos...]. O primeiro elemento
            # e o canonico e o resto sao sinonimos - por isso o corte em [1:],
            # sem o qual cada letra do sinonimo viraria uma entrada.
            canonico = str(grupo[0]).lower()
            for sinonimo in list(grupo[1:]):
                mapa[str(sinonimo).lower()] = canonico

    return mapa


class Normalizador:
    """Normaliza texto de consulta com mapa de sinonimos.

    Normalises query text with a synonym map.

    Atributos:
        mapa: Sinonimo em minusculas para termo canonico.
    """

    def __init__(self, mapa: dict[str, str] | None = None) -> None:
        self.mapa: dict[str, str] = dict(mapa or {})

    def canonico(self, token: str) -> str:
        """Devolve o termo canonico de um token.

        Return the canonical term for a token.

        O token volta inalterado quando nao ha sinonimo mapeado - e o caso mais
        comum, e nao e erro.

        Args:
            token: Token em minusculas.

        Returns:
            O termo canonico, ou o proprio token.
        """
        return self.mapa.get(token, token)

    def aplicar(self, tokens: list[str]) -> list[str]:
        """Substitui sinonimos por termos canonicos.

        Replace synonyms with canonical terms.

        Args:
            tokens: Tokens ja tokenizados.

        Returns:
            Tokens com sinonimos substituidos, sem duplicatas, na ordem da
            primeira aparição.
        """
        vistos: dict[str, None] = {}
        for token in tokens:
            vistos.setdefault(self.canonico(token), None)
        return list(vistos.keys())

    def expandir(self, tokens: list[str]) -> list[str]:
        """Expande um token canonico nos seus sinonimos.

        Expand a canonical token into its synonyms.

        Inverso de :meth:`aplicar`: em vez de fundir sinonimos no canonico,
        expande o canonico para todos os termos que apontam para ele. E o que
        faz o artigo que usa "travamento" ser encontrado por quem digita
        "travando".

        Args:
            tokens: Tokens ja canonizados.

        Returns:
            Tokens originais mais os sinonimos de cada um.
        """
        invertido: dict[str, list[str]] = {}
        for sinonimo, canonico in self.mapa.items():
            invertido.setdefault(canonico, []).append(sinonimo)

        saida: dict[str, None] = {}
        for token in tokens:
            saida.setdefault(token, None)
            for sinonimo in invertido.get(token, []):
                saida.setdefault(sinonimo, None)
        return list(saida.keys())


def padraes_padrao() -> dict[str, str]:
    """Mapa de sinonimos embutido, usado quando nao ha YAML.

    Built-in synonym map, used when there is no YAML.

    Existe para o pacote funcionar sem arquivo externo. O
    ``dados/sinonimos.yaml`` e mais completo e e o que a CLI usa.

    Returns:
        Dicionario de sinonimos.
    """
    return {
        # Travamento / congelamento
        "travado": "travamento",
        "travou": "travamento",
        "travando": "travamento",
        "congelou": "travamento",
        "congelando": "travamento",
        "congelado": "travamento",
        "azul": "travamento",
        # Queda de link ou de dispositivo
        "caiu": "queda",
        "cai": "queda",
        "caindo": "queda",
        "offline": "queda",
        "reiniciou": "reinicio",
        "reiniciando": "reinicio",
        "reboot": "reinicio",
        # Degradacao
        "lento": "degradacao",
        "lentidao": "degradacao",
        "demora": "degradacao",
        # Consumo de energia
        "gasto": "consumo",
        "alto": "consumo",
    }


__all__ = [
    "Normalizador",
    "carregar_sinonimos",
    "padraes_padrao",
    "STOPWORDS",
]