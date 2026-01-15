import React from "react";


export const NAV_ITEMS = [
  // Student / Professor: au "orarul meu"
  { id: "my-timetable", label: "Orarul meu", allowedRoles: ["student", "professor"] },

  // Secretariat/Scheduler/Admin/Sysadmin: gestionează orare pe clase
  { id: "class-timetable", label: "Orar pe clasă", allowedRoles: ["secretariat", "scheduler", "admin", "sysadmin"] },

  // Tooling pentru cei care gestionează orarul
  { id: "generate", label: "Generează orar", allowedRoles: ["secretariat", "scheduler", "admin", "sysadmin"] },
  { id: "conflicts", label: "Conflicte job", allowedRoles: ["secretariat", "scheduler", "admin", "sysadmin"] },

  // Strict admin/sysadmin
  { id: "audit", label: "Audit logs", allowedRoles: ["admin", "sysadmin"] },
  { id: "stats", label: "Stats", allowedRoles: ["admin", "sysadmin"] },

  { id: "students", label: "Studenți", allowedRoles: ["secretariat", "scheduler", "admin", "sysadmin"] },
  { id: "profile", label: "Date personale", allowedRoles: [] },
];

function hasAnyRole(userRoles, allowedRoles) {
  if (!allowedRoles || allowedRoles.length === 0) return true;
  return userRoles.some((r) => allowedRoles.includes(r));
}

export default function Sidebar({ roles, activeId, onSelect }) {
  const visible = NAV_ITEMS.filter((i) => hasAnyRole(roles, i.allowedRoles));

  return (
    <aside className="sidebar">
      <div className="sidebarTitle">Meniu</div>

      <div className="sidebarGroup">
        {visible.map((item) => (
          <button
            key={item.id}
            className={`navBtn ${activeId === item.id ? "active" : ""}`}
            onClick={() => onSelect(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="sidebarFooter">
        <div className="mutedSmall">Roluri:</div>
        <div className="rolesWrap">
          {roles.length === 0 ? (
            <span className="pill muted">—</span>
          ) : (
            roles.map((r) => (
              <span key={r} className="pill">
                {r}
              </span>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}
