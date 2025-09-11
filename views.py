# views.py
import hashlib
import pandas as pd
import streamlit as st

def _names_table(names, title):
    st.markdown(f"**{title}**")
    if not isinstance(names, list):
        names = []
    if names:
        st.table(pd.DataFrame({"Differential Diagnosis": names}))
    else:
        st.write("—")

def _row_toggle_key(row, suffix: str) -> str:
    # file_name 기반 키 (행마다 독립 토글)
    fid = str(row.get("file_name", ""))
    h = hashlib.md5(fid.encode("utf-8")).hexdigest()[:8]
    return f"{suffix}_{h}"

def render_core_view(row: pd.Series):
    st.markdown("### Core View")

    # ── 모델 DDX 표: 기본 감춤, 버튼으로 토글 ───────────────────────────
    toggle_key = _row_toggle_key(row, "SHOW_MODEL_DDX")
    if toggle_key not in st.session_state:
        st.session_state[toggle_key] = False

    # 버튼을 전체 폭으로 크게, 줄바꿈 없이
    btn_label = "Show model DDX lists" if not st.session_state[toggle_key] else "Hide model DDX lists"
    if st.button(btn_label, use_container_width=True):
        st.session_state[toggle_key] = not st.session_state[toggle_key]

    # 표시 상태일 때만 표 출력
    if st.session_state[toggle_key]:
        left, right = st.columns(2)
        with left:
            _names_table(row.get("__ddx_names_base__"), "Model (Base) — Differential Diagnoses")
        with right:
            _names_table(row.get("__ddx_names_applied__"), "Model (Applied) — Differential Diagnoses")

    # ── 하단: 원본 초진기록 크게 ─────────────────────────────────────────
    st.markdown("**원본 초진기록**")
    st.text_area("raw_visit", row.get("원본 초진기록", ""), height=420, label_visibility="collapsed")

def render_optional_sections(row, *, show_past, show_current, show_asso_sx, show_asso_dx, show_asso_tx):
    any_flag = any([show_past, show_current, show_asso_sx, show_asso_dx, show_asso_tx])
    if not any_flag:
        return
    st.markdown("---")
    st.subheader("Optional Sections")
    if show_current:
        st.markdown("**Current History**")
        st.text_area("opt_current", row.get("Current History", ""), height=160, label_visibility="collapsed")
    if show_past:
        st.markdown("**Past History**")
        st.text_area("opt_past", row.get("Past History", ""), height=160, label_visibility="collapsed")
    if show_asso_sx:
        st.caption("ASSO_SX_SN")
        st.text_area("opt_sx", row.get("ASSO_SX_SN", ""), height=80, label_visibility="collapsed")
    if show_asso_dx:
        st.caption("ASSO_DISEASE")
        st.text_area("opt_dx", row.get("ASSO_DISEASE", ""), height=80, label_visibility="collapsed")
    if show_asso_tx:
        st.caption("ASSO_TREATMENT")
        st.text_area("opt_tx", row.get("ASSO_TREATMENT", ""), height=80, label_visibility="collapsed")