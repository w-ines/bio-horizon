import { create } from "zustand";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
};

type AgentStep = {
  id: string;
  content: string;
  preview?: string;
  timestamp: Date;
};

interface RagState {
  messages: Message[];
  currentSteps: AgentStep[];
  conversationId: string;

  addMessage: (msg: Message) => void;
  setMessages: (msgs: Message[]) => void;
  setCurrentSteps: (steps: AgentStep[]) => void;
  addStep: (step: AgentStep) => void;
  setConversationId: (id: string) => void;
  clearConversation: () => void;
}

function generateConversationId() {
  return `rag_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

export const useRagStore = create<RagState>((set) => ({
  messages: [],
  currentSteps: [],
  conversationId:
    typeof window !== "undefined"
      ? localStorage.getItem("bio_horizon_conversation_id") ||
        (() => {
          const id = generateConversationId();
          localStorage.setItem("bio_horizon_conversation_id", id);
          return id;
        })()
      : generateConversationId(),

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),
  setMessages: (msgs) => set({ messages: msgs }),
  setCurrentSteps: (steps) => set({ currentSteps: steps }),
  addStep: (step) =>
    set((state) => ({ currentSteps: [...state.currentSteps, step] })),
  setConversationId: (id) => {
    if (typeof window !== "undefined")
      localStorage.setItem("bio_horizon_conversation_id", id);
    set({ conversationId: id });
  },
  clearConversation: () =>
    set({ messages: [], currentSteps: [] }),
}));
