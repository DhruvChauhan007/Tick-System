from celery import shared_task
from .models import Broker
from datetime import datetime
from .models import Tick, Script
import logging
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)


@shared_task
def test_task():
    """
    Simple sanity-check task to verify Celery is running.
    Run with: celery -A <project> call tick_consumer.tasks.test_task
    """
    return "success"


@shared_task
def get_broker(broker_id):
    """
    Fetches a broker and all its associated scripts from the DB.

    Called once at WebSocket startup (in the management command) to:
    - Get broker credentials/config
    - Build the symbol_map used to route incoming ticks to the right script

    Args:
        broker_id (int): Primary key of the Broker record

    Returns:
        dict: Broker info + list of script dicts
    """
    # Fetch the broker record — raises Broker.DoesNotExist if not found
    broker = Broker.objects.get(id=broker_id)

    # Serialize each related script into a plain dict
    # (Celery tasks must return JSON-serializable data, not ORM objects)
    scripts = []
    for script in broker.scripts.all():
        scripts.append({
            "id": script.id,
            "name": script.name,
            "trading_symbol": script.trading_symbol,  # e.g. "btcusdt"
            "additional_data": script.additional_data
        })

    return {
        "id": broker.id,
        "type": broker.type,        # e.g. "binance", "zerodha"
        "name": broker.name,
        "api_config": broker.api_config,  # API keys, secrets, etc.
        "scripts": scripts
    }


@shared_task
def consume_tick(tick_data):
    """
    Receives a single tick dict and immediately stores it in the DB.

    Called by the WebSocket on_message() handler via .delay()
    every time a new trade arrives from Binance.

    Args:
        tick_data (dict): {
            "script_id": int,       # which script/symbol this tick belongs to
            "value": float,         # trade price
            "volume": float,        # trade quantity (optional)
            "received_at": str      # ISO format timestamp e.g. "2026-06-06T06:44:44.837992+00:00"
        }

    Returns:
        str: Confirmation message with the saved Tick's DB id
    """
    # Look up the Script this tick belongs to
    # Raises Script.DoesNotExist if script_id is invalid
    script = Script.objects.get(id=tick_data["script_id"])

    # Create and immediately save one Tick row to the DB
    tick = Tick.objects.create(
        script=script,
        tick_value=tick_data["value"],
        volume=tick_data.get("volume"),  # .get() so it defaults to None if missing

        # Convert ISO string back to a datetime object for the DB field
        # e.g. "2026-06-06T06:44:44.837992+00:00" -> datetime with tzinfo
        received_at_producer=datetime.fromisoformat(tick_data["received_at"])
    )

    return f"Tick {tick.id} stored"