# 📋 Plan - Ce mai rămâne de făcut

## 🔴 Prioritate Înaltă (Necesare pentru funcționalitate completă)

### 1. Fix Scheduling Engine Service ⚠️
**Status**: Blocat (probleme de import Python)
- **Problema**: `scheduling-engine-service` nu poate importa codul din `timetable-management-service`
- **Impact**: Generarea asincronă de orare nu funcționează complet
- **Soluție**: 
  - Opțiunea 1: Fix import paths (complex)
  - Opțiunea 2: Package shared code ca librărie Python
  - Opțiunea 3: Duplicare cod necesar (simplu, dar nu ideal)
- **Timp estimat**: 2-4 ore

### 2. Testare completă a tuturor butoanelor frontend ✅
**Status**: În curs
- Verificare că toate butoanele funcționează corect
- Testare cu diferite roluri
- **Timp estimat**: 1-2 ore

---

## 🟡 Prioritate Medie (Îmbunătățiri importante)

### 3. Îmbunătățire algoritm generare orar
**Status**: MVP funcțional, dar simplu
- **Ce lipsește**:
  - Disponibilitate profesori (nu e modelată)
  - Disponibilitate săli (doar CRUD basic)
  - Preferințe profesori (ore preferate, zile libere)
  - Optimizare (evitare ore târzii, distribuție uniformă)
  - Raportare conflicte când nu există soluție
- **Timp estimat**: 4-6 ore

### 4. Disponibilitate Profesori și Săli
**Status**: Nu e modelată
- **Model nou**: `TeacherAvailability` (profesor_id, weekday, time_slot, available)
- **Model nou**: `RoomAvailability` (room_id, weekday, time_slot, available)
- **Endpoint-uri**: CRUD pentru disponibilități
- **Timp estimat**: 3-4 ore

### 5. Notifications Service separat (opțional)
**Status**: Integrat în timetable-management-service
- **Ce trebuie**: Microserviciu separat care consumă evenimente din RabbitMQ
- **Beneficii**: Scalare independentă, separare responsabilități
- **Timp estimat**: 2-3 ore

---

## 🟢 Prioritate Scăzută (Nice to have)

### 6. Unit Tests (pytest)
**Status**: Nu există
- Teste pentru fiecare endpoint
- Teste pentru algoritm generare orar
- Teste pentru RBAC
- **Timp estimat**: 4-6 ore

### 7. Migrații Alembic
**Status**: Folosim `Base.metadata.create_all()`
- **Ce trebuie**: Migrații versionate pentru schema DB
- **Beneficii**: Versionare schimbări DB, rollback
- **Timp estimat**: 2-3 ore

### 8. Documentație API completă
**Status**: Swagger există, dar poate fi îmbunătățită
- Descrieri detaliate pentru fiecare endpoint
- Exemple de request/response
- **Timp estimat**: 2-3 ore

### 9. Raport Final Milestone 3
**Status**: Fișier gol
- Documentare completă a implementării
- Screenshot-uri și demo-uri
- **Timp estimat**: 3-4 ore

### 10. Conflict Reports
**Status**: Nu există
- Endpoint pentru raportare conflicte la generare orar
- Listă conflicte (profesor indisponibil, sală ocupată, etc.)
- **Timp estimat**: 2-3 ore

---

## 📊 Rezumat

| Categorie | Număr | Timp Total Estimat |
|-----------|-------|-------------------|
| 🔴 Prioritate Înaltă | 2 | 3-6 ore |
| 🟡 Prioritate Medie | 3 | 9-13 ore |
| 🟢 Prioritate Scăzută | 5 | 13-19 ore |
| **TOTAL** | **10** | **25-38 ore** |

---

## 🎯 Recomandare

**Pentru a avea un proiect funcțional complet:**
1. ✅ Fix Scheduling Engine Service (dacă vrei generare asincronă)
2. ✅ Testare completă frontend
3. ✅ Îmbunătățire algoritm (opțional, dar recomandat)

**Pentru prezentare/demo:**
- Frontend-ul funcționează deja
- Backend-ul are toate endpoint-urile necesare
- Poți demonstra toate funcționalitățile

**Ce poți sări peste:**
- Unit tests (dacă nu e cerință explicită)
- Migrații Alembic (dacă nu schimbi schema DB)
- Notifications Service separat (funcționează integrat)

---

## 🚀 Următorii pași recomandați

1. **Testează toate butoanele** din frontend și notează ce nu funcționează
2. **Decide dacă vrei să fix Scheduling Engine** sau să-l lași pentru mai târziu
3. **Îmbunătățește algoritmul** dacă vrei să demonstrezi generare inteligentă
4. **Completează raportul final** cu ce ai implementat
