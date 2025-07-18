from opentelemetry import trace

from model import CodeReviewModel
from tracing.setup_tracer import tracer

# Wrap entire simulation in a trace
with tracer.start_as_current_span("Simulation.run") as sim_span:
    # Initialize model
    model = CodeReviewModel(num_coders=2, num_reviewers=1)

    # Test with sample tasks
    tasks = [
        "Implement user login with OAuth",
        "Add payment processing system",
        "Create user profile page with avatar upload",
        "Fix security vulnerability"
    ]

    sim_span.set_attribute("num.tasks", len(tasks))
    print(f"Starting simulation with {len(tasks)} tasks...")

    results = []
    for i, task in enumerate(tasks):
        task_span = tracer.start_span(f"Task.{i + 1}")
        with trace.use_span(task_span, end_on_exit=True):
            task_span.set_attribute("task.description", task)
            print(f"\nProcessing task {i + 1}/{len(tasks)}")
            results.append(model.run_task(task))

    print("\nSIMULATION COMPLETE!")
    print("=" * 40)
    for i, r in enumerate(results):
        print(f"Task {i + 1}: {r['task']}")
        print(f"  Result: {r['result']}")
        print(f"  Code: {r['code'][:40]}{'...' if len(r['code']) > 40 else ''}")
        print("-" * 40)

    # Record overall stats
    approved = sum(1 for r in results if r['result'] == "Approved")
    sim_span.set_attribute("tasks.approved", approved)
    sim_span.set_attribute("tasks.rejected", len(tasks) - approved)
    print(f"\nSUMMARY: {approved}/{len(tasks)} tasks approved")