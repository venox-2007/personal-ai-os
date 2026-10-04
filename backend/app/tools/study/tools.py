import os
import uuid
import time
from pathlib import Path
from typing import Dict, Any, List

from app.tools.base import BaseTool, ToolResult, PermissionLevel
from app.core.config import settings
from app.core.logging import logger
from app.tools.local_file.sandbox import sandbox

from app.integrations.embeddings.sentence_transformers_provider import SentenceTransformersProvider
from app.integrations.vector_store.chroma_store import ChromaVectorStore
from app.tools.study.document_parser import DocumentParser

# Global singletons for tools
_embedding_provider = SentenceTransformersProvider()
_vector_store = ChromaVectorStore()

class StudyIngestTool(BaseTool):
    name: str = "study_ingest_document"
    description: str = "Ingest a document into the study vector store (PDF, TXT, MD, DOCX, PPTX)."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_1_LOW_IMPACT
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path to the file to ingest."
            }
        },
        "required": ["file_path"]
    }
        
    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        if not file_path:
            return ToolResult(success=False, error="Missing required argument: file_path.")
            
        try:
            # Reusing sandbox rules to safely access files
            safe_path = sandbox.get_safe_path(file_path)
            if not safe_path.is_file():
                return ToolResult(success=False, error=f"Path is not a file or does not exist: {file_path}")
            
            # Check file size (50MB default)
            stats = safe_path.stat()
            max_bytes = settings.STUDY_MAX_DOC_SIZE_MB * 1024 * 1024
            if stats.st_size > max_bytes:
                return ToolResult(success=False, error=f"File exceeds maximum size of {settings.STUDY_MAX_DOC_SIZE_MB}MB.")
                
            doc_id = str(uuid.uuid4())
            parser = DocumentParser(
                chunk_size=settings.STUDY_CHUNK_SIZE,
                chunk_overlap=settings.STUDY_CHUNK_OVERLAP
            )
            
            chunks = parser.parse_file(safe_path, doc_id)
            if not chunks:
                return ToolResult(success=False, error="No text could be extracted from the document.")
                
            texts = [c.text for c in chunks]
            metadatas = [c.metadata for c in chunks]
            
            # Add ingestion timestamp
            ingest_time = time.ctime()
            for meta in metadatas:
                meta["ingested_at"] = ingest_time
                
            chunk_ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
            
            # Embed
            embeddings = _embedding_provider.embed_batch(texts)
            
            # Persist
            _vector_store.add_documents(chunk_ids, texts, embeddings, metadatas)
            
            return ToolResult(success=True, output={
                "document_id": doc_id,
                "filename": safe_path.name,
                "chunks_indexed": len(chunks),
                "ingested_at": ingest_time
            })
            
        except Exception as e:
            logger.error(f"Error in study_ingest_document: {e}")
            return ToolResult(success=False, error=f"Ingestion failed: {str(e)}")


class StudySearchTool(BaseTool):
    name: str = "study_search"
    description: str = "Semantic search over ingested study material."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query or concept to find."
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default 5)."
            }
        },
        "required": ["query"]
    }
        
    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        top_k = kwargs.get("top_k", settings.STUDY_RETRIEVAL_TOP_K)
        
        if not query:
            return ToolResult(success=False, error="Missing required argument: query.")
            
        try:
            query_embedding = _embedding_provider.embed_text(query)
            if not query_embedding:
                return ToolResult(success=False, error="Failed to generate embedding for query.")
                
            results = _vector_store.search(query_embedding, top_k=top_k)
            
            return ToolResult(success=True, output={"results": results})
        except Exception as e:
            logger.error(f"Error in study_search: {e}")
            return ToolResult(success=False, error=f"Search failed: {str(e)}")


class StudyListDocumentsTool(BaseTool):
    name: str = "study_list_documents"
    description: str = "List all documents currently ingested in the study vector store."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {}
    }
        
    async def execute(self, **kwargs) -> ToolResult:
        try:
            docs = _vector_store.list_documents()
            return ToolResult(success=True, output={"documents": docs, "count": len(docs)})
        except Exception as e:
            logger.error(f"Error in study_list_documents: {e}")
            return ToolResult(success=False, error=f"List failed: {str(e)}")


class StudyRemoveDocumentTool(BaseTool):
    name: str = "study_remove_document"
    description: str = "Remove a document and its vectors from the study store."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_3_DESTRUCTIVE
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "string",
                "description": "The unique ID of the document to remove."
            }
        },
        "required": ["document_id"]
    }
        
    async def execute(self, **kwargs) -> ToolResult:
        doc_id = kwargs.get("document_id")
        if not doc_id:
            return ToolResult(success=False, error="Missing required argument: document_id.")
            
        try:
            success = _vector_store.remove_document(doc_id)
            if success:
                return ToolResult(success=True, output={"status": "removed", "document_id": doc_id})
            else:
                return ToolResult(success=False, error="Failed to remove document, it may not exist.")
        except Exception as e:
            logger.error(f"Error in study_remove_document: {e}")
            return ToolResult(success=False, error=f"Remove failed: {str(e)}")

class StudyAskTool(BaseTool):
    name: str = "study_ask"
    description: str = "Ask a question about your study material. Automatically retrieves context and generates a grounded answer."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to ask."
            }
        },
        "required": ["question"]
    }
        
    async def execute(self, **kwargs) -> ToolResult:
        question = kwargs.get("question")
        context = kwargs.get("context", None)
        
        if not question:
            return ToolResult(success=False, error="Missing required argument: question.")
            
        if not context or not hasattr(context, "llm_provider"):
            return ToolResult(success=False, error="LLM provider not available in context.")
            
        try:
            # Retrieve chunks
            query_embedding = _embedding_provider.embed_text(question)
            results = _vector_store.search(query_embedding, top_k=settings.STUDY_RETRIEVAL_TOP_K)
            
            if not results:
                return ToolResult(success=True, output={
                    "answer": "I don't have any study material to answer that question. Please ingest some documents first.",
                    "sources": []
                })
                
            # Construct context
            context_text = ""
            sources = []
            for i, res in enumerate(results):
                idx = i + 1
                meta = res["metadata"]
                filename = meta.get("filename", "Unknown Document")
                page_info = f"Page {meta.get('page')}" if "page" in meta else (f"Slide {meta.get('slide')}" if "slide" in meta else f"Chunk {meta.get('chunk_index')}")
                
                source_citation = f"[{idx}] {filename} - {page_info}"
                sources.append({
                    "id": idx,
                    "filename": filename,
                    "metadata": meta,
                    "text": res["text"]
                })
                
                context_text += f"\n--- Source {idx} ---\nMetadata: {filename}, {page_info}\nContent:\n{res['text']}\n"
                
            # Ask LLM
            prompt = f"""You are a strict, helpful study assistant. 
Answer the user's question using ONLY the provided study material context.
If the provided context is insufficient to fully answer the question, clearly state that you do not have enough information in the study material.
Do NOT invent facts. Do NOT rely on your general knowledge if it contradicts or isn't present in the context.

When you use information from the context, cite the source using brackets like [1], [2], etc., corresponding to the Source number provided.

Context:
{context_text}

User Question: {question}
"""
            messages = [{"role": "user", "content": prompt}]
            
            response = await context.llm_provider.chat(
                messages=messages,
                temperature=0.1
            )
            
            return ToolResult(success=True, output={
                "answer": response.content,
                "sources": sources
            })
            
        except Exception as e:
            logger.error(f"Error in study_ask: {e}")
            return ToolResult(success=False, error=f"Ask failed: {str(e)}")

