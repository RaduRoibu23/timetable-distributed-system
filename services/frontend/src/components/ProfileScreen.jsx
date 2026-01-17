import React, { useEffect, useMemo, useState } from "react";
import { apiGet } from "../services/apiService";

function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decodeURIComponent(escape(json)));
  } catch {
    return null;
  }
}

function pickFirst(...vals) {
  for (const v of vals) {
    if (v !== undefined && v !== null && String(v).trim() !== "") return v;
  }
  return "—";
}

export default function ProfileScreen({ accessToken, roles }) {
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState(null);
  const [me, setMe] = useState(null);

  const tokenInfo = useMemo(() => decodeJwt(accessToken), [accessToken]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setBanner(null);
      try {
        const data = await apiGet("/me", accessToken);
        setMe(data);
      } catch (e) {
        setBanner({ type: "error", text: String(e?.message || e) });
      } finally {
        setLoading(false);
      }
    })();
  }, [accessToken]);

  // valori generale (merg pentru oricine)
  const username = pickFirst(
    tokenInfo?.preferred_username,
    tokenInfo?.username,
    me?.username,
    me?.user,
    me?.email
  );

  const firstName = pickFirst(
    tokenInfo?.given_name,
    me?.first_name,
    me?.firstName,
    me?.given_name
  );

  const lastName = pickFirst(
    tokenInfo?.family_name,
    me?.last_name,
    me?.lastName,
    me?.family_name
  );

  const email = pickFirst(tokenInfo?.email, me?.email);

  // clasa poate exista doar pentru student/profesor; pentru admin/sysadmin va fi —
  const classId = me?.class_id ?? me?.classId ?? me?.class?.id ?? null;
  const className = me?.class_name ?? me?.className ?? me?.class?.name ?? me?.class?.class_name ?? "";
  const classText = className || (classId ? `Clasa ${classId}` : "—");

  // materii predate (pentru profesori)
  const subjectsTaught = me?.subjects_taught ?? me?.subjectsTaught ?? [];
  const subjectsText = Array.isArray(subjectsTaught) && subjectsTaught.length > 0
    ? subjectsTaught.join(", ")
    : "—";

  // extra demo: sub (id), issuer, etc.
  const subject = pickFirst(tokenInfo?.sub, me?.id, me?.user_id);

  return (
    <section className="contentCard">
      <div className="contentHeader">
        <div>
          <div className="title">Date personale</div>
          <div className="subtitle">Profil utilizator (din /me + token).</div>
        </div>
      </div>

      {banner && <div className={`banner ${banner.type}`}>{banner.text}</div>}

      {loading ? (
        <div className="mutedBlock">Loading...</div>
      ) : (
        <div className="mutedBlock">
          <div style={{ display: "grid", gap: 10 }}>
            <div><strong>Username:</strong> {username}</div>
            <div><strong>Nume:</strong> {lastName}</div>
            <div><strong>Prenume:</strong> {firstName}</div>
            <div><strong>Email:</strong> {email}</div>

            <div><strong>Clasă:</strong> {classText}</div>

            {subjectsTaught.length > 0 && (
              <div><strong>Materii predate:</strong> {subjectsText}</div>
            )}

            <div>
              <strong>Roluri:</strong>{" "}
              {Array.isArray(roles) && roles.length ? roles.join(", ") : "—"}
            </div>

            <div><strong>User ID (sub):</strong> {subject}</div>
          </div>
        </div>
      )}
    </section>
  );
}
