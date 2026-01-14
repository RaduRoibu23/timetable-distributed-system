from __future__ import annotations

# Re-export from shared package for backward compatibility
from timetable_shared.services.rabbitmq_client import (
    get_rabbitmq_url,
    publish_timetable_generation_job,
    publish_notification_event,
)

__all__ = ['get_rabbitmq_url', 'publish_timetable_generation_job', 'publish_notification_event']
