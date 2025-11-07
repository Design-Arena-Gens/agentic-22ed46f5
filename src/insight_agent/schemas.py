"""Pydantic schemas used across the InsightAgent engine."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence

from pydantic import BaseModel, Field, model_validator


CANONICAL_COLUMNS: Dict[str, Sequence[str]] = {
    "campaign_name": ("campaign name", "campaign"),
    "ad_set_name": ("ad set name", "adset", "ad set"),
    "ad_name": ("ad name", "ad"),
    "ad_id": ("ad id", "creative id", "asset id"),
    "spend": ("spend", "cost"),
    "impressions": ("impressions", "impr"),
    "clicks": ("clicks", "link clicks"),
    "ctr": ("ctr", "click through rate", "ctr %"),
    "frequency": ("frequency",),
    "roas": ("roas", "return on ad spend"),
    "purchases": ("purchases", "purchase"),
    "purchase_value": ("purchase value", "purchase revenue", "revenue"),
    "adds_to_cart": ("adds to cart", "atc"),
    "ctr_7d": ("ctr 7d", "ctr last 7"),
    "ctr_prev7": ("ctr prev7", "ctr previous 7"),
    "status": ("status",),
}


class ColumnMapping(BaseModel):
    """Mapping between canonical metric names and actual dataset column headers."""

    campaign_name: Optional[str] = None
    ad_set_name: Optional[str] = None
    ad_name: Optional[str] = None
    ad_id: Optional[str] = None
    spend: Optional[str] = None
    impressions: Optional[str] = None
    clicks: Optional[str] = None
    ctr: Optional[str] = None
    frequency: Optional[str] = None
    roas: Optional[str] = None
    purchases: Optional[str] = None
    purchase_value: Optional[str] = None
    adds_to_cart: Optional[str] = None
    ctr_7d: Optional[str] = None
    ctr_prev7: Optional[str] = None
    status: Optional[str] = None

    def resolve(self, canonical: str) -> Optional[str]:
        """Return the mapped column for the given canonical name."""

        return getattr(self, canonical, None)

    def available_metrics(self) -> List[str]:
        return [name for name, value in self.model_dump().items() if value]


class Record(BaseModel):
    """Single marketing performance record."""

    values: Mapping[str, Any]

    def get(self, column: str, default: Any = None) -> Any:
        return self.values.get(column, default)


class Insight(BaseModel):
    """Actionable insight returned by the engine."""

    code: str
    label: str
    severity: Literal["info", "warning", "critical", "opportunity"] = "info"
    action: str
    rationale: str
    metrics: Dict[str, Any] = Field(default_factory=dict)


class InsightRequest(BaseModel):
    """Top-level request payload for the engine."""

    data: Sequence[Mapping[str, Any]]
    column_hints: Optional[Mapping[str, str]] = None
    metadata: Optional[Mapping[str, Any]] = None

    @model_validator(mode="after")
    def _ensure_data(self) -> "InsightRequest":
        if not self.data:
            raise ValueError("At least one row of data is required")
        return self


class InsightResponse(BaseModel):
    """Engine response."""

    column_mapping: ColumnMapping
    insights: List[Insight]
    diagnostics: Dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        return self.model_dump()
