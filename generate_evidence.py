#!/usr/bin/env python3
"""
Quick script to generate all visual evidence for presentation
"""
import os
import subprocess
import sys
from datetime import datetime


def main():
    # Create evidence directory
    evidence_dir = f"presentation_evidence_{datetime.now().strftime('%Y%m%d_%H%M')}"
    os.makedirs(evidence_dir, exist_ok=True)

    print("🎯 GENERATING PRESENTATION EVIDENCE...")

    # 1. Run a quick simulation to get fresh data
    print("1. Running quick simulation...")
    subprocess.run([sys.executable, "run_simulation.py"], check=True)

    # Find the latest results
    results_dirs = [d for d in os.listdir("results") if d.startswith("stress_test")]
    if not results_dirs:
        print("❌ No results found. Please run simulation first.")
        return

    latest_dir = sorted(results_dirs)[-1]
    results_file = f"results/{latest_dir}/full_results.jsonl"

    # 2. Generate metrics and charts
    print("2. Generating metrics and charts...")
    from analysis.failure_metrics import run_metrics_analysis
    metrics_report = run_metrics_analysis(results_file, evidence_dir)

    # 3. Generate workflow diagram
    print("3. Generating workflow diagram...")
    from analysis.workflow_visualizer import create_workflow_diagram
    create_workflow_diagram(f"{evidence_dir}/workflow_diagram.png")

    # 4. Create summary report
    print("4. Creating summary report...")
    with open(f"{evidence_dir}/evidence_summary.txt", "w") as f:
        f.write("PRESENTATION EVIDENCE SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        f.write("Generated visual evidence includes:\n")
        f.write("✅ impact_comparison.png - Quantitative failure impact\n")
        f.write("✅ failure_distribution.png - Failure type breakdown\n")
        f.write("✅ propagation_analysis.png - Failure cascade effects\n")
        f.write("✅ workflow_diagram.png - System architecture with hotspots\n")
        f.write("✅ detailed_metrics_report.txt - Complete numerical analysis\n\n")

        f.write("KEY FINDINGS:\n")
        f.write(f"- Failure Detection Rate: {metrics_report['failure_detection']['detection_rate']:.1%}\n")
        f.write(f"- Derailment Quality Impact: {metrics_report['impact_magnitude']['derailment_drop_pct']:.1f}%\n")
        f.write(f"- Reviewer Blindspots: {metrics_report['reviewer_blindspots']['blindspot_rate']:.1%}\n")
        f.write(f"- Average Propagation: {metrics_report['propagation_distance']['avg_affected_steps']:.1f} steps\n")

    print(f"✅ Evidence generated in: {evidence_dir}")
    print("📊 Your presentation now has concrete, data-driven evidence!")


if __name__ == "__main__":
    main()