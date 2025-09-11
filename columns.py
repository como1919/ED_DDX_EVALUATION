# columns.py
import json
import pandas as pd
from typing import Dict, Any, List

CANON = {
    "file_name": ["file_name"],
    "원본 초진기록": ["현병력-Free Text#13", "원본 초진기록"],
    "Current History": ["현병력-Free Text#13_Exaone_clean", "Current History"],
    "Past History": ["과거력-Free Text#14_Exaone_clean", "Past History"],
    "ASSO_SX_SN": ["ASSO_SX_SN"],
    "ASSO_DISEASE": ["ASSO_DISEASE"],
    "ASSO_TREATMENT": ["ASSO_TREATMENT"],
    "Label": ["CURRENT_COMPLAINT", "Label"],
    "llm_eval_raw_base": ["llm_eval_raw_base"],
    "llm_eval_raw_applied": ["llm_eval_raw_applied"],
    "Expected Diagnosis": ["expected_diagnosis_applied", "expected_diagnosis_base", "Expected Diagnosis"],
    "Differential Diagnoses list": ["differential_diagnoses_applied", "differential_diagnoses_base", "Differential Diagnoses list"],
    "Llm Evaluation Label": ["llm_eval_label_applied_strict", "llm_eval_label_applied_lenient", "Llm Evaluation Label"],
}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: Dict[str, str] = {}
    for canon, candidates in CANON.items():
        for c in candidates:
            if c in df.columns:
                rename_map[c] = canon
                break
    out = df.rename(columns=rename_map).copy()
    for k in CANON.keys():
        if k not in out.columns:
            out[k] = ""
    return out

def _safe_parse_json(s: str):
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        return json.loads(s)
    except Exception:
        return None

def _split_list_like(s: str) -> List[str]:
    if not isinstance(s, str):
        return []
    parts = [x.strip() for x in s.replace(";", ",").split(",") if x.strip()]
    return parts

def backfill_from_raw(df: pd.DataFrame, prefer: str = "applied") -> pd.DataFrame:
    """
    applied/base 양쪽 모두의 expected/ddx(+tier)를 파싱해 별도 컬럼으로 보관.
    또한 기존 코드와 호환을 위해 prefer(applied|base)에 따라 __exp_name__/__ddx_names__ 등 기본 뷰용 별칭도 채움.
    """
    def extract(row, which: str):
        raw_col = f"llm_eval_raw_{which}"
        obj = _safe_parse_json(row.get(raw_col, ""))
        if isinstance(obj, dict):
            exp = obj.get("expected", {}) or {}
            diffs = obj.get("differentials", []) or []
            exp_name = exp.get("name", "")
            exp_tier = exp.get("tier", "")
            ddx_names = [d.get("name", "") for d in diffs]
            ddx_tiers = [d.get("tier", "") for d in diffs]
        else:
            # 텍스트 기반 fallback
            if which == "applied":
                exp_name = row.get("Expected Diagnosis", "")
                ddx_names = _split_list_like(row.get("Differential Diagnoses list", ""))
            else:
                exp_name = ""
                ddx_names = []
            exp_tier = ""
            ddx_tiers = [""] * len(ddx_names)
        return exp_name, exp_tier, ddx_names, ddx_tiers

    exp_name_app, exp_tier_app, ddx_names_app, ddx_tiers_app = [], [], [], []
    exp_name_base, exp_tier_base, ddx_names_base, ddx_tiers_base = [], [], [], []

    for _, r in df.iterrows():
        a_name, a_tier, a_names, a_tiers = extract(r, "applied")
        b_name, b_tier, b_names, b_tiers = extract(r, "base")
        exp_name_app.append(a_name); exp_tier_app.append(a_tier); ddx_names_app.append(a_names); ddx_tiers_app.append(a_tiers)
        exp_name_base.append(b_name); exp_tier_base.append(b_tier); ddx_names_base.append(b_names); ddx_tiers_base.append(b_tiers)

    out = df.copy()
    # 상세 저장
    out["__exp_name_applied__"]  = exp_name_app
    out["__exp_tier_applied__"]  = exp_tier_app
    out["__ddx_names_applied__"] = ddx_names_app
    out["__ddx_tiers_applied__"] = ddx_tiers_app

    out["__exp_name_base__"]  = exp_name_base
    out["__exp_tier_base__"]  = exp_tier_base
    out["__ddx_names_base__"] = ddx_names_base
    out["__ddx_tiers_base__"] = ddx_tiers_base

    # 기본 뷰용 별칭 (prefer 우선)
    if prefer == "applied":
        out["__exp_name__"]  = out["__exp_name_applied__"]
        out["__exp_tier__"]  = out["__exp_tier_applied__"]
        out["__ddx_names__"] = out["__ddx_names_applied__"]
        out["__ddx_tiers__"] = out["__ddx_tiers_applied__"]
    else:
        out["__exp_name__"]  = out["__exp_name_base__"]
        out["__exp_tier__"]  = out["__exp_tier_base__"]
        out["__ddx_names__"] = out["__ddx_names_base__"]
        out["__ddx_tiers__"] = out["__ddx_tiers_base__"]

    return out