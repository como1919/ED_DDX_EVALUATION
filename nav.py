# nav.py
import streamlit as st

def row_key_of(selected_idx: int) -> str:
    return f"row_{int(selected_idx)}"

def reset_inputs_for_row(prev_row_key: str):
    PREFIXES = (
        "PHYS_DDX_", "BASE_QLT_", "BASE_COMP_", "BASE_APPR_",
        "APP_QLT_", "APP_COMP_", "APP_APPR_", "HIST_SCORE_", "COMMENT_",
    )
    for k in list(st.session_state.keys()):
        if k.endswith(prev_row_key) and any(k.startswith(p) for p in PREFIXES):
            st.session_state.pop(k, None)

def reset_inputs_for_row_if_changed(selected_idx: int):
    prev = st.session_state.get("CURRENT_ROW_KEY")
    curr = row_key_of(selected_idx)
    if prev != curr:
        if prev is not None:
            reset_inputs_for_row(prev)
        st.session_state["CURRENT_ROW_KEY"] = curr

# 라벨 폴백 헬퍼
def _row_title(df, i):
    fn = str(df.loc[i, "file_name"])
    # 우선순위: Label → __exp_name_applied__ → Expected Diagnosis (applied) → __exp_name_base__ → Expected Diagnosis (base)
    for c in ("Label", "__exp_name_applied__", "Expected Diagnosis (applied)",
              "__exp_name_base__", "Expected Diagnosis (base)"):
        if c in df.columns:
            val = str(df.loc[i, c])
            if val and val.lower() != "nan":
                return f"{fn} — {val[:40]}"
    return fn

def render_row_picker(filtered_df):
    id_options = list(filtered_df.index)
    if len(id_options) == 0:
        st.info("No rows after filtering. Adjust filters to see results.")
        return False, None, None

    # 외부 네비 요청 먼저 반영
    if "ROW_NAV_TARGET" in st.session_state:
        st.session_state["CURRENT_PICK"] = st.session_state.pop("ROW_NAV_TARGET")

    current_pick = st.session_state.get("CURRENT_PICK", id_options[0])
    try:
        pos = id_options.index(current_pick)
    except ValueError:
        pos = 0
        current_pick = id_options[0]
        st.session_state["CURRENT_PICK"] = current_pick

    sel_col, prev_col, next_col = st.columns([6, 1, 1])
    with prev_col:
        if st.button("◀ Prev", use_container_width=True, disabled=(pos <= 0)):
            st.session_state["ROW_NAV_TARGET"] = id_options[pos - 1]
            st.rerun()
    with next_col:
        if st.button("Next ▶", use_container_width=True, disabled=(pos >= len(id_options) - 1)):
            st.session_state["ROW_NAV_TARGET"] = id_options[pos + 1]
            st.rerun()
    with sel_col:
        selected_idx = st.selectbox(
            "Select a row",
            options=id_options,
            index=pos,
            format_func=lambda i: _row_title(filtered_df, i),  # KeyError 방지
        )

    st.session_state["CURRENT_PICK"] = selected_idx
    row = filtered_df.loc[selected_idx]
    return True, selected_idx, row