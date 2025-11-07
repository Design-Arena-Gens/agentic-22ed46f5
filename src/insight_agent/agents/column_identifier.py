"""Agent responsible for mapping dataset columns into canonical metrics."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Sequence

from ..schemas import CANONICAL_COLUMNS, ColumnMapping


def _normalize(label: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", label.strip().lower())
    return re.sub(r"\s+", " ", cleaned).strip()


@dataclass
class SemanticColumnIdentifier:
    """Semantic column identifier with rule-based heuristics."""

    def __call__(
        self,
        columns: Iterable[str],
        hints: Optional[Mapping[str, str]] = None,
    ) -> ColumnMapping:
        hint_mapping = {key: hints[key] for key in hints or {} if key in CANONICAL_COLUMNS}
        normalized_columns = {name: _normalize(name) for name in columns}

        canonical_to_source: Dict[str, Optional[str]] = {k: None for k in CANONICAL_COLUMNS}

        # Apply explicit hints first
        for canonical, hinted_column in hint_mapping.items():
            if hinted_column in normalized_columns:
                canonical_to_source[canonical] = hinted_column
            else:
                # attempt relaxed match for hints
                normalized_hint = _normalize(hinted_column)
                target = _find_best_match(normalized_hint, normalized_columns)
                if target:
                    canonical_to_source[canonical] = target

        # Auto-match for remaining metrics
        for canonical, synonyms in CANONICAL_COLUMNS.items():
            if canonical_to_source.get(canonical):
                continue
            candidates = list(synonyms) + [canonical]
            for column_name, normalized in normalized_columns.items():
                if normalized in candidates:
                    canonical_to_source[canonical] = column_name
                    break
                if normalized.replace(" ", "") in {x.replace(" ", "") for x in candidates}:
                    canonical_to_source[canonical] = column_name
                    break
            if canonical_to_source[canonical]:
                continue
            target = _find_best_match(
                canonical,
                normalized_columns,
                fallback_candidates=candidates,
            )
            if target:
                canonical_to_source[canonical] = target

        return ColumnMapping(**canonical_to_source)


def _find_best_match(
    key: str,
    normalized_columns: Mapping[str, str],
    fallback_candidates: Optional[Sequence[str]] = None,
) -> Optional[str]:
    if fallback_candidates:
        normalized_targets = {candidate: _normalize(candidate) for candidate in fallback_candidates}
    else:
        normalized_targets = {key: _normalize(key)}

    for column_name, normalized in normalized_columns.items():
        if normalized in normalized_targets.values():
            return column_name
        if normalized.replace(" ", "") in {v.replace(" ", "") for v in normalized_targets.values()}:
            return column_name
    for column_name, normalized in normalized_columns.items():
        if normalized.startswith(_normalize(key.split()[0])):
            return column_name
    return None
