"""Fixtures partilhadas dos testes."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

# Adiciona src/ ao path para os testes correrem sem instalar o pacote
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from audit_tool.models.canonical import (  # noqa: E402
    CanonicalTicket,
    DateField,
    ExtractedField,
    Person,
    RelevantDates,
)
from audit_tool.rules.engine import RuleConfig  # noqa: E402


def _f(value: str | None, confidence: float = 0.9) -> ExtractedField:
    return ExtractedField(value=value, confidence=confidence)


def _df(value: date | None, confidence: float = 0.9) -> DateField:
    return DateField(value=value, confidence=confidence)


def _person(name: str | None, email: str | None, confidence: float = 0.9) -> Person:
    return Person(display_name=_f(name, confidence), identifier=_f(email, confidence))


@pytest.fixture
def make_ticket():
    """Fábrica que produz tickets canónicos com defaults sensatos e overrides."""

    def _make(
        *,
        state: str | None = "Closed Complete",
        requester_email: str | None = "ana@x.pt",
        approver_email: str | None = "carla@x.pt",
        implementer_email: str | None = "diogo@x.pt",
        tester_email: str | None = None,  # reused as beneficiary_email for fixture compat
        request_date: date | None = date(2026, 2, 1),
        approval_date: date | None = date(2026, 2, 3),
        implementation_date: date | None = date(2026, 2, 4),
        validation_date: date | None = None,
        justification: str | None = "Novo colaborador",
        low_confidence_fields: tuple[str, ...] = (),
    ) -> CanonicalTicket:
        def conf(name: str) -> float:
            return 0.2 if name in low_confidence_fields else 0.9

        return CanonicalTicket(
            source_id="test",
            source_file="test.txt",
            ticket_code=_f("RITM0001", conf("ticket_code")),
            ticket_type=_f("Criação de acesso"),
            system=_f("SAP"),
            environment=_f("Produção"),
            state=_f(state, conf("state")),
            requester=_person("Requester", requester_email, conf("requester")),
            approver=_person("Approver", approver_email, conf("approver")),
            implementer=_person("Implementer", implementer_email, conf("implementer")),
            beneficiary=_person("Beneficiário", tester_email, conf("beneficiary")),
            dates=RelevantDates(
                request_date=_df(request_date, conf("request_date")),
                approval_date=_df(approval_date, conf("approval_date")),
                implementation_date=_df(implementation_date, conf("implementation_date")),
                validation_date=_df(validation_date, conf("validation_date")),
            ),
            justification=_f(justification, conf("justification")),
        )

    return _make


@pytest.fixture
def default_config() -> RuleConfig:
    return RuleConfig(
        confidence_threshold=0.6,
        expected_states=("Closed Complete", "Fechado"),
        sod_include_tester=False,
        require_validation=False,  # tickets base não têm tester
    )
