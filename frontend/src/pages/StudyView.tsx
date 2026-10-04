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
    <div className="flex-1 p-8 overflow-y-auto bg-slate-50/50 flex flex-col">
      <div className="max-w-6xl mx-auto w-full space-y-6 flex-1 flex flex-col">
        
        {/* Header */}
        <div className="p-6 bg-white border border-slate-200 rounded-xl flex items-start gap-4 shrink-0">
          <div className="w-12 h-12 rounded-xl bg-brand-600/20 text-brand-600 flex items-center justify-center shrink-0">
            <GraduationCap className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-slate-800">Study & Knowledge Agent</h2>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Upload documents to your local vector store and ask questions grounded entirely in your material.
            </p>
          </div>
        </div>

        <div className="flex gap-6 flex-1 min-h-0">
          
          {/* Left Panel - Document Management */}
          <div className="w-1/3 flex flex-col gap-6 overflow-y-auto">
            {/* Ingestion */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <h3 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <Upload className="w-4 h-4 text-brand-600" />
                Ingest Document
              </h3>
              <div className="space-y-3">
                <input 
                  type="text" 
                  placeholder="Absolute file path (e.g. C:/notes/OS.pdf)"
                  value={ingestPath}
                  onChange={e => setIngestPath(e.target.value)}
                  className="w-full bg-slate-50/50 border border-slate-200 rounded px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-brand-500"
                />
                <button 
                  onClick={handleIngest}
                  disabled={ingestStatus.loading || !ingestPath}
                  className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white px-4 py-2 rounded text-sm transition-colors"
                >
                  {ingestStatus.loading ? "Ingesting..." : "Ingest"}
                </button>
                {ingestStatus.error && (
                  <div className="text-xs text-red-600 bg-red-400/10 p-2 rounded border border-red-400/20">
                    {ingestStatus.error}
                  </div>
                )}
                {ingestStatus.success && (
                  <div className="text-xs text-emerald-700 bg-emerald-50 p-2 rounded border border-emerald-200">
                    {ingestStatus.success}
                  </div>
                )}
              </div>
            </div>

            {/* Document List */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl flex-1 flex flex-col min-h-0">
              <h3 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <Book className="w-4 h-4 text-brand-600" />
                Indexed Documents ({documents.length})
              </h3>
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {loadingDocs ? (
                  <div className="text-xs text-slate-500">Loading...</div>
                ) : documents.length === 0 ? (
                  <div className="text-xs text-slate-500">No documents ingested.</div>
                ) : (
                  documents.map((doc) => (
                    <div key={doc.document_id} className="bg-slate-50 border border-slate-200 p-3 rounded-lg group">
                      <div className="flex justify-between items-start">
                        <div className="truncate flex-1">
                          <p className="text-sm font-medium text-slate-800 truncate" title={doc.filename}>{doc.filename}</p>
                          <p className="text-[10px] text-slate-500 mt-1 font-mono">Chunks: {doc.chunks} • {doc.ingested_at}</p>
                        </div>
                        <button 
                          onClick={() => handleRemove(doc.document_id)}
                          className="opacity-0 group-hover:opacity-100 p-1.5 text-red-500 hover:bg-red-50 rounded transition-all"
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
          <div className="flex-1 bg-white border border-slate-200 rounded-2xl flex flex-col min-h-0 shadow-sm">
            <div className="p-5 border-b border-slate-200">
              <div className="flex items-center gap-2 mb-4">
                <button 
                  onClick={() => setSearchMode("ask")}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${searchMode === "ask" ? "bg-brand-50 text-brand-700" : "bg-white text-slate-500 hover:bg-slate-50"}`}
                >
                  Ask Question
                </button>
                <button 
                  onClick={() => setSearchMode("search")}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${searchMode === "search" ? "bg-brand-50 text-brand-700" : "bg-white text-slate-500 hover:bg-slate-50"}`}
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
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
                />
                <button 
                  onClick={handleQuery}
                  disabled={queryLoading || !query}
                  className="bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl flex items-center gap-2 text-sm font-medium transition-colors"
                >
                  {searchMode === "ask" ? <HelpCircle className="w-4 h-4" /> : <Search className="w-4 h-4" />}
                  {queryLoading ? "Running..." : "Run"}
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50">
              {queryError && (
                <div className="bg-red-50 border border-red-100 p-4 rounded-xl flex items-start gap-3">
                  <AlertTriangle className="text-red-500 w-5 h-5 shrink-0" />
                  <span className="text-red-700 text-sm">{queryError}</span>
                </div>
              )}
              
              {!queryError && !results && !queryLoading && (
                <div className="h-full flex flex-col items-center justify-center text-slate-500">
                  <GraduationCap className="w-12 h-12 mb-4 text-slate-700" />
                  <p className="text-sm font-medium">Enter a query to explore your study material.</p>
                </div>
              )}

              {queryLoading && (
                <div className="text-sm text-brand-600 font-medium animate-pulse flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin"></div>
                  Processing query...
                </div>
              )}

              {results?.type === "ask" && (
                <div className="space-y-6">
                  <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-2 h-2 rounded-full bg-brand-500"></div>
                      <h4 className="text-sm font-semibold text-slate-800">Grounded Answer</h4>
                    </div>
                    <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                      {results.answer}
                    </div>
                  </div>
                  
                  {results.sources?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Context Sources</h4>
                      <div className="space-y-3">
                        {results.sources.map((src: any) => (
                          <div key={src.id} className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs font-semibold text-brand-600">[{src.id}] {src.filename}</span>
                              <span className="text-[10px] text-slate-500 font-mono bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                                {src.metadata.page ? `Page ${src.metadata.page}` : src.metadata.slide ? `Slide ${src.metadata.slide}` : `Chunk ${src.metadata.chunk_index}`}
                              </span>
                            </div>
                            <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">{src.text}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {results?.type === "search" && (
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Search Results ({results.data.length})</h4>
                  {results.data.map((res: any) => (
                    <div key={res.id} className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-slate-800">{res.metadata.filename}</span>
                        <div className="flex items-center gap-3">
                           <span className="text-[10px] text-slate-500 bg-slate-50 px-2 py-1 rounded-md border border-slate-100 font-mono">
                            {res.metadata.page ? `Pg ${res.metadata.page}` : res.metadata.slide ? `Sl ${res.metadata.slide}` : `Ch ${res.metadata.chunk_index}`}
                           </span>
                           <span className="text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-100">
                            {Math.round(res.similarity * 100)}% Match
                           </span>
                        </div>
                      </div>
                      <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">{res.text}</p>
                    </div>
                  ))}
                  {results.data.length === 0 && (
                    <div className="text-sm text-slate-500 text-center py-8">No semantic matches found.</div>
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
