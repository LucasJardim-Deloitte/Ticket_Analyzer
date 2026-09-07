"""
Schema da ferramenta `extract_ticket` usada com o tool use da API Anthropic.

Força o modelo a devolver JSON conforme ao schema canónico.
Elimina texto livre e garante que a resposta é sempre parseável e validável por pydantic.

v0.3.1 — tester substituído por beneficiary; instruções de Tipo mais explícitas.
"""

from __future__ import annotations


def _field_schema(description: str) -> dict:
    return {
        "type": "object",
        "description": description,
        "properties": {
            "value":          {"type": ["string", "null"]},
            "raw_value":      {"type": ["string", "null"]},
            "source_excerpt": {"type": ["string", "null"], "description": "Excerto exato do documento (evidência)."},
            "confidence":     {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": ["value", "confidence"],
    }


def _person_schema(description: str) -> dict:
    return {
        "type": "object",
        "description": description,
        "properties": {
            "display_name": _field_schema("Nome como aparece no ticket."),
            "identifier":   _field_schema("Email ou username (preferido para comparação)."),
        },
        "required": ["display_name", "identifier"],
    }


def _date_field_schema(description: str) -> dict:
    return {
        "type": "object",
        "description": description,
        "properties": {
            "value":          {"type": ["string", "null"], "description": "Data em ISO 8601 (YYYY-MM-DD)."},
            "raw_value":      {"type": ["string", "null"]},
            "source_excerpt": {"type": ["string", "null"]},
            "confidence":     {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": ["value", "confidence"],
    }


EXTRACT_TICKET_TOOL = {
    "name": "extract_ticket",
    "description": (
        "Extrai os campos canónicos de um ticket de gestão de acessos. "
        "Devolve, por campo, o valor normalizado, o excerto-fonte (evidência) e a confiança 0-1."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticket_code": _field_schema("Número/código único do ticket."),
            "ticket_type": _field_schema(
                "Tipo/natureza do pedido. Deve ser descritivo e incluir contexto relevante "
                "(ex: 'Acesso temporário ao SAP FI para debug', não apenas 'Acesso temporário'). "
                "Preservar detalhe suficiente para perceber o propósito, sem incluir códigos "
                "técnicos internos ou referências a transações (ex: ST22) que não acrescentam contexto."
            ),
            "system":       _field_schema("Sistema ou aplicação alvo do acesso."),
            "environment":  _field_schema("Ambiente: Produção, Qualidade, Desenvolvimento, etc."),
            "state":        _field_schema("Estado atual do ticket na origem."),
            "requester":    _person_schema(
                "Quem ABRIU/PEDIU o ticket. É a pessoa que submeteu o pedido de acesso, "
                "não necessariamente quem recebe o acesso. "
                "Tipicamente: 'Requested by', 'Opened by', 'Caller', 'Solicitante'."
            ),
            "implementer":  _person_schema(
                "Quem EXECUTOU a atribuição do acesso. "
                "Tipicamente: 'Assigned to', 'Implemented by', 'Closed by', 'Implementado por'."
            ),
            "approver":     _person_schema(
                "Quem APROVOU o pedido. "
                "Tipicamente: 'Approved by', 'Approver', 'Aprovado por'."
            ),
            "beneficiary":  _person_schema(
                "Quem RECEBE o acesso — o utilizador alvo/beneficiário. "
                "É diferente do requester: pode ser um colega em nome de quem o pedido foi feito. "
                "Tipicamente: 'Requested for', 'Affected user', 'User', 'Beneficiário', 'Para'."
            ),
            "request_date":        _date_field_schema("Data em que o pedido foi submetido."),
            "approval_date":       _date_field_schema("Data em que o pedido foi aprovado."),
            "implementation_date": _date_field_schema("Data em que o acesso foi atribuído/implementado."),
            "validation_date":     _date_field_schema("Data em que a atribuição foi validada/testada."),
            "justification":       _field_schema("Justificação de negócio para o acesso pedido."),
        },
        "required": [
            "ticket_code", "ticket_type", "system", "environment", "state",
            "requester", "implementer", "approver", "beneficiary",
            "request_date", "approval_date", "implementation_date", "validation_date",
            "justification",
        ],
    },
}
