# API e custo

## Modelo e chamada

- Provedor: **API da Anthropic (Claude)**.
- Técnica: **tool use** para forçar a saída a um JSON schema (o modelo canónico). Isto
  garante que a resposta é sempre parseável e validável por pydantic, em vez de texto
  livre.
- Uma chamada por ticket (na v1). Tickets muito grandes podem exigir *chunking* — a
  camada de ingestão trata disso e reagrega antes da extração.

## Volume esperado

Ordem de grandeza por engagement: **dezenas, provavelmente abaixo de uma centena** de
tickets. Confortavelmente dentro de limites de rate normais. O desenho é, ainda assim,
**defensivo**:

- processamento em fila com *retry* e *backoff* em caso de rate-limit;
- processamento incremental (resultados aparecem à medida que ficam prontos, não em bloco);
- cada ticket é independente — um erro num ticket não afeta os outros (esse fica `REVER`).

## Custo

O custo da API é por **tokens** (entrada + saída). Estimativa por ticket depende do
tamanho do ticket e dos exemplos few-shot do profile. Para manter previsível:

- exemplos few-shot **curtos e representativos** (ver runbook);
- não reenviar o ticket inteiro se só interessam secções relevantes (a ingestão pode
  recortar cabeçalhos/rodapés repetitivos);
- registar tokens usados por run no trilho de auditoria, para acompanhar custo real.

Para dezenas de tickets por engagement, o custo por análise é baixo. Recomenda-se validar
com uma primeira medição real durante a fase de teste e afinar os profiles a partir daí.

## Configuração

Modelo, limiar de confiança e parâmetros de retry vivem em config, não em código, para
poderem ser ajustados sem redeploy.
