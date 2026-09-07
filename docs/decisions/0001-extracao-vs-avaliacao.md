# ADR 0001 — A IA extrai, o código julga

## Estado
Aceite.

## Contexto
A ferramenta usa um LLM e analisa tickets para concluir sobre controlos de auditoria
(segregação de funções, aprovação prévia, coerência de datas, etc.). Havia a tentação de
pedir ao LLM que também decidisse se cada controlo passa ou falha.

## Decisão
O LLM **apenas extrai** campos estruturados, com evidência e confiança. A decisão de
`CONFORME`/`EXCECAO`/`REVER`/`NAO_APLICAVEL` é feita por **regras determinísticas em
Python puro**.

## Justificação
- **Reprodutibilidade**: uma conclusão de auditoria tem de correr sempre igual. Código
  determinístico dá isso; um modelo tem variabilidade.
- **Defensabilidade**: perante o cliente ou um revisor de qualidade, tem de se explicar
  *porquê* um ticket é uma exceção. "A regra X comparou a data Y com a Z" defende-se;
  "o modelo achou" não.
- **Testabilidade**: as regras são cobertas por `pytest`, o que é prova de correção.
- **Separação de erros**: distingue-se "o controlo falhou" (EXCECAO) de "não conseguimos
  ler o ticket" (REVER) — impossível se o modelo devolvesse só um veredicto.

## Consequências
- O modelo canónico tem de capturar tudo o que as regras precisam.
- Qualquer juízo qualitativo (ex.: se uma justificação é *adequada*) fica com o humano; a
  IA no máximo dá um flag auxiliar, nunca um veredicto.
