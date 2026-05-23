import sqlite3
from datetime import datetime
import openpyxl

ADMIN_TELEFON = "919712222"

def connect():
    return sqlite3.connect("gigandtime.db")

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

    cur.execute('''CREATE TABLE IF NOT EXISTS kompaniyalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nomi TEXT NOT NULL,
        admin_telefon TEXT DEFAULT "919712222",
        admin_id INTEGER,
        gps_lat REAL DEFAULT 37.667088,
        gps_lon REAL DEFAULT 67.02551,
        gps_radius INTEGER DEFAULT 200
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS xodimlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ism TEXT NOT NULL,
        telefon TEXT,
        kod TEXT,
        lavozim TEXT,
        oylik REAL DEFAULT 0,
        ish_boshlanish TEXT DEFAULT "09:00",
        ish_tugash TEXT DEFAULT "18:00",
        ishga_kirgan TEXT,
        telegram_id INTEGER UNIQUE,
        kompaniya_id INTEGER,
        rol TEXT DEFAULT "xodim"
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS davomat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        xodim_id INTEGER,
        sana TEXT,
        keldi TEXT,
        ketdi TEXT,
        ish_soat REAL DEFAULT 0,
        kechikish INTEGER DEFAULT 0,
        holat TEXT DEFAULT "normal",
        izoh TEXT,
        keldi_rasm TEXT,
        ketdi_rasm TEXT,
        kiritdi TEXT DEFAULT "xodim",
        kiritdi_id INTEGER
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS sababli_sorovlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        xodim_id INTEGER,
        sana TEXT,
        sabab TEXT,
        holat TEXT DEFAULT "kutilmoqda"
    )''')

    conn.commit()
    conn.close()

def keldi_belgilash(xodim_id, kiritdi="xodim", kiritdi_id=None):
    conn = connect()
    cur = conn.cursor()
    sana = datetime.now().strftime("%Y-%m-%d")
    vaqt = datetime.now().strftime("%H:%M")
    cur.execute("SELECT id FROM davomat WHERE xodim_id=? AND sana=?", (xodim_id, sana))
    if cur.fetchone():
        conn.close()
        return "⚠️ Bugun allaqachon belgilangan!"
    cur.execute("SELECT ish_boshlanish FROM xodimlar WHERE id=?", (xodim_id,))
    xodim = cur.fetchone()
    kechikish = 0
    if xodim:
        try:
            belgi = datetime.strptime(xodim[0], "%H:%M")
            hozir = datetime.strptime(vaqt, "%H:%M")
            if hozir > belgi:
                kechikish = int((hozir - belgi).total_seconds() / 60)
        except:
            pass
    cur.execute('''INSERT INTO davomat
        (xodim_id, sana, keldi, kechikish, kiritdi, kiritdi_id)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (xodim_id, sana, vaqt, kechikish, kiritdi, kiritdi_id))
    conn.commit()
    conn.close()
    if kechikish > 0:
        return f"✅ Keldi vaqti: {vaqt}\n⚠️ Kechikish: {kechikish_format(kechikish)}"
    return f"✅ Keldi vaqti: {vaqt}"

def keldi_rasm_saqlash(xodim_id, rasm_id):
    conn = connect()
    cur = conn.cursor()
    sana = datetime.now().strftime("%Y-%m-%d")
    cur.execute("UPDATE davomat SET keldi_rasm=? WHERE xodim_id=? AND sana=?",
                (rasm_id, xodim_id, sana))
    conn.commit()
    conn.close()

def ketdi_belgilash(xodim_id, kiritdi="xodim", kiritdi_id=None):
    conn = connect()
    cur = conn.cursor()
    sana = datetime.now().strftime("%Y-%m-%d")
    vaqt = datetime.now().strftime("%H:%M")
    cur.execute("SELECT keldi FROM davomat WHERE xodim_id=? AND sana=?", (xodim_id, sana))
    row = cur.fetchone()
    if not row or not row[0]:
        conn.close()
        return "❌ Avval keldi belgilanmagan!"
    try:
        keldi = datetime.strptime(row[0], "%H:%M")
        ketdi = datetime.strptime(vaqt, "%H:%M")
        daqiqalar = int((ketdi - keldi).total_seconds() / 60)
        soat = daqiqalar // 60
        daqiqa = daqiqalar % 60
        ish_soat = round(daqiqalar / 60, 2)
        ish_matn = f"{soat} soat {daqiqa} daqiqa"
    except:
        ish_soat = 0
        ish_matn = "0 soat 0 daqiqa"
    cur.execute('''UPDATE davomat SET ketdi=?, ish_soat=?, kiritdi=?, kiritdi_id=?
                  WHERE xodim_id=? AND sana=?''',
                (vaqt, ish_soat, kiritdi, kiritdi_id, xodim_id, sana))
    conn.commit()
    conn.close()
    return f"🚪 Ketdi vaqti: {vaqt}\n⏱ Ish vaqti: {ish_matn}"

def ketdi_rasm_saqlash(xodim_id, rasm_id):
    conn = connect()
    cur = conn.cursor()
    sana = datetime.now().strftime("%Y-%m-%d")
    cur.execute("UPDATE davomat SET ketdi_rasm=? WHERE xodim_id=? AND sana=?",
                (rasm_id, xodim_id, sana))
    conn.commit()
    conn.close()

def manual_davomat(xodim_id, sana, keldi_vaqt, ketdi_vaqt,
                   holat, izoh, kiritdi_ism, kiritdi_id):
    conn = connect()
    cur = conn.cursor()
    ish_soat = 0
    kechikish = 0
    try:
        keldi = datetime.strptime(keldi_vaqt, "%H:%M")
        ketdi = datetime.strptime(ketdi_vaqt, "%H:%M")
        daqiqalar = int((ketdi - keldi).total_seconds() / 60)
        ish_soat = round(daqiqalar / 60, 2)
        cur.execute("SELECT ish_boshlanish FROM xodimlar WHERE id=?", (xodim_id,))
        xodim = cur.fetchone()
        if xodim:
            belgi = datetime.strptime(xodim[0], "%H:%M")
            if keldi > belgi:
                kechikish = int((keldi - belgi).total_seconds() / 60)
    except:
        pass
    cur.execute("SELECT id FROM davomat WHERE xodim_id=? AND sana=?", (xodim_id, sana))
    if cur.fetchone():
        cur.execute('''UPDATE davomat SET keldi=?, ketdi=?, ish_soat=?,
                      kechikish=?, holat=?, izoh=?, kiritdi=?, kiritdi_id=?
                      WHERE xodim_id=? AND sana=?''',
                    (keldi_vaqt, ketdi_vaqt, ish_soat, kechikish,
                     holat, izoh, kiritdi_ism, kiritdi_id, xodim_id, sana))
    else:
        cur.execute('''INSERT INTO davomat
                      (xodim_id, sana, keldi, ketdi, ish_soat,
                       kechikish, holat, izoh, kiritdi, kiritdi_id)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (xodim_id, sana, keldi_vaqt, ketdi_vaqt, ish_soat,
                     kechikish, holat, izoh, kiritdi_ism, kiritdi_id))
    conn.commit()
    conn.close()
    return "✅ Davomat kiritildi!"

def xodim_davomati(xodim_id, oy=None):
    conn = connect()
    cur = conn.cursor()
    if oy:
        cur.execute('''SELECT sana, keldi, ketdi, ish_soat, kechikish, holat, izoh, kiritdi
                      FROM davomat WHERE xodim_id=? AND sana LIKE ?''',
                    (xodim_id, f"%{oy}%"))
    else:
        cur.execute('''SELECT sana, keldi, ketdi, ish_soat, kechikish, holat, izoh, kiritdi
                      FROM davomat WHERE xodim_id=?''', (xodim_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def excel_hisobot(kompaniya_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute('''SELECT id, ism, lavozim, telefon, oylik,
                  ish_boshlanish, ish_tugash, rol
                  FROM xodimlar WHERE kompaniya_id=?''', (kompaniya_id,))
    xodimlar = cur.fetchall()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Davomat hisoboti"
    ws.append(["Ism", "Lavozim", "Telefon", "Oylik (so'm)",
               "Ish vaqti", "Rol", "Sana", "Keldi", "Ketdi",
               "Ish vaqti", "Kechikish", "Holat", "Izoh", "Kim kiritdi"])
    for x in xodimlar:
        cur.execute('''SELECT sana, keldi, ketdi, ish_soat, kechikish,
                      holat, izoh, kiritdi
                      FROM davomat WHERE xodim_id=? ORDER BY sana''', (x[0],))
        davomatlar = cur.fetchall()
        if davomatlar:
            for d in davomatlar:
                ws.append([
                    x[1], x[2], x[3], x[4],
                    f"{x[5]}-{x[6]}", x[7],
                    d[0], d[1], d[2],
                    soat_format(d[3]),
                    kechikish_format(d[4]),
                    d[5], d[6] or "—", d[7] or "xodim"
                ])
        else:
            ws.append([x[1], x[2], x[3], x[4],
                      f"{x[5]}-{x[6]}", x[7],
                      "—", "—", "—", "—", "—", "—", "—", "—"])
    conn.close()
    fayl = "hisobot.xlsx"
    wb.save(fayl)
    return fayl

create_tables()
print("Baza tayyor!")