# Prompt 2: testes caixa-branca com análise em passos

Tipo de prompt: few-shot com raciocínio em passos. A LLM recebe o código-fonte, dois testes de exemplo (para fixar estilo e helpers) e é obrigada a escrever uma análise antes do código.

Anexos colados nos lugares indicados: arquivos de `app/` (delimitados), `tests/conftest.py` e dois testes de `tests/p1_contrato/` como exemplo.

## Prompt usado

```text
PAPEL
Você é um engenheiro de testes sênior revisando a integração de uma API FastAPI com um
Provedor externo e um banco SQLite. Você tem acesso ao código-fonte.

CONTEXTO
Já existe uma suíte baseada no contrato (lista de nomes abaixo). Sua tarefa é encontrar o que
um leitor do contrato não consegue ver: o que o código faz em situações que o contrato não
descreve.

##### CÓDIGO-FONTE
[COLE AQUI app/provider.py, app/service.py, app/repository.py, app/main.py, app/schemas.py]
##### FIM DO CÓDIGO

##### FIXTURES
[COLE AQUI tests/conftest.py]
##### FIM DAS FIXTURES

EXEMPLOS DE ESTILO (dois testes já existentes)
[COLE AQUI test_r10_503_seguido_de_sucesso e test_r22_falha_devolve_credito]

LISTA DOS TESTES QUE JÁ EXISTEM
[COLE AQUI docs/casos_de_teste.md, seções do prompt 1]

TAREFA, EM DUAS PARTES
Parte 1, "Análise": percorra o código em passos, nesta ordem:
  a) liste cada ponto em que o código troca dados com algo externo (rede, banco, cabeçalho,
     corpo de requisição);
  b) para cada ponto, escreva o que acontece se a outra ponta responder fora do esperado
     (formato estranho, valor extremo, falha no meio da operação, chamadas simultâneas);
  c) marque os pontos em que o código parece não tratar a situação;
  d) devolva uma tabela: ponto, arquivo e função, situação, risco, teste proposto.
Parte 2, "Testes": escreva pytest para cada linha da tabela. Quando o teste for sobre uma
falha que o código provavelmente não trata, escreva o teste com o comportamento ESPERADO
(não com o comportamento atual) para que ele falhe se houver defeito.

RESTRIÇÕES
- Não repita casos da lista existente.
- Se precisar simular uma falha interna, use monkeypatch em vez de alterar o código.
- Se o TestClient precisar devolver 500 em vez de relançar a exceção, use
  TestClient(app, raise_server_exceptions=False).
- Cabeçalhos com bytes fora de ASCII devem ser criados como lista de tuplas de bytes em
  httpx.Response(headers=[(b"...", b"...")]), porque o httpx recusa str não ASCII.
- Para chamadas simultâneas use threading com Barrier, cada thread com o seu TestClient.

FORMATO DE SAÍDA
Primeiro a seção "Análise" (tabela em Markdown), depois o código Python em blocos por arquivo.
```

As restrições sobre `TestClient`, cabeçalhos em bytes e threads entraram no prompt como lições do trabalho: o httpx recusa `str` não ASCII em cabeçalhos (descoberto ao reproduzir o defeito 1) e o `TestClient` relança por padrão as exceções do servidor (ver `experimento/registro.md`). A análise produzida está em `experimento/analise_p2.md`.
