![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
![testes](https://img.shields.io/badge/testes-84%20passando-brightgreen?style=flat-square)
![cobertura](https://img.shields.io/badge/cobertura-98%25-brightgreen?style=flat-square)
![licenca](https://img.shields.io/badge/licenca-MIT-yellow?style=flat-square)

# kb-search

Busca por similaridade em base de conhecimento local com TF-IDF escrito em Python puro, sem scikit-learn e sem modelo de embedding. Roda offline, sem baixar nada.

## Problema / Por que existe

Triagem de chamado começa com "isso já aconteceu?". Quando a resposta demora porque ninguém se lembra, o chamado volta à fila.

Busca por palavra-chave exata falha na primeira frase útil: o técnico digita "congelou", o artigo diz "travamento". Busca por embeddings resolve isso, mas custa centenas de MB de download, o que não carrega numa estação de suporte com link instável.

O kb-search responde com os procedimentos mais relevantes da base usando TF-IDF e similaridade de cosseno implementados à mão em Python puro. Nada de ML, nada para baixar.

## O que faz

- Indexa artigos de uma base de conhecimento (JSON) com um índice TF-IDF construído do zero.
- Normaliza a consulta com um mapa de sinônimos (YAML), aplicando o mesmo mapa nos dois lados: consulta e índice.
- Expande termos canônicos em sinônimos, pesando o termo digitado mais que os gerados por expansão, para a expansão não diluir a consulta.
- Ranqueia por similaridade de cosseno entre o vetor da consulta e o vetor de cada artigo.
- Filtra por categoria e devolve o trecho do sintoma que casa com a consulta, mais a solução.
- Saída em texto ou JSON, gravável em arquivo com `--saida`.

## Stack

- Python 3.10+
- PyYAML (única dependência de runtime)
- pytest e pytest-cov (dev)
- Implementação própria: tokenização, TF-IDF com IDF suavizado `ln((N + 1) / (df + 1)) + 1` e similaridade de cosseno — sem numpy, sem scikit-learn.

## Como funciona

1. `carregar_base` lê o JSON de artigos e o YAML de sinônimos, monta objetos `Artigo` e constrói o índice.
2. Cada artigo vira um documento: título, categoria, sintoma e solução são tokenizados, os sinônimos viram termos canônicos e o vetor canônico é expandido com sinônimos.
3. O índice guarda frequência de termos, frequência de documentos (df) e IDF por termo.
4. Na busca, a consulta passa pelos mesmos passos: tokenizar, canonizar, expandir. O termo digitado pesa 4, o sinônimo gerado pesa 1 — o peso entra por repetição do token, que escala o TF, sem número mágico na fórmula.
5. Vetor da consulta (TF-IDF, termos com peso zero descartados) comparado por cosseno com cada artigo. Resultados acima de zero são ordenados por score decrescente, com desempate por prioridade e id.
6. Saída: título, categoria, score, trecho do sintoma e solução.

Fluxo: consulta -> tokenizar -> canonizar -> expandir -> ponderar -> vetor TF-IDF -> cosseno contra cada artigo -> ordenar.

## Como rodar

```powershell
# 1. Instalar
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# 2. Validar
python -m pytest tests/ -q

# 3. Executar
python -m kbsearch buscar "camera caiu" --top 5
```

Saída real:

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

Outros comandos:

```powershell
python -m kbsearch listar
python -m kbsearch buscar "vlan" --categoria rede --top 3
python -m kbsearch buscar "camera caiu" --formato json --saida exemplos/resultados-busca.json
```

Critério de aceite, verificado em teste:

```powershell
python -m kbsearch buscar "travando"   # congelou devolve o mesmo top 1
python -m kbsearch buscar "congelou"
```

## Estrutura do projeto

```
kb-search/
  pyproject.toml       projeto, ponto de entrada kbsearch, pytest
  requirements.txt     PyYAML, pytest, pytest-cov
  src/kbsearch/
    __init__.py        API pública e versão
    __main__.py        permite python -m kbsearch
    cli.py             interface de linha de comando (buscar, listar)
    indexador.py       tokenizacao, índice TF-IDF, similaridade de cosseno
    normalizacao.py    mapa de sinonimos, Normalizador
    busca.py           Artigo, BaseConhecimento, Resultado, carregar_base
  dados/
    base-conhecimento.json  84 artigos, 5 categorias (cftv, energia, hardware, rede, software)
    sinonimos.yaml     8 grupos de sinonimos
  docs/
    como-busca-por-similaridade-funciona.md
    como-escrever-um-artigo-de-base.md
  exemplos/            saidas reais de busca e listagem
  tests/               84 testes
```

## Trade-offs e decisões

- **TF-IDF puro em vez de embeddings:** sem download de centenas de MB, roda offline em qualquer estação com Python. O custo é entender apenas palavras, não frases nem intenção.
- **IDF suavizado com +1:** sem o `+ 1` no logaritmo, um termo presente em todos os documentos recebe IDF zero e some da busca. Palavras comuns na base ("cabo", "camera") não dominariam o ranking sem a suavização.
- **Sinônimo aplicado nos dois lados:** índice e consulta passam pelo mesmo normalizador. Normalizar só a consulta falhava no caso inverso (artigo com "travou", busca por "travando" não encontrava nada).
- **Peso por repetição:** o termo digitado pesa 4 e o sinônimo gerado pesa 1. O peso entra por repetição do token, que escala o TF — sem número mágico na fórmula.
- **Termos com IDF zero descartados da consulta:** manteriam peso na soma sem participar da similaridade e ainda reduziriam a norma do vetor.
- **Mapeamento de sinônimo ambíguo removido:** `azul` para `travamento` fazia artigo com "sem tela azul" contar como travamento. TF-IDF não lê negação.
- **Desempate por prioridade e id:** duas soluções igualmente relevantes empatam no score; o desempate é por `prioridade` e `id`, não por "qual resolve mais rápido".

## Limitações conhecidas

- Não entende sinônimo que ninguém mapeou. "Geladeira quebrada" não acha "refrigerador com defeito" sem esse mapeamento no YAML.
- Não lê negação. "sem tela azul" casa com "tela azul". É limite do modelo de contagem, não da implementação.
- Não tem embedding semântico. Zero ML, zero download — e também zero entendimento de frase.
- Busca por palavra, não por conceito. "SLA quebrado" só acha artigo que contenha essas duas palavras.
- O ranking é lexical. Duas soluções igualmente relevantes empatam, e o desempate vai por `prioridade` e `id`.
- Base de 84 artigos. O comportamento muda com volume: com 5 artigos tudo casa, com 500 o IDF pesa de verdade. O tuning não foi feito para base grande.

## Licença

MIT. Ver [LICENSE](LICENSE).

## Autor

Kelvin Oliveira

https://github.com/KelvinOliveiraCode

https://kelvinoliveiracode.github.io/portfolio/
