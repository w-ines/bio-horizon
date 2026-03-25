type Props = {
  answer?: string;
  loading?: boolean;
};

export default function Result({ answer, loading }: Props) {
  if (loading) {
    return (
      <div className="medical-card" style={{ padding: "1.5rem", marginTop: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{
            width: "20px",
            height: "20px",
            border: "2px solid var(--medical-gray-200)",
            borderTop: "2px solid var(--medical-primary)",
            borderRadius: "50%",
            animation: "spin 1s linear infinite"
          }}></div>
          <span style={{ fontSize: "0.9375rem", color: "var(--medical-gray-700)", fontWeight: "500" }}>Generating medical response…</span>
        </div>
      </div>
    );
  }
  if (!answer) {
    return null;
  }
  return (
    <div className="medical-card animate-fadeIn" style={{ 
      padding: "2rem", 
      marginTop: "1.5rem",
      borderLeft: "4px solid var(--medical-secondary)"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
        <div style={{
          width: "40px",
          height: "40px",
          background: "linear-gradient(135deg, var(--medical-secondary) 0%, var(--medical-accent) 100%)",
          borderRadius: "8px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
          </svg>
        </div>
        <h3 style={{ fontSize: "1.25rem", fontWeight: "600", color: "var(--medical-gray-900)", margin: 0 }}>Medical Response</h3>
      </div>
      <div style={{ 
        whiteSpace: "pre-wrap", 
        fontSize: "0.9375rem", 
        lineHeight: "1.75",
        color: "var(--medical-gray-800)",
        padding: "1rem",
        background: "var(--medical-gray-50)",
        borderRadius: "8px",
        border: "1px solid var(--medical-gray-200)"
      }}>
        {answer}
      </div>
    </div>
  );
}


