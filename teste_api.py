"""
Teste de conectividade e tool use com o proxy corporativo.
Corre com: python teste_api.py
"""

import os
import sys

# Tenta carregar do .env se existir
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv não instalado ainda -- ok, usa variáveis do sistema

api_key  = os.getenv("ANTHROPIC_FOUNDRY_API_KEY")
base_url = os.getenv("ANTHROPIC_FOUNDRY_BASE_URL")
model    = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

print("=== Teste de Conectividade — Ticket Analyzer ===")
print(f"  base_url : {base_url}")
print(f"  api_key  : {api_key[:8]}..." if api_key else "  api_key  : NÃO DEFINIDA")
print(f"  model    : {model}")
print()

if not api_key or not base_url:
    print("❌  Variáveis de ambiente em falta.")
    print("    Garante que ANTHROPIC_FOUNDRY_API_KEY e ANTHROPIC_FOUNDRY_BASE_URL")
    print("    estão definidas (variáveis de sistema ou no ficheiro .env).")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("❌  SDK Anthropic não instalado. Corre: pip install anthropic")
    sys.exit(1)

client = anthropic.Anthropic(api_key=api_key, base_url=base_url)

# ------------------------------------------------------------------
# Teste 1 — chamada simples de texto
# ------------------------------------------------------------------
print("▶ Teste 1: chamada de texto simples...")
try:
    r = client.messages.create(
        model=model,
        max_tokens=64,
        messages=[{"role": "user", "content": "Responde apenas com: OK"}],
    )
    text = r.content[0].text.strip()
    print(f"  ✅  Resposta: {text!r}")
except Exception as e:
    print(f"  ❌  Falhou: {e}")
    print("      Verifica base_url e api_key.")
    sys.exit(1)

# ------------------------------------------------------------------
# Teste 2 — tool use (crítico para a extração)
# ------------------------------------------------------------------
print()
print("▶ Teste 2: tool use (saída estruturada)...")

SIMPLE_TOOL = {
    "name": "resultado_teste",
    "description": "Devolve um resultado de teste.",
    "input_schema": {
        "type": "object",
        "properties": {
            "mensagem": {"type": "string", "description": "Mensagem de confirmação."},
            "numero":   {"type": "integer", "description": "Número qualquer."},
        },
        "required": ["mensagem", "numero"],
    },
}

try:
    r2 = client.messages.create(
        model=model,
        max_tokens=256,
        tools=[SIMPLE_TOOL],
        tool_choice={"type": "tool", "name": "resultado_teste"},
        messages=[{
            "role": "user",
            "content": "Usa a ferramenta resultado_teste com mensagem='proxy OK' e numero=42.",
        }],
    )
    # Encontrar o bloco tool_use
    tool_block = next(
        (b for b in r2.content if getattr(b, "type", None) == "tool_use"),
        None,
    )
    if tool_block and tool_block.input.get("numero") == 42:
        print(f"  ✅  Tool use OK — input recebido: {tool_block.input}")
    elif tool_block:
        print(f"  ⚠️   Tool use respondeu mas com valores inesperados: {tool_block.input}")
    else:
        print("  ❌  Resposta não continha bloco tool_use.")
        print(f"      Conteúdo recebido: {r2.content}")
        print()
        print("  ATENÇÃO: o proxy pode não suportar tool use.")
        print("  Contacta o responsável do proxy (cst-ai-proxy) para confirmar.")
        sys.exit(1)

except Exception as e:
    print(f"  ❌  Falhou: {e}")
    sys.exit(1)

# ------------------------------------------------------------------
# Resultado final
# ------------------------------------------------------------------
print()
print("=" * 50)
print("✅  Tudo OK — proxy e tool use funcionam.")
print("   Podes avançar com a configuração da ferramenta.")
print("=" * 50)
