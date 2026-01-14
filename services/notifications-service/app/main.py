"""
Notifications Service - Worker that consumes notification events from RabbitMQ.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime

import pika

# Import from shared package
from timetable_shared.db import SessionLocal
from timetable_shared.models import Notification, UserProfile, SchoolClass
from timetable_shared.services import notifications as notifications_service


def get_rabbitmq_url() -> str:
    """Get RabbitMQ connection URL from environment."""
    return os.getenv("RABBITMQ_URL", "amqp://admin:admin@rabbitmq:5672/")


def process_notification_event(event_type: str, event_data: dict, db_session):
    """Process a notification event."""
    print(f"[Notifications] Processing event: {event_type}")
    
    try:
        if event_type == "timetable_generated":
            class_id = event_data.get("class_id")
            class_name = event_data.get("class_name", f"clasa {class_id}")
            
            if class_id:
                message = f"Orarul pentru {class_name} a fost generat/actualizat."
                notifications_service.send_to_class(db_session, class_id, message)
                print(f"[Notifications] Sent notification to class {class_id}")
        
        elif event_type == "timetable_updated":
            class_id = event_data.get("class_id")
            class_name = event_data.get("class_name", f"clasa {class_id}")
            username = event_data.get("username", "sistem")
            
            if class_id:
                message = f"Orarul pentru {class_name} a fost modificat de {username}."
                notifications_service.send_to_class(db_session, class_id, message)
                print(f"[Notifications] Sent notification to class {class_id}")
        
        elif event_type == "timetable_entry_modified":
            class_id = event_data.get("class_id")
            class_name = event_data.get("class_name", f"clasa {class_id}")
            subject_name = event_data.get("subject_name", "o materie")
            
            if class_id:
                message = f"Modificare în orarul pentru {class_name}: {subject_name}."
                notifications_service.send_to_class(db_session, class_id, message)
                print(f"[Notifications] Sent notification to class {class_id}")
        
        elif event_type == "teacher_unavailable":
            teacher_id = event_data.get("teacher_id")
            teacher_username = event_data.get("teacher_username")
            class_id = event_data.get("class_id")
            
            if class_id:
                message = f"Profesorul {teacher_username or f'#{teacher_id}'} este indisponibil."
                notifications_service.send_to_class(db_session, class_id, message)
                print(f"[Notifications] Sent notification to class {class_id}")
        
        elif event_type == "room_unavailable":
            room_name = event_data.get("room_name", "o sală")
            class_id = event_data.get("class_id")
            
            if class_id:
                message = f"Sala {room_name} este indisponibilă."
                notifications_service.send_to_class(db_session, class_id, message)
                print(f"[Notifications] Sent notification to class {class_id}")
        
        elif event_type == "notification_custom":
            # Generic notification event
            target_type = event_data.get("target_type")  # "user" or "class"
            target_id = event_data.get("target_id")
            message = event_data.get("message")
            
            if not message:
                print(f"[Notifications] Missing message in custom notification event")
                return
            
            if target_type == "user":
                username = str(target_id)
                notifications_service.send_to_user(db_session, username, message)
                print(f"[Notifications] Sent notification to user {username}")
            elif target_type == "class":
                class_id = int(target_id)
                notifications_service.send_to_class(db_session, class_id, message)
                print(f"[Notifications] Sent notification to class {class_id}")
        
        else:
            print(f"[Notifications] Unknown event type: {event_type}")
            return False
        
        return True
        
    except Exception as e:
        print(f"[Notifications] Error processing event {event_type}: {e}")
        import traceback
        traceback.print_exc()
        return False


def callback(ch, method, properties, body, db_session_factory):
    """RabbitMQ message callback."""
    try:
        message = json.loads(body)
        event_type = message.get("event_type")
        event_data = message.get("event_data", {})
        
        if not event_type:
            print(f"[Notifications] Invalid message: missing event_type")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        # Create a new session for this event
        db_session = db_session_factory()
        try:
            success = process_notification_event(event_type, event_data, db_session)
            if success:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                # Reject but don't requeue on processing failure (to avoid infinite loops)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        finally:
            db_session.close()
            
    except Exception as e:
        print(f"[Notifications] Error processing message: {e}")
        import traceback
        traceback.print_exc()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Main worker loop."""
    print("[Notifications] Starting Notifications Service...")
    
    # Setup RabbitMQ connection
    rabbitmq_url = get_rabbitmq_url()
    
    while True:
        try:
            print("[Notifications] Connecting to RabbitMQ...")
            params = pika.URLParameters(rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            
            # Declare queue (idempotent)
            channel.queue_declare(queue="notifications", durable=True)
            
            # Set QoS to process one message at a time per worker
            channel.basic_qos(prefetch_count=1)
            
            print("[Notifications] Waiting for messages. To exit press CTRL+C")
            
            # Consume messages
            channel.basic_consume(
                queue="notifications",
                on_message_callback=lambda ch, method, properties, body: callback(
                    ch, method, properties, body, SessionLocal
                ),
            )
            
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError:
            print("[Notifications] RabbitMQ connection failed. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("[Notifications] Shutting down...")
            if 'connection' in locals() and connection.is_open:
                connection.close()
            break
        except Exception as e:
            print(f"[Notifications] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    main()
