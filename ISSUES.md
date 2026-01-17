# Probleme persistente - 14 ianuarie 2026

## Probleme identificate care necesită rezolvare

### 1. Eroarea 400 pentru conflict profesor
**Problema:** Eroarea `API error 400: {"detail":"Profesorul are deja o oră programată la acest interval..."}` apare în continuare când se încearcă editarea unui entry de orar.

**Status:** Modificări făcute în `services/timetable-management-service/app/api/routes_timetables.py` pentru a exclude entry-ul curent din validarea conflictelor, dar problema persistă.

**Locație cod:** `services/timetable-management-service/app/api/routes_timetables.py` - funcția `update_timetable_entry`, validarea conflictelor profesorului (liniile ~291-382)

**Pași pentru investigare:**
- Verifică dacă logica de filtrare a entry-ului curent funcționează corect
- Verifică dacă există alte entry-uri cu același profesor la același timeslot în alte clase
- Testează scenariul când se editează un entry existent fără a schimba profesorul/timeslot-ul

---

### 2. Distribuirea sălilor în generarea orarului
**Problema:** Sălile sunt încă `null` sau doar sala 19 apare predominant în orarele generate. Distribuirea nu este uniformă.

**Status:** Modificări făcute în `shared/timetable_shared/services/timetable_generator.py` pentru a verifica sălile ocupate în batch-ul curent, dar problema persistă.

**Locație cod:** `shared/timetable_shared/services/timetable_generator.py` - funcția `try_build_assignment()`, logica de atribuire a sălilor (liniile ~195-240)

**Pași pentru investigare:**
- Verifică dacă logica de verificare a sălilor ocupate în batch funcționează corect
- Verifică dacă `used_rooms` este populat corect pentru fiecare timeslot
- Testează dacă shuffle-ul aleator al sălilor funcționează
- Verifică dacă există suficiente săli disponibile pentru toate clasele
- Consideră implementarea unei strategii de distribuție mai inteligente (round-robin, load balancing)

---

### 3. Numele profesorilor după 10
**Problema:** Profesorii cu ID > 10 (professor11, professor12, etc.) apar cu "nume complet + id" (ex: "George Enache professor13") în loc de doar nume complet.

**Status:** Modificări făcute în `services/timetable-management-service/app/api/routes_timetables.py` pentru a curăța numele folosind regex, dar problema persistă.

**Locație cod:** `services/timetable-management-service/app/api/routes_timetables.py` - funcția `_get_teacher_display_name()` (liniile ~600-669)

**Pași pentru investigare:**
- Verifică ce date returnează Keycloak pentru profesorii 11-20 (firstName, lastName)
- Verifică dacă regex-ul `r',?\s*professor\d+'` funcționează corect
- Verifică dacă cache-ul nu păstrează vechile valori
- Consideră ștergerea cache-ului după modificări
- Verifică dacă numele din Keycloak conțin deja username-ul în firstName/lastName

---

## Modificări făcute (neconfirmate ca funcționale)

1. **Validare conflict profesor:** Adăugat filtru pentru a exclude entry-ul curent din lista de conflicte
2. **Distribuire săli:** Adăugat verificare pentru sălile atribuite în batch-ul curent de generare
3. **Curățare nume profesori:** Adăugat regex pentru eliminarea pattern-ului "professor" + număr din nume

## Fișiere modificate

- `services/timetable-management-service/app/api/routes_timetables.py`
- `shared/timetable_shared/services/timetable_generator.py`

## Note

- Toate serviciile au fost rebuild-uite și actualizate
- Modificările sunt în cod dar nu rezolvă problemele
- Este necesară investigare mai profundă pentru a identifica cauza root
