# Como busca por similaridade funciona

Este documento explica TF-IDF e similaridade de cosseno sem matematica
avancada, e responde a pergunta que importa: **por que isso funciona sem modelo
de IA**.

## O problema

O tecnico digita "travando". O artigo se chama "Estacao de trabalho travando e
reiniciando sozinha". A palavra esta la. E trivial, certo?

Nao. Tres problemas aparecem na hora:

1. **A palavra exata nem sempre esta.** Quem escreve o artigo diz "travou".
   Quem busca diz "travando". Quem atende o telefone ouve "congelou".
2. **Nem toda palavra que coincide significa algo.** "Camera caiu" e "papel caiu"
   tem "caiu" em comum. A palavra comum nao distingue nada.
3. **Algumas palavras distinguem demais.** O id `hw-001` aparece em 84 artigos,
   se indexado, e nao distingue nada tambem - mas o contrario tambem vale:
   "hidraulica" num so artigo diz muita coisa.

TF-IDF resolve os tres.

## Passo 1 - Quebrar em palavras

"Tela travada no computador" vira `tela`, `travada`, `computador`. Minusculas,
sem pontuacao, sem palavra vazia. Palavra vazia (de, da, em, no) sai fora: nao
distingue nada e aparece em todo texto.

## Passo 2 - TF: quantas vezes aparece no documento

TF e a frequencia do termo no documento. "cabo" aparecendo 5 vezes num artigo de
50 palavras tem TF alto.

Mas TF sozinho e ruim: um artigo longo repete palavras naturalmente, e o
artigo mais longo ganha por ser longo, nao por ser relevante.

## Passo 3 - IDF: o peso de "raridade"

IDF (Inverse Document Frequency) e a parte que resolve o problema 2 e o 3.

```
IDF = ln((N + 1) / (df + 1)) + 1
```

- `N` = total de documentos
- `df` = quantos documentos contem o termo

Termo em **todos** os documentos: `df = N`, IDF baixo. Ele nao distingue nada,
entao pesa pouco. E o caso de "camera", "sistema", "rede".

Termo em **um** documento: `df = 1`, IDF alto. Ele distingue muito, entao pesa
muito.

### Por que o `+ 1`

Sem o `+ 1` do log, um termo presente em todos os documentos recebe IDF
exatamente zero - e some da busca. Numa base de conhecimento, "cabo" e "camera"
aparecem em quase todo artigo. Sem a suavizacao, esses termos, que nao
distinguem nada, dominariam o ranking.

A forma suavizada `ln((N+1)/(df+1)) + 1` nunca da zero. Foi a escolha que fez
este repositorio funcionar.

## Passo 4 - TF-IDF: peso do termo no documento

```
peso(termo) = TF(termo) x IDF(termo)
```

Depois o vetor inteiro e normalizado para norma 1 (divide pela raiz da soma dos
quadrados). A normalizacao e o que permite comparar documentos de tamanhos
diferentes: um artigo de 40 palavras e um de 400 viram vetores na mesma escala.

## Passo 5 - Similaridade de cosseno

Coseno entre dois vetores normalizados e o produto escalar:

```
cos(A, B) = soma(A[i] * B[i]) para os termos em comum
```

Valor perto de 1: os documentos falam da mesma coisa.
Valor perto de 0: nao tem relacao.

Como os vetores ja vem normalizados, o cosseno degenera em produto escalar - e
por isso o codigo faz so a soma. **Pre-condicao:** os vetores tem que estar
normalizados. Se voce chamar `similaridade` direto com vetor nao normalizado,
o resultado sai fora do intervalo 0 a 1.

## Passo 6 - Sinonimos: onde o problema 1 aparece

TF-IDF so compara **palavra por palavra**. Ele nao sabe que "congelou" e
"travando" significam a mesma coisa.

E por isso que existe `normalizacao.py`. Um mapa leva varias palavras ao mesmo
termo canonico:

```
travou, congelou, travado, travando  ->  travamento
```

E o mapa e aplicado **dos dois lados**:

- na consulta, quem busca digita "congelou" e vira "travamento"
- no documento, quem escreveu "travamento" ganha tambem "congelou" e "travou"

Aplicar dos dois lados e essencial. Aplicar so na consulta funciona ate esbarrar
no caso inverso: artigo escrito com "travou", busca por "travando". Com os dois
lados normalizados, qualquer palavra do grupo encontra qualquer artigo do grupo.

## Passo 7 - Peso do que o usuario digitou

Expandir sinonimos tem custo: "travando" vira oito termos. Se todos valerem
igual, a consulta se dilui e um artigo que menciona "travou" numa frase de
passagem ganha de outro que traz "travando" no **titulo**.

Por isso o peso:

| Termo | Peso | Por que |
|---|---|---|
| Canonico de palavra digitada | 4 | O usuario pediu sinonimo |
| Palavra digitada | 2 | O que ele realmente escreveu |
| Sinonimo gerado | 1 | Variacao, nao intencao |

O peso entra por repeticao no texto da consulta, que equivale a multiplicar o
TF - e o TF e exatamente onde o peso entra. Sem numero magico: e a mesma conta.

## Por que isso funciona sem modelo de IA

Um modelo de embedding e uma rede neural treinada com centenas de milhoes de
frases que converte texto em vetor. Ele entende que "geladeira" e "torradeira"
sao coisas da mesma cozinha, sem ninguem ensinar a regra.

TF-IDF nao entende nada disso. Ele compara palavra por palavra. O que ele faz e
contar, e o counting funciona bem **quando o vocabulario e controlado**, que e
exatamente o caso de uma base de conhecimento de suporte.

| | Embedding | TF-IDF |
|---|---|---|
| Entende sinonimo que ninguem mapeou | sim | nao |
| Entende "geladeira" e "torradeira" | sim | nao |
| Download | centenas de MB | zero |
| Explicacao | dificeis de auditar | a conta |
| Ajuste ao dominio | precisa re-treinar | so editar o mapa |

O que o TF-IDF **nao** faz: encontrar "geladeira quebrada" se o artigo fala em
"refrigerador com defeito". Ninguem mapeou essa ligacao. Num banco de 84
artigos com vocabulario de infraestrutura, o mapa cobre o essencial - e o que
nao cobre, o tecnico adiciona em uma linha.

**A honestidade do limite:** TF-IDF acerta quando a palavra existe. Falha quando
so a intencao existe. Embedding acerta os dois e custa 500 MB. A escolha
depende do tamanho da base e do controle do vocabulario.

## Por que a base tem 84 artigos

Com 5 artigos, qualquer busca funciona - nao ha o que distinguir. Com 500, o
IDF comeca a importar de verdade. Com 84 e 5 categorias, ja da para ver o
comportamento: "camera caiu" traz o artigo de CFTV no topo, e o de rede aparece
em segundo porque a Camera IP depende de alimentacao PoE do switch. Esse
segundo lugar e o resultado honesto: a resposta existe nos dois artigos, e o
ranking mostra qual e mais especifico.

## Referencia rapida

| Conceito | Formula | O que resolve |
|---|---|---|
| TF | contagem do termo no documento | "ele aparecia muito aqui" |
| IDF | `ln((N+1)/(df+1)) + 1` | "ele distingue pouco ou muito" |
| TF-IDF | TF x IDF | peso final do termo |
| Cosseno | soma do produto dos termos em comum | "falamos da mesma coisa" |