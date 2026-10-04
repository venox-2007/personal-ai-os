import React, { useState, useEffect } from "react";
import { GraduationCap, Upload, Search, Trash2, HelpCircle, Book, AlertTriangle } from "lucide-react";
import { studyIngest, studyListDocuments, studyRemoveDocument, studySearch, studyAsk } from "../api/client";

export const StudyView: React.FC = () => {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [ingestPath, setIngestPath] = useState("");
  const [ingestStatus, setIngestStatus] = useState<{ loading: boolean; error?: string; success?: string }>({ loading: false });
  
  const [query, setQuery] = useState("");
  const [searchMode, setSearchMode] = useState<"search" | "ask">("ask");
  const [results, setResults] = useState<any>(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setLoadingDocs(true);
    try {
      const res = await studyListDocuments();
      setDocuments(res.documents || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleIngest = async () => {
    if (!ingestPath.trim()) return;
    setIngestStatus({ loading: true });
    try {
      const res = await studyIngest(ingestPath);
      setIngestStatus({ loading: false, success: `Ingested ${res.chunks_indexed} chunks from ${res.filename}` });
      setIngestPath("");
      fetchDocuments();
    } catch (err: any) {
      setIngestStatus({ loading: false, error: err.message });
    }
  };

  const handleRemove = async (id: string) => {
    if (!confirm("Are you sure you want to remove this document and its embeddings?")) return;
    try {
      await studyRemoveDocument(id);
      fetchDocuments();
    } catch (err: any) {
      alert("Error removing document: " + err.message);
    }
  };

  const handleQuery = async () => {
    if (!query.trim()) return;
    setQueryLoading(true);
    setQueryError(null);
    setResults(null);
    try {
      if (searchMode === "search") {
        const res = await studySearch(query);
        setResults({ type: "search", data: res.results });
      } else {
        const res = await studyAsk(query);
        setResults({ type: "ask", answer: res.answer, sources: res.sources });
      }
    } catch (err: any) {
      setQueryError(err.message);
    } finally {
      setQueryLoading(false);
    }
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto bg-background flex flex-col">
      <div className="max-w-6xl mx-auto w-full space-y-6 flex-1 flex flex-col">
        
        {/* Header */}
        <div className="p-6 bg-surface border border-surface-border rounded-xl flex items-start gap-4 shrink-0">
          <div className="w-12 h-12 rounded-xl bg-brand-600/20 text-brand-400 flex items-center justify-center shrink-0">
            <GraduationCap className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-slate-100">Study & Knowledge Agent</h2>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Upload documents to your local vector store and ask questions grounded entirely in your material.
            </p>
          </div>
        </div>

        <div className="flex gap-6 flex-1 min-h-0">
          
          {/* Left Panel - Document Management */}
          <div className="w-1/3 flex flex-col gap-6 overflow-y-auto">
            {/* Ingestion */}
            <div className="p-4 bg-surface border border-surface-border rounded-xl">
              <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                <Upload className="w-4 h-4 text-brand-400" />
                Ingest Document
              </h3>
              <div className="space-y-3">
                <input 
                  type="text" 
                  placeholder="Absolute file path (e.g. C:/notes/OS.pdf)"
                  value={ingestPath}
                  onChange={e => setIngestPath(e.target.value)}
                  className="w-full bg-background border border-surface-border rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500"
                />
                <button 
                  onClick={handleIngest}
                  disabled={ingestStatus.loading || !ingestPath}
                  className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white px-4 py-2 rounded text-sm transition-colors"
                >
                  {ingestStatus.loading ? "Ingesting..." : "Ingest"}
                </button>
                {ingestStatus.error && (
                  <div className="text-xs text-red-400 bg-red-400/10 p-2 rounded border border-red-400/20">
                    {ingestStatus.error}
                  </div>
                )}
                {ingestStatus.success && (
                  <div className="text-xs text-emerald-400 bg-emerald-400/10 p-2 rounded border border-emerald-400/20">
                    {ingestStatus.success}
                  </div>
                )}
              </div>
            </div>

            {/* Document List */}
            <div className="p-4 bg-surface border border-surface-border rounded-xl flex-1 flex flex-col min-h-0">
              <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                <Book className="w-4 h-4 text-brand-400" />
                Indexed Documents ({documents.length})
              </h3>
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {loadingDocs ? (
                  <div className="text-xs text-slate-500">Loading...</div>
                ) : documents.length === 0 ? (
                  <div className="text-xs text-slate-500">No documents ingested.</div>
                ) : (
                  documents.map((doc) => (
                    <div key={doc.document_id} className="bg-surface-secondary border border-surface-border p-3 rounded-lg group">
                      <div className="flex justify-between items-start">
                        <div className="truncate flex-1">
                          <p className="text-sm font-medium text-slate-200 truncate" title={doc.filename}>{doc.filename}</p>
                          <p className="text-[10px] text-slate-500 mt-1">Chunks: {doc.chunks} • {doc.ingested_at}</p>
                        </div>
                        <button 
                          onClick={() => handleRemove(doc.document_id)}
                          className="opacity-0 group-hover:opacity-100 p-1.5 text-red-400 hover:bg-red-400/20 rounded transition-all"
                          title="Remove Document"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Right Panel - Search & Ask */}
          <div className="flex-1 bg-surface border border-surface-border rounded-xl flex flex-col min-h-0">
            <div className="p-4 border-b border-surface-border">
              <div className="flex items-center gap-2 mb-4">
                <button 
                  onClick={() => setSearchMode("ask")}
                  className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${searchMode === "ask" ? "bg-brand-600 text-white" : "bg-surface-secondary text-slate-400 hover:text-slate-200"}`}
                >
                  Ask Question
                </button>
                <button 
                  onClick={() => setSearchMode("search")}
                  className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${searchMode === "search" ? "bg-brand-600 text-white" : "bg-surface-secondary text-slate-400 hover:text-slate-200"}`}
                >
                  Semantic Search
                </button>
              </div>
              <div className="flex gap-2">
                <input 
                  type="text" 
                  placeholder={searchMode === "ask" ? "Ask a question about your study material..." : "Search for concepts in your notes..."}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleQuery()}
                  className="flex-1 bg-background border border-surface-border rounded px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500"
                />
                <button 
                  onClick={handleQuery}
                  disabled={queryLoading || !query}
                  className="bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white px-4 py-2 rounded flex items-center gap-2 text-sm transition-colors"
                >
                  {searchMode === "ask" ? <HelpCircle className="w-4 h-4" /> : <Search className="w-4 h-4" />}
                  {queryLoading ? "Running..." : "Run"}
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 bg-background/50">
              {queryError && (
                <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-lg flex items-start gap-3">
                  <AlertTriangle className="text-red-400 w-5 h-5 shrink-0" />
                  <span className="text-red-200 text-sm">{queryError}</span>
                </div>
              )}
              
              {!queryError && !results && !queryLoading && (
                <div className="h-full flex flex-col items-center justify-center text-slate-500">
                  <GraduationCap className="w-12 h-12 mb-4 opacity-20" />
                  <p className="text-sm">Enter a query to explore your study material.</p>
                </div>
              )}

              {queryLoading && (
                <div className="text-sm text-slate-500 animate-pulse">Processing query through local models...</div>
              )}

              {results?.type === "ask" && (
                <div className="space-y-6">
                  <div className="bg-surface p-5 rounded-xl border border-surface-border">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></div>
                      <h4 className="text-sm font-semibold text-slate-200">Grounded Answer</h4>
                    </div>
                    <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                      {results.answer}
                    </div>
                  </div>
                  
                  {results.sources?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Context Sources</h4>
                      <div className="space-y-3">
                        {results.sources.map((src: any) => (
                          <div key={src.id} className="bg-surface-secondary border border-surface-border p-4 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs font-semibold text-brand-400">[{src.id}] {src.filename}</span>
                              <span className="text-[10px] text-slate-500 font-mono">
                                {src.metadata.page ? `Page ${src.metadata.page}` : src.metadata.slide ? `Slide ${src.metadata.slide}` : `Chunk ${src.metadata.chunk_index}`}
                              </span>
                            </div>
                            <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">{src.text}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {results?.type === "search" && (
                <div className="space-y-4">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Search Results ({results.data.length})</h4>
                  {results.data.map((res: any) => (
                    <div key={res.id} className="bg-surface border border-surface-border p-4 rounded-xl">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-slate-200">{res.metadata.filename}</span>
                        <div className="flex items-center gap-3">
                           <span className="text-[10px] text-slate-400 bg-surface-secondary px-2 py-0.5 rounded border border-surface-border font-mono">
                            {res.metadata.page ? `Pg ${res.metadata.page}` : res.metadata.slide ? `Sl ${res.metadata.slide}` : `Ch ${res.metadata.chunk_index}`}
                           </span>
                           <span className="text-xs text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full border border-emerald-400/20">
                            {Math.round(res.similarity * 100)}% Match
                           </span>
                        </div>
                      </div>
                      <p className="text-sm text-slate-400 leading-relaxed whitespace-pre-wrap">{res.text}</p>
                    </div>
                  ))}
                  {results.data.length === 0 && (
                    <div className="text-sm text-slate-500">No semantic matches found.</div>
                  )}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
