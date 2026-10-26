| Id | Regra | Defeito injetado | P1 v1 | P1 v2 | P2 | Todas |
|---|---|---|:-:|:-:|:-:|:-:|
| M01 | R10 | Retry-After sem limite de 10 s | **sobrevive** | mata | **sobrevive** | mata |
| M02 | R10 | backoff não dobra | mata | mata | mata | mata |
| M03 | R10 | espera também depois da última tentativa | **sobrevive** | mata | mata | mata |
| M04 | R10 | Idempotency-Key muda nas retentativas | **sobrevive** | mata | **sobrevive** | mata |
| M05 | R10 | 429 não é tentado de novo | mata | mata | mata | mata |
| M06 | R11 | 400 é tentado de novo | mata | mata | mata | mata |
| M07 | R12 | timeout vira provider_unavailable | mata | mata | **sobrevive** | mata |
| M08 | R10 | uma tentativa a menos | mata | mata | mata | mata |
| M09 | R13 | id vazio é aceito | mata | mata | **sobrevive** | mata |
| M10 | R10 | Retry-After não numérico derruba a requisição | **sobrevive** | mata | mata | mata |
| M11 | R13 | corpo JSON que não é objeto causa erro 500 | **sobrevive** | mata | **sobrevive** | mata |
| M12 | R13 | id repetido do Provedor deixa job preso e crédito debitado | **sobrevive** | **sobrevive** | mata | mata |
| M13 | R22 | webhook failed não devolve o crédito | mata | mata | mata | mata |
| M14 | R23 | webhook repetido é reaplicado | mata | mata | mata | mata |
| M15 | R07 | saldo igual ao custo é recusado | mata | mata | **sobrevive** | mata |
| M16 | R17 | listagem do mais antigo para o mais novo | mata | mata | **sobrevive** | mata |
| M17 | R17 | total ignora os filtros | mata | mata | mata | mata |
| M18 | R14 | reembolso parcial na falha de criação | mata | mata | mata | mata |
| M19 | R14 | fail_and_refund repete reembolso em job já finalizado | **sobrevive** | **sobrevive** | mata | mata |
| M20 | R18 | assinatura ausente é aceita | mata | mata | **sobrevive** | mata |
| M21 | R19 | image_url http é aceita | mata | mata | **sobrevive** | mata |
| M22 | R05 | prompt não é aparado | mata | mata | **sobrevive** | mata |
| M23 | R05 | campos extras no job são aceitos | mata | mata | **sobrevive** | mata |
| M24 | R19 | limite de 200 caracteres de error vira 2000 | **sobrevive** | mata | **sobrevive** | mata |
| M25 | R02 | credits aceita texto numérico como "10" | **sobrevive** | mata | **sobrevive** | mata |
| M26 | R17 | limit máximo vira 1000 | mata | mata | **sobrevive** | mata |
| M27 | R04 | custo de 2048 errado | mata | mata | mata | mata |
| M28 | R13 | 200 do Provedor é aceito como sucesso | mata | mata | **sobrevive** | mata |
| M29 | R19 | payload inválido devolve 400 | mata | mata | mata | mata |
| M30 | R04 | resolução padrão errada | mata | mata | mata | mata |
| M31 | R10 | limite do Retry-After vira 60 s | **sobrevive** | mata | **sobrevive** | mata |
| M32 | R22 | failure_reason padrão errado | mata | mata | **sobrevive** | mata |
| M33 | R10 | Retry-After com dígito não ASCII derruba a requisição (defeito real achado pelo P2) | **sobrevive** | **sobrevive** | mata | mata |
| M34 | R25 | falha do banco depois do aceite do Provedor deixa crédito preso (defeito real achado pelo P2) | **sobrevive** | **sobrevive** | mata | mata |
