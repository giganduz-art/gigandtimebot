import psycopg2
from datetime import datetime
import pytz
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import os

TASHKENT = pytz.timezone('Asia/Tashkent')
SUPER_ADMIN_KOD = os.environ.get("SUPER_ADMIN_KOD", "0001")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:RdcrgixOGANtWvspNqPdFVPhyUkBmjeS@kodama.proxy.rlwy.net:59039/railway"
)

def connect():
    return psycopg2.connect(DATABASE_URL)

def hozir():
    return datetime.now(TASHKENT)

def soat_format(soat_decimal):
    soat = int(float(soat_decimal or 0))
    daqiqa = int((float(soat_decimal or 0) - soat) * 60)
    return f"{soat} soat {daqiqa} daqiqa"

def kechikish_format(daqiqalar):
    d = int(daqiqalar or 0)
    soat = d // 60
    daqiqa = d % 60
    if soat > 0:
        return f"{soat} soat {daqiqa} daqiqa"
    return f"{daqiqa} daqiqa"

def create_tables():
    conn = connect()
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS super_adminlar (
        id SERIAL PRIMARY KEY,
        telefon TEXT NOT NULL,
        telegram_id BIGINT UNIQUE,
        ism TEXT DEFAULT 'Super Admin',
        kod TEXT DEFAULT '0001'
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS kompaniyalar (
        id SERIAL PRIMARY KEY,
        nomi TEXT NOT NULL,
        admin_telefon TEXT,
        admin_id BIGINT,
        admin_kod TEXT DEFAULT '1234',
        gps_lat REAL DEFAULT 41.299496,
        gps_lon REAL DEFAULT 69.240073,
        gps_radius INTEGER DEFAULT 200,
        holat TEXT DEFAULT 'faol',
        yaratilgan TEXT,
        gps_aktiv BOOLEAN DEFAULT TRUE,
        selfie_aktiv BOOLEAN DEFAULT TRUE,
        face_id_aktiv BOOLEAN DEFAULT FALSE,
        hikvision_aktiv BOOLEAN DEFAULT FALSE
    )''')

    # admin_kod ustunini qo'shish (agar yo'q bo'lsa)
    cur.execute("""
        ALTER TABLE kompaniyalar ADD COLUMN IF NOT EXISTS admin_kod TEXT DEFAULT '1234'
    """)

    cur.execute('''CREATE TABLE IF NOT EXISTS xodimlar (
        id SERIAL PRIMARY KEY,
        ism TEXT NOT NULL,
        telefon TEXT,
        kod TEXT,
        lavozim TEXT,
        oylik REAL DEFAULT 0,
        ish_boshlanish TEXT DEFAULT '09:00',
        ish_tugash TEXT DEFAULT '18:00',
        ishga_kirgan TEXT,
        telegram_id BIGINT UNIQUE,
        kompaniya_id INTEGER REFERENCES kompaniyalar(id),
        rol TEXT DEFAULT 'xodim',
        holat TEXT DEFAULT 'faol'
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS davomat (
        id SERIAL PRIMARY KEY,
        xodim_id INTEGER REFERENCES xodimlar(id),
        kompaniya_id INTEGER REFERENCES kompaniyalar(id),
        sana TEXT,
        keldi TEXT,
        ketdi TEXT,
        ish_soat REAL DEFAULT 0,
        kechikish INTEGER DEFAULT 0,
        holat TEXT DEFAULT 'normal',
        izoh TEXT,
        keldi_rasm TEXT,
        ketdi_rasm TEXT,
        kiritdi TEXT DEFAULT 'xodim',
        kiritdi_id BIGINT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS sababli_sorovlar (
        id SERIAL PRIMARY KEY,
        xodim_id INTEGER REFERENCES xodimlar(id),
        kompaniya_id INTEGER REFERENCES kompaniyalar(id),
        sana TEXT,
        sabab TEXT,
        holat TEXT DEFAULT 'kutilmoqda'
    )''')

    conn.commit()
    cur.close()
    conn.close()

# ==================== SUPER ADMIN ====================

def super_admin_tekshir(telefon):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, ism, telegram_id FROM super_adminlar WHERE telefon LIKE %s",
                (f"%{telefon[-9:]}%",))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def super_admin_kod_tekshir(kod):
    return kod == SUPER_ADMIN_KOD

def super_admin_telegram_saqlash(telefon, telegram_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id FROM super_adminlar WHERE telefon LIKE %s", (f"%{telefon[-9:]}%",))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE super_adminlar SET telegram_id=%s WHERE telefon LIKE %s",
                    (telegram_id, f"%{telefon[-9:]}%"))
    else:
        cur.execute("INSERT INTO super_adminlar (telefon, telegram_id) VALUES (%s, %s)",
                    (telefon, telegram_id))
    conn.commit()
    cur.close(); conn.close()

def super_admin_id_tekshir(telegram_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id FROM super_adminlar WHERE telegram_id=%s", (telegram_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row is not None

def super_admin_kod_ozgartir(yangi_kod):
    global SUPER_ADMIN_KOD
    SUPER_ADMIN_KOD = yangi_kod

def barcha_super_adminlar():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, telefon, telegram_id, ism FROM super_adminlar ORDER BY id")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def super_admin_qoshish(telefon, ism='Super Admin'):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id FROM super_adminlar WHERE telefon LIKE %s", (f"%{telefon[-9:]}%",))
    if cur.fetchone():
        cur.close(); conn.close()
        return False  # allaqachon bor
    cur.execute("INSERT INTO super_adminlar (telefon, ism) VALUES (%s, %s)", (telefon, ism))
    conn.commit()
    cur.close(); conn.close()
    return True

def super_admin_ochirish(sa_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM super_adminlar WHERE id=%s", (sa_id,))
    conn.commit()
    cur.close(); conn.close()

# ==================== KOMPANIYALAR ====================

def kompaniya_yaratish(nomi, admin_telefon, admin_kod='1234'):
    conn = connect()
    cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute('''INSERT INTO kompaniyalar (nomi, admin_telefon, admin_kod, yaratilgan)
                  VALUES (%s, %s, %s, %s) RETURNING id''', (nomi, admin_telefon, admin_kod, sana))
    komp_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    return komp_id

def barcha_kompaniyalar():
    conn = connect()
    cur = conn.cursor()
    cur.execute('''SELECT id, nomi, admin_telefon, holat, yaratilgan,
                  gps_aktiv, selfie_aktiv, face_id_aktiv, hikvision_aktiv, admin_kod
                  FROM kompaniyalar ORDER BY id''')
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def kompaniya_olish(komp_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute('''SELECT id, nomi, admin_telefon, admin_id, holat,
                  gps_lat, gps_lon, gps_radius, yaratilgan,
                  gps_aktiv, selfie_aktiv, face_id_aktiv, hikvision_aktiv, admin_kod
                  FROM kompaniyalar WHERE id=%s''', (komp_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def kompaniya_holat_ozgartir(komp_id, holat):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE kompaniyalar SET holat=%s WHERE id=%s", (holat, komp_id))
    conn.commit()
    cur.close(); conn.close()

def kompaniya_funksiya_ozgartir(komp_id, funksiya, qiymat):
    conn = connect()
    cur = conn.cursor()
    cur.execute(f"UPDATE kompaniyalar SET {funksiya}=%s WHERE id=%s", (qiymat, komp_id))
    conn.commit()
    cur.close(); conn.close()

def kompaniya_tahrirlash(komp_id, maydon, qiymat):
    conn = connect()
    cur = conn.cursor()
    cur.execute(f"UPDATE kompaniyalar SET {maydon}=%s WHERE id=%s", (qiymat, komp_id))
    conn.commit()
    cur.close(); conn.close()

def admin_telefon_orqali_kompaniya(telefon):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, nomi, holat, admin_kod FROM kompaniyalar WHERE admin_telefon LIKE %s",
                (f"%{telefon[-9:]}%",))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def admin_id_saqlash(komp_id, admin_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE kompaniyalar SET admin_id=%s WHERE id=%s", (admin_id, komp_id))
    conn.commit()
    cur.close(); conn.close()

def get_gps(komp_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT gps_lat, gps_lon, gps_radius FROM kompaniyalar WHERE id=%s", (komp_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        return row[0], row[1], row[2]
    return 41.299496, 69.240073, 200

# ==================== XODIMLAR ====================

def xodim_qoshish(ism, telefon, lavozim, oylik, ish_bosh, ish_tug, komp_id, rol, kod):
    conn = connect()
    cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute('''INSERT INTO xodimlar
        (ism, telefon, lavozim, oylik, ish_boshlanish, ish_tugash,
         kompaniya_id, rol, kod, ishga_kirgan)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id''',
        (ism, telefon, lavozim, oylik, ish_bosh, ish_tug, komp_id, rol, kod, sana))
    xodim_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    return xodim_id

def kompaniya_xodimlari(komp_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute('''SELECT id, ism, lavozim, telefon, oylik,
                  ish_boshlanish, ish_tugash, rol, kod, holat
                  FROM xodimlar WHERE kompaniya_id=%s ORDER BY id''', (komp_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def xodim_olish(xodim_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute('''SELECT id, ism, telefon, lavozim, oylik,
                  ish_boshlanish, ish_tugash, rol, kod, kompaniya_id, holat
                  FROM xodimlar WHERE id=%s''', (xodim_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def xodim_tahrirlash(xodim_id, maydon, qiymat):
    conn = connect()
    cur = conn.cursor()
    cur.execute(f"UPDATE xodimlar SET {maydon}=%s WHERE id=%s", (qiymat, xodim_id))
    conn.commit()
    cur.close(); conn.close()

def telegram_id_orqali_xodim(telegram_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, ism, rol, kompaniya_id FROM xodimlar WHERE telegram_id=%s", (telegram_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def telefon_orqali_xodim(telefon):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, ism, rol, kompaniya_id FROM xodimlar WHERE telefon LIKE %s",
                (f"%{telefon[-9:]}%",))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def xodim_telegram_saqlash(xodim_id, telegram_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE xodimlar SET telegram_id=%s WHERE id=%s", (telegram_id, xodim_id))
    conn.commit()
    cur.close(); conn.close()

def hr_idlari(komp_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT telegram_id FROM xodimlar WHERE kompaniya_id=%s AND rol='hr' AND telegram_id IS NOT NULL", (komp_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [r[0] for r in rows]

# ==================== DAVOMAT ====================

def keldi_belgilash(xodim_id, komp_id, kiritdi="xodim", kiritdi_id=None):
    conn = connect()
    cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    vaqt = hozir().strftime("%H:%M")
    cur.execute("SELECT id FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, sana))
    if cur.fetchone():
        cur.close(); conn.close()
        return "⚠️ Bugun allaqachon belgilangan!"
    cur.execute("SELECT ish_boshlanish FROM xodimlar WHERE id=%s", (xodim_id,))
    xodim = cur.fetchone()
    kechikish = 0
    if xodim:
        try:
            belgi = datetime.strptime(xodim[0], "%H:%M")
            keldi_v = datetime.strptime(vaqt, "%H:%M")
            if keldi_v > belgi:
                kechikish = int((keldi_v - belgi).total_seconds() / 60)
        except: pass
    cur.execute('''INSERT INTO davomat (xodim_id, kompaniya_id, sana, keldi, kechikish, kiritdi, kiritdi_id)
                  VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                (xodim_id, komp_id, sana, vaqt, kechikish, kiritdi, kiritdi_id))
    conn.commit()
    cur.close(); conn.close()
    if kechikish > 0:
        return f"✅ Keldi vaqti: {vaqt}\n⚠️ Kechikish: {kechikish_format(kechikish)}"
    return f"✅ Keldi vaqti: {vaqt}"

def keldi_rasm_saqlash(xodim_id, rasm_id):
    conn = connect()
    cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute("UPDATE davomat SET keldi_rasm=%s WHERE xodim_id=%s AND sana=%s", (rasm_id, xodim_id, sana))
    conn.commit()
    cur.close(); conn.close()

def ketdi_belgilash(xodim_id, komp_id, kiritdi="xodim", kiritdi_id=None):
    conn = connect()
    cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    vaqt = hozir().strftime("%H:%M")
    cur.execute("SELECT keldi FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, sana))
    row = cur.fetchone()
    if not row or not row[0]:
        cur.close(); conn.close()
        return "❌ Avval keldi belgilanmagan!"
    try:
        keldi = datetime.strptime(row[0], "%H:%M")
        ketdi = datetime.strptime(vaqt, "%H:%M")
        daqiqalar = int((ketdi - keldi).total_seconds() / 60)
        ish_soat = round(daqiqalar / 60, 2)
        soat = daqiqalar // 60
        daqiqa = daqiqalar % 60
        ish_matn = f"{soat} soat {daqiqa} daqiqa"
    except:
        ish_soat = 0
        ish_matn = "0 soat 0 daqiqa"
    cur.execute('''UPDATE davomat SET ketdi=%s, ish_soat=%s, kiritdi=%s, kiritdi_id=%s
                  WHERE xodim_id=%s AND sana=%s''',
                (vaqt, ish_soat, kiritdi, kiritdi_id, xodim_id, sana))
    conn.commit()
    cur.close(); conn.close()
    return f"🚪 Ketdi vaqti: {vaqt}\n⏱ Ish vaqti: {ish_matn}"

def ketdi_rasm_saqlash(xodim_id, rasm_id):
    conn = connect()
    cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute("UPDATE davomat SET ketdi_rasm=%s WHERE xodim_id=%s AND sana=%s", (rasm_id, xodim_id, sana))
    conn.commit()
    cur.close(); conn.close()

def xodim_davomati(xodim_id, oy=None):
    conn = connect()
    cur = conn.cursor()
    if oy:
        cur.execute('''SELECT sana, keldi, ketdi, ish_soat, kechikish, holat, izoh, kiritdi
                      FROM davomat WHERE xodim_id=%s AND sana LIKE %s ORDER BY sana''',
                    (xodim_id, f"%{oy}%"))
    else:
        cur.execute('''SELECT sana, keldi, ketdi, ish_soat, kechikish, holat, izoh, kiritdi
                      FROM davomat WHERE xodim_id=%s ORDER BY sana''', (xodim_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def kompaniya_davomati(komp_id, oy=None):
    conn = connect()
    cur = conn.cursor()
    if oy:
        cur.execute('''SELECT x.ism, d.sana, d.keldi, d.ketdi, d.ish_soat, d.kechikish, d.holat, d.izoh
                      FROM davomat d JOIN xodimlar x ON d.xodim_id=x.id
                      WHERE d.kompaniya_id=%s AND d.sana LIKE %s ORDER BY d.sana''',
                    (komp_id, f"%{oy}%"))
    else:
        cur.execute('''SELECT x.ism, d.sana, d.keldi, d.ketdi, d.ish_soat, d.kechikish, d.holat, d.izoh
                      FROM davomat d JOIN xodimlar x ON d.xodim_id=x.id
                      WHERE d.kompaniya_id=%s ORDER BY d.sana''', (komp_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def manual_davomat(xodim_id, komp_id, sana, keldi_vaqt, ketdi_vaqt, holat, izoh, kiritdi_ism, kiritdi_id):
    conn = connect()
    cur = conn.cursor()
    ish_soat = 0
    kechikish = 0
    try:
        keldi = datetime.strptime(keldi_vaqt, "%H:%M")
        ketdi = datetime.strptime(ketdi_vaqt, "%H:%M")
        daqiqalar = int((ketdi - keldi).total_seconds() / 60)
        ish_soat = round(daqiqalar / 60, 2)
        cur.execute("SELECT ish_boshlanish FROM xodimlar WHERE id=%s", (xodim_id,))
        x = cur.fetchone()
        if x:
            belgi = datetime.strptime(x[0], "%H:%M")
            if keldi > belgi:
                kechikish = int((keldi - belgi).total_seconds() / 60)
    except: pass
    cur.execute("SELECT id FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, sana))
    if cur.fetchone():
        cur.execute('''UPDATE davomat SET keldi=%s, ketdi=%s, ish_soat=%s, kechikish=%s,
                      holat=%s, izoh=%s, kiritdi=%s, kiritdi_id=%s WHERE xodim_id=%s AND sana=%s''',
                    (keldi_vaqt, ketdi_vaqt, ish_soat, kechikish, holat, izoh, kiritdi_ism, kiritdi_id, xodim_id, sana))
    else:
        cur.execute('''INSERT INTO davomat (xodim_id, kompaniya_id, sana, keldi, ketdi, ish_soat,
                      kechikish, holat, izoh, kiritdi, kiritdi_id)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (xodim_id, komp_id, sana, keldi_vaqt, ketdi_vaqt, ish_soat,
                     kechikish, holat, izoh, kiritdi_ism, kiritdi_id))
    conn.commit()
    cur.close(); conn.close()
    return "✅ Davomat kiritildi!"

# ==================== SABABLI SO'ROVLAR ====================

def sababli_sorov_saqlash(xodim_id, komp_id, sana, sabab):
    conn = connect()
    cur = conn.cursor()
    cur.execute('''INSERT INTO sababli_sorovlar (xodim_id, kompaniya_id, sana, sabab)
                  VALUES (%s, %s, %s, %s) RETURNING id''', (xodim_id, komp_id, sana, sabab))
    sorov_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    return sorov_id

def sababli_sorov_yangilash(sorov_id, holat, xodim_id, sana, sabab):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE sababli_sorovlar SET holat=%s WHERE id=%s", (holat, sorov_id))
    if holat == 'tasdiqlandi':
        cur.execute("SELECT id FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, sana))
        if cur.fetchone():
            cur.execute("UPDATE davomat SET holat='sababli', izoh=%s WHERE xodim_id=%s AND sana=%s",
                       (sabab, xodim_id, sana))
        else:
            cur.execute("INSERT INTO davomat (xodim_id, sana, holat, izoh) VALUES (%s, %s, 'sababli', %s)",
                       (xodim_id, sana, sabab))
    conn.commit()
    cur.close(); conn.close()

# ==================== HISOBOTLAR ====================

def super_admin_hisobot():
    conn = connect()
    cur = conn.cursor()
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "Kompaniyalar"
    ws1.append(["#", "Kompaniya", "Admin telefon", "Holat", "Xodimlar", "Yaratilgan"])
    cur.execute("SELECT id, nomi, admin_telefon, holat, yaratilgan FROM kompaniyalar ORDER BY id")
    kompaniyalar = cur.fetchall()
    for i, k in enumerate(kompaniyalar, 1):
        cur.execute("SELECT COUNT(*) FROM xodimlar WHERE kompaniya_id=%s", (k[0],))
        soni = cur.fetchone()[0]
        ws1.append([i, k[1], k[2], k[3], soni, k[4]])

    ws2 = wb.create_sheet("Barcha xodimlar")
    ws2.append(["#", "Kompaniya", "Ism", "Lavozim", "Telefon", "Oylik", "Ish vaqti", "Rol"])
    cur.execute('''SELECT k.nomi, x.ism, x.lavozim, x.telefon, x.oylik,
                  x.ish_boshlanish, x.ish_tugash, x.rol
                  FROM xodimlar x JOIN kompaniyalar k ON x.kompaniya_id=k.id ORDER BY k.id, x.id''')
    for i, x in enumerate(cur.fetchall(), 1):
        ws2.append([i, x[0], x[1], x[2], x[3], x[4], f"{x[5]}-{x[6]}", x[7]])

    ws3 = wb.create_sheet("Barcha davomat")
    ws3.append(["#", "Kompaniya", "Xodim", "Sana", "Keldi", "Ketdi", "Ish vaqti", "Kechikish", "Holat"])
    cur.execute('''SELECT k.nomi, x.ism, d.sana, d.keldi, d.ketdi, d.ish_soat, d.kechikish, d.holat
                  FROM davomat d JOIN xodimlar x ON d.xodim_id=x.id
                  JOIN kompaniyalar k ON d.kompaniya_id=k.id ORDER BY k.id, d.sana''')
    for i, d in enumerate(cur.fetchall(), 1):
        ws3.append([i, d[0], d[1], d[2], d[3], d[4], soat_format(d[5]), kechikish_format(d[6]), d[7]])

    ws4 = wb.create_sheet("Statistika")
    ws4.append(["Kompaniya", "Jami xodim", "Bugun kelgan", "O'rtacha kechikish", "Holat"])
    bugun = hozir().strftime("%Y-%m-%d")
    for k in kompaniyalar:
        cur.execute("SELECT COUNT(*) FROM xodimlar WHERE kompaniya_id=%s", (k[0],))
        jami = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM davomat WHERE kompaniya_id=%s AND sana=%s", (k[0], bugun))
        bugun_k = cur.fetchone()[0]
        cur.execute("SELECT AVG(kechikish) FROM davomat WHERE kompaniya_id=%s", (k[0],))
        ortacha = cur.fetchone()[0] or 0
        ws4.append([k[1], jami, bugun_k, round(ortacha, 1), k[3]])

    cur.close(); conn.close()
    fayl = "super_hisobot.xlsx"
    wb.save(fayl)
    return fayl

def kompaniya_hisobot(komp_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT nomi FROM kompaniyalar WHERE id=%s", (komp_id,))
    komp_nomi = cur.fetchone()[0]
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "Xodimlar"
    ws1.append(["#", "Ism", "Lavozim", "Telefon", "Oylik", "Ish vaqti", "Rol"])
    cur.execute('''SELECT id, ism, lavozim, telefon, oylik, ish_boshlanish, ish_tugash, rol
                  FROM xodimlar WHERE kompaniya_id=%s ORDER BY id''', (komp_id,))
    xodimlar = cur.fetchall()
    for i, x in enumerate(xodimlar, 1):
        ws1.append([i, x[1], x[2], x[3], x[4], f"{x[5]}-{x[6]}", x[7]])

    ws2 = wb.create_sheet("Davomat")
    ws2.append(["#", "Xodim", "Sana", "Keldi", "Ketdi", "Ish vaqti", "Kechikish", "Holat", "Izoh"])
    cur.execute('''SELECT x.ism, d.sana, d.keldi, d.ketdi, d.ish_soat, d.kechikish, d.holat, d.izoh
                  FROM davomat d JOIN xodimlar x ON d.xodim_id=x.id
                  WHERE d.kompaniya_id=%s ORDER BY d.sana, x.ism''', (komp_id,))
    for i, d in enumerate(cur.fetchall(), 1):
        ws2.append([i, d[0], d[1], d[2], d[3], soat_format(d[4]), kechikish_format(d[5]), d[6], d[7] or "—"])

    ws3 = wb.create_sheet("Statistika")
    ws3.append(["Xodim", "Lavozim", "Jami kun", "Jami ish soat", "O'rtacha kechikish", "Kech kelgan"])
    for x in xodimlar:
        cur.execute('''SELECT COUNT(*), SUM(ish_soat), AVG(kechikish), COUNT(CASE WHEN kechikish>0 THEN 1 END)
                      FROM davomat WHERE xodim_id=%s''', (x[0],))
        s = cur.fetchone()
        ws3.append([x[1], x[2], s[0] or 0, soat_format(s[1] or 0), kechikish_format(s[2] or 0), s[3] or 0])

    cur.close(); conn.close()
    fayl = f"hisobot_{komp_nomi}.xlsx"
    wb.save(fayl)
    return fayl

create_tables()
print("Baza tayyor!")