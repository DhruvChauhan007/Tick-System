import time
import MySQLdb

while True:
    try:
        MySQLdb.connect(
            host="mysql",
            user="root",
            passwd="root",
            db="tick_db"
        )
        print("Database is ready!")
        break

    except Exception as e:
        print(f"Waiting for database... {e}")
        time.sleep(2)