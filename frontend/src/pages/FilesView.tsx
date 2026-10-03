import React, { useState } from "react";
import { FolderTree, Search, FileText, Info, AlertTriangle } from "lucide-react";
import { searchFiles, getFileMetadata, readFileContent } from "../api/client";

export const FilesView: React.FC = () => {
  const [directory, setDirectory] = useState("");
  const [pattern, setPattern] = useState("*.*");
  const [files, setFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<any | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [contentLoading, setContentLoading] = useState(false);

  const handleSearch = async () => {
    if (!directory) return;
    setLoading(true);
    setError(null);
    setSelectedFile(null);
    setMetadata(null);
    setContent(null);
    try {
      const res = await searchFiles(directory, pattern);
      setFiles(res.files || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = async (file: string) => {
    setSelectedFile(file);
    setContentLoading(true);
    setMetadata(null);
    setContent(null);
    setError(null);
    
    try {
      const meta = await getFileMetadata(file);
      setMetadata(meta);
      
      if (meta.is_file) {
        const fileContent = await readFileContent(file);
        setContent(fileContent.content);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setContentLoading(false);
    }
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto bg-background flex flex-col">
      <div className="max-w-6xl mx-auto w-full space-y-6 flex-1 flex flex-col">
        {/* Title */}
        <div className="p-6 bg-surface border border-surface-border rounded-xl flex items-start gap-4 shrink-0">
          <div className="w-12 h-12 rounded-xl bg-brand-600/20 text-brand-400 flex items-center justify-center shrink-0">
            <FolderTree className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-slate-100">Local File Explorer</h2>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Search and view local files securely within the allowed sandbox.
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex items-center gap-4 bg-surface border border-surface-border p-4 rounded-xl shrink-0">
          <div className="flex-1 flex flex-col gap-1">
            <label className="text-xs text-slate-400 uppercase font-semibold">Directory (Absolute Path)</label>
            <input 
              type="text" 
              className="bg-background border border-surface-border rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500" 
              placeholder="e.g. C:/Users/yugag/Documents"
              value={directory}
              onChange={(e) => setDirectory(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
          </div>
          <div className="flex-1 flex flex-col gap-1">
            <label className="text-xs text-slate-400 uppercase font-semibold">Pattern</label>
            <input 
              type="text" 
              className="bg-background border border-surface-border rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500" 
              placeholder="*.md, **/*.py"
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
          </div>
          <button 
            onClick={handleSearch}
            disabled={loading || !directory}
            className="mt-5 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white px-4 py-2 rounded flex items-center gap-2 text-sm transition-colors"
          >
            <Search className="w-4 h-4" />
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
        
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-lg flex items-center gap-3 shrink-0">
            <AlertTriangle className="text-red-400 w-5 h-5" />
            <span className="text-red-200 text-sm">{error}</span>
          </div>
        )}

        {/* Content Area */}
        <div className="flex gap-6 flex-1 min-h-0">
          {/* File List */}
          <div className="w-1/3 bg-surface border border-surface-border rounded-xl flex flex-col overflow-hidden">
            <div className="p-4 border-b border-surface-border bg-surface-secondary">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Search className="w-4 h-4 text-slate-400" />
                Search Results ({files.length})
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              {files.length === 0 && !loading && !error && (
                <div className="text-center text-slate-500 p-8 text-sm">No files found.</div>
              )}
              {files.map((f, idx) => (
                <button
                  key={idx}
                  onClick={() => handleFileSelect(f)}
                  className={`w-full text-left px-3 py-2 rounded flex items-center gap-2 text-sm truncate transition-colors ${
                    selectedFile === f 
                      ? "bg-brand-600/20 text-brand-300 border border-brand-500/30" 
                      : "text-slate-300 hover:bg-surface-secondary border border-transparent"
                  }`}
                  title={f}
                >
                  <FileText className="w-4 h-4 shrink-0" />
                  <span className="truncate">{f.split(/[\\/]/).pop()}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* File Details */}
          <div className="flex-1 bg-surface border border-surface-border rounded-xl flex flex-col overflow-hidden">
             {selectedFile ? (
               <>
                 <div className="p-4 border-b border-surface-border bg-surface-secondary flex items-center gap-3 shrink-0">
                   <Info className="w-5 h-5 text-brand-400" />
                   <div className="truncate">
                     <h3 className="text-sm font-semibold text-slate-200 truncate" title={selectedFile}>
                       {selectedFile.split(/[\\/]/).pop()}
                     </h3>
                     {metadata && (
                       <p className="text-xs text-slate-500 flex gap-4 mt-0.5">
                         <span>{metadata.size_bytes} bytes</span>
                         <span>Modified: {metadata.modified_at}</span>
                       </p>
                     )}
                   </div>
                 </div>
                 <div className="flex-1 overflow-y-auto p-4 bg-background/50">
                   {contentLoading ? (
                     <div className="text-sm text-slate-500 animate-pulse">Loading content...</div>
                   ) : content ? (
                     <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap break-words">
                       {content}
                     </pre>
                   ) : (
                     <div className="text-sm text-slate-500">No text content available or binary file.</div>
                   )}
                 </div>
               </>
             ) : (
               <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-8 text-center">
                 <FileText className="w-12 h-12 mb-4 opacity-20" />
                 <p className="text-sm">Select a file from the search results to view its content.</p>
               </div>
             )}
          </div>
        </div>
      </div>
    </div>
  );
};
