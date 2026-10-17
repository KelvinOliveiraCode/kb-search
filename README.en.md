![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
![tests](https://img.shields.io/badge/tests-84%20passing-brightgreen?style=flat-square)
![coverage](https://img.shields.io/badge/coverage-98%25-brightgreen?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)

# kb-search

Similarity search over a local knowledge base with TF-IDF written in pure Python, no scikit-learn and no embedding model. Runs offline, downloads nothing.

## Problem / Why it exists

Ticket triage starts with "has this happened before?". When the answer takes long because nobody remembers, the ticket goes back to the queue.

Exact keyword search fails on the first useful sentence: the technician types "froze", the article says "lockup". Embedding search solves this but costs hundreds of MB to download, which does not load on a support station with an unstable link.

kb-search answers with the most relevant procedures from the base using TF-IDF and cosine similarity implemented by hand in pure Python. No ML, nothing to download.

## What it does

- Indexes knowledge base articles (JSON) with a TF-IDF index built from scratch.
- Normalizes the query with a synonym map (YAML), applying the same map on both sides: query and index.
- Expands canonical terms into synonyms, weighting the typed term more than expansion-generated ones, so expansion does not dilute the query.
- Ranks by cosine similarity between the query vector and each article vector.
- Filters by category and returns the symptom snippet matching the query, plus the solution.
- Text or JSON output, writable to a file with `--saida`.

## Stack

- Python 3.10+
- PyYAML (only runtime dependency)
- pytest and pytest-cov (dev)
- Custom implementation: tokenization, TF-IDF with smoothed IDF `ln((N + 1) / (df + 1)) + 1` and cosine similarity — no numpy, no scikit-learn.

## How it works

1. `carregar_base` reads the JSON of articles and the YAML of synonyms, builds `Artigo` objects and constructs the index.
2. Each article becomes a document: title, category, symptom and solution are tokenized, synonyms become canonical terms and the canonical vector is expanded with synonyms.
3. The index keeps term frequency, document frequency (df) and IDF per term.
4. On search, the query goes through the same steps: tokenize, canonicalize, expand. The typed term weighs 4, the generated synonym weighs 1 — weight enters by token repetition, which scales TF, with no magic number in the formula.
5. Query vector (TF-IDF, zero-weight terms discarded) compared by cosine with each article. Results above zero are ordered by descending score, with tiebreak by priority and id.
6. Output: title, category, score, symptom snippet and solution.

Flow: query -> tokenize -> canonicalize -> expand -> weight -> TF-IDF vector -> cosine against each article -> sort.

## How to run

```powershell
# 1. Install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# 2. Validate
python -m pytest tests/ -q

# 3. Execute
python -m kbsearch buscar "camera caiu" --top 5
```

Real output of `buscar "camera caiu" --top 5`

```
Consulta / query: 'camera caiu'
Base: 84 artigos

1. [cftv] Camera IP caiu e nao aparece no NVR  (score 0.3188)
   Trecho: A camera sumiu da lista de dispositivos online no NVR
   Solucao: Teste conectividade no IP da camera com ping a partir de outra maquina da mesma VLAN...

2. [rede] Queda de energia derruba as Cameras IP  (score 0.2899)
   Trecho: Apos retorno de energia, parte das cameras nao volta a transmitir.
   Solucao: Verifique a alimentacao PoE. Camera com fonte propria volta em segundos...

3. [cftv] Porta aberta por forca na madrugada  (score 0.0853)
```

Other commands

```powershell
python -m kbsearch listar
python -m kbsearch buscar "vlan" --categoria rede --top 3
python -m kbsearch buscar "camera caiu" --formato json --saida exemplos/resultados-busca.json
```

Acceptance criterion, verified in test

```powershell
python -m kbsearch buscar "travando"   # froze returns the same top 1
python -m kbsearch buscar "congelou"
```

## Project structure

```
kb-search/
  pyproject.toml       project, kbsearch entry point, pytest
  requirements.txt     PyYAML, pytest, pytest-cov
  src/kbsearch/
    __init__.py        public API and version
    __main__.py        allows python -m kbsearch
    cli.py             command line interface (buscar, listar)
    indexador.py       tokenization, TF-IDF index, cosine similarity
    normalizacao.py    synonym map, Normalizador
    busca.py           Artigo, BaseConhecimento, Resultado, carregar_base
  dados/
    base-conhecimento.json  84 articles, 5 categories (cftv, energia, hardware, rede, software)
    sinonimos.yaml     8 synonym groups
  docs/
    como-busca-por-similaridade-funciona.md
    como-escrever-um-artigo-de-base.md
  exemplos/            real search and listing outputs
  tests/               84 tests
```

## Trade-offs and decisions

Pure TF-IDF instead of embeddings — no hundreds-of-MB download, runs offline on any station with Python. The cost is understanding only words, not phrases or intent.

Smoothed IDF with +1 — without the `+ 1` in the logarithm, a term present in all documents gets IDF zero and drops out of the search. Common words in the base ("cabo", "camera") would not dominate the ranking without smoothing.

Synonym applied on both sides — index and query pass through the same normalizer. Normalizing only the query failed on the inverse case (article with "travou", search for "travando" found nothing).

Weight by repetition — the typed term weighs 4 and the generated synonym weighs 1. Weight enters by token repetition, which scales TF — no magic number in the formula.

Zero-IDF terms discarded from the query — they would keep weight in the sum without participating in similarity and would still reduce the vector norm.

Ambiguous synonym mapping removed — `azul` mapped to `travamento` made an article with "sem tela azul" count as lockup. TF-IDF does not read negation.

Tiebreak by priority and id — two equally relevant solutions tie on score; the tiebreak is `prioridade` and `id`, not "which resolves faster".

## Known limitations

Does not understand unmapped synonyms. "Geladeira quebrada" does not find "refrigerador com defeito" without that mapping in the YAML.

Does not read negation. "sem tela azul" matches "tela azul". It is a limit of the counting model, not the implementation.

No semantic embedding. Zero ML, zero download — and also zero sentence understanding.

Word search, not concept search. "SLA quebrado" only finds an article containing those two words.

Ranking is lexical. Two equally relevant solutions tie, and the tiebreak goes by `prioridade` and `id`.

84-article base. Behavior changes with volume: with 5 articles everything matches, with 500 IDF really matters. Tuning was not done for large bases.

## License

MIT. See [LICENSE](LICENSE).

## Author

Kelvin Oliveira

https://github.com/KelvinOliveiraCode

https://kelvinoliveiracode.github.io/portfolio/
