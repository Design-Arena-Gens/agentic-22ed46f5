from insight_agent import InsightEngine, InsightRequest


def test_engine_produces_rule_based_insights():
    engine = InsightEngine()

    data = [
        {
            "Campaign name": "Spring Drops",
            "Ad set name": "Women",
            "Ad name": "Creative A",
            "Ad ID": "123",
            "Spend": 150,
            "Impressions": 10000,
            "Clicks": 250,
            "CTR %": 2.5,
            "Frequency": 4.0,
            "ROAS": 1.5,
            "Purchases": 3,
            "Purchase value": 450,
            "Adds to cart": 20,
            "CTR 7d %": 2.6,
            "CTR prev7 %": 3.0,
            "Status (pause/fix/test/keep)": "keep",
        },
        {
            "Campaign name": "Spring Drops",
            "Ad set name": "Men",
            "Ad name": "Creative B",
            "Ad ID": "456",
            "Spend": 80,
            "Impressions": 4000,
            "Clicks": 80,
            "CTR %": 2.0,
            "Frequency": 3.2,
            "ROAS": 0.9,
            "Purchases": 0,
            "Purchase value": 0,
            "Adds to cart": 5,
            "CTR 7d %": 1.9,
            "CTR prev7 %": 2.5,
            "Status (pause/fix/test/keep)": "fix",
        },
    ]

    request = InsightRequest(data=data)
    response = engine.run(request)

    assert response.column_mapping.campaign_name == "Campaign name"
    assert response.insights, "Expected at least one insight"
    codes = {insight.code for insight in response.insights}
    assert "roas_1_2" in codes
    assert "ctr_healthy_low_conversion" in codes
    assert "narrative" in response.diagnostics
    assert response.diagnostics["insight_count"] == len(response.insights)
