"""
Cliente da API Anthropic para extração estruturada.

Usa TOOL USE para forçar a saída ao schema canónico (elimina texto livre).
Devolve o CanonicalTicket + o trilho de auditoria (versão de modelo/prompt, tokens,
resposta bruta) — tudo o que sustenta a defensabilidade da extração.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from anthropic import Anthropic

from audit_tool.config.profile import Profile
from audit_tool.config.settings import Settings
from audit_tool.extraction.prompt import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
    prompt_hash,
)
from audit_tool.extraction.tool_schema import EXTRACT_TICKET_TOOL
from audit_tool.ingestion.reader import RawTicketDocument
from audit_tool.models.canonical import (
    CanonicalTicket,
    DateField,
    ExtractedField,
    OperationType,
    Person,
    RelevantDates,
)


@dataclass
class ExtractionTrail:
    """Metadados que provam como a extração foi feita — para o rastreio."""

    model: str
    prompt_version: str
    prompt_hash: str
    profile_id: str
    profile_version: int
    input_tokens: int
    output_tokens: int
    raw_response: str
    timestamp: str


@dataclass
class ExtractionResult:
    ticket: CanonicalTicket
    trail: ExtractionTrail


class ExtractionClient:
    """Encapsula chamadas à API para extração de tickets."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = Anthropic(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url,
        )

    def extract(self, doc: RawTicketDocument, profile: Profile) -> ExtractionResult:
        """Extrai um ticket. Devolve o ticket canónico + trilho de auditoria."""

        profile_context = self._build_profile_context(profile)
        user_prompt = build_user_prompt(profile_context, doc.text)

        response = self._client.messages.create(
            model=self.settings.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[EXTRACT_TICKET_TOOL],
            tool_choice={"type": "tool", "name": "extract_ticket"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        tool_input = self._extract_tool_input(response)
        ticket = self._build_ticket(tool_input, profile, doc)

        trail = ExtractionTrail(
            model=self.settings.model,
            prompt_version=PROMPT_VERSION,
            prompt_hash=prompt_hash(),
            profile_id=profile.source_id,
            profile_version=profile.version,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            raw_response=json.dumps(tool_input, ensure_ascii=False, indent=2),
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
        return ExtractionResult(ticket=ticket, trail=trail)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_profile_context(profile: Profile) -> str:
        """Prepara o contexto do profile para o prompt (aliases + exemplos)."""

        lines = [
            f"Origem: {profile.display_name} (id: {profile.source_id})",
            "",
            "Aliases dos campos (rótulos como esta origem os chama):",
        ]
        for canonical, aliases in profile.field_aliases.items():
            lines.append(f"  - {canonical}: {', '.join(aliases)}")

        if profile.date_aliases:
            lines.append("")
            lines.append("Rótulos das datas:")
            for canonical, aliases in profile.date_aliases.items():
                lines.append(f"  - {canonical}: {', '.join(aliases)}")

        if profile.expected_states:
            lines.append("")
            lines.append(f"Estados de conclusão esperados: {', '.join(profile.expected_states)}")

        if profile.extraction_notes:
            lines.append("")
            lines.append("Notas de extração:")
            lines.append(profile.extraction_notes.strip())

        if profile.examples:
            lines.append("")
            lines.append("Exemplos (few-shot):")
            for ex in profile.examples:
                lines.append(f"\n--- Exemplo: {ex.name} ---")
                lines.append("Ticket:")
                lines.append(ex.ticket_text.strip())
                lines.append("Extração esperada:")
                lines.append(json.dumps(ex.expected_extraction, ensure_ascii=False, indent=2))

        return "\n".join(lines)

    @staticmethod
    def _extract_tool_input(response: Any) -> dict:
        """Extrai o dict devolvido pela tool call. Falha claro se não encontrado."""

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "extract_ticket":
                return block.input
        raise RuntimeError("O modelo não devolveu tool_use `extract_ticket`.")

    def _build_ticket(
        self, data: dict, profile: Profile, doc: RawTicketDocument
    ) -> CanonicalTicket:
        """Converte o dict da tool call num CanonicalTicket validado."""

        def field(key: str) -> ExtractedField:
            return _to_extracted_field(data.get(key))

        def person(key: str) -> Person:
            src = data.get(key) or {}
            return Person(
                display_name=_to_extracted_field(src.get("display_name")),
                identifier=_to_extracted_field(src.get("identifier")),
            )

        return CanonicalTicket(
            source_id=profile.source_id,
            source_file=doc.source_file,
            operation_type=OperationType.CRIACAO,
            ticket_code=field("ticket_code"),
            ticket_type=field("ticket_type"),
            system=field("system"),
            environment=field("environment"),
            state=field("state"),
            requester=person("requester"),
            implementer=person("implementer"),
            approver=person("approver"),
            beneficiary=person("beneficiary"),
            dates=RelevantDates(
                request_date=_to_date_field(data.get("request_date")),
                approval_date=_to_date_field(data.get("approval_date")),
                implementation_date=_to_date_field(data.get("implementation_date")),
                validation_date=_to_date_field(data.get("validation_date")),
            ),
            justification=field("justification"),
        )


def _to_extracted_field(src: dict | None) -> ExtractedField:
    if not src:
        return ExtractedField()
    return ExtractedField(
        value=src.get("value"),
        raw_value=src.get("raw_value"),
        source_excerpt=src.get("source_excerpt"),
        confidence=float(src.get("confidence") or 0.0),
    )


def _to_date_field(src: dict | None) -> DateField:
    if not src:
        return DateField()
    value = src.get("value")
    parsed: date | None = None
    if value:
        try:
            parsed = date.fromisoformat(value)
        except (TypeError, ValueError):
            parsed = None  # deixa None; confiança baixa lida com isto
    return DateField(
        value=parsed,
        raw_value=src.get("raw_value"),
        source_excerpt=src.get("source_excerpt"),
        confidence=float(src.get("confidence") or 0.0),
    )
