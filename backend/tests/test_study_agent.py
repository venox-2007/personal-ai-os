import pytest
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, AsyncMock

from app.core.config import settings
from app.integrations.embeddings.base import BaseEmbeddingProvider
from app.integrations.vector_store.base import BaseVectorStore
from app.tools.study.document_parser import DocumentParser, ParsedChunk
from app.tools.study.tools import (
    StudyIngestTool, StudySearchTool, StudyListDocumentsTool,
    StudyRemoveDocumentTool, StudyAskTool
)
from app.tools.local_file.sandbox import FileSandbox

class MockEmbeddingProvider(BaseEmbeddingProvider):
    def embed_text(self, text: str):
        return [0.1, 0.2, 0.3]
    def embed_batch(self, texts: list):
        return [[0.1, 0.2, 0.3] for _ in texts]

class MockVectorStore(BaseVectorStore):
    def __init__(self):
        self.docs = []
        self.metadata = []
        self.ids = []
        self.removed_called = False
    
    def add_documents(self, doc_ids, texts, embeddings, metadatas):
        self.ids.extend(doc_ids)
        self.docs.extend(texts)
        self.metadata.extend(metadatas)
        
    def search(self, query_embedding, top_k=5, filter_metadata=None):
        if not self.docs:
            return []
        res = []
        for i in range(min(top_k, len(self.docs))):
            res.append({
                "id": self.ids[i],
                "text": self.docs[i],
                "metadata": self.metadata[i],
                "distance": 0.1,
                "similarity": 0.9
            })
        return res
        
    def remove_document(self, doc_id):
        self.removed_called = True
        return True
        
    def list_documents(self):
        return [{"document_id": "test_id", "filename": "test.txt", "chunks": 2, "ingested_at": "now"}]

@pytest.fixture
def mock_study_tools(monkeypatch):
    mock_embed = MockEmbeddingProvider()
    mock_store = MockVectorStore()
    
    import app.tools.study.tools as tools_module
    monkeypatch.setattr(tools_module, "_embedding_provider", mock_embed)
    monkeypatch.setattr(tools_module, "_vector_store", mock_store)
    
    return mock_embed, mock_store

def test_document_parser_text():
    parser = DocumentParser(chunk_size=10, chunk_overlap=2)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test.txt"
        p.write_text("Hello world this is a test", encoding="utf-8")
        chunks = parser.parse_file(p, "doc1")
        assert len(chunks) > 1
        assert chunks[0].metadata["document_id"] == "doc1"
        assert chunks[0].metadata["filename"] == "test.txt"

@pytest.mark.asyncio
async def test_study_ingest_tool(mock_study_tools, monkeypatch):
    _, mock_store = mock_study_tools
    
    with tempfile.TemporaryDirectory() as td:
        # We need to temporarily add td to FILE_AGENT_ALLOWED_ROOTS for the sandbox to allow it
        original_roots = settings.FILE_AGENT_ALLOWED_ROOTS
        settings.FILE_AGENT_ALLOWED_ROOTS = td
        
        # We must re-init sandbox with the new roots for the test
        import app.tools.study.tools as tools_module
        test_sandbox = FileSandbox()
        monkeypatch.setattr(tools_module, "sandbox", test_sandbox)

        p = Path(td) / "test.txt"
        p.write_text("Test ingestion", encoding="utf-8")
        
        tool = StudyIngestTool()
        result = await tool.execute(file_path=str(p))
        
        assert result.success is True
        assert len(mock_store.docs) > 0
        assert mock_store.metadata[0]["filename"] == "test.txt"
        
        # Restore roots
        settings.FILE_AGENT_ALLOWED_ROOTS = original_roots

@pytest.mark.asyncio
async def test_study_search_tool(mock_study_tools):
    _, mock_store = mock_study_tools
    mock_store.docs = ["Some test content"]
    mock_store.metadata = [{"filename": "test.txt"}]
    mock_store.ids = ["id1"]
    
    tool = StudySearchTool()
    result = await tool.execute(query="test")
    
    assert result.success is True
    assert len(result.output["results"]) == 1
    assert result.output["results"][0]["text"] == "Some test content"

@pytest.mark.asyncio
async def test_study_ask_tool(mock_study_tools):
    _, mock_store = mock_study_tools
    mock_store.docs = ["Some test content"]
    mock_store.metadata = [{"filename": "test.txt", "page": 1}]
    mock_store.ids = ["id1"]
    
    class MockLLMResponse:
        content = "Based on [1], here is the answer."
        
    class MockLLMProvider:
        async def chat(self, messages, temperature=0.1):
            # Check prompt for grounding instructions
            prompt = messages[0]["content"]
            assert "Do NOT invent facts" in prompt
            return MockLLMResponse()
            
    class MockContext:
        llm_provider = MockLLMProvider()
        
    tool = StudyAskTool()
    result = await tool.execute(question="test question?", context=MockContext())
    
    assert result.success is True
    assert "Based on [1]" in result.output["answer"]
    assert len(result.output["sources"]) == 1
    assert result.output["sources"][0]["metadata"]["filename"] == "test.txt"
