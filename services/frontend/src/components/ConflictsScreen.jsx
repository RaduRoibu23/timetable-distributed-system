import React, { useState } from "react";
import { apiGet } from "../services/apiService";

export default function ConflictsScreen({ accessToken }) {
  const [jobId, setJobId] = useState("");
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState(null);
  const [data, setData] = useState(null);

  async function load() {
    if (!jobId.trim()) return;
    setLoading(true);
    setBanner(null);
    setData(null);
    try {
      const resp = await apiGet(`/timetables/jobs/${jobId.trim()}/conflicts`, accessToken);
      setData(resp);
      setBanner({ type: "ok", text: "Conflicte încărcate." });
    } catch (e) {
      setBanner({ type: "error", text: String(e.message || e) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="contentCard">
      <div className="contentHeader">
        <div>
          <div className="title">Conflicte job</div>
          <div className="subtitle">Verifică rapoartele de conflict pentru un job de generare.</div>
        </div>

        <div className="headerActions">
          <label className="label">Job ID</label>
          <input className="input" value={jobId} onChange={(e) => setJobId(e.target.value)} placeholder="ex: 123" />
          <button className="btn primary" onClick={load} disabled={loading || !jobId.trim()}>
            Load
          </button>
        </div>
      </div>

      {banner && <div className={`banner ${banner.type}`}>{banner.text}</div>}

      {data && (
        <pre className="jsonBox">{JSON.stringify(data, null, 2)}</pre>
      )}
    </section>
  );
}
