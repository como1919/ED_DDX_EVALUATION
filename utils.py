# utils.py
import re
import pandas as pd

def to_list_from_any(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    s = str(val).strip()
    if not s:
        return []
    parts = re.split(r"[,;\n]+", s)
    return [p.strip() for p in parts if p.strip()]

def pretty_multiline(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # []나 '' 제거, 쉼표/세미콜론은 줄바꿈
    t = text.strip()
    t = t.replace("[", "").replace("]", "").replace("'", "")
    t = re.sub(r"[;,]\s*", "\n", t)
    return t.strip()