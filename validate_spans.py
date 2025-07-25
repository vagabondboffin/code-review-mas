import json
import pandas as pd
from collections import defaultdict


def analyze_coverage(results_file):
    """Analyze span coverage across tasks"""
    coverage_stats = defaultdict(lambda: {
        "total": 0,
        "present": 0
    })

    with open(results_file) as f:
        for line in f:
            task = json.loads(line)
            for span_type in task["span_coverage"]:
                coverage_stats[span_type]["total"] += 1
                if task["span_coverage"][span_type]:
                    coverage_stats[span_type]["present"] += 1

    # Calculate coverage rates
    report = []
    for span_type, stats in coverage_stats.items():
        coverage_rate = stats["present"] / stats["total"]
        report.append({
            "Span Type": span_type,
            "Coverage Rate": f"{coverage_rate:.1%}",
            "Present": stats["present"],
            "Total": stats["total"]
        })

    return pd.DataFrame(report)


if __name__ == "__main__":
    # Usage: python validate_spans.py results/full_results.jsonl
    import sys

    if len(sys.argv) != 2:
        print("Usage: python validate_spans.py <results_file.jsonl>")
        sys.exit(1)

    df = analyze_coverage(sys.argv[1])
    print("\nSPAN COVERAGE REPORT")
    print("=" * 50)
    print(df)