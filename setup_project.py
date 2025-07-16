import os

# Define the directory structure (relative to current directory)
structure = [
    # Agents package
    ("agents", [
        "coder.py",
        "reviewer.py",
        "architect.py"
    ]),

    # LLM package
    ("llm", [
        "task_generator.py",
        "workflow_planner.py"
    ]),

    # Tracing package
    ("tracing", [
        "setup_tracer.py",
        "export_config.py"
    ]),

    # Analysis package
    ("analysis", [
        "mast_analysis.ipynb"
    ]),

    # Report package with screenshots
    ("report", [
        "findings.pdf",
        ("jaeger_screenshots", [])
    ]),

    # Root files
    "run_simulation.py",
    "requirements.txt",
    "README.md"
]


def create_structure(base_path, items):
    """Creates directory structure in the current directory"""
    for item in items:
        if isinstance(item, tuple):
            # Handle (folder, [files]) pattern
            folder, contents = item
            folder_path = os.path.join(base_path, folder)
            os.makedirs(folder_path, exist_ok=True)
            create_structure(folder_path, contents)
        elif isinstance(item, str):
            # Handle file creation
            file_path = os.path.join(base_path, item)
            if not os.path.exists(file_path):
                open(file_path, 'w').close()
        elif isinstance(item, list):
            # Handle nested lists
            create_structure(base_path, item)


# Create the structure in current directory
create_structure(os.getcwd(), structure)

print("✅ Directory structure created successfully in current directory!")
print("Current directory:", os.getcwd())