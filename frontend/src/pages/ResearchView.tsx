import React, { useState } from "react";
import { Compass, Search, Globe, Link, FileText, AlertTriangle, Loader2 } from "lucide-react";
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
      <div className="max-w-6xl mx-auto w-full space-y-6 flex-1 flex flex-col h-full">
        
        {/* Header */}
        <div className="p-6 bg-surface border border-surface-border rounded-xl flex items-center gap-4 shrink-0">
          <div className="w-12 h-12 rounded-xl bg-brand-600/20 text-brand-400 flex items-center justify-center shrink-0">
            <Compass className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-slate-100">Research Agent</h2>
            <p className="text-xs text-slate-400 mt-1">Web search and cited synthesis.</p>
          </div>
          <div className="flex gap-2 items-center flex-1 max-w-lg">
            <input 
              type="text" 
              placeholder="Enter a research topic..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              className="flex-1 bg-background border border-surface-border rounded px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500"
            />
            <button 
              onClick={handleSearch}
              disabled={loading || !query}
              className="bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white px-4 py-2 rounded text-sm transition-colors flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              Search
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-lg flex items-start gap-3 shrink-0">
            <AlertTriangle className="text-red-400 w-5 h-5 shrink-0" />
            <span className="text-red-200 text-sm">{error}</span>
          </div>
        )}

        <div className="flex flex-1 gap-6 min-h-0">
          
          {/* Results List */}
          <div className="w-1/3 flex flex-col bg-surface border border-surface-border rounded-xl p-4 overflow-y-auto">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Globe className="w-4 h-4 text-brand-400" />
              Search Results
            </h3>
            <div className="space-y-4 pr-2">
              {results.length === 0 && !loading && (
                <div className="text-sm text-slate-500 text-center py-8">No results. Search for a topic.</div>
              )}
              {results.map((r, i) => (
                <div key={i} className="border border-surface-border bg-background p-3 rounded-lg hover:border-brand-500/50 transition-colors">
                  <a href={r.url} target="_blank" rel="noreferrer" className="text-sm font-medium text-brand-400 hover:underline line-clamp-2 leading-tight">
                    {r.title}
                  </a>
                  <div className="text-[10px] text-slate-500 font-mono mt-1 mb-2 truncate">{r.url}</div>
                  <p className="text-xs text-slate-300 line-clamp-3 mb-3">{r.snippet}</p>
                  
                  <button 
                    onClick={() => handleFetch(r.url)}
                    className="w-full bg-surface-secondary hover:bg-surface border border-surface-border text-slate-200 text-xs py-1.5 rounded flex items-center justify-center gap-2 transition-colors"
                  >
                    <FileText className="w-3 h-3" />
                    Fetch Source
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Source Viewer */}
          <div className="flex-1 flex flex-col bg-surface border border-surface-border rounded-xl p-4 overflow-hidden">
             <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Link className="w-4 h-4 text-brand-400" />
              Source Content
            </h3>
            
            {activeSource ? (
              <div className="flex flex-col h-full bg-background border border-surface-border rounded-lg overflow-hidden">
                <div className="bg-surface-secondary border-b border-surface-border p-3 shrink-0">
                  <h4 className="font-semibold text-sm text-slate-200 line-clamp-1">{activeSource.title}</h4>
                  <a href={activeSource.url} target="_blank" rel="noreferrer" className="text-xs text-brand-400 hover:underline truncate block mt-1">
                    {activeSource.url}
                  </a>
                </div>
                <div className="flex-1 overflow-y-auto p-4">
                  {activeSource.text ? (
                    <pre className="text-xs text-slate-300 font-sans whitespace-pre-wrap leading-relaxed">
                      {activeSource.text}
                    </pre>
                  ) : (
                    <div className="text-sm text-slate-500 text-center italic py-8">No text extracted.</div>
                  )}
                </div>
              </div>
            ) : (
               <div className="h-full flex flex-col items-center justify-center text-slate-500">
                <FileText className="w-12 h-12 mb-4 opacity-20" />
                <p className="text-sm">Select a search result and click "Fetch Source".</p>
              </div>
            )}
          </div>
          
        </div>

      </div>
    </div>
  );
};
