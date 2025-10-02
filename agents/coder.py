from tracing.setup_tracer import tracer
# Add to imports in model.py and agents/coder.py
from opentelemetry.trace import Status, StatusCode
import random


class CoderAgent:
    def __init__(self, unique_id, model, ignore_feedback_probability=0.4):
        self.unique_id = unique_id
        self.model = model
        self.role = "Coder"
        self.ignore_feedback_probability = ignore_feedback_probability  # 30% chance to ignore feedback
        self.revision_attempts = {}  # Track revision attempts per task

    def step(self, task=None, feedback=None, previous_code=None):
        if task is None:
            raise ValueError("Coder requires a task")

        # Ensure task is a string
        if not isinstance(task, str):
            task = str(task)

        with tracer.start_as_current_span("CoderAgent.step") as span:
            span.set_attribute("agent.id", self.unique_id)
            span.set_attribute("agent.role", self.role)
            span.set_attribute("task.input", task)

            # Track if this is a revision attempt
            is_revision = feedback is not None and previous_code is not None
            span.set_attribute("coding.is_revision", is_revision)

            if is_revision:
                span.set_attribute("feedback.received", feedback)
                span.set_attribute("revision.attempt", self.revision_attempts.get(task, 0))

            print(f"Coder {self.unique_id} working on: {task}")
            if is_revision:
                print(f"  📝 Revision requested. Feedback: {feedback}")

            # FAILURE INJECTION: Ignore feedback with specified probability
            if is_revision and feedback == "Rejected":
                if random.random() < self.ignore_feedback_probability:
                    # MAJOR CHANGE: Signal this as an intentional failure
                    span.set_status(StatusCode.ERROR, "Intentionally ignoring feedback for experiment")
                    span.record_exception(
                        Exception(f"Coder {self.unique_id} intentionally ignoring Reviewer feedback")
                    )
                    span.set_attribute("failure.ignored_feedback", True)
                    span.set_attribute("failure.severity", "high")
                    span.set_attribute("task.output", previous_code)
                    span.set_attribute("task.status", "failed_ignored_feedback")
                    print(f"  🚨 Coder {self.unique_id} INTENTIONALLY IGNORED feedback")
                    return previous_code

            # Normal code generation (original logic)
            code = self._generate_code_based_on_task(task)

            # If this is a revision (but we didn't ignore), track the attempt
            if is_revision and feedback == "Rejected":
                self.revision_attempts[task] = self.revision_attempts.get(task, 0) + 1
                span.set_attribute("revision.attempt_count", self.revision_attempts[task])
                print(f"  ✅ Coder {self.unique_id} attempted revision")

            span.set_attribute("task.output", code)
            span.set_attribute("task.status", "completed")
            return code

    def _generate_code_based_on_task(self, task):
        """Original code generation logic extracted for clarity"""
        if "login" in task.lower():
            return self._generate_login_code()
        elif "payment" in task.lower():
            return self._generate_payment_code()
        elif "profile" in task.lower():
            return self._generate_profile_code()
        elif "security" in task.lower():
            return self._generate_security_code()
        else:
            return self._generate_generic_code(task)

    # ... keep all the existing code generation methods unchanged ...
    def _generate_login_code(self):
        implementations = [
            "def authenticate_user(username, password):\n    # TODO: Implement OAuth\n    return True",
            "class UserLogin:\n    def __init__(self):\n        self.oauth_provider = 'google'\n    def login(self, credentials):\n        return oauth.verify(credentials)",
            "async def handle_login(request):\n    token = await get_oauth_token()\n    return {'status': 'logged_in', 'token': token}"
        ]
        return random.choice(implementations)

    def _generate_payment_code(self):
        implementations = [
            "class PaymentProcessor:\n    def charge(self, amount, card):\n        # Stripe integration placeholder\n        return {'status': 'success', 'tx_id': 'ch_123'}",
            "def process_payment(amount, payment_method):\n    if payment_method == 'card':\n        return stripe.create_charge(amount)\n    raise ValueError('Unsupported payment method')"
        ]
        return random.choice(implementations)

    def _generate_profile_code(self):
        implementations = [
            "def create_profile(user_data):\n    profile = Profile.objects.create(**user_data)\n    if 'avatar' in user_data:\n        profile.avatar = process_avatar(user_data['avatar'])\n    profile.save()",
            "class ProfileManager:\n    def upload_avatar(self, file):\n        resized = resize_image(file)\n        return storage.upload(resized)"
        ]
        return random.choice(implementations)

    def _generate_security_code(self):
        implementations = [
            "def fix_vulnerability(vuln_id):\n    patch = SecurityPatch(vuln_id)\n    return patch.apply()",
            "class VulnerabilityScanner:\n    def scan_and_fix(self):\n        issues = scanner.detect()\n        for issue in issues:\n            issue.resolve()\n        return len(issues)"
        ]
        return random.choice(implementations)

    def _generate_generic_code(self, task):
        func_name = task.lower().replace(' ', '_').replace('-', '_')[:20]
        return f"def {func_name}():\n    \"\"\"{task}\"\"\"\n    # Implementation goes here\n    return True"