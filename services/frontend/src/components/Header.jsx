export default function Header({ status }) {
  return (
    <div className="header">
      <div className="brand">
        <div className="logo" aria-hidden="true"></div>
        <div>
          <h1>Timetable Management Distributed System</h1>
          <div className="sub">SCD — Frontend demo (Keycloak + API)</div>
        </div>
      </div>
      <div id="status-badge" className="badge">
        Status: {status}
      </div>
    </div>
  );
}
