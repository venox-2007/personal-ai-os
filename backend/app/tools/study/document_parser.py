import os
from pathlib import Path
from typing import Dict, Any, List

class ParsedChunk:
    def __init__(self, text: str, metadata: Dict[str, Any]):
        self.text = text
        self.metadata = metadata

class DocumentParser:
    """Extracts text from documents and splits into chunks."""
    
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _chunk_text(self, text: str, base_metadata: Dict[str, Any]) -> List[ParsedChunk]:
        """Simple token/character-based chunking."""
        # For simplicity, we chunk by character count, respecting word boundaries if possible.
        # A more advanced chunker would use tiktoken or sentence boundaries.
        chunks = []
        start = 0
        text_len = len(text)
        chunk_index = 0
        
        while start < text_len:
            end = start + self.chunk_size
            if end < text_len:
                # Try to find a space to split on
                space_idx = text.rfind(' ', start, end)
                if space_idx != -1 and space_idx > start + (self.chunk_size // 2):
                    end = space_idx
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                meta = base_metadata.copy()
                meta["chunk_index"] = chunk_index
                chunks.append(ParsedChunk(chunk_text, meta))
                chunk_index += 1
                
            start = end - self.chunk_overlap
            if start < 0:
                start = end  # Prevent infinite loop if overlap is larger than size
                
        return chunks

    def parse_file(self, file_path: Path, document_id: str) -> List[ParsedChunk]:
        """Extracts text based on file extension and chunks it."""
        ext = file_path.suffix.lower()
        filename = file_path.name
        
        base_meta = {
            "document_id": document_id,
            "filename": filename,
            "extension": ext
        }
        
        if ext in ['.txt', '.md', '.csv']:
            return self._parse_text(file_path, base_meta)
        elif ext == '.pdf':
            return self._parse_pdf(file_path, base_meta)
        elif ext == '.docx':
            return self._parse_docx(file_path, base_meta)
        elif ext == '.pptx':
            return self._parse_pptx(file_path, base_meta)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _parse_text(self, file_path: Path, base_meta: Dict[str, Any]) -> List[ParsedChunk]:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        return self._chunk_text(text, base_meta)
        
    def _parse_pdf(self, file_path: Path, base_meta: Dict[str, Any]) -> List[ParsedChunk]:
        import pypdf
        chunks = []
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    meta = base_meta.copy()
                    meta["page"] = i + 1
                    page_chunks = self._chunk_text(text, meta)
                    chunks.extend(page_chunks)
        return chunks

    def _parse_docx(self, file_path: Path, base_meta: Dict[str, Any]) -> List[ParsedChunk]:
        import docx
        doc = docx.Document(file_path)
        full_text = "\n".join([para.text for para in doc.paragraphs if para.text])
        return self._chunk_text(full_text, base_meta)

    def _parse_pptx(self, file_path: Path, base_meta: Dict[str, Any]) -> List[ParsedChunk]:
        import pptx
        prs = pptx.Presentation(file_path)
        chunks = []
        for i, slide in enumerate(prs.slides):
            text_runs = []
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text_runs.append(shape.text)
            text = "\n".join(text_runs)
            if text.strip():
                meta = base_meta.copy()
                meta["slide"] = i + 1
                slide_chunks = self._chunk_text(text, meta)
                chunks.extend(slide_chunks)
        return chunks
