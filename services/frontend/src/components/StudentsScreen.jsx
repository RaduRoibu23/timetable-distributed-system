import React, { useEffect, useState } from "react";
import { apiGet } from "../services/apiService";

export default function StudentsScreen({ accessToken }) {
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState(null);
  const [students, setStudents] = useState([]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setBanner(null);
      try {
        const data = await apiGet("/profiles?role=student", accessToken);
        setStudents(Array.isArray(data) ? data : []);
      } catch (e) {
        setBanner({ type: "error", text: String(e?.message || e) });
      } finally {
        setLoading(false);
      }
    })();
  }, [accessToken]);

  return (
    <section className="contentCard">
      <div className="contentHeader">
        <div>
          <div className="title">Lista Studenti</div>
          <div className="subtitle">Toti studentii din sistem.</div>
        </div>
      </div>

      {banner && <div className={`banner ${banner.type}`}>{banner.text}</div>}

      {loading ? (
        <div className="mutedBlock">Loading...</div>
      ) : students.length === 0 ? (
        <div className="mutedBlock">Nu exista studenti.</div>
      ) : (
        <div className="tableWrap">
          <table className="dataTable">
            <thead>
              <tr>
                <th>Username</th>
                <th>Nume</th>
                <th>Prenume</th>
                <th>Clasa</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.id || s.username}>
                  <td>{s.username || "—"}</td>
                  <td>{s.last_name || s.lastName || "—"}</td>
                  <td>{s.first_name || s.firstName || "—"}</td>
                  <td>{s.class_name || s.className || (s.class_id ? `Clasa ${s.class_id}` : "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
