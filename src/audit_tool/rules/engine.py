"""
Motor de avaliação — regras determinísticas em Python puro.

NUNCA usa o LLM. Recebe um CanonicalTicket (já extraído) e produz um TicketAssessment.
Cada regra devolve um de quatro estados: CONFORME, EXCECAO, NAO_APLICAVEL, REVER.

Regra transversal: se faltar informação fiável para decidir, o resultado é REVER
(não EXCECAO). "O controlo falhou" e "não conseguimos ler" são conclusões distintas.

100% testável com pytest — o que sustenta a defensabilidade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from audit_tool.models.canonical import (
    CanonicalTicket,
    EvalStatus,
    EvaluationResult,
    TicketAssessment,
)


@dataclass
class RuleConfig:
    """Parâmetros vindos do profile/config do cliente. Nada hard-coded."""

    confidence_threshold: float = 0.6
    expected_states: tuple[str, ...] = ()
    sod_include_tester: bool = False
    require_validation: bool = True
    timeliness_enabled: bool = False
    timeliness_sla_days: int | None = None

    def __post_init__(self):
        # Normaliza estados esperados para comparação case-insensitive
        object.__setattr__(
            self,
            "expected_states",
            tuple(s.strip().lower() for s in self.expected_states),
        )


# --------------------------------------------------------------------------- #
# R1 — Segregação de Funções
# --------------------------------------------------------------------------- #
def r1_segregation_of_duties(t: CanonicalTicket, c: RuleConfig) -> EvaluationResult:
    keys = {
        "requester": t.requester.comparison_key(c.confidence_threshold),
        "approver": t.approver.comparison_key(c.confidence_threshold),
        "implementer": t.implementer.comparison_key(c.confidence_threshold),
    }
    # beneficiary não entra na SoD — não é papel de controlo

    if any(v is None for v in keys.values()):
        return EvaluationResult(
            rule_id="R1",
            rule_name="Segregação de Funções",
            status=EvalStatus.REVER,
            rationale="Identidade insuficiente num ou mais papéis para comparar.",
        )

    present = [v for v in keys.values() if v]
    if len(set(present)) == len(present):
        return EvaluationResult(
            rule_id="R1",
            rule_name="Segregação de Funções",
            status=EvalStatus.CONFORME,
            rationale="Pedido, aprovação e implementação em pessoas distintas.",
        )

    seen: dict[str, str] = {}
    collisions = []
    for role, key in keys.items():
        if key in seen:
            collisions.append(f"{seen[key]}={role}")
        else:
            seen[key] = role
    return EvaluationResult(
        rule_id="R1",
        rule_name="Segregação de Funções",
        status=EvalStatus.EXCECAO,
        rationale="Acumulação de papéis: " + ", ".join(collisions) + ".",
    )


# --------------------------------------------------------------------------- #
# R2 — Autorização anterior à atribuição
# --------------------------------------------------------------------------- #
def r2_approval_before_implementation(
    t: CanonicalTicket, c: RuleConfig
) -> EvaluationResult:
    appr = t.dates.approval_date
    impl = t.dates.implementation_date
    if not (
        appr.is_reliable(c.confidence_threshold)
        and impl.is_reliable(c.confidence_threshold)
    ):
        return EvaluationResult(
            rule_id="R2",
            rule_name="Autorização anterior à atribuição",
            status=EvalStatus.REVER,
            rationale="Falta data de aprovação e/ou de implementação fiável.",
        )
    if appr.value <= impl.value:  # type: ignore[operator]
        return EvaluationResult(
            rule_id="R2",
            rule_name="Autorização anterior à atribuição",
            status=EvalStatus.CONFORME,
            rationale=f"Aprovação ({appr.value}) ≤ implementação ({impl.value}).",
        )
    return EvaluationResult(
        rule_id="R2",
        rule_name="Autorização anterior à atribuição",
        status=EvalStatus.EXCECAO,
        rationale=f"Aprovação ({appr.value}) posterior à implementação ({impl.value}).",
    )


# --------------------------------------------------------------------------- #
# R3 — Existe autorização
# --------------------------------------------------------------------------- #
def r3_authorization_exists(t: CanonicalTicket, c: RuleConfig) -> EvaluationResult:
    has_approver = t.approver.comparison_key(c.confidence_threshold) is not None
    has_approval_date = t.dates.approval_date.is_reliable(c.confidence_threshold)

    if has_approver and has_approval_date:
        return EvaluationResult(
            rule_id="R3",
            rule_name="Existe autorização",
            status=EvalStatus.CONFORME,
            rationale="Aprovador identificado e data de aprovação registada.",
        )
    if not has_approver and not has_approval_date:
        return EvaluationResult(
            rule_id="R3",
            rule_name="Existe autorização",
            status=EvalStatus.EXCECAO,
            rationale="Sem aprovador nem data de aprovação — não há evidência de autorização.",
        )
    return EvaluationResult(
        rule_id="R3",
        rule_name="Existe autorização",
        status=EvalStatus.REVER,
        rationale=(
            "Evidência parcial de autorização — falta "
            + ("aprovador" if not has_approver else "data de aprovação")
            + "."
        ),
    )


# --------------------------------------------------------------------------- #
# R4 — Acesso justificado
# --------------------------------------------------------------------------- #
# NOTA: verifica PRESENÇA, não QUALIDADE. Avaliar se a justificação é adequada é
# juízo humano e permanece com o auditor.
def r4_justification_present(t: CanonicalTicket, c: RuleConfig) -> EvaluationResult:
    if t.justification.is_reliable(c.confidence_threshold):
        return EvaluationResult(
            rule_id="R4",
            rule_name="Acesso justificado",
            status=EvalStatus.CONFORME,
            rationale=f"Justificação presente: «{_truncate(t.justification.value, 80)}»",
        )
    if t.justification.value is None:
        return EvaluationResult(
            rule_id="R4",
            rule_name="Acesso justificado",
            status=EvalStatus.EXCECAO,
            rationale="Sem justificação no ticket.",
        )
    return EvaluationResult(
        rule_id="R4",
        rule_name="Acesso justificado",
        status=EvalStatus.REVER,
        rationale="Justificação extraída com baixa confiança — revisão humana necessária.",
    )


# --------------------------------------------------------------------------- #
# R5 — Validação da atribuição
# --------------------------------------------------------------------------- #
# O campo tester foi substituído por beneficiary (quem recebe o acesso).
# A validação da atribuição passa a basear-se apenas na data de validação.
def r5_validation_present(t: CanonicalTicket, c: RuleConfig) -> EvaluationResult:
    if not c.require_validation:
        return EvaluationResult(
            rule_id="R5",
            rule_name="Validação da atribuição",
            status=EvalStatus.NAO_APLICAVEL,
            rationale="Cliente não exige validação — regra não aplicável.",
        )

    has_validation_date = t.dates.validation_date.is_reliable(c.confidence_threshold)
    if has_validation_date:
        return EvaluationResult(
            rule_id="R5",
            rule_name="Validação da atribuição",
            status=EvalStatus.CONFORME,
            rationale=f"Data de validação registada: {t.dates.validation_date.value}.",
        )
    return EvaluationResult(
        rule_id="R5",
        rule_name="Validação da atribuição",
        status=EvalStatus.EXCECAO,
        rationale="Sem data de validação — atribuição não foi validada.",
    )


# --------------------------------------------------------------------------- #
# R6 — Ticket no estado esperado
# --------------------------------------------------------------------------- #
def r6_expected_state(t: CanonicalTicket, c: RuleConfig) -> EvaluationResult:
    if not t.state.is_reliable(c.confidence_threshold):
        return EvaluationResult(
            rule_id="R6",
            rule_name="Ticket no estado esperado",
            status=EvalStatus.REVER,
            rationale="Estado do ticket não extraído com confiança suficiente.",
        )
    if not c.expected_states:
        return EvaluationResult(
            rule_id="R6",
            rule_name="Ticket no estado esperado",
            status=EvalStatus.NAO_APLICAVEL,
            rationale="Nenhum estado esperado configurado no profile.",
        )
    if t.state.value.strip().lower() in c.expected_states:  # type: ignore[union-attr]
        return EvaluationResult(
            rule_id="R6",
            rule_name="Ticket no estado esperado",
            status=EvalStatus.CONFORME,
            rationale=f"Estado «{t.state.value}» está entre os esperados.",
        )
    return EvaluationResult(
        rule_id="R6",
        rule_name="Ticket no estado esperado",
        status=EvalStatus.EXCECAO,
        rationale=f"Estado «{t.state.value}» não é um estado de conclusão esperado.",
    )


# --------------------------------------------------------------------------- #
# R7 — Coerência de datas
# --------------------------------------------------------------------------- #
def r7_date_coherence(t: CanonicalTicket, c: RuleConfig) -> EvaluationResult:
    seq = [
        ("pedido", t.dates.request_date),
        ("aprovação", t.dates.approval_date),
        ("implementação", t.dates.implementation_date),
        ("validação", t.dates.validation_date),
    ]
    present = [(n, f.value) for n, f in seq if f.is_reliable(c.confidence_threshold)]
    if len(present) < 2:
        return EvaluationResult(
            rule_id="R7",
            rule_name="Coerência de datas",
            status=EvalStatus.REVER,
            rationale="Datas insuficientes para avaliar coerência.",
        )
    today = date.today()
    for name, value in present:
        if value > today:  # type: ignore[operator]
            return EvaluationResult(
                rule_id="R7",
                rule_name="Coerência de datas",
                status=EvalStatus.EXCECAO,
                rationale=f"Data de {name} ({value}) está no futuro.",
            )
    for (n1, v1), (n2, v2) in zip(present, present[1:]):
        if v1 > v2:  # type: ignore[operator]
            return EvaluationResult(
                rule_id="R7",
                rule_name="Coerência de datas",
                status=EvalStatus.EXCECAO,
                rationale=f"{n1} ({v1}) é posterior a {n2} ({v2}).",
            )
    return EvaluationResult(
        rule_id="R7",
        rule_name="Coerência de datas",
        status=EvalStatus.CONFORME,
        rationale="Datas presentes estão em ordem cronológica e não são futuras.",
    )


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #
ALL_RULES = (
    r1_segregation_of_duties,
    r2_approval_before_implementation,
    r3_authorization_exists,
    r4_justification_present,
    r5_validation_present,
    r6_expected_state,
    r7_date_coherence,
)

# Regras críticas — se falharem, ditam o veredicto geral. Configurável no futuro.
CRITICAL_RULE_IDS = {"R1", "R2", "R3"}


def evaluate(t: CanonicalTicket, c: RuleConfig) -> TicketAssessment:
    """Corre todas as regras e devolve o assessment completo."""

    results = [rule(t, c) for rule in ALL_RULES]
    overall = _overall_verdict(results)
    return TicketAssessment(ticket=t, results=results, overall=overall)


def _overall_verdict(results: list[EvaluationResult]) -> EvalStatus:
    """
    Regras do veredicto:
    - Qualquer EXCECAO crítica -> EXCECAO
    - Qualquer outra EXCECAO -> EXCECAO
    - Sem exceções mas com algum REVER -> REVER (nunca escondido)
    - Todas CONFORME/NAO_APLICAVEL -> CONFORME
    """
    if any(r.status == EvalStatus.EXCECAO for r in results):
        return EvalStatus.EXCECAO
    if any(r.status == EvalStatus.REVER for r in results):
        return EvalStatus.REVER
    return EvalStatus.CONFORME


def _truncate(text: str | None, n: int) -> str:
    if not text:
        return ""
    return text if len(text) <= n else text[: n - 1] + "…"
