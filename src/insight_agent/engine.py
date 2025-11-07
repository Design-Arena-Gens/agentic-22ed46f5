"""LangGraph orchestrator wiring for the InsightAgent engine."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, TypedDict

from langgraph.graph import END, StateGraph

from .agents import MetricCalculator, RuleBasedInsightAgent, SemanticColumnIdentifier
from .agents.metrics import MetricSummary
from .config import InsightAgentSettings, get_settings
from .llm import BaseLLMClient, build_llm_client
from .schemas import ColumnMapping, Insight, InsightRequest, InsightResponse


class EngineState(TypedDict, total=False):
    records: Iterable[Mapping[str, Any]]
    column_mapping: ColumnMapping
    summary: MetricSummary
    insights: Iterable[Insight]
    diagnostics: Dict[str, Any]


class InsightEngine:
    def __init__(
        self,
        *,
        settings: InsightAgentSettings | None = None,
        column_identifier: SemanticColumnIdentifier | None = None,
        metric_calculator: MetricCalculator | None = None,
        insight_agent: RuleBasedInsightAgent | None = None,
        llm_client: BaseLLMClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.column_identifier = column_identifier or SemanticColumnIdentifier()
        self.metric_calculator = metric_calculator or MetricCalculator()
        self.insight_agent = insight_agent or RuleBasedInsightAgent()
        self.llm_client = llm_client or build_llm_client(self.settings)
        self._app = self._build_graph()

    def _build_graph(self):
        graph: StateGraph[EngineState] = StateGraph(EngineState)
        graph.add_node("identify_columns", self._identify_columns)
        graph.add_node("calculate_metrics", self._calculate_metrics)
        graph.add_node("generate_insights", self._generate_insights)
        graph.add_node("compose_narrative", self._compose_narrative)

        graph.set_entry_point("identify_columns")
        graph.add_edge("identify_columns", "calculate_metrics")
        graph.add_edge("calculate_metrics", "generate_insights")
        graph.add_edge("generate_insights", "compose_narrative")
        graph.add_edge("compose_narrative", END)

        return graph.compile()

    def _identify_columns(self, state: EngineState) -> EngineState:
        records = list(state["records"])
        columns = records[0].keys()
        hints = state.get("diagnostics", {}).get("column_hints")
        mapping = self.column_identifier(columns, hints=hints)
        diagnostics = dict(state.get("diagnostics", {}))
        diagnostics["column_mapping_confidence"] = mapping.available_metrics()
        return {"records": records, "column_mapping": mapping, "diagnostics": diagnostics}

    def _calculate_metrics(self, state: EngineState) -> EngineState:
        summary = self.metric_calculator(state["records"], state["column_mapping"])
        diagnostics = dict(state.get("diagnostics", {}))
        diagnostics["aggregate_metrics"] = summary.aggregates
        return {"summary": summary, "diagnostics": diagnostics, "records": state["records"], "column_mapping": state["column_mapping"]}

    def _generate_insights(self, state: EngineState) -> EngineState:
        insights = self.insight_agent(state["summary"])
        diagnostics = dict(state.get("diagnostics", {}))
        diagnostics["insight_count"] = len(insights)
        return {
            "insights": insights,
            "summary": state["summary"],
            "column_mapping": state["column_mapping"],
            "diagnostics": diagnostics,
        }

    def _compose_narrative(self, state: EngineState) -> EngineState:
        diagnostics = dict(state.get("diagnostics", {}))
        prompt = self._build_prompt(state["insights"], diagnostics)
        diagnostics["narrative"] = self.llm_client.generate(prompt)
        return {
            "insights": state["insights"],
            "summary": state.get("summary"),
            "column_mapping": state["column_mapping"],
            "diagnostics": diagnostics,
        }

    def _build_prompt(self, insights: Iterable[Insight], diagnostics: Dict[str, Any]) -> str:
        insight_lines = []
        for insight in insights:
            insight_lines.append(
                f"- {insight.label}: {insight.action} (metrics: {insight.metrics})"
            )
        metric_summary = diagnostics.get("aggregate_metrics", {})
        prompt = "\n".join(
            [
                "You are the InsightAgent marketing strategist. Summarize insights for the growth team.",
                "Focus on actionable next steps and highlight crucial metrics.",
                "Key metrics:",
                str(metric_summary),
                "Insights:",
                *insight_lines,
            ]
        )
        return prompt

    def run(self, payload: InsightRequest | Dict[str, Any]) -> InsightResponse:
        request = payload if isinstance(payload, InsightRequest) else InsightRequest.model_validate(payload)
        state: EngineState = {
            "records": request.data,
            "diagnostics": {"column_hints": dict(request.column_hints or {})},
        }
        final_state: EngineState = self._app.invoke(state)
        return InsightResponse(
            column_mapping=final_state["column_mapping"],
            insights=list(final_state.get("insights", [])),
            diagnostics=final_state.get("diagnostics", {}),
        )
