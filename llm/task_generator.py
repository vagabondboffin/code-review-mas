import os
from openai import OpenAI
from dotenv import load_dotenv
import random

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class TaskGenerator:
    def __init__(self, model="gpt-4o"):
        self.model = model
        self.task_types = [
            "authentication system",
            "payment processing",
            "user profile management",
            "data storage solution",
            "API endpoint",
            "security feature",
            "notification service",
            "performance optimization"
        ]

    def generate_task(self, temperature=0.7) -> str:
        """Generate a backend feature request using LLM"""
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "You are a product manager creating technical requirements for software engineers."},
                    {"role": "user",
                     "content": f"Generate a specific backend feature request for a {random.choice(self.task_types)}. Use technical language and include 1-2 key requirements."}
                ],
                temperature=temperature,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            return self._manual_task_generation()


    def _manual_task_generation(self) -> str:
        """Fallback task generation if API fails"""
        features = [
            "Implement JWT-based authentication with refresh tokens",
            "Create Stripe integration for recurring payments",
            "Add user profile picture upload with S3 storage",
            "Implement Redis caching for database queries",
            "Add rate limiting to API endpoints",
            "Create audit logging for security-sensitive operations"
        ]
        return random.choice(features)