import React, { useState } from "react";
import { Compass, Search, Globe, FileText, AlertTriangle, Loader2, ArrowRight } from "lucide-react";
import { researchSearch, researchFetch } from "../api/client";
import { motion, AnimatePresence } from "framer-motion";

export const ResearchView: React.FC = () => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [results, setResults] = useState<any[]>([]);
  const [activeSource, setActiveSource] = useState<any | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResults([]);
    setActiveSource(null);
    setHasSearched(true);
    
    try {
      const res = await researchSearch(query, 10);
      setResults(res.results || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFetch = async (url: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await researchFetch(url);
      setActiveSource(res);
    } catch (err: any) {
      setError(`Failed to fetch ${url}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-background flex flex-col font-sans">
      <div className="max-w-6xl mx-auto w-full px-8 py-12 flex-1 flex flex-col min-h-[90vh]">
        
        {/* Animated Hero/Search Header */}
        <motion.div 
          layout
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className={`flex flex-col items-center justify-center text-center ${hasSearched ? 'mb-8' : 'flex-1 mt-[-10vh]'}`}
        >
          <motion.div layout className="w-16 h-16 rounded-2xl bg-brand-50 flex items-center justify-center text-brand-600 mb-6 border border-brand-100">
            <Compass className="w-8 h-8" />
          </motion.div>
          <motion.h2 layout className="text-4xl font-bold text-slate-900 mb-3 tracking-tight">Research</motion.h2>
          <motion.p layout className="text-slate-500 max-w-lg mb-10 text-lg">
            Research anything across the web without the busywork. We'll find the sources and extract the evidence.
          </motion.p>
          
          <motion.div layout className="w-full max-w-2xl relative group">
            <div className="absolute inset-0 bg-brand-500/10 rounded-2xl blur-xl transition-all duration-500 group-focus-within:bg-brand-500/20 group-focus-within:blur-2xl opacity-50" />
            <div className="relative bg-white shadow-lg shadow-slate-200/50 rounded-2xl border border-slate-200 flex items-center p-3 transition-all duration-300 group-focus-within:border-brand-500 group-focus-within:ring-4 group-focus-within:ring-brand-500/10">
              <Search className="w-6 h-6 text-slate-400 ml-4 shrink-0 transition-colors group-focus-within:text-brand-600" />
              <input 
                type="text" 
                placeholder="What would you like to research?"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSearch()}
                className="flex-1 bg-transparent border-none outline-none px-5 py-4 text-lg text-slate-800 placeholder:text-slate-400 font-medium"
                autoFocus
              />
              <button 
                onClick={handleSearch}
                disabled={loading || !query}
                className="px-6 py-4 bg-brand-600 hover:bg-brand-700 disabled:bg-slate-300 text-white rounded-xl font-semibold transition-all shadow-sm flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}
              </button>
            </div>
          </motion.div>
          
          {!hasSearched && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="flex gap-3 mt-8 flex-wrap justify-center"
            >
              {["Latest advancements in LLMs", "History of typography", "How quantum computers work"].map((suggestion, i) => (
                <button 
                  key={i}
                  onClick={() => { setQuery(suggestion); setTimeout(handleSearch, 100); }}
                  className="px-4 py-2 bg-white border border-slate-200 rounded-full text-sm font-medium text-slate-600 hover:text-brand-700 hover:border-brand-300 hover:bg-brand-50 transition-all shadow-sm"
                >
                  {suggestion}
                </button>
              ))}
            </motion.div>
          )}
        </motion.div>

        {error && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-red-50 border border-red-100 p-4 rounded-xl flex items-start gap-3 mb-6 shrink-0 shadow-sm">
            <AlertTriangle className="text-red-500 w-5 h-5 shrink-0" />
            <span className="text-red-700 font-medium">{error}</span>
          </motion.div>
        )}

        <AnimatePresence>
          {hasSearched && (
            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-col md:flex-row flex-1 gap-8 min-h-0 pb-12"
            >
              {/* Results List */}
              <div className="w-full md:w-1/3 flex flex-col space-y-4">
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <Globe className="w-4 h-4 text-brand-600" />
                  Search Results
                </h3>
                <div className="flex-1 space-y-4 pr-1 overflow-y-auto" style={{ maxHeight: "calc(100vh - 300px)" }}>
                  {loading && results.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-16 space-y-4">
                      <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
                      <p className="text-slate-500 font-medium animate-pulse">Scouring the web...</p>
                    </div>
                  )}
                  {results.map((r, i) => (
                    <motion.div 
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      key={i} 
                      className="border border-slate-200 bg-white p-5 rounded-2xl hover:border-brand-300 hover:shadow-md transition-all group cursor-pointer"
                      onClick={() => handleFetch(r.url)}
                    >
                      <h4 className="text-sm font-semibold text-slate-900 group-hover:text-brand-600 line-clamp-2 leading-tight transition-colors">
                        {r.title}
                      </h4>
                      <div className="text-[11px] text-slate-400 font-mono mt-2 mb-3 truncate bg-slate-50 px-2 py-1 rounded inline-block">{r.url}</div>
                      <p className="text-sm text-slate-600 line-clamp-3 mb-4 leading-relaxed">{r.snippet}</p>
                      <div className="flex items-center text-xs font-semibold text-brand-600 group-hover:translate-x-1 transition-transform">
                        Read Source <ArrowRight className="w-3 h-3 ml-1" />
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Source Viewer */}
              <div className="flex-1 flex flex-col bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-xl" style={{ maxHeight: "calc(100vh - 300px)" }}>
                {activeSource ? (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col h-full">
                    <div className="bg-slate-50 border-b border-slate-200 p-6 shrink-0">
                      <h4 className="text-lg font-bold text-slate-900 line-clamp-2 leading-tight">{activeSource.title}</h4>
                      <a href={activeSource.url} target="_blank" rel="noreferrer" className="text-xs font-medium text-brand-600 hover:underline truncate block mt-2">
                        {activeSource.url}
                      </a>
                    </div>
                    <div className="flex-1 overflow-y-auto p-8">
                      {activeSource.text ? (
                        <pre className="text-base text-slate-700 font-sans whitespace-pre-wrap leading-relaxed max-w-3xl mx-auto">
                          {activeSource.text}
                        </pre>
                      ) : (
                        <div className="text-slate-500 text-center italic py-12">No text could be extracted.</div>
                      )}
                    </div>
                  </motion.div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 bg-slate-50/50">
                    <FileText className="w-16 h-16 mb-6 text-slate-200" />
                    <p className="text-lg font-medium text-slate-500">Select a source to read</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
