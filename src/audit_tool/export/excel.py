"""
Exportador de workpaper Excel.

4 abas:
- Resumo:   contagens e % de conformidade por controlo
- Análise:  1 linha por ticket com todos os campos + resultado por regra
- Exceções: só os tickets que falharam ou precisam rever (para trabalho do auditor)
- Rastreio: evidência da extração (excerto-fonte por campo, versão modelo/prompt)

Estilizado com as cores da marca:
  Azul primário   #002776
  Verde           #92D400
  Azul claro      #00A1DE
  Preto           #000000
  Branco          #FFFFFF
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from audit_tool.analyzer import AnalyzedTicket
from audit_tool.models.canonical import EvalStatus, ExtractedField


# --- Paleta ------------------------------------------------------------------
COLOR_PRIMARY = "002776"
COLOR_GREEN = "92D400"
COLOR_LIGHT_BLUE = "00A1DE"
COLOR_BLACK = "000000"
COLOR_WHITE = "FFFFFF"

# Estados -> cores (fills suaves para não distrair na tabela)
STATUS_FILL = {
    EvalStatus.CONFORME: PatternFill("solid", fgColor="E6F4D9"),      # verde suave
    EvalStatus.EXCECAO: PatternFill("solid", fgColor="F8D7DA"),       # vermelho suave
    EvalStatus.REVER: PatternFill("solid", fgColor="FFF3CD"),         # amarelo suave
    EvalStatus.NAO_APLICAVEL: PatternFill("solid", fgColor="E9ECEF"), # cinzento
}

HEADER_FILL = PatternFill("solid", fgColor=COLOR_PRIMARY)
HEADER_FONT = Font(bold=True, color=COLOR_WHITE, name="Calibri", size=11)
BODY_FONT = Font(name="Calibri", size=10)


# =============================================================================
# API pública
# =============================================================================
def export_workpaper(analyzed: list[AnalyzedTicket], output_path: Path) -> Path:
    """Gera o workpaper Excel com as 4 abas. Devolve o caminho gerado."""

    wb = Workbook()
    # openpyxl cria uma aba por defeito — vamos usá-la para a primeira
    wb.remove(wb.active)

    _build_summary(wb, analyzed)
    _build_analysis(wb, analyzed)
    _build_exceptions(wb, analyzed)
    _build_trail(wb, analyzed)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


# =============================================================================
# Abas
# =============================================================================
def _build_summary(wb: Workbook, analyzed: list[AnalyzedTicket]) -> None:
    ws = wb.create_sheet("Resumo")
    ws["A1"] = "Resumo da análise"
    ws["A1"].font = Font(bold=True, color=COLOR_PRIMARY, size=14)
    ws["A2"] = f"Total de tickets analisados: {len(analyzed)}"
    ws["A2"].font = BODY_FONT

    if not analyzed:
        return

    # Contagens do veredicto geral
    overall_counts = {s: 0 for s in EvalStatus}
    for a in analyzed:
        overall_counts[a.assessment.overall] += 1

    ws["A4"] = "Veredicto geral"
    ws["A4"].font = Font(bold=True, color=COLOR_PRIMARY, size=12)
    row = 5
    for status, count in overall_counts.items():
        ws.cell(row=row, column=1, value=status.value).font = BODY_FONT
        ws.cell(row=row, column=2, value=count).font = BODY_FONT
        ws.cell(row=row, column=1).fill = STATUS_FILL[status]
        row += 1

    # Contagens por regra
    row += 2
    ws.cell(row=row, column=1, value="Resultado por controlo").font = Font(
        bold=True, color=COLOR_PRIMARY, size=12
    )
    row += 1
    header = ["Regra", "Conforme", "Exceção", "A rever", "N/A"]
    for i, h in enumerate(header, start=1):
        cell = ws.cell(row=row, column=i, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    row += 1

    # Todas as regras que apareceram em algum ticket
    all_rules: dict[str, str] = {}
    for a in analyzed:
        for r in a.assessment.results:
            all_rules[r.rule_id] = r.rule_name

    for rule_id, rule_name in sorted(all_rules.items()):
        counts = {s: 0 for s in EvalStatus}
        for a in analyzed:
            for r in a.assessment.results:
                if r.rule_id == rule_id:
                    counts[r.status] += 1
        ws.cell(row=row, column=1, value=f"{rule_id} — {rule_name}").font = BODY_FONT
        ws.cell(row=row, column=2, value=counts[EvalStatus.CONFORME]).font = BODY_FONT
        ws.cell(row=row, column=3, value=counts[EvalStatus.EXCECAO]).font = BODY_FONT
        ws.cell(row=row, column=4, value=counts[EvalStatus.REVER]).font = BODY_FONT
        ws.cell(row=row, column=5, value=counts[EvalStatus.NAO_APLICAVEL]).font = BODY_FONT
        row += 1

    _autosize(ws)


def _build_analysis(wb: Workbook, analyzed: list[AnalyzedTicket]) -> None:
    ws = wb.create_sheet("Análise")

    fixed_headers = [
        "Ficheiro", "Código", "Tipo", "Sistema", "Ambiente", "Estado",
        "Requester", "Approver", "Implementer", "Beneficiário",
        "Data pedido", "Data aprovação", "Data implementação", "Data validação",
        "Justificação",
    ]
    rule_ids = _all_rule_ids(analyzed)
    headers = fixed_headers + rule_ids + ["Veredicto"]

    _write_header(ws, headers)

    for row_idx, a in enumerate(analyzed, start=2):
        t = a.assessment.ticket
        row = [
            t.source_file or "",
            _v(t.ticket_code), _v(t.ticket_type), _v(t.system),
            _v(t.environment), _v(t.state),
            _person_str(t.requester), _person_str(t.approver),
            _person_str(t.implementer), _person_str(t.beneficiary),
            _date_str(t.dates.request_date), _date_str(t.dates.approval_date),
            _date_str(t.dates.implementation_date), _date_str(t.dates.validation_date),
            _v(t.justification),
        ]
        for col_idx, val in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = BODY_FONT
            cell.alignment = Alignment(vertical="top", wrap_text=True)

        # colunas das regras
        results_by_id = {r.rule_id: r for r in a.assessment.results}
        for i, rule_id in enumerate(rule_ids):
            col_idx = len(fixed_headers) + 1 + i
            r = results_by_id.get(rule_id)
            if r is None:
                continue
            cell = ws.cell(row=row_idx, column=col_idx, value=r.status.value)
            cell.font = BODY_FONT
            cell.fill = STATUS_FILL[r.status]
            cell.alignment = Alignment(horizontal="center")

        # veredicto
        v_col = len(headers)
        vcell = ws.cell(row=row_idx, column=v_col, value=a.assessment.overall.value)
        vcell.font = Font(bold=True, name="Calibri", size=10)
        vcell.fill = STATUS_FILL[a.assessment.overall]
        vcell.alignment = Alignment(horizontal="center")

    _autosize(ws, max_width=40)
    ws.freeze_panes = "B2"


def _build_exceptions(wb: Workbook, analyzed: list[AnalyzedTicket]) -> None:
    ws = wb.create_sheet("Exceções")
    headers = ["Ficheiro", "Código", "Regra", "Estado", "Racional"]
    _write_header(ws, headers)

    row = 2
    for a in analyzed:
        t = a.assessment.ticket
        for r in a.assessment.results:
            if r.status not in (EvalStatus.EXCECAO, EvalStatus.REVER):
                continue
            ws.cell(row=row, column=1, value=t.source_file or "").font = BODY_FONT
            ws.cell(row=row, column=2, value=_v(t.ticket_code)).font = BODY_FONT
            ws.cell(row=row, column=3, value=f"{r.rule_id} — {r.rule_name}").font = BODY_FONT
            cell = ws.cell(row=row, column=4, value=r.status.value)
            cell.font = BODY_FONT
            cell.fill = STATUS_FILL[r.status]
            rat = ws.cell(row=row, column=5, value=r.rationale)
            rat.font = BODY_FONT
            rat.alignment = Alignment(wrap_text=True, vertical="top")
            row += 1

    _autosize(ws, max_width=60)
    ws.freeze_panes = "A2"


def _build_trail(wb: Workbook, analyzed: list[AnalyzedTicket]) -> None:
    ws = wb.create_sheet("Rastreio")
    headers = [
        "Ficheiro", "Código", "Campo", "Valor", "Confiança", "Excerto-fonte",
        "Modelo", "Versão prompt", "Hash prompt", "Profile", "Timestamp",
    ]
    _write_header(ws, headers)

    row = 2
    for a in analyzed:
        t = a.assessment.ticket
        for field_label, field in _iter_extracted_fields(t):
            ws.cell(row=row, column=1, value=t.source_file or "").font = BODY_FONT
            ws.cell(row=row, column=2, value=_v(t.ticket_code)).font = BODY_FONT
            ws.cell(row=row, column=3, value=field_label).font = BODY_FONT
            ws.cell(row=row, column=4, value=str(field.value) if field.value is not None else "").font = BODY_FONT
            ws.cell(row=row, column=5, value=round(field.confidence, 2)).font = BODY_FONT
            excerpt = ws.cell(row=row, column=6, value=field.source_excerpt or "")
            excerpt.font = BODY_FONT
            excerpt.alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=row, column=7, value=a.trail.model).font = BODY_FONT
            ws.cell(row=row, column=8, value=a.trail.prompt_version).font = BODY_FONT
            ws.cell(row=row, column=9, value=a.trail.prompt_hash).font = BODY_FONT
            ws.cell(row=row, column=10, value=f"{a.trail.profile_id} v{a.trail.profile_version}").font = BODY_FONT
            ws.cell(row=row, column=11, value=a.trail.timestamp).font = BODY_FONT
            row += 1

    _autosize(ws, max_width=50)
    ws.freeze_panes = "A2"


# =============================================================================
# Helpers
# =============================================================================
def _write_header(ws, headers: list[str]) -> None:
    for i, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=i, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24


def _autosize(ws, max_width: int = 30) -> None:
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        length = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[letter].width = min(max(length + 2, 12), max_width)


def _v(f: ExtractedField) -> str:
    return f.value if f and f.value else ""


def _person_str(person) -> str:
    if not person:
        return ""
    parts = []
    if person.display_name.value:
        parts.append(person.display_name.value)
    if person.identifier.value:
        parts.append(f"<{person.identifier.value}>")
    return " ".join(parts)


def _date_str(df) -> str:
    return df.value.isoformat() if df and df.value else ""


def _all_rule_ids(analyzed: list[AnalyzedTicket]) -> list[str]:
    seen: list[str] = []
    for a in analyzed:
        for r in a.assessment.results:
            if r.rule_id not in seen:
                seen.append(r.rule_id)
    return seen


def _iter_extracted_fields(ticket):
    """Itera todos os campos extraídos com o seu label, para a aba de rastreio."""
    yield "Código", ticket.ticket_code
    yield "Tipo", ticket.ticket_type
    yield "Sistema", ticket.system
    yield "Ambiente", ticket.environment
    yield "Estado", ticket.state
    yield "Requester (nome)", ticket.requester.display_name
    yield "Requester (id)", ticket.requester.identifier
    yield "Approver (nome)", ticket.approver.display_name
    yield "Approver (id)", ticket.approver.identifier
    yield "Implementer (nome)", ticket.implementer.display_name
    yield "Implementer (id)", ticket.implementer.identifier
    yield "Beneficiário (nome)", ticket.beneficiary.display_name
    yield "Beneficiário (id)", ticket.beneficiary.identifier
    yield "Justificação", ticket.justification
    # datas partilham a mesma estrutura mas com value=date
    for label, df in [
        ("Data pedido", ticket.dates.request_date),
        ("Data aprovação", ticket.dates.approval_date),
        ("Data implementação", ticket.dates.implementation_date),
        ("Data validação", ticket.dates.validation_date),
    ]:
        # Adapta-se à interface esperada por _iter (usa .value/.confidence/.source_excerpt)
        yield label, df
