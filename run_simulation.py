from model import CodeReviewModel

# Initialize model
model = CodeReviewModel(num_coders=2, num_reviewers=1)

# Test with sample tasks
tasks = [
    "Implement user login with OAuth",
    "Add payment processing system",
    "Create user profile page with avatar upload",
    "Fix security vulnerability"
]

print("Starting simulation with 2 coders and 1 reviewer...")
results = []
for i, task in enumerate(tasks):
    print(f"\nProcessing task {i + 1}/{len(tasks)}")
    results.append(model.run_task(task))

print("\nSIMULATION COMPLETE!")
print("=" * 40)
for i, r in enumerate(results):
    print(f"Task {i + 1}: {r['task']}")
    print(f"  Result: {r['result']}")
    print(f"  Code: {r['code'][:40]}{'...' if len(r['code']) > 40 else ''}")
    print("-" * 40)