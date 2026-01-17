import React, { useEffect, useState, useMemo } from "react";
import { apiGet } from "../services/apiService";

export default function StudentsScreen({ accessToken }) {
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState(null);
  const [students, setStudents] = useState([]);
  const [sortBy, setSortBy] = useState(null); // 'last_name' | 'class_name' | null

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

  const sortedStudents = useMemo(() => {
    if (!sortBy) return students;
    const sorted = [...students];
    sorted.sort((a, b) => {
      if (sortBy === 'last_name') {
        const aName = (a.last_name || a.lastName || '').toLowerCase();
        const bName = (b.last_name || b.lastName || '').toLowerCase();
        return aName.localeCompare(bName);
      } else if (sortBy === 'class_name') {
        const aClass = (a.class_name || a.className || '').toLowerCase();
        const bClass = (b.class_name || b.className || '').toLowerCase();
        return aClass.localeCompare(bClass);
      }
      return 0;
    });
    return sorted;
  }, [students, sortBy]);

  return (
    <section className="contentCard">
      <div className="contentHeader">
        <div>
          <div className="title">Lista Studenti</div>
          <div className="subtitle">Toti studentii din sistem.</div>
        </div>
        <div className="headerActions">
          <button
            className={`btn ${sortBy === 'last_name' ? 'primary' : ''}`}
            onClick={() => setSortBy(sortBy === 'last_name' ? null : 'last_name')}
            disabled={loading || students.length === 0}
          >
            Sort by Name
          </button>
          <button
            className={`btn ${sortBy === 'class_name' ? 'primary' : ''}`}
            onClick={() => setSortBy(sortBy === 'class_name' ? null : 'class_name')}
            disabled={loading || students.length === 0}
          >
            Sort by Class
          </button>
          {sortBy && (
            <button
              className="btn"
              onClick={() => setSortBy(null)}
              disabled={loading}
            >
              Clear Sort
            </button>
          )}
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
              {sortedStudents.map((s) => (
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
