# views.py
import hashlib
import pandas as pd
import streamlit as st


def _row_toggle_key(row, suffix: str) -> str:
    # file_name 기반 키 (행마다 독립 토글)
    fid = str(row.get("file_name", ""))
    h = hashlib.md5(fid.encode("utf-8")).hexdigest()[:8]
    return f"{suffix}_{h}"



def render_core_view(row: pd.Series):
    st.markdown("### Core View")

    # 모델 DDX 표 토글 버튼
    tkey = _row_toggle_key(row, "SHOW_MODEL_DDX")
    if tkey not in st.session_state:
        st.session_state[tkey] = False
    label = "Show model DDX lists" if not st.session_state[tkey] else "Hide model DDX lists"
    if st.button(label, key=f"{tkey}_btn", use_container_width=True):
        st.session_state[tkey] = not st.session_state[tkey]

    if st.session_state[tkey]:
        lc, rc = st.columns(2)
        with lc:
            st.markdown("**Model (Base) — Expected + Differentials**")
            rows = row.get("__ddx_table_base__") or []
            if rows:
                df_tbl = pd.DataFrame(rows)
                # Tier 컬럼 제거
                if "Tier" in df_tbl.columns:
                    df_tbl = df_tbl.drop(columns=["Tier"])
                st.table(df_tbl)
            else:
                st.write("—")

        with rc:
            st.markdown("**Model (Applied) — Expected + Differentials**")
            rows = row.get("__ddx_table_applied__") or []
            if rows:
                df_tbl = pd.DataFrame(rows)
                if "Tier" in df_tbl.columns:
                    df_tbl = df_tbl.drop(columns=["Tier"])
                st.table(df_tbl)
            else:
                st.write("—")

    # 하단 원본 초진기록
    st.markdown("**원본 초진기록**")
    st.text_area(
        "raw_visit",
        row.get("원본 초진기록", row.get("현병력-Free Text#13", "")),
        height=420,
        label_visibility="collapsed",
    )


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