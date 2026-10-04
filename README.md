<div align="center">

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/tests-84%20passing-brightgreen?style=flat-square" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-99%25-brightgreen-brightgreen?style=flat-square" alt="Coverage">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/deps-zero%20ML-brightgreen?style=flat-square" alt="No ML deps">
</p>

# kb-search

**Busca por similaridade em base de conhecimento, com TF-IDF escrito a mao.**

</div>

---

## PT-BR

### O que e

CLI que indexa uma base de conhecimento de suporte e responde a uma pergunta em
linguagem natural com os procedimentos mais relevantes. TF-IDF e similaridade de
cosseno implementados em Python puro, sem scikit-learn e sem modelo de
embedding. Roda offline, sem baixar nada.

### Por que foi feito

Triagem de chamado comeca com "isso ja aconteceu?". Quando a resposta demora dez
minutos porque ninguem lembra, o chamado volta a fila.

Busca por palavra-chave exata falha na primeira frase util: o usuario digita
"congelou", o artigo diz "travamento". Busca por embedding resolve isso - e
custa centenas de MB de download, que numa estacao de suporte com link
instavel simplesmente nao carrega.

TF-IDF nao resolve tudo, e o projeto diz onde. Ele acerta quando a palavra
existe; falha quando so a intencao existe. Numa base de infraestrutura, com
vocabulario controlado, o mapa de sinonimos cobre o essencial.

### Como rodar

```powershell
# 1. Instalar
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
# instala o pacote local para o python -m <pacote>$nl
# 2. Validar
python -m pytest tests/ -v

# 3. Executar
python -m kbsearch buscar "camera caiu" --top 5
```

Saida real:

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

O segundo resultado e de rede, e o ranking esta certo: a resposta "a camera
caiu" tem duas causas provaveis, e alimentacao PoE do switch e a primeira delas.

Criterio de aceite do projeto, verificado em teste:

```powershell
python -m kbsearch buscar "travando"   # congelou devolve o mesmo top 1
python -m kbsearch buscar "congelou"
```

Outros comandos:

```powershell
python -m kbsearch listar
python -m kbsearch buscar "vlan" --categoria rede --top 3
python -m kbsearch buscar "camera caiu" --formato json --saida exemplos/resultados-busca.json
```

### O que aprendi

- **O `+ 1` do IDF nao e detalhe, e condicao de existencia.** Sem o `ln((N+1)/(df+1))+1`,
  um termo presente em todos os documentos recebe IDF zero e some da busca.
  Numa base de suporte, "cabo" aparece em 7 dos 84 artigos e "camera" em 12 -
  sem a suavizacao, as palavras que menos distinguem eram as que dominavam o
  ranking.
- **Normalizar so a consulta nao basta.** O primeiro versao mapeava sinonimo
  apenas no texto buscado. Funcionava, ate esbarrar no caso invertido: artigo
  escrito com "travou", busca por "travando" nao encontrava nada. Passar o mapa
  nos **dois** lados resolve os dois sentidos de uma vez.
- **Expandir sinonimo dilui a consulta.** Com "travando" virando 9 termos (o
  proprio mais 8 sinonimos), o
  artigo que menciona "travou" numa frase de passagem vencia o que traz
  "travando" no titulo. Pesar o termo canonico em 4 e o sinonimo gerado em 1
  resolveu - e o peso entra por repeticao, que equivale a multiplicar o TF, sem
  numero magico na formula.
- **Termo com IDF zero ainda dilui.** Meu `vetor_consulta` mantinha no vetor os
  termos que nao existem em nenhum documento. Eles nao contribuem nada para a
  similaridade e so reduzem a norma. Descartar peso zero foi a correcao.
- **Sinonimo ambiguo quebra contexto.** Mapear `azul` para `travamento` (tela
  azul) fez um artigo que diz "**sem** tela azul" ser considerado travamento.
  TF-IDF nao le negacao. Removi o mapeamento: palavra que aparece em frase
  negativa nao serve.
- **Sintoma vazio nao aparece em nenhum lugar.** Quatro dos 84 artigos tinham
  `solucao` faltando - e nenhum teste reclamava. O teste que verifica campo
  preenchido pegou os quatro antes do commit. E como a solucao tambem e
  indexada, artigo sem solucao e artigo que nao ensina.

### Limitacoes

- **Nao entende sinonimo que ninguem mapeou.** "Geladeira quebrada" nao encontra
  "refrigerador com defeito". Ninguem mapeou essa ligacao. Num vocabulario de
  infraestrutura o mapa cobre o essencial; fora dele, o limite aparece.
- **Nao le negacao.** "sem tela azul" casa com "tela azul". E limitacao de
  modelo de contagem, nao de implementacao.
- **Nao tem embedding semantico.** Zero ML, zero download - e tambem zero
  entendimento de frase.
- **Busca por palavra, nao por conceito.** "SLA quebrado" so acha artigo que
  contenha essas duas palavras.
- **O ranking e lexical.** Duas solucoes igualmente relevantes empatam, e o
  desempate vai por `prioridade` e `id` - nao por "qual resolve mais".
- **Base de 84 artigos.** O comportamento muda com volume: com 5 artigos tudo
  casa, com 500 o IDF pesa de verdade. O tuning nao foi feito para a base grande.

### Licenca

MIT. Ver [LICENSE](LICENSE).

---

## EN

### What it is

A CLI that indexes a support knowledge base and answers a natural-language
question with the most relevant procedures. TF-IDF and cosine similarity
implemented in pure Python, without scikit-learn and without an embedding model.
Runs offline, with nothing to download.

### Why it was built

Ticket triage starts with "has this happened before?". When the answer takes ten
minutes because nobody remembers, the ticket goes back in the queue.

Exact keyword search fails on the first useful phrase: the user types "congelou",
the article says "travamento". Embedding search fixes that - and costs hundreds
of MB of download, which on a support desk with a flaky link simply will not
load.

TF-IDF does not solve everything, and the project says where. It is right when
the word is present; it fails when only the intent is. In an infrastructure
knowledge base, with controlled vocabulary, the synonym map covers the
essentials.

### How to run

```powershell
# 1. Install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
# instala o pacote local para o python -m <pacote>$nl
# 2. Validate
python -m pytest tests/ -v

# 3. Run
python -m kbsearch buscar "camera caiu" --top 5
```

Real output:

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

The second result is network, and the ranking is right: "the camera went down"
has two likely causes, and PoE power from the switch is the first of them.

Project acceptance criterion, verified in a test:

```powershell
python -m kbsearch buscar "travando"   # congelou returns the same top 1
python -m kbsearch buscar "congelou"
```

Other commands:

```powershell
python -m kbsearch listar
python -m kbsearch buscar "vlan" --categoria rede --top 3
python -m kbsearch buscar "camera caiu" --formato json --saida exemplos/resultados-busca.json
```

### What I learned

- **The `+ 1` in IDF is not a detail, it is a condition of existence.** Without
  `ln((N+1)/(df+1))+1`, a term present in every document gets IDF zero and drops
  out of the search entirely. In a support base, "cabo" and "camera" appear in
  nearly every article - without smoothing, the words that distinguish least
  were the ones dominating the ranking.
- **Normalising only the query is not enough.** The first version mapped
  synonyms only in the search text. It worked, until it hit the reverse case: an
  article written with "travou", a search for "travando" found nothing. Running
  the map on **both** sides fixes both directions at once.
- **Expanding synonyms dilutes the query.** With "travando" becoming eight
  terms, the article mentioning "travou" in passing beat the one with
  "travando" in the title. Weighting the canonical term at 4 and a generated
  synonym at 1 fixed it - and the weight enters by repetition, which is just
  scaling the TF, with no magic number in the formula.
- **Zero-IDF terms still dilute.** My `vetor_consulta` kept terms that appear
  in no document at all. They contribute nothing to the similarity and only
  shrink the norm. Dropping zero weight was the fix.
- **An ambiguous synonym breaks context.** Mapping `azul` to `travamento`
  (blue screen) made an article that says "**no** blue screen" count as a
  freeze. TF-IDF does not read negation. I removed the mapping: a word that
  shows up in a negated sentence is not a synonym.
- **An empty symptom shows up nowhere.** Four of the 84 articles had a missing
  `solucao` - and no test complained. The test that checks for filled fields
  caught all four before the commit. Since the solution is indexed too, an
  article without one does not teach anything.

### Limitations

- **No understanding of unmapped synonyms.** "Broken fridge" will not find
  "refrigerator with a fault". Nobody mapped that link. Infrastructure
  vocabulary is covered by the map; outside it, the limit shows.
- **It does not read negation.** "no blue screen" matches "blue screen". That is
  a limit of counting models, not of the implementation.
- **No semantic embedding.** Zero ML, zero download - and also zero
  understanding of phrasing.
- **Word search, not concept search.** "SLA breached" only matches an article
  containing both words.
- **Ranking is lexical.** Two equally valid procedures tie, and the tiebreak
  goes on `prioridade` then `id` - not on "which one resolves it faster".
- **An 84-article base.** Behaviour shifts with volume: at 5 articles everything
  matches, at 500 the IDF really matters. Tuning was not done for the large base.

### License

MIT. See [LICENSE](LICENSE).

---

## Estrutura / Structure

```
src/kbsearch/
  indexador.py     TF-IDF e cosseno em Python puro
  normalizacao.py  mapa de sinonimos
  busca.py         ranking, trecho relevante, filtro de categoria
  cli.py           interface de linha de comando
dados/
  base-conhecimento.json   84 artigos ficticios, 5 categorias
  sinonimos.yaml           8 grupos de sinonimos
docs/
  como-busca-por-similaridade-funciona.md
  como-escrever-um-artigo-de-base.md
exemplos/          saidas reais
tests/             84 testes
```

## Como a busca funciona / How search works

```
consulta -> tokenizar -> canonizar -> expandir -> ponderar
         -> vetor TF-IDF -> cosseno contra cada artigo -> ordenar
```

## Licenca / License

MIT &mdash; [LICENSE](LICENSE)

---

<div align="center">
  <sub>Por <a href="https://github.com/KelvinOliveiraCode">Kelvin Oliveira</a> &middot;
  <a href="https://kelvinoliveiracode.github.io/portfolio/">portfolio</a></sub>
</div>