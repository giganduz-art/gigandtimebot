import psycopg2
from datetime import datetime, timedelta
import pytz
import openpyxl
import os

TASHKENT = pytz.timezone('Asia/Tashkent')
SUPER_ADMIN_KOD = os.environ.get("SUPER_ADMIN_KOD", "0001")  # Boshlang'ich kod
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:RdcrgixOGANtWvspNqPdFVPhyUkBmjeS@kodama.proxy.rlwy.net:59039/railway"
)

def connect():
    return psycopg2.connect(DATABASE_URL)

def hozir():
    return datetime.now(TASHKENT)

def soat_format(v):
    v = float(v or 0)
    s = int(v); d = int((v - s) * 60)
    return f"{s} soat {d} daqiqa"

def kechikish_format(d):
    d = int(d or 0)
    return f"{d//60} soat {d%60} daqiqa" if d >= 60 else f"{d} daqiqa"

def create_tables():
    conn = connect(); cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS super_adminlar (
        id SERIAL PRIMARY KEY, telefon TEXT NOT NULL,
        telegram_id BIGINT, ism TEXT DEFAULT 'Super Admin', kod TEXT DEFAULT '0001'
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS kompaniyalar (
        id SERIAL PRIMARY KEY, nomi TEXT NOT NULL,
        admin_telefon TEXT, admin_id BIGINT, admin_kod TEXT DEFAULT '1234',
        gps_lat REAL DEFAULT 41.299496, gps_lon REAL DEFAULT 69.240073,
        gps_radius INTEGER DEFAULT 200, holat TEXT DEFAULT 'faol', yaratilgan TEXT,
        gps_aktiv BOOLEAN DEFAULT TRUE, selfie_aktiv BOOLEAN DEFAULT TRUE,
        face_id_aktiv BOOLEAN DEFAULT FALSE, hikvision_aktiv BOOLEAN DEFAULT FALSE,
        live_gps_aktiv BOOLEAN DEFAULT FALSE, live_gps_tekshiruv BOOLEAN DEFAULT FALSE
    )''')
    cur.execute("ALTER TABLE kompaniyalar ADD COLUMN IF NOT EXISTS admin_kod TEXT DEFAULT '1234'")
    cur.execute("ALTER TABLE kompaniyalar ADD COLUMN IF NOT EXISTS live_gps_aktiv BOOLEAN DEFAULT FALSE")
    cur.execute("ALTER TABLE kompaniyalar ADD COLUMN IF NOT EXISTS live_gps_tekshiruv BOOLEAN DEFAULT FALSE")
    cur.execute("ALTER TABLE kompaniyalar ADD COLUMN IF NOT EXISTS wifi_aktiv BOOLEAN DEFAULT FALSE")
    cur.execute("ALTER TABLE kompaniyalar ADD COLUMN IF NOT EXISTS wifi_ssid TEXT DEFAULT ''")

    # Migration: rename wifi_ip to wifi_mac if wifi_ip exists but wifi_mac doesn't
    try:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='kompaniyalar' AND column_name='wifi_ip'")
        if cur.fetchone():
            cur.execute("ALTER TABLE kompaniyalar RENAME COLUMN wifi_ip TO wifi_mac")
    except:
        pass

    # If migration didn't work, just add wifi_mac column
    cur.execute("ALTER TABLE kompaniyalar ADD COLUMN IF NOT EXISTS wifi_mac TEXT DEFAULT ''")

    cur.execute('''CREATE TABLE IF NOT EXISTS xodimlar (
        id SERIAL PRIMARY KEY, ism TEXT NOT NULL, telefon TEXT, kod TEXT,
        lavozim TEXT, oylik REAL DEFAULT 0,
        ish_boshlanish TEXT DEFAULT '09:00', ish_tugash TEXT DEFAULT '18:00',
        ishga_kirgan TEXT, telegram_id BIGINT UNIQUE,
        kompaniya_id INTEGER REFERENCES kompaniyalar(id),
        rol TEXT DEFAULT 'xodim', holat TEXT DEFAULT 'faol', tugilgan_kun TEXT
    )''')
    cur.execute("ALTER TABLE xodimlar ADD COLUMN IF NOT EXISTS tugilgan_kun TEXT")

    cur.execute('''CREATE TABLE IF NOT EXISTS davomat (
        id SERIAL PRIMARY KEY, xodim_id INTEGER REFERENCES xodimlar(id),
        kompaniya_id INTEGER REFERENCES kompaniyalar(id),
        sana TEXT, keldi TEXT, ketdi TEXT, ish_soat REAL DEFAULT 0,
        kechikish INTEGER DEFAULT 0, holat TEXT DEFAULT 'normal',
        izoh TEXT, keldi_rasm TEXT, ketdi_rasm TEXT,
        kiritdi TEXT DEFAULT 'xodim', kiritdi_id BIGINT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS sababli_sorovlar (
        id SERIAL PRIMARY KEY, xodim_id INTEGER REFERENCES xodimlar(id),
        kompaniya_id INTEGER REFERENCES kompaniyalar(id),
        sana TEXT, sabab TEXT, holat TEXT DEFAULT 'kutilmoqda'
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS live_lokatsiyalar (
        id SERIAL PRIMARY KEY, xodim_id INTEGER REFERENCES xodimlar(id),
        kompaniya_id INTEGER REFERENCES kompaniyalar(id),
        lat REAL, lon REAL, vaqt TEXT, faol BOOLEAN DEFAULT TRUE
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS sozlamalar (
        kalit TEXT PRIMARY KEY, qiymat TEXT
    )''')
    cur.execute("INSERT INTO sozlamalar(kalit,qiymat) VALUES('murojaat_raqam','919712222') ON CONFLICT(kalit) DO NOTHING")

    cur.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY, kompaniya_id INTEGER REFERENCES kompaniyalar(id),
        xodim_id INTEGER REFERENCES xodimlar(id),
        amal TEXT, tafsilot TEXT, vaqt TEXT, rasm_id TEXT, video_id TEXT,
        user_id BIGINT, user_ism TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS wifi_macs (
        id SERIAL PRIMARY KEY, kompaniya_id INTEGER REFERENCES kompaniyalar(id),
        mac_address TEXT NOT NULL, nomi TEXT DEFAULT ''
    )''')

    conn.commit(); cur.close(); conn.close()

# ========== SOZLAMALAR ==========

def get_murojaat_raqam():
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT qiymat FROM sozlamalar WHERE kalit='murojaat_raqam'")
    r = cur.fetchone(); cur.close(); conn.close()
    return r[0] if r else '919712222'

def set_murojaat_raqam(raqam):
    conn = connect(); cur = conn.cursor()
    cur.execute("INSERT INTO sozlamalar(kalit,qiymat) VALUES('murojaat_raqam',%s) ON CONFLICT(kalit) DO UPDATE SET qiymat=%s", (raqam, raqam))
    conn.commit(); cur.close(); conn.close()

# ========== SUPER ADMIN ==========

def super_admin_tekshir(telefon):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id,ism,telegram_id FROM super_adminlar WHERE telefon LIKE %s", (f"%{telefon[-9:]}%",))
    r = cur.fetchone(); cur.close(); conn.close(); return r

def super_admin_kod_tekshir(kod):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT kod FROM super_adminlar LIMIT 1")
    r = cur.fetchone(); cur.close(); conn.close()
    db_kod = r[0] if r else SUPER_ADMIN_KOD
    return kod == db_kod

def super_admin_telegram_saqlash(telefon, telegram_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id FROM super_adminlar WHERE telefon LIKE %s", (f"%{telefon[-9:]}%",))
    if cur.fetchone():
        cur.execute("UPDATE super_adminlar SET telegram_id=%s WHERE telefon LIKE %s", (telegram_id, f"%{telefon[-9:]}%"))
    else:
        cur.execute("INSERT INTO super_adminlar(telefon,telegram_id) VALUES(%s,%s)", (telefon, telegram_id))
    conn.commit(); cur.close(); conn.close()

def super_admin_id_tekshir(telegram_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id FROM super_adminlar WHERE telegram_id=%s", (telegram_id,))
    r = cur.fetchone(); cur.close(); conn.close(); return r is not None

def super_admin_kod_ozgartir(yangi_kod):
    conn = connect(); cur = conn.cursor()
    cur.execute("UPDATE super_adminlar SET kod=%s", (yangi_kod,))
    conn.commit(); cur.close(); conn.close()

def super_admin_telefon_ozgartir(telegram_id, tel):
    conn = connect(); cur = conn.cursor()
    cur.execute("UPDATE super_adminlar SET telefon=%s WHERE telegram_id=%s", (tel, telegram_id))
    conn.commit(); cur.close(); conn.close()

def super_admin_ism_ozgartir(telegram_id, ism):
    conn = connect(); cur = conn.cursor()
    cur.execute("UPDATE super_adminlar SET ism=%s WHERE telegram_id=%s", (ism, telegram_id))
    conn.commit(); cur.close(); conn.close()

def barcha_super_adminlar():
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id,telefon,telegram_id,ism FROM super_adminlar ORDER BY id")
    r = cur.fetchall(); cur.close(); conn.close(); return r

def barcha_super_admin_idlar():
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT telegram_id FROM super_adminlar WHERE telegram_id IS NOT NULL")
    r = cur.fetchall(); cur.close(); conn.close(); return [x[0] for x in r]

def super_admin_qoshish(telefon, ism='Super Admin'):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id FROM super_adminlar WHERE telefon LIKE %s", (f"%{telefon[-9:]}%",))
    if cur.fetchone(): cur.close(); conn.close(); return False
    cur.execute("INSERT INTO super_adminlar(telefon,ism) VALUES(%s,%s)", (telefon, ism))
    conn.commit(); cur.close(); conn.close(); return True

def super_admin_ochirish(sa_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("DELETE FROM super_adminlar WHERE id=%s", (sa_id,))
    conn.commit(); cur.close(); conn.close()

def super_admin_olish(telegram_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id,telefon,ism FROM super_adminlar WHERE telegram_id=%s", (telegram_id,))
    r = cur.fetchone(); cur.close(); conn.close(); return r

# ========== KOMPANIYALAR ==========

def kompaniya_yaratish(nomi, admin_telefon, admin_kod='1234'):
    conn = connect(); cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute("INSERT INTO kompaniyalar(nomi,admin_telefon,admin_kod,yaratilgan) VALUES(%s,%s,%s,%s) RETURNING id",
                (nomi, admin_telefon, admin_kod, sana))
    kid = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close(); return kid

def kompaniya_ochirish(komp_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("DELETE FROM live_lokatsiyalar WHERE kompaniya_id=%s", (komp_id,))
    cur.execute("DELETE FROM sababli_sorovlar WHERE kompaniya_id=%s", (komp_id,))
    cur.execute("DELETE FROM davomat WHERE kompaniya_id=%s", (komp_id,))
    cur.execute("DELETE FROM xodimlar WHERE kompaniya_id=%s", (komp_id,))
    cur.execute("DELETE FROM kompaniyalar WHERE id=%s", (komp_id,))
    conn.commit(); cur.close(); conn.close()

def barcha_kompaniyalar():
    conn = connect(); cur = conn.cursor()
    cur.execute('''SELECT id,nomi,admin_telefon,holat,yaratilgan,
                  gps_aktiv,selfie_aktiv,face_id_aktiv,hikvision_aktiv,admin_kod,
                  live_gps_aktiv,live_gps_tekshiruv FROM kompaniyalar ORDER BY id''')
    r = cur.fetchall(); cur.close(); conn.close(); return r

def kompaniya_olish(komp_id):
    conn = connect(); cur = conn.cursor()
    cur.execute('''SELECT id,nomi,admin_telefon,admin_id,holat,
                  gps_lat,gps_lon,gps_radius,yaratilgan,
                  gps_aktiv,selfie_aktiv,face_id_aktiv,hikvision_aktiv,admin_kod,
                  live_gps_aktiv,live_gps_tekshiruv,wifi_aktiv,wifi_ssid,wifi_mac FROM kompaniyalar WHERE id=%s''', (komp_id,))
    r = cur.fetchone(); cur.close(); conn.close(); return r

def kompaniya_holat_ozgartir(komp_id, holat):
    conn = connect(); cur = conn.cursor()
    cur.execute("UPDATE kompaniyalar SET holat=%s WHERE id=%s", (holat, komp_id))
    conn.commit(); cur.close(); conn.close()

def kompaniya_funksiya_ozgartir(komp_id, funksiya, qiymat):
    conn = connect(); cur = conn.cursor()
    cur.execute(f"UPDATE kompaniyalar SET {funksiya}=%s WHERE id=%s", (qiymat, komp_id))
    conn.commit(); cur.close(); conn.close()

def kompaniya_tahrirlash(komp_id, maydon, qiymat):
    conn = connect(); cur = conn.cursor()
    cur.execute(f"UPDATE kompaniyalar SET {maydon}=%s WHERE id=%s", (qiymat, komp_id))
    conn.commit(); cur.close(); conn.close()

def admin_telefon_orqali_kompaniya(telefon):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id,nomi,holat,admin_kod FROM kompaniyalar WHERE admin_telefon LIKE %s", (f"%{telefon[-9:]}%",))
    r = cur.fetchone(); cur.close(); conn.close(); return r

def admin_id_saqlash(komp_id, admin_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("UPDATE kompaniyalar SET admin_id=%s WHERE id=%s", (admin_id, komp_id))
    conn.commit(); cur.close(); conn.close()

def get_gps(komp_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT gps_lat,gps_lon,gps_radius FROM kompaniyalar WHERE id=%s", (komp_id,))
    r = cur.fetchone(); cur.close(); conn.close()
    return r if r else (41.299496, 69.240073, 200)

def get_wifi(komp_id):
    """WiFi sozlamalarini olish (SSID va MAC)"""
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT wifi_aktiv,wifi_ssid,wifi_mac FROM kompaniyalar WHERE id=%s", (komp_id,))
    r = cur.fetchone(); cur.close(); conn.close()
    return r if r else (False, "", "")

def get_wifi_mac(komp_id):
    """WiFi MAC manzilini olish"""
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT wifi_aktiv,wifi_mac FROM kompaniyalar WHERE id=%s", (komp_id,))
    r = cur.fetchone(); cur.close(); conn.close()
    return r if r else (False, "")

def wifi_sozla(komp_id, aktiv, ssid, mac=""):
    """WiFi sozlamalarini o'rnatish (SSID va MAC)"""
    conn = connect(); cur = conn.cursor()
    cur.execute("UPDATE kompaniyalar SET wifi_aktiv=%s,wifi_ssid=%s,wifi_mac=%s WHERE id=%s",
                (aktiv, ssid, mac, komp_id))
    conn.commit(); cur.close(); conn.close()

def wifi_mac_qosh(komp_id, mac_address, nomi=""):
    """WiFi MAC manzilini qo'shish"""
    conn = connect(); cur = conn.cursor()
    cur.execute("INSERT INTO wifi_macs(kompaniya_id, mac_address, nomi) VALUES(%s, %s, %s)",
                (komp_id, mac_address.upper(), nomi))
    conn.commit(); cur.close(); conn.close()

def wifi_mac_olish(komp_id):
    """Kompaniyaning barcha WiFi MAC manzillarini olish"""
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id, mac_address, nomi FROM wifi_macs WHERE kompaniya_id=%s ORDER BY id", (komp_id,))
    r = cur.fetchall(); cur.close(); conn.close()
    return r if r else []

def wifi_mac_tekshir(komp_id, mac_address):
    """MAC manzil kompaniya ro'yxatida bor-yo'qligini tekshirish"""
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id FROM wifi_macs WHERE kompaniya_id=%s AND UPPER(mac_address)=%s",
                (komp_id, mac_address.upper()))
    r = cur.fetchone(); cur.close(); conn.close()
    return r is not None

def wifi_mac_ochir(mac_id):
    """WiFi MAC manzilini o'chirish"""
    conn = connect(); cur = conn.cursor()
    cur.execute("DELETE FROM wifi_macs WHERE id=%s", (mac_id,))
    conn.commit(); cur.close(); conn.close()

def wifi_mac_tahrir(mac_id, nomi):
    """WiFi MAC nomini tahrirlash"""
    conn = connect(); cur = conn.cursor()
    cur.execute("UPDATE wifi_macs SET nomi=%s WHERE id=%s", (nomi, mac_id))
    conn.commit(); cur.close(); conn.close()

def komp_bugun_rasmlar(komp_id):
    """Kompaniya xodimlarining bugungi barcha rasmlari - to'liq ma'lumot bilan"""
    conn = connect(); cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute('''SELECT x.id, x.ism, x.lavozim, d.keldi, d.keldi_rasm, a.tafsilot
                   FROM davomat d
                   JOIN xodimlar x ON d.xodim_id=x.id
                   LEFT JOIN audit_log a ON a.xodim_id=x.id AND a.amal='KELDI' AND DATE(a.vaqt)=%s
                   WHERE d.sana=%s AND x.komp_id=%s AND d.keldi_rasm IS NOT NULL
                   ORDER BY d.keldi DESC''', (sana, sana, komp_id))
    r = cur.fetchall(); cur.close(); conn.close(); return r

def komp_bugun_videolar(komp_id):
    """Kompaniya xodimlarining bugungi barcha videolari - to'liq ma'lumot bilan"""
    conn = connect(); cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute('''SELECT x.id, x.ism, x.lavozim, d.ketdi, d.ketdi_rasm, a.tafsilot
                   FROM davomat d
                   JOIN xodimlar x ON d.xodim_id=x.id
                   LEFT JOIN audit_log a ON a.xodim_id=x.id AND a.amal='KETDI' AND DATE(a.vaqt)=%s
                   WHERE d.sana=%s AND x.komp_id=%s AND d.ketdi_rasm IS NOT NULL
                   ORDER BY d.ketdi DESC''', (sana, sana, komp_id))
    r = cur.fetchall(); cur.close(); conn.close(); return r

def barcha_komp_bugun_rasmlar():
    """Barcha kompaniyalarning bugungi rasmlari - super admin uchun - to'liq ma'lumot"""
    conn = connect(); cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute('''SELECT k.nomi, x.ism, x.lavozim, d.keldi, d.keldi_rasm, a.tafsilot
                   FROM davomat d
                   JOIN xodimlar x ON d.xodim_id=x.id
                   JOIN kompaniyalar k ON x.komp_id=k.id
                   LEFT JOIN audit_log a ON a.xodim_id=x.id AND a.amal='KELDI' AND DATE(a.vaqt)=%s
                   WHERE d.sana=%s AND d.keldi_rasm IS NOT NULL
                   ORDER BY d.keldi DESC''', (sana, sana))
    r = cur.fetchall(); cur.close(); conn.close(); return r

# ========== XODIMLAR ==========

def xodim_qoshish(ism, telefon, lavozim, oylik, ish_bosh, ish_tug, komp_id, rol, kod):
    conn = connect(); cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute('''INSERT INTO xodimlar(ism,telefon,lavozim,oylik,ish_boshlanish,
                  ish_tugash,kompaniya_id,rol,kod,ishga_kirgan)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id''',
                (ism,telefon,lavozim,oylik,ish_bosh,ish_tug,komp_id,rol,kod,sana))
    xid = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close(); return xid

def xodim_ochirish(xodim_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("DELETE FROM live_lokatsiyalar WHERE xodim_id=%s", (xodim_id,))
    cur.execute("DELETE FROM sababli_sorovlar WHERE xodim_id=%s", (xodim_id,))
    cur.execute("DELETE FROM davomat WHERE xodim_id=%s", (xodim_id,))
    cur.execute("DELETE FROM xodimlar WHERE id=%s", (xodim_id,))
    conn.commit(); cur.close(); conn.close()

def kompaniya_xodimlari(komp_id):
    conn = connect(); cur = conn.cursor()
    cur.execute('''SELECT id,ism,lavozim,telefon,oylik,ish_boshlanish,
                  ish_tugash,rol,kod,holat FROM xodimlar
                  WHERE kompaniya_id=%s ORDER BY id''', (komp_id,))
    r = cur.fetchall(); cur.close(); conn.close(); return r

def xodim_olish(xodim_id):
    conn = connect(); cur = conn.cursor()
    cur.execute('''SELECT id,ism,telefon,lavozim,oylik,ish_boshlanish,
                  ish_tugash,rol,kod,kompaniya_id,holat,tugilgan_kun
                  FROM xodimlar WHERE id=%s''', (xodim_id,))
    r = cur.fetchone(); cur.close(); conn.close(); return r

def xodim_tahrirlash(xodim_id, maydon, qiymat):
    conn = connect(); cur = conn.cursor()
    cur.execute(f"UPDATE xodimlar SET {maydon}=%s WHERE id=%s", (qiymat, xodim_id))
    conn.commit(); cur.close(); conn.close()

def telegram_id_orqali_xodim(telegram_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id,ism,rol,kompaniya_id FROM xodimlar WHERE telegram_id=%s", (telegram_id,))
    r = cur.fetchone(); cur.close(); conn.close(); return r

def telefon_orqali_xodim(telefon):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id,ism,rol,kompaniya_id FROM xodimlar WHERE telefon LIKE %s", (f"%{telefon[-9:]}%",))
    r = cur.fetchone(); cur.close(); conn.close(); return r

def xodim_telegram_saqlash(xodim_id, telegram_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("UPDATE xodimlar SET telegram_id=%s WHERE id=%s", (telegram_id, xodim_id))
    conn.commit(); cur.close(); conn.close()

def hr_idlari(komp_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT telegram_id FROM xodimlar WHERE kompaniya_id=%s AND rol='hr' AND telegram_id IS NOT NULL", (komp_id,))
    r = cur.fetchall(); cur.close(); conn.close(); return [x[0] for x in r]

def barcha_xodimlar_eslatma():
    conn = connect(); cur = conn.cursor()
    cur.execute('''SELECT x.id,x.telegram_id,x.ism,x.ish_boshlanish,x.tugilgan_kun,k.id
                  FROM xodimlar x JOIN kompaniyalar k ON x.kompaniya_id=k.id
                  WHERE x.telegram_id IS NOT NULL AND x.holat='faol' AND k.holat='faol' ''')
    r = cur.fetchall(); cur.close(); conn.close(); return r

# ========== DAVOMAT ==========

def keldi_belgilash(xodim_id, komp_id, kiritdi="xodim", kiritdi_id=None):
    conn = connect(); cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    vaqt = hozir().strftime("%H:%M")
    cur.execute("SELECT id FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, sana))
    if cur.fetchone(): cur.close(); conn.close(); return "already"
    cur.execute("SELECT ish_boshlanish FROM xodimlar WHERE id=%s", (xodim_id,))
    x = cur.fetchone(); kechikish = 0
    if x:
        try:
            b = datetime.strptime(x[0], "%H:%M"); k = datetime.strptime(vaqt, "%H:%M")
            if k > b: kechikish = int((k - b).total_seconds() / 60)
        except: pass
    cur.execute('''INSERT INTO davomat(xodim_id,kompaniya_id,sana,keldi,kechikish,kiritdi,kiritdi_id)
                  VALUES(%s,%s,%s,%s,%s,%s,%s)''', (xodim_id,komp_id,sana,vaqt,kechikish,kiritdi,kiritdi_id))
    conn.commit(); cur.close(); conn.close()
    return f"keldi|{vaqt}|{kechikish}"

def keldi_rasm_saqlash(xodim_id, rasm_id):
    conn = connect(); cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute("UPDATE davomat SET keldi_rasm=%s WHERE xodim_id=%s AND sana=%s", (rasm_id,xodim_id,sana))
    conn.commit(); cur.close(); conn.close()

def ketdi_belgilash(xodim_id, komp_id, kiritdi="xodim", kiritdi_id=None):
    conn = connect(); cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    vaqt = hozir().strftime("%H:%M")
    cur.execute("SELECT keldi FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, sana))
    row = cur.fetchone()
    if not row or not row[0]: cur.close(); conn.close(); return "nokeldi"
    try:
        k = datetime.strptime(row[0], "%H:%M"); kv = datetime.strptime(vaqt, "%H:%M")
        ish_soat = round((kv - k).total_seconds() / 3600, 2)
    except: ish_soat = 0
    cur.execute('''UPDATE davomat SET ketdi=%s,ish_soat=%s,kiritdi=%s,kiritdi_id=%s
                  WHERE xodim_id=%s AND sana=%s''', (vaqt,ish_soat,kiritdi,kiritdi_id,xodim_id,sana))
    conn.commit()
    cur.execute("SELECT ish_tugash FROM xodimlar WHERE id=%s", (xodim_id,))
    x = cur.fetchone(); cur.close(); conn.close()
    ish_tugash = x[0] if x else "18:00"
    return f"ketdi|{vaqt}|{ish_soat}|{ish_tugash}"

def ketdi_rasm_saqlash(xodim_id, rasm_id):
    conn = connect(); cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    cur.execute("UPDATE davomat SET ketdi_rasm=%s WHERE xodim_id=%s AND sana=%s", (rasm_id,xodim_id,sana))
    conn.commit(); cur.close(); conn.close()

def davomat_tahrirlash(davomat_id, maydon, qiymat):
    conn = connect(); cur = conn.cursor()
    cur.execute(f"UPDATE davomat SET {maydon}=%s WHERE id=%s", (qiymat, davomat_id))
    conn.commit(); cur.close(); conn.close()

def xodim_davomati(xodim_id, oy=None):
    conn = connect(); cur = conn.cursor()
    if oy:
        cur.execute('''SELECT id,sana,keldi,ketdi,ish_soat,kechikish,holat,izoh,kiritdi
                      FROM davomat WHERE xodim_id=%s AND sana LIKE %s ORDER BY sana''',
                    (xodim_id, f"%{oy}%"))
    else:
        cur.execute('''SELECT id,sana,keldi,ketdi,ish_soat,kechikish,holat,izoh,kiritdi
                      FROM davomat WHERE xodim_id=%s ORDER BY sana DESC''', (xodim_id,))
    r = cur.fetchall(); cur.close(); conn.close(); return r

def kompaniya_davomati(komp_id, sana=None):
    conn = connect(); cur = conn.cursor()
    if sana:
        cur.execute('''SELECT x.ism,d.sana,d.keldi,d.ketdi,d.ish_soat,d.kechikish,d.holat,d.id
                      FROM davomat d JOIN xodimlar x ON d.xodim_id=x.id
                      WHERE d.kompaniya_id=%s AND d.sana=%s ORDER BY x.ism''', (komp_id, sana))
    else:
        cur.execute('''SELECT x.ism,d.sana,d.keldi,d.ketdi,d.ish_soat,d.kechikish,d.holat,d.id
                      FROM davomat d JOIN xodimlar x ON d.xodim_id=x.id
                      WHERE d.kompaniya_id=%s ORDER BY d.sana DESC,x.ism''', (komp_id,))
    r = cur.fetchall(); cur.close(); conn.close(); return r

def manual_davomat(xodim_id, komp_id, sana, keldi_v, ketdi_v, holat, izoh, kiritdi_ism, kiritdi_id):
    conn = connect(); cur = conn.cursor()
    ish_soat = 0; kechikish = 0
    try:
        k = datetime.strptime(keldi_v, "%H:%M"); kt = datetime.strptime(ketdi_v, "%H:%M")
        ish_soat = round((kt - k).total_seconds() / 3600, 2)
        cur.execute("SELECT ish_boshlanish FROM xodimlar WHERE id=%s", (xodim_id,))
        x = cur.fetchone()
        if x:
            b = datetime.strptime(x[0], "%H:%M")
            if k > b: kechikish = int((k - b).total_seconds() / 60)
    except: pass
    cur.execute("SELECT id FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, sana))
    if cur.fetchone():
        cur.execute('''UPDATE davomat SET keldi=%s,ketdi=%s,ish_soat=%s,kechikish=%s,
                      holat=%s,izoh=%s,kiritdi=%s,kiritdi_id=%s WHERE xodim_id=%s AND sana=%s''',
                    (keldi_v,ketdi_v,ish_soat,kechikish,holat,izoh,kiritdi_ism,kiritdi_id,xodim_id,sana))
    else:
        cur.execute('''INSERT INTO davomat(xodim_id,kompaniya_id,sana,keldi,ketdi,ish_soat,
                      kechikish,holat,izoh,kiritdi,kiritdi_id)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (xodim_id,komp_id,sana,keldi_v,ketdi_v,ish_soat,kechikish,holat,izoh,kiritdi_ism,kiritdi_id))
    conn.commit(); cur.close(); conn.close()
    return "✅ Davomat kiritildi!"

# ========== SABABLI SO'ROVLAR ==========

def sababli_sorov_saqlash(xodim_id, komp_id, sana, sabab):
    conn = connect(); cur = conn.cursor()
    cur.execute("INSERT INTO sababli_sorovlar(xodim_id,kompaniya_id,sana,sabab) VALUES(%s,%s,%s,%s) RETURNING id",
                (xodim_id,komp_id,sana,sabab))
    sid = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close(); return sid

def sababli_sorov_yangilash(sorov_id, holat, xodim_id, sana, sabab):
    conn = connect(); cur = conn.cursor()
    cur.execute("UPDATE sababli_sorovlar SET holat=%s WHERE id=%s", (holat, sorov_id))
    if holat == 'tasdiqlandi':
        cur.execute("SELECT id FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, sana))
        if cur.fetchone():
            cur.execute("UPDATE davomat SET holat='sababli',izoh=%s WHERE xodim_id=%s AND sana=%s",
                       (sabab,xodim_id,sana))
        else:
            cur.execute("INSERT INTO davomat(xodim_id,sana,holat,izoh) VALUES(%s,%s,'sababli',%s)",
                       (xodim_id,sana,sabab))
    conn.commit(); cur.close(); conn.close()

# ========== LIVE LOKATSIYA ==========

def live_lokatsiya_saqlash(xodim_id, komp_id, lat, lon):
    conn = connect(); cur = conn.cursor()
    vaqt = hozir().strftime("%H:%M:%S")
    cur.execute("SELECT id FROM live_lokatsiyalar WHERE xodim_id=%s AND faol=TRUE", (xodim_id,))
    if cur.fetchone():
        cur.execute("UPDATE live_lokatsiyalar SET lat=%s,lon=%s,vaqt=%s WHERE xodim_id=%s AND faol=TRUE",
                    (lat,lon,vaqt,xodim_id))
    else:
        cur.execute("INSERT INTO live_lokatsiyalar(xodim_id,kompaniya_id,lat,lon,vaqt,faol) VALUES(%s,%s,%s,%s,%s,TRUE)",
                    (xodim_id,komp_id,lat,lon,vaqt))
    conn.commit(); cur.close(); conn.close()

def live_lokatsiya_olish(xodim_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT lat,lon,vaqt FROM live_lokatsiyalar WHERE xodim_id=%s AND faol=TRUE", (xodim_id,))
    r = cur.fetchone(); cur.close(); conn.close(); return r

def live_lokatsiya_ochirish(xodim_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("UPDATE live_lokatsiyalar SET faol=FALSE WHERE xodim_id=%s", (xodim_id,))
    conn.commit(); cur.close(); conn.close()

def barcha_live_xodimlar():
    conn = connect(); cur = conn.cursor()
    bugun = hozir().strftime("%Y-%m-%d")
    cur.execute('''SELECT ll.xodim_id,ll.kompaniya_id,ll.lat,ll.lon,x.ism,x.telegram_id,
                  k.gps_lat,k.gps_lon,k.gps_radius,k.admin_id,k.nomi
                  FROM live_lokatsiyalar ll
                  JOIN xodimlar x ON ll.xodim_id=x.id
                  JOIN kompaniyalar k ON ll.kompaniya_id=k.id
                  WHERE ll.faol=TRUE AND k.live_gps_tekshiruv=TRUE AND k.holat='faol'
                  AND EXISTS(SELECT 1 FROM davomat d WHERE d.xodim_id=ll.xodim_id
                             AND d.sana=%s AND d.keldi IS NOT NULL AND d.ketdi IS NULL)''', (bugun,))
    r = cur.fetchall(); cur.close(); conn.close(); return r

# ========== STATISTIKA ==========

def xodim_oy_statistika(xodim_id, oy=None):
    conn = connect(); cur = conn.cursor()
    if not oy: oy = hozir().strftime("%Y-%m")
    cur.execute('''SELECT COUNT(*),COALESCE(SUM(ish_soat),0),
                  COUNT(CASE WHEN kechikish>0 THEN 1 END),
                  COALESCE(SUM(kechikish),0),
                  COUNT(CASE WHEN holat='sababli' THEN 1 END),
                  COUNT(CASE WHEN keldi IS NULL THEN 1 END)
                  FROM davomat WHERE xodim_id=%s AND sana LIKE %s''',
                (xodim_id, f"{oy}%"))
    r = cur.fetchone(); cur.close(); conn.close(); return r

def kompaniya_reyting(komp_id, oy=None):
    conn = connect(); cur = conn.cursor()
    if not oy: oy = hozir().strftime("%Y-%m")
    cur.execute('''SELECT x.ism,x.lavozim,COUNT(d.id),
                  COALESCE(SUM(d.ish_soat),0),COALESCE(SUM(d.kechikish),0),
                  COUNT(CASE WHEN d.kechikish>0 THEN 1 END)
                  FROM xodimlar x LEFT JOIN davomat d ON x.id=d.xodim_id AND d.sana LIKE %s
                  WHERE x.kompaniya_id=%s AND x.holat='faol'
                  GROUP BY x.id,x.ism,x.lavozim ORDER BY 5 ASC,3 DESC''',
                (f"{oy}%", komp_id))
    r = cur.fetchall(); cur.close(); conn.close(); return r

def haftalik_davomat_kompaniyalar():
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id,nomi,admin_id FROM kompaniyalar WHERE holat='faol' AND admin_id IS NOT NULL")
    r = cur.fetchall(); cur.close(); conn.close(); return r

def kompaniya_haftalik_stat(komp_id):
    conn = connect(); cur = conn.cursor()
    bugun = hozir().date()
    dushanba = bugun - timedelta(days=bugun.weekday())
    juma = dushanba + timedelta(days=4)
    cur.execute('''SELECT COUNT(DISTINCT xodim_id),COUNT(DISTINCT sana),
                  COALESCE(SUM(ish_soat),0),COALESCE(AVG(CASE WHEN kechikish>0 THEN kechikish END),0)
                  FROM davomat WHERE kompaniya_id=%s AND sana>=%s AND sana<=%s''',
                (komp_id, str(dushanba), str(juma)))
    r = cur.fetchone(); cur.close(); conn.close(); return r

# ========== HISOBOTLAR ==========

def super_admin_hisobot():
    conn = connect(); cur = conn.cursor()
    wb = openpyxl.Workbook()

    ws1 = wb.active; ws1.title = "Kompaniyalar"
    ws1.append(["#","Kompaniya","Admin telefon","Holat","Xodimlar","Yaratilgan"])
    cur.execute("SELECT id,nomi,admin_telefon,holat,yaratilgan FROM kompaniyalar ORDER BY id")
    kompaniyalar = cur.fetchall()
    for i,k in enumerate(kompaniyalar,1):
        cur.execute("SELECT COUNT(*) FROM xodimlar WHERE kompaniya_id=%s", (k[0],))
        ws1.append([i,k[1],k[2],k[3],cur.fetchone()[0],k[4]])

    ws2 = wb.create_sheet("Xodimlar")
    ws2.append(["#","Kompaniya","Ism","Lavozim","Telefon","Oylik","Ish vaqti","Rol","Holat"])
    cur.execute('''SELECT k.nomi,x.ism,x.lavozim,x.telefon,x.oylik,x.ish_boshlanish,x.ish_tugash,x.rol,x.holat
                  FROM xodimlar x JOIN kompaniyalar k ON x.kompaniya_id=k.id ORDER BY k.id,x.id''')
    for i,x in enumerate(cur.fetchall(),1):
        ws2.append([i,x[0],x[1],x[2],x[3],x[4],f"{x[5]}-{x[6]}",x[7],x[8]])

    ws3 = wb.create_sheet("Davomat")
    ws3.append(["#","Kompaniya","Xodim","Sana","Keldi","Ketdi","Ish vaqti","Kechikish","Holat"])
    cur.execute('''SELECT k.nomi,x.ism,d.sana,d.keldi,d.ketdi,d.ish_soat,d.kechikish,d.holat
                  FROM davomat d JOIN xodimlar x ON d.xodim_id=x.id
                  JOIN kompaniyalar k ON d.kompaniya_id=k.id ORDER BY k.id,d.sana''')
    for i,d in enumerate(cur.fetchall(),1):
        ws3.append([i,d[0],d[1],d[2],d[3],d[4],soat_format(d[5]),kechikish_format(d[6]),d[7]])

    ws4 = wb.create_sheet("Statistika")
    ws4.append(["Kompaniya","Jami xodim","Bugun kelgan","O'rt kechikish","Holat"])
    bugun = hozir().strftime("%Y-%m-%d")
    for k in kompaniyalar:
        cur.execute("SELECT COUNT(*) FROM xodimlar WHERE kompaniya_id=%s", (k[0],))
        jami = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM davomat WHERE kompaniya_id=%s AND sana=%s", (k[0],bugun))
        bk = cur.fetchone()[0]
        cur.execute("SELECT AVG(kechikish) FROM davomat WHERE kompaniya_id=%s", (k[0],))
        ort = cur.fetchone()[0] or 0
        ws4.append([k[1],jami,bk,round(ort,1),k[3]])

    cur.close(); conn.close()
    wb.save("super_hisobot.xlsx")
    return "super_hisobot.xlsx"

def kompaniya_hisobot(komp_id):
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT nomi FROM kompaniyalar WHERE id=%s", (komp_id,))
    r = cur.fetchone()
    if not r: return None
    nomi = r[0]; wb = openpyxl.Workbook()

    ws1 = wb.active; ws1.title = "Xodimlar"
    ws1.append(["#","Ism","Lavozim","Telefon","Oylik","Ish vaqti","Rol","Holat"])
    cur.execute('''SELECT id,ism,lavozim,telefon,oylik,ish_boshlanish,ish_tugash,rol,holat
                  FROM xodimlar WHERE kompaniya_id=%s ORDER BY id''', (komp_id,))
    xodimlar = cur.fetchall()
    for i,x in enumerate(xodimlar,1):
        ws1.append([i,x[1],x[2],x[3],x[4],f"{x[5]}-{x[6]}",x[7],x[8]])

    ws2 = wb.create_sheet("Davomat")
    ws2.append(["#","Xodim","Sana","Keldi","Ketdi","Ish vaqti","Kechikish","Holat","Izoh"])
    cur.execute('''SELECT x.ism,d.sana,d.keldi,d.ketdi,d.ish_soat,d.kechikish,d.holat,d.izoh
                  FROM davomat d JOIN xodimlar x ON d.xodim_id=x.id
                  WHERE d.kompaniya_id=%s ORDER BY d.sana DESC,x.ism''', (komp_id,))
    for i,d in enumerate(cur.fetchall(),1):
        ws2.append([i,d[0],d[1],d[2],d[3],soat_format(d[4]),kechikish_format(d[5]),d[6],d[7] or "—"])

    ws3 = wb.create_sheet("Statistika")
    ws3.append(["Xodim","Lavozim","Jami kun","Jami ish soat","O'rt kechikish","Kech kelgan"])
    for x in xodimlar:
        cur.execute('''SELECT COUNT(*),SUM(ish_soat),AVG(kechikish),COUNT(CASE WHEN kechikish>0 THEN 1 END)
                      FROM davomat WHERE xodim_id=%s''', (x[0],))
        s = cur.fetchone()
        ws3.append([x[1],x[2],s[0] or 0,soat_format(s[1] or 0),kechikish_format(s[2] or 0),s[3] or 0])

    cur.close(); conn.close()
    fayl = f"hisobot_{nomi}.xlsx"
    wb.save(fayl); return fayl

# ========== AUDIT LOG ==========

def audit_log_qoshish(komp_id, amal, tafsilot, xodim_id=None, rasm_id=None, video_id=None, user_id=None, user_ism=None):
    """Audit log'ga amal qo'shish"""
    conn = connect(); cur = conn.cursor()
    vaqt = hozir().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute('''INSERT INTO audit_log(kompaniya_id,xodim_id,amal,tafsilot,vaqt,rasm_id,video_id,user_id,user_ism)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (komp_id, xodim_id, amal, tafsilot, vaqt, rasm_id, video_id, user_id, user_ism))
    conn.commit(); cur.close(); conn.close()

def audit_log_olish(komp_id, limit=50, offset=0):
    """Kompaniya'ning audit log'larini olish"""
    conn = connect(); cur = conn.cursor()
    cur.execute('''SELECT id,xodim_id,amal,tafsilot,vaqt,rasm_id,video_id,user_ism
                  FROM audit_log WHERE kompaniya_id=%s
                  ORDER BY vaqt DESC LIMIT %s OFFSET %s''',
                (komp_id, limit, offset))
    r = cur.fetchall(); cur.close(); conn.close(); return r

def super_admin_audit_log(limit=100, offset=0):
    """Super admin - barcha kompaniya audit log'lari"""
    conn = connect(); cur = conn.cursor()
    cur.execute('''SELECT k.nomi,al.amal,al.tafsilot,al.vaqt,al.user_ism,al.xodim_id,x.ism
                  FROM audit_log al
                  JOIN kompaniyalar k ON al.kompaniya_id=k.id
                  LEFT JOIN xodimlar x ON al.xodim_id=x.id
                  ORDER BY al.vaqt DESC LIMIT %s OFFSET %s''',
                (limit, offset))
    r = cur.fetchall(); cur.close(); conn.close(); return r

def export_audit_log_excel(komp_id=None):
    """Audit log'ni Excel'ga export qilish"""
    conn = connect(); cur = conn.cursor()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Audit Log"
    ws.append(["#", "Kompaniya", "Amal", "Xodim", "Vaqt", "User", "Tafsilot"])

    if komp_id:
        cur.execute('''SELECT al.amal,k.nomi,x.ism,al.vaqt,al.user_ism,al.tafsilot
                      FROM audit_log al
                      JOIN kompaniyalar k ON al.kompaniya_id=k.id
                      LEFT JOIN xodimlar x ON al.xodim_id=x.id
                      WHERE al.kompaniya_id=%s ORDER BY al.vaqt DESC''', (komp_id,))
    else:
        cur.execute('''SELECT al.amal,k.nomi,x.ism,al.vaqt,al.user_ism,al.tafsilot
                      FROM audit_log al
                      JOIN kompaniyalar k ON al.kompaniya_id=k.id
                      LEFT JOIN xodimlar x ON al.xodim_id=x.id
                      ORDER BY al.vaqt DESC''')

    for i, row in enumerate(cur.fetchall(), 1):
        amal, komp_nomi, xodim_ism, vaqt, user_ism, tafsilot = row
        ws.append([i, komp_nomi, amal, xodim_ism or '—', vaqt, user_ism, tafsilot[:50]])

    cur.close(); conn.close()
    fayl = f"audit_log_{komp_id or 'all'}.xlsx"
    wb.save(fayl); return fayl

# ========== MOTIVATSIYA TIZIMI ==========

def xodim_streak_olish(xodim_id):
    """Xodimning davomiylik streakini olish"""
    conn = connect(); cur = conn.cursor()
    bugun = hozir().date()
    streak = 0

    for i in range(30):
        check_date = (bugun - timedelta(days=i)).strftime("%Y-%m-%d")
        cur.execute("SELECT id FROM davomat WHERE xodim_id=%s AND sana=%s AND keldi IS NOT NULL", (xodim_id, check_date))
        if cur.fetchone(): streak += 1
        else: break

    cur.close(); conn.close(); return streak

def haftalik_reyting_xodimlar(komp_id):
    """Kompaniyaning haftalik top 5 xodimi"""
    conn = connect(); cur = conn.cursor()
    bugun = hozir().date()
    dushanba = bugun - timedelta(days=bugun.weekday())
    juma = dushanba + timedelta(days=4)

    cur.execute('''SELECT x.id,x.ism,x.lavozim,
                  COUNT(DISTINCT d.sana) as kun,
                  COALESCE(SUM(d.ish_soat),0) as soat,
                  COUNT(CASE WHEN d.kechikish>0 THEN 1 END) as kechikkan,
                  COALESCE(AVG(d.kechikish),0) as ort_kechikish
                  FROM xodimlar x
                  LEFT JOIN davomat d ON x.id=d.xodim_id
                  WHERE x.kompaniya_id=%s AND x.holat='faol'
                  AND (d.sana IS NULL OR (d.sana>=%s AND d.sana<=%s AND d.holat NOT IN ('kasal','ta\'til')))
                  GROUP BY x.id,x.ism,x.lavozim
                  ORDER BY ort_kechikish ASC, kun DESC, soat DESC
                  LIMIT 5''', (komp_id, str(dushanba), str(juma)))
    r = cur.fetchall(); cur.close(); conn.close(); return r

def xodim_bugun_statistika(xodim_id):
    """Bugungi xodim statistikasi"""
    conn = connect(); cur = conn.cursor()
    bugun = hozir().strftime("%Y-%m-%d")
    cur.execute('''SELECT keldi,ketdi,ish_soat,kechikish,holat
                  FROM davomat WHERE xodim_id=%s AND sana=%s''', (xodim_id, bugun))
    r = cur.fetchone(); cur.close(); conn.close(); return r

def generate_keldi_motivation(xodim, kechikish, streak):
    """Keldi uchun motivatsiya matni"""
    ism = xodim[1] if xodim else 'Xodim'
    if kechikish == 0:
        msg = f"🎉 *{ism}! Vaqtida keldingiz!*\n"
        if streak >= 5: msg += f"🔥 {streak} kunlik streak! Zo'r!"
        elif streak >= 3: msg += f"💪 {streak} kunlik davomiylik! Yaxshi!"
        return msg
    elif kechikish <= 15:
        return f"⚠️ *{ism}!* Bugun {kechikish} daqiqaga kechiktingiz.\nKeying safar vaqtida keling!"
    else:
        kech_fmt = kechikish_format(kechikish)
        return f"🚨 *DIQQAT!* {ism}, siz {kech_fmt}ga kechiktingiz!\nBu intizom buzilishi!"

def generate_ketdi_motivation(xodim, ish_tugash, ketdi_vaqt, ish_soat, streak):
    """Ketdi uchun motivatsiya matni"""
    ism = xodim[1] if xodim else 'Xodim'
    try:
        tug = datetime.strptime(ish_tugash, "%H:%M")
        ket = datetime.strptime(ketdi_vaqt, "%H:%M")
        farq = int((ket - tug).total_seconds() / 60)
    except:
        farq = 0

    s = int(ish_soat); d = int((ish_soat - s) * 60)
    farq_fmt = kechikish_format(abs(farq))

    if farq >= 30:
        return (f"🌙 *QOLIB ISHLASH!* (+{farq_fmt} ortiqcha)\n"
                f"🏆 Rahmat, {ism}! Bugun {s} soat {d} daqiqa ishlading.\n"
                f"Qo'shimcha mehnat ko'rishingiz qadrlanadi! 💪\n"
                f"{'🔥 ' + str(streak) + ' kunlik streak!' if streak >= 3 else ''}")
    elif farq >= -15:
        return (f"✅ *TO'LIQ ISH KUNI!*\n"
                f"Yaxshi ish, {ism}!\n⏱ {s} soat {d} daqiqa samarali mehnat. 💼\n"
                f"{'🔥 Streakingiz: ' + str(streak) + ' kun!' if streak >= 3 else ''}")
    elif farq >= -30:
        return (f"⚠️ *ERTA KETISH* ({farq_fmt} oldin)\n"
                f"{ism}, ish vaqti tugamay ketdingiz.\n"
                f"Sababini HR ga bildiring! 📋")
    else:
        return (f"❌ *JIDDIY ERTA KETISH!* ({farq_fmt} oldin)\n"
                f"Bu intizom buzilishi! HR va admin xabardor qilindi! 🚫")
