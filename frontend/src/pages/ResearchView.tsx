import React, { useState } from "react";
import { Compass, Search, Globe, FileText, AlertTriangle, Loader2 } from "lucide-react";
import { researchSearch, researchFetch } from "../api/client";

export const ResearchView: React.FC = () => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [results, setResults] = useState<any[]>([]);
  const [activeSource, setActiveSource] = useState<any | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResults([]);
    setActiveSource(null);
    
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
    <div className="flex-1 p-8 overflow-hidden bg-background flex flex-col">
      <div className="max-w-5xl mx-auto w-full space-y-6 flex-1 flex flex-col h-full">
        
        {/* Header */}
        <div className="p-6 bg-white border border-slate-200 rounded-2xl flex items-center gap-4 shrink-0 shadow-sm">
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-slate-800">Research</h2>
            <p className="text-sm text-slate-500 mt-1">Research anything across the web.</p>
          </div>
          <div className="flex gap-2 items-center flex-1 max-w-lg relative">
            <Search className="w-5 h-5 text-slate-400 absolute left-3" />
            <input 
              type="text" 
              placeholder="What would you like to research?"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 transition-all"
            />
            <button 
              onClick={handleSearch}
              disabled={loading || !query}
              className="absolute right-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white p-1.5 rounded-lg transition-colors"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-100 p-4 rounded-xl flex items-start gap-3 shrink-0">
            <AlertTriangle className="text-red-500 w-5 h-5 shrink-0" />
            <span className="text-red-700 text-sm">{error}</span>
          </div>
        )}

        <div className="flex flex-1 gap-6 min-h-0">
          
          {/* Results List */}
          <div className="w-1/3 flex flex-col bg-white border border-slate-200 rounded-2xl p-5 overflow-y-auto shadow-sm">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Globe className="w-4 h-4 text-slate-400" />
              Sources
            </h3>
            <div className="space-y-4 pr-1">
              {results.length === 0 && !loading && (
                <div className="text-sm text-slate-500 text-center py-12 space-y-4">
                  <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mx-auto">
                    <Compass className="w-6 h-6 text-slate-300" />
                  </div>
                  <p>Search for a topic to begin.</p>
                </div>
              )}
              {results.map((r, i) => (
                <div key={i} className="border border-slate-200 bg-white p-4 rounded-xl hover:border-brand-300 hover:shadow-sm transition-all group">
                  <a href={r.url} target="_blank" rel="noreferrer" className="text-sm font-semibold text-brand-600 hover:underline line-clamp-2 leading-tight">
                    {r.title}
                  </a>
                  <div className="text-[11px] text-slate-400 font-mono mt-1.5 mb-2 truncate">{r.url}</div>
                  <p className="text-xs text-slate-600 line-clamp-3 mb-4 leading-relaxed">{r.snippet}</p>
                  
                  <button 
                    onClick={() => handleFetch(r.url)}
                    className="w-full bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-medium py-2 rounded-lg flex items-center justify-center gap-2 transition-colors"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    Read Source
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Source Viewer */}
          <div className="flex-1 flex flex-col bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            {activeSource ? (
              <div className="flex flex-col h-full bg-white overflow-hidden">
                <div className="bg-slate-50 border-b border-slate-200 p-5 shrink-0">
                  <h4 className="font-semibold text-slate-800 line-clamp-1">{activeSource.title}</h4>
                  <a href={activeSource.url} target="_blank" rel="noreferrer" className="text-xs text-brand-600 hover:underline truncate block mt-1">
                    {activeSource.url}
                  </a>
                </div>
                <div className="flex-1 overflow-y-auto p-6 bg-white">
                  {activeSource.text ? (
                    <pre className="text-sm text-slate-700 font-sans whitespace-pre-wrap leading-relaxed max-w-3xl mx-auto">
                      {activeSource.text}
                    </pre>
                  ) : (
                    <div className="text-sm text-slate-500 text-center italic py-8">No text extracted.</div>
                  )}
                </div>
              </div>
            ) : (
               <div className="h-full flex flex-col items-center justify-center text-slate-400 bg-slate-50/50">
                <FileText className="w-12 h-12 mb-4 text-slate-300" />
                <p className="text-sm font-medium">Select a source to read</p>
              </div>
            )}
          </div>
          
        </div>

      </div>
    </div>
  );
};
