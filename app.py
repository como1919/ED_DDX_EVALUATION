# app.py
import pandas as pd
import streamlit as st

from columns import normalize_columns, backfill_from_raw
from nav import render_row_picker, row_key_of, reset_inputs_for_row_if_changed
from views import render_core_view, render_optional_sections
from ddx_eval import render_physician_ddx_and_evaluations

st.set_page_config(page_title="ER DDX Viewer v3", layout="wide")


def main():
    st.title("ER Differential Diagnosis Viewer — v3")
    st.caption("의사가 먼저 감별진단(DDX)을 작성하고, 모델/의사 리스트 및 Current/Past History를 리커트 척도로 평가합니다.")

    # ───────────────── Sidebar: data ─────────────────
    st.sidebar.title("Data")
    uploaded = st.sidebar.file_uploader("Upload result CSV", type=["csv"])
    if uploaded is None:
        st.write("⬅️ 왼쪽에서 CSV를 업로드하세요.")
        st.stop()

    df_raw = pd.read_csv(uploaded, dtype=str).fillna("")
    df = normalize_columns(df_raw)
    # RAW(JSON) 및 문자열 형태에서 Expected / Differential 파생 생성 (applied/base 각각)
    df = backfill_from_raw(df, prefer="applied")

    # ───────────────── Sidebar: filters & options ─────────────────
    st.sidebar.title("Filters")
    query = st.sidebar.text_input("Search (file / Expected Dx / DDx)", value="")

    st.sidebar.title("Optional Sections")
    show_past = st.sidebar.checkbox("Show Past History", value=True)
    show_current = st.sidebar.checkbox("Show Current History", value=True)

    # ASSO 컬럼 유무에 따라 토글 노출
    has_asso_sx = "ASSO_SX_SN" in df.columns
    has_asso_dx = "ASSO_DISEASE" in df.columns
    has_asso_tx = "ASSO_TREATMENT" in df.columns
    show_asso_sx = st.sidebar.checkbox("Show ASSO_SX_SN", value=False) if has_asso_sx else False
    show_asso_dx = st.sidebar.checkbox("Show ASSO_DISEASE", value=False) if has_asso_dx else False
    show_asso_tx = st.sidebar.checkbox("Show ASSO_TREATMENT", value=False) if has_asso_tx else False

    # ───────────────── Apply filter (Label 없이도 안전) ─────────────────
    filtered = df.copy()
    if query.strip():
        q = query.lower()

        def s(series_like):
            return pd.Series(series_like, index=df.index, dtype="object").astype(str).str.lower()

        conds = [
            s(df["file_name"]).str.contains(q, na=False),
            s(df.get("__exp_name_applied__", "")).str.contains(q, na=False),
            s(df.get("__exp_name_base__", "")).str.contains(q, na=False),
            s(df.get("__ddx_names_applied__", "")).str.contains(q, na=False),
            s(df.get("__ddx_names_base__", "")).str.contains(q, na=False),
            s(df.get("Current History", "")).str.contains(q, na=False),
            s(df.get("Past History", "")).str.contains(q, na=False),
        ]
        # 과거 통합 컬럼 호환(있을 경우만)
        if "Expected Diagnosis" in df.columns:
            conds.append(s(df["Expected Diagnosis"]).str.contains(q, na=False))
        if "Differential Diagnoses list" in df.columns:
            conds.append(s(df["Differential Diagnoses list"]).str.contains(q, na=False))

        mask = conds[0]
        for c in conds[1:]:
            mask = mask | c
        filtered = df[mask]

    # ───────────────── Layout ─────────────────
    left, right = st.columns([2.2, 1.6], gap="large")

    with left:
        # 행 선택 + Prev/Next (KeyError 없는 format_func를 nav.py에서 처리)
        has_row, selected_idx, row = render_row_picker(filtered)
        if not has_row:
            st.stop()

        # 행 전환 시 해당 행 키로 입력 초기화
        reset_inputs_for_row_if_changed(selected_idx)

        # Core view (Expected & Differential을 표로, 모델 DDX는 버튼으로 토글)
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
        # v3 핵심: 의사 DDX 작성 + (Base/Applied) 리커트 + History 리커트 + 코멘트 + 저장/점프/다운로드
        render_physician_ddx_and_evaluations(
            row=row,
            selected_idx=int(selected_idx),
            all_indices=list(df.index),
            df_all=df,
        )

    # ───────────────── Bottom quick browse ─────────────────
    st.markdown("---")
    st.subheader("Records (Quick Browse)")

    # 존재하는 컬럼만 보여주도록 안전 구성
    quick_cols_pref = [
        "file_name",
        "원본 초진기록",
        "Current History",
        "Past History",
        # 통합 컬럼이 있는 경우(구버전 호환)
        "Expected Diagnosis",
        "Differential Diagnoses list",
        # 분리 표준 컬럼(신규)
        "Expected Diagnosis (applied)",
        "Differential Diagnoses (applied)",
        "Expected Diagnosis (base)",
        "Differential Diagnoses (base)",
    ]
    quick_cols = [c for c in quick_cols_pref if c in filtered.columns]
    if not quick_cols:
        quick_cols = ["file_name"]

    st.dataframe(
        filtered[quick_cols].reset_index(drop=True),
        use_container_width=True,
        height=320
    )

    # ───────────────── Export filtered ─────────────────
    st.markdown("---")
    st.caption("Export (filtered)")
    csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download filtered CSV",
        data=csv_bytes,
        file_name="filtered_results_v3.csv",
        mime="text/csv"
    )


if __name__ == "__main__":
    main()