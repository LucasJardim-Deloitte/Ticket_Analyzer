"""
Modelo canónico de um ticket de acesso.

Este é o ALVO FIXO da extração: independentemente da origem (ServiceNow, Jira, ...) ou do
formato do ficheiro (PDF, email, ...), o resultado da extração é sempre esta estrutura.
É o contrato estável entre a camada de extração (IA) e o motor de avaliação (regras).

Princípios refletidos aqui:
- Cada campo carrega a sua própria EVIDÊNCIA de extração (source_excerpt) + confiança.
- O modelo prevê remoção/alteração de acessos (operation_type) sem reescrita.
- A avaliação tem QUATRO estados, distinguindo "falhou" de "não conseguimos ler".

v0.3.1 — tester substituído por beneficiary (pessoa que recebe o acesso).
         tester não é papel de controlo para SoD e raramente aparece nos tickets.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Blocos de base
# --------------------------------------------------------------------------- #
class SourceLocation(BaseModel):
    page: Optional[int] = None
    section: Optional[str] = None


class ExtractedField(BaseModel):
    """
    Um valor extraído + a sua evidência.
    Cada campo traz o excerto-fonte de onde o valor foi tirado (evidência da extração).
    """
    value: Optional[str] = Field(None, description="Valor normalizado; None se não encontrado.")
    raw_value: Optional[str] = Field(None, description="Texto exato como aparecia no ticket.")
    source_excerpt: Optional[str] = Field(None, description="Excerto do documento (evidência).")
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    location: Optional[SourceLocation] = None

    @property
    def is_present(self) -> bool:
        return self.value is not None and self.value.strip() != ""

    def is_reliable(self, threshold: float = 0.6) -> bool:
        return self.is_present and self.confidence >= threshold


class Person(BaseModel):
    """Uma pessoa envolvida no ticket, normalizada para comparação (SoD)."""
    display_name: ExtractedField = Field(default_factory=ExtractedField)
    identifier: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Email/username — chave preferida para comparar pessoas.",
    )

    def comparison_key(self, threshold: float = 0.6) -> Optional[str]:
        """Chave para comparar pessoas na regra de SoD. Prefere identifier."""
        if self.identifier.is_reliable(threshold):
            return self.identifier.value.strip().lower()  # type: ignore[union-attr]
        if self.display_name.is_reliable(threshold):
            return self.display_name.value.strip().lower()  # type: ignore[union-attr]
        return None


class DateField(BaseModel):
    """Uma data extraída, normalizada para ISO 8601."""
    value: Optional[date] = None
    raw_value: Optional[str] = None
    source_excerpt: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)

    @property
    def is_present(self) -> bool:
        return self.value is not None

    def is_reliable(self, threshold: float = 0.6) -> bool:
        return self.is_present and self.confidence >= threshold


class RelevantDates(BaseModel):
    request_date: DateField = Field(default_factory=DateField)
    approval_date: DateField = Field(default_factory=DateField)
    implementation_date: DateField = Field(default_factory=DateField)
    validation_date: DateField = Field(default_factory=DateField)


class OperationType(str, Enum):
    CRIACAO   = "CRIACAO"
    REMOCAO   = "REMOCAO"
    ALTERACAO = "ALTERACAO"


# --------------------------------------------------------------------------- #
# O ticket canónico
# --------------------------------------------------------------------------- #
class CanonicalTicket(BaseModel):
    """Representação canónica e estável de um ticket, alvo da extração."""

    source_id:      str = Field(..., description="Origem lógica: 'servicenow', 'jira', ...")
    source_file:    Optional[str] = Field(None, description="Ficheiro de onde veio.")
    operation_type: OperationType = OperationType.CRIACAO

    # 1–5 — identificação e contexto
    ticket_code:  ExtractedField = Field(default_factory=ExtractedField)   # 1
    ticket_type:  ExtractedField = Field(default_factory=ExtractedField)   # 2
    system:       ExtractedField = Field(default_factory=ExtractedField)   # 3
    environment:  ExtractedField = Field(default_factory=ExtractedField)   # 4
    state:        ExtractedField = Field(default_factory=ExtractedField)   # 5

    # 6–9 — pessoas
    requester:    Person = Field(default_factory=Person)   # 6 — quem pediu
    implementer:  Person = Field(default_factory=Person)   # 7 — quem executou
    approver:     Person = Field(default_factory=Person)   # 8 — quem aprovou
    beneficiary:  Person = Field(default_factory=Person)   # 9 — quem recebe o acesso

    # 10 — datas
    dates: RelevantDates = Field(default_factory=RelevantDates)

    # campo de suporte a R4 (justificação)
    justification: ExtractedField = Field(default_factory=ExtractedField)

    # 11 — Evidências: realizado como source_excerpt de cada campo acima.


# --------------------------------------------------------------------------- #
# Resultado da avaliação
# --------------------------------------------------------------------------- #
class EvalStatus(str, Enum):
    CONFORME      = "CONFORME"
    EXCECAO       = "EXCECAO"
    NAO_APLICAVEL = "NAO_APLICAVEL"
    REVER         = "REVER"


class EvaluationResult(BaseModel):
    rule_id:   str
    rule_name: str
    status:    EvalStatus
    rationale: str = Field(..., description="Explicação legível do resultado.")


class TicketAssessment(BaseModel):
    ticket:  CanonicalTicket
    results: list[EvaluationResult] = Field(default_factory=list)
    overall: EvalStatus = EvalStatus.REVER
