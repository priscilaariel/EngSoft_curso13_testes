# Catálogo de casos de teste

Gerado a partir de `pytest --collect-only`. Cada linha é um teste (os parametrizados aparecem uma vez por combinação).
Total: 133 casos.


## Prompt 1, versão 1 (contrato): 71 casos

### test_consulta.py (12)

- `test_r16_get_job_existente`
- `test_r16_get_job_inexistente`
- `test_r16_id_que_nao_e_uuid`
- `test_r17_listagem_com_total`
- `test_r17_filtro_por_usuario`
- `test_r17_filtro_por_status`
- `test_r17_paginacao_com_limit_e_offset`
- `test_r17_mais_recente_primeiro`
- `test_r17_parametros_invalidos[params0]`
- `test_r17_parametros_invalidos[params1]`
- `test_r17_parametros_invalidos[params2]`
- `test_r17_parametros_invalidos[params3]`

### test_criacao_job.py (16)

- `test_r08_criacao_com_sucesso`
- `test_r04_resolucao_padrao_e_1024_com_custo_2`
- `test_r04_custo_por_resolucao[512-1]`
- `test_r04_custo_por_resolucao[1024-2]`
- `test_r04_custo_por_resolucao[2048-4]`
- `test_r07_saldo_igual_ao_custo_termina_em_zero`
- `test_r07_saldo_insuficiente_retorna_402`
- `test_r06_usuario_inexistente_retorna_404`
- `test_r05_prompt_invalido[]`
- `test_r05_prompt_invalido[   ]`
- `test_r05_prompt_invalido[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]`
- `test_r05_prompt_com_500_caracteres_e_aceito`
- `test_r05_prompt_e_aparado`
- `test_r05_resolucao_fora_da_lista`
- `test_r05_campo_extra_e_rejeitado`
- `test_r05_user_id_fora_do_padrao`

### test_provedor.py (15)

- `test_r09_requisicao_enviada_ao_provedor`
- `test_r10_503_seguido_de_sucesso`
- `test_r10_backoff_dobra_a_cada_tentativa`
- `test_r10_retry_after_substitui_o_backoff`
- `test_r12_tres_falhas_5xx_retornam_502`
- `test_r12_timeouts_retornam_504`
- `test_r12_erro_de_conexao_retorna_502`
- `test_r11_4xx_nao_e_tentado_de_novo`
- `test_r13_resposta_invalida_do_provedor[resposta0]`
- `test_r13_resposta_invalida_do_provedor[resposta1]`
- `test_r13_resposta_invalida_do_provedor[resposta2]`
- `test_r13_resposta_invalida_do_provedor[resposta3]`
- `test_r13_resposta_invalida_do_provedor[resposta4]`
- `test_r14_falha_marca_job_como_failed_e_devolve_credito`
- `test_r15_retentativa_com_sucesso_gera_um_unico_job`

### test_usuarios.py (15)

- `test_r01_put_cria_usuario_com_saldo`
- `test_r01_put_substitui_saldo_existente`
- `test_r02_limites_validos_de_credits[0]`
- `test_r02_limites_validos_de_credits[10000]`
- `test_r02_credits_invalido_retorna_422[-1]`
- `test_r02_credits_invalido_retorna_422[10001]`
- `test_r02_credits_invalido_retorna_422[dez]`
- `test_r02_credits_invalido_retorna_422[1.5]`
- `test_r02_credits_invalido_retorna_422[None]`
- `test_r02_user_id_invalido_retorna_422[ANA]`
- `test_r02_user_id_invalido_retorna_422[ana.silva]`
- `test_r02_user_id_invalido_retorna_422[aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa]`
- `test_r02_user_id_invalido_retorna_422[ana silva]`
- `test_r03_get_usuario_existente`
- `test_r03_get_usuario_inexistente`

### test_webhook.py (13)

- `test_r18_assinatura_invalida_retorna_401`
- `test_r18_sem_assinatura_retorna_401`
- `test_r21_sucesso_atualiza_o_job`
- `test_r22_falha_devolve_credito`
- `test_r22_falha_sem_mensagem_usa_provider_failed`
- `test_r20_id_desconhecido`
- `test_r19_payload_invalido[payload0]`
- `test_r19_payload_invalido[payload1]`
- `test_r19_payload_invalido[payload2]`
- `test_r19_payload_invalido[payload3]`
- `test_r23_evento_duplicado_e_ignorado`
- `test_r23_falha_duplicada_nao_reembolsa_duas_vezes`
- `test_r23_evento_conflitante_apos_estado_final`

## Prompt 1, versão 2 (acréscimos): 28 casos

### test_bordas_e_efeitos.py (28)

- `test_r10_retry_after_acima_de_10_segundos_e_limitado`
- `test_r10_429_sem_retry_after_usa_o_backoff`
- `test_r10_nao_ha_espera_depois_da_ultima_tentativa`
- `test_r10_todas_as_tentativas_usam_a_mesma_idempotency_key_e_o_mesmo_corpo`
- `test_r10_429_persistente_esgota_as_tres_tentativas`
- `test_r12_a_ultima_falha_define_o_codigo_de_erro`
- `test_r13_respostas_que_nao_sao_um_objeto_com_id[resposta0]`
- `test_r13_respostas_que_nao_sao_um_objeto_com_id[resposta1]`
- `test_r13_respostas_que_nao_sao_um_objeto_com_id[resposta2]`
- `test_r13_respostas_que_nao_sao_um_objeto_com_id[resposta3]`
- `test_r13_respostas_que_nao_sao_um_objeto_com_id[resposta4]`
- `test_r13_respostas_que_nao_sao_um_objeto_com_id[resposta5]`
- `test_r14_toda_falha_devolve_o_credito_e_registra_o_job_como_failed[5xx]`
- `test_r14_toda_falha_devolve_o_credito_e_registra_o_job_como_failed[timeout]`
- `test_r14_toda_falha_devolve_o_credito_e_registra_o_job_como_failed[conexao]`
- `test_r14_toda_falha_devolve_o_credito_e_registra_o_job_como_failed[rejeitado]`
- `test_r14_toda_falha_devolve_o_credito_e_registra_o_job_como_failed[sem_id]`
- `test_r06_r07_r05_nao_chamam_o_provedor`
- `test_r08_um_unico_debito_e_uma_unica_chamada`
- `test_r19_error_com_200_caracteres_e_aceito_e_com_201_nao`
- `test_r02_credits_como_texto_numerico_e_rejeitado`
- `test_r17_offset_alem_do_fim_devolve_lista_vazia_com_total`
- `test_r17_limit_100_e_aceito`
- `test_r17_filtros_combinados`
- `test_r18_assinatura_invalida_nao_altera_nada`
- `test_r18_a_assinatura_e_verificada_antes_do_corpo`
- `test_r21_sucesso_nao_mexe_nos_creditos`
- `test_r23_evento_ignorado_nao_altera_image_url_nem_motivo`

## Prompt 2 (código-fonte e análise em passos): 34 casos

### test_provedor_e_servico.py (22)

- `test_p2_retry_after_que_nao_e_inteiro_cai_no_backoff[abc]`
- `test_p2_retry_after_que_nao_e_inteiro_cai_no_backoff[-1]`
- `test_p2_retry_after_que_nao_e_inteiro_cai_no_backoff[1.5]`
- `test_p2_retry_after_que_nao_e_inteiro_cai_no_backoff[]`
- `test_p2_retry_after_que_nao_e_inteiro_cai_no_backoff[Wed, 21 Oct 2026 07:28:00 GMT]`
- `test_p2_retry_after_zero_nao_espera`
- `test_p2_retry_after_com_digito_nao_ascii_nao_derruba_a_api`
- `test_p2_retry_after_so_vale_para_429`
- `test_p2_provedor_repete_o_mesmo_id_para_outro_job`
- `test_p2_corpo_extra_na_resposta_202_e_ignorado`
- `test_p2_prompt_com_emoji_e_quebra_de_linha_chega_intacto_ao_provedor`
- `test_p2_500_emojis_contam_como_500_caracteres`
- `test_p2_url_base_com_barra_final_nao_gera_barra_dupla`
- `test_p2_uma_unica_tentativa_configurada_nao_tem_retentativa_nem_espera`
- `test_p2_cinco_tentativas_configuradas_seguem_o_backoff_dobrando`
- `test_p2_settings_from_env`
- `test_p2_falha_do_banco_depois_do_aceite_do_provedor_nao_deixa_credito_preso`
- `test_p2_debito_e_insercao_do_job_sao_atomicos`
- `test_p2_fail_and_refund_em_job_finalizado_ou_inexistente_nao_devolve_nada`
- `test_p2_user_id_com_sql_e_tratado_como_texto`
- `test_p2_get_job_aceita_uuid_em_maiusculas`
- `test_p2_updated_at_muda_quando_o_webhook_e_aplicado`

### test_webhook_codigo.py (12)

- `test_p2_corpo_que_nao_e_json_com_assinatura_valida_retorna_422`
- `test_p2_corpo_vazio_com_assinatura_valida_retorna_422`
- `test_p2_campo_desconhecido_no_evento_e_rejeitado`
- `test_p2_evento_failed_com_image_url_nao_guarda_a_url`
- `test_p2_evento_succeeded_com_error_ignora_o_texto_de_erro`
- `test_p2_id_vazio_no_evento_retorna_422`
- `test_p2_job_que_falhou_na_criacao_nao_pode_receber_webhook`
- `test_p2_assinatura_em_maiusculas_e_recusada`
- `test_p2_assinatura_calculada_sobre_o_corpo_reserializado_e_recusada`
- `test_p2_assinatura_com_caractere_nao_ascii_retorna_401_e_nao_erro_500`
- `test_p2_webhooks_simultaneos_do_mesmo_evento_reembolsam_uma_unica_vez`
- `test_p2_webhooks_de_jobs_diferentes_do_mesmo_usuario_somam_os_reembolsos`
