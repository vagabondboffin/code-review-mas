from model import CodeReviewModel
import pandas as pd
from tracing.setup_tracer import tracer

# Initialize model
model = CodeReviewModel(num_coders=2, num_reviewers=1)

# Test with sample tasks
tasks = [
    "Implement user login with OAuth",
    "Add payment processing system",
    "Create user profile page with avatar upload",
    "Fix security vulnerability"
]

print(f"Starting simulation with {len(tasks)} tasks...")
results = []
for i, task in enumerate(tasks):
    print(f"\nProcessing task {i + 1}/{len(tasks)}")
    results.append(model.run_task(task))

print("\nSIMULATION COMPLETE!")
print("=" * 60)
print("TASK METRICS SUMMARY:")
print("=" * 60)

# Create detailed report
report_data = []
for i, r in enumerate(results):
    report_data.append({
        "task_id": i + 1,
        "assigned_task": r['task'],
        "original_task": r['original_task'],
        "similarity": r['similarity'],
        "errors": r['errors'],
        "error_sources": ", ".join(r['error_sources']) if r['error_sources'] else "None",
        "result": r['result'],
        "code_snippet": r['code'][:100] + ('...' if len(r['code']) > 100 else '')
    })

df = pd.DataFrame(report_data)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print(df)

# Save full results
df.to_csv("results/simulation_metrics.csv", index=False)
print("\nDetailed metrics saved to results/simulation_metrics.csv")

# Calculate statistics
approval_rate = df[df['result'] == 'Approved'].shape[0] / len(df)
avg_similarity = df['similarity'].mean()
error_rate = (df['errors'] > 0).mean()

print("\nSUMMARY STATISTICS:")
print(f"Approval rate: {approval_rate:.1%}")
print(f"Average similarity: {avg_similarity:.2f}")
print(f"Error incidence rate: {error_rate:.1%}")