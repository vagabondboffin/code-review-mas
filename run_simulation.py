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

    # Initialize model with feedback loop enabled for failure injection
    enable_failure_injection = True  # Set to False for baseline comparison
    model = CodeReviewModel(
        num_coders=2,
        num_reviewers=1,
        num_planners=1,
        enable_feedback_loop=enable_failure_injection
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
    print(f"⚡ Failure Injection: {enable_failure_injection} (30% ignore probability)")

    # Create parent span for entire simulation
    with tracer.start_as_current_span("FullSimulation") as sim_span:
        sim_span.set_attribute("task_count", num_tasks)
        sim_span.set_attribute("jaeger.export", True)
        sim_span.set_attribute("failure_injection.enabled", enable_failure_injection)
        sim_span.set_attribute("failure_injection.type", "ignored_reviewer_input")
        sim_span.set_attribute("failure_injection.probability", 0.3)

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
        generate_reports(full_results, results_dir, enable_failure_injection)

        # Performance metrics
        duration = time.time() - start_time
        sim_span.set_attribute("simulation.duration", duration)
        print(f"\n⏱️  STRESS TEST COMPLETED IN {duration:.2f} SECONDS")
        print(f"⏱️  AVERAGE TIME PER TASK: {duration / num_tasks:.2f} SECONDS")


def generate_reports(full_results, results_dir, failure_injection_enabled):
    # Main task report (CSV)
    main_report = []
    total_feedback_failures = 0

    for i, task_result in enumerate(full_results):
        feedback_failures = task_result.get('feedback_loop_failures', 0)
        total_feedback_failures += feedback_failures

        main_report.append({
            "task_id": i + 1,
            "task": task_result['task'],
            "original_task": task_result['original_task'],
            "subtask_count": len(task_result['workflow']),
            "avg_similarity": task_result['similarity'],
            "errors": task_result['errors'],
            "error_sources": ", ".join(task_result['error_sources']),
            "feedback_loop_failures": feedback_failures,
            "success_rate": sum(1 for r in task_result['subtask_results'] if r['result'] == "Approved") /
                            len(task_result['subtask_results'])
        })

    df_main = pd.DataFrame(main_report)
    df_main.to_csv(f"{results_dir}/main_task_metrics.csv", index=False)

    # Subtask-level report (CSV)
    subtask_report = []
    ignored_feedback_count = 0

    for i, task_result in enumerate(full_results):
        for j, subtask_result in enumerate(task_result['subtask_results']):
            subtask_report.append({
                "main_task_id": i + 1,
                "subtask_id": j + 1,
                "subtask": subtask_result['subtask'],
                "result": subtask_result['result'],
                "similarity": subtask_result.get('similarity', 0),
                "had_feedback_loop": subtask_result.get('had_feedback_loop', False),
                "code_snippet": subtask_result['code'][:100] + ('...' if len(subtask_result['code']) > 100 else '')
            })

            # Count ignored feedback instances
            if subtask_result.get('had_feedback_loop', False) and subtask_result['result'] == "Rejected":
                ignored_feedback_count += 1

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
        f.write(f"Total Feedback Loop Failures: {total_feedback_failures}\n")
        f.write(f"Ignored Feedback Instances: {ignored_feedback_count}\n\n")
        f.write("COMMON MISSING SPANS:\n")
        for span_type, count in validation_results['missing_spans'].most_common(5):
            f.write(f"- {span_type}: {count} occurrences\n")

    # Failure injection analysis
    with open(f"{results_dir}/failure_analysis.txt", "w") as f:
        f.write("FAILURE INJECTION ANALYSIS\n")
        f.write("=" * 50 + "\n")
        f.write(f"Failure Type: Ignored Reviewer Input\n")
        f.write(f"Injection Probability: 30%\n")
        f.write(f"Total Tasks: {len(full_results)}\n")
        f.write(f"Total Subtasks: {len(df_subtasks)}\n")
        f.write(f"Feedback Loop Activations: {len(df_subtasks[df_subtasks['had_feedback_loop'] == True])}\n")
        f.write(f"Ignored Feedback Count: {ignored_feedback_count}\n")
        f.write(
            f"Ignore Rate: {ignored_feedback_count / max(1, len(df_subtasks[df_subtasks['had_feedback_loop'] == True])):.1%}\n\n")

        if ignored_feedback_count > 0:
            f.write("IMPACT ANALYSIS:\n")
            failed_subtasks = df_subtasks[
                (df_subtasks['had_feedback_loop'] == True) &
                (df_subtasks['result'] == 'Rejected')
                ]
            if len(failed_subtasks) > 0:
                avg_similarity_failed = failed_subtasks['similarity'].mean()
                avg_similarity_all = df_subtasks['similarity'].mean()
                f.write(f"Average Similarity (Failed): {avg_similarity_failed:.2f}\n")
                f.write(f"Average Similarity (All): {avg_similarity_all:.2f}\n")
                f.write(f"Quality Impact: {avg_similarity_all - avg_similarity_failed:.2f} points\n")

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
        f.write("   - Tags: failure_injection.enabled OR agent.role\n\n")
        f.write("4. NEW FAILURE TRACES TO LOOK FOR:\n")
        f.write("   - Feedback.Loop spans (indicates rejection → revision)\n")
        f.write("   - failure.ignored_feedback: true attributes\n")
        f.write("   - Subtasks with multiple CoderAgent.step calls\n")
        f.write("   - Tasks with feedback_loop_failures > 0\n\n")
        f.write("5. Trace hierarchy with failures:\n")
        f.write("   MainTask.X\n")
        f.write("   ├── Model.run_task\n")
        f.write("   │   ├── Planner.create_workflow\n")
        f.write("   │   ├── Subtask.1\n")
        f.write("   │   │   ├── CoderAgent.step\n")
        f.write("   │   │   ├── ReviewerAgent.step → Rejected\n")
        f.write("   │   │   └── Feedback.Loop 🚨\n")
        f.write("   │   │       ├── CoderAgent.step (ignored)\n")
        f.write("   │   │       └── ReviewerAgent.step → Rejected\n")
        f.write("   │   └── Subtask.2\n")
        f.write("   └── MainTask.X (completed with failures)\n\n")
        f.write("6. Troubleshooting:\n")
        f.write("   - No traces? Check Docker: docker logs jaeger\n")
        f.write("   - Connection issues? Verify OTLP exporter config\n")

    print(f"\n💾 All reports saved to: {results_dir}")
    print(f"🚨 Failure Injection Analysis:")
    print(f"   - Feedback loop failures: {total_feedback_failures}")
    print(f"   - Ignored feedback instances: {ignored_feedback_count}")
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


if __name__ == "__main__":
    main()