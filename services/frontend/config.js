// config.js
window.APP_CONFIG = {
  keycloak: {
    url: 'http://localhost:8181',
    realm: 'timetable-realm',
    clientId: 'timetable-frontend'
  },
  api: {
    baseUrl: 'http://localhost:8000'
  },
  auth: {
    storageKey: 'timetable_auth'
  }
};
