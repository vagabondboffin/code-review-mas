from mesa import Agent


class CoderAgent(Agent):
    def __init__(self, unique_id, model):
        # Simplified initialization for Mesa 3.0.0 + Python 3.13
        self.unique_id = unique_id
        self.model = model
        self.role = "Coder"

    def step(self, task=None):
        if task is None:
            raise ValueError("Coder requires a task")
        print(f"Coder {self.unique_id} working on: {task}")
        return f"Code for {task}"