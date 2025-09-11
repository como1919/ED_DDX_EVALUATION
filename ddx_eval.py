# ddx_eval.py
from __future__ import annotations
import time
import pandas as pd
import streamlit as st
from typing import Dict, Any, List, Sequence

def _init_store():
    if "V3_ROWS" not in st.session_state:
        st.session_state.V3_ROWS: List[Dict[str, Any]] = []
    if "REVIEWER_NAME" not in st.session_state:
        st.session_state.REVIEWER_NAME = ""
    if "AUTO_ADVANCE_ON_SAVE" not in st.session_state:
        st.session_state.AUTO_ADVANCE_ON_SAVE = True

def _as_list(text: str) -> list[str]:
    if not text:
        return []
    parts: List[str] = []
    for line in text.splitlines():
        for p in line.replace("，", ",").replace(";", ",").split(","):
            p = p.strip()
            if p:
                parts.append(p)
    # dedup keep order
    seen, out = set(), []
    for x in parts:
        if x not in seen:
            out.append(x); seen.add(x)
    return out

def render_physician_ddx_and_evaluations(
    *,
    row: pd.Series,
    selected_idx: int,
    all_indices: Sequence[int],
    df_all: pd.DataFrame,
):
    """
    의사 DDX 작성 + 모델(Base/Applied) 각각 3개 리커트 + History(1개) + 코멘트 + 저장/자동 이동
    """
    _init_store()
    rk = f"row_{int(selected_idx)}"

    st.markdown("### Physician DDX & Evaluations")
    with st.container(border=True):
        # 헤더 + 진행률
        c1, c2 = st.columns([1.2, 1])
        with c1:
            # 세션 기본값 보장
            st.session_state.setdefault("REVIEWER_NAME", "")
            st.session_state.setdefault("AUTO_ADVANCE_ON_SAVE", True)

            # value 전달 제거 → key만 사용
            st.text_input("Reviewer (선택)", key="REVIEWER_NAME")
            st.checkbox("Save 후 다음 미평가 행으로 자동 이동", key="AUTO_ADVANCE_ON_SAVE")
        with c2:
            st.write(f"**File:** {row.get('file_name','')}")
            st.caption("Model(Base vs Applied) 비교 + Physician DDX + History 평가")

        evaluated_ids = [rec.get("row_id") for rec in st.session_state.V3_ROWS]
        done = len(set(e for e in evaluated_ids if e is not None))
        total_rows = len(all_indices)
        st.progress(done / total_rows if total_rows else 0.0, text=f"Progress: {done}/{total_rows} rows evaluated")


        # ---- 폼 ----
        with st.form(key=f"v3_form_{rk}", clear_on_submit=False):
            # 1) 의사 DDX (직접 생성)
            st.markdown("**1) Physician DDX (줄바꿈/쉼표로 구분)**")
            st.text_area(
                f"PHYS_DDX_{rk}",
                key=f"PHYS_DDX_{rk}",
                value="",
                placeholder="예) Colles' fracture\nDistal radial fracture\nRadial nerve injury",
                height=120,
            )

            st.markdown("**2) Model (Base) — Likert (1–5)**")
            b1, b2, b3 = st.columns(3)
            with b1:
                base_quality = st.slider("Quality: inclusion of final diagnosis", 1, 5, 3, key=f"BASE_QLT_{rk}")
            with b2:
                base_comp   = st.slider("Comprehensiveness", 1, 5, 3, key=f"BASE_COMP_{rk}")
            with b3:
                base_appr   = st.slider("Appropriateness", 1, 5, 3, key=f"BASE_APPR_{rk}")

            st.markdown("**3) Model (Applied) — Likert (1–5)**")
            a1, a2, a3 = st.columns(3)
            with a1:
                app_quality = st.slider("Quality: inclusion of final diagnosis ", 1, 5, 3, key=f"APP_QLT_{rk}")
            with a2:
                app_comp    = st.slider("Comprehensiveness ", 1, 5, 3, key=f"APP_COMP_{rk}")
            with a3:
                app_appr    = st.slider("Appropriateness ", 1, 5, 3, key=f"APP_APPR_{rk}")

            st.markdown("**4) History Adequacy (Current + Past) — Likert (1–5)**")
            hist_score = st.slider("History adequacy", 1, 5, 3, key=f"HIST_SCORE_{rk}")

            comment = st.text_area("Comment (선택)", value="", key=f"COMMENT_{rk}", height=80)

            saved = st.form_submit_button("Save evaluation", use_container_width=True, type="primary")

        if saved:
            new_rec: Dict[str, Any] = {
                "order": len(st.session_state.V3_ROWS) + 1,
                "row_id": int(selected_idx),
                "file_name": row.get("file_name",""),
                "reviewer": st.session_state.get("REVIEWER_NAME",""),
                "ts": int(time.time()),
                # 의사 DDX
                "phys_ddx": _as_list(st.session_state.get(f"PHYS_DDX_{rk}", "")),
                # Base 3점수
                "base_quality": int(st.session_state.get(f"BASE_QLT_{rk}", 3)),
                "base_comprehensiveness": int(st.session_state.get(f"BASE_COMP_{rk}", 3)),
                "base_appropriateness": int(st.session_state.get(f"BASE_APPR_{rk}", 3)),
                # Applied 3점수
                "applied_quality": int(st.session_state.get(f"APP_QLT_{rk}", 3)),
                "applied_comprehensiveness": int(st.session_state.get(f"APP_COMP_{rk}", 3)),
                "applied_appropriateness": int(st.session_state.get(f"APP_APPR_{rk}", 3)),
                # History 1점수
                "history_adequacy": int(st.session_state.get(f"HIST_SCORE_{rk}", 3)),
                "comment": st.session_state.get(f"COMMENT_{rk}", "").strip(),
            }

            # 행 단위 덮어쓰기
            rows = st.session_state.V3_ROWS
            existing_idx = next((i for i, r in enumerate(rows) if r.get("row_id") == int(selected_idx)), None)
            if existing_idx is not None:
                new_rec["order"] = rows[existing_idx].get("order", existing_idx + 1)
                rows[existing_idx] = new_rec
                st.info("Updated existing evaluation for this row.")
            else:
                rows.append(new_rec)
                st.success("Saved.")

            # 자동 이동: ROW_NAV_TARGET 사용 (ROW_PICKER 직접 수정 금지)
            if st.session_state.get("AUTO_ADVANCE_ON_SAVE", True):
                evaluated_set = set(r.get("row_id") for r in rows if r.get("row_id") is not None)
                unreviewed = [i for i in all_indices if i not in evaluated_set]
                if unreviewed:
                    greater = [i for i in unreviewed if i > selected_idx]
                    next_id = (min(greater) if greater else unreviewed[0])
                    st.session_state["ROW_NAV_TARGET"] = next_id
            st.rerun()

        # 미평가 목록 + 점프
        st.markdown("---")
        evaluated_set = set(e for e in evaluated_ids if e is not None)
        unreviewed = [i for i in all_indices if i not in evaluated_set]

        colA, colB = st.columns([1.3, 1])
        with colA:
            st.caption("Unreviewed rows")
            if unreviewed:
                preview = df_all.loc[unreviewed, ["file_name"]].reset_index().rename(columns={"index": "row_id"})
                st.dataframe(preview, use_container_width=True, height=180)
            else:
                st.success("All rows are evaluated 🎉")

        with colB:
            st.caption("Quick Nav")
            next_id = None
            if unreviewed:
                greater = [i for i in unreviewed if i > selected_idx]
                next_id = (min(greater) if greater else unreviewed[0])

            go1, go2 = st.columns(2)
            with go1:
                if st.button("Next unreviewed ▶", use_container_width=True, disabled=(next_id is None)):
                    st.session_state["ROW_NAV_TARGET"] = next_id
                    st.rerun()
            with go2:
                if st.button("First unreviewed ⏭", use_container_width=True, disabled=(not unreviewed)):
                    st.session_state["ROW_NAV_TARGET"] = unreviewed[0]
                    st.rerun()

        # 저장 미리보기 + 다운로드
        st.markdown("---")
        df_eval = pd.DataFrame(st.session_state.V3_ROWS)
        st.caption(f"Saved evaluations: **{len(df_eval)}** (unique rows: {len(evaluated_set)}/{total_rows})")
        if len(df_eval):
            df_eval = df_eval.sort_values("order")
            st.dataframe(df_eval.tail(10), use_container_width=True, height=220)
            csv_bytes = df_eval.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Download evaluations (CSV)",
                data=csv_bytes,
                file_name="physician_evaluations_v3.csv",
                mime="text/csv",
                use_container_width=True,
            )