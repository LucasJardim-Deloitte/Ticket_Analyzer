# Ticket Analyzer — Auditoria de Acessos

Ferramenta interna de apoio à Auditoria de IT para **análise de tickets de gestão de
acessos**. Na v1 cobre a **criação de perfis/acessos**; está desenhada para estender-se
depois a **remoção** e **alteração** de acessos sem reescrita.

## Como começar

Ver `SETUP.md` para instruções passo a passo em Windows/PowerShell. TL;DR:

```powershell
cd "C:\GenAI\Ticket Analyzer Deloitte"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # e preencher a chave
streamlit run app.py
```

## Princípios de desenho

1. **A IA extrai. O código julga.** O LLM lê o ticket e devolve campos estruturados
   com evidência. As regras de auditoria (segregação de funções, aprovação prévia, etc.)
   são avaliadas por código Python puro, determinístico e testado com pytest. Isto torna
   as conclusões reproduzíveis e defensáveis. Ver `docs/decisions/0001-*.md`.

2. **Configuração, não código.** Adicionar uma origem nova (ServiceNow, Jira, …) ou um
   cliente novo é criar um ficheiro YAML em `profiles/`. Zero alterações de código. Ver
   `docs/decisions/0002-*.md`.

3. **Quatro estados, não dois.** Cada regra devolve `CONFORME`, `EXCECAO`,
   `NAO_APLICAVEL` ou `REVER` (dados insuficientes). Distinguir "o controlo falhou" de
   "não conseguimos ler" é crítico em auditoria.

## Estrutura do repositório

```
├── app.py                       ← aplicação Streamlit (interface)
├── requirements.txt
├── SETUP.md                     ← guia de instalação passo a passo
├── docs/                        ← documentação técnica (ler primeiro)
├── profiles/                    ← um YAML por origem (ServiceNow, ...)
├── samples/                     ← tickets de exemplo para testar
├── src/audit_tool/              ← núcleo do pacote (independente da UI)
│   ├── analyzer.py                fachada principal
│   ├── config/                    settings + profile loader
│   ├── ingestion/                 leitura de ficheiros
│   ├── extraction/                cliente Anthropic (tool use)
│   ├── models/canonical.py        modelo canónico do ticket
│   ├── rules/engine.py            motor de regras (determinístico)
│   └── export/excel.py            gerador de workpaper Excel
└── tests/                       ← suite pytest
```

## Estado atual (v0.2)

- ✅ Configuração via `.env`, loader de profiles YAML validado com pydantic
- ✅ Ingestão: `.txt` e `.eml`, com suporte a N tickets por ficheiro
- ✅ Extração via API Anthropic com **tool use** (saída estruturada garantida)
- ✅ **7 regras** implementadas (R1–R7), com suite pytest completa
- ✅ UI Streamlit com cores da marca (tabela global + drill-down com evidência)
- ✅ Exportador Excel (4 abas: Resumo, Análise, Exceções, Rastreio)
- ✅ Trilho de auditoria (versão modelo/prompt, tokens, timestamp)

## Próximos passos (v0.3+)

- Ingestão: PDF, `.msg` (Outlook), Excel, HTML, imagens (OCR/vision)
- Persistência de análises (SQLite opcional)
- Pseudonimização opcional para clientes com restrições contratuais
- Regras adicionais quando definidas pela equipa (ex.: SLA/timeliness)
- v2: remoção de acessos, alteração de acessos
- v3: least-privilege, geração de amostragem
