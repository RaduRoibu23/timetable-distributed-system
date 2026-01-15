import React, { useEffect, useState } from "react";
import { apiGet } from "../services/apiService";

export default function StatsScreen({ accessToken }) {
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState(null);
  const [data, setData] = useState(null);

  async function load() {
    setLoading(true);
    setBanner(null);
    try {
      const resp = await apiGet("/timetables/stats", accessToken);
      setData(resp);
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
          <div className="title">Stats</div>
          <div className="subtitle">Indicatori / agregări pentru orare.</div>
        </div>
        <div className="headerActions">
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
