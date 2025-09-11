# nav.py
import streamlit as st

def row_key_of(selected_idx: int) -> str:
    return f"row_{int(selected_idx)}"

def reset_inputs_for_row(prev_row_key: str):
    # v3 입력 위젯 키 패턴 정리 (행 전환 시 초기화)
    PREFIXES = (
        "PHYS_DDX_",          # 의사 ddx 텍스트
        "BASE_QLT_", "BASE_COMP_", "BASE_APPR_",   # Base 3 Likerts
        "APP_QLT_", "APP_COMP_", "APP_APPR_",     # Applied 3 Likerts
        "HIST_SCORE_",        # History 1 Likert
        "COMMENT_",           # 코멘트
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

def render_row_picker(filtered_df):
    id_options = list(filtered_df.index)
    if len(id_options) == 0:
        st.info("No rows after filtering. Adjust filters to see results.")
        return False, None, None

    # ── 외부 네비 요청(ROW_NAV_TARGET) 먼저 반영: selectbox 만들기 前 ──
    if "ROW_NAV_TARGET" in st.session_state:
        st.session_state["CURRENT_PICK"] = st.session_state.pop("ROW_NAV_TARGET")

    # 현재 선택 준비 (없으면 첫 행)
    current_pick = st.session_state.get("CURRENT_PICK", id_options[0])
    try:
        pos = id_options.index(current_pick)
    except ValueError:
        pos = 0
        current_pick = id_options[0]
        st.session_state["CURRENT_PICK"] = current_pick

    # Prev/Next는 selectbox 생성 전에 처리하고 즉시 rerun
    sel_col, prev_col, next_col = st.columns([6, 1, 1])
    with prev_col:
        if st.button("◀ Prev", use_container_width=True, disabled=(pos <= 0)):
            st.session_state["ROW_NAV_TARGET"] = id_options[pos - 1]
            st.rerun()
    with next_col:
        if st.button("Next ▶", use_container_width=True, disabled=(pos >= len(id_options) - 1)):
            st.session_state["ROW_NAV_TARGET"] = id_options[pos + 1]
            st.rerun()

    # selectbox에는 key를 주지 않음 → 위젯-세션 충돌 방지
    with sel_col:
        selected_idx = st.selectbox(
            "Select a row",
            options=id_options,
            index=pos,
            format_func=lambda i: f"{filtered_df.loc[i, 'file_name']} — {filtered_df.loc[i, 'Label'][:40]}",
        )

    # 최종 선택 세션 반영 (ROW_PICKER 대신 CURRENT_PICK 사용)
    st.session_state["CURRENT_PICK"] = selected_idx
    row = filtered_df.loc[selected_idx]
    return True, selected_idx, row