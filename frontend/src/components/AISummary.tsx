import React from 'react';

interface AISummaryProps {
  summary: string;
}

const AISummary: React.FC<AISummaryProps> = ({ summary }) => {
  if (!summary) return null;

  return (
    <div
      style={{
        marginTop: '12px',
        padding: '10px',
        fontFamily: "'Inconsolata', monospace",
        fontSize: 12,
        color: 'var(--accent)',
        backgroundColor: 'var(--bg-light)',
        border: '1px solid var(--accent)',
        borderRadius: 4,
        whiteSpace: 'pre-wrap',
        overflow: 'auto',
        height: '100%'
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: 'var(--muted)',
          marginBottom: 6,
          fontStyle: 'italic',
        }}
      >
        AI-generated summary — verify outputs independently
      </div>
      {summary}
    </div>
  );
};

export default AISummary;
