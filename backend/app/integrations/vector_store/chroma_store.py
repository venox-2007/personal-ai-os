import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.integrations.vector_store.base import BaseVectorStore
from app.core.config import settings

logger = logging.getLogger(__name__)

class ChromaVectorStore(BaseVectorStore):
    """Local vector store using ChromaDB."""
    
    def __init__(self, collection_name: str = "study_material"):
        self.collection_name = collection_name
        self.persist_dir = Path(settings.STUDY_STORAGE_DIR) / "chroma"
        self._client = None
        self._collection = None
        
    @property
    def client(self):
        if self._client is None:
            try:
                import chromadb
                # Ensure directory exists securely
                os.makedirs(str(self.persist_dir), exist_ok=True)
                self._client = chromadb.PersistentClient(path=str(self.persist_dir))
                self._collection = self._client.get_or_create_collection(name=self.collection_name)
            except ImportError:
                logger.error("Failed to import chromadb. Ensure it is installed.")
                raise
        return self._client
        
    @property
    def collection(self):
        if self._collection is None:
            self.client # Initialize client which sets collection
        return self._collection

    def add_documents(
        self, 
        doc_ids: List[str], 
        texts: List[str], 
        embeddings: List[List[float]], 
        metadatas: List[Dict[str, Any]]
    ) -> None:
        if not doc_ids:
            return
            
        # Chroma requires unique IDs for every chunk, not just the document ID.
        # We assume doc_ids here are unique chunk IDs (e.g. "doc123_chunk1")
        # Ensure metadata has string/int/float types only for Chroma
        sanitized_metadatas = []
        for meta in metadatas:
            safe_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    safe_meta[k] = v
                elif v is None:
                    safe_meta[k] = ""
                else:
                    safe_meta[k] = str(v)
            sanitized_metadatas.append(safe_meta)
            
        self.collection.add(
            ids=doc_ids,
            embeddings=embeddings,
            metadatas=sanitized_metadatas,
            documents=texts
        )
        logger.info(f"Added {len(doc_ids)} chunks to Chroma vector store.")

    def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        # Handle optional metadata filtering (basic equality)
        where_clause = filter_metadata if filter_metadata else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
            include=["metadatas", "documents", "distances"]
        )
        
        formatted_results = []
        if results and results["ids"] and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                # Check for empty lists to prevent index errors
                doc_text = results["documents"][0][i] if results.get("documents") and results["documents"][0] else ""
                meta = results["metadatas"][0][i] if results.get("metadatas") and results["metadatas"][0] else {}
                distance = results["distances"][0][i] if results.get("distances") and results["distances"][0] else 0.0
                
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": doc_text,
                    "metadata": meta,
                    "distance": distance,
                    "similarity": 1.0 - min(distance, 1.0) # Very rough similarity metric based on distance
                })
        return formatted_results

    def remove_document(self, doc_id: str) -> bool:
        """Removes all chunks belonging to a document ID."""
        try:
            # We assume metadata contains "document_id"
            self.collection.delete(where={"document_id": doc_id})
            logger.info(f"Removed document {doc_id} from vector store.")
            return True
        except Exception as e:
            logger.error(f"Error removing document {doc_id}: {e}")
            return False

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        Lists unique documents by getting all metadata.
        For large collections this might be slow, but suitable for personal AI scale.
        """
        try:
            data = self.collection.get(include=["metadatas"])
            docs = {}
            if data and data["metadatas"]:
                for meta in data["metadatas"]:
                    if not meta: continue
                    doc_id = meta.get("document_id")
                    if doc_id and doc_id not in docs:
                        docs[doc_id] = {
                            "document_id": doc_id,
                            "filename": meta.get("filename", "Unknown"),
                            "chunks": 1,
                            "ingested_at": meta.get("ingested_at", "")
                        }
                    elif doc_id:
                        docs[doc_id]["chunks"] += 1
            return list(docs.values())
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
