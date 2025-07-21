import pymysql

# --- CONFIG --- #
HOST = '127.0.0.1'
USER = 'root'
PASSWORD = 'admin'
DATABASE = 'blog_scraper'

try:
    connection = pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE
    )

    print("✅ Connected successfully to MySQL using PyMySQL.")
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE();")
        db = cursor.fetchone()
        print(f"📂 Current database: {db[0]}")

except pymysql.err.OperationalError as e:
    if "Access denied" in str(e):
        print("❌ Access Denied: Check username/password.")
    elif "Can't connect" in str(e):
        print("❌ Can't connect: Check if MySQL server is running.")
    elif "Unknown database" in str(e):
        print(f"❌ Unknown database '{DATABASE}'.")
    else:
        print(f"❌ Operational error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
finally:
    if 'connection' in locals() and connection.open:
        connection.close()
        print("🔌 Connection closed.")
