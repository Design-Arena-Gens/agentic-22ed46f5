"""Rule-based insight generation agent."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from ..schemas import Insight
from .metrics import MetricSummary


@dataclass
class RuleContext:
    summary: MetricSummary


@dataclass
class Rule:
    code: str
    label: str

    def applies(self, ctx: RuleContext) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def build_insight(self, ctx: RuleContext) -> Insight:  # pragma: no cover - interface
        raise NotImplementedError


class _RoasOneToTwoRule(Rule):
    def __init__(self) -> None:
        super().__init__(code="roas_1_2", label="ROAS between 1 and 2")

    def applies(self, ctx: RuleContext) -> bool:
        roas = ctx.summary.aggregates.get("avg_roas")
        return roas is not None and 1.0 <= roas <= 2.0

    def build_insight(self, ctx: RuleContext) -> Insight:
        roas = ctx.summary.aggregates.get("avg_roas", 0.0)
        return Insight(
            code=self.code,
            label=self.label,
            severity="opportunity",
            action="Test 2–3 new hooks/thumbnails; rotate in new ad creative; cap frequency if over-performing",
            rationale="ROAS is in the modest 1–2 band, signalling room for incremental lift from creative testing and fatigue mitigation",
            metrics={"avg_roas": roas},
        )


class _HealthyCtrWeakConversionRule(Rule):
    def __init__(self) -> None:
        super().__init__(code="ctr_healthy_low_conversion", label="CTR healthy, conversion weak")

    def applies(self, ctx: RuleContext) -> bool:
        ctr = ctx.summary.aggregates.get("avg_ctr")
        atc_purchase = ctx.summary.aggregates.get("avg_atc_to_purchase")
        return bool(ctr and ctr >= 0.015 and (atc_purchase is None or atc_purchase < 0.2))

    def build_insight(self, ctx: RuleContext) -> Insight:
        return Insight(
            code=self.code,
            label=self.label,
            severity="warning",
            action="Audit landing and checkout flows; ensure offer-message match and remove friction",
            rationale="Traffic is engaged (strong CTR) but shoppers are not completing purchases after adding to cart",
            metrics={
                "avg_ctr": ctx.summary.aggregates.get("avg_ctr", 0.0),
                "avg_atc_to_purchase": ctx.summary.aggregates.get("avg_atc_to_purchase", 0.0),
            },
        )


class _HighFrequencyFatigueRule(Rule):
    def __init__(self) -> None:
        super().__init__(code="frequency_fatigue", label="High frequency risk")

    def applies(self, ctx: RuleContext) -> bool:
        frequency = ctx.summary.aggregates.get("avg_frequency")
        return bool(frequency and frequency >= 3.5)

    def build_insight(self, ctx: RuleContext) -> Insight:
        return Insight(
            code=self.code,
            label=self.label,
            severity="warning",
            action="Rotate fresh creative or expand audiences to lower frequency",
            rationale="Average frequency is high, indicating audience saturation and performance decay risk",
            metrics={"avg_frequency": ctx.summary.aggregates.get("avg_frequency", 0.0)},
        )


class _CtrDropRule(Rule):
    def __init__(self) -> None:
        super().__init__(code="ctr_drop_vs_prev7", label="CTR dropped vs previous 7 days")

    def applies(self, ctx: RuleContext) -> bool:
        delta = ctx.summary.aggregates.get("avg_ctr_delta")
        return bool(delta is not None and delta < -0.1)

    def build_insight(self, ctx: RuleContext) -> Insight:
        return Insight(
            code=self.code,
            label=self.label,
            severity="critical",
            action="Investigate creative fatigue and audience overlap; run rapid creative refresh",
            rationale="CTR declined more than 10% week-over-week, signalling creative engagement issues",
            metrics={"avg_ctr_delta": ctx.summary.aggregates.get("avg_ctr_delta", 0.0)},
        )


class _SpendZeroPurchasesRule(Rule):
    def __init__(self) -> None:
        super().__init__(code="spend_no_purchases", label="Spend with no purchases")

    def applies(self, ctx: RuleContext) -> bool:
        for row in ctx.summary.per_row:
            spend = row.get("spend")
            purchases = row.get("purchases")
            if spend and spend > 50 and (not purchases or purchases == 0):
                return True
        return False

    def build_insight(self, ctx: RuleContext) -> Insight:
        offenders = [
            {
                "spend": row.get("spend", 0.0),
                "purchases": row.get("purchases", 0.0),
                "campaign_name": row.get("campaign_name"),
                "ad_name": row.get("ad_name"),
            }
            for row in ctx.summary.per_row
            if row.get("spend") and row.get("spend") > 50 and (not row.get("purchases") or row.get("purchases") == 0)
        ]
        return Insight(
            code=self.code,
            label=self.label,
            severity="critical",
            action="Pause or fix underperforming ads with spend but zero purchases; audit funnel quickly",
            rationale="Detected ads spending meaningful budget without returning purchases",
            metrics={"offenders": offenders},
        )


class RuleBasedInsightAgent:
    def __init__(self, extra_rules: Iterable[Rule] | None = None) -> None:
        self.rules: List[Rule] = list(
            extra_rules or []
        ) + [
            _RoasOneToTwoRule(),
            _HealthyCtrWeakConversionRule(),
            _HighFrequencyFatigueRule(),
            _CtrDropRule(),
            _SpendZeroPurchasesRule(),
        ]

    def __call__(self, summary: MetricSummary) -> List[Insight]:
        ctx = RuleContext(summary=summary)
        insights: List[Insight] = []
        for rule in self.rules:
            if rule.applies(ctx):
                insights.append(rule.build_insight(ctx))
        return insights
