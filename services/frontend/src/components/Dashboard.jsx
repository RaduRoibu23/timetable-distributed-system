import { useEffect, useMemo, useState } from "react";
import { rolesFromToken, tokenExpiryText, loadSession, refreshAccessToken } from "../services/authService";
import Sidebar, { NAV_ITEMS } from "./Sidebar";
import TimetableScreen from "./TimetableScreen";
import GenerateTimetableScreen from "./GenerateTimetableScreen";
import ConflictsScreen from "./ConflictsScreen";
import AuditLogsScreen from "./AuditLogsScreen";
import StatsScreen from "./StatsScreen";

function hasAnyRole(userRoles, allowedRoles) {
  if (!allowedRoles || allowedRoles.length === 0) return true;
  return userRoles.some((r) => allowedRoles.includes(r));
}

function defaultActionForRoles(roles) {
  // Student/professor -> orarul meu
  if (roles.includes("student") || roles.includes("professor")) return "my-timetable";
  // Secretariat/scheduler/admin/sysadmin -> orar pe clasă
  return "class-timetable";
}

export default function Dashboard({ accessToken, idToken, onRefreshToken, onLogout }) {
  const roles = useMemo(() => rolesFromToken(accessToken), [accessToken]);
  const expiry = tokenExpiryText(accessToken);

  const visibleActionIds = useMemo(() => {
    return NAV_ITEMS
      .filter((i) => hasAnyRole(roles, i.allowedRoles))
      .map((i) => i.id);
  }, [roles]);

  const [active, setActive] = useState(() => defaultActionForRoles(roles));

  // dacă rolurile se schimbă (refresh token) sau active nu mai e permis, corectăm
  useEffect(() => {
    const def = defaultActionForRoles(roles);
    if (!visibleActionIds.includes(active)) setActive(def);
  }, [roles, visibleActionIds, active]);

  const handleRefreshToken = async () => {
    try {
      const session = loadSession();
      if (session?.refreshToken) {
        const tokens = await refreshAccessToken(session.refreshToken);
        onRefreshToken(tokens);
      }
    } catch (err) {
      console.error("Token refresh failed:", err);
    }
  };

  return (
    <div className="appShell">
      <Sidebar roles={roles} activeId={active} onSelect={setActive} />

      <main className="content">
        <div className="topBar">
          <div className="topBarLeft">
            <div className="topTitle">Timetable Management</div>
            <div className="topSub">Token exp: {expiry}</div>
          </div>
          <div className="topBarRight">
            <button className="btn" onClick={handleRefreshToken}>Refresh token</button>
            <button className="btn danger" onClick={onLogout}>Logout</button>
          </div>
        </div>

        {active === "my-timetable" && (
          <TimetableScreen accessToken={accessToken} roles={roles} mode="my" />
        )}

        {active === "class-timetable" && (
          <TimetableScreen accessToken={accessToken} roles={roles} mode="class" />
        )}

        {active === "generate" && (
          <GenerateTimetableScreen accessToken={accessToken} roles={roles} />
        )}

        {active === "conflicts" && (
          <ConflictsScreen accessToken={accessToken} roles={roles} />
        )}

        {active === "audit" && (
          <AuditLogsScreen accessToken={accessToken} roles={roles} />
        )}

        {active === "stats" && (
          <StatsScreen accessToken={accessToken} roles={roles} />
        )}
      </main>
    </div>
  );
}
