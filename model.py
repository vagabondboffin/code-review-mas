from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from utils.similarity import SimilarityCalculator
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

            print(f"\nStarting task: {task}")
            if is_synthetic_ambiguity or is_natural_ambiguity:
                print(f"  !! Ambiguous task (sources: {', '.join(error_sources)})")

            # Get agents
            coder = random.choice(self.coders)
            reviewer = random.choice(self.reviewers)

            # Generate code
            code = coder.step(task)

            # Inject bad code (10% chance)
            is_bad_code = random.random() < 0.1
            if is_bad_code:
                original_code = code
                code = self._generate_bad_code()
                error_sources.append("bad_code")
                print(f"  !! Bad code injected (original: {original_code[:20]}...)")

            # Calculate similarity
            similarity = self.similarity_calculator.calculate_similarity(task, code)

            # Review code
            result = reviewer.step(code)

            # Final metrics
            errors = len(error_sources)
            span.set_attribute("task_code.similarity", float(similarity))
            span.set_attribute("task.errors", errors)
            span.set_attribute("task.error_sources", ",".join(error_sources))
            span.set_attribute("task.result", result)

            print(f"Task completed: {result} (Similarity: {similarity:.2f}, Errors: {errors})")
            return {
                "task": task,
                "original_task": original_task,
                "code": code,
                "result": result,
                "similarity": similarity,
                "errors": errors,
                "error_sources": error_sources
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