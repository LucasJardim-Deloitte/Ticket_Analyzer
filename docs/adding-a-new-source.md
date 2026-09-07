# Runbook: adicionar uma origem nova

Objetivo: suportar tickets de uma origem/cliente novo **sem alterar código** — apenas
criando um profile YAML. Requer ~30 min e alguns tickets reais de exemplo.

## Pré-requisitos

- 3 a 5 tickets reais representativos da nova origem.
- Saber que estados aquela origem usa para "concluído/fechado".

## Passos

1. **Copiar o template.** Duplicar `profiles/servicenow.yaml` para
   `profiles/<nova-origem>.yaml` e ajustar `source_id` e `display_name`.

2. **Preencher os aliases.** Para cada campo canónico, listar todos os rótulos que a
   origem usa, em PT e EN. Exemplo:
   ```yaml
   field_aliases:
     requester: ["Solicitante", "Requested by", "Caller", "Opened by"]
   ```
   Regra prática: abrir um ticket real e, para cada valor que se quer extrair, anotar
   exatamente o rótulo que o antecede.

3. **Definir os estados esperados.** Listar em `expected_states` os estados que contam
   como concluído (ex.: `["Closed Complete", "Fechado", "Resolvido"]`).

4. **Declarar os formatos de data.** Em `date_formats`, os padrões usados (ex.:
   `"%d/%m/%Y %H:%M"`, `"%Y-%m-%d"`).

5. **Adicionar exemplos few-shot.** Colar 2–4 tickets reais e, ao lado, a extração
   correta. Este é o passo que mais melhora a qualidade. Anonimizar se necessário.

6. **Configurar os checks.** Em `checks`, ativar/desativar avaliadores e definir
   parâmetros (ex.: `sla_days`).

7. **Testar.** Correr a app, escolher a nova origem, carregar os tickets de teste, rever
   o drill-down. Corrigir aliases/exemplos até a extração estabilizar.

8. **Documentar.** Registar no `CHANGELOG.md` a nova origem e, se houve decisões não
   óbvias, um ADR em `docs/decisions/`.

## Boas práticas

- **Um alias por variação real observada** — não inventar variações hipotéticas.
- **Preferir `identifier` (email/username)** aos nomes nos campos de pessoas, para a
  comparação de SoD ser fiável.
- **Não hard-codar nada no código** — se aparece a tentação de tratar um caso especial
  em Python, provavelmente é um campo de profile em falta.
- Manter os exemplos **curtos e representativos**; muitos exemplos longos aumentam custo
  de tokens sem ganho proporcional.
