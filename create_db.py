import MySQLdb

db_config = {
    'user': 'root',
    'passwd': 'Sameem23@',
    'host': 'localhost',
}

try:
    db = MySQLdb.connect(**db_config)
    cursor = db.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS banking_db")
    print("Database 'banking_db' created successfully (or already existed).")
    cursor.close()
    db.close()
except Exception as err:
    print(f"Error: {err}")
