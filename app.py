"""
Aplicação Streamlit — Ticket Analyzer (Auditoria de Acessos).
Corre com:  streamlit run app.py
"""

from __future__ import annotations

import dataclasses
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import streamlit as st

from audit_tool.analyzer import AnalyzedTicket, Analyzer
from audit_tool.config.profile import list_available_profiles, load_profile
from audit_tool.config.settings import MODELS, load_settings
from audit_tool.export.excel import export_workpaper
from audit_tool.models.canonical import EvalStatus

# ---------------------------------------------------------------------------
# Paleta Deloitte
# ---------------------------------------------------------------------------
C_BLACK      = "#000000"
C_PRIMARY    = "#002776"   # azul escuro (acentos, links)
C_GREEN      = "#86BC25"   # verde Deloitte
C_LIGHT_BLUE = "#00A3E0"   # azul claro
C_WHITE      = "#FFFFFF"
C_BG         = "#F5F5F5"   # fundo geral
C_SURFACE    = "#FFFFFF"   # fundo de cards
C_BORDER     = "#E0E0E0"
C_TEXT       = "#1A1A1A"
C_MUTED      = "#6B6B6B"

STATUS_BG   = {
    EvalStatus.CONFORME:      "#EAF5D6",
    EvalStatus.EXCECAO:       "#FDECEA",
    EvalStatus.REVER:         "#FEF9E7",
    EvalStatus.NAO_APLICAVEL: "#F2F2F2",
}
STATUS_BORDER = {
    EvalStatus.CONFORME:      C_GREEN,
    EvalStatus.EXCECAO:       "#D32F2F",
    EvalStatus.REVER:         "#F9A825",
    EvalStatus.NAO_APLICAVEL: "#BDBDBD",
}
STATUS_TEXT = {
    EvalStatus.CONFORME:      "#2E7D32",
    EvalStatus.EXCECAO:       "#B71C1C",
    EvalStatus.REVER:         "#795B00",
    EvalStatus.NAO_APLICAVEL: "#616161",
}
STATUS_ICON = {
    EvalStatus.CONFORME:      "✅",
    EvalStatus.EXCECAO:       "❌",
    EvalStatus.REVER:         "⚠️",
    EvalStatus.NAO_APLICAVEL: "—",
}

MODEL_LABELS = {
    "haiku":  "Haiku — rápido / económico",
    "sonnet": "Sonnet — padrão ✦",
    "opus":   "Opus — máxima capacidade",
}

TICKET_TYPES = ["Acessos", "Alterações ao Sistema"]

# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Ticket Analyzer | Deloitte",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');

  html, body, [class*="css"] {{
    font-family: 'Open Sans', sans-serif;
    color: {C_TEXT};
  }}

  /* Remove padding por cima para o header colar ao topo */
  .main .block-container {{
    padding-top: 0 !important;
    padding-bottom: 2.5rem;
    max-width: 1400px;
  }}

  /* ---- Header preto ---- */
  .brand-header {{
    background: {C_BLACK};
    padding: 0 32px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: -1rem -1rem 0 -1rem;
  }}
  .brand-header-left {{
    display: flex;
    align-items: center;
    gap: 20px;
  }}
  .brand-header img {{
    height: 28px;
    width: auto;
  }}
  .brand-header-divider {{
    width: 1px;
    height: 28px;
    background: rgba(255,255,255,0.25);
  }}
  .brand-header-title {{
    color: {C_WHITE};
    font-size: 0.95rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    margin: 0;
  }}
  .brand-header-right {{
    color: rgba(255,255,255,0.55);
    font-size: 0.75rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}

  /* ---- Linha verde sob o header ---- */
  .green-stripe {{
    height: 4px;
    background: {C_GREEN};
    margin: 0 -1rem 1.8rem -1rem;
  }}

  /* ---- Sidebar ---- */
  section[data-testid="stSidebar"] > div {{
    background: {C_BLACK};
    padding-top: 1.5rem;
  }}
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] .stRadio > label,
  section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] span {{
    color: {C_WHITE} !important;
  }}
  section[data-testid="stSidebar"] .stSelectbox > label,
  section[data-testid="stSidebar"] .stRadio > label {{
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(255,255,255,0.6) !important;
  }}
  section[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.12);
    margin: 1rem 0;
  }}
  /* Selectbox e radio dentro da sidebar */
  section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {{
    background: rgba(255,255,255,0.08) !important;
    border-color: rgba(255,255,255,0.15) !important;
  }}

  /* ---- Botões ---- */
  .stButton > button {{
    background: {C_GREEN} !important;
    color: {C_BLACK} !important;
    border: none !important;
    border-radius: 2px !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.04em !important;
    padding: 0.5rem 1.6rem !important;
    transition: opacity 0.15s;
  }}
  .stButton > button:hover {{ opacity: 0.88; }}
  .stButton > button:disabled {{
    background: #BDBDBD !important;
    color: #757575 !important;
  }}

  /* ---- Métricas ---- */
  div[data-testid="stMetric"] {{
    background: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 14px 18px;
    border-top: 3px solid {C_GREEN};
  }}
  div[data-testid="stMetricValue"] {{
    color: {C_BLACK} !important;
    font-size: 1.9rem !important;
    font-weight: 700 !important;
  }}
  div[data-testid="stMetricLabel"] {{
    font-size: 0.77rem;
    color: {C_MUTED};
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  /* ---- Section labels ---- */
  .section-label {{
    font-size: 0.70rem;
    font-weight: 700;
    color: {C_MUTED};
    text-transform: uppercase;
    letter-spacing: 0.10em;
    margin: 2rem 0 0.6rem 0;
    padding-bottom: 6px;
    border-bottom: 2px solid {C_GREEN};
    display: inline-block;
  }}

  /* ---- Card de controlo ---- */
  .ctrl-card {{
    border-left: 3px solid;
    background: {C_SURFACE};
    border-radius: 0 4px 4px 0;
    padding: 9px 13px;
    margin-bottom: 5px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  }}
  .ctrl-card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2px;
  }}
  .ctrl-card-rule {{ font-size: 0.82rem; font-weight: 700; }}
  .ctrl-card-status {{ font-size: 0.75rem; font-weight: 700; }}
  .ctrl-card-rationale {{ font-size: 0.79rem; color: {C_MUTED}; }}

  /* ---- Verdict box ---- */
  .verdict-box {{
    border-radius: 4px;
    padding: 12px 16px;
    margin-top: 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.88rem;
    font-weight: 700;
    border: 1px solid;
  }}

  /* ---- WIP banner ---- */
  .wip-banner {{
    background: #FFF8E1;
    border-left: 3px solid #F9A825;
    border-radius: 0 4px 4px 0;
    padding: 10px 14px;
    font-size: 0.82rem;
    color: #4E3B00;
    margin-bottom: 1.2rem;
  }}

  /* ---- Footer ---- */
  .app-footer {{
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid {C_BORDER};
    text-align: center;
    font-size: 0.72rem;
    color: {C_MUTED};
  }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header preto com logo
# ---------------------------------------------------------------------------
LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"

def _logo_html() -> str:
    if LOGO_PATH.exists():
        import base64
        data = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{data}" alt="Deloitte">'
    # Fallback: wordmark em texto caso o logo não exista ainda
    return f'<span style="color:{C_GREEN}; font-size:1.3rem; font-weight:700; letter-spacing:0.01em;">Deloitte</span>'

st.markdown(f"""
<div class="brand-header">
  <div class="brand-header-left">
    {_logo_html()}
    <div class="brand-header-divider"></div>
    <p class="brand-header-title">Ticket Analyzer</p>
  </div>
  <div class="brand-header-right">Auditoria de IT</div>
</div>
<div class="green-stripe"></div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Estado da sessão
# ---------------------------------------------------------------------------
if "analyzed" not in st.session_state:
    st.session_state.analyzed: list[AnalyzedTicket] = []

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f'<p style="font-size:0.70rem; font-weight:700; text-transform:uppercase; '
        f'letter-spacing:0.10em; color:rgba(255,255,255,0.45); margin-bottom:1rem;">'
        f'Configuração</p>',
        unsafe_allow_html=True,
    )

    # Tipo de ticket
    st.markdown(
        '<p style="font-size:0.70rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:rgba(255,255,255,0.5);margin-bottom:4px;">Tipo de ticket</p>',
        unsafe_allow_html=True,
    )
    ticket_type = st.radio(
        "tipo", TICKET_TYPES, label_visibility="collapsed"
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # Modelo AI
    st.markdown(
        '<p style="font-size:0.70rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:rgba(255,255,255,0.5);margin-bottom:4px;">Modelo de IA</p>',
        unsafe_allow_html=True,
    )
    model_key = st.selectbox(
        "modelo", list(MODEL_LABELS.keys()),
        index=1,
        format_func=lambda k: MODEL_LABELS[k],
        label_visibility="collapsed",
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # Origem
    st.markdown(
        '<p style="font-size:0.70rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:rgba(255,255,255,0.5);margin-bottom:4px;">Origem do ticket</p>',
        unsafe_allow_html=True,
    )

    try:
        settings = load_settings()
    except ValueError as e:
        st.error(str(e))
        st.stop()

    settings = dataclasses.replace(settings, model=MODELS[model_key])
    profiles = list_available_profiles(settings.profiles_dir)
    if not profiles:
        st.error("Sem profiles disponíveis.")
        st.stop()

    profile_name = st.selectbox(
        "origem", list(profiles.keys()), label_visibility="collapsed"
    )
    profile = load_profile(profiles[profile_name])

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown(
        f'<p style="font-size:0.72rem; color:rgba(255,255,255,0.45); line-height:1.7;">'
        f'<b style="color:rgba(255,255,255,0.7);">Modelo:</b> {MODELS[model_key]}<br>'
        f'<b style="color:rgba(255,255,255,0.7);">Profile:</b> {profile.source_id} v{profile.version}<br>'
        f'<b style="color:rgba(255,255,255,0.7);">Confiança:</b> {profile.checks.confidence_threshold}'
        f'</p>',
        unsafe_allow_html=True,
    )

    if st.session_state.analyzed:
        st.markdown("")
        if st.button("Limpar sessão", use_container_width=True):
            st.session_state.analyzed = []
            st.rerun()

# ---------------------------------------------------------------------------
# Aviso WIP
# ---------------------------------------------------------------------------
if ticket_type == "Alterações ao Sistema":
    st.markdown(
        '<div class="wip-banner">🚧 <b>Alterações ao Sistema</b> está em desenvolvimento '
        'e será disponibilizado numa versão futura. Seleciona <b>Acessos</b> para continuar.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ---------------------------------------------------------------------------
# Secção 1 — Upload
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Carregar tickets</div>', unsafe_allow_html=True)
st.markdown("")

uploaded = st.file_uploader(
    "Arrastar ficheiros ou clicar para selecionar (.txt, .eml)",
    type=["txt", "eml", "pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

col_btn, col_info = st.columns([2, 8])
with col_btn:
    do_analyze = st.button(
        "▶  Analisar",
        disabled=not uploaded,
        use_container_width=True,
    )
with col_info:
    if uploaded:
        st.markdown(
            f'<p style="margin-top:8px; font-size:0.82rem; color:{C_MUTED};">'
            f'{len(uploaded)} ficheiro(s) · <b>{profile_name}</b> · <b>{MODEL_LABELS[model_key]}</b></p>',
            unsafe_allow_html=True,
        )

if do_analyze:
    st.session_state.analyzed = []
    analyzer = Analyzer(settings, profile)
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for uf in uploaded:
            p = Path(tmp) / uf.name
            p.write_bytes(uf.getbuffer())
            paths.append(p)

        prog = st.progress(0.0, text="A analisar…")
        log  = st.empty()
        for i, result in enumerate(analyzer.analyze_files(paths), start=1):
            st.session_state.analyzed.append(result)
            code    = result.assessment.ticket.ticket_code.value or "(sem código)"
            verdict = result.assessment.overall
            log.markdown(
                f'{STATUS_ICON[verdict]} `{code}` — **{verdict.value}**'
            )
            prog.progress(min(i / max(len(paths), 1), 1.0), text=f"{i}/{len(paths)} analisado(s)…")
        prog.empty()
        log.empty()

    st.success(f"Análise concluída — {len(st.session_state.analyzed)} ticket(s) processado(s).")

# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------
analyzed: list[AnalyzedTicket] = st.session_state.analyzed
if not analyzed:
    st.markdown(
        f'<p style="color:{C_MUTED}; font-size:0.88rem; margin-top:1rem;">'
        f'Carregue ficheiros e clique <b>▶ Analisar</b> para começar.</p>',
        unsafe_allow_html=True,
    )
    st.stop()

# Métricas
st.markdown('<div class="section-label">Resumo</div>', unsafe_allow_html=True)
st.markdown("")
counts = {s: 0 for s in EvalStatus}
for a in analyzed:
    counts[a.assessment.overall] += 1

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total",          len(analyzed))
m2.metric("Conformes",      counts[EvalStatus.CONFORME])
m3.metric("Exceções",       counts[EvalStatus.EXCECAO])
m4.metric("A rever",        counts[EvalStatus.REVER])
m5.metric("N/A",            counts[EvalStatus.NAO_APLICAVEL])

# Tabela global
st.markdown('<div class="section-label">Análise global</div>', unsafe_allow_html=True)
st.markdown("")

def _to_row(a: AnalyzedTicket) -> dict:
    t = a.assessment.ticket
    row = {
        "Ficheiro":    t.source_file or "",
        "Código":      t.ticket_code.value or "",
        "Sistema":     t.system.value or "",
        "Ambiente":    t.environment.value or "",
        "Estado":      t.state.value or "",
        "Requester":   t.requester.display_name.value or t.requester.identifier.value or "",
        "Approver":    t.approver.display_name.value or t.approver.identifier.value or "",
        "Implementer": t.implementer.display_name.value or t.implementer.identifier.value or "",
    }
    for r in a.assessment.results:
        row[r.rule_id] = r.status.value
    row["Veredicto"] = a.assessment.overall.value
    return row

df = pd.DataFrame([_to_row(a) for a in analyzed])
st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Drill-down
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Detalhe do ticket</div>', unsafe_allow_html=True)
st.markdown("")

options = {
    f"{STATUS_ICON[a.assessment.overall]}  "
    f"{a.assessment.ticket.ticket_code.value or '(sem código)'}  —  "
    f"{a.assessment.ticket.source_file}": i
    for i, a in enumerate(analyzed)
}
sel    = st.selectbox("Selecionar ticket", list(options.keys()), label_visibility="collapsed")
picked = analyzed[options[sel]]
t      = picked.assessment.ticket

col_l, col_r = st.columns([1, 1], gap="large")

with col_l:
    st.markdown(
        f'<p style="font-size:0.78rem; font-weight:700; color:{C_MUTED}; '
        f'text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;">Campos extraídos</p>',
        unsafe_allow_html=True,
    )
    rows = []
    for label, f in [
        ("Código", t.ticket_code), ("Tipo", t.ticket_type),
        ("Sistema", t.system), ("Ambiente", t.environment),
        ("Estado", t.state), ("Justificação", t.justification),
    ]:
        rows.append({
            "Campo":     label,
            "Valor":     f.value or "—",
            "Conf.":     f"{f.confidence:.0%}",
            "Evidência": (f.source_excerpt or "—")[:100],
        })
    for label, p in [
        ("Requester", t.requester), ("Approver", t.approver),
        ("Implementer", t.implementer), ("Beneficiário", t.beneficiary),
    ]:
        who = " ".join(x for x in [
            p.display_name.value,
            f"<{p.identifier.value}>" if p.identifier.value else "",
        ] if x)
        rows.append({
            "Campo":     label,
            "Valor":     who or "—",
            "Conf.":     f"{max(p.display_name.confidence, p.identifier.confidence):.0%}",
            "Evidência": (p.display_name.source_excerpt or p.identifier.source_excerpt or "—")[:100],
        })
    for label, df_ in [
        ("Data pedido",        t.dates.request_date),
        ("Data aprovação",     t.dates.approval_date),
        ("Data implementação", t.dates.implementation_date),
        ("Data validação",     t.dates.validation_date),
    ]:
        rows.append({
            "Campo":     label,
            "Valor":     df_.value.isoformat() if df_.value else "—",
            "Conf.":     f"{df_.confidence:.0%}",
            "Evidência": (df_.source_excerpt or "—")[:100],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with col_r:
    st.markdown(
        f'<p style="font-size:0.78rem; font-weight:700; color:{C_MUTED}; '
        f'text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;">Avaliação dos controlos</p>',
        unsafe_allow_html=True,
    )
    for r in picked.assessment.results:
        bg  = STATUS_BG[r.status]
        bc  = STATUS_BORDER[r.status]
        txt = STATUS_TEXT[r.status]
        st.markdown(f"""
        <div class="ctrl-card" style="background:{bg}; border-left-color:{bc};">
          <div class="ctrl-card-header">
            <span class="ctrl-card-rule" style="color:{C_TEXT};">{r.rule_id} — {r.rule_name}</span>
            <span class="ctrl-card-status" style="color:{txt};">{STATUS_ICON[r.status]} {r.status.value}</span>
          </div>
          <div class="ctrl-card-rationale">{r.rationale}</div>
        </div>
        """, unsafe_allow_html=True)

    ov = picked.assessment.overall
    st.markdown(f"""
    <div class="verdict-box"
         style="background:{STATUS_BG[ov]};
                border-color:{STATUS_BORDER[ov]};
                color:{STATUS_TEXT[ov]};">
      {STATUS_ICON[ov]}&nbsp; Veredicto geral: {ov.value}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    with st.expander("Rastreio da extração"):
        st.json({
            "model":          picked.trail.model,
            "prompt_version": picked.trail.prompt_version,
            "prompt_hash":    picked.trail.prompt_hash,
            "profile":        f"{picked.trail.profile_id} v{picked.trail.profile_version}",
            "ticket_type":    ticket_type,
            "tokens_in":      picked.trail.input_tokens,
            "tokens_out":     picked.trail.output_tokens,
            "timestamp":      picked.trail.timestamp,
        })

# ---------------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Exportar workpaper</div>', unsafe_allow_html=True)
st.markdown("")

col_e, col_note = st.columns([2, 8])
with col_e:
    if st.button("⬇  Gerar Excel", use_container_width=True):
        out_dir  = Path(tempfile.gettempdir()) / "ticket-analyzer-exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"workpaper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        path     = export_workpaper(analyzed, out_dir / filename)
        with open(path, "rb") as fh:
            st.download_button(
                "📥  Descarregar",
                data=fh.read(),
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
with col_note:
    st.markdown(
        f'<p style="margin-top:8px; font-size:0.82rem; color:{C_MUTED};">'
        f'Gera workpaper Excel com 4 abas: Resumo · Análise · Exceções · Rastreio. '
        f'{len(analyzed)} ticket(s) na sessão atual.</p>',
        unsafe_allow_html=True,
    )

# ===========================================================================
# SECÇÃO DE CALIBRAÇÃO
# Separada da análise principal. Objetivo: carregar um ticket, rever a
# extração campo a campo, corrigir o que estiver errado, e guardar como
# exemplo validado no profile YAML (few-shot para análises futuras).
# ===========================================================================

st.markdown("---")
st.markdown('<div class="section-label">Calibração de profile</div>', unsafe_allow_html=True)
st.markdown("")

with st.expander("ℹ️ Como funciona a calibração", expanded=False):
    st.markdown("""
    A calibração permite **melhorar a qualidade da extração** para uma origem ao longo do tempo,
    sem alterar código.

    **Fluxo:**
    1. Carrega um ticket de exemplo (preferencialmente representativo da origem)
    2. A app extrai os campos automaticamente
    3. Revês e corrigis os valores errados ou em falta
    4. Guardas como exemplo — fica guardado no YAML do profile e passa a guiar extrações futuras

    Recomenda-se 2–4 exemplos por origem para uma melhoria significativa.
    Os exemplos existentes podem ser geridos na secção abaixo.
    """)

# --- Upload de ticket para calibração ---------------------------------------
st.markdown(
    f'<p style="font-size:0.82rem; color:{C_MUTED}; margin-bottom:6px;">'
    f'Profile selecionado: <b>{profile_name}</b></p>',
    unsafe_allow_html=True,
)

cal_uploaded = st.file_uploader(
    "Ticket para calibrar (.txt, .eml, .pdf)",
    type=["txt", "eml", "pdf"],
    key="calibration_upload",
    label_visibility="collapsed",
)

if cal_uploaded:
    import tempfile as _tmp
    from audit_tool.extraction.client import ExtractionClient

    col_cal_btn, _ = st.columns([2, 8])
    with col_cal_btn:
        do_extract_cal = st.button("🔍 Extrair para calibração", use_container_width=True)

    if do_extract_cal or "cal_extraction" in st.session_state:
        # Extrai só uma vez por upload
        if do_extract_cal:
            with _tmp.TemporaryDirectory() as _t:
                _p = Path(_t) / cal_uploaded.name
                _p.write_bytes(cal_uploaded.getbuffer())
                from audit_tool.ingestion.reader import read_file as _read_file
                docs = _read_file(_p)
                if not docs:
                    st.error("Não foi possível ler o ficheiro.")
                    st.stop()
                doc = docs[0]

            extractor = ExtractionClient(settings)
            with st.spinner("A extrair campos…"):
                result = extractor.extract(doc, profile)

            st.session_state["cal_extraction"] = result
            st.session_state["cal_doc_text"]   = doc.text

        result   = st.session_state["cal_extraction"]
        doc_text = st.session_state.get("cal_doc_text", "")
        t_cal    = result.ticket

        st.markdown("")
        st.markdown(
            f'<p style="font-size:0.78rem; font-weight:700; color:{C_MUTED}; '
            f'text-transform:uppercase; letter-spacing:0.06em;">Corrigir campos extraídos</p>',
            unsafe_allow_html=True,
        )
        st.caption("Corrige os valores que o modelo apanhou incorretamente. Deixa em branco se o campo não existe no ticket.")

        # --- Formulário de correção -----------------------------------------
        col_f1, col_f2 = st.columns(2)

        def _val(f) -> str:
            return f.value or "" if f else ""

        def _person_val(p) -> str:
            parts = []
            if p and p.display_name.value:
                parts.append(p.display_name.value)
            if p and p.identifier.value:
                parts.append(f"<{p.identifier.value}>")
            return " ".join(parts)

        with col_f1:
            c_code    = st.text_input("Código do ticket",  value=_val(t_cal.ticket_code))
            c_type    = st.text_input("Tipo",              value=_val(t_cal.ticket_type))
            c_system  = st.text_input("Sistema",           value=_val(t_cal.system))
            c_env     = st.text_input("Ambiente",          value=_val(t_cal.environment))
            c_state   = st.text_input("Estado",            value=_val(t_cal.state))
            c_just    = st.text_area("Justificação",       value=_val(t_cal.justification), height=80)

        with col_f2:
            c_req  = st.text_input("Requester",   value=_person_val(t_cal.requester))
            c_apr  = st.text_input("Approver",    value=_person_val(t_cal.approver))
            c_impl = st.text_input("Implementer", value=_person_val(t_cal.implementer))
            c_test = st.text_input("Beneficiário", value=_person_val(t_cal.beneficiary))
            c_req_date  = st.text_input("Data pedido",        value=_val(t_cal.dates.request_date) if not t_cal.dates.request_date.value else t_cal.dates.request_date.value.isoformat())
            c_apr_date  = st.text_input("Data aprovação",     value="" if not t_cal.dates.approval_date.value else t_cal.dates.approval_date.value.isoformat())
            c_impl_date = st.text_input("Data implementação", value="" if not t_cal.dates.implementation_date.value else t_cal.dates.implementation_date.value.isoformat())
            c_val_date  = st.text_input("Data validação",     value="" if not t_cal.dates.validation_date.value else t_cal.dates.validation_date.value.isoformat())

        # --- Nome do exemplo e guardar --------------------------------------
        st.markdown("")
        col_name, col_save = st.columns([3, 2])
        with col_name:
            default_name = f"{profile.source_id}_{c_code.strip().lower().replace(' ','_') or 'exemplo'}"
            example_name = st.text_input(
                "Nome do exemplo",
                value=default_name,
                help="Nome único para identificar este exemplo no profile. Usa algo descritivo.",
            )

        with col_save:
            st.markdown("<div style='margin-top:28px;'>", unsafe_allow_html=True)
            do_save = st.button("💾  Guardar exemplo", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if do_save:
            if not example_name.strip():
                st.warning("Define um nome para o exemplo antes de guardar.")
            else:
                from audit_tool.config.calibration import add_example_to_profile

                corrected = {
                    "ticket_code":           c_code.strip() or None,
                    "ticket_type":           c_type.strip() or None,
                    "system":                c_system.strip() or None,
                    "environment":           c_env.strip() or None,
                    "state":                 c_state.strip() or None,
                    "requester":             c_req.strip() or None,
                    "approver":              c_apr.strip() or None,
                    "implementer":           c_impl.strip() or None,
                    "beneficiary":           c_test.strip() or None,
                    "request_date":          c_req_date.strip() or None,
                    "approval_date":         c_apr_date.strip() or None,
                    "implementation_date":   c_impl_date.strip() or None,
                    "validation_date":       c_val_date.strip() or None,
                    "justification":         c_just.strip() or None,
                }
                # Remove campos None para não inflar o YAML
                corrected = {k: v for k, v in corrected.items() if v is not None}

                profile_path = profiles[profile_name]
                try:
                    add_example_to_profile(
                        profile_path=profile_path,
                        example_name=example_name.strip(),
                        ticket_text=doc_text,
                        extraction=corrected,
                    )
                    st.success(
                        f"✅ Exemplo **{example_name}** guardado em `{profile_path.name}`. "
                        f"Será usado como referência nas próximas extrações desta origem."
                    )
                    # Limpa o estado de calibração para novo ticket
                    for k in ("cal_extraction", "cal_doc_text"):
                        st.session_state.pop(k, None)
                except Exception as e:
                    st.error(f"Erro ao guardar: {e}")

# --- Gestão de exemplos existentes ------------------------------------------
st.markdown("")
st.markdown(
    f'<p style="font-size:0.78rem; font-weight:700; color:{C_MUTED}; '
    f'text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;">'
    f'Exemplos guardados — {profile_name}</p>',
    unsafe_allow_html=True,
)

from audit_tool.config.calibration import list_examples, remove_example_from_profile

profile_path = profiles[profile_name]
existing     = list_examples(profile_path)

if not existing:
    st.caption("Nenhum exemplo guardado ainda para esta origem.")
else:
    for ex_name in existing:
        col_ex, col_rm = st.columns([6, 1])
        with col_ex:
            st.markdown(
                f'<div style="padding:6px 10px; background:{C_BG}; border-radius:4px; '
                f'font-size:0.82rem; border:1px solid {C_BORDER};">📋 {ex_name}</div>',
                unsafe_allow_html=True,
            )
        with col_rm:
            if st.button("🗑", key=f"rm_{ex_name}", help=f"Remover exemplo {ex_name}"):
                remove_example_from_profile(profile_path, ex_name)
                st.success(f"Exemplo '{ex_name}' removido.")
                st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    f'<div class="app-footer">Ticket Analyzer · Uso interno · Auditoria de IT</div>',
    unsafe_allow_html=True,
)
