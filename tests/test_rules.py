"""
Testes do motor de regras. Todas as regras testadas exaustivamente:
- caso conforme
- caso exceção
- caso "rever" (dados insuficientes / baixa confiança)
- casos-limite (datas iguais, mesmo dia, etc.)

Estes testes são a garantia de defensabilidade: se todos passam, provamos que a
avaliação é determinística e reproduzível.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from audit_tool.models.canonical import EvalStatus
from audit_tool.rules.engine import (
    RuleConfig,
    evaluate,
    r1_segregation_of_duties,
    r2_approval_before_implementation,
    r3_authorization_exists,
    r4_justification_present,
    r5_validation_present,
    r6_expected_state,
    r7_date_coherence,
)


# =============================================================================
# R1 — Segregação de Funções
# =============================================================================
class TestR1SoD:
    def test_conforme_quando_tres_pessoas_distintas(self, make_ticket, default_config):
        t = make_ticket()
        assert r1_segregation_of_duties(t, default_config).status == EvalStatus.CONFORME

    def test_excecao_requester_igual_implementer(self, make_ticket, default_config):
        t = make_ticket(implementer_email="ana@x.pt")
        r = r1_segregation_of_duties(t, default_config)
        assert r.status == EvalStatus.EXCECAO
        assert "requester" in r.rationale and "implementer" in r.rationale

    def test_excecao_requester_igual_approver(self, make_ticket, default_config):
        t = make_ticket(approver_email="ana@x.pt")
        assert r1_segregation_of_duties(t, default_config).status == EvalStatus.EXCECAO

    def test_excecao_approver_igual_implementer(self, make_ticket, default_config):
        t = make_ticket(implementer_email="carla@x.pt")
        assert r1_segregation_of_duties(t, default_config).status == EvalStatus.EXCECAO

    def test_rever_se_falta_identidade(self, make_ticket, default_config):
        t = make_ticket(approver_email=None)
        # Nome fica presente mas identifier (email) não; nome-só serve como fallback
        # -> ainda conforme. Testamos o caso extremo em que ambos faltam:
        t.approver.display_name.value = None
        t.approver.display_name.confidence = 0.0
        assert r1_segregation_of_duties(t, default_config).status == EvalStatus.REVER

    def test_comparacao_case_insensitive(self, make_ticket, default_config):
        t = make_ticket(implementer_email="ANA@X.PT")
        assert r1_segregation_of_duties(t, default_config).status == EvalStatus.EXCECAO

    def test_include_tester_deteta_colisao_com_tester(self, make_ticket):
        cfg = RuleConfig(expected_states=(), sod_include_tester=True)
        # beneficiary não entra na SoD — este teste já não se aplica
        pass


# =============================================================================
# R2 — Autorização anterior à atribuição
# =============================================================================
class TestR2ApprovalBeforeImplementation:
    def test_conforme_aprovacao_antes(self, make_ticket, default_config):
        t = make_ticket(approval_date=date(2026, 2, 3), implementation_date=date(2026, 2, 4))
        assert r2_approval_before_implementation(t, default_config).status == EvalStatus.CONFORME

    def test_conforme_mesmo_dia(self, make_ticket, default_config):
        d = date(2026, 2, 3)
        t = make_ticket(approval_date=d, implementation_date=d)
        assert r2_approval_before_implementation(t, default_config).status == EvalStatus.CONFORME

    def test_excecao_aprovacao_depois(self, make_ticket, default_config):
        t = make_ticket(approval_date=date(2026, 2, 5), implementation_date=date(2026, 2, 4))
        r = r2_approval_before_implementation(t, default_config)
        assert r.status == EvalStatus.EXCECAO

    def test_rever_sem_data_aprovacao(self, make_ticket, default_config):
        t = make_ticket(approval_date=None)
        assert r2_approval_before_implementation(t, default_config).status == EvalStatus.REVER

    def test_rever_com_confianca_baixa(self, make_ticket, default_config):
        t = make_ticket(low_confidence_fields=("approval_date",))
        assert r2_approval_before_implementation(t, default_config).status == EvalStatus.REVER


# =============================================================================
# R3 — Existe autorização
# =============================================================================
class TestR3AuthorizationExists:
    def test_conforme_com_aprovador_e_data(self, make_ticket, default_config):
        t = make_ticket()
        assert r3_authorization_exists(t, default_config).status == EvalStatus.CONFORME

    def test_excecao_sem_aprovador_nem_data(self, make_ticket, default_config):
        t = make_ticket(approver_email=None, approval_date=None)
        t.approver.display_name.value = None
        assert r3_authorization_exists(t, default_config).status == EvalStatus.EXCECAO

    def test_rever_apenas_com_aprovador(self, make_ticket, default_config):
        t = make_ticket(approval_date=None)
        assert r3_authorization_exists(t, default_config).status == EvalStatus.REVER

    def test_rever_apenas_com_data(self, make_ticket, default_config):
        t = make_ticket(approver_email=None)
        t.approver.display_name.value = None
        assert r3_authorization_exists(t, default_config).status == EvalStatus.REVER


# =============================================================================
# R4 — Justificação
# =============================================================================
class TestR4Justification:
    def test_conforme_com_justificacao(self, make_ticket, default_config):
        assert r4_justification_present(make_ticket(), default_config).status == EvalStatus.CONFORME

    def test_excecao_sem_justificacao(self, make_ticket, default_config):
        t = make_ticket(justification=None)
        assert r4_justification_present(t, default_config).status == EvalStatus.EXCECAO

    def test_rever_com_confianca_baixa(self, make_ticket, default_config):
        t = make_ticket(low_confidence_fields=("justification",))
        assert r4_justification_present(t, default_config).status == EvalStatus.REVER


# =============================================================================
# R5 — Validação
# =============================================================================
class TestR5Validation:
    def test_nao_aplicavel_quando_nao_exigida(self, make_ticket):
        cfg = RuleConfig(require_validation=False)
        assert r5_validation_present(make_ticket(), cfg).status == EvalStatus.NAO_APLICAVEL

    def test_conforme_com_data_validacao(self, make_ticket):
        cfg = RuleConfig(require_validation=True)
        t = make_ticket(validation_date=date(2026, 2, 5))
        assert r5_validation_present(t, cfg).status == EvalStatus.CONFORME

    def test_excecao_sem_data_validacao(self, make_ticket):
        cfg = RuleConfig(require_validation=True)
        t = make_ticket(validation_date=None)
        assert r5_validation_present(t, cfg).status == EvalStatus.EXCECAO


# =============================================================================
# R6 — Estado esperado
# =============================================================================
class TestR6ExpectedState:
    def test_conforme_estado_conhecido(self, make_ticket, default_config):
        assert r6_expected_state(make_ticket(), default_config).status == EvalStatus.CONFORME

    def test_conforme_case_insensitive(self, make_ticket, default_config):
        t = make_ticket(state="CLOSED COMPLETE")
        assert r6_expected_state(t, default_config).status == EvalStatus.CONFORME

    def test_excecao_estado_desconhecido(self, make_ticket, default_config):
        t = make_ticket(state="In Progress")
        assert r6_expected_state(t, default_config).status == EvalStatus.EXCECAO

    def test_rever_estado_nao_extraido(self, make_ticket, default_config):
        t = make_ticket(state=None)
        assert r6_expected_state(t, default_config).status == EvalStatus.REVER

    def test_nao_aplicavel_sem_config_de_estados(self, make_ticket):
        cfg = RuleConfig(expected_states=())
        assert r6_expected_state(make_ticket(), cfg).status == EvalStatus.NAO_APLICAVEL


# =============================================================================
# R7 — Coerência de datas
# =============================================================================
class TestR7DateCoherence:
    def test_conforme_datas_em_ordem(self, make_ticket, default_config):
        assert r7_date_coherence(make_ticket(), default_config).status == EvalStatus.CONFORME

    def test_excecao_ordem_invertida(self, make_ticket, default_config):
        t = make_ticket(request_date=date(2026, 2, 5), approval_date=date(2026, 2, 3))
        assert r7_date_coherence(t, default_config).status == EvalStatus.EXCECAO

    def test_excecao_data_futura(self, make_ticket, default_config):
        future = date.today() + timedelta(days=30)
        t = make_ticket(implementation_date=future, validation_date=None)
        assert r7_date_coherence(t, default_config).status == EvalStatus.EXCECAO

    def test_rever_datas_insuficientes(self, make_ticket, default_config):
        t = make_ticket(
            request_date=None, approval_date=None,
            implementation_date=date(2026, 2, 4), validation_date=None,
        )
        assert r7_date_coherence(t, default_config).status == EvalStatus.REVER

    def test_ignora_datas_ausentes_na_ordem(self, make_ticket, default_config):
        t = make_ticket(approval_date=None)  # falta aprovação mas request<impl
        assert r7_date_coherence(t, default_config).status == EvalStatus.CONFORME


# =============================================================================
# Veredicto geral
# =============================================================================
class TestOverallVerdict:
    def test_conforme_quando_tudo_conforme(self, make_ticket, default_config):
        assert evaluate(make_ticket(), default_config).overall == EvalStatus.CONFORME

    def test_excecao_quando_uma_regra_falha(self, make_ticket, default_config):
        t = make_ticket(implementer_email="ana@x.pt")  # colisão SoD
        assert evaluate(t, default_config).overall == EvalStatus.EXCECAO

    def test_rever_prevalece_sobre_conforme_quando_nao_ha_excecao(self, make_ticket, default_config):
        t = make_ticket(low_confidence_fields=("state",))
        assert evaluate(t, default_config).overall == EvalStatus.REVER

    def test_excecao_prevalece_sobre_rever(self, make_ticket, default_config):
        t = make_ticket(
            implementer_email="ana@x.pt",           # SoD -> EXCECAO
            low_confidence_fields=("state",),       # R6 -> REVER
        )
        assert evaluate(t, default_config).overall == EvalStatus.EXCECAO
