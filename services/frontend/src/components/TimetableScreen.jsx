import React, { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch } from "../services/apiService";

const WEEKDAY = ["Luni", "Marți", "Miercuri", "Joi", "Vineri"];
const TIME_LABELS = {
    1: "13:00–14:00",
    2: "14:00–15:00",
    3: "15:00–16:00",
    4: "16:00–17:00",
    5: "17:00–18:00",
    6: "18:00–19:00",
    7: "19:00–20:00",
  };
  

function canEdit(roles) {
  // ajustezi aici dacă vrei să permită și secretariat/professor etc.
  const allowed = ["secretariat", "scheduler", "admin", "sysadmin"];
  return roles.some(r => allowed.includes(r));
}

function normalizeRoom(val) {
  if (val === "" || val === undefined) return null;
  if (val === null) return null;
  const n = Number(val);
  return Number.isFinite(n) ? n : null;
}

export default function TimetableScreen({ accessToken, roles, mode }) {
  // mode: "my" | "class"
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState(null);

  const [classes, setClasses] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState(1);

  const [subjects, setSubjects] = useState([]);
  const subjectsById = useMemo(() => {
    const m = new Map();
    subjects.forEach(s => m.set(s.id, s));
    return m;
  }, [subjects]);

  const [entries, setEntries] = useState([]);
  const [original, setOriginal] = useState([]);
  const [isEditing, setIsEditing] = useState(false);

  const editingAllowed = canEdit(roles);

  async function loadSubjects() {
    const s = await apiGet("/subjects", accessToken);
    setSubjects(Array.isArray(s) ? s : []);
  }

  async function loadClasses() {
    const c = await apiGet("/classes", accessToken);
    setClasses(Array.isArray(c) ? c : []);
    if (Array.isArray(c) && c.length > 0) {
      setSelectedClassId(c[0].id);
    }
  }

  async function loadTimetableForClass(classId) {
    const data = await apiGet(`/timetables/classes/${classId}`, accessToken);
    const list = Array.isArray(data) ? data : [];
    // sort minimal: weekday, index_in_day
    list.sort((a, b) => (a.weekday - b.weekday) || (a.index_in_day - b.index_in_day));
    setEntries(list);
    setOriginal(JSON.parse(JSON.stringify(list)));
  }

  // Minimal: "orarul meu" încearcă să deducă class_id din /me.
  // Dacă /me nu conține class_id, UI va arăta mesaj clar.
  async function loadMyTimetable() {
    const me = await apiGet("/me", accessToken);
    const classId = me?.class_id ?? me?.classId ?? me?.class?.id;
    if (!classId) {
      setEntries([]);
      setOriginal([]);
      setBanner({
        type: "warn",
        text: "Nu pot determina clasa ta din /me (lipsește class_id). Pentru student trebuie fie /me să includă class_id, fie un endpoint dedicat (ex: /timetables/me).",
      });
      return;
    }
    await loadTimetableForClass(classId);
  }

  async function initialLoad() {
    setLoading(true);
    setBanner(null);
    try {
      await loadSubjects();
      if (mode === "class") {
        await loadClasses();
      }
    } catch (e) {
      setBanner({ type: "error", text: String(e.message || e) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    initialLoad();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    // auto-load data when mode changes / class changes
    (async () => {
      setBanner(null);
      setLoading(true);
      try {
        if (mode === "class") {
          await loadTimetableForClass(selectedClassId);
        } else {
          await loadMyTimetable();
        }
      } catch (e) {
        setBanner({ type: "error", text: String(e.message || e) });
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, selectedClassId]);

  function beginEdit() {
    setIsEditing(true);
    setBanner(null);
  }

  function cancelEdit() {
    setIsEditing(false);
    // revert
    setEntries(JSON.parse(JSON.stringify(original)));
    setBanner(null);
  }

  function updateEntryLocal(entryId, patch) {
    setEntries(prev =>
      prev.map(e => (e.id === entryId ? { ...e, ...patch } : e))
    );
  }

  function computeChanges() {
    const origById = new Map(original.map(e => [e.id, e]));
    const changed = [];
    for (const e of entries) {
      const o = origById.get(e.id);
      if (!o) continue;
      const subjectChanged = e.subject_id !== o.subject_id;
      const roomChanged = (e.room_id ?? null) !== (o.room_id ?? null);
      if (subjectChanged || roomChanged) {
        const body = { version: e.version };
        if (subjectChanged) body.subject_id = e.subject_id;
        if (roomChanged) body.room_id = e.room_id ?? null;
        changed.push({ id: e.id, body });
      }
    }
    return changed;
  }

  async function saveAll() {
    setLoading(true);
    setBanner(null);

    const changes = computeChanges();
    if (changes.length === 0) {
      setBanner({ type: "ok", text: "Nu există modificări de salvat." });
      setLoading(false);
      setIsEditing(false);
      return;
    }

    try {
      for (const ch of changes) {
        await apiPatch(`/timetables/entries/${ch.id}`, ch.body, accessToken);
      }
      setBanner({ type: "ok", text: "Modificările au fost salvate." });
      setIsEditing(false);

      // refetch (global truth)
      if (mode === "class") {
        await loadTimetableForClass(selectedClassId);
      } else {
        await loadMyTimetable();
      }
    } catch (e) {
      const msg = String(e.message || e);

      // Heuristic: optimistic lock conflict => refresh suggestion
      if (msg.includes("API error 409") || msg.includes("API error 412") || msg.includes("API error 423")) {
        setBanner({
          type: "warn",
          text: "Concurență detectată (versiune depășită / blocare). Am nevoie de Refresh ca să preiei varianta curentă.",
        });
      } else {
        setBanner({ type: "error", text: msg });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="contentCard">
      <div className="contentHeader">
        <div>
          <div className="title">
            {mode === "class" ? "Orar pe clasă" : "Orarul meu"}
          </div>
          <div className="subtitle">
            Tabel minimal cu editare (subject/room) + optimistic locking.
          </div>
        </div>

        <div className="headerActions">
          {mode === "class" && (
            <div className="row">
              <label className="label">Clasă</label>
              <select
                className="select"
                value={selectedClassId}
                onChange={(e) => setSelectedClassId(Number(e.target.value))}
                disabled={loading || isEditing}
              >
                {classes.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.name ?? c.class_name ?? `Clasa ${c.id}`}
                  </option>
                ))}
              </select>
            </div>
          )}

          {editingAllowed && !isEditing && (
            <button className="btn primary" onClick={beginEdit} disabled={loading || entries.length === 0}>
              Edit
            </button>
          )}

          {editingAllowed && isEditing && (
            <>
              <button className="btn" onClick={cancelEdit} disabled={loading}>
                Cancel
              </button>
              <button className="btn primary" onClick={saveAll} disabled={loading}>
                Save
              </button>
            </>
          )}
        </div>
      </div>

      {banner && (
        <div className={`banner ${banner.type}`}>
          {banner.text}
        </div>
      )}

      {loading ? (
        <div className="mutedBlock">Loading...</div>
      ) : entries.length === 0 ? (
        <div className="mutedBlock">Nu există intrări de orar.</div>
    ) : (
        (() => {
          const byKey = new Map();
          for (const e of entries) {
            byKey.set(`${e.weekday}-${e.index_in_day}`, e);
          }

          const maxIdx = Math.max(7, ...entries.map(e => e.index_in_day || 0));
          const rows = Array.from({ length: maxIdx }, (_, i) => i + 1);
          const weekdays = [0, 1, 2, 3, 4];

          return (
            <div className="tableWrap">
              <table className="tbl tblGrid">
                <thead>
                  <tr>
                    <th className="stickyLeft">Orar</th>
                    <th>Luni</th>
                    <th>Marți</th>
                    <th>Miercuri</th>
                    <th>Joi</th>
                    <th>Vineri</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((idx) => (
                    <tr key={idx}>
                      <td className="stickyLeft timeCell">
                        <div className="timeBig">{TIME_LABELS[idx] ?? `Slot ${idx}`}</div>
                        <div className="timeSmall">({idx})</div>
                      </td>

                      {weekdays.map((wd) => {
                        const cell = byKey.get(`${wd}-${idx}`);

                        if (!cell) {
                          return (
                            <td key={`${wd}-${idx}`} className="cellEmpty">
                              —
                            </td>
                          );
                        }

                        return (
                          <td key={cell.id} className="cell">
                            {!isEditing ? (
                              <>
                                <div className="cellTitle">{cell.subject_name ?? `#${cell.subject_id}`}</div>
                                <div className="cellMeta">
                                  {cell.room_id == null ? "—" : `Sala ${cell.room_id}`}
                                  <span className="cellVersion">v{cell.version}</span>
                                </div>
                              </>
                            ) : (
                              <div className="cellEdit">
                                <select
                                  className="select small"
                                  value={cell.subject_id}
                                  onChange={(ev) => {
                                    const newId = Number(ev.target.value);
                                    const subj = subjectsById.get(newId);
                                    updateEntryLocal(cell.id, {
                                      subject_id: newId,
                                      subject_name: subj?.name ?? cell.subject_name,
                                    });
                                  }}
                                >
                                  {subjects.map((s) => (
                                    <option key={s.id} value={s.id}>
                                      {s.name ?? `Materie ${s.id}`}
                                    </option>
                                  ))}
                                </select>

                                <input
                                  className="input small"
                                  type="number"
                                  placeholder="room_id / gol=null"
                                  value={cell.room_id ?? ""}
                                  onChange={(ev) =>
                                    updateEntryLocal(cell.id, { room_id: normalizeRoom(ev.target.value) })
                                  }
                                />
                                <div className="cellVersion">v{cell.version}</div>
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })()
      )}
    </section>
  );
}
