import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchActiveWorkflows } from '../api/client';
import { Workflow } from '../types';

export const WorkflowProgress: React.FC = () => {
  const [activeWorkflows, setActiveWorkflows] = useState<Workflow[]>([]);

  useEffect(() => {
    const pollWorkflows = async () => {
      try {
        const workflows = await fetchActiveWorkflows();
        setActiveWorkflows(workflows);
      } catch (err) {
        console.error("Error polling workflows", err);
      }
    };

    pollWorkflows();
    const interval = setInterval(pollWorkflows, 2000);
    return () => clearInterval(interval);
  }, []);

  if (activeWorkflows.length === 0) return null;

  return (
    <div className="absolute top-4 right-4 z-50 flex flex-col gap-2">
      <AnimatePresence>
        {activeWorkflows.map((wf) => {
          const currentStep = wf.steps.find((s: any) => s.status === 'RUNNING' || s.status === 'WAITING_APPROVAL' || s.status === 'PENDING') || wf.steps[wf.steps.length - 1];
          const stepText = currentStep ? `${currentStep.sequence + 1}. ${currentStep.tool_name.replace(/_/g, ' ')}` : 'Processing...';

          return (
            <motion.div
              key={wf.id}
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
              className="bg-slate-900/90 backdrop-blur border border-slate-700/50 rounded-xl p-4 shadow-xl text-sm min-w-[280px]"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-200 font-medium">{wf.goal || wf.name}</span>
                {wf.status === 'WAITING_APPROVAL' ? (
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                  </span>
                ) : (
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                  </span>
                )}
              </div>
              <div className="text-slate-400 text-xs flex items-center gap-2">
                {wf.status === 'WAITING_APPROVAL' ? (
                  <span>Waiting for your approval...</span>
                ) : (
                  <span>{stepText}</span>
                )}
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1 mt-3 overflow-hidden">
                <motion.div
                  className={`h-1 rounded-full ${wf.status === 'WAITING_APPROVAL' ? 'bg-amber-500' : 'bg-blue-500'}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${currentStep ? ((currentStep.sequence + 1) / Math.max(1, wf.steps.length)) * 100 : 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
};
