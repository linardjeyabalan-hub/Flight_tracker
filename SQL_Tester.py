import sqlite3

conn = sqlite3.connect("prices.db")

cursor = conn.execute("SELECT * FROM prices")

for row in cursor:
    print(row)

conn.close()