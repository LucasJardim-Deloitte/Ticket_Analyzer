# Arquitetura

## Visão geral

A ferramenta está organizada em **camadas independentes**. A lógica de negócio
(extração, modelo canónico, avaliação) não sabe que a interface Streamlit existe — o que
permite trocar a UI, correr em batch, ou migrar para uma web app na cloud **sem reescrever
o núcleo**.

```
1. Ingestão e normalização    ficheiro → texto
   .txt  .eml  .pdf (texto selecionável)
         |
2. Seleção de profile         auditor escolhe a origem manualmente
   profiles/*.yaml
         |
3. Extração (LLM)             JSON schema obrigatório via tool use
   campos + evidência + confiança
         |
4. Modelo canónico            pydantic — validação forte
   models/canonical.py
         |
5. Motor de avaliação         regras determinísticas (Python puro)
   rules/engine.py
         |
6. Apresentação + Exportação  Streamlit UI + workpaper Excel
   app.py  /  export/excel.py

Transversais:
  profiles/*.yaml   — aliases, exemplos, config por origem
  config/calibration.py — edição automática de profiles
  Trilho de auditoria — versão modelo/prompt, tokens, timestamp
```

## As camadas em detalhe

### 1. Ingestão e normalização
Recebe o ficheiro e transforma-o em texto. Um adaptador por **formato físico**:

| Formato | Adaptador | Notas |
|---|---|---|
| `.txt` | leitura direta | tolerante a encoding (utf-8, latin-1, cp1252) |
| `.eml` | stdlib `email` | extrai cabeçalhos + corpo texto |
| `.pdf` | `pdfplumber` | texto selecionável; PDFs digitalizados devolvem aviso |

Suporta **1 ficheiro = 1 ticket** e **1 ficheiro = N tickets** (separador `---TICKET---`).

### 2. Seleção de profile
O auditor **escolhe manualmente** a origem no upload. Decisão deliberada: auto-detetar
mal introduz erro silencioso numa ferramenta de auditoria.

### 3. Extração (LLM)
Envia ao modelo: texto do ticket + esquema canónico (via *tool use*) + profile da origem
(aliases, exemplos few-shot, notas). Devolve, por campo: **valor**, **excerto-fonte**
(evidência) e **confiança**. O modelo nunca avalia controlos.

A ligação à API usa o **proxy corporativo Anthropic Foundry** via variáveis de ambiente
`ANTHROPIC_FOUNDRY_API_KEY` e `ANTHROPIC_FOUNDRY_BASE_URL` (definidas como variáveis
de utilizador Windows).

### 4. Modelo canónico
Os 11 campos validados por **pydantic**. Inclui `tipo_operacao`
(CRIACAO/REMOCAO/ALTERACAO) para o roadmap futuro. Ver `data-model.md`.

### 5. Motor de avaliação
7 regras **determinísticas em Python puro**. Cada regra devolve um de **quatro** estados:
`CONFORME`, `EXCECAO`, `NAO_APLICAVEL`, `REVER`. Testado a 100% com `pytest`.
Ver `rules-catalog.md`.

### 6. Apresentação e exportação
- **Tabela global**: 1 linha por ticket, campos + resultado por avaliador + veredicto
- **Drill-down**: valor + excerto-fonte + confiança por campo; cards de controlos
- **Calibração**: secção separada para validar extrações e guardar exemplos nos profiles
- **Workpaper Excel**: abas Resumo, Análise, Exceções, Rastreio

## Transversais

### Profiles (YAML)
Tudo o que varia por cliente/origem — aliases, exemplos few-shot, estados esperados,
thresholds. **Nada hard-coded.** Adicionar uma origem = criar um YAML.
Ver `extraction-and-profiles.md` e `adding-a-new-source.md`.

### Calibração
`config/calibration.py` — edita os profiles YAML automaticamente quando o auditor valida
e guarda um exemplo na UI. Usa `ruamel.yaml` para preservar comentários e formatação.

### Trilho de auditoria
Por cada extração regista: versão do modelo, hash do prompt, profile e versão, tokens,
timestamp. Vai para a aba `Rastreio` do workpaper.

### Costura de pseudonimização
Ponto único antes do envio à API, desligado por omissão. Ativável por flag de config
se um cliente futuro exigir que dados não saiam para a API.

## Persistência
Na v1, análises vivem **só em sessão**. A forma de guardar é exportar o workpaper Excel.
A camada de dados está desenhada para receber um back-end SQLite no futuro sem alterar
as camadas 3–5.

## Fronteira de reutilização
As camadas 3, 4 e 5 vivem em `src/audit_tool/` sem dependências de UI. Uma futura
API FastAPI, runner de batch ou outra UI consomem o mesmo núcleo.

## Tipo de ticket (v0.3+)
A UI distingue **Acessos** (operacional) de **Alterações ao Sistema** (em desenvolvimento).
O campo `tipo_operacao` no modelo canónico já prevê CRIACAO / REMOCAO / ALTERACAO para
o roadmap de remoção e alteração de acessos.
