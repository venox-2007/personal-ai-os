from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseVectorStore(ABC):
    """Abstract base class for vector databases."""
    
    @abstractmethod
    def add_documents(
        self, 
        doc_ids: List[str], 
        texts: List[str], 
        embeddings: List[List[float]], 
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """Adds embedded documents and their metadata to the store."""
        pass
        
    @abstractmethod
    def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Searches for similar vectors and returns metadata and texts."""
        pass
        
    @abstractmethod
    def remove_document(self, doc_id: str) -> bool:
        """Removes all chunks associated with a specific document ID."""
        pass
        
    @abstractmethod
    def list_documents(self) -> List[Dict[str, Any]]:
        """Returns a summary of all unique documents currently indexed."""
        pass
