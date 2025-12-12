"""Semantic similarity-based scenario matcher using sentence transformers."""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Tuple


class ScenarioMatcher:
    """Matches queries against scenarios using semantic similarity."""
    
    def __init__(self, scenarios: List[str], model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the scenario matcher.
        
        Args:
            scenarios: List of scenario descriptions to match against
            model_name: Name of the sentence transformer model to use
        """
        self.model = SentenceTransformer(model_name)
        self.scenarios = scenarios
        
        # Pre-encode all scenarios for efficient matching
        self.emb = self.model.encode(
            scenarios,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
    
    def match(self, query: str, k: int = 5, min_score: float = 0.35) -> List[Tuple[str, float]]:
        """
        Match a query against scenarios using semantic similarity.
        
        Args:
            query: The query text to match
            k: Number of top matches to return
            min_score: Minimum similarity score threshold (0-1)
        
        Returns:
            List of tuples (scenario, score) sorted by score descending.
            Returns empty list if best match is below min_score.
            Only returns results with scores >= min_score.
        """
        # Encode the query
        q = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        
        # Calculate cosine similarity
        scores = cosine_similarity(q, self.emb)[0]
        
        # Get top k indices
        top_idx = np.argsort(scores)[::-1][:k]
        
        # Build results list and filter by min_score
        results = []
        for i in top_idx:
            score = float(scores[i])
            if score >= min_score:
                results.append((self.scenarios[i], score))
        
        # Reject if nothing is really relevant (best score check)
        if not results:
            return []
        
        best_score = results[0][1]
        if best_score < min_score:
            return []
        
        return results

