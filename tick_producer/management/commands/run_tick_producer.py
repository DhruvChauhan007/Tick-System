import time
import json
import logging
import websocket
from django.core.management.base import BaseCommand
from django.utils import timezone
from tick_consumer.tasks import get_broker, consume_tick

logger = logging.getLogger(__name__)

# Global dict to map trading symbol (e.g. "btcusdt") -> script DB id
# Populated once at startup from broker's script list
symbol_map = {}


def on_message(ws, message):
    """
    Called automatically by websocket-client every time
    Binance sends a new trade message over the WebSocket.
    Parses the raw JSON, extracts trade info, and queues
    a Celery task to store the tick in the database.
    """
    try:
        # Binance sends JSON strings — parse to Python dict
        data = json.loads(message)

        # Binance combined streams wrap the actual payload under a "data" key
        # e.g. { "stream": "btcusdt@trade", "data": { "e": "trade", ... } }
        trade_data = data.get("data")
        if not trade_data:
            logger.warning("No 'data' key in message: %s", data)
            return

        # Binance streams can send multiple event types (e.g. "trade", "kline")
        # We only care about "trade" events
        if trade_data.get("e") != "trade":
            return

        # Get the trading symbol from the message and look up its DB script id
        symbol = trade_data.get("s", "").lower()  # e.g. "BTCUSDT" -> "btcusdt"
        script_id = symbol_map.get(symbol)

        if not script_id:
            # Symbol received but not registered under this broker
            logger.warning("Unknown symbol: %s", symbol)
            return

        # Build a clean tick dict from the raw Binance trade fields:
        # "p" = price, "q" = quantity (volume)
        tick = {
            "script_id": script_id,
            "value": float(trade_data["p"]),   # trade price
            "volume": float(trade_data["q"]),  # trade quantity
            "received_at": timezone.now().isoformat()  # timestamp when WE received it
        }
        print("TICK:", tick)
        logger.info("Tick received: %s", tick)

        # Send tick to Celery worker asynchronously via .delay()
        # The worker will store it in the DB immediately (one tick at a time)
        try:
            consume_tick.delay(tick)
        except Exception as e:
            logger.exception(f"Failed to queue tick: {e}")

    except Exception as e:
        logger.error("Error processing message: %s", e, exc_info=True)


def on_open(ws):
    """
    Called once when the WebSocket connection is successfully established.
    Good place to send any initial subscription messages if needed.
    """
    print("CONNECTED TO BINANCE")


def on_error(ws, error):
    """
    Called when a WebSocket error occurs (network issue, bad frame, etc.)
    The outer while loop in handle() will automatically reconnect after this.
    """
    print("ERROR:", error)


def on_close(ws, close_status_code, close_msg):
    """
    Called when the WebSocket connection is closed — either by us,
    by Binance, or due to a network drop.
    The outer while loop will reconnect after a 5-second delay.
    """
    print("CLOSED:", close_status_code, close_msg)


class Command(BaseCommand):
    """
    Custom Django management command.
    Run with: python manage.py <command_name> --broker_id=1
    This keeps the WebSocket connection alive as a long-running process.
    """
    help = "Start Binance WebSocket tick consumer"

    def add_arguments(self, parser):
        # Accept broker_id from CLI so we know which broker's symbols to subscribe to
        parser.add_argument("--broker_id", type=int, required=True)

    def handle(self, *args, **kwargs):
        broker_id = kwargs["broker_id"]

        # Fetch broker + its scripts from DB via Celery task
        # Returns dict with broker info and list of scripts
        broker_data = get_broker(broker_id)

        # Build symbol_map: { "btcusdt": 3, "ethusdt": 5, ... }
        # Used in on_message() to resolve symbol -> script DB id
        global symbol_map
        symbol_map = {
            script["trading_symbol"].lower(): script["id"]
            for script in broker_data["scripts"]
        }

        if not symbol_map:
            self.stderr.write("No symbols found for broker. Exiting.")
            return

        # Build Binance combined stream URL
        # Format: wss://.../stream?streams=btcusdt@trade/ethusdt@trade/...
        streams = "/".join(f"{symbol}@trade" for symbol in symbol_map)
        stream_url = f"wss://stream.binance.com:9443/stream?streams={streams}"

        self.stdout.write(f"Connecting to: {stream_url}")

        running = True

        try:
            # Keep reconnecting if the connection drops
            while running:
                # Create a new WebSocketApp with all event handlers attached
                ws = websocket.WebSocketApp(
                    stream_url,
                    on_message=on_message,  # fires on every incoming tick
                    on_open=on_open,        # fires on successful connect
                    on_error=on_error,      # fires on any error
                    on_close=on_close       # fires when connection closes
                )

                # Blocks here — runs the WebSocket event loop until disconnected
                ws.run_forever()

                # If we reach here, connection was lost — wait before retrying
                print("Reconnecting in 5 seconds...")
                time.sleep(5)

        except KeyboardInterrupt:
            # User pressed Ctrl+C — exit cleanly
            print("Stopping producer...")
            running = False