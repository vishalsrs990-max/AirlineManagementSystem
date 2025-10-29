import sqlite3

# Connect to (or create) flights.db
conn = sqlite3.connect('flights.db')
cursor = conn.cursor()

# Create the flights table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS flights (
        flightID TEXT PRIMARY KEY,
        origin TEXT NOT NULL,
        destination TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL
    )
''')

conn.commit()
conn.close()

print("✅ flights.db initialized with 'flights' table.")