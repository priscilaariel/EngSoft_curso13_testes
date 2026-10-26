# Contrato da Render Jobs API (v1.1)

A Render Jobs API recebe pedidos de geração de imagem, cobra créditos do usuário, delega a geração a um provedor externo (o "Provedor") por HTTP e recebe o resultado por webhook.

Este documento é a fonte de verdade usada nos prompts do experimento. Cada regra tem um identificador (R01, R02...) para rastrear os testes.

## 1. Fluxo de integração

```
Cliente --POST /jobs--> API --POST /v1/generations--> Provedor
                         |  (debita crédito, grava job)      |
                         |<-------- 202 {"id": "gen_1"} -----|
Cliente <--201 (processing)                                  |
                                                             |  (gera a imagem)
Provedor --POST /webhooks/provider (assinado)--> API
                         (atualiza job, devolve crédito se falhou)
Cliente --GET /jobs/{id}--> API
```

Pontos de integração: Cliente e API (REST), API e Provedor (HTTP, com retentativas), Provedor e API (webhook assinado), API e banco SQLite (débito e reembolso atômicos).

## 2. Usuários

### PUT /users/{user_id}
Corpo: `{"credits": <inteiro>}`. Cria o usuário ou substitui o saldo.

- R01: resposta 200 com `{"user_id": "...", "credits": N}`. Um segundo PUT substitui o saldo anterior.
- R02: `user_id` deve casar com `^[a-z0-9_-]{1,32}$` e `credits` deve ser inteiro entre 0 e 10000. Caso contrário, 422.

### GET /users/{user_id}
- R03: 200 com `{"user_id": "...", "credits": N}`, ou 404 com `{"detail": "user_not_found"}`.

## 3. Jobs

### POST /jobs
Corpo: `{"user_id": str, "prompt": str, "resolution": 512 | 1024 | 2048}`.

- R04: custo em créditos por resolução: 512 custa 1, 1024 custa 2, 2048 custa 4. Se `resolution` não for enviada, vale 1024.
- R05: `prompt` tem os espaços das pontas removidos e deve ter de 1 a 500 caracteres depois disso. `resolution` fora da lista, `user_id` fora do padrão do R02 e campos extras no corpo resultam em 422.
- R06: usuário inexistente: 404 `user_not_found`, sem chamar o Provedor.
- R07: saldo menor que o custo: 402 `insufficient_credits`, saldo inalterado, nenhum job criado, nenhuma chamada ao Provedor. Saldo igual ao custo é permitido e termina em 0.
- R08: sucesso: 201 com o job em `status = "processing"`, `provider_id` igual ao `id` devolvido pelo Provedor, `cost` preenchido, `image_url` e `failure_reason` nulos. O saldo do usuário diminui exatamente o custo, uma única vez.

Campos do job: `id` (UUID), `user_id`, `prompt`, `resolution`, `cost`, `status`, `provider_id`, `image_url`, `failure_reason`, `created_at`, `updated_at`.

### GET /jobs/{job_id}
- R16: 200 com o job, 404 `job_not_found` se não existir, 422 se `job_id` não for um UUID.

### GET /jobs
Parâmetros opcionais: `user_id`, `status` (`queued`, `processing`, `succeeded`, `failed`), `limit` (1 a 100, padrão 20), `offset` (0 ou mais, padrão 0).

- R17: resposta `{"items": [...], "total": N}`. `total` conta os jobs que passam pelos filtros, ignorando a paginação. Ordem: mais recente primeiro. Valores inválidos de `status`, `limit` ou `offset` resultam em 422.

## 4. Contrato consumido do Provedor

### POST {base}/v1/generations
Corpo enviado: `{"prompt": str, "size": <resolution>, "client_reference": "<id do job>"}`.
Cabeçalhos enviados: `Authorization: Bearer <chave>` e `Idempotency-Key: <id do job>`.
Resposta esperada: 202 com `{"id": "gen_..."}`.

- R09: a API envia exatamente a requisição acima, uma vez por tentativa.
- R10: respostas 429, 500, 502, 503 e 504, além de falhas de conexão e timeout, são tentadas de novo, até 3 tentativas no total, sempre com a mesma `Idempotency-Key`. A espera entre tentativas é de 0,5 s e depois 1,0 s (dobra a cada tentativa) e não há espera depois da última tentativa. Se a resposta 429 trouxer `Retry-After` com um inteiro de segundos, a API espera esse valor no lugar do backoff, no máximo 10 s.
- R11: outros códigos 4xx não são tentados de novo. A criação falha com 502 `provider_rejected`.
- R12: esgotadas as tentativas, a resposta é 502 `provider_unavailable` (429, 5xx ou erro de conexão) ou 504 `provider_timeout` (timeout). O código vem da última falha.
- R13: se o Provedor responder 202 com corpo que não seja JSON, sem `id`, ou com `id` vazio ou que não seja texto, ou responder qualquer 2xx ou 3xx diferente de 202, a criação falha com 502 `provider_invalid_response`, sem retentativa.
- R14: em qualquer falha de criação (R11, R12, R13) o job fica com `status = "failed"` e `failure_reason` igual ao código do erro, o crédito é devolvido integralmente, a resposta tem o formato `{"detail": "<código>", "job_id": "<id>"}` e o job pode ser consultado por GET.
- R15: se uma retentativa for bem-sucedida, o resultado é o mesmo do R08, com um único débito e um único job.

- R25 (acrescentada na v1.1, depois do P2): se o Provedor aceitar o pedido (202) mas a API falhar ao gravar o `provider_id` no banco, o job fica `failed` com `failure_reason = "internal_error"`, o crédito é devolvido e a resposta é 500 `{"detail": "internal_error", "job_id": "<id>"}`. Sem o `provider_id` a API nunca receberia o webhook, por isso o job não pode ficar preso em `queued` com o crédito debitado.

## 5. Webhook do Provedor

### POST /webhooks/provider
Corpo: `{"id": "<provider_id>", "status": "succeeded" | "failed", "image_url": str, "error": str}`.
Cabeçalho: `X-Signature` com o HMAC-SHA256, em hexadecimal minúsculo, do corpo bruto da requisição usando o segredo compartilhado.

- R18: assinatura ausente ou incorreta: 401 `invalid_signature`, sem alterar nada. A assinatura é verificada antes da validação do corpo.
- R19: corpo inválido: 422 `invalid_payload`. `status = "succeeded"` exige `image_url` começando com `https://`. `error` tem no máximo 200 caracteres. `image_url` e `error` são opcionais nos demais casos.
- R20: `id` que não corresponde a nenhum job: 404 `job_not_found`.
- R21: `succeeded` para um job em `processing`: o job passa a `succeeded`, guarda `image_url`, os créditos não mudam, resposta 200 `{"result": "applied"}`.
- R22: `failed` para um job em `processing`: o job passa a `failed`, `failure_reason` recebe o texto de `error` (ou `provider_failed` se não houver), o crédito é devolvido integralmente, resposta 200 `{"result": "applied"}`.
- R23: evento para um job que já terminou (`succeeded` ou `failed`): resposta 200 `{"result": "ignored"}`, nada muda e nenhum reembolso adicional é feito, mesmo que o status do evento seja diferente do estado atual do job.

## 6. Erros de validação
- R24: erros de validação de entrada seguem o formato padrão do FastAPI (status 422).

## 7. Ponto de montagem para testes
```python
from app.config import Settings
from app.main import create_app

app = create_app(settings=Settings(...), http_client=httpx.Client(transport=...), sleep=<função de espera>)
```
`Settings` aceita `db_path`, `provider_base_url`, `provider_api_key`, `webhook_secret`, `provider_max_attempts`, `provider_backoff_seconds` e `provider_timeout_seconds`. O parâmetro `sleep` recebe a função usada nas esperas entre tentativas, o que permite registrar os tempos sem esperar de verdade.
