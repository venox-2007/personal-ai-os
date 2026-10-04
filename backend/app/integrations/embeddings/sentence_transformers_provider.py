from typing import List
import logging
from app.integrations.embeddings.base import BaseEmbeddingProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class SentenceTransformersProvider(BaseEmbeddingProvider):
    """Local embedding provider using sentence-transformers (HuggingFace)."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.STUDY_EMBEDDING_MODEL
        self._model = None
        
    @property
    def model(self):
        # Lazy load the model to save memory/startup time if not used
        if self._model is None:
            logger.info(f"Loading local embedding model: {self.model_name}")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                logger.error("Failed to import sentence_transformers. Ensure it is installed.")
                raise
        return self._model
        
    def embed_text(self, text: str) -> List[float]:
        if not text.strip():
            return []
        # encode returns numpy array, convert to list
        vector = self.model.encode(text).tolist()
        return vector
        
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors = self.model.encode(texts).tolist()
        return vectors
