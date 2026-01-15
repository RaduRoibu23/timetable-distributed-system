import React, { useEffect, useState, useRef, useCallback } from "react";
import { CONFIG } from "../config";
import { apiPatch, apiGet } from "../services/apiService";

export default function NotificationPopup({ accessToken }) {
  const [notifications, setNotifications] = useState([]);
  const abortRef = useRef(null);
  const lastIdRef = useRef(0);

  // Poll for new notifications instead of SSE (more reliable with token refresh)
  const checkNotifications = useCallback(async () => {
    if (!accessToken) return;
    
    try {
      const data = await apiGet("/notifications/me?unread_only=true", accessToken);
      if (Array.isArray(data)) {
        const newNotifs = data.filter(n => n.id > lastIdRef.current);
        if (newNotifs.length > 0) {
          setNotifications(prev => {
            const existing = new Set(prev.map(p => p.id));
            const toAdd = newNotifs.filter(n => !existing.has(n.id));
            return [...prev, ...toAdd];
          });
          lastIdRef.current = Math.max(...data.map(n => n.id));
        }
      }
    } catch (err) {
      // Ignore errors silently - will retry on next poll
    }
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken) return;

    // Initial check
    checkNotifications();

    // Poll every 3 seconds
    const interval = setInterval(checkNotifications, 3000);

    return () => {
      clearInterval(interval);
    };
  }, [accessToken, checkNotifications]);

  const dismissNotification = async (id) => {
    // Mark as read in backend
    try {
      await apiPatch(`/notifications/${id}/read`, {}, accessToken);
    } catch (e) {
      // Ignore errors - still remove from UI
    }
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  if (notifications.length === 0) return null;

  return (
    <div className="notificationContainer">
      {notifications.map((notif) => (
        <div key={notif.id} className="notificationPopup">
          <div className="notificationContent">
            <div className="notificationMessage">{notif.message}</div>
            <div className="notificationTime">
              {new Date(notif.created_at).toLocaleTimeString()}
            </div>
          </div>
          <button
            className="notificationClose"
            onClick={() => dismissNotification(notif.id)}
            title="Dismiss"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
