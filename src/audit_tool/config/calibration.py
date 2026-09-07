"""
Módulo de calibração — guarda exemplos validados pelo auditor nos profiles YAML.

Fluxo:
1. Auditor analisa um ticket na secção de Calibração
2. Revê os campos extraídos e corrige o que estiver errado
3. Clica "Guardar como exemplo" — este módulo adiciona o exemplo ao profile YAML

O profile YAML é editado em memória com ruamel.yaml para preservar comentários
e formatação existentes. Se ruamel.yaml não estiver instalado, cai para pyyaml
(perde comentários mas funciona).

Decisão de design: edição automática do YAML (mais fluida para uso individual).
Ver docs/decisions/0002-profiles-vs-finetuning.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def add_example_to_profile(
    profile_path: Path,
    example_name: str,
    ticket_text: str,
    extraction: dict[str, Any],
) -> None:
    """
    Adiciona um exemplo validado ao profile YAML.

    Cria a chave `examples` se não existir.
    Substitui um exemplo existente com o mesmo nome (idempotente).

    Args:
        profile_path:  caminho para o ficheiro YAML do profile
        example_name:  nome curto e descritivo (ex: "servicenow_conforme_sap")
        ticket_text:   texto do ticket tal como foi lido (ou excerto representativo)
        extraction:    dicionário com os valores corrigidos pelo auditor
    """
    content = _load_yaml(profile_path)

    if "examples" not in content or content["examples"] is None:
        content["examples"] = []

    # Remove exemplo com o mesmo nome se já existir (substituição)
    content["examples"] = [
        ex for ex in content["examples"]
        if ex.get("name") != example_name
    ]

    new_example = {
        "name": example_name,
        "ticket_text": _truncate_for_yaml(ticket_text),
        "expected_extraction": extraction,
    }
    content["examples"].append(new_example)

    _save_yaml(profile_path, content)


def remove_example_from_profile(profile_path: Path, example_name: str) -> bool:
    """
    Remove um exemplo pelo nome. Devolve True se removeu, False se não encontrou.
    """
    content = _load_yaml(profile_path)
    examples = content.get("examples") or []
    new_examples = [ex for ex in examples if ex.get("name") != example_name]
    if len(new_examples) == len(examples):
        return False
    content["examples"] = new_examples
    _save_yaml(profile_path, content)
    return True


def list_examples(profile_path: Path) -> list[str]:
    """Devolve os nomes dos exemplos guardados num profile."""
    content = _load_yaml(profile_path)
    return [ex.get("name", "") for ex in (content.get("examples") or [])]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate_for_yaml(text: str, max_chars: int = 2000) -> str:
    """
    Trunca o texto do ticket para não inflar o YAML.
    2000 chars é suficiente para o few-shot; o LLM não precisa do ticket completo.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[... truncado para exemplo ...]"


def _load_yaml(path: Path) -> dict:
    """Carrega YAML preservando estrutura. Tenta ruamel primeiro, cai para pyyaml."""
    try:
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        with open(path, encoding="utf-8") as f:
            return yaml.load(f) or {}
    except ImportError:
        import yaml as pyyaml
        with open(path, encoding="utf-8") as f:
            return pyyaml.safe_load(f) or {}


def _save_yaml(path: Path, content: dict) -> None:
    """Guarda YAML preservando estrutura se possível."""
    try:
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        yaml.indent(mapping=2, sequence=4, offset=2)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(content, f)
    except ImportError:
        import yaml as pyyaml
        with open(path, "w", encoding="utf-8") as f:
            pyyaml.dump(content, f, allow_unicode=True, default_flow_style=False)
