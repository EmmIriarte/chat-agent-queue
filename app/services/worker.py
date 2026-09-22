"""Background worker for processing message queue"""
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.services.queue_persistent import persistent_queue_manager

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def process_queue():
    """Process pending messages in the queue"""
    try:
        await persistent_queue_manager.process_queue()
    except Exception as e:
        logger.error(f"Error in queue processor: {e}", exc_info=True)


def start_worker():
    """Start the background worker"""
    try:
        # Schedule queue processing every 30 seconds
        scheduler.add_job(
            process_queue,
            trigger=IntervalTrigger(seconds=30),
            id="queue_processor",
            name="Process message queue",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Background worker started (checking queue every 30 seconds)")
        
    except Exception as e:
        logger.error(f"Failed to start background worker: {e}")


def stop_worker():
    """Stop the background worker"""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Background worker stopped")
    except Exception as e:
        logger.error(f"Error stopping background worker: {e}")

