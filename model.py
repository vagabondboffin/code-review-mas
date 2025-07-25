from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.planner import PlannerAgent
from utils.similarity import SimilarityCalculator
from tracing.setup_tracer import tracer
import random
import json
import time
import logging

logger = logging.getLogger(__name__)

class CodeReviewModel:
    def __init__(self, num_coders=2, num_reviewers=1, num_planners=1):
        self.next_id = 0
        self.coders = []
        self.reviewers = []
        self.planners = []

        # Create planners (new)
        for _ in range(num_planners):
            agent = PlannerAgent(self.next_id, self)
            self.planners.append(agent)
            self.next_id += 1

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

        self.similarity_calculator = SimilarityCalculator()
        self.ambiguous_phrases = [
            "using appropriate methods", "with proper implementation",
            "following best practices", "in a scalable way"
        ]

    def run_task(self, task):
        with tracer.start_as_current_span("Model.run_task") as span:
            # Track error sources
            error_sources = []
            original_task = task

            # Inject ambiguity (30% chance)
            is_synthetic_ambiguity = random.random() < 0.3
            if is_synthetic_ambiguity:
                task = self._make_ambiguous(task)
                error_sources.append("synthetic_ambiguity")

            # Detect natural ambiguity
            is_natural_ambiguity = any(phrase in task for phrase in self.ambiguous_phrases)
            if is_natural_ambiguity:
                error_sources.append("natural_ambiguity")

            span.set_attribute("task.original", original_task)
            span.set_attribute("task.assigned", task)
            span.set_attribute("task.synthetic_ambiguity", is_synthetic_ambiguity)
            span.set_attribute("task.natural_ambiguity", is_natural_ambiguity)

            # print(f"\nStarting main task: {task}")
            logger.info(f"Starting task: {task[:50]}")
            if is_synthetic_ambiguity or is_natural_ambiguity:
                logger.warning(f"Ambiguous task detected: {error_sources}")
                # print(f"  !! Ambiguous task (sources: {', '.join(error_sources)})")

            # Get planner - new
            planner = random.choice(self.planners)

            # Create workflow decomposition - new
            subtasks = planner.create_workflow(task)
            span.set_attribute("workflow.subtasks", json.dumps(subtasks))
            print(f"Workflow created with {len(subtasks)} subtasks")

            # Execute subtasks
            subtask_results = []
            total_similarity = 0
            total_errors = 0

            # Trace span creation
            span_created = {
                "model_run_task": True,
                "planner_workflow": bool(subtasks),
                "coder_steps": 0,
                "review_steps": 0
            }

            for i, subtask in enumerate(subtasks):
                with tracer.start_as_current_span(f"Subtask.{i + 1}") as subtask_span:
                    subtask_span.set_attribute("subtask.description", subtask)
                    print(f"\nProcessing subtask {i + 1}/{len(subtasks)}: {subtask}")

                    # Get agents for this subtask
                    coder = random.choice(self.coders)
                    reviewer = random.choice(self.reviewers)

                    # Generate code
                    code = coder.step(subtask)

                    # Inject bad code (10% chance) - per subtask now
                    is_bad_code = random.random() < 0.1
                    if is_bad_code:
                        original_code = code
                        code = self._generate_bad_code()
                        error_sources.append(f"subtask_{i + 1}_bad_code")
                        print(f"  !! Bad code injected in subtask {i + 1}")

                    # Calculate similarity for this subtask
                    similarity = self.similarity_calculator.calculate_similarity(subtask, code)
                    total_similarity += similarity

                    # Review code
                    result = reviewer.step(code)

                    # Record subtask results
                    subtask_results.append({
                        "subtask": subtask,
                        "code": code,
                        "result": result,
                        "similarity": similarity
                    })

                    # Add subtask attributes to span
                    subtask_span.set_attribute("subtask.similarity", float(similarity))
                    subtask_span.set_attribute("subtask.result", result)

                    span_created["coder_steps"] += 1
                    span_created["review_steps"] += 1


            # Calculate average similarity across subtasks
            avg_similarity = total_similarity / len(subtasks) if subtasks else 0

            # metrics
            errors = len(error_sources)
            span.set_attribute("task_code.avg_similarity", float(avg_similarity))
            span.set_attribute("task.errors", errors)
            span.set_attribute("task.error_sources", ",".join(error_sources))
            span.set_attribute("task.result", "Completed")  # Overall task status

            # Record span coverage in error sources
            for key, present in span_created.items():
                if not present:
                    error_sources.append(f"missing_span_{key}")

            print(f"\nMain task completed. Avg similarity: {avg_similarity:.2f}, Errors: {errors}")
            return {
                "task": task,
                "original_task": original_task,
                "workflow": subtasks,
                "subtask_results": subtask_results,
                "similarity": avg_similarity,
                "errors": errors,
                "error_sources": error_sources,
                "span_coverage": span_created
            }

    def _make_ambiguous(self, task: str) -> str:
        return f"{task} {random.choice(self.ambiguous_phrases)}"

    def _generate_bad_code(self) -> str:
        bad_code_examples = [
            "# TODO: Implement this functionality",
            "raise NotImplementedError('Pending implementation')",
            "return {'status': 'unimplemented'}",
            "// PLACEHOLDER: Actual code goes here",
            "pass  # To be completed"
        ]
        return random.choice(bad_code_examples)