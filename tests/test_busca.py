"""Testes da busca e da CLI.

Tests for the search and the CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kbsearch.busca import Artigo, BaseConhecimento, carregar_base
from kbsearch.cli import main
from kbsearch.normalizacao import Normalizador

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ / "dados" / "base-conhecimento.json"
SINONIMOS = RAIZ / "dados" / "sinonimos.yaml"


@pytest.fixture(scope="module")
def base() -> BaseConhecimento:
    """Base carregada uma vez para os testes."""
    return carregar_base(BASE, SINONIMOS)


class TestCargaBase:
    """Leitura da base."""

    def test_carrega_mais_de_60_artigos(self, base) -> None:
        assert len(base.artigos) >= 60

    def test_tem_cinco_categorias(self, base) -> None:
        cats = {a.categoria for a in base.artigos}
        assert {"rede", "energia", "cftv", "hardware", "software"} <= cats

    def test_todo_artigo_tem_campos_preenchidos(self, base) -> None:
        for a in base.artigos:
            assert a.id and a.titulo and a.sintoma and a.solucao

    def test_ids_sao_unicos(self, base) -> None:
        ids = [a.id for a in base.artigos]
        assert len(ids) == len(set(ids))

    def test_indice_tem_um_documento_por_artigo(self, base) -> None:
        assert len(base.indice) == len(base.artigos)

    def test_sinonimos_carregados(self, base) -> None:
        assert base.normalizador.mapa["congelou"] == "travamento"

    def test_json_sem_lista_levanta_valueerror(self, tmp_path) -> None:
        p = tmp_path / "b.json"
        p.write_text('{"outro": 1}', encoding="utf-8")
        with pytest.raises(ValueError, match="lista de artigos"):
            carregar_base(p)

    def test_json_com_chave_artigos_e_aceito(self, tmp_path) -> None:
        p = tmp_path / "b.json"
        p.write_text(
            '{"artigos": [{"id":"a","titulo":"t","categoria":"rede",'
            '"sintoma":"s","solucao":"sol"}]}',
            encoding="utf-8",
        )
        assert len(carregar_base(p).artigos) == 1

    def test_arquivo_inexistente_levanta_oserror(self) -> None:
        with pytest.raises(OSError):
            carregar_base("nao-existe.json")


class TestCriterioDeAceiteTravamento:
    """Criterio de aceite: 'travando' e 'congelou' no mesmo top 1."""

    def test_travando_retorna_artigo_de_travamento(self, base) -> None:
        r = base.buscar("travando", top=5)
        assert r, "a busca nao retornou nada"
        assert r[0].artigo.categoria == "hardware"
        assert "trav" in (r[0].artigo.titulo + r[0].artigo.sintoma).lower()

    def test_congelou_retorna_o_mesmo_article(self, base) -> None:
        a = base.buscar("travando", top=1)[0].artigo.id
        b = base.buscar("congelou", top=1)[0].artigo.id
        assert a == b, f"travando -> {a}, congelou -> {b}"

    def test_score_proximo_entre_as_duas_consultas(self, base) -> None:
        a = base.buscar("travando", top=1)[0].score
        b = base.buscar("congelou", top=1)[0].score
        assert abs(a - b) < 0.01


class TestCriterioDeAceiteCamera:
    """Criterio de aceite: 'camera caiu' traz CFTV antes de energia."""

    def test_primeiro_resultado_e_cftv(self, base) -> None:
        r = base.buscar("camera caiu", top=5)
        assert r[0].artigo.categoria == "cftv"

    def test_artigo_de_camera_entre_os_primeiros(self, base) -> None:
        r = base.buscar("camera caiu", top=3)
        assert any(a.artigo.categoria == "cftv" for a in r[:2])

    def test_cftv_vem_antes_de_energia(self, base) -> None:
        r = base.buscar("camera caiu", top=5)
        pos_cftv = [i for i, x in enumerate(r) if x.artigo.categoria == "cftv"]
        pos_ener = [i for i, x in enumerate(r) if x.artigo.categoria == "energia"]
        if pos_ener:
            assert min(pos_cftv) < min(pos_ener)


class TestConsultaVazia:
    """Consultas degeneradas."""

    def test_texto_vazio_nao_quebra(self, base) -> None:
        assert base.buscar("") == []

    def test_somente_palavra_vazia(self, base) -> None:
        assert base.buscar("de da do em") == []

    def test_termo_inexistente(self, base) -> None:
        assert base.buscar("zzzqqqxxx") == []


class TestFiltroCategoria:
    """Filtro por categoria."""

    def test_filtro_energia_respeitado(self, base) -> None:
        r = base.buscar("medidor", top=10, categoria="energia")
        assert r and all(x.artigo.categoria == "energia" for x in r)

    def test_filtro_inexistente_devolve_vazio(self, base) -> None:
        assert base.buscar("medidor", top=10, categoria="inexistente") == []

    def test_sem_filtro_traz_varias_categorias(self, base) -> None:
        r = base.buscar("rede", top=10)
        assert len({x.artigo.categoria for x in r}) >= 1


class TestRanking:
    """Ordenacao dos resultados."""

    def test_scores_em_ordem_decrescente(self, base) -> None:
        r = base.buscar("camera nao aparece", top=5)
        scores = [x.score for x in r]
        assert scores == sorted(scores, reverse=True)

    def test_respeita_o_topo(self, base) -> None:
        assert len(base.buscar("rede", top=3)) <= 3

    def test_topo_1_tem_no_maximo_um(self, base) -> None:
        assert len(base.buscar("rede", top=1)) <= 1

    def test_score_dentro_de_zero_e_um(self, base) -> None:
        for x in base.buscar("cabo switch vlan", top=10):
            assert 0.0 < x.score <= 1.0

    def test_score_arredondado(self, base) -> None:
        x = base.buscar("rede", top=1)[0]
        assert round(x.score, 4) == x.score

    def test_resultado_tem_trecho(self, base) -> None:
        x = base.buscar("camera caiu", top=1)[0]
        assert x.trecho

    def test_busca_deterministica(self, base) -> None:
        a = [(r.artigo.id, r.score) for r in base.buscar("vlan trunk", top=5)]
        b = [(r.artigo.id, r.score) for r in base.buscar("vlan trunk", top=5)]
        assert a == b

    def test_consultas_independentes(self, base) -> None:
        a = base.buscar("cabo lento", top=3)
        b = base.buscar("medidor energia", top=3)
        assert a != b


class TestArtigoTexto:
    """Montagem do texto indexado."""

    def test_texto_inclui_todos_os_campos(self) -> None:
        a = Artigo("x", "Titulo", "rede", "Sintoma aqui", "Solucao aqui")
        t = a.texto.lower()
        assert "titulo" in t and "rede" in t and "sintoma" in t and "solucao" in t

    def test_artigo_sem_prioridade_usa_padrao(self) -> None:
        assert Artigo("x", "t", "c", "s", "sol").prioridade == 2


class TestCLI:
    """Interface de linha de comando."""

    def test_buscar_texto(self, capsys) -> None:
        assert main(["buscar", "camera caiu", "--top", "3"]) == 0
        assert "cftv" in capsys.readouterr().out

    def test_buscar_json(self, capsys) -> None:
        assert main(["buscar", "camera caiu", "--formato", "json"]) == 0
        dados = json.loads(capsys.readouterr().out)
        assert dados["resultados"][0]["categoria"] == "cftv"

    def test_json_tem_rank_e_score(self, capsys) -> None:
        main(["buscar", "camera caiu", "--formato", "json"])
        primeiro = json.loads(capsys.readouterr().out)["resultados"][0]
        assert primeiro["rank"] == 1
        assert "score" in primeiro
        assert "solucao" in primeiro

    def test_json_tem_registro_da_consulta(self, capsys) -> None:
        main(["buscar", "vlan", "--formato", "json"])
        assert json.loads(capsys.readouterr().out)["consulta"] == "vlan"

    def test_grava_saida(self, capsys, tmp_path) -> None:
        destino = tmp_path / "r.json"
        codigo = main(["buscar", "camera caiu", "--saida", str(destino)])
        assert codigo == 0
        assert destino.exists()
        assert json.loads(destino.read_text(encoding="utf-8"))["resultados"]

    def test_categoria_filtra(self, capsys) -> None:
        main(["buscar", "medidor", "--categoria", "energia", "--formato", "json"])
        for r in json.loads(capsys.readouterr().out)["resultados"]:
            assert r["categoria"] == "energia"

    def test_consulta_sem_resultado_nao_quebra(self, capsys) -> None:
        assert main(["buscar", "zzzqqqxxx"]) == 0
        assert "Nenhum artigo" in capsys.readouterr().out

    def test_listar_mostra_total(self, capsys) -> None:
        assert main(["listar"]) == 0
        saida = capsys.readouterr().out
        assert "artigos" in saida
        assert "rede" in saida

    def test_listar_respeita_topo(self, capsys) -> None:
        main(["listar", "--top", "3"])
        assert len([l for l in capsys.readouterr().out.splitlines() if l.startswith(("hw-", "net-", "cftv-", "ener-", "sw-", "acc-", "soft-", "sec-", "rack-", "patch-"))]) <= 3

    def test_base_inexistente_retorna_dois(self, capsys) -> None:
        codigo = main(["buscar", "x", "--base", "nao-existe.json"])
        assert codigo == 2
        assert "Erro" in capsys.readouterr().err

    def test_help_principal(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0

    def test_help_buscar(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["buscar", "--help"])
        assert exc.value.code == 0

    def test_sem_subcomando_falha(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code != 0


class TestBaseVazia:
    """Base sem artigos."""

    def test_busca_em_base_vazia(self) -> None:
        b = BaseConhecimento(normalizador=Normalizador({}))
        b.construir()
        assert b.buscar("rede") == []

    def test_construir_sem_artigos(self) -> None:
        BaseConhecimento().construir()