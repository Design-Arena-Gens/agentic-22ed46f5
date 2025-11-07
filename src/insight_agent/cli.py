"""Command line interface for the InsightAgent engine."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from . import InsightEngine, InsightRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run InsightAgent analysis against a JSON dataset")
    parser.add_argument("--input", type=Path, required=True, help="Path to JSON file containing an array of rows")
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8") as handle:
        payload: Any = json.load(handle)

    engine = InsightEngine()
    response = engine.run(payload)
    print(json.dumps(response.to_json(), indent=2))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
