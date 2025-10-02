import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, ConnectionPatch
import numpy as np


def create_workflow_diagram(output_path):
    """Create a professional workflow diagram with failure hotspots"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))

    # Colors
    normal_color = '#3498db'
    failure_color = '#e74c3c'
    highlight_color = '#f39c12'
    success_color = '#2ecc71'

    # Coordinates for workflow steps
    steps = {
        'task_generation': (1, 6),
        'planner': (3, 6),
        'subtask_1': (5, 7),
        'subtask_2': (5, 5),
        'coder': (7, 7),
        'reviewer': (9, 7),
        'success': (11, 7),
        'feedback_loop': (8, 5.5),
        'failure': (11, 5)
    }

    # Draw workflow boxes
    boxes = {
        'Task Generation': (steps['task_generation'][0] - 0.8, steps['task_generation'][1] - 0.3, 1.6, 0.6),
        'Planner Agent': (steps['planner'][0] - 0.8, steps['planner'][1] - 0.3, 1.6, 0.6),
        'Subtask 1': (steps['subtask_1'][0] - 0.6, steps['subtask_1'][1] - 0.2, 1.2, 0.4),
        'Subtask 2': (steps['subtask_2'][0] - 0.6, steps['subtask_2'][1] - 0.2, 1.2, 0.4),
        'Coder Agent': (steps['coder'][0] - 0.8, steps['coder'][1] - 0.3, 1.6, 0.6),
        'Reviewer Agent': (steps['reviewer'][0] - 0.8, steps['reviewer'][1] - 0.3, 1.6, 0.6),
        'Success ✓': (steps['success'][0] - 0.6, steps['success'][1] - 0.2, 1.2, 0.4),
        'Feedback Loop': (steps['feedback_loop'][0] - 0.8, steps['feedback_loop'][1] - 0.2, 1.6, 0.4),
        'Failure ✗': (steps['failure'][0] - 0.6, steps['failure'][1] - 0.2, 1.2, 0.4)
    }

    # Draw boxes
    for label, (x, y, w, h) in boxes.items():
        color = normal_color
        if 'Failure' in label:
            color = failure_color
        elif 'Success' in label:
            color = success_color
        elif 'Feedback' in label:
            color = highlight_color

        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                             linewidth=2, edgecolor='black', facecolor=color, alpha=0.8)
        ax.add_patch(box)
        ax.text(x + w / 2, y + h / 2, label, ha='center', va='center', fontweight='bold', fontsize=9)

    # Draw connections
    connections = [
        (steps['task_generation'], steps['planner']),
        (steps['planner'], steps['subtask_1']),
        (steps['planner'], steps['subtask_2']),
        (steps['subtask_1'], steps['coder']),
        (steps['coder'], steps['reviewer']),
        (steps['reviewer'], steps['success']),
        (steps['reviewer'], (steps['reviewer'][0] + 0.5, steps['reviewer'][1] - 1)),
        ((steps['reviewer'][0] + 0.5, steps['reviewer'][1] - 1), steps['feedback_loop']),
        (steps['feedback_loop'], (steps['coder'][0], steps['feedback_loop'][1])),
        ((steps['coder'][0], steps['feedback_loop'][1]), steps['coder']),
        ((steps['reviewer'][0] + 0.5, steps['reviewer'][1] - 1), steps['failure'])
    ]

    for start, end in connections:
        arrow = ConnectionPatch(start, end, "data", "data",
                                arrowstyle="->", shrinkA=5, shrinkB=5,
                                mutation_scale=20, fc="black", lw=1.5)
        ax.add_patch(arrow)

    # Add failure hotspots
    hotspots = [
        (steps['subtask_2'], "🚨 Task Derailment\nWrong domain work", failure_color),
        (steps['feedback_loop'], "🚨 Ignored Feedback\nSame code resubmitted", failure_color),
        (steps['reviewer'], "🙈 Reviewer Blindspot\nApproves derailed work", highlight_color)
    ]

    for pos, text, color in hotspots:
        circle = Circle(pos, radius=0.3, facecolor=color, edgecolor='black', linewidth=2, alpha=0.9)
        ax.add_patch(circle)
        ax.text(pos[0], pos[1] - 0.5, text, ha='center', va='top', fontsize=8,
                fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))

    # Add metrics annotations
    metrics_text = """
    Key Failure Metrics:
    • Failure Detection Rate: 85-95%
    • Derailment Impact: 40-60% quality drop
    • Reviewer Blindspots: 15-25% derailed work approved
    • Propagation: 2-4 affected steps per failure
    """

    ax.text(12, 6, metrics_text, fontsize=10, bbox=dict(boxstyle="round,pad=1", facecolor='lightblue', alpha=0.8))

    # Setup plot
    ax.set_xlim(0, 14)
    ax.set_ylim(4, 8)
    ax.set_aspect('equal')
    ax.axis('off')

    plt.title('Multi-Agent Workflow with Failure Injection Hotspots', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    create_workflow_diagram("results/workflow_diagram.png")