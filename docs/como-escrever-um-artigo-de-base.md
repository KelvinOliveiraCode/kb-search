# Como escrever um artigo de base de conhecimento

O ranking da busca depende inteiramente da qualidade do texto. TF-IDF nao le o
que voce quis dizer - ele conta as palavras que voce escreveu. Este documento e
sobre escrever de um jeito que a contagem funcione.

## A regra que mais importa

**Escreva o sintoma como o usuario falaria, nao como voce tecnicamente chamaria
a coisa.**

| Ruim | Bom |
|---|---|
| "Falha de energia no dispositivo de rede" | "O equipamento apaga sozinho" |
| "Inconsistencia no cache de tabela ARP" | "A rede some e volta sozinha" |
| "Saturacao de buffer de saida" | "A internet fica lenta na hora do video" |

O primeiro texto e preciso. O segundo e o que o usuario digita. Se os dois
artigos forem escritos no primeiro estilo, a busca so funciona para quem
tecnico.

## Estrutura de um artigo

```json
{
  "id": "cftv-001",
  "categoria": "cftv",
  "prioridade": 1,
  "titulo": "Camera IP caiu e nao aparece no NVR",
  "sintoma": "A camera sumiu da lista de dispositivos online no NVR.",
  "solucao": "Teste conectividade no IP da camera com ping..."
}
```

| Campo | Para que serve |
|---|---|
| `id` | Referencia estavel. Nao mude depois de publicado |
| `categoria` | Filtro. Valores: rede, energia, cftv, hardware, software |
| `prioridade` | Desempate. 1 = mais importante |
| `titulo` | Indexado, e o que mais pesa na leitura |
| `sintoma` | O que o usuario observa. **Parte mais indexada** |
| `solucao` | O procedimento. Menos indexada, mas e a resposta |

## O sintoma e o campo que importa

O sintoma entra com peso alto na busca porque e o que o usuario descreve. Ele
precisa:

### Dizer o observavel, nao o diagnostico

Ruim: "Perda de pacote no caminho de retorno" (diagnostico ja pronto)
Bom: "A pagina carrega pela metade e trava" (observavel)

O usuario nao sabe o diagnostico. Se o sintoma describes o diagnostico, o
artigo so aparece para quem ja sabe a resposta.

### Incluir o contexto do equipamento

```json
"sintoma": "A camera sumiu da lista de dispositivos online no NVR.
           Quando acontece: depois que o NVR reinicia."
```

O "quando acontece" e o que diferencia dois artigos com sintoma parecido.
"Caiu" pode ser alimentacao, rede ou NVR.

### Cobrir as palavras que o usuario digita

Escreva o termo tecnico **e** o termo popular:

```json
"sintoma": "O computador trava, congela e a tela fica azul.
           O usuario chama de travamento, congelamento ou tela azul."
```

A lista de palavras no fim do sintoma entra direto no indice. E o truque mais
barato e mais eficiente do documento.

## A solucao e um procedimento, nao uma explicacao

Compare:

Ruim:
> "A causa mais comum e falta de alimentacao PoE no switch, que pode ser
> verificada no lado do switch."

Bom:
> "1. Teste ping no IP da camera a partir de outra maquina da mesma VLAN.
>  2. Sem resposta: e camada fisica. Verifique alimentacao PoE, porta do switch
>     e crimpagem.
>  3. Com resposta mas sem imagem no NVR: o NVR esta em outra subnet sem rota."

O segundo e executavel por alguem que nunca viu aquele equipamento. O primeiro
explica a causa e nao diz o que fazer.

### A solucao tambem e indexada

Nao e so o sintoma que conta. A palavra "ping" na solucao faz o artigo aparecer
para quem busca "nao responde no ping". Escreva a solucao com os termos que o
tecnico usaria no google.

## O que NAO fazer

### Nao repetir o titulo no sintoma

```json
"titulo": "Camera IP caiu e nao aparece no NVR",
"sintoma": "A camera IP caiu e nao aparece no NVR"
```

O titulo ja esta no indice. Repetir infla o TF sem acrescentar nada e faz o
artigo parecer mais relevante do que e. Escreva o sintoma com **outras** palavras.

### Nao escrever artigo de um defeito so

Um artigo por defeito, e nao um artigo com 12 defeitos. O indice e por artigo:
um texto gigante dilui o peso de cada defeito e nao casa bem com nenhuma
consulta especifica.

### Nao usar sigla sem o significado

```json
"sintoma": "Erro de CRC no enlace do barramento"
```

Quem busca "crc" acha. Quem busca "erro de dado corrompido" nao. Use os dois:
"Erro de CRC, que indica dado corrompido no enlace".

### Nao deixar campo vazio

Campo vazio e campo que nao indexa. Este repositorio tem um teste que falha se
qualquer `sintoma` ou `solucao` vier vazio - e ele pegou 4 artigos com
`solucao` faltando antes do primeiro commit.

## Sinonimos: quando a base cresce

Quando comecam a aparecer os mesmos varios artigos resolvendo o mesmo problema,
o mapa de sinonimos precisa crescer:

```yaml
travamento:
  canonico: travamento
  sinonimos:
    - travou
    - congelou
    - travando
    - travado
```

Regra pratica: **so mapeie palavra que o usuario DIGITA, nunca palavra que so o
tecnico usa.** "congelou" entra; "deadlock" nao entra - se o usuario digitasse
"deadlock", ele resolveria sozinho.

E cuidado com sinonimo ambiguo. `azul` parece obvio para "travamento" (tela
azul), e quebra a busca: um artigo que diz "**sem** tela azul" passa a ser
considerado travamento. Sinonimo que vira palavra em contexto negativo nao
serve.

## Como saber se o artigo esta funcionando

Rode a consulta que o usuario provavelmente digitaria:

```powershell
python -m kbsearch buscar "camera caiu" --top 5
```

Se o artigo nao aparece, ou aparece em ultimo:

1. O sintoma tem as palavras que o usuario digita?
2. O titulo repete o sintoma (dilui)?
3. Falta um sinonimo no mapa?

Nao e preciso modelo para diagnosticar isso: le o ranking e ve qual artigo
ganhou e por que palavra.