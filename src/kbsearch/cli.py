"""CLI do kbsearch.

CLI entry point for kbsearch.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .busca import carregar_base

RAIZ = Path(__file__).resolve().parents[2]
BASE_PADRAO = RAIZ / "dados" / "base-conhecimento.json"
SINONIMOS_PADRAO = RAIZ / "dados" / "sinonimos.yaml"


def _resultado_json(base, consulta: str, top: int, categoria: str | None) -> dict:
    """Monta o payload JSON da busca.

    Build the JSON payload of a search.
    """
    achados = base.buscar(consulta, top=top, categoria=categoria)
    return {
        "consulta": consulta,
        "categoria_filtro": categoria,
        "total_resultados": len(achados),
        "resultados": [
            {
                "rank": i + 1,
                "id": r.artigo.id,
                "titulo": r.artigo.titulo,
                "categoria": r.artigo.categoria,
                "score": r.score,
                "trecho": r.trecho,
                "solucao": r.artigo.solucao,
            }
            for i, r in enumerate(achados)
        ],
    }


def _cmd_buscar(args: argparse.Namespace) -> int:
    """Executa uma busca.

    Run a search.
    """
    base = carregar_base(args.base, args.sinonimos)
    payload = _resultado_json(base, args.consulta, args.top, args.categoria)

    if args.formato == "json":
        texto = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.saida:
            Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
            Path(args.saida).write_text(texto + "\n", encoding="utf-8")
            print(f"Resultado gravado em: {args.saida}")
        else:
            print(texto)
        return 0

    print(f"Consulta / query: {args.consulta!r}")
    print(f"Base: {len(base.artigos)} artigos")
    print()
    if not payload["resultados"]:
        print("Nenhum artigo acima do corte.")
        return 0
    for r in payload["resultados"]:
        print(f"{r['rank']}. [{r['categoria']}] {r['titulo']}  (score {r['score']:.4f})")
        print(f"   Trecho: {r['trecho']}")
        print(f"   Solucao: {r['solucao'][:110]}")
        print()

    if args.saida:
        Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
        Path(args.saida).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Resultado gravado em: {args.saida}")
    return 0


def _cmd_listar(args: argparse.Namespace) -> int:
    """Lista os artigos da base.

    List the articles of the base.
    """
    base = carregar_base(args.base, args.sinonimos)
    categorias: dict[str, int] = {}
    for a in base.artigos:
        categorias[a.categoria] = categorias.get(a.categoria, 0) + 1

    print(f"{len(base.artigos)} artigos em {len(categorias)} categorias")
    for cat in sorted(categorias):
        print(f"  {cat:<12} {categorias[cat]}")
    print()
    for a in base.artigos[: args.top]:
        print(f"{a.id:<12} [{a.categoria}] {a.titulo}")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    """Monta o parser de argumentos.

    Build the argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="kbsearch",
        description=(
            "Busca por similaridade em base de conhecimento local. "
            "Similarity search over a local knowledge base."
        ),
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    def _comum(p: argparse.ArgumentParser) -> None:
        p.add_argument("--base", default=str(BASE_PADRAO), help="JSON da base.")
        p.add_argument("--sinonimos", default=str(SINONIMOS_PADRAO), help="YAML de sinonimos.")

    p_b = sub.add_parser("buscar", help="Busca por sintoma em linguagem natural.")
    _comum(p_b)
    p_b.add_argument("consulta", help="Sintoma descrito pelo tecnico.")
    p_b.add_argument("--top", type=int, default=5, help="Quantos resultados.")
    p_b.add_argument("--categoria", help="Filtra por categoria.")
    p_b.add_argument("--formato", choices=["texto", "json"], default="texto")
    p_b.add_argument("--saida", help="Grava o resultado JSON neste caminho.")
    p_b.set_defaults(func=_cmd_buscar)

    p_l = sub.add_parser("listar", help="Lista os artigos.")
    _comum(p_l)
    p_l.add_argument("--top", type=int, default=10, help="Quantos listar.")
    p_l.set_defaults(func=_cmd_listar)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI.

    CLI entry point.
    """
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro / error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())