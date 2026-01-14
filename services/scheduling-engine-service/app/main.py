"""
Scheduling Engine Service - Worker that consumes timetable generation jobs from RabbitMQ.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

import pika

# Add shared code path to import shared models
shared_path = os.getenv("SHARED_CODE_PATH", "/app/shared")
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

# Import from shared code (timetable-management-service)
# Import db first to ensure Base is available
import db as shared_db
from models import TimetableJob, SchoolClass
from services.timetable_generator import generate_timetable_for_class
from services import notifications as notifications_service


def get_shared_db_session_factory():
    """Get database session factory using shared db module."""
    # Use the shared db module's SessionLocal (which is a sessionmaker)
    return shared_db.SessionLocal


def get_rabbitmq_url() -> str:
    """Get RabbitMQ connection URL from environment."""
    return os.getenv("RABBITMQ_URL", "amqp://admin:admin@rabbitmq:5672/")


def process_job(job_id: int, class_id: int, db_session):
    """Process a single timetable generation job."""
    print(f"[Worker] Processing job {job_id} for class {class_id}")
    
    # Update job status to processing
    job = db_session.query(TimetableJob).filter(TimetableJob.id == job_id).first()
    if not job:
        print(f"[Worker] Job {job_id} not found in database")
        return False
    
    job.status = "processing"
    job.started_at = datetime.utcnow()
    db_session.commit()
    
    try:
        # Generate timetable
        entries = generate_timetable_for_class(db_session, class_id)
        
        # Update job status to completed
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        db_session.commit()
        
        # Send notification to class
        class_obj = db_session.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        if class_obj:
            notifications_service.send_to_class(
                db_session,
                class_id,
                f"Orarul pentru clasa {class_obj.name} a fost generat/actualizat.",
            )
        
        # Log audit action
        try:
            from services import audit as audit_service
            audit_service.log_action(
                db_session,
                username="scheduling-engine",
                action="timetable_generated",
                resource_type="timetable",
                resource_id=job_id,
                details=f"Generated timetable for class {class_id} with {len(entries)} entries",
            )
        except ImportError:
            # Audit service might not be available, skip silently
            pass
        except Exception as e:
            print(f"[Worker] Failed to log audit action: {e}")
        
        print(f"[Worker] Job {job_id} completed successfully ({len(entries)} entries)")
        return True
        
    except Exception as e:
        print(f"[Worker] Job {job_id} failed: {e}")
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db_session.commit()
        return False


def callback(ch, method, properties, body, db_session_factory):
    """RabbitMQ message callback."""
    try:
        message = json.loads(body)
        job_id = message.get("job_id")
        class_id = message.get("class_id")
        
        if not job_id or not class_id:
            print(f"[Worker] Invalid message: {message}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        # Create a new session for this job
        db_session = db_session_factory()
        try:
            success = process_job(job_id, class_id, db_session)
            if success:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                # Reject and requeue on failure
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        finally:
            db_session.close()
            
    except Exception as e:
        print(f"[Worker] Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """Main worker loop."""
    print("[Worker] Starting Scheduling Engine Service...")
    
    # Use shared db module for consistency
    # The shared db module already has the engine and SessionLocal configured
    SessionLocal = get_shared_db_session_factory()
    
    # Setup RabbitMQ connection
    rabbitmq_url = get_rabbitmq_url()
    
    while True:
        try:
            print("[Worker] Connecting to RabbitMQ...")
            params = pika.URLParameters(rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            
            # Declare queue (idempotent)
            channel.queue_declare(queue="timetable_generation", durable=True)
            
            # Set QoS to process one message at a time per worker
            channel.basic_qos(prefetch_count=1)
            
            print("[Worker] Waiting for messages. To exit press CTRL+C")
            
            # Consume messages
            channel.basic_consume(
                queue="timetable_generation",
                on_message_callback=lambda ch, method, properties, body: callback(
                    ch, method, properties, body, SessionLocal
                ),
            )
            
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError:
            print("[Worker] RabbitMQ connection failed. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("[Worker] Shutting down...")
            if 'connection' in locals() and connection.is_open:
                connection.close()
            break
        except Exception as e:
            print(f"[Worker] Unexpected error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
