from __future__ import annotations

import asyncio
import logging
import sys
import time

import redis as redis_lib
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from config import DATABASE_URL, REDIS_URL, BATCH_SIZE
from gpu_monitor import detect_gpus
from inference import ModelPool
from pipeline import fetch_active_streams, process_batch
from scheduler import Scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class RedisLogHandler(logging.Handler):
    """Publishes log lines to Redis so the frontend can stream them."""

    def __init__(self, redis_client, channel="worker:logs"):
        super().__init__()
        self.redis_client = redis_client
        self.channel = channel

    def emit(self, record):
        try:
            msg = self.format(record)
            self.redis_client.publish(self.channel, msg)
            # Keep last 500 lines in a list for initial page load
            self.redis_client.rpush("worker:log_buffer", msg)
            self.redis_client.ltrim("worker:log_buffer", -500, -1)
        except Exception:
            pass


def register_gpus(session: Session):
    gpus = detect_gpus()
    if not gpus:
        logger.info("No NVIDIA GPUs detected — running in CPU mode")
        return

    session.execute(text("DELETE FROM gpu_inventory"))
    for gpu in gpus:
        session.execute(
            text("""
                INSERT INTO gpu_inventory (device_index, name, total_memory_mb, compute_capability)
                VALUES (:idx, :name, :mem, :cc)
            """),
            {"idx": gpu["device_index"], "name": gpu["name"],
             "mem": gpu["total_memory_mb"], "cc": gpu["compute_capability"]},
        )
    session.commit()
    logger.info("Registered %d GPU(s): %s", len(gpus),
                ", ".join(f"{g['name']} ({g['total_memory_mb']}MB)" for g in gpus))


def get_running_projects(session: Session) -> list[dict]:
    result = session.execute(
        text("SELECT id, name FROM projects WHERE status = 'running'")
    )
    return [dict(row._mapping) for row in result]


async def main():
    engine = create_engine(DATABASE_URL)

    try:
        redis_client = redis_lib.from_url(REDIS_URL)
        redis_client.ping()
        logger.info("Connected to Redis")
        # Attach Redis log handler so frontend can stream logs
        redis_handler = RedisLogHandler(redis_client)
        redis_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logging.getLogger().addHandler(redis_handler)
    except Exception as e:
        logger.warning("Redis not available, live updates disabled: %s", e)
        redis_client = None

    model_pool = ModelPool()
    scheduler = Scheduler()

    with Session(engine) as session:
        register_gpus(session)

    logger.info("WildSight worker started — waiting for running projects...")

    while True:
        try:
            with Session(engine) as session:
                projects = get_running_projects(session)

                if not projects:
                    await asyncio.sleep(2)
                    continue

                for project in projects:
                    streams = fetch_active_streams(session, str(project["id"]))
                    ready = scheduler.get_ready_streams(streams)

                    if not ready:
                        continue

                    for i in range(0, len(ready), BATCH_SIZE):
                        batch = ready[i:i + BATCH_SIZE]
                        process_batch(batch, model_pool, session, scheduler, redis_client)

        except Exception:
            logger.exception("Error in worker loop")
            await asyncio.sleep(5)

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
