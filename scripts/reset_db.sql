-- Reset complet: goleste toate tabelele aplicatiei (pastram Keycloak).
-- Ruleaza: docker exec -i $(docker ps -q -f name=scd_scd_postgres) psql -U keycloak -d keycloak < scripts/reset_db.sql
TRUNCATE
  conflict_reports,
  timetable_entries,
  subject_teachers,
  curricula,
  timetable_jobs,
  user_profiles,
  room_availability,
  teacher_availability,
  notifications,
  audit_logs,
  lessons,
  rooms,
  time_slots,
  subjects,
  school_classes
RESTART IDENTITY CASCADE;
