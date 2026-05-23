import psycopg2
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:RdcrgixOGANtWvspNqPdFVPhyUkBmjeS@kodama.proxy.rlwy.net:59039/railway"
)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Mavjud ustunlarni tekshir
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'kompaniyalar'
""")
ustunlar = [r[0] for r in cur.fetchall()]
print("Mavjud ustunlar:", ustunlar)

# Yetishmayotgan ustunlarni qo'sh
qoshish = {
    'holat': "ALTER TABLE kompaniyalar ADD COLUMN holat TEXT DEFAULT 'faol'",
    'gps_aktiv': "ALTER TABLE kompaniyalar ADD COLUMN gps_aktiv BOOLEAN DEFAULT TRUE",
    'selfie_aktiv': "ALTER TABLE kompaniyalar ADD COLUMN selfie_aktiv BOOLEAN DEFAULT TRUE",
    'face_id_aktiv': "ALTER TABLE kompaniyalar ADD COLUMN face_id_aktiv BOOLEAN DEFAULT FALSE",
    'hikvision_aktiv': "ALTER TABLE kompaniyalar ADD COLUMN hikvision_aktiv BOOLEAN DEFAULT FALSE",
    'admin_id': "ALTER TABLE kompaniyalar ADD COLUMN admin_id BIGINT",
    'yaratilgan': "ALTER TABLE kompaniyalar ADD COLUMN yaratilgan TEXT",
    'gps_lat': "ALTER TABLE kompaniyalar ADD COLUMN gps_lat REAL DEFAULT 41.299496",
    'gps_lon': "ALTER TABLE kompaniyalar ADD COLUMN gps_lon REAL DEFAULT 69.240073",
    'gps_radius': "ALTER TABLE kompaniyalar ADD COLUMN gps_radius INTEGER DEFAULT 200",
}

for ustun, sql in qoshish.items():
    if ustun not in ustunlar:
        cur.execute(sql)
        print(f"✅ '{ustun}' ustuni qo'shildi")
    else:
        print(f"⏭ '{ustun}' allaqachon mavjud")

conn.commit()
cur.close()
conn.close()
print("\nBaza yangilandi!")
