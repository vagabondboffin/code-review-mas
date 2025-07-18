from tracing.setup_tracer import tracer


class CoderAgent:
    def __init__(self, unique_id, model):
        self.unique_id = unique_id
        self.model = model
        self.role = "Coder"

    def step(self, task=None):
        if task is None:
            raise ValueError("Coder requires a task")

        # Create span for coding activity
        with tracer.start_as_current_span("CoderAgent.step") as span:
            span.set_attribute("agent.id", self.unique_id)
            span.set_attribute("agent.role", self.role)
            span.set_attribute("task.input", task)

            print(f"Coder {self.unique_id} working on: {task}")
            code = f"Code for {task}"

            span.set_attribute("task.output", code)
            span.set_attribute("task.status", "completed")

            return code