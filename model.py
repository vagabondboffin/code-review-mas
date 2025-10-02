from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.planner import PlannerAgent
from utils.similarity import SimilarityCalculator
from tracing.setup_tracer import tracer
from opentelemetry.trace import Status, StatusCode
import random
import json
import time
import logging

logger = logging.getLogger(__name__)


class CodeReviewModel:
    def __init__(self, num_coders=2, num_reviewers=1, num_planners=1,
                 enable_feedback_loop=True, derailment_probability=0.2):
        self.next_id = 0
        self.coders = []
        self.reviewers = []
        self.planners = []
        self.enable_feedback_loop = enable_feedback_loop
        self.derailment_probability = derailment_probability  # 20% chance of task derailment

        # Create planners
        for _ in range(num_planners):
            agent = PlannerAgent(self.next_id, self)
            self.planners.append(agent)
            self.next_id += 1

        # Create coders with failure probability
        for _ in range(num_coders):
            agent = CoderAgent(self.next_id, self, ignore_feedback_probability=0.3)
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

        # Derailment task templates
        self.derailment_templates = [
            "Implement user profile management system",
            "Add payment processing functionality",
            "/Create database migration scripts",
            "Build notification service",
            "Develop API rate limiting",
            "Set up logging and monitoring",
            "Optimize database queries",
            "Add error handling middleware",
            "Implement caching mechanism",
            "Create documentation for {topic}",
            "Write tests for {topic}",
            "Debug issues in {topic}",
            "Refactor existing {topic} code",
            "Optimize performance of {topic}",
            "Add security features to {topic}"
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
            span.set_attribute("feedback_loop.enabled", self.enable_feedback_loop)
            span.set_attribute("derailment.probability", self.derailment_probability)

            print(f"\nStarting main task: {task}")
            if is_synthetic_ambiguity or is_natural_ambiguity:
                print(f"  !! Ambiguous task (sources: {', '.join(error_sources)})")

            # Get planner
            planner = random.choice(self.planners)

            # Create workflow decomposition
            subtasks = planner.create_workflow(task)
            span.set_attribute("workflow.subtasks", json.dumps(subtasks))
            print(f"Workflow created with {len(subtasks)} subtasks")

            # Execute subtasks
            subtask_results = []
            total_similarity = 0
            total_errors = 0
            derailment_count = 0

            for i, subtask in enumerate(subtasks):
                # Ensure subtask is a string
                if not isinstance(subtask, str):
                    subtask = str(subtask)
                    error_sources.append(f"subtask_{i + 1}_type_conversion")

                with tracer.start_as_current_span(f"Subtask.{i + 1}") as subtask_span:
                    subtask_span.set_attribute("subtask.assigned", subtask)
                    subtask_span.set_attribute("subtask.position", i + 1)

                    # FAILURE INJECTION: Task Derailment
                    actual_task, was_derailed = self._inject_derailment(subtask, task)
                    if was_derailed:
                        derailment_count += 1
                        error_sources.append(f"subtask_{i + 1}_derailment")
                        subtask_span.set_attribute("failure.task_derailment", True)
                        subtask_span.set_attribute("task.assigned", subtask)
                        subtask_span.set_attribute("task.actual", actual_task)
                        subtask_span.set_attribute("derailment.type", self._get_derailment_type(actual_task))
                        subtask_span.set_status(StatusCode.ERROR, "Task derailment detected")
                        print(f"  🚨 TASK DERAILMENT: Agent working on '{actual_task}' instead of '{subtask}'")

                    subtask_span.set_attribute("subtask.description", actual_task)
                    print(f"\nProcessing subtask {i + 1}/{len(subtasks)}: {actual_task}")

                    # Get agents for this subtask
                    coder = random.choice(self.coders)
                    reviewer = random.choice(self.reviewers)

                    # Generate code for the actual task (which might be derailed)
                    code = coder.step(actual_task)

                    # Inject bad code (10% chance)
                    is_bad_code = random.random() < 0.1
                    if is_bad_code:
                        original_code = code
                        code = self._generate_bad_code()
                        error_sources.append(f"subtask_{i + 1}_bad_code")
                        print(f"  !! Bad code injected in subtask {i + 1}")

                    # Review code
                    result = reviewer.step(code)

                    # FEEDBACK LOOP: If rejected and feedback enabled, allow revision
                    if result == "Rejected" and self.enable_feedback_loop:
                        with tracer.start_as_current_span("Feedback.Loop") as feedback_span:
                            feedback_span.set_attribute("subtask.id", i + 1)
                            feedback_span.set_attribute("initial_result", result)
                            feedback_span.set_attribute("was_derailed", was_derailed)

                            print(f"  🔁 Feedback loop activated for subtask {i + 1}")

                            # Generate revised code
                            revised_code = coder.step(actual_task, feedback=result, previous_code=code)

                            # Detect if coder ignored feedback (same code returned)
                            code_unchanged = (code == revised_code)
                            feedback_span.set_attribute("feedback.code_unchanged", code_unchanged)

                            if code_unchanged:
                                # Major failure: Coder completely ignored feedback
                                feedback_span.set_status(StatusCode.ERROR, "Coder ignored reviewer feedback")
                                error_sources.append(f"subtask_{i + 1}_ignored_feedback")
                                print(f"  🚨 MAJOR FAILURE: Coder ignored feedback and resubmitted same code!")

                            revised_result = reviewer.step(revised_code)

                            # If code was unchanged and still rejected, this is a critical failure
                            if code_unchanged and revised_result == "Rejected":
                                feedback_span.set_attribute("failure.critical", True)
                                error_sources.append(f"subtask_{i + 1}_critical_feedback_failure")
                                print(f"  💥 CRITICAL: Complete communication breakdown!")

                            feedback_span.set_attribute("revised_result", revised_result)
                            feedback_span.set_attribute("code_changed", code != revised_code)

                            # Use the revised result
                            code = revised_code
                            result = revised_result

                            print(f"  🔁 Feedback loop completed. New result: {result}")

                    # Calculate similarity for this subtask (using ORIGINAL assigned task)
                    # This measures how derailed the work is from what was actually needed
                    intended_similarity = self.similarity_calculator.calculate_similarity(subtask, code)
                    actual_similarity = self.similarity_calculator.calculate_similarity(actual_task, code)

                    total_similarity += intended_similarity  # Use intended for overall score

                    # Record subtask results
                    subtask_results.append({
                        "subtask": subtask,
                        "actual_task": actual_task,
                        "was_derailed": was_derailed,
                        "code": code,
                        "result": result,
                        "intended_similarity": intended_similarity,
                        "actual_similarity": actual_similarity,
                        "similarity": intended_similarity,  # Main metric uses intended
                        "had_feedback_loop": result == "Rejected" and self.enable_feedback_loop
                    })

                    # Add subtask attributes to span
                    subtask_span.set_attribute("subtask.intended_similarity", float(intended_similarity))
                    subtask_span.set_attribute("subtask.actual_similarity", float(actual_similarity))
                    subtask_span.set_attribute("subtask.similarity_gap", float(intended_similarity - actual_similarity))
                    subtask_span.set_attribute("subtask.result", result)
                    subtask_span.set_attribute("subtask.feedback_loop_used",
                                               result == "Rejected" and self.enable_feedback_loop)
                    subtask_span.set_attribute("subtask.was_derailed", was_derailed)

            # Calculate average similarity across subtasks
            avg_similarity = total_similarity / len(subtasks) if subtasks else 0

            # Count feedback loop failures
            feedback_failures = sum(1 for r in subtask_results
                                    if r.get('had_feedback_loop') and r['result'] == "Rejected")
            if feedback_failures > 0:
                error_sources.append(f"feedback_loop_failures:{feedback_failures}")

            # metrics
            errors = len(error_sources)
            span.set_attribute("task_code.avg_similarity", float(avg_similarity))
            span.set_attribute("task.errors", errors)
            span.set_attribute("task.error_sources", ",".join(error_sources))
            span.set_attribute("task.feedback_loop_failures", feedback_failures)
            span.set_attribute("task.derailment_count", derailment_count)
            span.set_attribute("task.result", "Completed")

            print(f"\nMain task completed. Avg similarity: {avg_similarity:.2f}, Errors: {errors}")
            if feedback_failures > 0:
                print(f"  🚨 Feedback loop failures: {feedback_failures}")
            if derailment_count > 0:
                print(f"  🚨 Task derailments: {derailment_count}")

            return {
                "task": task,
                "original_task": original_task,
                "workflow": subtasks,
                "subtask_results": subtask_results,
                "similarity": avg_similarity,
                "errors": errors,
                "error_sources": error_sources,
                "feedback_loop_failures": feedback_failures,
                "derailment_count": derailment_count
            }

    def _inject_derailment(self, original_task, main_task):
        """Inject task derailment with specified probability"""
        if random.random() < self.derailment_probability:
            derailed_task = self._generate_derailed_task(original_task, main_task)
            return derailed_task, True
        return original_task, False

    def _generate_derailed_task(self, original_task, main_task):
        """Generate a realistically derailed task"""
        # Choose derailment type
        derailment_type = random.choice(["domain_shift", "meta_task", "related_but_wrong"])

        if derailment_type == "domain_shift":
            # Completely different domain
            template = random.choice([t for t in self.derailment_templates if "{topic}" not in t])
            return template

        elif derailment_type == "meta_task":
            # Work on meta-aspects instead of actual task
            meta_templates = [t for t in self.derailment_templates if "{topic}" in t]
            template = random.choice(meta_templates)
            return template.format(topic=original_task.lower())

        else:  # related_but_wrong
            # Work on something related but not what was assigned
            related_actions = ["debug", "optimize", "refactor", "document", "test", "secure"]
            action = random.choice(related_actions)
            return f"{action} {original_task}"

    def _get_derailment_type(self, derailed_task):
        """Classify the type of derailment"""
        if any(template in derailed_task for template in self.derailment_templates if "{topic}" not in template):
            return "domain_shift"
        elif any(word in derailed_task for word in ["debug", "optimize", "refactor", "document", "test"]):
            return "related_but_wrong"
        else:
            return "meta_task"

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