import psycopg2
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:RdcrgixOGANtWvspNqPdFVPhyUkBmjeS@kodama.proxy.rlwy.net:59039/railway"
)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Telefon raqamni turli formatda qo'shish
telefon = "+998333930303"

cur.execute("""
    INSERT INTO super_adminlar (telefon, ism, kod) 
    VALUES (%s, 'Super Admin', '0001') 
    ON CONFLICT (telefon) DO UPDATE SET ism='Super Admin', kod='0001'
""", (telefon,))

conn.commit()

# Tekshir
cur.execute("SELECT * FROM super_adminlar")
rows = cur.fetchall()
print("Super adminlar:")
for r in rows:
    print(r)

cur.close()
conn.close()
print("\n✅ Super Admin qo'shildi! Telefon:", telefon, "| Kod: 0001")