export const CONFIG = {
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
  },

  // Quick login presets (editează aici dacă ai alte username/parole în Keycloak)
  demoUsers: [
    { label: 'Sysadmin', username: 'sysadmin01', password: 'sysadmin01' },
    { label: 'Admin', username: 'admin01', password: 'admin01' },
    { label: 'Secretariat', username: 'secretariat01', password: 'secretariat01' },
    { label: 'Profesor', username: 'professor01', password: 'professor01' },
    { label: 'Student', username: 'student01', password: 'student01' },
    { label: 'Scheduler', username: 'scheduler01', password: 'scheduler01' },

  ]
};
