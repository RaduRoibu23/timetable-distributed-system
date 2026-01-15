import React, { useEffect, useState } from "react";
import { apiGet } from "../services/apiService";

export default function AuditLogsScreen({ accessToken }) {
  const [limit, setLimit] = useState(50);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState(null);
  const [data, setData] = useState(null);

  async function load() {
    setLoading(true);
    setBanner(null);
    try {
      const resp = await apiGet(`/audit-logs?limit=${limit}`, accessToken);
      setData(resp);
      setBanner({ type: "ok", text: "Audit logs încărcate." });
    } catch (e) {
      setBanner({ type: "error", text: String(e.message || e) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="contentCard">
      <div className="contentHeader">
        <div>
          <div className="title">Audit logs</div>
          <div className="subtitle">Ultimele evenimente (limit).</div>
        </div>

        <div className="headerActions">
          <label className="label">Limit</label>
          <input
            className="input"
            type="number"
            min={1}
            max={500}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          />
          <button className="btn primary" onClick={load} disabled={loading}>
            Refresh
          </button>
        </div>
      </div>

      {banner && <div className={`banner ${banner.type}`}>{banner.text}</div>}

      {data && <pre className="jsonBox">{JSON.stringify(data, null, 2)}</pre>}
    </section>
  );
}
