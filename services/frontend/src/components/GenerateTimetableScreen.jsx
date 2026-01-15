import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../services/apiService";

export default function GenerateTimetableScreen({ accessToken }) {
  const [classes, setClasses] = useState([]);
  const [classId, setClassId] = useState("");
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState(null);
  const [jobIds, setJobIds] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const c = await apiGet("/classes", accessToken);
        const list = Array.isArray(c) ? c : [];
        setClasses(list);
        if (list.length > 0) setClassId(String(list[0].id));
      } catch (e) {
        setBanner({ type: "error", text: String(e.message || e) });
      }
    })();
  }, [accessToken]);

  async function generate() {
    if (!classId) return;
    setLoading(true);
    setBanner(null);
    try {
      const resp = await apiPost("/timetables/generate", { class_id: Number(classId) }, accessToken);
      const ids = resp?.job_ids ?? resp?.jobIds ?? [];
      setJobIds(Array.isArray(ids) ? ids : []);
      setBanner({ type: "ok", text: "Job de generare creat." });
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
          <div className="title">Generează orar</div>
          <div className="subtitle">Creează job de generare pentru o clasă.</div>
        </div>
        <div className="headerActions">
          <label className="label">Clasă</label>
          <select className="select" value={classId} onChange={(e) => setClassId(e.target.value)} disabled={loading}>
            {classes.map((c) => (
              <option key={c.id} value={String(c.id)}>
                {c.name ?? c.class_name ?? `Clasa ${c.id}`}
              </option>
            ))}
          </select>

          <button className="btn primary" onClick={generate} disabled={loading || !classId}>
            Generate
          </button>
        </div>
      </div>

      {banner && <div className={`banner ${banner.type}`}>{banner.text}</div>}

      {jobIds.length > 0 && (
        <div className="mutedBlock">
          <div style={{ marginBottom: 8, color: "var(--text)", fontWeight: 800 }}>Job IDs:</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {jobIds.map((id) => (
              <li key={id}>{id}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
