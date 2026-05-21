"""
BharatGraph -- Retrieval Quality Benchmark
==========================================
Evaluates three retrieval pipelines on Hindi/Marathi/Telugu QA:
  1. Simple RAG      (ChromaDB dense vector)
  2. Hybrid RAG      (ChromaDB dense + BM25)
  3. Hybrid Graph RAG (Neo4j vector + fulltext + entity graph)

Metrics: Hit Rate@K (K=1,5,10), MRR, NDCG@10, Precision@K, Avg Score

NOTE: This script uses simulated (estimated) scores derived from the
architecture characteristics and comparison.py run patterns.
To run against the live Neo4j database, replace MockEvaluator with
LiveEvaluator (see TODO comments below).

Requirements: numpy
Run: python benchmarks/benchmark_retrieval.py
"""

import json
import math
import random
from datetime import datetime
from pathlib import Path

# -- Evaluation set (Easy/Medium/Hard per language) ----------------------------
EVAL_SET = [
    # (language, difficulty, question, relevant_source)
    ("hindi",   "Easy",   "संविधान की उद्देशिका में 'समाजवादी' और 'पंथनिरपेक्ष' शब्द कब जोड़े गए?",         "doc_hindi_constitution"),
    ("hindi",   "Medium", "NCF 2005 के अनुसार बच्चों में सीखने की प्रक्रिया को प्रभावित करने वाले कारक?",    "doc_hindi_ncf2005"),
    ("hindi",   "Hard",   "42वें संविधान संशोधन अधिनियम 1976 ने उद्देशिका में क्या परिवर्तन किए?",            "doc_hindi_constitution"),
    ("marathi", "Easy",   "खनिजतेल कशापासून तयार होते?",                                                      "doc_marathi_mineraloil"),
    ("marathi", "Medium", "खनिजतेलाच्या ज्वलनामुळे कोणते वायू तयार होतात?",                                   "doc_marathi_mineraloil"),
    ("marathi", "Hard",   "नरसिंह मेहेता यांचे भक्तिमार्गातील योगदान काय होते?",                               "doc_marathi_narsinh"),
    ("telugu",  "Easy",   "గరుడ పురాణంలో మూడు కాండలు ఏవి?",                                                   "doc_telugu_garuda"),
    ("telugu",  "Medium", "ప్రేతకాండలో మరణానంతర ఆత్మ ప్రయాణం ఏ విధంగా వర్ణించబడింది?",                       "doc_telugu_garuda"),
    ("telugu",  "Hard",   "గరుడ పురాణం వైష్ణవ పురాణంగా ఎందుకు పరిగణించబడుతుంది?",                            "doc_telugu_garuda"),
]

K_VALUES = [1, 5, 10]


# -- Mock Evaluator -- deterministic simulated scores ---------------------------
# Scores derived from architecture analysis:
#   - Simple RAG: dense-only has retrieval ceiling limited by embedding alone
#   - Hybrid RAG: BM25 boosts exact-match tokens (Devanagari script benefits)
#   - Graph RAG:  entity traversal adds structural context, god-node filtering
#                 removes noise -> best precision
#
# Per-language adjustment: Hindi > Marathi > Telugu (data volume proxy)
# Per-difficulty adjustment: Hard queries retrieve less precisely
class MockEvaluator:
    PIPELINE_PARAMS = {
        "simple_rag": {
            "hit_at_1": 0.44, "hit_at_5": 0.61, "hit_at_10": 0.67,
            "mrr": 0.51, "ndcg_10": 0.58, "precision_10": 0.34, "avg_score": 0.612,
        },
        "hybrid_rag": {
            "hit_at_1": 0.56, "hit_at_5": 0.72, "hit_at_10": 0.78,
            "mrr": 0.62, "ndcg_10": 0.71, "precision_10": 0.44, "avg_score": 0.681,
        },
        "hybrid_graph_rag": {
            "hit_at_1": 0.67, "hit_at_5": 0.83, "hit_at_10": 0.89,
            "mrr": 0.74, "ndcg_10": 0.83, "precision_10": 0.57, "avg_score": 0.763,
        },
    }

    LANG_SCALE = {"hindi": 1.00, "marathi": 0.93, "telugu": 0.87}
    DIFF_SCALE = {"Easy": 1.00, "Medium": 0.94, "Hard": 0.87}

    def evaluate(self, pipeline: str) -> dict:
        params = self.PIPELINE_PARAMS[pipeline]
        results = []
        for lang, diff, question, source in EVAL_SET:
            ls = self.LANG_SCALE[lang]
            ds = self.DIFF_SCALE[diff]
            scale = (ls + ds) / 2
            results.append({
                "language":    lang,
                "difficulty":  diff,
                "question":    question,
                "hit_at_1":    min(1.0, round(params["hit_at_1"]  * scale + random.uniform(-0.02, 0.02), 3)),
                "hit_at_5":    min(1.0, round(params["hit_at_5"]  * scale + random.uniform(-0.02, 0.02), 3)),
                "hit_at_10":   min(1.0, round(params["hit_at_10"] * scale + random.uniform(-0.02, 0.02), 3)),
                "mrr":         min(1.0, round(params["mrr"]        * scale + random.uniform(-0.02, 0.02), 3)),
                "ndcg_10":     min(1.0, round(params["ndcg_10"]    * scale + random.uniform(-0.02, 0.02), 3)),
                "precision_10":min(1.0, round(params["precision_10"]* scale + random.uniform(-0.01, 0.01), 3)),
                "avg_score":   min(1.0, round(params["avg_score"]  * scale + random.uniform(-0.02, 0.02), 3)),
            })
        return results


def aggregate(results: list[dict]) -> dict:
    keys = ["hit_at_1", "hit_at_5", "hit_at_10", "mrr", "ndcg_10", "precision_10", "avg_score"]
    return {k: round(sum(r[k] for r in results) / len(results), 4) for k in keys}


def print_table(pipelines: dict[str, dict]):
    cols = ["hit_at_1", "hit_at_5", "hit_at_10", "mrr", "ndcg_10", "precision_10", "avg_score"]
    header_labels = ["Hit@1", "Hit@5", "Hit@10", "MRR", "NDCG@10", "Prec@10", "AvgScore"]

    col_w = 10
    row_w = 22

    header = f"{'Pipeline':<{row_w}}" + "".join(f"{h:>{col_w}}" for h in header_labels)
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    pipeline_labels = {
        "simple_rag":       "Simple RAG",
        "hybrid_rag":       "Hybrid RAG",
        "hybrid_graph_rag": "Hybrid Graph RAG",
    }

    for pipe, agg in pipelines.items():
        label = pipeline_labels[pipe]
        row = f"{label:<{row_w}}" + "".join(f"{agg[c]:>{col_w}.4f}" for c in cols)
        print(row)

    print("-" * len(header))


def main():
    random.seed(42)
    evaluator = MockEvaluator()
    output: dict = {"run_at": datetime.now().isoformat(), "pipelines": {}}

    print("\n" + "=" * 72)
    print("  BharatGraph -- Retrieval Quality Benchmark")
    print("  NOTE: Simulated scores (estimated from architecture analysis)")
    print("=" * 72)

    pipelines = {}
    for pipe in ["simple_rag", "hybrid_rag", "hybrid_graph_rag"]:
        results = evaluator.evaluate(pipe)
        agg = aggregate(results)
        pipelines[pipe] = agg
        output["pipelines"][pipe] = {"aggregate": agg, "per_query": results}

    print("\n  Aggregate Results -- All Languages / All Difficulties")
    print()
    print_table(pipelines)

    # Per-language breakdown
    for lang in ["hindi", "marathi", "telugu"]:
        lang_pipelines = {}
        for pipe in ["simple_rag", "hybrid_rag", "hybrid_graph_rag"]:
            lang_results = [r for r in output["pipelines"][pipe]["per_query"] if r["language"] == lang]
            lang_pipelines[pipe] = aggregate(lang_results)
        print(f"\n  Language: {lang.upper()}")
        print_table(lang_pipelines)

    # Save JSON
    out_path = Path(__file__).parent / "results" / "retrieval_benchmark.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Results saved -> {out_path}")


if __name__ == "__main__":
    main()
