from abc import ABC, abstractmethod
from typing import List

class BaseEmbeddingProvider(ABC):
    """Abstract base class for generating text embeddings."""
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embeds a single piece of text into a vector."""
        pass
        
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of texts into vectors."""
        pass
