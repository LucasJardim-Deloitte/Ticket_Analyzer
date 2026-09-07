# Modelo de dados canónico

O **modelo canónico** é o alvo fixo da extração: independentemente da origem
(ServiceNow, Jira, …) ou do formato (PDF, email, …), o resultado é sempre esta mesma
estrutura. É o contrato estável entre a camada de extração (IA) e o motor de avaliação
(regras). Implementação em `src/audit_tool/models/canonical.py`.

## Princípio: cada campo carrega a sua evidência

O campo original "Evidências" (nº 11 da lista) foi **clarificado como evidência da
extração**. Por isso não é uma coluna solta: realiza-se como o **excerto-fonte anexado a
cada campo**. Cada valor extraído vem sempre acompanhado de:

- `value` — o valor normalizado (ou `null` se não encontrado)
- `raw_value` — o texto exato como aparecia no ticket (antes de normalizar)
- `source_excerpt` — o excerto do documento de onde o valor foi tirado (**a evidência**)
- `confidence` — confiança da extração, 0.0–1.0
- `location` — página/secção, quando aplicável

Isto permite a um auditor verificar cada valor sem reabrir o ticket, e é o que sustenta a
coluna `Rastreio` do workpaper.

## Os campos

| # | Campo canónico | `field` | Notas |
|---|---|---|---|
| 1 | Código do ticket | `ticket_code` | Identificador único no sistema de origem |
| 2 | Tipo | `ticket_type` | Ex.: criação de acesso, novo perfil… |
| 3 | Sistema | `system` | Sistema/aplicação alvo do acesso |
| 4 | Ambiente | `environment` | Produção, Qualidade, Desenvolvimento… |
| 5 | Estado | `state` | Estado do ticket na origem (ver `expected_states`) |
| 6 | Quem fez o request | `requester` | Solicitante |
| 7 | Quem implementou | `implementer` | Quem executou a atribuição |
| 8 | Quem aprovou | `approver` | Aprovador |
| 9 | Quem testou | `tester` | Quem validou a atribuição (4º papel) |
| 10 | Datas relevantes | `dates` | request / approval / implementation / validation |
| 11 | Evidências | *(dissolvido)* | Realizado como `source_excerpt` de cada campo |

## Datas (campo 10, detalhado)

`dates` é um objeto com quatro datas, cada uma um campo extraído completo (valor +
evidência + confiança):

- `request_date` — data do pedido
- `approval_date` — data da aprovação
- `implementation_date` — data da implementação/atribuição
- `validation_date` — data da validação/teste

Como os tickets vêm em **PT e EN** e de origens diferentes, os formatos de data são
declarados por origem no profile (`date_formats`) e normalizados para ISO 8601 na
extração.

## Identidade das pessoas (para a Segregação de Funções)

`requester`, `approver`, `implementer` e `tester` são normalizados para permitir
comparação fiável (a regra de SoD compara pessoas). Guarda-se:

- `display_name` — nome como aparece
- `identifier` — email/username quando disponível (chave de comparação preferida)

A comparação da SoD usa `identifier` quando existe; caso contrário cai para `display_name`
normalizado. Se a identidade for ambígua, a regra devolve `REVER`, não `EXCECAO`.

## Campo para o futuro: `tipo_operacao`

O modelo inclui `operation_type` com valores `CRIACAO` | `REMOCAO` | `ALTERACAO`. Na v1
é sempre `CRIACAO`. Está presente desde já para que remoção e alteração de acessos (v2)
não obriguem a reescrever o modelo nem os exports.

## Estados de avaliação

Cada avaliador (regra) produz um `EvaluationResult` com um de **quatro** estados:

- `CONFORME` — o controlo passou
- `EXCECAO` — o controlo falhou
- `NAO_APLICAVEL` — a regra não se aplica a este ticket
- `REVER` — **não foi possível concluir** por dados insuficientes ou baixa confiança na
  extração

A distinção `EXCECAO` vs `REVER` é deliberada e crítica: "o controlo falhou" e "não
conseguimos ler o ticket" são conclusões diferentes e nunca devem ser confundidas.
