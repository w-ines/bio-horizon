"use client";

import { useState, useRef, useEffect } from "react";
import { useRagStore } from "@/stores/ragStore";
import SearchForm from "@/features/rag/components/SearchForm";
import { AgentStepsProvider } from "@/features/rag/hooks/use-agent-steps";
import { linkifyText } from "@/lib/linkify";

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

export default function RagPageContent() {
  const {
    messages, addMessage, setMessages,
    currentSteps, setCurrentSteps, addStep,
    conversationId, setConversationId,
    clearConversation,
  } = useRagStore();
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll vers le bas quand de nouveaux messages arrivent
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentSteps]);

  function handleUserMessage(userQuery: string) {
    const userMsg: Message = {
      id: `msg_${Date.now()}_user`,
      role: "user",
      content: userQuery,
      timestamp: new Date(),
    };
    addMessage(userMsg);
  }

  function handleAssistantResponse(assistantResponse: string) {
    const assistantMsg: Message = {
      id: `msg_${Date.now()}_assistant`,
      role: "assistant",
      content: assistantResponse,
      timestamp: new Date(),
    };
    addMessage(assistantMsg);
    setCurrentSteps([]); // Clear steps after message is complete
  }

  function handleNewMessage(userQuery: string, assistantResponse: string) {
    // Legacy: pour compatibilité, mais on préfère handleUserMessage + handleAssistantResponse
    handleUserMessage(userQuery);
    handleAssistantResponse(assistantResponse);
  }

  function handleStep(step: string, preview?: string) {
    const stepObj: AgentStep = {
      id: `step_${Date.now()}_${Math.random()}`,
      content: step,
      preview: preview,
      timestamp: new Date(),
    };
    addStep(stepObj);
  }

  function startNewChat() {
    const newId = `rag_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    setConversationId(newId);
    clearConversation();
  }

  function clearChat() {
    if (confirm("Start a new conversation?")) {
      startNewChat();
    }
  }

  return (
    <AgentStepsProvider>
      <div style={{ 
        minHeight: "100vh", 
        background: "#f8fafc",
        display: "flex",
        flexDirection: "column"
      }}>
        {/* Header */}
        <header style={{
          background: "white",
          borderBottom: "1px solid #e2e8f0",
          padding: "1rem 1.5rem",
          flexShrink: 0
        }}>
          <div style={{ maxWidth: "1200px", margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <div style={{
                width: "36px",
                height: "36px",
                background: "linear-gradient(135deg, #38bdf8, #34d399)",
                borderRadius: "10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <div>
                <h1 style={{ fontSize: "1.125rem", fontWeight: "700", color: "#0f172a", margin: 0, letterSpacing: "-0.025em" }}>
                  Bio Horizon Chat
                </h1>
                <p style={{ fontSize: "0.75rem", color: "#64748b", margin: 0 }}>
                  Conversational AI with RAG
                </p>
              </div>
            </div>
            {messages.length > 0 && (
              <button
                onClick={clearChat}
                style={{
                  padding: "0.5rem 1rem",
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  background: "white",
                  color: "#64748b",
                  fontSize: "0.875rem",
                  fontWeight: "500",
                  cursor: "pointer",
                  transition: "all 0.2s"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "#ef4444";
                  e.currentTarget.style.color = "#ef4444";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "#e2e8f0";
                  e.currentTarget.style.color = "#64748b";
                }}
              >
                Clear
              </button>
            )}
          </div>
        </header>

        {/* Messages Container */}
        <div style={{
          flex: 1,
          overflowY: "auto",
          padding: "2rem 1rem"
        }}>
          <div style={{
            maxWidth: "1200px",
            margin: "0 auto",
            display: "flex",
            flexDirection: "column",
            gap: "1.5rem"
          }}>
            {messages.length === 0 && currentSteps.length === 0 ? (
              <div style={{ textAlign: "center", padding: "3rem 1rem", color: "#94a3b8" }}>
                <div style={{
                  width: "64px",
                  height: "64px",
                  margin: "0 auto 1.5rem",
                  background: "linear-gradient(135deg, #38bdf8, #34d399)",
                  borderRadius: "20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: 0.2
                }}>
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                </div>
                <h2 style={{ fontSize: "1.25rem", fontWeight: "600", color: "#475569", margin: "0 0 0.5rem 0" }}>
                  Start a conversation
                </h2>
                <p style={{ fontSize: "0.9375rem", color: "#94a3b8", margin: 0 }}>
                  Ask questions, upload documents, and get AI-powered answers with full context.
                </p>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    style={{
                      display: "flex",
                      gap: "1rem",
                      alignItems: "flex-start"
                    }}
                  >
                    {/* Avatar */}
                    <div style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      flexShrink: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      background: msg.role === "user" 
                        ? "#e0f2fe" 
                        : "linear-gradient(135deg, #38bdf8, #34d399)",
                      color: msg.role === "user" ? "#0369a1" : "white"
                    }}>
                      {msg.role === "user" ? (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                          <circle cx="12" cy="7" r="4" />
                        </svg>
                      ) : (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 2v20M2 12h20" />
                          <circle cx="12" cy="12" r="10" />
                        </svg>
                      )}
                    </div>

                    {/* Message Content */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: "0.8125rem",
                        fontWeight: "600",
                        color: "#475569",
                        marginBottom: "0.5rem"
                      }}>
                        {msg.role === "user" ? "You" : "Bio Horizon Assistant"}
                      </div>
                      <div style={{
                        fontSize: "0.9375rem",
                        color: "#1e293b",
                        lineHeight: "1.65",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word"
                      }}>
                        {msg.role === "assistant" ? linkifyText(msg.content) : msg.content}
                      </div>
                    </div>
                  </div>
                ))}
                
                {/* Current agent steps (thinking process) */}
                {currentSteps.length > 0 && (
                  <div style={{
                    display: "flex",
                    gap: "1rem",
                    alignItems: "flex-start"
                  }}>
                    <div style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      flexShrink: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      background: "linear-gradient(135deg, #38bdf8, #34d399)",
                      color: "white"
                    }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 2v20M2 12h20" />
                        <circle cx="12" cy="12" r="10" />
                      </svg>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "0.8125rem", fontWeight: "600", color: "#475569", marginBottom: "0.5rem" }}>
                        Bio Horizon Assistant
                      </div>
                      <div style={{
                        background: "#f8fafc",
                        borderRadius: "8px",
                        padding: "0.75rem 1rem",
                        border: "1px solid #e2e8f0"
                      }}>
                        {currentSteps.map((step, idx) => (
                          <div key={step.id} style={{
                            marginBottom: idx < currentSteps.length - 1 ? "0.75rem" : 0
                          }}>
                            <div style={{
                              fontSize: "0.875rem",
                              color: "#64748b",
                              fontFamily: "monospace",
                              marginBottom: step.preview ? "0.5rem" : 0
                            }}>
                              {step.content}
                            </div>
                            {step.preview && (
                              <div style={{
                                fontSize: "0.8125rem",
                                color: "#94a3b8",
                                fontFamily: "monospace",
                                background: "#f1f5f9",
                                padding: "0.5rem",
                                borderRadius: "4px",
                                borderLeft: "2px solid #cbd5e1",
                                whiteSpace: "pre-wrap",
                                wordBreak: "break-word",
                                maxHeight: "150px",
                                overflowY: "auto"
                              }}>
                                {step.preview}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </>
            )}
          </div>
        </div>

        {/* Input Area (Fixed at bottom) */}
        <div style={{
          background: "white",
          borderTop: "1px solid #e2e8f0",
          padding: "1.5rem",
          flexShrink: 0
        }}>
          <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
            <SearchForm 
              onUserMessage={handleUserMessage}
              onAssistantResponse={handleAssistantResponse}
              onStep={handleStep}
              onLoadingChange={setLoading}
              conversationId={conversationId}
            />
          </div>
        </div>
      </div>
    </AgentStepsProvider>
  );
}


