import argparse
import pandas as pd
import os
from datetime import datetime
from .trace_parser import load_trace_data, compute_agent_interactions
from .visualizations import (
    plot_misalignment_clusters,
    plot_error_propagation,
    plot_agent_sankey,
    plot_agent_network
)


def main():
    parser = argparse.ArgumentParser(description="Run MAST-style analysis on trace data")
    parser.add_argument("input_file", help="Path to full_results.jsonl file")
    args = parser.parse_args()

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"results/mast_analysis_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"🔍 Loading trace data from {args.input_file}")
    df = load_trace_data(args.input_file)

    print("📊 Computing MAST metrics...")
    metrics = compute_agent_interactions(df)

    # Save processed data
    df.to_csv(f"{output_dir}/processed_trace_data.csv", index=False)
    metrics['role_errors'].to_csv(f"{output_dir}/role_error_metrics.csv")
    metrics['misalignment_clusters'].to_csv(f"{output_dir}/misalignment_clusters.csv")
    metrics['error_propagation'].to_csv(f"{output_dir}/error_propagation.csv")

    print("🎨 Generating visualizations...")
    plot_misalignment_clusters(df, output_dir)
    plot_error_propagation(metrics['role_errors'], output_dir)
    plot_agent_sankey(df, output_dir)
    plot_agent_network(df, output_dir)

    # Generate summary report
    with open(f"{output_dir}/analysis_summary.txt", "w") as f:
        f.write("MAST-STYLE ANALYSIS SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Tasks Analyzed: {df['task_id'].nunique()}\n")
        f.write(f"Subtasks Analyzed: {len(df)}\n\n")
        f.write("Key Metrics:\n")
        f.write(f"- Average Misalignment Score: {df['subtask_misalignment'].mean():.2f}\n")
        f.write(f"- Overall Error Rate: {df['is_error'].mean():.2f}\n")
        f.write(
            f"- Critical Misalignment Rate: {metrics['misalignment_clusters'].get('Critical', 0) / len(df):.2f}\n\n")
        f.write("Visualizations Generated:\n")
        f.write("- misalignment_clusters.png: Distribution of misalignment severity\n")
        f.write("- error_rates.png: Error rates by agent role\n")
        f.write("- agent_sankey.html: Interactive workflow diagram\n")
        f.write("- agent_network.png: Agent interaction network\n")

    print(f"✅ Analysis complete! Results saved to {output_dir}")


if __name__ == "__main__":
    main()