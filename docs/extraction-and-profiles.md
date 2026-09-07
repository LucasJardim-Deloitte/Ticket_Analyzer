# Extração e Profiles

Este documento explica o mecanismo que torna a ferramenta **escalável e transversal a
vários clientes**: como ela "aprende" o layout dos tickets de origens diferentes sem
treinar/afinar modelos.

## Porque não usamos fine-tuning

O instinto seria treinar um modelo por cliente. Rejeitámos essa via porque:

- É caro e precisa de muitos dados anotados.
- É **opaco** — não se consegue explicar *porquê* extraiu determinado valor.
- Fica desatualizado quando o cliente muda o layout dos tickets.

Ver `decisions/0002-profiles-vs-finetuning.md`.

## Como funciona: profiles guiados por exemplos

Cada **origem lógica** tem um ficheiro **`profiles/<origem>.yaml`**:

| Profile | Origem | Estado |
|---|---|---|
| `servicenow.yaml` | ServiceNow | Completo |
| `ibm_control_desk.yaml` | IBM Control Desk | Completo |
| `jira.yaml` | Jira | Esqueleto — calibrar |
| `remedy.yaml` | BMC Remedy | Esqueleto — calibrar |
| `azure_devops.yaml` | Azure DevOps | Esqueleto — calibrar |
| `bmc_helix.yaml` | BMC Helix | Esqueleto — calibrar |
| `generic.yaml` | Genérico | Esqueleto — calibrar |

O profile contém:
- **`field_aliases`** — como aquela origem chama a cada campo canónico (PT e EN).
- **`expected_states`** — estados que contam como "fechado/concluído" (regra R6).
- **`date_formats`** — formatos de data típicos daquela origem.
- **`examples`** — tickets reais + extração correta validada por auditor (*few-shot*).
- **`extraction_notes`** — instruções específicas em linguagem natural.
- **`checks`** — avaliadores ativos e seus parâmetros.

## O fluxo de extração

1. A camada de ingestão converte o ficheiro em texto (`.txt`, `.eml`, `.pdf`).
2. Carrega-se o profile da origem escolhida pelo auditor.
3. Monta-se o pedido ao modelo com: instruções + contexto do profile + texto do ticket.
4. A saída é **forçada a um JSON schema** (via *tool use*) — o modelo é obrigado a
   devolver, por campo, `value` + `source_excerpt` + `confidence`.
5. O JSON é validado por pydantic. Falhas de validação → ticket entra como `REVER`.

O modelo **só extrai**. A avaliação dos controlos é feita depois, em código.

## Calibração — como "aprender" um layout novo

O processo de calibração é operacional, não algorítmico. Usa a secção **Calibração**
da app:

1. Carrega um ticket real daquela origem.
2. A app extrai os campos automaticamente.
3. Revês e corriges os valores errados no formulário.
4. Defines um nome e clicas "Guardar exemplo".
5. O exemplo fica imediatamente no YAML do profile.

A partir daí, todas as extrações dessa origem usam o exemplo como referência.
Com 2–4 exemplos bem escolhidos, a qualidade sobe significativamente.

O ficheiro YAML é editado automaticamente pelo módulo `config/calibration.py` usando
`ruamel.yaml` (preserva comentários e formatação).

## Confiança e limiares

Cada campo traz `confidence` (0–1). Um limiar configurável (por defeito 0.6) decide
quando um campo é fiável. Campos abaixo do limiar não bloqueiam a extração, mas fazem
as regras que deles dependem devolver `REVER`. O limiar vive no profile/config.

## Adicionar uma origem nova

É uma tarefa de **configuração, não de programação**. Ver `adding-a-new-source.md`.

## Roadmap: extrator híbrido (futuro)

Quando existirem 50+ exemplos validados por origem, avaliar a implementação de um
extrator híbrido: regex/heurísticas para campos simples e bem estruturados + LLM apenas
para campos ambíguos ou em falta. Redução estimada de 60–80% das chamadas à API em
origens estabilizadas. Ver `decisions/0002-profiles-vs-finetuning.md`.
