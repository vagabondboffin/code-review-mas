from tracing.setup_tracer import tracer
from openai import OpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class PlannerAgent:
    def __init__(self, unique_id, model):
        self.unique_id = unique_id
        self.model = model
        self.role = "Planner"

    def create_workflow(self, task: str) -> list:
        """Break down task into subtasks using GPT-4-turbo"""
        with tracer.start_as_current_span("Planner.create_workflow") as span:
            span.set_attribute("agent.id", self.unique_id)
            span.set_attribute("agent.role", self.role)
            span.set_attribute("task.input", task)

            print(f"Planner {self.unique_id} decomposing task...")

            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system",
                         "content": "You are a software architect. Break technical tasks into 2-4 subtasks as JSON strings."},
                        {"role": "user",
                         "content": f"Decompose this backend task: {task}\nOutput JSON format: {{'subtasks': [str]}}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=300
                )

                content = response.choices[0].message.content
                workflow = json.loads(content)
                subtasks = workflow.get('subtasks', [])

                # Ensure all subtasks are strings
                subtasks = [str(item) for item in subtasks]

                span.set_attribute("workflow.subtasks", json.dumps(subtasks))
                print(f"Planner created {len(subtasks)} subtasks")
                return subtasks

            except Exception as e:
                print(f"Planning failed: {e}")
                span.record_exception(e)
                return self._fallback_workflow(task)

    def _fallback_workflow(self, task: str) -> list:
        """Fallback workflow generation"""
        if "authentication" in task.lower():
            return ["Design auth flow", "Implement core logic", "Add security safeguards"]
        elif "payment" in task.lower():
            return ["Integrate payment gateway", "Create transaction handling", "Implement reconciliation"]
        else:
            return [f"Subtask 1 for {task[:20]}", f"Subtask 2 for {task[:20]}"]