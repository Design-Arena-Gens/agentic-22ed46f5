"""Agent for calculating derived performance metrics."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Mapping, Sequence

from ..schemas import ColumnMapping


@dataclass
class MetricSummary:
    column_mapping: ColumnMapping
    per_row: List[Dict[str, Any]]
    aggregates: Dict[str, float]


class MetricCalculator:
    def __call__(
        self,
        records: Sequence[Mapping[str, Any]],
        mapping: ColumnMapping,
    ) -> MetricSummary:
        records_list = list(records)
        per_row_metrics = self._derive_row_metrics(records_list, mapping)
        aggregate_metrics = self._aggregate(per_row_metrics)

        return MetricSummary(
            column_mapping=mapping,
            per_row=per_row_metrics,
            aggregates=aggregate_metrics,
        )

    def _derive_row_metrics(self, records: Sequence[Mapping[str, Any]], mapping: ColumnMapping) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for record in records:
            metrics: Dict[str, Any] = {}
            for canonical in mapping.available_metrics():
                column = mapping.resolve(canonical)
                if column is None:
                    continue
                value = record.get(column)
                if canonical in self._numeric_fields():
                    metrics[canonical] = self._to_float(value)
                else:
                    metrics[canonical] = value

            metrics["ctr"] = self._compute_ctr(metrics)
            metrics["atc_to_purchase"] = self._compute_ratio(
                metrics.get("purchases"), metrics.get("adds_to_cart")
            )
            metrics["ctr_delta"] = self._compute_ctr_delta(metrics)
            results.append(metrics)
        return results

    def _compute_ctr(self, metrics: Mapping[str, Any]) -> float:
        value = metrics.get("ctr")
        if self._is_valid_number(value):
            return float(value)
        clicks = metrics.get("clicks")
        impressions = metrics.get("impressions")
        if not self._is_valid_number(clicks) or not self._is_valid_number(impressions):
            return float("nan")
        if float(impressions) == 0:
            return float("nan")
        return float(clicks) / float(impressions)

    def _compute_ratio(self, numerator: Any, denominator: Any) -> float:
        if not self._is_valid_number(numerator) or not self._is_valid_number(denominator):
            return float("nan")
        if float(denominator) == 0:
            return float("nan")
        return float(numerator) / float(denominator)

    def _compute_ctr_delta(self, metrics: Mapping[str, Any]) -> float:
        current = metrics.get("ctr_7d")
        if not self._is_valid_number(current):
            current = metrics.get("ctr")
        previous = metrics.get("ctr_prev7")
        if not self._is_valid_number(current) or not self._is_valid_number(previous):
            return float("nan")
        prev_value = float(previous)
        if prev_value == 0:
            return float("nan")
        return (float(current) - prev_value) / prev_value

    def _aggregate(self, rows: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
        sums: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for row in rows:
            for metric in [
                "spend",
                "impressions",
                "clicks",
                "purchases",
                "purchase_value",
                "adds_to_cart",
            ]:
                value = row.get(metric)
                if self._is_valid_number(value):
                    sums[f"total_{metric}"] = sums.get(f"total_{metric}", 0.0) + float(value)

            for metric in [
                "ctr",
                "frequency",
                "roas",
                "atc_to_purchase",
                "ctr_7d",
                "ctr_prev7",
                "ctr_delta",
            ]:
                value = row.get(metric)
                if self._is_valid_number(value):
                    key = f"avg_{metric}"
                    sums[key] = sums.get(key, 0.0) + float(value)
                    counts[key] = counts.get(key, 0) + 1

        for key, count in counts.items():
            if count:
                sums[key] = sums[key] / count
        return sums

    def _numeric_fields(self) -> set[str]:
        return {
            "spend",
            "impressions",
            "clicks",
            "ctr",
            "frequency",
            "roas",
            "purchases",
            "purchase_value",
            "adds_to_cart",
            "ctr_7d",
            "ctr_prev7",
        }

    def _to_float(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace("%", ""))
            except ValueError:
                return float("nan")
        return float("nan")

    def _is_valid_number(self, value: Any) -> bool:
        if value is None:
            return False
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return False
        return math.isfinite(numeric)
