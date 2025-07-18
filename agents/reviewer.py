from tracing.setup_tracer import tracer


class ReviewerAgent:
    def __init__(self, unique_id, model):
        self.unique_id = unique_id
        self.model = model
        self.role = "Reviewer"

    def step(self, code=None):
        if code is None:
            raise ValueError("Reviewer requires code to review")

        # Create span for reviewing activity
        with tracer.start_as_current_span("ReviewerAgent.step") as span:
            span.set_attribute("agent.id", self.unique_id)
            span.set_attribute("agent.role", self.role)
            span.set_attribute("code.input", code[:100])  # First 100 chars

            print(f"Reviewer {self.unique_id} reviewing code")
            result = "Approved" if len(code) > 10 else "Rejected"

            span.set_attribute("review.result", result)
            span.set_attribute("code.length", len(code))

            return result