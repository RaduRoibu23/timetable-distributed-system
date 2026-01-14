export function formatTimetable(entries) {
  if (!entries || entries.length === 0) {
    return '<p class="hint">Nu există intrări în orar.</p>';
  }
  
  const days = ['Luni', 'Marți', 'Miercuri', 'Joi', 'Vineri'];
  const timetable = {};
  
  entries.forEach(e => {
    const weekday = e.weekday ?? e.timeslot_weekday ?? 0;
    const hour = e.index_in_day ?? e.timeslot_index ?? 1;
    if (!timetable[weekday]) timetable[weekday] = {};
    timetable[weekday][hour] = {
      subject: e.subject_name || `Materie ${e.subject_id}`,
      class: e.class_name || `Clasă ${e.class_id}`,
      room: e.room_name || '-',
      id: e.id
    };
  });
  
  let html = '<div class="timetable-container">';
  html += '<table class="timetable-table">';
  html += '<thead><tr><th>Ora</th>';
  for (let d = 0; d < 5; d++) {
    html += `<th>${days[d]}</th>`;
  }
  html += '</tr></thead><tbody>';
  
  for (let hour = 1; hour <= 7; hour++) {
    html += `<tr><td class="hour-label">${hour}</td>`;
    for (let d = 0; d < 5; d++) {
      const entry = timetable[d]?.[hour];
      if (entry) {
        html += `<td class="timetable-cell">
          <div class="cell-subject">${entry.subject}</div>
          <div class="cell-room">${entry.room}</div>
        </td>`;
      } else {
        html += '<td class="timetable-cell empty">—</td>';
      }
    }
    html += '</tr>';
  }
  
  html += '</tbody></table></div>';
  return html;
}

export function formatList(items, fields) {
  if (!items || items.length === 0) {
    return '<p class="hint">Nu există elemente.</p>';
  }
  
  let html = '<table class="data-table">';
  html += '<thead><tr>';
  fields.forEach(f => {
    html += `<th>${f.label}</th>`;
  });
  html += '</tr></thead><tbody>';
  
  items.forEach(item => {
    html += '<tr>';
    fields.forEach(f => {
      const value = f.path ? f.path.split('.').reduce((obj, key) => obj?.[key], item) : item[f.key];
      html += `<td>${value ?? '-'}</td>`;
    });
    html += '</tr>';
  });
  
  html += '</tbody></table>';
  return html;
}

export function formatResponse(actionId, data) {
  if (actionId === 'view-my-timetable' || actionId === 'view-class-timetable' || actionId === 'my-lessons') {
    return formatTimetable(data);
  } else if (actionId === 'list-classes') {
    return formatList(data, [
      { key: 'id', label: 'ID' },
      { key: 'name', label: 'Nume Clasă' }
    ]);
  } else if (actionId === 'list-subjects') {
    return formatList(data, [
      { key: 'id', label: 'ID' },
      { key: 'name', label: 'Nume Materie' },
      { key: 'short_code', label: 'Cod' }
    ]);
  } else if (actionId === 'list-rooms' || actionId === 'list-lessons') {
    return formatList(data, Object.keys(data[0] || {}).map(key => ({
      key: key,
      label: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')
    })));
  } else if (actionId === 'list-curricula') {
    return formatList(data, [
      { key: 'id', label: 'ID' },
      { key: 'class_id', label: 'Clasă ID' },
      { key: 'subject_id', label: 'Materie ID' },
      { key: 'hours_per_week', label: 'Ore/săptămână' }
    ]);
  } else if (actionId === 'my-notifications') {
    if (data.length === 0) {
      return '<p class="hint">Nu ai notificări.</p>';
    }
    let html = '<div class="notifications-list">';
    data.forEach(n => {
      const date = new Date(n.created_at).toLocaleString('ro-RO');
      html += `
        <div class="notification-item ${n.read ? 'read' : 'unread'}">
          <div class="notification-message">${n.message}</div>
          <div class="notification-meta">${date} ${n.read ? '✓ Citit' : '● Necitit'}</div>
        </div>
      `;
    });
    html += '</div>';
    return html;
  } else if (actionId === 'my-info') {
    return `
      <div class="user-info-display">
        <div class="info-row"><strong>Username:</strong> ${data.username || '-'}</div>
        <div class="info-row"><strong>Email:</strong> ${data.email || '-'}</div>
        <div class="info-row"><strong>Roluri:</strong> ${(data.roles || []).join(', ') || 'Niciun rol'}</div>
        <div class="info-row"><strong>Clasă ID:</strong> ${data.class_id || '-'}</div>
        <div class="info-row"><strong>Teacher ID:</strong> ${data.teacher_id || '-'}</div>
      </div>
    `;
  } else if (actionId.startsWith('create-') || actionId.startsWith('update-')) {
    const actionLabel = actionId.includes('create') ? 'Creat' : 'Actualizat';
    return `
      <div class="success-display">
        <p class="success-title">✓ ${actionLabel} cu succes</p>
        <div class="object-display" style="margin-top:12px">
          ${Object.entries(data).map(([key, value]) => {
            const label = key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
            const displayValue = typeof value === 'object' ? JSON.stringify(value) : String(value);
            return `<div class="info-row"><strong>${label}:</strong> ${displayValue}</div>`;
          }).join('')}
        </div>
      </div>
    `;
  } else if (actionId.startsWith('delete-')) {
    return `
      <div class="success-display">
        <p class="success-title">✓ Șters cu succes</p>
        <p class="hint">Elementul a fost șters.</p>
      </div>
    `;
  } else if (Array.isArray(data)) {
    if (data.length === 0) {
      return '<p class="hint">Nu există elemente.</p>';
    }
    return formatList(data, Object.keys(data[0]).map(key => ({
      key: key,
      label: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')
    })));
  } else if (typeof data === 'object') {
    let html = '<div class="object-display">';
    for (const [key, value] of Object.entries(data)) {
      const label = key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
      html += `<div class="info-row"><strong>${label}:</strong> ${JSON.stringify(value)}</div>`;
    }
    html += '</div>';
    return html;
  } else {
    return `<pre class="json-display">${JSON.stringify(data, null, 2)}</pre>`;
  }
}
