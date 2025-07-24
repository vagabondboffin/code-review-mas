from tracing.setup_tracer import tracer
import random


class CoderAgent:
    def __init__(self, unique_id, model):
        self.unique_id = unique_id
        self.model = model
        self.role = "Coder"

    def step(self, task=None):
        if task is None:
            raise ValueError("Coder requires a task")

        with tracer.start_as_current_span("CoderAgent.step") as span:
            span.set_attribute("agent.id", self.unique_id)
            span.set_attribute("agent.role", self.role)
            span.set_attribute("task.input", task)

            print(f"Coder {self.unique_id} working on: {task}")

            # Generate realistic code based on task
            if "login" in task.lower():
                code = self._generate_login_code()
            elif "payment" in task.lower():
                code = self._generate_payment_code()
            elif "profile" in task.lower():
                code = self._generate_profile_code()
            elif "security" in task.lower():
                code = self._generate_security_code()
            else:
                code = self._generate_generic_code(task)

            span.set_attribute("task.output", code)
            span.set_attribute("task.status", "completed")

            return code

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
        # Convert task to function name
        func_name = task.lower().replace(' ', '_').replace('-', '_')[:20]
        return f"def {func_name}():\n    \"\"\"{task}\"\"\"\n    # Implementation goes here\n    return True"