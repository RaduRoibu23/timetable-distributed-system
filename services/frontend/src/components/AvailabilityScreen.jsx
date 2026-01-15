import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../services/apiService";

const WEEKDAY = ["Luni", "Marți", "Miercuri", "Joi", "Vineri"];

export default function AvailabilityScreen({ accessToken }) {
  const [tab, setTab] = useState("teacher"); // teacher | room
  const [teachers, setTeachers] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [id, setId] = useState("");
  const [weekday, setWeekday] = useState(0);
  const [indexInDay, setIndexInDay] = useState(1);
  const [available, setAvailable] = useState(true);

  const [banner, setBanner] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        let t = [];
        let r = [];
        try { t = await apiGet("/teachers", accessToken); } catch { t = []; }
        try { r = await apiGet("/rooms", accessToken); } catch { r = []; }
        setTeachers(Array.isArray(t) ? t : []);
        setRooms(Array.isArray(r) ? r : []);

        if (tab === "teacher" && t?.[0]) setId(String(t[0].id));
        if (tab === "room" && r?.[0]) setId(String(r[0].id));
      } catch (e) {
        setBanner({ type: "error", text: String(e.message || e) });
      }
    })();
  }, [accessToken]);

  useEffect(() => {
    if (tab === "teacher" && teachers[0]) setId(String(teachers[0].id));
    if (tab === "room" && rooms[0]) setId(String(rooms[0].id));
  }, [tab, teachers, rooms]);

  async function save() {
    if (!id) return;
    setLoading(true);
    setBanner(null);
    try {
      const path =
        tab === "teacher"
          ? `/teachers/${Number(id)}/availability`
          : `/rooms/${Number(id)}/availability`;

      await apiPost(path, { weekday, index_in_day: indexInDay, available }, accessToken);
      setBanner({ type: "ok", text: "Disponibilitatea a fost salvată." });
    } catch (e) {
      setBanner({ type: "error", text: String(e.message || e) });
    } finally {
      setLoading(false);
    }
  }

  const list = tab === "teacher" ? teachers : rooms;

  return (
    <section className="contentCard">
      <div className="contentHeader">
        <div>
          <div className="title">Disponibilități</div>
          <div className="subtitle">Setezi availability pentru profesor sau sală.</div>
        </div>
        <div className="headerActions">
          <button className={`btn ${tab === "teacher" ? "primary" : ""}`} onClick={() => setTab("teacher")}>Teacher</button>
          <button className={`btn ${tab === "room" ? "primary" : ""}`} onClick={() => setTab("room")}>Room</button>
        </div>
      </div>

      {banner && <div className={`banner ${banner.type}`}>{banner.text}</div>}

      <div className="row row-wrap" style={{ gap: 10 }}>
        <div className="row">
          <label className="label">{tab === "teacher" ? "Profesor" : "Sală"}</label>
          {list.length > 0 ? (
            <select className="select" value={id} onChange={(e) => setId(e.target.value)} disabled={loading}>
              {list.map(x => (
                <option key={x.id} value={String(x.id)}>
                  {x.name ?? x.full_name ?? x.code ?? `${tab} ${x.id}`}
                </option>
              ))}
            </select>
          ) : (
            <input className="input" type="number" value={id} onChange={(e) => setId(e.target.value)} placeholder="id" />
          )}
        </div>

        <div className="row">
          <label className="label">Zi</label>
          <select className="select" value={weekday} onChange={(e) => setWeekday(Number(e.target.value))} disabled={loading}>
            {WEEKDAY.map((d, i) => (
              <option key={i} value={i}>{d}</option>
            ))}
          </select>
        </div>

        <div className="row">
          <label className="label">Slot</label>
          <input
            className="input"
            type="number"
            min={1}
            max={12}
            value={indexInDay}
            onChange={(e) => setIndexInDay(Number(e.target.value))}
            disabled={loading}
            style={{ width: 110 }}
          />
        </div>

        <div className="row">
          <label className="label">Available</label>
          <input
            type="checkbox"
            checked={available}
            onChange={(e) => setAvailable(e.target.checked)}
            disabled={loading}
          />
        </div>

        <button className="btn primary" onClick={save} disabled={loading || !id}>
          Save
        </button>
      </div>
    </section>
  );
}
