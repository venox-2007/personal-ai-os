import React, { useState, useEffect } from "react";
import { Upload, Search, FileText, HelpCircle, AlertTriangle, Trash2, Loader2, GraduationCap, Sparkles } from "lucide-react";
import { 
  studyListDocuments, 
  studyIngest, 
  studyRemoveDocument, 
  studyAsk,
  studySearch
} from "../api/client";
import { motion, AnimatePresence } from "framer-motion";

export const StudyView: React.FC = () => {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState("");
  const [searchMode, setSearchMode] = useState<"ask" | "search">("ask");
  
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [results, setResults] = useState<any | null>(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setLoadingDocs(true);
    try {
      const docs = await studyListDocuments();
      setDocuments(docs);
    } catch (err: any) {
      setError("Failed to fetch library.");
    } finally {
      setLoadingDocs(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Simulate file path for ingestion (since backend expects a file_path string right now for local RAG)
    setUploading(true);
    setError(null);
    try {
      // Assuming user inputs absolute path for now since it's a local file agent, or fake it
      const filePath = prompt("Enter the absolute file path to ingest:", "");
      if (filePath) {
        await studyIngest(filePath);
        await fetchDocuments();
      }
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleRemove = async (docId: string) => {
    try {
      await studyRemoveDocument(docId);
      setDocuments(docs => docs.filter(d => d.document_id !== docId));
    } catch (err: any) {
      setError(err.message || "Failed to remove document");
    }
  };

  const handleQuery = async () => {
    if (!query.trim()) return;
    
    setQueryLoading(true);
    setQueryError(null);
    setResults(null);
    
    try {
      if (searchMode === "ask") {
        const res = await studyAsk(query);
        setResults({ type: "ask", ...res });
      } else {
        const res = await studySearch(query, 5);
        setResults({ type: "search", ...res });
      }
    } catch (err: any) {
      setQueryError(err.message);
    } finally {
      setQueryLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-background flex flex-col font-sans">
      <div className="max-w-6xl mx-auto w-full px-8 py-10 flex-1 flex flex-col min-h-[90vh]">
        
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 flex justify-between items-end"
        >
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center text-brand-600 border border-brand-100">
                <GraduationCap className="w-5 h-5" />
              </div>
              <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Study Library</h2>
            </div>
            <p className="text-slate-500 max-w-xl text-lg mt-2">Chat with your study documents using local secure RAG.</p>
          </div>
          <div>
            <input
              type="file"
              id="doc-upload"
              className="hidden"
              onChange={handleUpload}
              accept=".txt,.md,.pdf,.csv"
              disabled={uploading}
            />
            <label 
              htmlFor="doc-upload"
              className="cursor-pointer bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white px-6 py-3 rounded-xl text-sm font-semibold transition-all shadow-md flex items-center gap-2"
            >
              {uploading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</>
              ) : (
                <><Upload className="w-4 h-4" /> Add Material</>
              )}
            </label>
          </div>
        </motion.div>

        {error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-red-50 border border-red-100 p-4 rounded-xl flex items-start gap-3 mb-6 shadow-sm">
            <AlertTriangle className="text-red-500 w-5 h-5 shrink-0" />
            <span className="text-red-700 font-medium">{error}</span>
          </motion.div>
        )}

        <div className="flex flex-col lg:flex-row flex-1 gap-8 min-h-0">
          
          {/* Left Panel - Documents */}
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="w-full lg:w-1/3 flex flex-col bg-white border border-slate-200 rounded-3xl p-6 shadow-xl"
            style={{ maxHeight: "calc(100vh - 200px)" }}
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <FileText className="w-4 h-4 text-brand-500" />
                Your Knowledge
              </h3>
              <span className="text-xs font-semibold bg-slate-100 text-slate-600 px-2.5 py-1 rounded-lg">
                {documents.length} docs
              </span>
            </div>
            
            <div className="flex-1 overflow-y-auto pr-2 space-y-3">
              {loadingDocs ? (
                <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 text-slate-300 animate-spin" /></div>
              ) : documents.length === 0 ? (
                <div className="text-sm text-slate-500 text-center py-12 flex flex-col items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-slate-50 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-slate-300" />
                  </div>
                  <p>Your library is empty.</p>
                </div>
              ) : (
                <AnimatePresence>
                  {documents.map((doc, i) => (
                    <motion.div 
                      layout
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ delay: i * 0.05 }}
                      key={doc.document_id} 
                      className="group flex items-start gap-3 p-4 rounded-2xl bg-slate-50 hover:bg-white border border-transparent hover:border-slate-200 transition-all hover:shadow-sm"
                    >
                      <div className="mt-1">
                        <FileText className="w-4 h-4 text-brand-500 opacity-70" />
                      </div>
                      <div className="truncate flex-1">
                        <p className="text-sm font-semibold text-slate-800 truncate" title={doc.filename}>{doc.filename}</p>
                        <p className="text-[11px] text-slate-500 mt-1 font-mono">Chunks: {doc.chunks}</p>
                      </div>
                      <button 
                        onClick={() => handleRemove(doc.document_id)}
                        className="opacity-0 group-hover:opacity-100 p-2 text-red-500 hover:bg-red-50 rounded-xl transition-all"
                        title="Remove Document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </motion.div>
                  ))}
                </AnimatePresence>
              )}
            </div>
          </motion.div>

          {/* Right Panel - Search & Ask */}
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="flex-1 bg-white border border-slate-200 rounded-3xl flex flex-col min-h-0 shadow-xl overflow-hidden"
            style={{ maxHeight: "calc(100vh - 200px)" }}
          >
            <div className="p-6 border-b border-slate-100 bg-slate-50/50">
              <div className="flex items-center gap-2 mb-4 bg-slate-100/50 p-1 rounded-xl w-fit">
                <button 
                  onClick={() => setSearchMode("ask")}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${searchMode === "ask" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
                >
                  Ask Question
                </button>
                <button 
                  onClick={() => setSearchMode("search")}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${searchMode === "search" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
                >
                  Semantic Search
                </button>
              </div>
              <div className="relative group">
                <div className="absolute inset-0 bg-brand-500/10 rounded-2xl blur-xl transition-all duration-500 group-focus-within:bg-brand-500/20 group-focus-within:blur-2xl opacity-50" />
                <div className="relative bg-white shadow-sm rounded-2xl border border-slate-200 flex items-center p-2 transition-all duration-300 group-focus-within:border-brand-500 group-focus-within:ring-4 group-focus-within:ring-brand-500/10">
                  <input 
                    type="text" 
                    placeholder={searchMode === "ask" ? "Ask a question about your study material..." : "Search for concepts in your notes..."}
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleQuery()}
                    className="flex-1 bg-transparent border-none outline-none px-4 py-3 text-base text-slate-800 placeholder:text-slate-400 font-medium"
                  />
                  <button 
                    onClick={handleQuery}
                    disabled={queryLoading || !query}
                    className="bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white px-6 py-3 rounded-xl flex items-center gap-2 text-sm font-semibold transition-all"
                  >
                    {queryLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : searchMode === "ask" ? <HelpCircle className="w-4 h-4" /> : <Search className="w-4 h-4" />}
                    {queryLoading ? "Running..." : "Run"}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-8 bg-white">
              {queryError && (
                <div className="bg-red-50 border border-red-100 p-4 rounded-xl flex items-start gap-3">
                  <AlertTriangle className="text-red-500 w-5 h-5 shrink-0" />
                  <span className="text-red-700 text-sm font-medium">{queryError}</span>
                </div>
              )}
              
              {!queryError && !results && !queryLoading && (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-6">
                  <div className="w-20 h-20 rounded-full bg-slate-50 flex items-center justify-center">
                    <GraduationCap className="w-10 h-10 text-slate-300" />
                  </div>
                  <p className="text-base font-medium">Ready to explore your material.</p>
                </div>
              )}

              {queryLoading && (
                <div className="flex flex-col items-center justify-center h-full space-y-4">
                  <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
                  <p className="text-slate-500 font-medium animate-pulse">Analyzing library...</p>
                </div>
              )}

              {results?.type === "ask" && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
                  <div>
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-8 h-8 rounded-full bg-brand-50 flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-brand-600" />
                      </div>
                      <h4 className="text-lg font-bold text-slate-900">Answer</h4>
                    </div>
                    <div className="text-base text-slate-700 leading-relaxed whitespace-pre-wrap ml-11">
                      {results.answer}
                    </div>
                  </div>
                  
                  {results.sources?.length > 0 && (
                    <div className="ml-11 pt-6 border-t border-slate-100">
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Context Sources</h4>
                      <div className="space-y-4">
                        {results.sources.map((src: any, i: number) => (
                          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }} key={src.id} className="bg-slate-50 border border-slate-200 p-5 rounded-2xl">
                            <div className="flex items-center justify-between mb-3">
                              <span className="text-sm font-semibold text-slate-800">[{src.id}] {src.filename}</span>
                              <span className="text-[11px] text-slate-500 font-mono bg-white px-2 py-1 rounded-md border border-slate-200">
                                {src.metadata.page ? `Page ${src.metadata.page}` : src.metadata.slide ? `Slide ${src.metadata.slide}` : `Chunk ${src.metadata.chunk_index}`}
                              </span>
                            </div>
                            <p className="text-sm text-slate-600 line-clamp-3 leading-relaxed">{src.text}</p>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}

              {results?.type === "search" && (
                <div className="space-y-6">
                  <h4 className="text-sm font-bold text-slate-900 mb-4">Search Results ({results.data.length})</h4>
                  {results.data.map((res: any, i: number) => (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }} key={res.id} className="bg-slate-50 border border-slate-200 p-6 rounded-2xl">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-base font-bold text-slate-900">{res.metadata.filename}</span>
                        <div className="flex items-center gap-3">
                           <span className="text-[11px] text-slate-500 bg-white px-2 py-1 rounded-md border border-slate-200 font-mono">
                            {res.metadata.page ? `Pg ${res.metadata.page}` : res.metadata.slide ? `Sl ${res.metadata.slide}` : `Ch ${res.metadata.chunk_index}`}
                           </span>
                           <span className="text-xs font-semibold text-brand-700 bg-brand-50 px-2.5 py-1 rounded-lg border border-brand-100">
                            {Math.round(res.similarity * 100)}% Match
                           </span>
                        </div>
                      </div>
                      <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">{res.text}</p>
                    </motion.div>
                  ))}
                  {results.data.length === 0 && (
                    <div className="text-base text-slate-500 text-center py-12">No semantic matches found.</div>
                  )}
                </div>
              )}
            </div>
          </motion.div>

        </div>
      </div>
    </div>
  );
};
