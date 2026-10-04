"""Confere encoding dos arquivos de texto do repositorio.

Check the encoding of every text file in the repository.

Rejeita BOM UTF-8 no inicio do arquivo, o caractere de substituicao
U+FFFD e qualquer ideograma CJK. Nenhum dos tres pertence a este
repositorio, entao e mais barato falhar aqui do que no diff.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: Raiz do repositorio.
RAIZ = Path(__file__).resolve().parent.parent

#: Extensoes varridas. Binarios ficam de fora de proposito.
EXTENSOES = {".py", ".md", ".txt", ".json", ".yml", ".yaml",
             ".toml", ".cfg", ".ini", ".ps1"}

#: Diretorios e arquivos ignorados.
IGNORADOS = {".git", "__pycache__", ".pytest_cache", ".coverage"}

#: BOM UTF-8 em bytes.
BOM = b"\xef\xbb\xbf"

#: Intervalo de ideogramas CJK.
CJK = range(0x3000, 0x9FFF + 1)

#: Caractere de substituicao.
SUBSTITUICAO = 0xFFFD


def varrer(raiz: Path = RAIZ) -> tuple[list[tuple[str, int, str]], int]:
    """Procura arquivo de texto com caractere invalido.

    Find text files holding an invalid character.

    Args:
        raiz: Diretorio a varrer.

    Returns:
        Tupla ``(problemas, conferidos)``; ``problemas`` e uma lista de
        ``(caminho, linha, motivo)`` e ``conferidos`` e a quantidade de
        arquivos lidos.
    """
    problemas: list[tuple[str, int, str]] = []
    conferidos = 0
    for caminho in sorted(raiz.rglob("*")):
        if not caminho.is_file():
            continue
        if any(parte in IGNORADOS for parte in caminho.parts):
            continue
        if caminho.suffix.lower() not in EXTENSOES:
            continue
        conferidos += 1
        bruto = caminho.read_bytes()
        if bruto.startswith(BOM):
            problemas.append((
                str(caminho.relative_to(raiz)), 1,
                "BOM UTF-8 no inicio do arquivo",
            ))
            continue
        try:
            texto = bruto.decode("utf-8")
        except UnicodeDecodeError as exc:
            problemas.append((
                str(caminho.relative_to(raiz)), 0,
                f"nao decodifica como UTF-8: {exc}",
            ))
            continue
        for numero, linha in enumerate(texto.splitlines(), 1):
            for caractere in linha:
                ponto = ord(caractere)
                if ponto == SUBSTITUICAO:
                    problemas.append((
                        str(caminho.relative_to(raiz)), numero,
                        "caractere de substituicao U+FFFD",
                    ))
                    break
                if ponto in CJK:
                    problemas.append((
                        str(caminho.relative_to(raiz)), numero,
                        f"ideograma CJK U+{ponto:04X}",
                    ))
                    break
    return problemas, conferidos


def main() -> int:
    """Executa a varredura e reporta.

    Run the sweep and report.
    """
    problemas, conferidos = varrer()
    if not problemas:
        print(f"encoding ok: {conferidos} arquivo(s), nenhum BOM, U+FFFD ou CJK")
        return 0
    print(f"encoding FALHOU: {conferidos} arquivo(s), {len(problemas)} ocorrencia(s)")
    for caminho, linha, motivo in problemas:
        onde = f"{caminho}:{linha}" if linha else caminho
        print(f"  {onde}: {motivo}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
