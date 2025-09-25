# columns.py
import json
import re
import ast
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional

# ─────────────────────────────────────────────────────────────
# 1) 컬럼 정규화
#    - applied/base를 동일 키로 합치지 않도록 주의!
#    - 각 버전을 별도로 표준화하고, generic은 backfill에서 채운다.
# ─────────────────────────────────────────────────────────────
CANON = {
    "file_name": ["file_name"],
    "원본 초진기록": ["현병력-Free Text#13", "원본 초진기록"],
    "Current History": ["현병력-Free Text#13_Exaone_clean", "Current History"],
    "Past History": ["과거력-Free Text#14_Exaone_clean", "Past History"],

    # 원래 있던 ASSO는 있으면 살리고, 없으면 나중에 비표시
    "ASSO_SX_SN": ["ASSO_SX_SN"],
    "ASSO_DISEASE": ["ASSO_DISEASE"],
    "ASSO_TREATMENT": ["ASSO_TREATMENT"],

    # LLM raw(JSON) 결과 (있으면 파싱에 사용)
    "llm_eval_raw_base": ["llm_eval_raw_base"],
    "llm_eval_raw_applied": ["llm_eval_raw_applied"],

    # applied/base를 별도 표준 컬럼으로 보존
    "Expected Diagnosis (applied)": ["expected_diagnosis_applied"],
    "Differential Diagnoses (applied)": ["differential_diagnoses_applied"],
    "Expected Diagnosis (base)": ["expected_diagnosis_base"],
    "Differential Diagnoses (base)": ["differential_diagnoses_base"],

    # (예전 호환) LLM 평가 라벨 (있어도 v3에서는 기본 숨김)
    "Llm Evaluation Label (applied/strict)": ["llm_eval_label_applied_strict"],
    "Llm Evaluation Label (applied/lenient)": ["llm_eval_label_applied_lenient"],
    "Llm Evaluation Label (base/strict)": ["llm_eval_label_base_strict"],
    "Llm Evaluation Label (base/lenient)": ["llm_eval_label_base_lenient"],
}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: Dict[str, str] = {}
    for canon, candidates in CANON.items():
        for c in candidates:
            if c in df.columns:
                rename_map[c] = canon
                break
    out = df.rename(columns=rename_map).copy()
    # ensure all canon columns exist
    for k in CANON.keys():
        if k not in out.columns:
            out[k] = ""
    return out

# ─────────────────────────────────────────────────────────────
# 2) 파서 유틸
#    - JSON/문자열을 안전하게 Expected(단건 문자열)과 Differentials(다건 리스트)로 변환
# ─────────────────────────────────────────────────────────────
def _safe_json_load(s: str) -> Optional[Any]:
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        norm = s.replace("None", "null").replace("True", "true").replace("False", "false")
        return json.loads(norm)
    except Exception:
        return None

def _parse_expected(val: Any) -> str:
    """Expected를 단일 문자열로 정규화"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if not s:
        return ""

    # 1) JSON(dict/list) 시도
    if s.startswith("{") or s.startswith("["):
        x = _safe_json_load(s)
        if isinstance(x, dict):
            for k in ("name", "diagnosis", "text", "value"):
                if x.get(k):
                    return str(x[k])
            return s
        if isinstance(x, list) and x:
            first = x[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                for k in ("name", "diagnosis", "text", "value"):
                    if first.get(k):
                        return str(first[k])
            return str(first)

        # 2) JSON 실패 시: 파이썬 리터럴(list/dict) 시도
        try:
            y = ast.literal_eval(s)
            if isinstance(y, dict):
                for k in ("name", "diagnosis", "text", "value"):
                    if y.get(k):
                        return str(y[k])
                return s
            if isinstance(y, list) and y:
                return str(y[0]) if not isinstance(y[0], dict) else str(y[0].get("name", "")) or str(y[0])
        except Exception:
            pass

    # 3) 그냥 문자열
    return s

def _parse_diffs(val: Any) -> List[str]:
    """Differentials를 문자열 리스트로 정규화"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    s = str(val).strip()
    if not s:
        return []

    # 1) JSON(list/dict) 시도
    if s.startswith("[") or s.startswith("{"):
        x = _safe_json_load(s)
        if isinstance(x, list):
            out = []
            for it in x:
                if isinstance(it, str):
                    out.append(it.strip())
                elif isinstance(it, dict):
                    for k in ("name", "diagnosis", "text", "value"):
                        if it.get(k):
                            out.append(str(it[k]))
                            break
            return out
        if isinstance(x, dict):
            for k in ("name", "diagnosis", "text", "value"):
                if x.get(k):
                    return [str(x[k])]
            return [s]

        # 2) JSON 실패 시: 파이썬 리스트 리터럴 시도
        try:
            y = ast.literal_eval(s)
            if isinstance(y, list):
                return [str(it.get("name")) if isinstance(it, dict) and it.get("name") else str(it) for it in y]
            if isinstance(y, dict):
                for k in ("name", "diagnosis", "text", "value"):
                    if y.get(k):
                        return [str(y[k])]
                return [s]
        except Exception:
            pass

    # 3) 최후수단: 콤마/세미콜론/줄바꿈 분할 → 대괄호/따옴표 정리
    parts = re.split(r"[,;\n]+", s)
    clean = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 양 끝 대괄호/따옴표 제거
        p = p.strip("[]'\" ")
        if p:
            clean.append(p)
    return clean

def _mk_rows(expected: str, diffs: List[str]) -> List[Dict[str, str]]:
    """Core View 표용: Expected + Differential을 Role로 구분한 행 리스트"""
    rows: List[Dict[str, str]] = []
    if expected:
        rows.append({"Diagnosis": expected, "Role": "Expected"})
    for d in diffs:
        rows.append({"Diagnosis": d, "Role": "Differential"})
    return rows

# ─────────────────────────────────────────────────────────────
# 3) backfill_from_raw
#    - llm_eval_raw_* → 우선 파싱
#    - 없으면 Expected/Diff (applied/base) 표준 컬럼에서 파싱
#    - __ddx_table_* 및 generic(*prefer*) 컬럼까지 생성
# ─────────────────────────────────────────────────────────────
def _extract_from_llm_raw(row: pd.Series, which: str) -> Tuple[str, str, List[str], List[str]]:
    """llm_eval_raw_{which}에서 expected.name/tier, differentials[].name/tier를 추출"""
    raw_col = f"llm_eval_raw_{which}"
    obj = _safe_json_load(row.get(raw_col, ""))
    if not isinstance(obj, dict):
        return "", "", [], []
    exp = obj.get("expected") or {}
    diffs = obj.get("differentials") or []
    exp_name = str(exp.get("name", "") or "")
    exp_tier = str(exp.get("tier", "") or "")
    ddx_names, ddx_tiers = [], []
    for d in diffs if isinstance(diffs, list) else []:
        if isinstance(d, dict):
            ddx_names.append(str(d.get("name", "") or ""))
            ddx_tiers.append(str(d.get("tier", "") or ""))
        else:
            ddx_names.append(str(d))
            ddx_tiers.append("")
    return exp_name, exp_tier, ddx_names, ddx_tiers

def backfill_from_raw(df: pd.DataFrame, prefer: str = "applied") -> pd.DataFrame:
    """
    - applied/base 각각에 대해 Expected/Diff를 안전 파싱하여 별도 컬럼(__exp_name_*__, __ddx_names_*__ 등)에 적재
    - Core View 표용 __ddx_table_base__/__ddx_table_applied__ 생성
    - prefer(applied|base)에 따라 generic(__exp_name__, __ddx_names__ 등) 채움
    """
    out = df.copy()

    # applied
    exp_name_app, exp_tier_app, ddx_names_app, ddx_tiers_app = [], [], [], []
    # base
    exp_name_base, exp_tier_base, ddx_names_base, ddx_tiers_base = [], [], [], []

    for _, row in out.iterrows():
        # 1) 우선 llm_eval_raw_*에서 시도
        a_name, a_tier, a_names, a_tiers = _extract_from_llm_raw(row, "applied")
        b_name, b_tier, b_names, b_tiers = _extract_from_llm_raw(row, "base")

        # 2) 실패 시 표준 컬럼에서 보완
        if not a_name:
            # Expected Diagnosis (applied) 가 있으면 사용
            a_name = _parse_expected(row.get("Expected Diagnosis (applied)", "")) \
                     or _parse_expected(row.get("Expected Diagnosis", ""))  # 매우 예외적 호환
        if not a_names:
            a_names = _parse_diffs(row.get("Differential Diagnoses (applied)", "")) \
                      or _parse_diffs(row.get("Differential Diagnoses list", ""))  # 매우 예외적 호환
        if not a_tiers:
            a_tiers = [""] * len(a_names)

        if not b_name:
            b_name = _parse_expected(row.get("Expected Diagnosis (base)", ""))
        if not b_names:
            b_names = _parse_diffs(row.get("Differential Diagnoses (base)", ""))
        if not b_tiers:
            b_tiers = [""] * len(b_names)

        exp_name_app.append(a_name); exp_tier_app.append(a_tier); ddx_names_app.append(a_names); ddx_tiers_app.append(a_tiers)
        exp_name_base.append(b_name); exp_tier_base.append(b_tier); ddx_names_base.append(b_names); ddx_tiers_base.append(b_tiers)

    # 상세 저장
    out["__exp_name_applied__"]  = exp_name_app
    out["__exp_tier_applied__"]  = exp_tier_app
    out["__ddx_names_applied__"] = ddx_names_app
    out["__ddx_tiers_applied__"] = ddx_tiers_app

    out["__exp_name_base__"]  = exp_name_base
    out["__exp_tier_base__"]  = exp_tier_base
    out["__ddx_names_base__"] = ddx_names_base
    out["__ddx_tiers_base__"] = ddx_tiers_base

    # Core View 표용
    out["__ddx_table_applied__"] = [
        _mk_rows(e, ds) for e, ds in zip(out["__exp_name_applied__"], out["__ddx_names_applied__"])
    ]
    out["__ddx_table_base__"] = [
        _mk_rows(e, ds) for e, ds in zip(out["__exp_name_base__"], out["__ddx_names_base__"])
    ]

    # (레거시) 이름만 합친 리스트
    out["__ddx_names__applied_only"] = [
        list(dict.fromkeys(([e] if e else []) + ds)) for e, ds in zip(out["__exp_name_applied__"], out["__ddx_names_applied__"])
    ]
    out["__ddx_names__base_only"] = [
        list(dict.fromkeys(([e] if e else []) + ds)) for e, ds in zip(out["__exp_name_base__"], out["__ddx_names_base__"])
    ]

    # generic (prefer 우선) — 기존 코드 호환을 위해 제공
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