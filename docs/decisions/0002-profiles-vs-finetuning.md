# ADR 0002 — Profiles YAML em vez de fine-tuning

## Estado
Aceite.

## Contexto
A ferramenta tem de ler tickets de várias origens (ServiceNow, Jira, Control-M, Remedy,
Azure DevOps, BMC Helix, Genérico…) e de clientes diferentes, cada um com o seu layout e
vocabulário. É preciso "aprender" esses layouts de forma escalável.

## Decisão
Cada origem tem um **profile YAML** com aliases de campos, estados esperados, formatos de
data, exemplos few-shot validados e parâmetros de checks. A extração é guiada por esse
profile + saída estruturada obrigatória. **Não** se faz fine-tuning de modelos.

## Justificação
- **Transparência/defensabilidade**: consegue-se explicar exatamente o que guiou cada
  extração (está no YAML, versionado em git). Fine-tuning é opaco.
- **Escala sem código**: adicionar cliente/origem = editar um YAML, sem tocar em Python
  nem redeploy.
- **Custo e dados**: fine-tuning precisaria de muitos dados anotados e seria caro;
  few-shot precisa de 2–4 exemplos.
- **Robustez a mudança**: se o cliente muda o layout, ajusta-se o profile em minutos.

## Alternativas consideradas
- **Parser por cliente em código**: inmantível, cresce sem limite.
- **Fine-tuning por cliente**: opaco, caro, desatualiza.
- **Regex puro**: frágil perante variação de layout e bilinguismo PT/EN.

## Consequências
- Existe um processo operacional de "afinar profile" na fase de teste (rever → corrigir →
  virar alias/exemplo).
- A qualidade depende da curadoria dos profiles — daí o runbook `adding-a-new-source.md`.
