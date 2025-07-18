from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from tracing.setup_tracer import tracer
import random


class CodeReviewModel:
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
        # Create span for entire task
        with tracer.start_as_current_span("Model.run_task") as span:
            span.set_attribute("task.description", task)

            print(f"\nStarting task: {task}")

            # Get a random coder
            if not self.coders:
                span.record_exception(RuntimeError("No coders available"))
                raise RuntimeError("No coders available")
            coder = random.choice(self.coders)

            # Get a random reviewer
            if not self.reviewers:
                span.record_exception(RuntimeError("No reviewers available"))
                raise RuntimeError("No reviewers available")
            reviewer = random.choice(self.reviewers)

            # Execute task flow
            code = coder.step(task)
            result = reviewer.step(code)

            print(f"Task completed: {result}")

            # Record final results
            span.set_attribute("task.result", result)
            span.set_attribute("code.length", len(code))

            return {"task": task, "code": code, "result": result}