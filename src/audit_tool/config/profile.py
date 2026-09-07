"""
Carregamento e validação de profiles YAML.

Um profile descreve uma origem lógica (ServiceNow, Jira, ...) — aliases de campos,
estados esperados, formatos de data, exemplos few-shot e configuração dos checks.

Modelo em pydantic para validação forte: se um profile estiver mal formado, falha
imediatamente com erro claro, em vez de partir a extração mais tarde.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SoDConfig(BaseModel):
    include_tester: bool = False
    allow_role_overlap: bool = False


class ValidationConfig(BaseModel):
    required: bool = True


class TimelinessConfig(BaseModel):
    enabled: bool = False
    sla_days: int | None = None


class ChecksConfig(BaseModel):
    confidence_threshold: float = 0.6
    sod: SoDConfig = Field(default_factory=SoDConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    timeliness: TimelinessConfig = Field(default_factory=TimelinessConfig)


class Example(BaseModel):
    name: str
    ticket_text: str
    expected_extraction: dict[str, Any]


class Profile(BaseModel):
    """Modelo tipado de um profile YAML."""

    source_id: str
    display_name: str
    version: int = 1

    field_aliases: dict[str, list[str]] = Field(default_factory=dict)
    date_aliases: dict[str, list[str]] = Field(default_factory=dict)
    date_formats: list[str] = Field(default_factory=list)
    expected_states: list[str] = Field(default_factory=list)
    extraction_notes: str = ""
    examples: list[Example] = Field(default_factory=list)
    checks: ChecksConfig = Field(default_factory=ChecksConfig)


def load_profile(path: Path) -> Profile:
    """Carrega um profile de um caminho YAML."""

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Profile.model_validate(data)


def list_available_profiles(profiles_dir: Path) -> dict[str, Path]:
    """
    Descobre todos os profiles disponíveis na pasta.

    Devolve um dict {display_name: caminho} pronto para popular um dropdown na UI.
    """

    result: dict[str, Path] = {}
    if not profiles_dir.exists():
        return result
    for path in sorted(profiles_dir.glob("*.yaml")):
        try:
            profile = load_profile(path)
            result[profile.display_name] = path
        except Exception:  # noqa: BLE001 - profile mal formado é ignorado (log seria melhor)
            continue
    return result
