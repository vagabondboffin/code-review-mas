import pandas as pd
import json
import numpy as np
from collections import defaultdict
import ast


def load_trace_data(file_path):
    """Load JSONL trace data into a structured DataFrame"""
    records = []
    with open(file_path) as f:
        for line in f:
            record = json.loads(line)

            # Flatten task-level data
            task_data = {
                'task_id': record.get('task_id', None),
                'main_task': record['task'],
                'original_task': record['original_task'],
                'subtask_count': len(record['workflow']),
                'avg_similarity': record['similarity'],
                'misalignment_score': 1 - record['similarity'],
                'total_errors': record['errors'],
                'error_sources': ', '.join(record['error_sources']),
                'success_rate': sum(1 for r in record['subtask_results'] if r['result'] == "Approved") /
                                len(record['subtask_results'])
            }

            # Process subtasks
            for i, subtask in enumerate(record['subtask_results']):
                records.append({
                    **task_data,
                    'subtask_id': i + 1,
                    'subtask': subtask['subtask'],
                    'code_snippet': subtask['code'][:100] + ('...' if len(subtask['code']) > 100 else ''),
                    'subtask_result': subtask['result'],
                    'subtask_similarity': subtask.get('similarity', 0),
                    'subtask_misalignment': 1 - subtask.get('similarity', 0),
                    'is_error': 'error' in subtask['subtask'].lower() or
                                'rejected' in subtask['result'].lower()
                })

    return pd.DataFrame(records)


def compute_agent_interactions(df):
    """Compute agent interaction metrics"""
    # Role-based error propagation
    role_errors = df.groupby(['subtask_result', 'is_error']).size().unstack().fillna(0)
    role_errors['error_rate'] = role_errors[True] / (role_errors[True] + role_errors[False])

    # Misalignment clustering
    df['misalignment_cluster'] = pd.cut(
        df['subtask_misalignment'],
        bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
        labels=['Low', 'Moderate', 'High', 'Severe', 'Critical']
    )

    # Error propagation metrics
    error_propagation = df.groupby('task_id').apply(
        lambda x: x['is_error'].sum() / len(x)
    ).reset_index(names='error_propagation')

    return {
        'role_errors': role_errors,
        'misalignment_clusters': df.groupby('misalignment_cluster').size(),
        'error_propagation': error_propagation
    }