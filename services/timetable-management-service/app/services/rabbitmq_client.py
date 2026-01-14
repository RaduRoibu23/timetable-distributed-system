from __future__ import annotations

import json
import os
from typing import Any

import pika


def get_rabbitmq_url() -> str:
    """Get RabbitMQ connection URL from environment."""
    return os.getenv("RABBITMQ_URL", "amqp://admin:admin@localhost:5672/")


def publish_timetable_generation_job(class_id: int, job_id: int) -> bool:
    """
    Publish a timetable generation job to RabbitMQ queue.
    
    Args:
        class_id: The class ID to generate timetable for
        job_id: The database job ID for tracking
        
    Returns:
        True if published successfully, False otherwise
    """
    try:
        url = get_rabbitmq_url()
        params = pika.URLParameters(url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        
        # Declare queue (idempotent)
        channel.queue_declare(queue="timetable_generation", durable=True)
        
        # Publish message
        message = {
            "job_id": job_id,
            "class_id": class_id,
        }
        
        channel.basic_publish(
            exchange="",
            routing_key="timetable_generation",
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
            ),
        )
        
        connection.close()
        return True
    except Exception as e:
        print(f"Failed to publish job to RabbitMQ: {e}")
        return False


def publish_notification_event(event_type: str, event_data: dict[str, Any]) -> bool:
    """
    Publish a notification event to RabbitMQ queue.
    
    Args:
        event_type: Type of event (e.g., "timetable_generated", "timetable_updated")
        event_data: Dictionary with event-specific data
        
    Returns:
        True if published successfully, False otherwise
    """
    try:
        url = get_rabbitmq_url()
        params = pika.URLParameters(url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        
        # Declare queue (idempotent)
        channel.queue_declare(queue="notifications", durable=True)
        
        # Publish message
        message = {
            "event_type": event_type,
            "event_data": event_data,
        }
        
        channel.basic_publish(
            exchange="",
            routing_key="notifications",
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
            ),
        )
        
        connection.close()
        return True
    except Exception as e:
        print(f"Failed to publish notification event to RabbitMQ: {e}")
        return False
