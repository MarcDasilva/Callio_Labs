"""Simple pure-Python primer design. No Primer3 dependency; fast, no timeouts.

Output matches Primer3 Boulder-style so the same stats are present (Tm, GC, penalty,
self-complementarity, product size, etc.). Thermodynamic/structure fields use
simple estimates or 0 when not computed.
"""

from __future__ import annotations

from typing import Any

# Defaults
PRIMER_LEN = 20
PRODUCT_MIN = 80
PRODUCT_MAX = 400
NUM_RETURN = 3

COMPLEMENT = str.maketrans("ACGTacgt", "TGCAtgca")


def revcomp(seq: str) -> str:
    """Return reverse complement of DNA sequence."""
    return seq.translate(COMPLEMENT)[::-1]


def gc_content(seq: str) -> float:
    """GC content as fraction 0-1."""
    s = seq.upper()
    if not s:
        return 0.0
    return (s.count("G") + s.count("C")) / len(s)


def simple_tm(seq: str) -> float:
    """Tm in °C (Wallace rule: 2*(A+T) + 4*(G+C) for short oligos in 50 mM Na+)."""
    s = seq.upper()
    if not s:
        return 0.0
    at = s.count("A") + s.count("T")
    gc = s.count("G") + s.count("C")
    return 2 * at + 4 * gc


def _end_stability(seq: str) -> float:
    """Approximate 3' end stability (dG). Simple: -0.5 per G/C at last 5 bases."""
    s = seq.upper()[-5:] if len(seq) >= 5 else seq.upper()
    return -0.5 * (s.count("G") + s.count("C"))


def _self_any_score(seq: str) -> float:
    """Placeholder: self-complementarity any (kcal/mol). Not computed; return 0."""
    return 0.0


def _self_end_score(seq: str) -> float:
    """Placeholder: 3' self-complementarity (kcal/mol). Not computed; return 0."""
    return 0.0


def _compl_any_score(left_seq: str, right_seq: str) -> float:
    """Placeholder: pair complementarity any (kcal/mol). Not computed; return 0."""
    return 0.0


def _compl_end_score(left_seq: str, right_seq: str) -> float:
    """Placeholder: 3' pair complementarity (kcal/mol). Not computed; return 0."""
    return 0.0


def design_primers(
    sequence: str,
    sequence_id: str = "seq",
    target_start: int = 0,
    target_len: int | None = None,
    product_min: int = PRODUCT_MIN,
    product_max: int = PRODUCT_MAX,
    primer_len: int = PRIMER_LEN,
    num_return: int = NUM_RETURN,
) -> dict[str, Any]:
    """
    Design primer pairs that amplify a target region. Returns a dict in
    Boulder-style shape (PRIMER_LEFT, PRIMER_RIGHT, PRIMER_PAIR, etc.)
    for compatibility with existing API responses.
    """
    seq = sequence.upper().replace(" ", "").replace("\n", "")
    if not seq or not all(c in "ACGTN" for c in seq):
        return _empty_result(sequence_id)

    L = len(seq)
    if target_len is None:
        target_len = min(80, L)
    target_end = min(target_start + target_len, L)
    target_len = target_end - target_start
    if target_len < 10:
        return _empty_result(sequence_id)

    # We want product size in [product_min, product_max]. Product = (right_3' - left_5' + 1).
    # Forward primer 5' at left_5', reverse primer 3' at right_3' (on template).
    # So left_5' can be at target_start (or a bit left), right_3' at target_end-1 or more.
    product_opt = min(product_max, max(product_min, target_len + 40))
    pairs: list[dict[str, Any]] = []

    for i in range(num_return):
        # Vary product size slightly for multiple suggestions
        size = product_opt + (i - num_return // 2) * 20
        size = max(product_min, min(product_max, size))
        # Left primer 5' position; right primer 3' position = left_5' + size - 1
        left_5 = max(0, target_start)
        right_3 = left_5 + size - 1
        if right_3 >= L:
            right_3 = L - 1
            left_5 = right_3 - size + 1
            if left_5 < 0:
                left_5 = 0
                right_3 = min(left_5 + size - 1, L - 1)
        # Forward: from left_5, length primer_len
        fwd_seq = seq[left_5 : left_5 + primer_len]
        # Reverse: 3' on template at right_3, so reverse primer binds template[right_3 - primer_len + 1 : right_3 + 1], revcomp
        rev_start = right_3 - primer_len + 1
        if rev_start < 0:
            rev_start = 0
        rev_template = seq[rev_start : right_3 + 1]
        rev_seq = revcomp(rev_template)
        if len(fwd_seq) < 16 or len(rev_seq) < 16:
            continue
        product_size = right_3 - left_5 + 1
        left_tm = simple_tm(fwd_seq)
        right_tm = simple_tm(rev_seq)
        left_gc = gc_content(fwd_seq)
        right_gc = gc_content(rev_seq)
        pairs.append({
            "left_start": left_5,
            "left_len": len(fwd_seq),
            "right_start": rev_start,
            "right_len": len(rev_seq),
            "left_seq": fwd_seq,
            "right_seq": rev_seq,
            "product_size": product_size,
            "left_tm": left_tm,
            "right_tm": right_tm,
            "left_gc": left_gc,
            "right_gc": right_gc,
            "left_penalty": 0.0,
            "right_penalty": 0.0,
            "pair_penalty": 0.0,
            "left_self_any": _self_any_score(fwd_seq),
            "right_self_any": _self_any_score(rev_seq),
            "left_self_end": _self_end_score(fwd_seq),
            "right_self_end": _self_end_score(rev_seq),
            "left_end_stability": _end_stability(fwd_seq),
            "right_end_stability": _end_stability(rev_seq),
            "compl_any": _compl_any_score(fwd_seq, rev_seq),
            "compl_end": _compl_end_score(fwd_seq, rev_seq),
            "product_tm": (left_tm + right_tm) / 2.0,
        })

    return _boulder_result(sequence_id, seq, pairs)


def _empty_result(sequence_id: str) -> dict[str, Any]:
    return {
        "PRIMER_LEFT_EXPLAIN": "no sequence or invalid",
        "PRIMER_RIGHT_EXPLAIN": "",
        "PRIMER_PAIR_EXPLAIN": "",
        "PRIMER_LEFT_NUM_RETURNED": 0,
        "PRIMER_RIGHT_NUM_RETURNED": 0,
        "PRIMER_INTERNAL_NUM_RETURNED": 0,
        "PRIMER_PAIR_NUM_RETURNED": 0,
        "PRIMER_LEFT": [],
        "PRIMER_RIGHT": [],
        "PRIMER_INTERNAL": [],
        "PRIMER_PAIR": [],
    }


def _boulder_result(sequence_id: str, seq: str, pairs: list[dict]) -> dict[str, Any]:
    """Build Boulder-style result dict matching Primer3 output keys."""
    n = len(pairs)
    result: dict[str, Any] = {
        "PRIMER_LEFT_EXPLAIN": f"ok {n}",
        "PRIMER_RIGHT_EXPLAIN": f"ok {n}",
        "PRIMER_PAIR_EXPLAIN": f"ok {n}",
        "PRIMER_INTERNAL_EXPLAIN": "",
        "PRIMER_LEFT_NUM_RETURNED": n,
        "PRIMER_RIGHT_NUM_RETURNED": n,
        "PRIMER_INTERNAL_NUM_RETURNED": 0,
        "PRIMER_PAIR_NUM_RETURNED": n,
        "PRIMER_LEFT": [],
        "PRIMER_RIGHT": [],
        "PRIMER_INTERNAL": [],
        "PRIMER_PAIR": [],
    }
    for i, p in enumerate(pairs):
        left_gc_pct = p["left_gc"] * 100
        right_gc_pct = p["right_gc"] * 100
        # Coordinates: [start_0-based, length] (Primer3 uses 0-based in API)
        result["PRIMER_LEFT"].append([p["left_start"], p["left_len"]])
        result["PRIMER_RIGHT"].append([p["right_start"], p["right_len"]])
        # PRIMER_PAIR[i] = dict like Primer3 (PENALTY, PRODUCT_SIZE, COMPL_ANY, etc.)
        result["PRIMER_PAIR"].append({
            "PENALTY": p["pair_penalty"],
            "PRODUCT_SIZE": p["product_size"],
            "COMPL_ANY": p["compl_any"],
            "COMPL_END": p["compl_end"],
            "PRODUCT_TM": p["product_tm"],
        })
        # Per-primer flat keys (same as Primer3)
        result[f"PRIMER_LEFT_{i}"] = [p["left_start"], p["left_len"]]
        result[f"PRIMER_RIGHT_{i}"] = [p["right_start"], p["right_len"]]
        result[f"PRIMER_LEFT_{i}_SEQUENCE"] = p["left_seq"]
        result[f"PRIMER_RIGHT_{i}_SEQUENCE"] = p["right_seq"]
        result[f"PRIMER_LEFT_{i}_TM"] = p["left_tm"]
        result[f"PRIMER_RIGHT_{i}_TM"] = p["right_tm"]
        result[f"PRIMER_LEFT_{i}_GC_PERCENT"] = left_gc_pct
        result[f"PRIMER_RIGHT_{i}_GC_PERCENT"] = right_gc_pct
        result[f"PRIMER_LEFT_{i}_PENALTY"] = p["left_penalty"]
        result[f"PRIMER_RIGHT_{i}_PENALTY"] = p["right_penalty"]
        result[f"PRIMER_LEFT_{i}_PROBLEMS"] = ""
        result[f"PRIMER_RIGHT_{i}_PROBLEMS"] = ""
        result[f"PRIMER_LEFT_{i}_SELF_ANY"] = p["left_self_any"]
        result[f"PRIMER_RIGHT_{i}_SELF_ANY"] = p["right_self_any"]
        result[f"PRIMER_LEFT_{i}_SELF_ANY_TH"] = p["left_self_any"]
        result[f"PRIMER_RIGHT_{i}_SELF_ANY_TH"] = p["right_self_any"]
        result[f"PRIMER_LEFT_{i}_SELF_END"] = p["left_self_end"]
        result[f"PRIMER_RIGHT_{i}_SELF_END"] = p["right_self_end"]
        result[f"PRIMER_LEFT_{i}_SELF_END_TH"] = p["left_self_end"]
        result[f"PRIMER_RIGHT_{i}_SELF_END_TH"] = p["right_self_end"]
        result[f"PRIMER_LEFT_{i}_END_STABILITY"] = p["left_end_stability"]
        result[f"PRIMER_RIGHT_{i}_END_STABILITY"] = p["right_end_stability"]
        # Per-pair flat keys
        result[f"PRIMER_PAIR_{i}_PENALTY"] = p["pair_penalty"]
        result[f"PRIMER_PAIR_{i}_PRODUCT_SIZE"] = p["product_size"]
        result[f"PRIMER_PAIR_{i}_PRODUCT_TM"] = p["product_tm"]
        result[f"PRIMER_PAIR_{i}_COMPL_ANY"] = p["compl_any"]
        result[f"PRIMER_PAIR_{i}_COMPL_ANY_TH"] = p["compl_any"]
        result[f"PRIMER_PAIR_{i}_COMPL_END"] = p["compl_end"]
        result[f"PRIMER_PAIR_{i}_COMPL_END_TH"] = p["compl_end"]
    return result
