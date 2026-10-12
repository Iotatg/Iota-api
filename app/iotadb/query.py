"""In-process JSON query, aggregation, and injection guards for IotaDB."""
from __future__ import annotations

from typing import Any

FORBIDDEN_OPERATORS = {
    "$where",
    "$eval",
    "$accumulator",
    "$function",
    "$expr",
    "$map",
    "$reduce",
    "$let",
    "$lookup",
    "$graphLookup",
}

ALLOWED_STAGES = {"$match", "$sort", "$limit", "$project", "$count"}
COMPARE_OPS = {"$gt", "$gte", "$lt", "$lte", "$in", "$ne", "$exists"}


def sanitize_query(query: Any) -> Any:
    if isinstance(query, dict):
        clean: dict[str, Any] = {}
        for k, v in query.items():
            if k in FORBIDDEN_OPERATORS or k.startswith("$where") or k.startswith("$function"):
                continue
            clean[k] = sanitize_query(v)
        return clean
    if isinstance(query, list):
        return [sanitize_query(item) for item in query]
    return query


def _match_op(value: Any, spec: dict[str, Any]) -> bool:
    for op, expected in spec.items():
        if op not in COMPARE_OPS:
            continue
        if op == "$exists":
            exists = value is not None
            if bool(expected) != exists:
                return False
            continue
        if value is None:
            return False
        if op == "$gt" and not (value > expected):
            return False
        if op == "$gte" and not (value >= expected):
            return False
        if op == "$lt" and not (value < expected):
            return False
        if op == "$lte" and not (value <= expected):
            return False
        if op == "$ne" and value == expected:
            return False
        if op == "$in":
            if not isinstance(expected, list) or value not in expected:
                return False
    return True


def _match_doc(doc: dict[str, Any], query: dict[str, Any] | None) -> bool:
    if not query:
        return True
    for key, spec in query.items():
        if key.startswith("$"):
            continue
        value = doc.get(key)
        if isinstance(spec, dict) and any(k.startswith("$") for k in spec):
            if "$exists" in spec:
                present = key in doc and doc.get(key) is not None
                if bool(spec["$exists"]) != present:
                    return False
                rest = {k: v for k, v in spec.items() if k != "$exists"}
                if rest and not _match_op(value, rest):
                    return False
            elif not _match_op(value, spec):
                return False
        elif value != spec:
            return False
    return True


def apply_query(docs: list[dict[str, Any]], query: dict[str, Any] | None) -> list[dict[str, Any]]:
    clean = sanitize_query(query or {})
    return [d for d in docs if _match_doc(d, clean)]


def run_aggregation(docs: list[dict[str, Any]], pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stages = sanitize_query(pipeline or [])
    if not isinstance(stages, list):
        raise ValueError("pipeline must be a list")
    current = list(docs)
    for stage in stages:
        if not isinstance(stage, dict) or not stage:
            raise ValueError("invalid aggregation stage")
        op = next(iter(stage.keys()))
        if op not in ALLOWED_STAGES:
            raise ValueError(f"unsupported aggregation stage: {op}")
        arg = stage[op]
        if op == "$match":
            current = apply_query(current, arg if isinstance(arg, dict) else {})
        elif op == "$sort":
            if not isinstance(arg, dict) or not arg:
                continue
            field = next(iter(arg.keys()))
            descending = int(arg[field]) < 0
            current = sorted(current, key=lambda d: d.get(field, 0), reverse=descending)
        elif op == "$limit":
            current = current[: max(0, int(arg))]
        elif op == "$project":
            if not isinstance(arg, dict):
                continue
            include = {k for k, v in arg.items() if v}
            projected = []
            for d in current:
                row = {k: d[k] for k in include if k in d}
                projected.append(row)
            current = projected
        elif op == "$count":
            name = arg if isinstance(arg, str) and arg else "count"
            return [{name: len(current)}]
    return current


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = sum(a * a for a in v1) ** 0.5
    mag2 = sum(b * b for b in v2) ** 0.5
    if not mag1 or not mag2:
        return 0.0
    return dot / (mag1 * mag2)
