from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re


class SimilarityCalculator:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def calculate_similarity(self, task: str, code: str) -> float:
        # Preprocess code - remove comments and special characters
        clean_code = re.sub(r'#.*|\/\/.*|\/\*.*?\*\/', '', code, flags=re.DOTALL)
        clean_code = re.sub(r'\s+', ' ', clean_code).strip()

        # Preprocess task - remove ambiguity markers
        clean_task = task
        for phrase in [
            "using appropriate methods", "with proper implementation",
            "following best practices", "in a scalable way"
        ]:
            clean_task = clean_task.replace(phrase, '')
        clean_task = re.sub(r'\s+', ' ', clean_task).strip()

        # Calculate embeddings
        embeddings = self.model.encode([clean_task, clean_code])
        return max(0, cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])