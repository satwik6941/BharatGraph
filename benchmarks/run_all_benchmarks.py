"""
BharatGraph -- Run All Benchmarks
=================================
Runs all three benchmarks and writes a combined JSON report.

Run: python benchmarks/run_all_benchmarks.py
"""

import json
import sys
import importlib.util
from datetime import datetime
from pathlib import Path

BENCHMARKS_DIR = Path(__file__).parent


def load_and_run(script_name: str) -> dict:
    """Import and run a benchmark module's main(), return its results JSON."""
    path = BENCHMARKS_DIR / script_name
    spec = importlib.util.spec_from_file_location(script_name[:-3], path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "main"):
        mod.main()

    # Load saved JSON result
    result_name = script_name.replace("benchmark_", "").replace(".py", "_benchmark.json")
    result_path = BENCHMARKS_DIR / "results" / result_name
    if result_path.exists():
        with open(result_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    print("\n" + "#" * 72)
    print("  BharatGraph -- Complete Benchmark Suite")
    print("#" * 72)

    combined = {"run_at": datetime.now().isoformat(), "benchmarks": {}}

    benchmarks = [
        ("benchmark_retrieval.py",    "retrieval"),
        ("benchmark_answer_quality.py", "answer_quality"),
        ("benchmark_multilingual.py",  "multilingual"),
    ]

    for script, key in benchmarks:
        print(f"\n{'>' * 3}  Running {script} ...")
        print("-" * 72)
        try:
            result = load_and_run(script)
            combined["benchmarks"][key] = result
        except Exception as exc:
            print(f"  [ERROR] {exc}")
            combined["benchmarks"][key] = {"error": str(exc)}

    out_path = BENCHMARKS_DIR / "results" / "combined_benchmark_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print("\n" + "#" * 72)
    print(f"  All benchmarks complete.  Combined report -> {out_path}")
    print("#" * 72)


if __name__ == "__main__":
    main()
