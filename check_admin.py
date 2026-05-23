import psycopg2
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:RdcrgixOGANtWvspNqPdFVPhyUkBmjeS@kodama.proxy.rlwy.net:59039/railway"
)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT id, telefon, ism, telegram_id, kod FROM super_adminlar")
rows = cur.fetchall()
print("=== Super adminlar ===")
for r in rows:
    print(f"ID:{r[0]} | Tel:{r[1]} | Ism:{r[2]} | TG_ID:{r[3]} | Kod:{r[4]}")

# Telefon formatini to'g'irlab qayta yozamiz
cur.execute("DELETE FROM super_adminlar WHERE telefon LIKE '%333930303%'")
cur.execute("""
    INSERT INTO super_adminlar (telefon, ism, kod) 
    VALUES ('333930303', 'Super Admin', '0001')
""")
conn.commit()

cur.execute("SELECT * FROM super_adminlar")
print("\n=== Yangilangandan keyin ===")
for r in cur.fetchall():
    print(r)

cur.close()
conn.close()
print("\n✅ Tayyor!")