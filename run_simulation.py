from model import CodeReviewModel
from llm.task_generator import TaskGenerator
import pandas as pd
from tracing.setup_tracer import tracer
import time
import random
import json
import os
from datetime import datetime
import logging
from opentelemetry import trace
import numpy as np

from analysis.failure_metrics import run_metrics_analysis


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_float32(obj):
    """Recursively convert float32 to Python float for JSON serialization"""
    if isinstance(obj, np.float32):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_float32(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_float32(elem) for elem in obj]
    else:
        return obj


def main():
    # Initialize Jaeger tracer
    tracer = trace.get_tracer_provider().get_tracer(__name__)

    # Initialize model with multiple failure modes
    enable_failure_injection = True
    derailment_probability = 0.3  # 30% chance of task derailment

    model = CodeReviewModel(
        num_coders=2,
        num_reviewers=1,
        num_planners=1,
        enable_feedback_loop=enable_failure_injection,
        derailment_probability=derailment_probability
    )

    task_gen = TaskGenerator()

    # Create results directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"results/stress_test_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)

    # Generate tasks using LLM
    num_tasks = 10
    tasks = []
    print(f"🔧 Generating {num_tasks} tasks with LLM...")
    print(f"⚡ Failure Injection: {enable_failure_injection}")
    print(f"⚡ Ignore Feedback Probability: 0%")
    print(f"⚡ Task Derailment Probability: {derailment_probability * 100}%")

    # Create parent span for entire simulation
    with tracer.start_as_current_span("FullSimulation") as sim_span:
        sim_span.set_attribute("task_count", num_tasks)
        sim_span.set_attribute("jaeger.export", True)
        sim_span.set_attribute("failure_injection.enabled", enable_failure_injection)
        sim_span.set_attribute("failure_injection.types", "ignored_feedback,task_derailment")
        sim_span.set_attribute("failure_injection.ignore_feedback_probability", 0.3)
        sim_span.set_attribute("failure_injection.derailment_probability", derailment_probability)

        # Generate tasks in batches
        for i in range(num_tasks):
            with tracer.start_as_current_span("TaskGeneration") as span:
                task = task_gen.generate_task(temperature=0.8)
                tasks.append(task)
                span.set_attribute("task.content", task)
                if (i + 1) % 10 == 0:
                    print(f"  Generated task {i + 1}/{num_tasks}")
                time.sleep(0.5)

        # Save generated tasks
        with open(f"{results_dir}/tasks.json", "w") as f:
            json.dump(tasks, f)

        # Run simulation
        print(f"\n🚀 Starting simulation with {len(tasks)} tasks...")
        full_results = []
        start_time = time.time()

        for i, task in enumerate(tasks):
            print(f"\n{'=' * 60}")
            print(f"🔍 PROCESSING TASK {i + 1}/{len(tasks)}")
            print(f"{'=' * 60}")

            with tracer.start_as_current_span(f"MainTask.{i + 1}") as task_span:
                task_span.set_attribute("task.description", task)
                task_span.set_attribute("failure_injection.enabled", enable_failure_injection)

                task_result = model.run_task(task)
                full_results.append(task_result)

        # Generate reports
        print("\n📊 SIMULATION COMPLETE! GENERATING REPORTS...")
        generate_reports(full_results, results_dir, enable_failure_injection, derailment_probability)
        generate_enhanced_reports(full_results, results_dir, enable_failure_injection, derailment_probability)

        # Performance metrics
        duration = time.time() - start_time
        sim_span.set_attribute("simulation.duration", duration)
        print(f"\n⏱️  STRESS TEST COMPLETED IN {duration:.2f} SECONDS")
        print(f"⏱️  AVERAGE TIME PER TASK: {duration / num_tasks:.2f} SECONDS")


def generate_reports(full_results, results_dir, failure_injection_enabled, derailment_probability):
    # Main task report (CSV)
    main_report = []
    total_feedback_failures = 0
    total_derailments = 0

    for i, task_result in enumerate(full_results):
        feedback_failures = task_result.get('feedback_loop_failures', 0)
        derailments = task_result.get('derailment_count', 0)
        total_feedback_failures += feedback_failures
        total_derailments += derailments

        main_report.append({
            "task_id": i + 1,
            "task": task_result['task'],
            "original_task": task_result['original_task'],
            "subtask_count": len(task_result['workflow']),
            "avg_similarity": task_result['similarity'],
            "errors": task_result['errors'],
            "error_sources": ", ".join(task_result['error_sources']),
            "feedback_loop_failures": feedback_failures,
            "derailment_count": derailments,
            "success_rate": sum(1 for r in task_result['subtask_results'] if r['result'] == "Approved") /
                            len(task_result['subtask_results'])
        })

    df_main = pd.DataFrame(main_report)
    df_main.to_csv(f"{results_dir}/main_task_metrics.csv", index=False)

    # Subtask-level report (CSV)
    subtask_report = []
    ignored_feedback_count = 0
    derailed_subtasks = 0

    for i, task_result in enumerate(full_results):
        for j, subtask_result in enumerate(task_result['subtask_results']):
            subtask_report.append({
                "main_task_id": i + 1,
                "subtask_id": j + 1,
                "assigned_subtask": subtask_result['subtask'],
                "actual_task": subtask_result['actual_task'],
                "was_derailed": subtask_result['was_derailed'],
                "result": subtask_result['result'],
                "intended_similarity": subtask_result.get('intended_similarity', 0),
                "actual_similarity": subtask_result.get('actual_similarity', 0),
                "similarity_gap": subtask_result.get('intended_similarity', 0) - subtask_result.get('actual_similarity',
                                                                                                    0),
                "had_feedback_loop": subtask_result.get('had_feedback_loop', False),
                "code_snippet": subtask_result['code'][:100] + ('...' if len(subtask_result['code']) > 100 else '')
            })

            # Count ignored feedback instances
            if subtask_result.get('had_feedback_loop', False) and subtask_result['result'] == "Rejected":
                ignored_feedback_count += 1

            # Count derailed subtasks
            if subtask_result.get('was_derailed', False):
                derailed_subtasks += 1

    df_subtasks = pd.DataFrame(subtask_report)
    df_subtasks.to_csv(f"{results_dir}/subtask_metrics.csv", index=False)

    # Full results in JSONL format (with float conversion)
    with open(f"{results_dir}/full_results.jsonl", "w") as f:
        for result in full_results:
            # Convert float32 to standard float
            converted_result = convert_float32(result)
            f.write(json.dumps(converted_result) + "\n")

    # Validation report
    validation_results = validate_span_coverage(full_results)
    with open(f"{results_dir}/validation_report.txt", "w") as f:
        f.write("SPAN COVERAGE VALIDATION REPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Tasks Processed: {len(full_results)}\n")
        f.write(f"Tasks With Complete Coverage: {validation_results['complete_coverage']}/{len(full_results)}\n")
        f.write(f"Coverage Success Rate: {validation_results['coverage_rate']:.1%}\n")
        f.write(f"Failure Injection Enabled: {failure_injection_enabled}\n")
        f.write(f"Derailment Probability: {derailment_probability}\n")
        f.write(f"Total Feedback Loop Failures: {total_feedback_failures}\n")
        f.write(f"Total Task Derailments: {total_derailments}\n")
        f.write(f"Ignored Feedback Instances: {ignored_feedback_count}\n")
        f.write(f"Derailed Subtasks: {derailed_subtasks}\n\n")
        f.write("COMMON MISSING SPANS:\n")
        for span_type, count in validation_results['missing_spans'].most_common(5):
            f.write(f"- {span_type}: {count} occurrences\n")

    # Failure injection analysis
    with open(f"{results_dir}/failure_analysis.txt", "w") as f:
        f.write("FAILURE INJECTION ANALYSIS\n")
        f.write("=" * 50 + "\n")
        f.write(f"Failure Types: Ignored Reviewer Input + Task Derailment\n")
        f.write(f"Ignore Feedback Probability: 0%\n")
        f.write(f"Task Derailment Probability: {derailment_probability}\n")
        f.write(f"Total Tasks: {len(full_results)}\n")
        f.write(f"Total Subtasks: {len(df_subtasks)}\n")
        f.write(f"Feedback Loop Activations: {len(df_subtasks[df_subtasks['had_feedback_loop'] == True])}\n")
        f.write(f"Ignored Feedback Count: {ignored_feedback_count}\n")
        f.write(
            f"Ignore Rate: {ignored_feedback_count / max(1, len(df_subtasks[df_subtasks['had_feedback_loop'] == True])):.1%}\n")
        f.write(f"Derailed Subtasks: {derailed_subtasks}\n")
        f.write(f"Derailment Rate: {derailed_subtasks / len(df_subtasks):.1%}\n\n")

        if ignored_feedback_count > 0 or derailed_subtasks > 0:
            f.write("IMPACT ANALYSIS:\n")

            # Analyze derailment impact
            derailed_tasks = df_subtasks[df_subtasks['was_derailed'] == True]
            if len(derailed_tasks) > 0:
                avg_similarity_derailed = derailed_tasks['intended_similarity'].mean()
                avg_similarity_normal = df_subtasks[df_subtasks['was_derailed'] == False]['intended_similarity'].mean()
                f.write(f"Average Similarity (Derailed): {avg_similarity_derailed:.2f}\n")
                f.write(f"Average Similarity (Normal): {avg_similarity_normal:.2f}\n")
                f.write(f"Derailment Quality Impact: {avg_similarity_normal - avg_similarity_derailed:.2f} points\n\n")

            # Analyze combined failure impact
            failed_subtasks = df_subtasks[
                ((df_subtasks['had_feedback_loop'] == True) & (df_subtasks['result'] == 'Rejected')) |
                (df_subtasks['was_derailed'] == True)
                ]
            if len(failed_subtasks) > 0:
                avg_similarity_failed = failed_subtasks['intended_similarity'].mean()
                avg_similarity_all = df_subtasks['intended_similarity'].mean()
                f.write(f"Average Similarity (All Failed): {avg_similarity_failed:.2f}\n")
                f.write(f"Average Similarity (All Tasks): {avg_similarity_all:.2f}\n")
                f.write(f"Combined Failure Impact: {avg_similarity_all - avg_similarity_failed:.2f} points\n")

    # Jaeger visualization guide
    with open(f"{results_dir}/jaeger_guide.txt", "w") as f:
        f.write("JAEGER TRACE VISUALIZATION GUIDE\n")
        f.write("=" * 50 + "\n")
        f.write("1. Start Jaeger: docker run -d --name jaeger \\\n")
        f.write("   -e COLLECTOR_OTLP_ENABLED=true \\\n")
        f.write("   -p 16686:16686 -p 4317:4317 \\\n")
        f.write("   jaegertracing/all-in-one:latest\n\n")
        f.write("2. Access Jaeger UI: http://localhost:16686\n\n")
        f.write("3. Search parameters:\n")
        f.write("   - Service: code-review-mas\n")
        f.write("   - Operation: FullSimulation\n")
        f.write("   - Tags: failure.task_derailment OR failure.ignored_feedback\n\n")
        f.write("4. NEW DERAILMENT TRACES TO LOOK FOR:\n")
        f.write("   - failure.task_derailment: true attributes\n")
        f.write("   - task.assigned vs task.actual differences\n")
        f.write("   - subtask.intended_similarity vs subtask.actual_similarity gaps\n")
        f.write("   - derailment.type: domain_shift|meta_task|related_but_wrong\n\n")
        f.write("5. Trace hierarchy with derailment:\n")
        f.write("   MainTask.X\n")
        f.write("   ├── Model.run_task\n")
        f.write("   │   ├── Planner.create_workflow\n")
        f.write("   │   ├── Subtask.1\n")
        f.write("   │   │   ├── CoderAgent.step → Works on assigned task ✅\n")
        f.write("   │   │   └── ReviewerAgent.step\n")
        f.write("   │   ├── Subtask.2 🚨\n")
        f.write("   │   │   ├── failure.task_derailment: true\n")
        f.write("   │   │   ├── task.assigned: 'Implement API'\n")
        f.write("   │   │   ├── task.actual: 'Add payment processing'\n")
        f.write("   │   │   ├── CoderAgent.step → Works on wrong task!\n")
        f.write("   │   │   └── ReviewerAgent.step\n")
        f.write("   │   └── Subtask.3\n")
        f.write("   └── MainTask.X (completed with derailments)\n\n")
        f.write("6. Troubleshooting:\n")
        f.write("   - No traces? Check Docker: docker logs jaeger\n")
        f.write("   - Connection issues? Verify OTLP exporter config\n")

    print(f"\n💾 All reports saved to: {results_dir}")
    print(f"🚨 Failure Injection Analysis:")
    print(f"   - Feedback loop failures: {total_feedback_failures}")
    print(f"   - Ignored feedback instances: {ignored_feedback_count}")
    print(f"   - Task derailments: {total_derailments}")
    print(f"   - Derailed subtasks: {derailed_subtasks}")
    print("📘 Jaeger guide available in jaeger_guide.txt")


def validate_span_coverage(full_results):
    from collections import Counter
    validation = {
        "complete_coverage": 0,
        "missing_spans": Counter(),
        "coverage_rate": 0
    }

    required_spans = [
        "Model.run_task",
        "Planner.create_workflow",
        "CoderAgent.step",
        "ReviewerAgent.step"
    ]

    for result in full_results:
        missing = []
        for span in required_spans:
            if not any(span in source for source in result['error_sources']):
                if span == "Planner.create_workflow" and len(result['workflow']) == 0:
                    missing.append(span)
                elif span not in ["Planner.create_workflow"]:
                    missing.append(span)

        if not missing:
            validation["complete_coverage"] += 1
        else:
            for span in missing:
                validation["missing_spans"][span] += 1

    validation["coverage_rate"] = validation["complete_coverage"] / len(full_results)
    return validation


def generate_enhanced_reports(full_results, results_dir, enable_failure_injection, derailment_probability):
    # ... your existing report generation code ...

    # NEW: Run comprehensive failure metrics analysis
    if enable_failure_injection:
        print("\n📊 RUNNING ADVANCED FAILURE METRICS ANALYSIS...")
        results_file = f"{results_dir}/full_results.jsonl"
        metrics_report = run_metrics_analysis(results_file, results_dir)

        # Add metrics to validation report
        with open(f"{results_dir}/validation_report.txt", "a") as f:
            f.write("\nADVANCED FAILURE METRICS:\n")
            f.write("=" * 30 + "\n")
            f.write(f"Failure Detection Rate: {metrics_report['failure_detection']['detection_rate']:.1%}\n")
            f.write(
                f"Derailment Impact: {metrics_report['impact_magnitude']['derailment_drop_pct']:.1f}% quality drop\n")
            f.write(f"Feedback Impact: {metrics_report['impact_magnitude']['feedback_drop_pct']:.1f}% quality drop\n")
            f.write(f"Reviewer Blindspot Rate: {metrics_report['reviewer_blindspots']['blindspot_rate']:.1%}\n")
            f.write(f"Avg Propagation: {metrics_report['propagation_distance']['avg_affected_steps']:.1f} steps\n")

if __name__ == "__main__":
    main()