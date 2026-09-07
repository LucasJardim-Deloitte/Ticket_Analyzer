"""
Configuração global da aplicação.

Lê variáveis de ambiente (via python-dotenv se existir .env, ou das variáveis de sistema).
A ligação à API usa um proxy corporativo Anthropic Foundry — requer ANTHROPIC_FOUNDRY_API_KEY
e ANTHROPIC_FOUNDRY_BASE_URL definidos como variáveis de utilizador do Windows ou no .env.

Falha cedo e com mensagem clara se algo obrigatório estiver em falta.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _project_root() -> Path:
    """Raiz do projeto = 3 níveis acima deste ficheiro (src/audit_tool/config/)."""
    return Path(__file__).resolve().parents[3]


# Carrega .env da raiz do projeto (silencioso se não existir — as variáveis de sistema
# já estão disponíveis via os.getenv sem necessidade do ficheiro .env).
load_dotenv(_project_root() / ".env")


@dataclass(frozen=True)
class Settings:
    """Configuração imutável. Instanciar uma vez com load_settings()."""

    anthropic_api_key: str
    anthropic_base_url: str
    model: str
    confidence_threshold: float
    project_root: Path
    profiles_dir: Path


# Mapa de nomes de modelo — importável pela UI para popular o seletor
MODELS: dict[str, str] = {
    "haiku":  "claude-haiku-4-5",
    "sonnet": "claude-sonnet-4-6",
    "opus":   "claude-opus-4-6",
}
DEFAULT_MODEL = "haiku" 


def load_settings() -> Settings:
    """
    Constrói Settings a partir do ambiente.

    Variáveis lidas (por ordem de prioridade: .env > variáveis de sistema):
      ANTHROPIC_FOUNDRY_API_KEY   — chave do proxy corporativo (obrigatória)
      ANTHROPIC_FOUNDRY_BASE_URL  — endpoint do proxy (obrigatório)
      ANTHROPIC_MODEL             — nome curto do modelo: haiku | sonnet | opus
                                    ou string completa do modelo
      AUDIT_CONFIDENCE_THRESHOLD  — limiar de confiança, default 0.6
    """
    api_key = os.getenv("ANTHROPIC_FOUNDRY_API_KEY", "").strip()
    base_url = os.getenv("ANTHROPIC_FOUNDRY_BASE_URL", "").strip()

    missing = []
    if not api_key:
        missing.append("ANTHROPIC_FOUNDRY_API_KEY")
    if not base_url:
        missing.append("ANTHROPIC_FOUNDRY_BASE_URL")
    if missing:
        raise ValueError(
            f"Variáveis de ambiente em falta: {', '.join(missing)}.\n"
            "Garante que estão definidas como variáveis de utilizador do Windows\n"
            "(já configuradas no teu sistema) ou no ficheiro .env da raiz do projeto."
        )

    # Resolve o modelo: aceita nome curto ("haiku") ou string completa
    model_env = os.getenv("ANTHROPIC_MODEL", "").strip()
    model = MODELS.get(model_env) or model_env or MODELS[DEFAULT_MODEL]

    root = _project_root()
    return Settings(
        anthropic_api_key=api_key,
        anthropic_base_url=base_url,
        model=model,
        confidence_threshold=float(os.getenv("AUDIT_CONFIDENCE_THRESHOLD", "0.6")),
        project_root=root,
        profiles_dir=root / "profiles",
    )
