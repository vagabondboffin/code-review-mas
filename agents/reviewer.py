from tracing.setup_tracer import tracer


class ReviewerAgent:
    def __init__(self, unique_id, model):
        self.unique_id = unique_id
        self.model = model
        self.role = "Reviewer"
        # Define patterns that indicate bad/incomplete code
        self.bad_code_patterns = [
            "todo", "pass", "placeholder",
            "notimplemented", "fixme", "//", "/*"
        ]

    def step(self, code=None):
        if code is None:
            raise ValueError("Reviewer requires code to review")

        # Create span for reviewing activity
        with tracer.start_as_current_span("ReviewerAgent.step") as span:
            span.set_attribute("agent.id", self.unique_id)
            span.set_attribute("agent.role", self.role)
            span.set_attribute("code.input", code[:100])  # First 100 chars

            print(f"Reviewer {self.unique_id} reviewing code")

            # Enhanced error detection logic
            rejection_reason = None
            result = "Approved"  # Default to approved

            # Check 1: Code length (original check)
            if len(code) <= 10:
                result = "Rejected"
                rejection_reason = "code_too_short"

            # Check 2: Bad code patterns (new)
            elif any(pattern in code.lower() for pattern in self.bad_code_patterns):
                result = "Rejected"
                rejection_reason = "bad_code_pattern"

            # Check 3: Placeholder code (new)
            elif "return" not in code and "=" not in code:
                result = "Rejected"
                rejection_reason = "no_implementation"

            # Record results in span
            span.set_attribute("review.results", result)
            span.set_attribute("code.length", len(code))

            if rejection_reason:
                span.set_attribute("rejection.reason", rejection_reason)

            return result