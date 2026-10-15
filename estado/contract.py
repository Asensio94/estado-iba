"""Check a signals.json against the contract (CONTRATO.md and signals.schema.json).

The build reads leniently: a bad signal is dropped and the rest is published. This check is
strict, so that whoever publishes learns what the panel drops before it drops it.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from functools import cache

from jsonschema import Draft202012Validator

from . import config

SCHEMA_PATH = config.ROOT / "signals.schema.json"
MAX_MESSAGE = 160


@cache
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def kinds() -> set[str]:
    return set(schema()["$defs"]["signal"]["properties"]["kind"]["enum"])


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    unknown_kinds: Counter = field(default_factory=Counter)  # kind -> signals the panel drops
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and not self.unknown_kinds


def _where(path) -> str:
    out = ""
    for p in path:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else p)
    return out or "(raíz)"


def validate(doc: dict, source: str | None = None) -> Report:
    """Everything that breaks the contract, with kinds outside it counted apart: they are the usual drift."""
    r = Report()
    for e in Draft202012Validator(schema()).iter_errors(doc):
        path = list(e.absolute_path)
        if path[-1:] == ["kind"] and e.validator == "enum" and isinstance(e.instance, str):
            r.unknown_kinds[e.instance] += 1
            continue
        msg = e.message if len(e.message) <= MAX_MESSAGE else e.message[:MAX_MESSAGE] + "…"
        r.errors.append(f"{_where(path)}: {msg}")
    if source and isinstance(doc, dict) and doc.get("source") != source:
        r.errors.append(f"source: {doc.get('source')!r} en vez de {source!r}")
    signals = doc.get("signals") if isinstance(doc, dict) else None
    if not isinstance(signals, list):
        return r
    ids = Counter(str(s.get("id")) for s in signals if isinstance(s, dict))
    if dup := sorted(i for i, n in ids.items() if n > 1):
        r.errors.append(f"{len(dup)} id repetidos: {', '.join(dup[:5])}")
    unplaced = [str(s.get("id")) for s in signals if isinstance(s, dict) and s.get("precision") == "punto"
                and not (s.get("sites") or s.get("municipalities") or s.get("municipality_names")
                         or (s.get("details") or {}).get("point"))]
    if unplaced:
        r.warnings.append(f"{len(unplaced)} señales «punto» sin lugar ni details.point, que el panel no puede situar: "
                          + ", ".join(unplaced[:5]))
    return r


def describe(r: Report, limit: int = 10) -> list[str]:
    """The report as lines in Spanish, the most useful first."""
    lines = [f"{n} señales de tipo «{k}», que el contrato no recoge: el panel las descarta."
             for k, n in r.unknown_kinds.most_common()]
    lines += r.errors[:limit]
    if len(r.errors) > limit:
        lines.append(f"… y {len(r.errors) - limit} errores más.")
    return lines + r.warnings
