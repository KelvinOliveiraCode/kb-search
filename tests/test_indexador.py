"""Testes do indice TF-IDF e da normalizacao de sinonimos.

Tests for the TF-IDF index and synonym normalisation.
"""

from __future__ import annotations

import math

import pytest

from kbsearch.indexador import (
    STOPWORDS,
    Indice,
    similaridade,
    tokenizar,
)
from kbsearch.normalizacao import Normalizador, carregar_sinonimos, padraes_padrao


class TestTokenizacao:
    """Quebra de texto em tokens."""

    def test_minusculas_e_separacao(self) -> None:
        assert tokenizar("Rede Lenta no Andar") == ["rede", "lenta", "andar"]

    def test_palavra_vazia_removida(self) -> None:
        assert "de" not in tokenizar("falha de leitura no disco")

    def test_unicode_removido(self) -> None:
        tokens = tokenizar("cabeamento, cabos; switch")
        assert "," not in tokens and ";" not in tokens

    def test_token_de_uma_letra_removido(self) -> None:
        assert "a" not in tokenizar("a rede caiu")

    def test_vazio_retorna_lista_vazia(self) -> None:
        assert tokenizar("") == []

    def test_somente_palavra_vazia_retorna_vazia(self) -> None:
        assert tokenizar("de da do em no") == []

    def test_stopwords_tem_ingles_e_portugues(self) -> None:
        assert "the" in STOPWORDS and "de" in STOPWORDS


class TestIndice:
    """Construcao do indice."""

    def test_indice_conta_documentos(self) -> None:
        i = Indice()
        i.adicionar("a", "texto de rede")
        i.adicionar("b", "texto de energia")
        assert len(i) == 2

    def test_indice_vazio(self) -> None:
        assert len(Indice()) == 0

    def test_idf_de_termo_em_todos_os_docs_nao_e_zero(self) -> None:
        # Forma suavizada: termo comum tem IDF > 0, senao some da busca.
        i = Indice()
        for n in range(4):
            i.adicionar(str(n), "cabo de rede estruturado")
        i.construir()
        assert i.idf["cabo"] > 0.0

    def test_idf_cresce_com_raridade(self) -> None:
        # Com pocos documentos, todo termo tem o mesmo df e o IDF empata.
        # A diferenca so aparece quando um termo aparece em menos documentos.
        i = Indice()
        i.adicionar("a", "cabo de rede")
        i.adicionar("b", "cabo de rede")
        i.adicionar("c", "cabo de rede")
        i.adicionar("d", "fibra otica")
        i.construir()
        assert i.idf["fibra"] > i.idf["rede"]

    def test_idf_empata_quando_df_igual(self) -> None:
        i = Indice()
        i.adicionar("a", "cabo")
        i.adicionar("b", "fibra")
        i.construir()
        assert math.isclose(i.idf["cabo"], i.idf["fibra"], rel_tol=1e-9)

    def test_construir_em_indice_vazio_nao_quebra(self) -> None:
        i = Indice()
        i.construir()
        assert i.idf == {}

    def test_vetor_normalizado(self) -> None:
        i = Indice()
        i.adicionar("a", "rede lenta no switch do andar")
        i.construir()
        v = i.vetor(0)
        assert math.isclose(math.sqrt(sum(x * x for x in v.values())), 1.0, rel_tol=1e-9)

    def test_vetor_de_documento_vazio(self) -> None:
        i = Indice()
        i.adicionar("a", "!!! ???")
        i.construir()
        assert i.vetor(0) == {}

    def test_indice_fora_da_falha_levanta_indexerror(self) -> None:
        i = Indice()
        i.adicionar("a", "rede")
        i.construir()
        with pytest.raises(IndexError):
            i.vetor(9)

    def test_vetor_consulta_vazio(self) -> None:
        i = Indice()
        i.adicionar("a", "rede")
        i.construir()
        assert i.vetor_consulta("") == {}

    def test_vetor_consulta_descarta_termo_inexistente(self) -> None:
        i = Indice()
        i.adicionar("a", "rede lenta")
        i.construir()
        v = i.vetor_consulta("xyzinexistente")
        assert v == {}


class TestSimilaridade:
    """Cosseno a mao."""

    def test_vetores_iguais_dao_um(self) -> None:
        v = {"a": 0.6, "b": 0.8}
        assert math.isclose(similaridade(v, dict(v)), 1.0, rel_tol=1e-9)

    def test_vetores_disjuntos_dao_zero(self) -> None:
        assert similaridade({"a": 1.0}, {"b": 1.0}) == 0.0

    def test_vetor_vazio_da_zero(self) -> None:
        assert similaridade({}, {"a": 1.0}) == 0.0

    def test_ordem_dos_termos_nao_altera(self) -> None:
        a = {"x": 0.5, "y": 0.5}
        b = {"y": 0.5, "x": 0.5}
        assert similaridade(a, b) == similaridade(b, a)

    def test_cosseno_presupoe_vetor_normalizado(self) -> None:
        # A funcao e produto escalar puro: os vetores chegam normalizados do
        # Indice. Sem normalizar, o valor sai fora de 0..1 - e isso contrato
        # documentado, nao bug. O indice e quem garante a normalizacao.
        a = {"x": 0.6, "y": 0.8}
        b = {"x": 0.6, "y": 0.8}
        assert similaridade(a, b) == pytest.approx(1.0)

        nao_normalizado = {"x": 3.0, "y": 4.0}
        assert similaridade(nao_normalizado, b) > 1.0

    def test_cossino_preserva_sinal(self) -> None:
        # Vetores normalizados: resultado entre 0 e 1.
        a = {"x": 0.6, "y": 0.8}
        b = {"x": 0.6, "y": 0.8}
        assert 0.0 <= similaridade(a, b) <= 1.0


class TestNormalizador:
    """Mapeamento de sinonimos."""

    def test_canonico_substitui_sinonimo(self) -> None:
        n = Normalizador({"congelou": "travamento"})
        assert n.canonico("congelou") == "travamento"

    def test_termo_sem_mapeamento_volta_igual(self) -> None:
        n = Normalizador({"congelou": "travamento"})
        assert n.canonico("rede") == "rede"

    def test_aplicar_funde_sinonimos(self) -> None:
        n = Normalizador({"travou": "travamento", "congelou": "travamento"})
        assert n.aplicar(["travou", "congelou"]) == ["travamento"]

    def test_aplicar_remove_duplicatas(self) -> None:
        n = Normalizador({})
        assert n.aplicar(["rede", "rede", "cabo"]) == ["rede", "cabo"]

    def test_expandir_devolve_sinonimos_do_canonico(self) -> None:
        n = Normalizador({"congelou": "travamento"})
        assert "congelou" in n.expandir(["travamento"])

    def test_expandir_preserva_o_canonico(self) -> None:
        n = Normalizador({"congelou": "travamento"})
        assert "travamento" in n.expandir(["travamento"])

    def test_expandir_de_canonico_sem_sinonimo(self) -> None:
        n = Normalizador({})
        assert n.expandir(["rede"]) == ["rede"]

    def test_mapas_padrao_carregam(self) -> None:
        m = padraes_padrao()
        assert m["congelou"] == "travamento"
        assert m["caiu"] == "queda"


class TestCarregarSinonimos:
    """Leitura do YAML de sinonimos."""

    def test_carrega_mapa(self, tmp_path) -> None:
        p = tmp_path / "s.yaml"
        p.write_text(
            "travamento:\n  canonico: travamento\n  sinonimos:\n    - travou\n",
            encoding="utf-8",
        )
        assert carregar_sinonimos(p) == {"travou": "travamento"}

    def test_carrega_varios_grupos(self, tmp_path) -> None:
        p = tmp_path / "s.yaml"
        p.write_text(
            "a:\n  canonico: x\n  sinonimos:\n    - p\n"
            "b:\n  canonico: y\n  sinonimos:\n    - q\n",
            encoding="utf-8",
        )
        m = carregar_sinonimos(p)
        assert m == {"p": "x", "q": "y"}

    def test_grupo_sem_canonico_e_ignorado(self, tmp_path) -> None:
        p = tmp_path / "s.yaml"
        p.write_text("a:\n  sinonimos:\n    - p\n", encoding="utf-8")
        assert carregar_sinonimos(p) == {}

    def test_formato_compacto_em_lista(self, tmp_path) -> None:
        p = tmp_path / "s.yaml"
        p.write_text("a:\n  - canonico\n  - sinon1\n  - sinon2\n", encoding="utf-8")
        m = carregar_sinonimos(p)
        assert m == {"sinon1": "canonico", "sinon2": "canonico"}

    def test_yaml_sem_mapa_levanta_valueerror(self, tmp_path) -> None:
        p = tmp_path / "s.yaml"
        p.write_text("- apenas\n- uma\n- lista\n", encoding="utf-8")
        with pytest.raises(ValueError, match="mapeamento"):
            carregar_sinonimos(p)

    def test_arquivo_inexistente_levanta_oserror(self) -> None:
        with pytest.raises(OSError):
            carregar_sinonimos("nao-existe.yaml")