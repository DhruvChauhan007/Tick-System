This project consists of:

Django application
Tick Producer app
Tick Consumer app
Celery worker
Redis broker
MySQL database
Binance WebSocket integration

The producer receives live ticks from Binance and sends them to Celery. Celery processes the ticks and stores them in MySQL.

----------------------------------------------------------------------------------------------------------------------------

Bring Up the Stack

Start all services:
docker compose up --build

Services:

Django
MySQL
Redis
Celery Worker

----------------------------------------------------------------------------------------------------------------------------

Apply Migrations
docker compose exec django python manage.py migrate

----------------------------------------------------------------------------------------------------------------------------

Create Superuser
docker compose exec django python manage.py createsuperuser
Follow to create username, email and password.

----------------------------------------------------------------------------------------------------------------------------

Django Admin Login

Open:
http://localhost:8000/admin
Login using the superuser credentials created above.

----------------------------------------------------------------------------------------------------------------------------

Add Broker

In Django Admin:
Open Brokers
Click Add Broker

Example:
Name: Binance Live
Type: BINANCE

Save the Broker.

----------------------------------------------------------------------------------------------------------------------------

Add Scripts

Create Scripts and attach them to the Broker.

Example:
Bitcoin
Trading Symbol: btcusdt
Ethereum
Trading Symbol: ethusdt
Pepe
Trading Symbol: pepeusdt

Save all Scripts.

----------------------------------------------------------------------------------------------------------------------------

Run Tick Producer

Start the Binance tick producer:
docker compose exec django python manage.py run_tick_producer --broker_id=1

Example output:

Connected to Binance
TICK: {'script_id': 1, 'value': 61250.10, 'volume': 0.001}

----------------------------------------------------------------------------------------------------------------------------

Verify Tick Storage

Open Django Admin:
http://localhost:8000/admin
Login using the superuser credentials.

Navigate to:
Tick Consumer → Ticks

Refresh the Ticks page periodically.
New tick records should appear with:
Script
Tick Value
Volume
Received At Producer
Click any tick record to view its complete details.

This confirms that live Binance ticks are successfully being processed through Celery and stored in the database.

----------------------------------------------------------------------------------------------------------------------------
