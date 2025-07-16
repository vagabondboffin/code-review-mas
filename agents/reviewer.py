from mesa import Agent


class ReviewerAgent(Agent):
    def __init__(self, unique_id, model):
        # Simplified initialization for Mesa 3.0.0 + Python 3.13
        self.unique_id = unique_id
        self.model = model
        self.role = "Reviewer"

    def step(self, code=None):
        if code is None:
            raise ValueError("Reviewer requires code to review")
        print(f"Reviewer {self.unique_id} reviewing code")
        return "Approved" if len(code) > 10 else "Rejected"