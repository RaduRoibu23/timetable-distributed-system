import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../services/apiService";

export default function CurriculumScreen({ accessToken }) {
  const [classes, setClasses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [banner, setBanner] = useState(null);
  const [loading, setLoading] = useState(false);

  const [classId, setClassId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [teacherId, setTeacherId] = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const c = await apiGet("/classes", accessToken);
        const s = await apiGet("/subjects", accessToken);

        // Teachers endpoint (likely exists)
        let t = [];
        try { t = await apiGet("/teachers", accessToken); } catch { t = []; }

        const cl = Array.isArray(c) ? c : [];
        const sb = Array.isArray(s) ? s : [];
        const th = Array.isArray(t) ? t : [];

        setClasses(cl);
        setSubjects(sb);
        setTeachers(th);

        if (cl[0]) setClassId(String(cl[0].id));
        if (sb[0]) setSubjectId(String(sb[0].id));
        if (th[0]) setTeacherId(String(th[0].id));
      } catch (e) {
        setBanner({ type: "error", text: String(e.message || e) });
      } finally {
        setLoading(false);
      }
    })();
  }, [accessToken]);

  async function assign() {
    if (!classId || !subjectId || !teacherId) return;
    setLoading(true);
    setBanner(null);
    try {
      await apiPost(`/subjects/${Number(subjectId)}/teachers`, {
        class_id: Number(classId),
        teacher_id: Number(teacherId),
      }, accessToken);

      setBanner({ type: "ok", text: "Maparea a fost salvată (materie→profesor pentru clasa selectată)." });
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
          <div className="title">Curriculum (Materie→Profesor)</div>
          <div className="subtitle">Asignezi profesor unei materii pentru o clasă.</div>
        </div>
      </div>

      {banner && <div className={`banner ${banner.type}`}>{banner.text}</div>}

      <div className="row row-wrap" style={{ gap: 10 }}>
        <div className="row">
          <label className="label">Clasă</label>
          <select className="select" value={classId} onChange={(e) => setClassId(e.target.value)} disabled={loading}>
            {classes.map(c => (
              <option key={c.id} value={String(c.id)}>
                {c.name ?? c.class_name ?? `Clasa ${c.id}`}
              </option>
            ))}
          </select>
        </div>

        <div className="row">
          <label className="label">Materie</label>
          <select className="select" value={subjectId} onChange={(e) => setSubjectId(e.target.value)} disabled={loading}>
            {subjects.map(s => (
              <option key={s.id} value={String(s.id)}>
                {s.name ?? `Materie ${s.id}`}
              </option>
            ))}
          </select>
        </div>

        <div className="row">
          <label className="label">Profesor</label>

          {teachers.length > 0 ? (
            <select className="select" value={teacherId} onChange={(e) => setTeacherId(e.target.value)} disabled={loading}>
              {teachers.map(t => (
                <option key={t.id} value={String(t.id)}>
                  {t.name ?? t.full_name ?? `Teacher ${t.id}`}
                </option>
              ))}
            </select>
          ) : (
            <input
              className="input"
              type="number"
              value={teacherId}
              onChange={(e) => setTeacherId(e.target.value)}
              placeholder="teacher_id"
              disabled={loading}
              style={{ width: 150 }}
            />
          )}
        </div>

        <button className="btn primary" onClick={assign} disabled={loading || !classId || !subjectId || !teacherId}>
          Assign
        </button>
      </div>
    </section>
  );
}
