from mesa import Model
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
import random


class CodeReviewModel:
    """Simplified model without Mesa dependency"""

    def __init__(self, num_coders=2, num_reviewers=1):
        self.next_id = 0
        self.coders = []
        self.reviewers = []

        # Create coders
        for _ in range(num_coders):
            agent = CoderAgent(self.next_id, self)
            self.coders.append(agent)
            self.next_id += 1

        # Create reviewers
        for _ in range(num_reviewers):
            agent = ReviewerAgent(self.next_id, self)
            self.reviewers.append(agent)
            self.next_id += 1

    def run_task(self, task):
        print(f"\nStarting task: {task}")

        # Get a random coder
        import random
        if not self.coders:
            raise RuntimeError("No coders available")
        coder = random.choice(self.coders)

        # Get a random reviewer
        if not self.reviewers:
            raise RuntimeError("No reviewers available")
        reviewer = random.choice(self.reviewers)

        # Execute task flow
        code = coder.step(task)
        result = reviewer.step(code)

        print(f"Task completed: {result}")
        return {"task": task, "code": code, "result": result}