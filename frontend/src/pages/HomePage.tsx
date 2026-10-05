import React from "react";
import { ChatArea } from "../components/ChatArea";
import { ChatMessage } from "../types";
import { Search, Compass, GraduationCap, Code2, ShieldCheck, Sparkles, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { WorkflowProgress } from "../components/WorkflowProgress";

interface HomePageProps {
  messages: ChatMessage[];
  activities: any[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  onSelectMessageActivities: (msg: ChatMessage) => void;
  onApproveAction?: (approvalId: string, reason?: string) => Promise<void>;
  onRejectAction?: (approvalId: string, reason?: string) => Promise<void>;
}

const HeroSection = ({ input, setInput, onSendMessage }: any) => {
  return (
    <div className="relative min-h-[90vh] flex flex-col items-center justify-center px-6 overflow-hidden bg-background">
      {/* Background elegant gradient/blur */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-200 rounded-full blur-[140px] opacity-40 -z-10 pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="max-w-4xl w-full text-center space-y-8"
      >
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 1, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-50 border border-brand-100 text-brand-700 text-xs font-semibold uppercase tracking-widest mb-4"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Personal AI OS 2.0</span>
        </motion.div>
        
        <h1 className="text-5xl md:text-7xl font-bold text-slate-900 tracking-tight leading-[1.1]">
          The future of productivity is <span className="text-brand-600">human + AI</span>
        </h1>
        
        <p className="text-lg md:text-xl text-slate-500 max-w-2xl mx-auto leading-relaxed mt-6">
          Your personal local-first intelligence. We help you research, study, write code, and manage your files without sacrificing privacy.
        </p>
        
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-2xl mx-auto mt-12 pt-8"
        >
          <div className="relative group">
            <div className="absolute inset-0 bg-brand-500/10 rounded-2xl blur-xl transition-all duration-500 group-focus-within:bg-brand-500/20 group-focus-within:blur-2xl" />
            <div className="relative bg-white shadow-xl shadow-slate-200/50 rounded-2xl border border-slate-200 flex items-center p-3 transition-all duration-300 group-focus-within:border-brand-500 group-focus-within:ring-4 group-focus-within:ring-brand-500/10 hover:border-slate-300">
              <Search className="w-6 h-6 text-slate-400 ml-4 shrink-0 transition-colors group-focus-within:text-brand-600" />
              <input 
                type="text" 
                placeholder="Ask anything or tell me what you need to do..."
                className="flex-1 bg-transparent border-none outline-none px-5 py-4 text-lg text-slate-800 placeholder:text-slate-400 font-medium"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && input.trim()) {
                    onSendMessage(input.trim());
                    setInput("");
                  }
                }}
                autoFocus
              />
              <button 
                onClick={() => {
                  if (input.trim()) {
                    onSendMessage(input.trim());
                    setInput("");
                  }
                }}
                className="px-6 py-4 bg-brand-600 hover:bg-brand-700 text-white rounded-xl font-semibold transition-all shadow-md hover:shadow-lg flex items-center gap-2"
              >
                Execute <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <div className="flex flex-wrap justify-center gap-3 mt-8 opacity-80">
            {["Research quantum computing", "Summarize my notes", "Review codebase", "Find duplicate files"].map((suggestion, i) => (
              <button 
                key={i}
                onClick={() => onSendMessage(suggestion)}
                className="px-4 py-2 bg-white border border-slate-200 rounded-full text-sm font-medium text-slate-600 hover:text-brand-700 hover:border-brand-300 hover:bg-brand-50 transition-all shadow-sm"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};

const FeatureSection = ({ icon: Icon, title, description, reverse, children }: any) => {
  return (
    <div className="py-24 border-t border-slate-200 bg-background overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <div className={`flex flex-col ${reverse ? 'md:flex-row-reverse' : 'md:flex-row'} items-center gap-16`}>
          <motion.div 
            initial={{ opacity: 0, x: reverse ? 50 : -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1 space-y-6"
          >
            <div className="w-16 h-16 rounded-2xl bg-brand-50 flex items-center justify-center text-brand-600 mb-8 border border-brand-100">
              <Icon className="w-8 h-8" />
            </div>
            <h2 className="text-4xl font-bold text-slate-900 tracking-tight leading-tight">
              {title}
            </h2>
            <p className="text-lg text-slate-500 leading-relaxed max-w-lg">
              {description}
            </p>
          </motion.div>
          <motion.div 
            initial={{ opacity: 0, scale: 0.9, y: 30 }}
            whileInView={{ opacity: 1, scale: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1 w-full"
          >
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-tr from-brand-100 to-transparent rounded-3xl blur-3xl opacity-30 -z-10" />
              {children}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export const HomePage: React.FC<HomePageProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onSelectMessageActivities,
  onApproveAction,
  onRejectAction,
}) => {
  const [input, setInput] = React.useState("");

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto bg-background font-sans scroll-smooth">
        <HeroSection input={input} setInput={setInput} onSendMessage={onSendMessage} />
        
        <FeatureSection 
          icon={Compass}
          title="Research without the busywork."
          description="Automate deep web research. The AI searches, extracts evidence, and synthesizes answers with inline citations. No more endless tab switching."
        >
          <div className="bg-white border border-slate-200 shadow-xl rounded-3xl p-8 transform rotate-1 hover:rotate-0 transition-transform duration-500">
            <div className="space-y-4">
              <div className="h-4 w-1/3 bg-slate-100 rounded-full" />
              <div className="h-4 w-full bg-slate-100 rounded-full" />
              <div className="h-4 w-5/6 bg-slate-100 rounded-full" />
              <div className="flex gap-4 pt-4">
                <div className="h-24 flex-1 bg-brand-50 rounded-2xl border border-brand-100" />
                <div className="h-24 flex-1 bg-brand-50 rounded-2xl border border-brand-100" />
              </div>
            </div>
          </div>
        </FeatureSection>

        <FeatureSection 
          icon={GraduationCap}
          title="Your knowledge, connected."
          description="Upload thousands of documents. The Study agent securely embeds them locally and answers questions instantly, grounding every answer in your specific material."
          reverse={true}
        >
          <div className="bg-slate-900 border border-slate-800 shadow-2xl rounded-3xl p-8 transform -rotate-1 hover:rotate-0 transition-transform duration-500">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <div className="w-4 h-4 rounded-full bg-emerald-500" />
              </div>
              <div className="h-6 w-32 bg-slate-800 rounded-lg" />
            </div>
            <div className="space-y-3">
              <div className="h-3 w-full bg-slate-800 rounded-full" />
              <div className="h-3 w-full bg-slate-800 rounded-full" />
              <div className="h-3 w-2/3 bg-slate-800 rounded-full" />
            </div>
          </div>
        </FeatureSection>

        <FeatureSection 
          icon={Code2}
          title="Build with your AI."
          description="Point the Coding agent at any local repository. It explores files, finds bugs, suggests architecture, and can even edit files and run tests when you approve."
        >
          <div className="bg-slate-50 border border-slate-200 shadow-lg rounded-3xl p-6 relative overflow-hidden">
             <div className="absolute top-0 left-0 right-0 h-10 border-b border-slate-200 flex items-center px-4 gap-2 bg-white">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <div className="w-3 h-3 rounded-full bg-amber-400" />
                <div className="w-3 h-3 rounded-full bg-emerald-400" />
             </div>
             <div className="pt-10 font-mono text-xs text-slate-600 space-y-2">
                <p><span className="text-brand-600">const</span> analyzeRepo = <span className="text-purple-600">async</span> () =&#62; {"{"}</p>
                <p className="pl-4">await <span className="text-blue-600">tools.readDirectory</span>('./src');</p>
                <p className="pl-4">return <span className="text-emerald-600">"Architecture understood"</span>;</p>
                <p>{"}"};</p>
             </div>
          </div>
        </FeatureSection>

        <div className="py-32 bg-slate-900 text-center px-6 relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-brand-900/40 via-slate-900 to-slate-900 -z-10" />
          <ShieldCheck className="w-16 h-16 text-emerald-400 mx-auto mb-8" />
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">Designed for absolute control.</h2>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-12 leading-relaxed">
            Local execution. Zero cloud dependency. Every side-effect action requires your explicit approval.
          </p>
          <button 
            onClick={() => {
              window.scrollTo({ top: 0, behavior: 'smooth' });
              setTimeout(() => document.querySelector('input')?.focus(), 500);
            }}
            className="px-8 py-4 bg-white text-slate-900 hover:bg-slate-100 rounded-xl font-bold transition-colors shadow-xl"
          >
            Start your session
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex h-full overflow-hidden justify-center bg-background relative">
      <WorkflowProgress />
      <div className="max-w-4xl w-full flex-1 relative">
        <ChatArea
          messages={messages}
          isLoading={isLoading}
          onSendMessage={onSendMessage}
          onSelectMessageActivities={onSelectMessageActivities}
          onApproveAction={onApproveAction}
          onRejectAction={onRejectAction}
        />
      </div>
    </div>
  );
};
