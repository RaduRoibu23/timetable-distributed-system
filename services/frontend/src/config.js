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

  // Quick login presets (aliniate cu seed_keycloak.sh)
  // Format: sysadmin (fără număr), admin/professor/secretariat/scheduler (2 cifre), student (2 cifre)
  demoUsers: [
    { label: 'Sysadmin', username: 'sysadmin', password: 'sysadmin' },
    { label: 'Admin', username: 'admin01', password: 'admin01' },
    { label: 'Secretariat', username: 'secretariat01', password: 'secretariat01' },
    { label: 'Profesor', username: 'professor01', password: 'professor01' },
    { label: 'Student', username: 'student01', password: 'student01' },
    { label: 'Scheduler', username: 'scheduler01', password: 'scheduler01' },

  ]
};
