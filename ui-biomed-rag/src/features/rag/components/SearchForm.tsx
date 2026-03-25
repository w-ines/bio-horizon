"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useAgentSteps } from "@/features/rag/hooks/use-agent-steps";

type Props = {
  onUserMessage: (userQuery: string) => void;
  onAssistantResponse: (answer: string) => void;
  onStep?: (step: string, preview?: string) => void;
  onLoadingChange?: (loading: boolean) => void;
  conversationId?: string;
};

export default function SearchForm({ onUserMessage, onAssistantResponse, onStep, onLoadingChange, conversationId }: Props) {
  // ============================================================================
  // STATE LOCAL
  // ============================================================================
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [mounted, setMounted] = useState(false);
  
  // Hook pour gérer les steps de l'agent (affichage en temps réel)
  const { resetSteps, addStep, updateSteps, finishDisplaying } = useAgentSteps();
  
  // S'assure que le composant est monté côté client (évite les erreurs SSR)
  useEffect(() => setMounted(true), []);

  // ============================================================================
  // FONCTION PRINCIPALE : Soumission du formulaire
  // ============================================================================
  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    onLoadingChange?.(true);
    
    // Reset les steps affichés avant de commencer une nouvelle requête
    resetSteps();
    
    // Sauvegarder query et files avant de les vider
    const currentQuery = query;
    const currentFiles = [...files];
    
    // Afficher le message utilisateur immédiatement
    onUserMessage(currentQuery);
    
    // Vider l'input et les fichiers immédiatement
    setQuery("");
    setFiles([]);
    
    try {
      const hasFiles = currentFiles.length > 0;
      
      if (hasFiles) {
        // CAS 1: Avec fichiers → Streaming pour voir l'upload + indexation
        console.log("[SearchForm] Mode: Upload + RAG avec streaming");
        await handleStreamingWithFiles(currentQuery, currentFiles);
      } else {
        // CAS 2: Sans fichiers → Streaming aussi (backend retourne NDJSON)
        console.log("[SearchForm] Mode: Web search avec streaming");
        await handleStreamingJsonQuery(currentQuery);
      }
    } catch (err) {
      console.error("[SearchForm] Error:", err);
      setError((err as Error).message || "Request failed");
    } finally {
      onLoadingChange?.(false);
    }
  }

  // ============================================================================
  // CAS 1: STREAMING POUR REQUÊTE JSON (sans fichiers)
  // ============================================================================
  async function handleStreamingJsonQuery(userQuery: string) {
    try {
      console.log("[SearchForm] Sending JSON query with streaming...");
      
      // Appel API avec Content-Type JSON
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          query: userQuery,
          conversation_id: conversationId 
        }),
      });

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      // Le backend retourne maintenant du NDJSON pour tout
      const contentType = response.headers.get("content-type") || "";
      console.log("[SearchForm] Response content-type:", contentType);

      // Le backend retourne toujours du NDJSON maintenant
      if (contentType.includes("application/x-ndjson")) {
        await handleNDJSONStream(response, userQuery);
      } else {
        // Fallback pour compatibilité (ne devrait plus arriver)
        const data = await response.json();
        console.log("[SearchForm] Fallback JSON response:", data);
        
        if (data.steps && Array.isArray(data.steps)) {
          updateSteps(data.steps);
        }
        if (data.answer) {
          onAssistantResponse(data.answer);
        }
      }
      
    } catch (err) {
      console.error("[SearchForm] Streaming JSON request error:", err);
      throw err;
    }
  }

  // ============================================================================
  // CAS 2: STREAMING (avec fichiers uploadés)
  // ============================================================================
  async function handleStreamingWithFiles(userQuery: string, uploadFiles: File[]) {
    try {
      // Prépare le FormData avec query + fichiers
      const formData = new FormData();
      formData.append("query", userQuery);
      if (conversationId) {
        formData.append("conversation_id", conversationId);
      }
      for (const file of uploadFiles) {
        formData.append("files", file);
      }

      console.log("[SearchForm] Sending multipart with streaming...");

      // Appel API avec streaming
      const response = await fetch("/api/ask", {
        method: "POST",
        body: formData,
        // Pas de Content-Type ici, le browser le gère automatiquement
      });

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      // Vérifie le type de réponse
      const contentType = response.headers.get("content-type") || "";
      console.log("[SearchForm] Response content-type:", contentType);

      // Si c'est du NDJSON (streaming), on lit ligne par ligne
      if (contentType.includes("application/x-ndjson") || contentType.includes("text/event-stream")) {
        await handleNDJSONStream(response, userQuery);
      } else {
        // Sinon, c'est une réponse JSON classique
        const data = await response.json();
        console.log("[SearchForm] Regular JSON response:", data);
        
        if (data.steps) {
          updateSteps(data.steps);
        }
        if (data.answer) {
          onAssistantResponse(data.answer);
        }
      }
      
    } catch (err) {
      console.error("[SearchForm] Streaming request error:", err);
      throw err;
    }
  }

  // ============================================================================
  // LECTURE DU STREAM NDJSON (newline-delimited JSON)
  // ============================================================================
  async function handleNDJSONStream(response: Response, userQuery: string) {
    const reader = response.body?.getReader();
    if (!reader) throw new Error("No reader available");

    const decoder = new TextDecoder();
    let buffer = ""; // Buffer pour les lignes incomplètes
    let finalAnswer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log("[SearchForm] Stream completed");
          break;
        }

        // Décode le chunk et ajoute au buffer
        buffer += decoder.decode(value, { stream: true });

        // Traite toutes les lignes complètes dans le buffer
        const lines = buffer.split("\n");
        
        // Garde la dernière ligne incomplète dans le buffer
        buffer = lines.pop() || "";

        // Parse chaque ligne complète
        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!trimmedLine) continue; // Skip les lignes vides

          try {
            // Handle SSE format: "data: {...}" - strip prefix if present (v2)
            let jsonStr = trimmedLine;
            console.log("[SearchForm] Raw line:", trimmedLine.substring(0, 50));
            if (trimmedLine.startsWith('data:')) {
              jsonStr = trimmedLine.slice(5).trim();
              console.log("[SearchForm] Stripped to:", jsonStr.substring(0, 50));
            }
            
            // Skip if not valid JSON (e.g., just "data:" without content, or empty)
            if (!jsonStr || jsonStr === "") continue;
            
            const data = JSON.parse(jsonStr);
            console.log("[SearchForm] Received chunk:", data);

            // TRAITEMENT DES DIFFÉRENTS TYPES DE MESSAGES

            // 1. Steps progressifs (pendant l'upload/indexation)
            if (data.step && typeof data.step === "string") {
              console.log("[SearchForm] Adding step:", data.step);
              addStep(data.step);
              // Appeler onStep pour afficher dans l'interface chatbot
              if (onStep) {
                const preview = data.preview && typeof data.preview === "string" ? data.preview : undefined;
                onStep(data.step, preview);
              }
            }

            // 2. Erreur - handle gracefully without throwing
            if (data.error) {
              const errorMessage = typeof data.error === 'string' 
                ? data.error 
                : (typeof data.error === 'boolean' 
                    ? 'An unknown error occurred' 
                    : JSON.stringify(data.error));
              console.error("[SearchForm] Stream error:", errorMessage);
              console.error("[SearchForm] Full error data:", data);
              // Set error as the final answer instead of throwing
              finishDisplaying();
              finalAnswer = `❌ Error: ${errorMessage}`;
              // Don't throw - continue to display the error gracefully
              break; // Exit the parsing loop
            }

            // 3. Steps de l'agent (array avec un ou plusieurs steps)
            if (data.steps && Array.isArray(data.steps)) {
              console.log("[SearchForm] Received steps:", data.steps);
              // Add each step individually for progressive display
              data.steps.forEach((step: unknown) => {
                if (step && typeof step === "string") {
                  addStep(step);
                }
              });
            }

            // 4. Réponse finale
            if (data.response && !data.error) {
              finalAnswer = data.response;
              console.log("[SearchForm] Final response received:", finalAnswer.substring(0, 100));
            }
            
            // Legacy support for "answer" field
            if (data.answer) {
              finalAnswer = data.answer;
              console.log("[SearchForm] Final answer received:", finalAnswer.substring(0, 100));
            }

          } catch (parseError) {
            console.warn("[SearchForm] Failed to parse line:", line, parseError);
            // Continue avec la ligne suivante
          }
        }
      }

      // Affiche la réponse finale
      if (finalAnswer) {
        finishDisplaying(); // Stop showing "Agent is thinking..."
        onAssistantResponse(finalAnswer);
      } else {
        console.warn("[SearchForm] No final answer received from stream");
      }

    } catch (err) {
      console.error("[SearchForm] Stream reading error:", err);
      // Don't re-throw - set error as final answer
      finishDisplaying();
      const errorMsg = (err as Error).message || "Stream reading failed";
      onAssistantResponse(`❌ Error: ${errorMsg}`);
      return; // Exit gracefully
    }
  }

  // ============================================================================
  // GESTION DES FICHIERS
  // ============================================================================
  
  function removeFile(index: number) {
    setFiles(prev => prev.filter((_, i) => i !== index));
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  // ============================================================================
  // RENDER
  // ============================================================================
  
  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {/* Input Query + Bouton Attach */}
      <div className="flex w-full flex-1 items-center gap-3">
        <div className="relative flex-1">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask your medical question..."
            aria-label="Query"
            style={{ paddingRight: "3rem", fontSize: "0.9375rem" }}
          />

          {/* Bouton pour attacher des fichiers (seulement côté client) */}
          {mounted ? (
            <>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.doc,.docx,.txt"
                aria-label="Files"
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
                className="hidden"
              />
              <button
                type="button"
                aria-label="Attach files"
                title={files.length ? `${files.length} file${files.length > 1 ? "s" : ""} selected` : "Attach files"}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  position: "absolute",
                  right: "0.5rem",
                  top: "50%",
                  transform: "translateY(-50%)",
                  width: "2rem",
                  height: "2rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "6px",
                  border: "none",
                  background: files.length > 0 ? "var(--medical-primary-light)" : "transparent",
                  color: files.length > 0 ? "var(--medical-primary)" : "var(--medical-gray-600)",
                  cursor: "pointer",
                  transition: "all 0.2s ease"
                }}
                onMouseEnter={(e) => {
                  if (files.length === 0) {
                    e.currentTarget.style.background = "var(--medical-gray-100)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (files.length === 0) {
                    e.currentTarget.style.background = "transparent";
                  }
                }}
              >
                {/* Icône de trombone */}
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                </svg>
              </button>
            </>
          ) : null}
        </div>

        {/* Bouton Submit */}
        <Button 
          type="submit" 
          disabled={!query.trim() && files.length === 0}
          style={{ 
            minWidth: "120px",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem"
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          Search
        </Button>
      </div>

      {/* Liste des fichiers sélectionnés */}
      {files.length > 0 && (
        <div className="medical-card" style={{ padding: "1rem", background: "var(--medical-primary-light)" }}>
          <div style={{ fontSize: "0.8125rem", fontWeight: "600", color: "var(--medical-primary-dark)", marginBottom: "0.75rem" }}>
            {files.length} file{files.length > 1 ? 's' : ''} selected:
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {files.map((file, index) => (
              <div
                key={index}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "0.5rem",
                  padding: "0.75rem 1rem",
                  background: "white",
                  borderRadius: "8px",
                  fontSize: "0.875rem",
                  border: "1px solid var(--medical-gray-200)"
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", minWidth: 0, flex: 1 }}>
                  {/* Icône fichier */}
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--medical-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--medical-gray-900)" }}>{file.name}</span>
                  <span style={{ fontSize: "0.75rem", color: "var(--medical-gray-600)", flexShrink: 0 }}>
                    ({formatFileSize(file.size)})
                  </span>
                </div>
                {/* Bouton supprimer */}
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  aria-label={`Remove ${file.name}`}
                  style={{
                    flexShrink: 0,
                    borderRadius: "6px",
                    padding: "0.25rem",
                    border: "none",
                    background: "transparent",
                    color: "var(--medical-gray-400)",
                    cursor: "pointer",
                    transition: "all 0.2s ease"
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "#fee2e2";
                    e.currentTarget.style.color = "var(--medical-error)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "transparent";
                    e.currentTarget.style.color = "var(--medical-gray-400)";
                  }}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Affichage des erreurs */}
      {error ? (
        <div className="medical-card" style={{ padding: "1rem", background: "#fef2f2", borderColor: "#fecaca" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--medical-error)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span style={{ fontSize: "0.875rem", color: "var(--medical-error)", fontWeight: "500" }}>{error}</span>
          </div>
        </div>
      ) : null}
    </form>
  );
}