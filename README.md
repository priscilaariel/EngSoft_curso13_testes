# Render Jobs API: testes de integração apoiados por GenAI

Repositório do fórum da Unidade III (curso 13, testes). Mostra como dois tipos de prompt geram casos de teste de integração diferentes para o mesmo sistema, e mede a diferença com um teste de mutação.

## O sistema testado

Uma API FastAPI que recebe pedidos de geração de imagem e integra três pontos:

```
Cliente --REST--> API --HTTP (retentativas, Idempotency-Key)--> Provedor externo
                   |                                              |
                   | SQLite (débito e reembolso de créditos)      |
                   <------------- webhook assinado (HMAC) --------+
```

O contrato com 25 regras numeradas (R01 a R25) está em `docs/contrato.md`. O Provedor é simulado em `tests/conftest.py` com `httpx.MockTransport`.

## Os dois tipos de prompt

| Prompt | Técnica | O que a LLM recebe | Arquivos |
|---|---|---|---|
| 1 | zero-shot estruturado, caixa-preta | contrato e fixtures | `prompts/p1_contrato.md`, `tests/p1_contrato/`, `tests/p1_contrato_v2/` |
| 2 | few-shot com análise em passos, caixa-branca | código-fonte, exemplos e a lista de testes existentes | `prompts/p2_codigo_passos.md`, `tests/p2_codigo/`, `experimento/analise_p2.md` |

## Resultados

133 testes, todos passando. Teste de mutação com 34 defeitos injetados à mão:

| Suíte | Testes | Defeitos detectados |
|---|---:|---:|
| Prompt 1, v1 | 71 | 22 |
| Prompt 1, v1 + v2 | 99 | 30 |
| Prompt 2 sozinho | 34 | 17 |
| Todas | 133 | 34 |

O prompt 2 encontrou dois defeitos reais na API (`Retry-After` com dígito não ASCII e crédito preso quando o banco falha depois do aceite do Provedor). Ambos foram corrigidos; o segundo virou a regra R25. Detalhes em `experimento/registro.md`.

## Como rodar no VS Code

Requisito: Python 3.11 ou mais novo.

1. Abra a pasta do projeto no VS Code (`File > Open Folder`). O VS Code sugere instalar a extensão Python.
2. Abra um terminal (`Terminal > New Terminal`) e crie o ambiente:
   - macOS ou Linux: `python3 -m venv .venv && source .venv/bin/activate`
   - Windows (PowerShell): `py -m venv .venv; .venv\Scripts\Activate.ps1`
3. Instale as dependências: `pip install -r requirements.txt`
4. Selecione o interpretador: `Ctrl+Shift+P`, "Python: Select Interpreter", escolha o da pasta `.venv`.
5. Rode os testes pelo painel Testing (ícone de frasco) ou com `python -m pytest`. Esperado: `133 passed`.

Atalhos já configurados em `Terminal > Run Task`: todos os testes, só prompt 1, só prompt 2 e teste de mutação. Em `Run and Debug` há a configuração "API (uvicorn)" para subir a API em `http://localhost:8000` (documentação interativa em `/docs`).

## Teste de mutação

`python experimento/mutantes.py` copia o projeto para uma pasta temporária, injeta um defeito por vez (lista em `experimento/mutantes.py`), roda cada suíte e grava `experimento/resultados_mutacao.json`. Leva alguns minutos. Um mutante sobrevivente mostra o que a suíte não verifica. Tabela de resultados: `experimento/tabela_mutacao.md`.

## Como repetir o experimento com a sua LLM

1. Copie o prompt de `prompts/p1_contrato.md`, cole `docs/contrato.md` e `tests/conftest.py` nos lugares indicados e peça os testes.
2. Salve a saída em uma pasta nova dentro de `tests/` e rode `python -m pytest`.
3. Faça o mesmo com `prompts/p2_codigo_passos.md`, colando o código de `app/`.
4. Rode `python experimento/mutantes.py` ajustando o dicionário `SUITES` para as suas pastas e compare.

## Estrutura

```
app/                  API (FastAPI, cliente do Provedor, repositório SQLite)
docs/                 contrato, OpenAPI gerado e catálogo dos 133 casos de teste
prompts/              os dois prompts e os ajustes de cada um
tests/                conftest.py (Provedor simulado) e as três pastas de teste
experimento/          análise do prompt 2, mutantes, resultados e registro
.vscode/              configuração de testes, execução e tarefas
```

## Limitações

O contrato, a API e os testes foram feitos na mesma sessão com o mesmo modelo. Os testes da v1 foram escritos antes do código para reduzir o viés, mas um experimento independente deveria usar outra pessoa ou outro modelo escrevendo a API. O Provedor é simulado.
