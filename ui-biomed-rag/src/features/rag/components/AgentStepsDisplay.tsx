"use client";

import { useAgentSteps } from "@/features/rag/hooks/use-agent-steps";
import { ReactNode } from "react";

// Simple markdown-like renderer without external dependencies
function MarkdownRenderer({ content }: { content: string }) {
  // Parse simple markdown patterns
  const renderContent = (text: string) => {
    const parts: ReactNode[] = [];
    let currentIndex = 0;
    let key = 0;

    // Match **bold** text
    const boldRegex = /\*\*(.+?)\*\*/g;
    // Match `code` text
    const codeRegex = /`([^`]+)`/g;
    // Match code blocks ```language\ncode\n```
    const codeBlockRegex = /```(\w+)?\n([\s\S]+?)\n```/g;

    // First, handle code blocks
    let match;
    const codeBlocks: Array<{ start: number; end: number; content: string; language?: string }> = [];
    while ((match = codeBlockRegex.exec(text)) !== null) {
      codeBlocks.push({
        start: match.index,
        end: match.index + match[0].length,
        language: match[1],
        content: match[2]
      });
    }

    // Process text with inline formatting
    const processInline = (str: string, startKey: number) => {
      const elements: ReactNode[] = [];
      let lastIndex = 0;
      let localKey = startKey;

      // Combine bold and code patterns
      const combinedRegex = /(\*\*(.+?)\*\*)|(`([^`]+)`)/g;
      let inlineMatch;

      while ((inlineMatch = combinedRegex.exec(str)) !== null) {
        // Add text before match
        if (inlineMatch.index > lastIndex) {
          elements.push(str.substring(lastIndex, inlineMatch.index));
        }

        if (inlineMatch[2]) {
          // Bold text
          elements.push(
            <strong key={`bold-${localKey++}`} className="font-semibold text-foreground">
              {inlineMatch[2]}
            </strong>
          );
        } else if (inlineMatch[4]) {
          // Inline code
          elements.push(
            <code key={`code-${localKey++}`} className="rounded bg-gray-200 dark:bg-gray-800 px-1 py-0.5 text-xs">
              {inlineMatch[4]}
            </code>
          );
        }

        lastIndex = inlineMatch.index + inlineMatch[0].length;
      }

      // Add remaining text
      if (lastIndex < str.length) {
        elements.push(str.substring(lastIndex));
      }

      return elements.length > 0 ? elements : str;
    };

    // Process text with code blocks
    if (codeBlocks.length > 0) {
      codeBlocks.forEach((block, idx) => {
        // Add text before code block
        if (block.start > currentIndex) {
          const textBefore = text.substring(currentIndex, block.start);
          parts.push(
            <span key={`text-${key++}`}>
              {processInline(textBefore, key)}
            </span>
          );
        }

        // Add code block
        parts.push(
          <pre key={`block-${key++}`} className="mt-2 overflow-x-auto rounded bg-gray-900 p-2 text-xs">
            <code className="text-gray-100">{block.content}</code>
          </pre>
        );

        currentIndex = block.end;
      });

      // Add remaining text
      if (currentIndex < text.length) {
        const textAfter = text.substring(currentIndex);
        parts.push(
          <span key={`text-${key++}`}>
            {processInline(textAfter, key)}
          </span>
        );
      }
    } else {
      // No code blocks, just process inline
      return <>{processInline(text, 0)}</>;
    }

    return <>{parts}</>;
  };

  return <div className="whitespace-pre-wrap">{renderContent(content)}</div>;
}

export default function AgentStepsDisplay() {
  const { agentSteps, isDisplayingSteps } = useAgentSteps();

  if (agentSteps.length === 0 && !isDisplayingSteps) {
    return null;
  }

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <div className="medical-card" style={{ padding: "1.5rem", borderLeft: "4px solid var(--medical-accent)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div style={{
              width: "36px",
              height: "36px",
              background: "linear-gradient(135deg, var(--medical-accent) 0%, var(--medical-primary) 100%)",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
            </div>
            <h3 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--medical-gray-900)", margin: 0 }}>
              Reasoning Steps
            </h3>
          </div>
          {agentSteps.length > 0 && (
            <span className="medical-badge" style={{ background: "var(--medical-accent)", color: "white" }}>
              {agentSteps.length} step{agentSteps.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {agentSteps.map((step, index) => (
            <div
              key={index}
              className="animate-fadeIn"
              style={{
                padding: "1rem",
                background: "var(--medical-primary-light)",
                borderRadius: "8px",
                border: "1px solid var(--medical-primary)",
                transition: "all 0.2s ease"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--medical-primary-dark)";
                e.currentTarget.style.boxShadow = "0 2px 4px rgba(0, 102, 204, 0.1)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--medical-primary)";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              <div style={{ display: "flex", alignItems: "start", gap: "0.75rem" }}>
                <span style={{
                  fontSize: "0.75rem",
                  fontWeight: "700",
                  color: "var(--medical-primary-dark)",
                  background: "white",
                  padding: "0.25rem 0.5rem",
                  borderRadius: "4px",
                  minWidth: "2rem",
                  textAlign: "center",
                  marginTop: "0.125rem"
                }}>
                  #{index + 1}
                </span>
                <div style={{ flex: 1, fontSize: "0.875rem", color: "var(--medical-gray-800)" }}>
                  <MarkdownRenderer content={step} />
                </div>
              </div>
            </div>
          ))}
          {isDisplayingSteps && (
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem", fontSize: "0.875rem", color: "var(--medical-gray-600)" }}>
              <div style={{
                width: "16px",
                height: "16px",
                border: "2px solid var(--medical-gray-200)",
                borderTop: "2px solid var(--medical-accent)",
                borderRadius: "50%",
                animation: "spin 1s linear infinite"
              }}></div>
              <span>Analyzing...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
