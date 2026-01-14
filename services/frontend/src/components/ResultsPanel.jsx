export default function ResultsPanel({ title, content, visible, onClose }) {
  if (!visible) return null;

  return (
    <div id="results-section" className="section results-panel" style={{ marginTop: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 id="results-title">{title}</h3>
        <button
          className="btn"
          id="btn-clear-results"
          style={{ padding: '6px 10px', fontSize: '12px' }}
          onClick={onClose}
        >
          Șterge
        </button>
      </div>
      <div
        id="results-content"
        style={{ maxHeight: '760px', overflowY: 'auto' }}
        dangerouslySetInnerHTML={{ __html: content }}
      />
    </div>
  );
}
