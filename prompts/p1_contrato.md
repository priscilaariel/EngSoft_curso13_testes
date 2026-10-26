# Prompt 1: testes caixa-preta a partir do contrato

Tipo de prompt: zero-shot estruturado (papel, contexto, tarefa, restrições, formato de saída). A LLM só recebe o contrato e as fixtures, sem ver o código da API.

Anexos colados no lugar indicado: `docs/contrato.md` e `tests/conftest.py`.

## Versão 1 (primeira tentativa)

```text
PAPEL
Você é um engenheiro de testes sênior, especialista em testes de integração de APIs REST em Python.

CONTEXTO
Vou testar uma API FastAPI que integra três pontos: clientes REST, um Provedor externo de
geração de imagens (chamado por HTTP) e um banco SQLite. O contrato completo está abaixo.

[COLE AQUI docs/contrato.md]

As fixtures e os helpers já existem em tests/conftest.py (provider, sleeps, client, make_user,
create_job, new_job, send_webhook, credits_of). Use-os em vez de criar outros.

[COLE AQUI tests/conftest.py]

TAREFA
Gere testes de integração em pytest para cobrir o contrato.

RESTRIÇÕES
- Use apenas o que está no contrato. Não suponha comportamento que não esteja escrito.
- Teste só pela interface HTTP (TestClient). Não acesse o banco nem os módulos internos.
- Pelo menos um teste por regra Rnn. Inclua o id da regra no nome do teste (test_r10_...).
- Agrupe por assunto em arquivos: usuários, criação de job, provedor, consulta, webhook.

FORMATO DE SAÍDA
Somente código Python, um bloco por arquivo, com o caminho do arquivo no cabeçalho do bloco.
```

Resultado da v1: 71 testes, todos passando. No teste de mutação, 22 de 34 defeitos injetados foram detectados (ver `experimento/tabela_mutacao.md`). A maior parte dos defeitos que passaram direto era de três tipos: valor de limite que ninguém testou (teto de 10 s, 200 caracteres), comportamento de cada tentativa (cabeçalho, espera após a última) e formato de resposta do Provedor que o teste não variou.

## Versão 2 (ajuste)

Acrescentei ao prompt o bloco abaixo, depois de RESTRIÇÕES. O resto ficou igual. A saída da v2 foi pedida como arquivo novo (`tests/p1_contrato_v2/`), sem repetir os testes da v1.

```text
CRITÉRIOS DE QUALIDADE (cada teste novo precisa passar nesta checagem)
1. Teste que falharia se a regra fosse removida: para cada regra, imagine o defeito mais simples
   que a quebraria (limite trocado, passo omitido, valor errado) e escreva o teste que o pegaria.
2. Os dois lados de cada limite: se a regra tem um número (10 s, 200 caracteres, 100 itens, 3
   tentativas), teste o valor no limite, um acima e um abaixo.
3. Efeitos colaterais, não só o status HTTP: depois de cada falha, confira saldo do usuário,
   estado do job, número de jobs na listagem e número de chamadas ao Provedor.
4. Cada tentativa conta: em fluxos com retentativa, confira cabeçalhos, corpo e tempo de espera
   de todas as tentativas, e a ordem em que as falhas acontecem.
5. Respostas de terceiros variam de formato: quando o Provedor responde com JSON, varie o tipo
   do corpo (objeto vazio, lista, null, texto, número) e os códigos de status (204, 301).
6. Não repita casos que já existem na lista de testes abaixo; foque no que ela não cobre.

[COLE AQUI a lista de nomes dos testes da v1: docs/casos_de_teste.md, seção da v1]
```

Resultado da v2: 28 testes novos. Juntos com os da v1, detectam 30 de 34 defeitos. Os 4 que restam dependem de informação que o contrato não tem (ver o prompt 2).
