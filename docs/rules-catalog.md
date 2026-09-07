# Catálogo de regras (avaliadores)

Cada avaliador é uma **regra determinística em Python puro**. Recebe um ticket canónico
(já extraído e validado) e devolve um `EvaluationResult` com um de quatro estados:
`CONFORME`, `EXCECAO`, `NAO_APLICAVEL`, `REVER`. As regras **não** usam o LLM.

Regra transversal: se algum campo de que a regra depende estiver ausente ou abaixo do
limiar de confiança, o resultado é **`REVER`** (não `EXCECAO`). "Falhou o controlo" e
"não conseguimos ler" são conclusões distintas.

Todas as regras são configuráveis por origem/cliente no bloco `checks` do profile.

---

## R1 — Segregação de Funções (SoD)

**Pergunta:** as funções de pedir, aprovar e implementar estão em pessoas distintas?

- **CONFORME** se `requester`, `approver` e `implementer` são três pessoas distintas.
- **EXCECAO** se duas ou mais coincidem.
- **REVER** se falta identidade fiável de algum dos três.

Comparação por `identifier` (email/username) quando existe; senão por `display_name`
normalizado. Na v1 o alvo é o **trio**; o 4º papel (`tester`) e a política de acumulação
de papéis são configuráveis (`sod.include_tester`, `sod.allow_role_overlap`) para o
futuro.

## R2 — Autorização anterior à atribuição

**Pergunta:** a aprovação ocorreu antes (ou no mesmo momento) da implementação?

- **CONFORME** se `approval_date <= implementation_date`.
- **EXCECAO** se `approval_date > implementation_date`.
- **REVER** se falta alguma das datas ou têm baixa confiança.

## R3 — Existe autorização

**Pergunta:** o ticket tem aprovação registada?

- **CONFORME** se `approver` presente **e** existe evidência de aprovação (estado/data).
- **EXCECAO** se não há aprovador nem evidência de aprovação.
- **REVER** se ambíguo.

## R4 — Acesso justificado

**Pergunta:** existe justificação para o acesso?

- **CONFORME** se o campo de justificação está **presente e não-vazio**.
- **EXCECAO** se ausente/vazio.

Nota importante: a regra verifica **presença**, não **qualidade**. Avaliar se a
justificação é *adequada* é juízo humano. A ferramenta pode anexar um flag qualitativo
da IA como auxílio, mas a decisão fica com o auditor (nunca é `EXCECAO` por qualidade).

## R5 — Validação da atribuição

**Pergunta:** a atribuição foi validada/testada?

- **CONFORME** se há `tester` e/ou evidência de validação.
- **EXCECAO** se não há.
- **NAO_APLICAVEL** se o cliente não exige validação (configurável).

## R6 — Ticket no estado esperado

**Pergunta:** o ticket está num estado de conclusão válido?

- **CONFORME** se `state ∈ expected_states` (do profile).
- **EXCECAO** se está noutro estado (aberto, em curso, cancelado…).
- **REVER** se o estado não foi extraído.

## R7 — Coerência de datas

**Pergunta:** as datas fazem sentido cronológico?

- **CONFORME** se `request_date <= approval_date <= implementation_date <= validation_date`
  (ignorando as ausentes) **e** nenhuma data está no futuro **e** todas caem no período
  de análise (se definido).
- **EXCECAO** se a ordem é violada, há data futura, ou fora do período.
- **REVER** se há poucas datas para concluir.

---

## Veredicto geral do ticket

Derivado dos resultados individuais, por política configurável:

- **Exceção** se qualquer regra crítica devolver `EXCECAO`.
- **A rever** se não há exceções mas há um ou mais `REVER`.
- **Conforme** se todas as regras aplicáveis são `CONFORME`.

Que regras são "críticas" é configurável por cliente. O veredicto nunca *esconde* um
`REVER`: ele aparece sempre, para o auditor saber onde a leitura foi incerta.

## Timeliness / SLA (opcional)

Quando o cliente define SLA, uma regra adicional verifica se
`implementation_date - request_date <= sla_days`. Fica desligada por omissão e ativa-se
no profile com `checks.timeliness.sla_days`.
