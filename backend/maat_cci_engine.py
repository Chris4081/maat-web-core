from __future__ import annotations

import re
from typing import Any


LAST_ADVANCED_CCI: dict[str, Any] | None = None


def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, float(value)))


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", str(text or "")))


def _sentence_count(text: str) -> int:
    return len([part for part in re.split(r"[.!?]+", str(text or "")) if part.strip()])


def _instability(text: str) -> float:
    wc = _word_count(text)
    sc = _sentence_count(text)
    value = 3.0
    if wc > 120:
        value += 2.0
    if sc > 6:
        value += 1.5
    if "!!!" in text or "???" in text:
        value += 1.5
    return _clamp(value)


def _production(text: str) -> float:
    t = _norm(text)
    keywords = ["idee", "beispiel", "struktur", "modell", "idea", "example", "structure", "model"]
    return _clamp(3.0 + sum(0.8 for keyword in keywords if keyword in t))


def _coherence(text: str) -> float:
    wc = _word_count(text)
    sc = _sentence_count(text)
    value = 5.0
    if 20 <= wc <= 180:
        value += 1.5
    if 1 <= sc <= 6:
        value += 1.5
    if "1." in text or "-" in text:
        value += 1.0
    return _clamp(value)


def _consistency(text: str) -> float:
    t = _norm(text)
    value = 6.0
    if "aber" in t or "jedoch" in t or "gleichzeitig" in t:
        value += 1.0
    if "immer" in t and "nie" in t:
        value -= 2.0
    return _clamp(value)


def _correctness(text: str) -> float:
    t = _norm(text)
    value = 6.5
    if "ich weiß nicht" in t or "ich weiss nicht" in t or "nicht sicher" in t:
        value += 1.5
    if "definitiv" in t or "garantiert" in t or "100% sicher" in t:
        value -= 1.5
    return _clamp(value)


def _integration(user_input: str, output: str) -> float:
    user_words = set(_norm(user_input).split())
    output_words = set(_norm(output).split())
    overlap = len(user_words & output_words)
    return _clamp(3.0 + overlap * 0.3)


def _structural_uncertainty(maat_eval: dict[str, Any] | None) -> float:
    if not maat_eval:
        return 1.0
    try:
        values = [float(maat_eval[key]) for key in ("H", "B", "S", "V", "R")]
    except (KeyError, TypeError, ValueError):
        return 1.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def compute_advanced_cci(
    user_input: str,
    output: str,
    maat_eval: dict[str, Any] | None = None,
    *,
    kappa: float = 0.5,
) -> dict[str, Any]:
    eps = 0.01
    safe_kappa = max(0.0, min(float(kappa or 0.5), 5.0))

    gamma_inst = _instability(output)
    gamma_prod = _production(output)
    gamma_coh = _coherence(output)
    gamma_cons = _consistency(output)
    gamma_corr = _correctness(output)
    gamma_int = _integration(user_input, output)
    u_struct = _structural_uncertainty(maat_eval)

    cci = (gamma_inst * gamma_prod * (1 + safe_kappa * u_struct)) / (
        gamma_coh + gamma_cons + gamma_corr + gamma_int + eps
    )

    if cci < 0.28:
        regime = "ordered"
    elif cci < 0.35:
        regime = "critical"
    else:
        regime = "chaotic"

    components = {
        "inst": round(gamma_inst, 2),
        "prod": round(gamma_prod, 2),
        "coh": round(gamma_coh, 2),
        "cons": round(gamma_cons, 2),
        "corr": round(gamma_corr, 2),
        "int": round(gamma_int, 2),
        "U_struct": round(u_struct, 3),
        "kappa": round(safe_kappa, 3),
    }
    return {
        "cci": round(cci, 4),
        "CCI": round(cci, 4),
        "regime": regime,
        "components": components,
        "text": f"Advanced CCI={cci:.4f} → {regime}",
    }


def report_lines(result: dict[str, Any] | None) -> list[str]:
    if not result:
        return ["Advanced CCI: noch keine Antwort analysiert."]
    components = result.get("components") or {}
    return [
        str(result.get("text") or "Advanced CCI=n/a"),
        (
            "components: "
            f"inst={components.get('inst', 0):.2f} "
            f"prod={components.get('prod', 0):.2f} "
            f"coh={components.get('coh', 0):.2f} "
            f"cons={components.get('cons', 0):.2f} "
            f"corr={components.get('corr', 0):.2f} "
            f"int={components.get('int', 0):.2f} "
            f"U_struct={components.get('U_struct', 0):.3f}"
        ),
    ]


def remember_advanced_cci(result: dict[str, Any]) -> None:
    global LAST_ADVANCED_CCI
    LAST_ADVANCED_CCI = result


def get_last_advanced_cci() -> dict[str, Any] | None:
    return LAST_ADVANCED_CCI
