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
import numpy as np  # NEW: For float conversion

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

    # Initialize model with planner
    model = CodeReviewModel(num_coders=2, num_reviewers=1, num_planners=1)
    task_gen = TaskGenerator()

    # Create results directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"results/stress_test_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)

    # Generate tasks using LLM
    num_tasks = 5
    tasks = []
    print(f"🔧 Generating {num_tasks} tasks with LLM...")

    # Create parent span for entire simulation
    with tracer.start_as_current_span("FullSimulation") as sim_span:
        sim_span.set_attribute("task_count", num_tasks)
        sim_span.set_attribute("jaeger.export", True)

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
                task_result = model.run_task(task)
                full_results.append(task_result)

        # Generate reports
        print("\n📊 SIMULATION COMPLETE! GENERATING REPORTS...")
        generate_reports(full_results, results_dir)

        # Performance metrics
        duration = time.time() - start_time
        sim_span.set_attribute("simulation.duration", duration)
        print(f"\n⏱️  STRESS TEST COMPLETED IN {duration:.2f} SECONDS")
        print(f"⏱️  AVERAGE TIME PER TASK: {duration / num_tasks:.2f} SECONDS")


def generate_reports(full_results, results_dir):
    # Main task report (CSV)
    main_report = []
    for i, task_result in enumerate(full_results):
        main_report.append({
            "task_id": i + 1,
            "task": task_result['task'],
            "original_task": task_result['original_task'],
            "subtask_count": len(task_result['workflow']),
            "avg_similarity": task_result['similarity'],
            "errors": task_result['errors'],
            "error_sources": ", ".join(task_result['error_sources']),
            "success_rate": sum(1 for r in task_result['subtask_results'] if r['result'] == "Approved") /
                            len(task_result['subtask_results'])
        })

    df_main = pd.DataFrame(main_report)
    df_main.to_csv(f"{results_dir}/main_task_metrics.csv", index=False)

    # Subtask-level report (CSV)
    subtask_report = []
    for i, task_result in enumerate(full_results):
        for j, subtask_result in enumerate(task_result['subtask_results']):
            subtask_report.append({
                "main_task_id": i + 1,
                "subtask_id": j + 1,
                "subtask": subtask_result['subtask'],
                "result": subtask_result['result'],
                "similarity": subtask_result.get('similarity', 0),
                "code_snippet": subtask_result['code'][:100] + ('...' if len(subtask_result['code']) > 100 else '')
            })

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
        f.write(f"Coverage Success Rate: {validation_results['coverage_rate']:.1%}\n\n")
        f.write("COMMON MISSING SPANS:\n")
        for span_type, count in validation_results['missing_spans'].most_common(5):
            f.write(f"- {span_type}: {count} occurrences\n")

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
        f.write("   - Tags: agent.role OR task.input\n\n")
        f.write("4. Trace hierarchy example:\n")
        f.write("   FullSimulation (root)\n")
        f.write("   ├── TaskGeneration\n")
        f.write("   ├── MainTask.1\n")
        f.write("   │   ├── Model.run_task\n")
        f.write("   │   │   ├── Planner.create_workflow\n")
        f.write("   │   │   ├── Subtask.1\n")
        f.write("   │   │   │   ├── CoderAgent.step\n")
        f.write("   │   │   │   └── ReviewerAgent.step\n")
        f.write("   │   │   └── Subtask.2\n")
        f.write("   │   │       ├── CoderAgent.step\n")
        f.write("   │   │       └── ReviewerAgent.step\n")
        f.write("   └── MainTask.2\n\n")
        f.write("5. Troubleshooting:\n")
        f.write("   - No traces? Check Docker: docker logs jaeger\n")
        f.write("   - Connection issues? Verify OTLP exporter config\n")

    print(f"\n💾 All reports saved to: {results_dir}")
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