Repositório: [COLE AQUI O LINK DO SEU REPOSITÓRIO NO GITHUB]

Cenário: uma API de geração de imagens com três pontos de integração. O cliente chama a API por REST, a API chama um provedor externo por HTTP (com retentativas, Idempotency-Key e webhook assinado de volta) e grava no SQLite o débito e o reembolso de créditos do usuário. O provedor é simulado com httpx.MockTransport. Escrevi o contrato com 25 regras numeradas, e os casos gerados (133 no total) estão em tests/ e no catálogo docs/casos_de_teste.md.

Usei o Claude com dois tipos de prompt e, para medir a qualidade de cada um, injetei 34 defeitos no código, um por vez, e contei quantos cada suíte detectava.

Prompt 1, zero-shot estruturado, só com o contrato. Gerou 71 testes que passaram de primeira e cobriu bem a variedade de rotas, códigos HTTP e erros de validação, porque cada regra virou um caso. Detectou 22 dos 34 defeitos. O que escapou estava em detalhes numéricos e de sequência: o teto de 10 s do Retry-After, o limite de 200 caracteres, a mesma Idempotency-Key em todas as tentativas.

Prompt 2, few-shot com o código-fonte e uma análise em passos antes dos testes (onde há troca de dados, o que acontece se a outra ponta responder fora do padrão, tabela de riscos). Gerou 34 testes que sozinhos detectaram só 17 defeitos, mas com outro tipo de diversidade: Unicode, requisições simultâneas, falha do banco no meio da operação. Foi o único a achar dois defeitos reais da minha API. Um Retry-After com dígito não ASCII derrubava a requisição, e se o banco falhasse depois de o provedor aceitar o pedido o crédito ficava debitado com o job preso em "queued".

Ajustes. No prompt 1 incluí critérios de qualidade: testar os dois lados de cada limite, conferir efeitos colaterais (saldo, estado do job, número de chamadas ao provedor), conferir cada tentativa e variar o formato das respostas do provedor. Vieram 28 testes novos e a detecção subiu de 22 para 30. No prompt 2 pedi que o teste descrevesse o comportamento esperado, e não o atual, para falhar se houvesse defeito, e passei instruções práticas (TestClient com raise_server_exceptions=False, cabeçalhos em bytes, threads com Barrier). Juntas, as duas suítes detectam os 34.

Em resumo, o contrato dá amplitude e o código dá profundidade. Nenhum dos dois sozinho bastou, e só o teste de mutação mostrou isso com números.
