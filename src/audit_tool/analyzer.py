"""
Fachada principal: recebe ficheiros + profile, devolve assessments.

É o único ponto de entrada que a UI (Streamlit) e futuras integrações usam.
Assim garantimos que a UI não sabe nada sobre extração ou regras — só chama isto.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from audit_tool.config.profile import Profile
from audit_tool.config.settings import Settings
from audit_tool.extraction.client import ExtractionClient, ExtractionTrail
from audit_tool.ingestion.reader import read_file
from audit_tool.models.canonical import TicketAssessment
from audit_tool.rules.engine import RuleConfig, evaluate


@dataclass
class AnalyzedTicket:
    """Um ticket processado: assessment + trilho de auditoria."""

    assessment: TicketAssessment
    trail: ExtractionTrail


class Analyzer:
    """Orquestra: ingestão -> extração -> avaliação, por cada ticket."""

    def __init__(self, settings: Settings, profile: Profile):
        self.settings = settings
        self.profile = profile
        self._extractor = ExtractionClient(settings)
        self._rule_config = self._build_rule_config()

    def analyze_files(self, paths: list[Path]) -> Iterator[AnalyzedTicket]:
        """
        Processa múltiplos ficheiros, devolvendo cada ticket à medida que fica pronto.

        É um iterador para a UI poder mostrar resultados incrementalmente e não
        bloquear em cargas grandes.
        """
        for path in paths:
            for doc in read_file(path):
                extraction = self._extractor.extract(doc, self.profile)
                assessment = evaluate(extraction.ticket, self._rule_config)
                yield AnalyzedTicket(assessment=assessment, trail=extraction.trail)

    def _build_rule_config(self) -> RuleConfig:
        checks = self.profile.checks
        return RuleConfig(
            confidence_threshold=checks.confidence_threshold,
            expected_states=tuple(self.profile.expected_states),
            sod_include_tester=checks.sod.include_tester,
            require_validation=checks.validation.required,
            timeliness_enabled=checks.timeliness.enabled,
            timeliness_sla_days=checks.timeliness.sla_days,
        )
