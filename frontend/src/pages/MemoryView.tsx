import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Memory } from "../types";
import { fetchMemories, createMemory, updateMemory, deleteMemory, archiveMemory, restoreMemory } from "../api/client";
import { Plus, Search, Archive, Trash2, Edit2, RotateCcw } from "lucide-react";

export const MemoryView: React.FC = () => {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState("ALL");
  const [showArchived, setShowArchived] = useState(false);

  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    content: "",
    memory_type: "FACT",
    category: "",
  });

  const memoryTypes = ["FACT", "PREFERENCE", "GOAL", "PROJECT", "EPISODE"];

  const loadMemories = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchMemories(filterType, searchQuery, showArchived);
      setMemories(res.items || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemories();
  }, [filterType, showArchived]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadMemories();
  };

  const handleSave = async () => {
    try {
      setError(null);
      if (editingId) {
        await updateMemory(editingId, {
          content: formData.content,
          memory_type: formData.memory_type,
          category: formData.category || null,
        });
      } else {
        await createMemory({
          content: formData.content,
          memory_type: formData.memory_type,
          category: formData.category || null,
        });
      }
      setIsCreating(false);
      setEditingId(null);
      setFormData({ content: "", memory_type: "FACT", category: "" });
      loadMemories();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Permanently delete this memory?")) {
      try {
        await deleteMemory(id);
        loadMemories();
      } catch (err: any) {
        setError(err.message);
      }
    }
  };

  const handleArchive = async (id: string, currentlyArchived: boolean) => {
    try {
      if (currentlyArchived) {
        await restoreMemory(id);
      } else {
        await archiveMemory(id);
      }
      loadMemories();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const startEdit = (mem: Memory) => {
    setEditingId(mem.id);
    setFormData({
      content: mem.content,
      memory_type: mem.memory_type,
      category: mem.category || "",
    });
    setIsCreating(true);
  };

  const cancelEdit = () => {
    setIsCreating(false);
    setEditingId(null);
    setFormData({ content: "", memory_type: "FACT", category: "" });
  };

  return (
    <div className="flex flex-col h-full bg-white text-gray-900 p-6 overflow-hidden">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-light tracking-tight text-gray-900">Memory</h1>
        <button
          onClick={() => {
            cancelEdit();
            setIsCreating(true);
          }}
          className="flex items-center px-4 py-2 bg-black text-white rounded hover:bg-gray-800 transition-colors shadow-sm text-sm"
        >
          <Plus size={16} className="mr-2" />
          Add Memory
        </button>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <form onSubmit={handleSearch} className="flex-1 relative">
          <input
            type="text"
            placeholder="Search memories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 transition-shadow bg-gray-50"
          />
          <Search size={18} className="absolute left-3 top-2.5 text-gray-400" />
        </form>

        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 bg-gray-50 text-gray-700"
        >
          <option value="ALL">All Types</option>
          {memoryTypes.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <label className="flex items-center space-x-2 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="rounded border-gray-300 text-black focus:ring-black"
          />
          <span>Show Archived</span>
        </label>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-100 text-red-600 rounded-lg text-sm">
          {error}
        </div>
      )}

      <AnimatePresence>
        {isCreating && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-6 bg-gray-50 p-5 rounded-xl border border-gray-100 overflow-hidden"
          >
            <h3 className="text-lg font-medium mb-4">{editingId ? "Edit Memory" : "New Memory"}</h3>
            <div className="space-y-4">
              <textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                placeholder="Memory content..."
                rows={3}
                className="w-full p-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 bg-white resize-none text-sm"
              />
              <div className="flex gap-4">
                <select
                  value={formData.memory_type}
                  onChange={(e) => setFormData({ ...formData, memory_type: e.target.value })}
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
                >
                  {memoryTypes.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <input
                  type="text"
                  placeholder="Category (optional)"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-gray-900"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={cancelEdit}
                  className="px-4 py-2 text-gray-500 hover:text-gray-900 transition-colors text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={!formData.content.trim()}
                  className="px-4 py-2 bg-black text-white rounded hover:bg-gray-800 transition-colors text-sm font-medium disabled:opacity-50"
                >
                  Save
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 overflow-y-auto pr-2 pb-10 space-y-4">
        {loading && memories.length === 0 ? (
          <div className="text-center text-gray-400 py-10">Loading memories...</div>
        ) : memories.length === 0 ? (
          <div className="text-center text-gray-400 py-10">No memories found.</div>
        ) : (
          memories.map((mem) => (
            <motion.div
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              key={mem.id}
              className={`p-5 rounded-xl border ${mem.is_archived ? 'bg-gray-50 border-gray-100 opacity-60' : 'bg-white border-gray-200 shadow-sm'} flex flex-col gap-3 group transition-all hover:shadow-md`}
            >
              <div className="flex justify-between items-start gap-4">
                <div className="flex-1 whitespace-pre-wrap text-sm text-gray-800 leading-relaxed">
                  {mem.content}
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => startEdit(mem)} className="p-1.5 text-gray-400 hover:text-blue-600 rounded" title="Edit">
                    <Edit2 size={16} />
                  </button>
                  <button onClick={() => handleArchive(mem.id, mem.is_archived)} className="p-1.5 text-gray-400 hover:text-orange-600 rounded" title={mem.is_archived ? "Restore" : "Archive"}>
                    {mem.is_archived ? <RotateCcw size={16} /> : <Archive size={16} />}
                  </button>
                  <button onClick={() => handleDelete(mem.id)} className="p-1.5 text-gray-400 hover:text-red-600 rounded" title="Delete">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-400 uppercase tracking-wider font-medium">
                <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-600">{mem.memory_type}</span>
                {mem.category && <span>{mem.category}</span>}
                <span>•</span>
                <span>{new Date(mem.created_at).toLocaleDateString()}</span>
                {mem.is_archived && (
                  <>
                    <span>•</span>
                    <span className="text-orange-600 flex items-center"><Archive size={10} className="mr-1"/> Archived</span>
                  </>
                )}
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
};
