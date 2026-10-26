# Análise em passos produzida pelo prompt 2

Resultado da Parte 1 do prompt 2: a tabela que guiou os testes de `tests/p2_codigo/`. A coluna "Resultado" é o que aconteceu quando os testes rodaram contra o código antes de qualquer correção.

| # | Ponto de integração | Onde | Situação | Risco | Teste | Resultado |
|---|---|---|---|---|---|---|
| 1 | Cabeçalho `Retry-After` vindo do Provedor | `provider._retry_after` | valor não numérico, negativo, decimal, data HTTP, vazio | espera errada ou erro | `test_p2_retry_after_que_nao_e_inteiro_cai_no_backoff` | passou |
| 2 | Mesmo cabeçalho | `provider._retry_after` | dígito não ASCII (por exemplo `²`): `str.isdigit()` aceita, `int()` recusa | `ValueError` vira erro 500 e o crédito fica debitado | `test_p2_retry_after_com_digito_nao_ascii_nao_derruba_a_api` | **falhou: defeito 1** |
| 3 | Registro do `provider_id` no banco | `service.create_job` | o Provedor já aceitou, mas o banco falha ao gravar o id | job preso em `queued`, crédito debitado, webhook nunca chega | `test_p2_falha_do_banco_depois_do_aceite_do_provedor_nao_deixa_credito_preso` | **falhou: defeito 2** |
| 4 | Id devolvido pelo Provedor | `repository.mark_processing`, coluna `UNIQUE` | o Provedor repete o mesmo id para outro job | `IntegrityError` não tratado | `test_p2_provedor_repete_o_mesmo_id_para_outro_job` | passou (já havia tratamento) |
| 5 | Débito e criação do job | `repository.create_job_debiting` | a inserção falha depois do débito | débito sem job | `test_p2_debito_e_insercao_do_job_sao_atomicos` | passou |
| 6 | Reembolso | `repository.fail_and_refund` | chamado duas vezes ou para job inexistente | reembolso duplicado | `test_p2_fail_and_refund_em_job_finalizado_ou_inexistente_nao_devolve_nada` | passou |
| 7 | Webhooks simultâneos | `main.provider_webhook`, `repository.apply_provider_result` | oito requisições idênticas ao mesmo tempo | reembolso repetido | `test_p2_webhooks_simultaneos_do_mesmo_evento_reembolsam_uma_unica_vez` | passou |
| 8 | Assinatura | `main.provider_webhook` | maiúsculas, corpo reserializado, caractere não ASCII no cabeçalho | aceitar assinatura errada ou erro 500 | três testes `test_p2_assinatura_*` | passou |
| 9 | Corpo bruto do webhook | `WebhookEvent.model_validate_json` | não é JSON, vazio, campo desconhecido, id vazio | erro 500 em vez de 422 | quatro testes de payload | passou |
| 10 | Campos que não se aplicam ao status | `apply_provider_result` | `failed` com `image_url`, `succeeded` com `error` | gravar dado indevido | dois testes `test_p2_evento_*` | passou |
| 11 | Job que falhou na criação | `repository` | webhook com id que nunca foi gravado | reembolso indevido | `test_p2_job_que_falhou_na_criacao_nao_pode_receber_webhook` | passou |
| 12 | Texto do prompt | `schemas.JobCreate`, corpo enviado ao Provedor | emoji, quebra de linha, 500 caracteres de 4 bytes | contagem em bytes, perda de dados | dois testes de Unicode | passou |
| 13 | Configuração | `config.Settings`, `ProviderClient` | URL com barra final, 1 e 5 tentativas, variáveis de ambiente | barra dupla, backoff errado | quatro testes de configuração | passou |
| 14 | Filtro de listagem | `repository.list_jobs` | `user_id` com aspas e SQL | injeção | `test_p2_user_id_com_sql_e_tratado_como_texto` | passou |
| 15 | Identificador na URL | `main.get_job` | UUID em maiúsculas | 404 indevido | `test_p2_get_job_aceita_uuid_em_maiusculas` | passou |

## Correções feitas depois da primeira rodada

- Defeito 1: `app/provider.py`, `_retry_after` passou a exigir `value.isascii() and value.isdigit()`.
- Defeito 2: `app/service.py` passou a capturar `sqlite3.Error` depois do aceite do Provedor, marcar o job como `failed` (`internal_error`), devolver o crédito e responder 500 com o `job_id`. A regra virou a R25 no contrato (v1.1).

Com as duas correções, a suíte completa passou (133 testes).
