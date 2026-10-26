# Registro do experimento

Cenário: Render Jobs API, uma API FastAPI de geração de imagens com três pontos de integração (cliente REST, Provedor externo por HTTP com retentativas e webhook assinado, banco SQLite com débito e reembolso de créditos). Contrato em `docs/contrato.md`.

LLM usada para gerar os testes: Claude. O Provedor é simulado com `httpx.MockTransport`, a API usa o cliente HTTP real e o banco é SQLite em memória.

## Linha do tempo

1. Escrevi o contrato (R01 a R24) antes de qualquer teste ou código.
2. Prompt 1, versão 1 (`prompts/p1_contrato.md`): gerou 71 testes a partir do contrato e das fixtures. Os testes foram escritos antes da API existir. Quando a API ficou pronta, os 71 passaram na primeira execução.
3. Teste de mutação sobre a v1 (`experimento/mutantes.py`): 32 defeitos injetados nessa etapa, 22 detectados.
4. Prompt 1, versão 2: acrescentei os critérios de qualidade ao prompt. Gerou mais 28 testes. Com a v1, a suíte detecta 30 dos 34 mutantes finais.
5. Prompt 2 (`prompts/p2_codigo_passos.md`): análise em passos do código-fonte e 34 testes. Primeira execução: 32 passaram e 2 falharam. Cada falha era um defeito real da API, não do teste (`experimento/analise_p2.md`).
6. Correções: `Retry-After` com dígito não ASCII (`provider.py`) e falha do banco depois do aceite do Provedor (`service.py`, regra R25). Depois delas, os 133 testes passaram. Como esses dois defeitos viraram mutantes (M33 e M34), o total passou de 32 para 34.

## Resultado do teste de mutação (34 defeitos)

| Suíte | Testes | Defeitos detectados |
|---|---:|---:|
| Prompt 1, versão 1 | 71 | 22 |
| Prompt 1, versão 1 + versão 2 | 99 | 30 |
| Prompt 2 sozinho | 34 | 17 |
| Todas juntas | 133 | 34 |

Tabela completa, mutante por mutante, em `experimento/tabela_mutacao.md`. Para reproduzir: `python experimento/mutantes.py`.

## Como cada prompt influenciou a qualidade e a diversidade

- Prompt 1 (contrato): diversidade ampla de endpoints, códigos HTTP e erros de validação, porque cada regra do contrato virou pelo menos um teste. A qualidade ficou limitada ao que o texto do contrato dizia de forma explícita, e a v1 só olhava o status e o corpo da resposta.
- Prompt 2 (código e análise em passos): menos testes e menos cobertura do contrato (17 de 34 sozinho), mas diversidade de outro tipo: Unicode, chamadas simultâneas, falha do banco no meio de uma operação, cabeçalhos malformados, configuração. Foi o único que achou defeitos reais.
- Os dois se complementam: das 34 mutações, 17 só foram pegas pelas suítes do prompt 1, 4 só pelas do prompt 2 e 13 pelas duas.

## Ajustes de prompt

Prompt 1:
- A v1 pedia "pelo menos um teste por regra". Isso garantiu cobertura, mas os testes olhavam o status HTTP e pouco mais.
- A v2 acrescentou cinco critérios: teste que falharia se a regra fosse removida, os dois lados de cada limite, efeitos colaterais (saldo, estado do job, número de chamadas), conferir cada tentativa e variar o formato das respostas do Provedor. Também passei a lista de testes já existentes para evitar repetição.

Prompt 2:
- Pedi que o teste expresse o comportamento esperado quando o código provavelmente não trata a situação. Foi assim que os dois defeitos apareceram como testes vermelhos.
- Instruções práticas que fizeram diferença: `TestClient(app, raise_server_exceptions=False)` para observar o erro 500, cabeçalhos em bytes (o httpx recusa `str` não ASCII), `threading.Barrier` para chamadas simultâneas, `monkeypatch` para simular falha interna.
- A lista dos testes existentes foi incluída para que a análise se concentrasse no que o contrato não mostra.

## Limitações

- O código da API, o contrato e os testes foram produzidos na mesma sessão com o mesmo modelo. Para reduzir o viés, o contrato e os testes da v1 foram escritos antes do código, mas um experimento independente deveria usar outra pessoa ou outro modelo escrevendo a API.
- O teste de mutação usa 34 defeitos escolhidos à mão. É um indicador de força da suíte, não uma medida completa.
- Os testes pegam o que o Provedor simulado faz. Um Provedor real pode divergir do contrato assumido.
