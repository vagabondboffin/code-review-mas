import seaborn as sns
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from plotly import graph_objects as go


def plot_misalignment_clusters(df, output_path):
    """Plot misalignment cluster distribution"""
    plt.figure(figsize=(10, 6))
    ax = sns.countplot(
        x='misalignment_cluster',
        data=df,
        order=['Low', 'Moderate', 'High', 'Severe', 'Critical'],
        palette='viridis'
    )
    plt.title('Task Misalignment Distribution')
    plt.xlabel('Misalignment Level')
    plt.ylabel('Count')
    plt.savefig(f"{output_path}/misalignment_clusters.png")
    plt.close()


def plot_error_propagation(role_errors, output_path):
    """Plot error rates by agent role"""
    plt.figure(figsize=(10, 6))
    role_errors['error_rate'].plot(kind='bar', color='coral')
    plt.title('Error Rate by Subtask Outcome')
    plt.ylabel('Error Rate')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(f"{output_path}/error_rates.png")
    plt.close()


def plot_agent_sankey(df, output_path):
    """Create Sankey diagram of agent workflows"""
    # Prepare node labels
    nodes = [
        "Planner", "Coder", "Reviewer Approved",
        "Reviewer Rejected", "Success", "Failure"
    ]

    # Calculate link values
    coder_counts = df.groupby('subtask_result').size()
    reviewer_counts = df.groupby(['subtask_result', 'is_error']).size()

    links = pd.DataFrame({
        'source': [0, 0, 1, 1, 2, 3],
        'target': [1, 1, 2, 3, 4, 5],
        'value': [
            len(df),  # All tasks go from Planner to Coder
            len(df),  # Duplicate for visualization balance
            coder_counts.get('Approved', 0),
            coder_counts.get('Rejected', 0),
            reviewer_counts.get(('Approved', False), 0),
            reviewer_counts.get(('Rejected', True), 0)
        ],
        'label': [
            "Plan", "Plan", "Code", "Code",
            "Approve", "Reject"
        ]
    })

    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=nodes,
            color="blue"
        ),
        link=dict(
            source=links['source'],
            target=links['target'],
            value=links['value'],
            label=links['label']
        )
    )])

    fig.update_layout(
        title_text="Agent Workflow Sankey Diagram",
        font_size=12,
        height=600
    )
    fig.write_html(f"{output_path}/agent_sankey.html")


def plot_agent_network(df, output_path):
    """Create network graph of agent interactions"""
    G = nx.DiGraph()

    # Add nodes
    G.add_node("Planner", role="planning", size=500)
    G.add_node("Coder", role="implementation", size=400)
    G.add_node("Reviewer", role="evaluation", size=400)
    G.add_node("Success", role="outcome", size=300)
    G.add_node("Failure", role="outcome", size=300)

    # Add edges with weights
    approved = df[df['subtask_result'] == 'Approved'].shape[0]
    rejected = df[df['subtask_result'] == 'Rejected'].shape[0]

    G.add_edge("Planner", "Coder", weight=len(df), label="plans")
    G.add_edge("Coder", "Reviewer", weight=len(df), label="implements")
    G.add_edge("Reviewer", "Success", weight=approved, label="approves")
    G.add_edge("Reviewer", "Failure", weight=rejected, label="rejects")

    # Visualize
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, seed=42)
    node_colors = [G.nodes[n]['role'] for n in G.nodes]

    nx.draw_networkx_nodes(
        G, pos, node_size=[G.nodes[n]['size'] for n in G.nodes],
        node_color=[{'planning': 'skyblue', 'implementation': 'lightgreen',
                     'evaluation': 'coral', 'outcome': 'gold'}[G.nodes[n]['role']]
                    for n in G.nodes]
    )

    nx.draw_networkx_edges(
        G, pos, width=[d['weight'] / 100 for _, _, d in G.edges(data=True)],
        edge_color='gray', alpha=0.6
    )

    nx.draw_networkx_labels(G, pos, font_size=10)
    edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

    plt.title("Agent Interaction Network")
    plt.axis('off')
    plt.savefig(f"{output_path}/agent_network.png")
    plt.close()