import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import numpy as np


class FailureMetricsAnalyzer:
    def __init__(self, results_file):
        self.results_file = results_file
        self.df = self._load_data()

    def _load_data(self):
        """Load and process the JSONL results"""
        records = []
        with open(self.results_file) as f:
            for line in f:
                task = json.loads(line)
                for i, subtask in enumerate(task['subtask_results']):
                    records.append({
                        'task_id': task.get('task_id', len(records)),
                        'main_task': task['task'],
                        'subtask_id': i + 1,
                        'assigned_subtask': subtask['subtask'],
                        'actual_task': subtask.get('actual_task', subtask['subtask']),
                        'was_derailed': subtask.get('was_derailed', False),
                        'had_feedback_loop': subtask.get('had_feedback_loop', False),
                        'result': subtask['result'],
                        'intended_similarity': subtask.get('intended_similarity', 0),
                        'actual_similarity': subtask.get('actual_similarity', 0),
                        'similarity_gap': subtask.get('intended_similarity', 0) - subtask.get('actual_similarity', 0),
                        'errors': len(task.get('error_sources', [])),
                        'error_sources': task.get('error_sources', []),
                        'code': subtask['code']
                    })
        return pd.DataFrame(records)

    def calculate_failure_detection_rate(self):
        """Calculate what percentage of injected failures appear in traces"""
        total_injected = len(self.df[
                                 (self.df['was_derailed']) |
                                 (self.df['had_feedback_loop'] & (self.df['result'] == 'Rejected'))
                                 ])

        detected_in_traces = len(self.df[
                                     ((self.df['was_derailed']) & (self.df['similarity_gap'] > 0.3)) |
                                     ((self.df['had_feedback_loop']) & (self.df['result'] == 'Rejected') & (
                                                 self.df['intended_similarity'] < 0.5))
                                     ])

        detection_rate = detected_in_traces / total_injected if total_injected > 0 else 0
        return {
            'detection_rate': detection_rate,
            'total_injected': total_injected,
            'detected': detected_in_traces
        }

    def calculate_impact_magnitude(self):
        """Calculate average similarity score drop per failure type"""
        baseline = self.df[
            (~self.df['was_derailed']) &
            (~self.df['had_feedback_loop'])
            ]['intended_similarity'].mean()

        derailment_impact = baseline - self.df[
            self.df['was_derailed']
        ]['intended_similarity'].mean()

        feedback_impact = baseline - self.df[
            self.df['had_feedback_loop'] & (self.df['result'] == 'Rejected')
            ]['intended_similarity'].mean()

        return {
            'baseline_similarity': baseline,
            'derailment_impact': derailment_impact,
            'feedback_impact': feedback_impact,
            'derailment_drop_pct': (derailment_impact / baseline) * 100,
            'feedback_drop_pct': (feedback_impact / baseline) * 100
        }

    def calculate_propagation_distance(self):
        """Calculate how many workflow steps are affected by failures"""
        propagation_data = []

        for task_id in self.df['task_id'].unique():
            task_data = self.df[self.df['task_id'] == task_id].sort_values('subtask_id')
            failures = task_data[
                task_data['was_derailed'] | (task_data['had_feedback_loop'] & (task_data['result'] == 'Rejected'))]

            if len(failures) > 0:
                first_failure_idx = failures['subtask_id'].min()
                affected_subtasks = len(task_data[task_data['subtask_id'] >= first_failure_idx])
                propagation_data.append({
                    'task_id': task_id,
                    'affected_steps': affected_subtasks,
                    'total_steps': len(task_data),
                    'propagation_ratio': affected_subtasks / len(task_data)
                })

        if propagation_data:
            propagation_df = pd.DataFrame(propagation_data)
            return {
                'avg_affected_steps': propagation_df['affected_steps'].mean(),
                'avg_propagation_ratio': propagation_df['propagation_ratio'].mean(),
                'max_affected_steps': propagation_df['affected_steps'].max()
            }
        return {'avg_affected_steps': 0, 'avg_propagation_ratio': 0, 'max_affected_steps': 0}

    def calculate_reviewer_blindspots(self):
        """Calculate % of derailed tasks that still get approved"""
        derailed_tasks = self.df[self.df['was_derailed']]
        total_derailed = len(derailed_tasks)

        if total_derailed > 0:
            approved_derailed = len(derailed_tasks[derailed_tasks['result'] == 'Approved'])
            blindspot_rate = approved_derailed / total_derailed

            # Calculate the quality of approved derailed tasks
            approved_derailed_quality = derailed_tasks[
                derailed_tasks['result'] == 'Approved'
                ]['intended_similarity'].mean()

            return {
                'blindspot_rate': blindspot_rate,
                'approved_derailed_count': approved_derailed,
                'total_derailed': total_derailed,
                'approved_derailed_quality': approved_derailed_quality
            }
        return {'blindspot_rate': 0, 'approved_derailed_count': 0, 'total_derailed': 0, 'approved_derailed_quality': 0}

    def generate_comprehensive_report(self):
        """Generate all metrics in one report"""
        return {
            'failure_detection': self.calculate_failure_detection_rate(),
            'impact_magnitude': self.calculate_impact_magnitude(),
            'propagation_distance': self.calculate_propagation_distance(),
            'reviewer_blindspots': self.calculate_reviewer_blindspots()
        }


def run_metrics_analysis(results_file, output_dir):
    """Run complete metrics analysis and generate visualizations"""
    analyzer = FailureMetricsAnalyzer(results_file)
    report = analyzer.generate_comprehensive_report()

    # Print comprehensive report
    print("🚀 COMPREHENSIVE FAILURE METRICS ANALYSIS")
    print("=" * 60)

    # Failure Detection
    det = report['failure_detection']
    print(f"\n🔍 FAILURE DETECTION RATE: {det['detection_rate']:.1%}")
    print(f"   Total injected failures: {det['total_injected']}")
    print(f"   Detected in traces: {det['detected']}")

    # Impact Magnitude
    impact = report['impact_magnitude']
    print(f"\n📉 IMPACT MAGNITUDE:")
    print(f"   Baseline similarity: {impact['baseline_similarity']:.2f}")
    print(f"   Derailment impact: -{impact['derailment_impact']:.2f} ({impact['derailment_drop_pct']:.1f}%)")
    print(f"   Feedback failure impact: -{impact['feedback_impact']:.2f} ({impact['feedback_drop_pct']:.1f}%)")

    # Propagation
    prop = report['propagation_distance']
    print(f"\n🔄 PROPAGATION DISTANCE:")
    print(f"   Avg affected steps: {prop['avg_affected_steps']:.1f}")
    print(f"   Propagation ratio: {prop['avg_propagation_ratio']:.1%}")
    print(f"   Max cascade: {prop['max_affected_steps']} steps")

    # Blindspots
    blind = report['reviewer_blindspots']
    print(f"\n🙈 REVIEWER BLINDSPOTS:")
    print(f"   Derailed but approved: {blind['blindspot_rate']:.1%}")
    print(f"   Approved derailed quality: {blind['approved_derailed_quality']:.2f}")

    # Generate visualizations
    generate_visualizations(analyzer, output_dir, report)

    return report


def generate_visualizations(analyzer, output_dir, report):
    """Generate all visualizations"""
    # Set style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")

    # 1. Impact Comparison Bar Chart
    plt.figure(figsize=(10, 6))
    impact_data = [
        report['impact_magnitude']['baseline_similarity'],
        report['impact_magnitude']['baseline_similarity'] - report['impact_magnitude']['derailment_impact'],
        report['impact_magnitude']['baseline_similarity'] - report['impact_magnitude']['feedback_impact']
    ]
    labels = ['Baseline', 'After Derailment', 'After Feedback Failures']
    colors = ['#2ecc71', '#e74c3c', '#f39c12']

    bars = plt.bar(labels, impact_data, color=colors, alpha=0.8)
    plt.title('Impact of Failure Modes on Output Quality', fontsize=14, fontweight='bold')
    plt.ylabel('Similarity Score', fontweight='bold')
    plt.ylim(0, 1)

    # Add value labels on bars
    for bar, value in zip(bars, impact_data):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                 f'{value:.2f}', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(f'{output_dir}/impact_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 2. Failure Distribution Pie Chart
    plt.figure(figsize=(8, 8))
    failure_types = ['Derailment', 'Feedback Failures', 'Successful']
    failure_counts = [
        len(analyzer.df[analyzer.df['was_derailed']]),
        len(analyzer.df[analyzer.df['had_feedback_loop'] & (analyzer.df['result'] == 'Rejected')]),
        len(analyzer.df[~(analyzer.df['was_derailed']) & ~(
                    analyzer.df['had_feedback_loop'] & (analyzer.df['result'] == 'Rejected'))])
    ]

    plt.pie(failure_counts, labels=failure_types, autopct='%1.1f%%', startangle=90)
    plt.title('Distribution of Failure Types', fontsize=14, fontweight='bold')
    plt.savefig(f'{output_dir}/failure_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 3. Propagation Analysis
    plt.figure(figsize=(10, 6))

    # Calculate propagation by task
    propagation_data = []
    for task_id in analyzer.df['task_id'].unique():
        task_data = analyzer.df[analyzer.df['task_id'] == task_id].sort_values('subtask_id')
        if len(task_data[task_data['was_derailed']]) > 0:
            first_failure = task_data[task_data['was_derailed']]['subtask_id'].min()
            propagation_data.append({
                'task_id': task_id,
                'first_failure_step': first_failure,
                'total_steps': len(task_data)
            })

    if propagation_data:
        prop_df = pd.DataFrame(propagation_data)
        plt.scatter(prop_df['first_failure_step'], prop_df['total_steps'], alpha=0.6, s=100)
        plt.xlabel('First Failure Step', fontweight='bold')
        plt.ylabel('Total Steps in Task', fontweight='bold')
        plt.title('Failure Propagation: Early Failures Affect More Steps', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/propagation_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python failure_metrics.py <results_file.jsonl> <output_dir>")
        sys.exit(1)

    results_file = sys.argv[1]
    output_dir = sys.argv[2]

    report = run_metrics_analysis(results_file, output_dir)

    # Save detailed report
    with open(f'{output_dir}/detailed_metrics_report.txt', 'w') as f:
        f.write("DETAILED FAILURE METRICS REPORT\n")
        f.write("=" * 50 + "\n\n")
        for category, data in report.items():
            f.write(f"{category.upper()}:\n")
            for key, value in data.items():
                if isinstance(value, float):
                    f.write(f"  {key}: {value:.3f}\n")
                else:
                    f.write(f"  {key}: {value}\n")
            f.write("\n")