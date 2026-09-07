# Changelog

## v0.3 — PDF, calibração e profiles multi-origem

### Adicionado
- **Ingestão PDF** (`ingestion/reader.py`): adaptador `pdfplumber` para PDFs com texto
  selecionável. PDFs digitalizados (imagem) devolvem aviso claro em vez de falhar
  silenciosamente. File uploader na UI aceita agora `.txt`, `.eml` e `.pdf`.
- **Modo de calibração** (secção separada na app): carregar ticket → extrair → corrigir
  campo a campo → guardar como exemplo validado no profile YAML. Lista e remoção de
  exemplos existentes por profile.
- **`config/calibration.py`**: edição automática de profiles YAML com `ruamel.yaml`
  (preserva comentários). Funções: `add_example_to_profile`, `remove_example_from_profile`,
  `list_examples`.
- **Profile IBM Control Desk** (`profiles/ibm_control_desk.yaml`): completo com aliases
  típicos do IBM Control Desk / Maximo ITSM, datas, estados e notas de extração.
- **Profiles esqueleto** prontos para calibrar: Jira, BMC Remedy, Azure DevOps, BMC
  Helix, Genérico (`profiles/*.yaml`).
- `ruamel.yaml>=0.18` e `pdfplumber>=0.11` adicionados ao `requirements.txt`.
- Documentação atualizada: `architecture.md`, `extraction-and-profiles.md`.

### Por fazer (v0.4+)
- Ingestão `.msg` (Outlook).
- Persistência opcional de análises (SQLite).
- Extrator híbrido regex + LLM após acumulação de exemplos validados.
- Remoção de acessos e alteração de acessos (v2).

---

## v0.2.1 — Identidade visual Deloitte + melhorias de UX

### Adicionado
- Header preto com logo (ou fallback em texto), linha verde, sidebar preta.
- Seletor de modelo AI em runtime (Haiku / Sonnet / Opus).
- Seletor de tipo de ticket (Acessos / Alterações ao Sistema — WIP).
- `validation.required: false` no profile ServiceNow (elimina falsos positivos em R5).

---

## v0.2 — Núcleo end-to-end funcional

### Adicionado
- Configuração via variáveis de ambiente corporativas (`ANTHROPIC_FOUNDRY_API_KEY`,
  `ANTHROPIC_FOUNDRY_BASE_URL`). Proxy HTTP Anthropic Foundry.
- Ingestão `.txt` e `.eml`.
- Extração via API Anthropic com *tool use* (saída estruturada garantida).
- 7 regras implementadas (R1–R7) com suite pytest completa (37 testes).
- UI Streamlit com cores da marca: tabela global + drill-down com evidência.
- Exportador Excel (4 abas: Resumo, Análise, Exceções, Rastreio).
- Trilho de auditoria (versão modelo/prompt, tokens, timestamp).
- Samples de teste (`samples/`). `SETUP.md` para Windows/PowerShell.

---

## v0.1 — Planeamento e scaffolding

- Documentação em `docs/` + ADRs.
- Modelo canónico em pydantic.
- Esqueleto do motor de regras (R1, R2, R6, R7).
- Profile de exemplo ServiceNow.
