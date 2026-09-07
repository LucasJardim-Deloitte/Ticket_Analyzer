# Setup (Windows / PowerShell)

Guia passo a passo para pôr a ferramenta a correr localmente.
Requer Python 3.11 ou superior.

## 1. Verificar Python

```powershell
python --version
```

Deve dizer `Python 3.11.x` ou superior. Se não tiveres, instala de python.org
e marca **"Add Python to PATH"** no instalador.

## 2. Ir para a pasta do projeto

```powershell
cd "C:\GenAI\Ticket Analyzer Deloitte"
```

## 3. Criar e ativar ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> **Se der erro de execução de scripts:** correr uma vez
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
> e voltar a ativar. Só é preciso a primeira vez.

Quando o venv está ativo, o prompt fica com `(.venv)` no início.
**O venv tem de estar ativo sempre que usas a ferramenta.**

## 4. Instalar dependências

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

Dependências principais: `anthropic`, `streamlit`, `pdfplumber`, `openpyxl`,
`pydantic`, `ruamel.yaml`.

## 5. Verificar variáveis de ambiente

As credenciais do proxy corporativo devem estar definidas como variáveis de
utilizador Windows (já configuradas). Para verificar:

```powershell
[System.Environment]::GetEnvironmentVariable("ANTHROPIC_FOUNDRY_API_KEY","User")
[System.Environment]::GetEnvironmentVariable("ANTHROPIC_FOUNDRY_BASE_URL","User")
```

Ambas devem devolver valores. Se não, definir:

```powershell
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_FOUNDRY_API_KEY","cst-...", "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_FOUNDRY_BASE_URL","https://cst-ai-proxy.azurewebsites.net/api/anthropic", "User")
```

## 6. (Opcional) Adicionar logotipo

Colocar o ficheiro PNG do logotipo Deloitte em:
```
C:\GenAI\Ticket Analyzer Deloitte\assets\logo.png
```
A pasta `assets\` pode ter de ser criada. Sem o ficheiro, aparece "Deloitte"
em texto como fallback.

## 7. Testar conectividade

```powershell
python teste_api.py
```

Deve mostrar `✅ Tudo OK` nos dois testes (texto simples + tool use).

## 8. Correr os testes unitários

```powershell
pytest
```

37 testes devem passar sem erros.

## 9. Arrancar a aplicação

```powershell
streamlit run app.py
```

O browser abre em `http://localhost:8501`. Se não abrir automaticamente,
cola o endereço no browser.

## Utilizações seguintes

```powershell
cd "C:\GenAI\Ticket Analyzer Deloitte"
.\.venv\Scripts\Activate.ps1      ← obrigatório
streamlit run app.py
```

## Formatos de ticket suportados

| Formato | Extensão | Notas |
|---|---|---|
| Texto | `.txt` | Qualquer encoding |
| Email | `.eml` | Extrai cabeçalhos + corpo |
| PDF | `.pdf` | Apenas texto selecionável; PDFs digitalizados não são suportados |

## Resolução de problemas

| Erro | Solução |
|---|---|
| `'streamlit' is not recognized` | O venv não está ativo — correr `.\.venv\Scripts\Activate.ps1` |
| `ANTHROPIC_FOUNDRY_API_KEY em falta` | Ver passo 5 |
| `401 authentication_error` | Verificar que as variáveis de ambiente estão definidas e corretas |
| PDF sem texto extraído | O PDF é digitalizado (imagem) — converter para texto ou `.txt` |
| `ModuleNotFoundError` | Correr `pip install -r requirements.txt` com o venv ativo |

## Estrutura da pasta

```
C:\GenAI\Ticket Analyzer Deloitte\
├── app.py                    ← aplicação Streamlit
├── requirements.txt
├── SETUP.md                  ← este ficheiro
├── README.md
├── CHANGELOG.md
├── teste_api.py              ← teste de conectividade
├── .env.example              ← template (opcional — variáveis já no sistema)
├── assets\                   ← logo.png (opcional)
├── docs\                     ← documentação técnica
├── profiles\                 ← YAMLs por origem (ServiceNow, IBM Control Desk, ...)
├── samples\                  ← tickets de exemplo (.txt)
├── src\audit_tool\           ← código do pacote
│   ├── analyzer.py
│   ├── config\               ← settings, profile loader, calibração
│   ├── ingestion\            ← leitura de ficheiros (txt, eml, pdf)
│   ├── extraction\           ← cliente Anthropic (tool use)
│   ├── models\               ← modelo canónico pydantic
│   ├── rules\                ← motor de avaliação (7 regras)
│   └── export\               ← gerador de workpaper Excel
└── tests\                    ← suite pytest (37 testes)
```
