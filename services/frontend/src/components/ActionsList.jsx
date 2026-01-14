import { useMemo } from 'react';
import { ALL_ACTIONS, hasPermission } from '../constants/actions';
import { performAction } from '../services/actionService';

export default function ActionsList({ accessToken, roles, onActionResult }) {
  const allowedActions = useMemo(() => {
    return ALL_ACTIONS.filter(action => hasPermission(roles, action.requiredRoles));
  }, [roles]);

  const handleAction = async (action) => {
    try {
      const result = await performAction(action, accessToken);
      onActionResult(action.label, result);
    } catch (err) {
      const errorHtml = `
        <div class="error-display">
          <p class="error-title">❌ Eroare</p>
          <p class="error-message">${err.message || String(err)}</p>
          <p class="hint" style="margin-top:8px">Endpoint: ${action.method || 'GET'} ${action.apiPath}</p>
        </div>
      `;
      onActionResult(`${action.label} - Eroare`, errorHtml);
    }
  };

  return (
    <div id="role-actions" className="section" style={{ marginTop: '14px' }}>
      <h3>Acțiuni pe rol</h3>
      <p className="hint">
        Butonelor li se aplică vizibilitate bazată pe rol. Apasă pentru a rula acțiuni demo.
      </p>
      <div id="actions-list" style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {allowedActions.length === 0 ? (
          <div className="hint">Nicio acțiune disponibilă pentru rolurile tale.</div>
        ) : (
          allowedActions.map((action) => (
            <button
              key={action.id}
              className="btn"
              onClick={() => handleAction(action)}
            >
              {action.label}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
