// config.js
window.APP_CONFIG = {
  keycloak: {
    url: 'http://localhost:8181',
    realm: 'timetable-realm',
    clientId: 'timetable-frontend'
  },
  api: {
    // setează aici URL-ul backend-ului tău FastAPI (din stack)
    baseUrl: 'http://localhost:8000'
  },
  auth: {
    // stocare token în localStorage (simplu pentru demo/proiect)
    storageKey: 'timetable_auth'
  }
};
