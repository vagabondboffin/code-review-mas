from model import CodeReviewModel
from llm.task_generator import TaskGenerator
import pandas as pd
from tracing.setup_tracer import tracer
import time
import random


def main():
    # Initialize model with planner
    model = CodeReviewModel(num_coders=2, num_reviewers=1, num_planners=1)

    # Initialize task generator
    task_gen = TaskGenerator()

    # Generate tasks using LLM
    num_tasks = 1
    tasks = []
    print(f"🔧 Generating {num_tasks} tasks with LLM...")
    for i in range(num_tasks):
        with tracer.start_as_current_span("TaskGeneration") as span:
            task = task_gen.generate_task()
            tasks.append(task)
            span.set_attribute("task.content", task)
            print(f"  Generated task {i + 1}: {task}")
        time.sleep(1)  # Avoid rate limiting

    # Run simulation with workflow execution
    print(f"\n🚀 Starting simulation with {len(tasks)} generated tasks...")
    full_results = []

    for i, task in enumerate(tasks):
        print(f"\n{'=' * 60}")
        print(f"🔍 PROCESSING MAIN TASK {i + 1}/{len(tasks)}: {task}")
        print(f"{'=' * 60}")

        with tracer.start_as_current_span(f"MainTask.{i + 1}") as task_span:
            task_span.set_attribute("task.description", task)
            task_result = model.run_task(task)
            full_results.append(task_result)

            # Print workflow summary
            print(f"\n📋 Workflow Summary for Task {i + 1}:")
            for j, subtask in enumerate(task_result['workflow']):
                result = task_result['subtask_results'][j]['result']
                similarity = task_result['subtask_results'][j].get('similarity', 0)
                print(f"  Subtask {j + 1}: {subtask[:50]}... → {result} (Sim: {similarity:.2f})")

            # Add main task metrics to span
            task_span.set_attribute("task.avg_similarity", task_result['similarity'])
            task_span.set_attribute("task.errors", task_result['errors'])

    # Generate detailed reports
    print("\n📊 SIMULATION COMPLETE! GENERATING REPORTS...")
    generate_reports(full_results)


def generate_reports(full_results):
    # Main task report
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
            "success_rate": sum(1 for r in task_result['subtask_results'] if r['result'] == "Approved") / len(
                task_result['subtask_results'])
        })

    df_main = pd.DataFrame(main_report)
    print("\n📈 MAIN TASK REPORT:")
    print("=" * 80)
    print(df_main)
    df_main.to_csv("results/main_task_metrics.csv", index=False)
    print("\n💾 Main task metrics saved to results/main_task_metrics.csv")

    # Subtask-level report
    subtask_report = []
    for i, task_result in enumerate(full_results):
        for j, subtask_result in enumerate(task_result['subtask_results']):
            subtask_report.append({
                "main_task_id": i + 1,
                "main_task": task_result['task'],
                "subtask_id": j + 1,
                "subtask": subtask_result['subtask'],
                "result": subtask_result['result'],
                "similarity": subtask_result.get('similarity', 0),
                "code_snippet": subtask_result['code'][:100] + ('...' if len(subtask_result['code']) > 100 else '')
            })

    df_subtasks = pd.DataFrame(subtask_report)
    print("\n📊 SUBTASK REPORT:")
    print("=" * 80)
    print(df_subtasks.head(10))  # Show first 10 subtasks
    df_subtasks.to_csv("results/subtask_metrics.csv", index=False)
    print("\n💾 Subtask metrics saved to results/subtask_metrics.csv")

    # Summary statistics
    total_subtasks = len(df_subtasks)
    approval_rate = df_subtasks[df_subtasks['result'] == 'Approved'].shape[0] / total_subtasks
    avg_similarity = df_subtasks['similarity'].mean()

    print("\n📌 SUMMARY STATISTICS:")
    print(f"Total main tasks: {len(full_results)}")
    print(f"Total subtasks: {total_subtasks}")
    print(f"Subtask approval rate: {approval_rate:.1%}")
    print(f"Average subtask similarity: {avg_similarity:.2f}")


if __name__ == "__main__":
    main()