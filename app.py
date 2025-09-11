# app.py
import pandas as pd
import streamlit as st

from columns import normalize_columns, backfill_from_raw
from utils import pretty_multiline
from nav import render_row_picker, row_key_of, reset_inputs_for_row_if_changed
from views import render_core_view, render_optional_sections
from ddx_eval import render_physician_ddx_and_evaluations

st.set_page_config(page_title="ER DDX Viewer v3", layout="wide")

def main():
    st.title("ER Differential Diagnosis Viewer — v3")
    st.caption("의사가 먼저 감별진단(DDX)을 작성하고, 모델/의사 리스트 및 Current/Past History를 리커트 척도로 평가합니다.")

    # Sidebar: data
    st.sidebar.title("Data")
    uploaded = st.sidebar.file_uploader("Upload result CSV", type=["csv"])
    if uploaded is None:
        st.write("⬅️ 왼쪽에서 CSV를 업로드하세요.")
        st.stop()

    df_raw = pd.read_csv(uploaded, dtype=str).fillna("")
    df = normalize_columns(df_raw)
    df = backfill_from_raw(df, prefer="applied")  # RAW JSON 기준 Expected/Diff tiers 파생

    # Sidebar: filters & optional sections
    st.sidebar.title("Filters")
    query = st.sidebar.text_input("Search (file / Label / Expected Dx / DDx)", value="")

    st.sidebar.title("Optional Sections")
    show_past = st.sidebar.checkbox("Show Past History", value=True)
    show_current = st.sidebar.checkbox("Show Current History", value=True)
    show_asso_sx = st.sidebar.checkbox("Show ASSO_SX_SN", value=False)
    show_asso_dx = st.sidebar.checkbox("Show ASSO_DISEASE", value=False)
    show_asso_tx = st.sidebar.checkbox("Show ASSO_TREATMENT", value=False)

    # Apply filter
    filtered = df.copy()
    if query.strip():
        q = query.lower()
        filtered = filtered[
            filtered["file_name"].str.lower().str.contains(q)
            | filtered["Label"].str.lower().str.contains(q)
            | filtered["Expected Diagnosis"].str.lower().str.contains(q)
            | filtered["Differential Diagnoses list"].str.lower().str.contains(q)
        ]

    left, right = st.columns([2.0, 1.6], gap="large")

    with left:
        # 행 선택 + Prev/Next (안전 네비게이션 포함)
        has_row, selected_idx, row = render_row_picker(filtered)
        if not has_row:
            st.stop()

        # 행 전환 시 입력 초기화
        reset_inputs_for_row_if_changed(selected_idx)

        # Core view (표 기반)
        render_core_view(row)

        # Optional sections
        render_optional_sections(
            row,
            show_past=show_past,
            show_current=show_current,
            show_asso_sx=show_asso_sx,
            show_asso_dx=show_asso_dx,
            show_asso_tx=show_asso_tx,
        )

    with right:
        # v3 핵심: 의사 DDX 작성 + 리스트(모델/의사) 리커트 + Current/Past History 리커트 + 코멘트 + 저장/다운로드
        render_physician_ddx_and_evaluations(
            row=row,
            selected_idx=int(selected_idx),
            all_indices=list(df.index),
            df_all=df,
        )

    # Bottom quick browse
    st.markdown("---")
    st.subheader("Records (Quick Browse)")
    base_cols = [
        "file_name", "원본 초진기록", "Label",
        "Expected Diagnosis", "Differential Diagnoses list",
    ]
    st.dataframe(filtered[base_cols].reset_index(drop=True), use_container_width=True, height=320)

    # Export filtered
    st.markdown("---")
    st.caption("Export (filtered)")
    csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Download filtered CSV", data=csv_bytes, file_name="filtered_results_v3.csv", mime="text/csv")

if __name__ == "__main__":
    main()