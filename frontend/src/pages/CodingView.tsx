import React, { useState } from "react";
import { Code2, Folder, Search, FileText, GitBranch, Terminal, AlertTriangle, FileCode2 } from "lucide-react";
import { codingListRepo, codingMetadata, codingSearch, codingReadFile, codingGitStatus, codingGitLog, codingGitDiff } from "../api/client";

export const CodingView: React.FC = () => {
  const [repoPath, setRepoPath] = useState("");
  const [activeRepo, setActiveRepo] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  const [files, setFiles] = useState<string[]>([]);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchPattern, setSearchPattern] = useState("");
  
  const [viewingFile, setViewingFile] = useState<{ path: string; content: string } | null>(null);
  
  const [gitStatus, setGitStatus] = useState<string>("");
  const [gitLog, setGitLog] = useState<any[]>([]);
  const [gitDiff, setGitDiff] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"search" | "diff">("search");

  const loadRepository = async () => {
    if (!repoPath.trim()) return;
    setLoading(true);
    setError(null);
    setFiles([]);
    setViewingFile(null);
    setSearchResults([]);
    setGitStatus("");
    setGitLog([]);
    setGitDiff("");
    
    try {
      const meta = await codingMetadata(repoPath);
      setActiveRepo(meta);
      
      const list = await codingListRepo(repoPath);
      setFiles(list.files || []);
      
      try {
        const status = await codingGitStatus(repoPath);
        setGitStatus(status.status);
        const logs = await codingGitLog(repoPath);
        setGitLog(logs.commits);
      } catch (e) {
        // Not a git repo or failed
      }
      
    } catch (err: any) {
      setError(err.message);
      setActiveRepo(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDiff = async () => {
    if (!activeRepo) return;
    setLoading(true);
    try {
      const res = await codingGitDiff(repoPath);
      setGitDiff(res.diff || "No changes.");
      setActiveTab("diff");
      setViewingFile(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!activeRepo || !searchPattern.trim()) return;
    setLoading(true);
    try {
      const res = await codingSearch(repoPath, searchPattern);
      setSearchResults(res.matches || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReadFile = async (relPath: string) => {
    setLoading(true);
    try {
      const fullPath = repoPath.replace(/\\/g, "/") + "/" + relPath;
      const res = await codingReadFile(fullPath);
      setViewingFile({ path: relPath, content: res.content });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 p-8 overflow-hidden bg-background flex flex-col font-sans">
      <div className="max-w-7xl mx-auto w-full space-y-6 flex-1 flex flex-col h-full">
        
        {/* Header & Repo Selection */}
        <div className="p-6 bg-white border border-slate-200 rounded-xl flex items-center gap-4 shrink-0">
          <div className="w-12 h-12 rounded-xl bg-brand-600/20 text-brand-600 flex items-center justify-center shrink-0">
            <Code2 className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-slate-800">Coding & GitHub Agent</h2>
            <p className="text-xs text-slate-500 mt-1">Read-only code analysis, structural search, and git inspection.</p>
          </div>
          <div className="flex gap-2 items-center flex-1 max-w-lg">
            <input 
              type="text" 
              placeholder="Absolute Repository Path (e.g. C:/Projects/App)"
              value={repoPath}
              onChange={e => setRepoPath(e.target.value)}
              onKeyDown={e => e.key === "Enter" && loadRepository()}
              className="flex-1 bg-slate-50/50 border border-slate-200 rounded px-4 py-2 text-sm text-slate-800 focus:outline-none focus:border-brand-500"
            />
            <button 
              onClick={loadRepository}
              disabled={loading || !repoPath}
              className="bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white px-4 py-2 rounded text-sm transition-colors"
            >
              Load
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 p-4 rounded-lg flex items-start gap-3 shrink-0">
            <AlertTriangle className="text-red-600 w-5 h-5 shrink-0" />
            <span className="text-red-200 text-sm">{error}</span>
          </div>
        )}

        {/* Main Content Area */}
        {activeRepo && (
          <div className="flex gap-6 flex-1 min-h-0">
            
            {/* Sidebar: File Tree & Git */}
            <div className="w-1/4 flex flex-col gap-4 overflow-y-auto pr-2">
              <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col min-h-0 flex-1">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Folder className="w-4 h-4 text-brand-600" />
                  Repository Files
                </h3>
                <div className="flex-1 overflow-y-auto space-y-1 pr-2">
                  {files.map(f => (
                    <button
                      key={f}
                      onClick={() => handleReadFile(f)}
                      className="w-full text-left text-xs text-slate-700 hover:text-brand-600 hover:bg-white-secondary px-2 py-1.5 rounded truncate"
                      title={f}
                    >
                      <FileCode2 className="w-3 h-3 inline-block mr-2 opacity-50" />
                      {f}
                    </button>
                  ))}
                </div>
              </div>

              {gitStatus && (
                <div className="bg-white border border-slate-200 rounded-xl p-4 shrink-0">
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <GitBranch className="w-4 h-4 text-brand-600" />
                    Git Info
                  </h3>
                  <div className="text-[10px] text-slate-500 font-mono whitespace-pre-wrap max-h-32 overflow-y-auto mb-4">
                    {gitStatus}
                  </div>
                  {gitLog.length > 0 && (
                    <div className="space-y-2 mt-2 border-t border-slate-200 pt-2">
                      <h4 className="text-[10px] font-semibold text-slate-500 uppercase">Recent Commits</h4>
                      {gitLog.slice(0, 3).map((commit, i) => (
                        <div key={i} className="text-[10px] text-slate-700">
                          <span className="text-brand-600 font-mono">{commit.sha.substring(0,7)}</span> - <span className="truncate" title={commit.message}>{commit.message.substring(0, 30)}{commit.message.length > 30 ? "..." : ""}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Main Area: Viewer & Search */}
            <div className="flex-1 flex flex-col gap-4 min-h-0">
              
              {/* Search Bar / Toggles */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shrink-0 flex gap-2 items-center">
                <input 
                  type="text" 
                  placeholder="Regex / Pattern search in code..."
                  value={searchPattern}
                  onChange={e => setSearchPattern(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") { handleSearch(); setActiveTab("search"); } }}
                  className="flex-1 bg-slate-50/50 border border-slate-200 rounded px-4 py-2 text-sm text-slate-800 focus:outline-none focus:border-brand-500"
                />
                <button 
                  onClick={() => {handleSearch(); setActiveTab("search");}}
                  disabled={loading || !searchPattern}
                  className="bg-white-secondary hover:bg-white-border disabled:opacity-50 text-slate-800 px-4 py-2 rounded flex items-center gap-2 text-sm transition-colors border border-slate-200"
                >
                  <Search className="w-4 h-4" />
                  Search
                </button>
                <button 
                  onClick={handleLoadDiff}
                  disabled={loading}
                  className={`px-4 py-2 rounded text-sm transition-colors border border-slate-200 ${activeTab === "diff" ? "bg-brand-600 border-brand-500 text-white" : "bg-white-secondary text-slate-800"}`}
                >
                  Workspace Diff
                </button>
              </div>

              {/* Viewport */}
              <div className="bg-white border border-slate-200 rounded-xl flex-1 flex flex-col min-h-0 overflow-hidden relative">
                {loading && (
                  <div className="absolute inset-0 bg-slate-50/50/50 flex items-center justify-center z-10 backdrop-blur-sm">
                    <div className="text-brand-600 animate-pulse text-sm flex items-center gap-2">
                      <Terminal className="w-4 h-4" /> Loading...
                    </div>
                  </div>
                )}
                
                {activeTab === "diff" ? (
                  <div className="flex flex-col h-full">
                    <div className="bg-white-secondary border-b border-slate-200 px-4 py-2 flex justify-between items-center shrink-0">
                      <span className="text-xs font-semibold text-slate-800 font-mono flex items-center gap-2">
                        <GitBranch className="w-4 h-4 text-brand-600" />
                        git diff
                      </span>
                    </div>
                    <div className="flex-1 overflow-auto p-4 bg-slate-50/50">
                      {gitDiff ? (
                        <pre className="text-[11px] font-mono whitespace-pre-wrap break-words leading-relaxed">
                          {gitDiff.split('\n').map((line, i) => (
                            <div key={i} className={line.startsWith('+') && !line.startsWith('+++') ? 'text-green-400' : line.startsWith('-') && !line.startsWith('---') ? 'text-red-600' : 'text-slate-700'}>
                              {line}
                            </div>
                          ))}
                        </pre>
                      ) : (
                        <div className="text-slate-500 text-sm">No changes in workspace.</div>
                      )}
                    </div>
                  </div>
                ) : searchResults.length > 0 && !viewingFile ? (
                  <div className="p-4 overflow-y-auto h-full space-y-4">
                    <h3 className="text-sm font-semibold text-slate-800 sticky top-0 bg-white pb-2">Search Results ({searchResults.length})</h3>
                    {searchResults.map((res, i) => (
                      <div key={i} className="bg-slate-50/50 border border-slate-200 rounded p-3 cursor-pointer hover:border-brand-500 transition-colors" onClick={() => handleReadFile(res.file)}>
                        <div className="text-xs font-semibold text-brand-600 mb-1">{res.file}:{res.line_number}</div>
                        <div className="text-xs text-slate-700 font-mono bg-white-secondary p-2 rounded truncate">
                          {res.content}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : viewingFile ? (
                  <div className="flex flex-col h-full">
                    <div className="bg-white-secondary border-b border-slate-200 px-4 py-2 flex justify-between items-center shrink-0">
                      <span className="text-xs font-semibold text-slate-800 font-mono flex items-center gap-2">
                        <FileText className="w-4 h-4 text-brand-600" />
                        {viewingFile.path}
                      </span>
                      <button onClick={() => setViewingFile(null)} className="text-xs text-slate-500 hover:text-slate-800">
                        Close
                      </button>
                    </div>
                    <div className="flex-1 overflow-auto p-4 bg-slate-50/50">
                      <pre className="text-[11px] text-slate-700 font-mono whitespace-pre-wrap break-words leading-relaxed">
                        {viewingFile.content}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500">
                    <Code2 className="w-12 h-12 mb-4 opacity-20" />
                    <p className="text-sm">Select a file from the tree or search the repository.</p>
                  </div>
                )}
              </div>
            </div>
            
          </div>
        )}
      </div>
    </div>
  );
};
