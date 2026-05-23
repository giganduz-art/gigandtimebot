from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from database import (connect, create_tables, keldi_belgilash, ketdi_belgilash,
                      keldi_rasm_saqlash, ketdi_rasm_saqlash, xodim_davomati,
                      excel_hisobot, soat_format, kechikish_format, manual_davomat,
                      ADMIN_TELEFON)
from datetime import datetime
import os
import math

TOKEN = "8728106880:AAH0lQlLcgNI0czxmEbCJXIDE6vVmTS47fU"

(KOMPANIYA_NOMI, XODIM_ISM, XODIM_TELEFON, XODIM_LAVOZIM,
 XODIM_OYLIK, XODIM_ISH_BOSH, XODIM_ISH_TUG, XODIM_ROL,
 XODIM_KOD, TELEFON_TASDIQ, XODIM_KOD_TASDIQ) = range(11)

(KELDI_GPS, KELDI_RASM, KETDI_GPS, KETDI_RASM,
 TAHRIR_TANLASH, TAHRIR_QIYMAT,
 MANUAL_XODIM, MANUAL_SANA, MANUAL_KELDI,
 MANUAL_KETDI, MANUAL_HOLAT, MANUAL_IZOH,
 SABAB_SOROV, SOZLAMA_TANLASH, SOZLAMA_QIYMAT) = range(11, 26)

def masofa(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def get_gps():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT gps_lat, gps_lon, gps_radius FROM kompaniyalar WHERE id=1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return row[0], row[1], row[2]
    return 37.667088, 67.02551, 200

def get_hr_ids(kompaniya_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT telegram_id FROM xodimlar WHERE kompaniya_id=%s AND rol='hr' AND telegram_id IS NOT NULL", (kompaniya_id,))
    hrs = cur.fetchall()
    cur.close()
    conn.close()
    return [h[0] for h in hrs]

def get_admin_id():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT admin_id FROM kompaniyalar WHERE id=1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None

def motivatsiya_keldi(ism, kechikish):
    if kechikish == 0:
        return (f"✅ Xush kelibsiz, {ism}!\n"
                f"Bugun o'z vaqtida keldingiz.\n"
                f"Samarali ish kuni tilaymiz! 💼")
    elif kechikish <= 30:
        return (f"⚠️ {ism}, bugun {kechikish_format(kechikish)} kech keldingiz.\n"
                f"Iltimos, ish tartibiga rioya qiling! ⏰")
    else:
        return (f"❌ {ism}, bugun {kechikish_format(kechikish)} kechikdingiz!\n"
                f"Bu qabul qilib bo'lmaydigan holat.\n"
                f"Rahbariyat xabardor qilinadi! ⚠️")

def motivatsiya_ketdi(ism, ish_soat, kerak_soat):
    farq = kerak_soat - ish_soat
    soat = int(ish_soat)
    daqiqa = int((ish_soat - soat) * 60)
    if farq <= 0:
        return (f"✅ {ism}, bugun {soat} soat {daqiqa} daqiqa\n"
                f"mehnat qildingiz.\n"
                f"Xizmatingiz uchun rahmat! 👏")
    elif farq <= 1:
        return (f"⚠️ {ism}, ish vaqti tugamay ketdingiz.\n"
                f"Bugun {soat} soat {daqiqa} daqiqa ishlading.\n"
                f"Sababi haqida HR ga ma'lum qiling! 📋")
    else:
        return (f"❌ {ism}, bugun atigi {soat} soat {daqiqa} daqiqa ishlading.\n"
                f"Bu ish intizomiga ziddir.\n"
                f"Rahbariyat xabardor etiladi! ❌")

async def admin_menu(update):
    buttons = [
        ["👥 Xodimlar", "➕ Xodim qo'shish"],
        ["✏️ Xodim tahrirlash", "📝 Manual davomat"],
        ["📋 Sababli so'rovlar", "📊 Hisobot"],
        ["⚙️ Sozlamalar"]
    ]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text("👑 Admin panel:", reply_markup=markup)

async def xodim_menu(update, ism):
    buttons = [
        ["✅ Keldi", "🚪 Ketdi"],
        ["📋 Sababli so'rov", "📋 Mening davomatim"]
    ]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text(f"👷 Xush kelibsiz, {ism}!", reply_markup=markup)

async def hr_menu(update):
    buttons = [
        ["👥 Xodimlar ro'yxati", "➕ Xodim qo'shish"],
        ["📝 Manual davomat", "📋 Sababli so'rovlar"],
        ["📊 Hisobot", "🔙 Orqaga"]
    ]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text("👔 HR panel:", reply_markup=markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT admin_id FROM kompaniyalar WHERE id=1")
    admin = cur.fetchone()
    if admin and admin[0] == user_id:
        cur.close(); conn.close()
        await admin_menu(update)
        return ConversationHandler.END
    cur.execute("SELECT id, ism, rol FROM xodimlar WHERE telegram_id=%s", (user_id,))
    xodim = cur.fetchone()
    if xodim:
        cur.close(); conn.close()
        if xodim[2] == "hr":
            await hr_menu(update)
        else:
            await xodim_menu(update, xodim[1])
        return ConversationHandler.END
    cur.close(); conn.close()
    button = KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👋 Xush kelibsiz!\n\n📱 Telefon raqamingizni yuboring:", reply_markup=markup)
    return TELEFON_TASDIQ

async def telefon_tasdiq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        button = KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
        markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("❌ Iltimos telefon tugmasini bosing!", reply_markup=markup)
        return TELEFON_TASDIQ
    telefon = contact.phone_number.replace("+", "")
    user_id = update.effective_user.id
    if telefon.endswith(ADMIN_TELEFON):
        conn = connect(); cur = conn.cursor()
        cur.execute("SELECT id FROM kompaniyalar WHERE id=1")
        komp = cur.fetchone()
        cur.close(); conn.close()
        if not komp:
            context.user_data['yangi_rol'] = 'admin'
            context.user_data['user_id'] = user_id
            await update.message.reply_text("🏢 Kompaniyangiz nomini kiriting:")
            return KOMPANIYA_NOMI
        else:
            conn2 = connect(); cur2 = conn2.cursor()
            cur2.execute("UPDATE kompaniyalar SET admin_id=%s WHERE id=1", (user_id,))
            conn2.commit(); cur2.close(); conn2.close()
            await admin_menu(update)
            return ConversationHandler.END
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id, ism, rol FROM xodimlar WHERE telefon LIKE %s", (f"%{telefon[-9:]}%",))
    xodim = cur.fetchone()
    cur.close(); conn.close()
    if not xodim:
        await update.message.reply_text(f"⛔️ Sizning raqamingiz tizimda yo'q!\n\nAdmin bilan bog'laning:\n📱 +998 {ADMIN_TELEFON}")
        return ConversationHandler.END
    context.user_data['telefon_xodim'] = xodim
    context.user_data['user_id'] = user_id
    await update.message.reply_text("🔐 Sizga berilgan kodni kiriting:")
    return XODIM_KOD_TASDIQ

async def kod_tasdiq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kiritilgan_kod = update.message.text
    xodim = context.user_data.get('telefon_xodim')
    user_id = context.user_data.get('user_id')
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT kod FROM xodimlar WHERE id=%s", (xodim[0],))
    row = cur.fetchone()
    if not row or row[0] != kiritilgan_kod:
        cur.close(); conn.close()
        await update.message.reply_text(f"❌ Kod noto'g'ri!\n\nAdmin bilan bog'laning:\n📱 +998 {ADMIN_TELEFON}")
        return ConversationHandler.END
    cur.execute("UPDATE xodimlar SET telegram_id=%s WHERE id=%s", (user_id, xodim[0]))
    conn.commit(); cur.close(); conn.close()
    if xodim[2] == "hr":
        await hr_menu(update)
    else:
        await xodim_menu(update, xodim[1])
    return ConversationHandler.END

async def kompaniya_saqlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('yangi_rol') == 'admin':
        nomi = update.message.text
        user_id = context.user_data.get('user_id')
        conn = connect(); cur = conn.cursor()
        cur.execute("INSERT INTO kompaniyalar (nomi, admin_telefon, admin_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (nomi, ADMIN_TELEFON, user_id))
        conn.commit(); cur.close(); conn.close()
        await update.message.reply_text(f"✅ '{nomi}' kompaniyasi yaratildi!")
        await admin_menu(update)
        return ConversationHandler.END
    return KOMPANIYA_NOMI

async def xodim_qosh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 Xodim ism familiyasini kiriting:")
    return XODIM_ISM

async def xodim_ism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ism'] = update.message.text
    await update.message.reply_text("📱 Telefon raqamini kiriting:")
    return XODIM_TELEFON

async def xodim_telefon_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['telefon'] = update.message.text
    await update.message.reply_text("💼 Lavozimini kiriting:")
    return XODIM_LAVOZIM

async def xodim_lavozim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['lavozim'] = update.message.text
    await update.message.reply_text("💰 Oylik maoshini kiriting (so'm):")
    return XODIM_OYLIK

async def xodim_oylik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['oylik'] = update.message.text
    await update.message.reply_text("⏰ Ish boshlanish vaqti (masalan: 09:00):")
    return XODIM_ISH_BOSH

async def xodim_ish_bosh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ish_bosh'] = update.message.text
    await update.message.reply_text("⏰ Ish tugash vaqti (masalan: 18:00):")
    return XODIM_ISH_TUG

async def xodim_ish_tug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ish_tug'] = update.message.text
    buttons = [["👷 Xodim", "👔 HR"]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text("🔑 Rolini tanlang:", reply_markup=markup)
    return XODIM_ROL

async def xodim_rol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rol'] = "hr" if update.message.text == "👔 HR" else "xodim"
    await update.message.reply_text("🔐 Xodim uchun kirish kodi kiriting:")
    return XODIM_KOD

async def xodim_kod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    kod = update.message.text
    rol = context.user_data['rol']
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id FROM kompaniyalar WHERE id=1")
    komp = cur.fetchone()
    if not komp:
        cur.execute("SELECT kompaniya_id FROM xodimlar WHERE telegram_id=%s AND rol='hr'", (user_id,))
        hr = cur.fetchone()
        if hr:
            komp = hr
    if komp:
        cur.execute('''INSERT INTO xodimlar (ism, telefon, lavozim, oylik, ish_boshlanish, ish_tugash, kompaniya_id, rol, kod)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (context.user_data['ism'], context.user_data['telefon'], context.user_data['lavozim'],
             context.user_data['oylik'], context.user_data['ish_bosh'], context.user_data['ish_tug'],
             komp[0], rol, kod))
        conn.commit()
    cur.close(); conn.close()
    await update.message.reply_text(
        f"✅ {context.user_data['ism']} qo'shildi!\n"
        f"💼 {context.user_data['lavozim']}\n💰 {context.user_data['oylik']} so'm\n"
        f"⏰ {context.user_data['ish_bosh']} - {context.user_data['ish_tug']}\n"
        f"🔑 Rol: {rol}\n🔐 Kod: {kod}")
    conn2 = connect(); cur2 = conn2.cursor()
    cur2.execute("SELECT admin_id FROM kompaniyalar WHERE id=1")
    admin = cur2.fetchone()
    cur2.close(); conn2.close()
    if admin and admin[0] == user_id:
        await admin_menu(update)
    else:
        await hr_menu(update)
    return ConversationHandler.END

async def xodimlar_royxat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT admin_id FROM kompaniyalar WHERE id=1")
    admin = cur.fetchone()
    is_admin = admin and admin[0] == user_id
    cur.execute("SELECT ism, lavozim, telefon, oylik, ish_boshlanish, ish_tugash, rol, kod FROM xodimlar WHERE kompaniya_id=1")
    xodimlar = cur.fetchall()
    cur.close(); conn.close()
    if not xodimlar:
        await update.message.reply_text("❌ Xodim yo'q!")
        return
    matn = "👥 Xodimlar ro'yxati:\n\n"
    for i, x in enumerate(xodimlar, 1):
        matn += f"{i}. {x[0]}\n   💼 {x[1]} | 📱 {x[2]}\n   💰 {x[3]} so'm\n   ⏰ {x[4]} - {x[5]}\n   🔑 {x[6]}\n"
        if is_admin:
            matn += f"   🔐 Kod: {x[7]}\n"
        matn += "\n"
    await update.message.reply_text(matn)

async def tahrirlash_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT admin_id FROM kompaniyalar WHERE id=1")
    admin = cur.fetchone()
    cur.close(); conn.close()
    if not admin or admin[0] != user_id:
        await update.message.reply_text("❌ Faqat admin tahrirlashi mumkin!")
        return ConversationHandler.END
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id, ism, lavozim FROM xodimlar WHERE kompaniya_id=1")
    xodimlar = cur.fetchall()
    cur.close(); conn.close()
    if not xodimlar:
        await update.message.reply_text("❌ Xodim yo'q!")
        return ConversationHandler.END
    matn = "👤 Qaysi xodimni tahrirlaysiz?\n\n"
    buttons = []
    for x in xodimlar:
        matn += f"{x[0]}. {x[1]} — {x[2]}\n"
        buttons.append([f"{x[0]}. {x[1]}"])
    buttons.append(["🔙 Bekor qilish"])
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text(matn, reply_markup=markup)
    return TAHRIR_TANLASH

async def tahrirlash_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 Bekor qilish":
        await admin_menu(update)
        return ConversationHandler.END
    try:
        xodim_id = int(text.split(".")[0])
        context.user_data['tahrir_id'] = xodim_id
        conn = connect(); cur = conn.cursor()
        cur.execute("SELECT ism, telefon, lavozim, oylik, ish_boshlanish, ish_tugash, rol, kod FROM xodimlar WHERE id=%s", (xodim_id,))
        x = cur.fetchone()
        cur.close(); conn.close()
        if not x:
            await update.message.reply_text("❌ Xodim topilmadi!")
            return ConversationHandler.END
        buttons = [["👤 Ism", "📱 Telefon"], ["💼 Lavozim", "💰 Oylik"],
                   ["⏰ Ish boshlanish", "⏰ Ish tugash"], ["🔑 Rol", "🔐 Kod"], ["🔙 Bekor qilish"]]
        markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        await update.message.reply_text(
            f"✏️ {x[0]} — nimani o'zgartirasiz?\n\n👤 Ism: {x[0]}\n📱 Telefon: {x[1]}\n"
            f"💼 Lavozim: {x[2]}\n💰 Oylik: {x[3]} so'm\n⏰ Ish vaqti: {x[4]} - {x[5]}\n"
            f"🔑 Rol: {x[6]}\n🔐 Kod: {x[7]}", reply_markup=markup)
        return TAHRIR_QIYMAT
    except:
        await update.message.reply_text("❌ Xato! Qaytadan tanlang.")
        return TAHRIR_TANLASH

async def tahrirlash_qiymat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    xodim_id = context.user_data.get('tahrir_id')
    if text == "🔙 Bekor qilish":
        await admin_menu(update)
        return ConversationHandler.END
    maydon_map = {
        "👤 Ism": ("ism", "Yangi ismni kiriting:"),
        "📱 Telefon": ("telefon", "Yangi telefon raqamini kiriting:"),
        "💼 Lavozim": ("lavozim", "Yangi lavozimni kiriting:"),
        "💰 Oylik": ("oylik", "Yangi oylik maoshini kiriting:"),
        "⏰ Ish boshlanish": ("ish_boshlanish", "Yangi ish boshlanish vaqtini kiriting (09:00):"),
        "⏰ Ish tugash": ("ish_tugash", "Yangi ish tugash vaqtini kiriting (18:00):"),
        "🔑 Rol": ("rol", "Rolni tanlang:"),
        "🔐 Kod": ("kod", "Yangi kodni kiriting:"),
    }
    if text in maydon_map:
        context.user_data['tahrir_maydon'] = maydon_map[text][0]
        if text == "🔑 Rol":
            markup = ReplyKeyboardMarkup([["👷 Xodim", "👔 HR"]], resize_keyboard=True)
            await update.message.reply_text(maydon_map[text][1], reply_markup=markup)
        else:
            await update.message.reply_text(maydon_map[text][1])
        context.user_data['tahrir_kutish'] = True
        return TAHRIR_QIYMAT
    if context.user_data.get('tahrir_kutish'):
        maydon = context.user_data.get('tahrir_maydon')
        yangi_qiymat = "hr" if (maydon == "rol" and text == "👔 HR") else ("xodim" if maydon == "rol" else text)
        conn = connect(); cur = conn.cursor()
        cur.execute(f"UPDATE xodimlar SET {maydon}=%s WHERE id=%s", (yangi_qiymat, xodim_id))
        conn.commit(); cur.close(); conn.close()
        context.user_data['tahrir_kutish'] = False
        await update.message.reply_text("✅ Muvaffaqiyatli yangilandi!")
        await admin_menu(update)
        return ConversationHandler.END
    return TAHRIR_QIYMAT

async def keldi_gps_sorov(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id FROM xodimlar WHERE telegram_id=%s", (user_id,))
    xodim = cur.fetchone()
    cur.close(); conn.close()
    if not xodim:
        await update.message.reply_text("❌ Siz ro'yxatdan o'tmagansiz!")
        return ConversationHandler.END
    lat, lon, radius = get_gps()
    button = KeyboardButton("📍 Joylashuvni yuborish", request_location=True)
    markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(f"📍 Joylashuvingizni yuboring!\n⚠️ Faqat ish joyidan {radius} metr ichida bo'lsangiz belgilanadi.", reply_markup=markup)
    return KELDI_GPS

async def keldi_gps_tekshir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    location = update.message.location
    if not location:
        await update.message.reply_text("❌ Joylashuv yuborilmadi!")
        return ConversationHandler.END
    lat, lon, radius = get_gps()
    m = masofa(lat, lon, location.latitude, location.longitude)
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id, ism FROM xodimlar WHERE telegram_id=%s", (user_id,))
    xodim = cur.fetchone()
    cur.close(); conn.close()
    if m > radius:
        await update.message.reply_text(f"❌ Siz ish joyidan uzoqdasiz!\n📏 Masofa: {int(m)} metr\n✅ Ruxsat: {radius} metr")
        await xodim_menu(update, xodim[1] if xodim else "")
        return ConversationHandler.END
    context.user_data['keldi_xodim_id'] = xodim[0]
    context.user_data['keldi_masofa'] = int(m)
    await update.message.reply_text(f"✅ Joylashuv tasdiqlandi! ({int(m)} metr)\n\n🤳 Endi selfie yuboring:")
    return KELDI_RASM

async def keldi_rasm_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Iltimos rasm yuboring!")
        return KELDI_RASM
    xodim_id = context.user_data.get('keldi_xodim_id')
    rasm_id = update.message.photo[-1].file_id
    natija = keldi_belgilash(xodim_id)
    keldi_rasm_saqlash(xodim_id, rasm_id)
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT ism, lavozim, kompaniya_id FROM xodimlar WHERE id=%s", (xodim_id,))
    xodim = cur.fetchone()
    cur.execute("SELECT kechikish FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, datetime.now().strftime("%Y-%m-%d")))
    dav = cur.fetchone()
    cur.close(); conn.close()
    kechikish = dav[0] if dav else 0
    motiv = motivatsiya_keldi(xodim[0], kechikish)
    await update.message.reply_text(f"{natija}\n📏 Masofa: {context.user_data.get('keldi_masofa')} metr\n\n{motiv}")
    admin_id = get_admin_id()
    hr_ids = get_hr_ids(xodim[2])
    xabar = (f"📨 KELDI XABARI\n━━━━━━━━━━━━━━━\n👤 {xodim[0]}\n💼 {xodim[1]}\n"
             f"⏰ {datetime.now().strftime('%H:%M')}\n⚠️ Kechikish: {kechikish_format(kechikish)}\n"
             f"📏 Masofa: {context.user_data.get('keldi_masofa')} metr\n━━━━━━━━━━━━━━━")
    bot = update.get_bot()
    if admin_id:
        try:
            await bot.send_message(admin_id, xabar)
            await bot.send_photo(admin_id, rasm_id)
        except: pass
    for hr_id in hr_ids:
        try:
            await bot.send_message(hr_id, xabar)
            await bot.send_photo(hr_id, rasm_id)
        except: pass
    await xodim_menu(update, xodim[0])
    return ConversationHandler.END

async def ketdi_gps_sorov(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id FROM xodimlar WHERE telegram_id=%s", (user_id,))
    xodim = cur.fetchone()
    cur.close(); conn.close()
    if not xodim:
        await update.message.reply_text("❌ Siz ro'yxatdan o'tmagansiz!")
        return ConversationHandler.END
    lat, lon, radius = get_gps()
    button = KeyboardButton("📍 Joylashuvni yuborish", request_location=True)
    markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(f"📍 Joylashuvingizni yuboring!\n⚠️ Faqat ish joyidan {radius} metr ichida bo'lsangiz belgilanadi.", reply_markup=markup)
    return KETDI_GPS

async def ketdi_gps_tekshir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    location = update.message.location
    if not location:
        await update.message.reply_text("❌ Joylashuv yuborilmadi!")
        return ConversationHandler.END
    lat, lon, radius = get_gps()
    m = masofa(lat, lon, location.latitude, location.longitude)
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id, ism FROM xodimlar WHERE telegram_id=%s", (user_id,))
    xodim = cur.fetchone()
    cur.close(); conn.close()
    if m > radius:
        await update.message.reply_text(f"❌ Siz ish joyidan uzoqdasiz!\n📏 Masofa: {int(m)} metr\n✅ Ruxsat: {radius} metr")
        await xodim_menu(update, xodim[1] if xodim else "")
        return ConversationHandler.END
    context.user_data['ketdi_xodim_id'] = xodim[0]
    context.user_data['ketdi_masofa'] = int(m)
    await update.message.reply_text(f"✅ Joylashuv tasdiqlandi! ({int(m)} metr)\n\n🤳 Endi selfie yuboring:")
    return KETDI_RASM

async def ketdi_rasm_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Iltimos rasm yuboring!")
        return KETDI_RASM
    xodim_id = context.user_data.get('ketdi_xodim_id')
    rasm_id = update.message.photo[-1].file_id
    natija = ketdi_belgilash(xodim_id)
    ketdi_rasm_saqlash(xodim_id, rasm_id)
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT ism, lavozim, kompaniya_id, ish_tugash FROM xodimlar WHERE id=%s", (xodim_id,))
    xodim = cur.fetchone()
    cur.execute("SELECT ish_soat FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, datetime.now().strftime("%Y-%m-%d")))
    dav = cur.fetchone()
    cur.close(); conn.close()
    ish_soat = dav[0] if dav else 0
    try:
        tugash = datetime.strptime(xodim[3], "%H:%M")
        kerak = (tugash - datetime.strptime("09:00", "%H:%M")).total_seconds() / 3600
    except:
        kerak = 8
    motiv = motivatsiya_ketdi(xodim[0], ish_soat, kerak)
    await update.message.reply_text(f"{natija}\n📏 Masofa: {context.user_data.get('ketdi_masofa')} metr\n\n{motiv}")
    admin_id = get_admin_id()
    hr_ids = get_hr_ids(xodim[2])
    xabar = (f"📨 KETDI XABARI\n━━━━━━━━━━━━━━━\n👤 {xodim[0]}\n💼 {xodim[1]}\n"
             f"⏰ {datetime.now().strftime('%H:%M')}\n⏱ Ish vaqti: {soat_format(ish_soat)}\n"
             f"📏 Masofa: {context.user_data.get('ketdi_masofa')} metr\n━━━━━━━━━━━━━━━")
    bot = update.get_bot()
    if admin_id:
        try:
            await bot.send_message(admin_id, xabar)
            await bot.send_photo(admin_id, rasm_id)
        except: pass
    for hr_id in hr_ids:
        try:
            await bot.send_message(hr_id, xabar)
            await bot.send_photo(hr_id, rasm_id)
        except: pass
    await xodim_menu(update, xodim[0])
    return ConversationHandler.END

async def manual_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT admin_id FROM kompaniyalar WHERE id=1")
    admin = cur.fetchone()
    is_admin = admin and admin[0] == user_id
    cur.execute("SELECT id, rol FROM xodimlar WHERE telegram_id=%s", (user_id,))
    xodim = cur.fetchone()
    is_hr = xodim and xodim[1] == "hr"
    cur.close(); conn.close()
    if not is_admin and not is_hr:
        await update.message.reply_text("❌ Ruxsat yo'q!")
        return ConversationHandler.END
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id, ism, lavozim FROM xodimlar WHERE kompaniya_id=1")
    xodimlar = cur.fetchall()
    cur.close(); conn.close()
    if not xodimlar:
        await update.message.reply_text("❌ Xodim yo'q!")
        return ConversationHandler.END
    matn = "👤 Qaysi xodim uchun kiritasiz?\n\n"
    buttons = []
    for x in xodimlar:
        matn += f"{x[0]}. {x[1]} — {x[2]}\n"
        buttons.append([f"{x[0]}. {x[1]}"])
    buttons.append(["🔙 Bekor qilish"])
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text(matn, reply_markup=markup)
    return MANUAL_XODIM

async def manual_xodim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 Bekor qilish":
        await admin_menu(update)
        return ConversationHandler.END
    try:
        xodim_id = int(text.split(".")[0])
        context.user_data['manual_xodim_id'] = xodim_id
        await update.message.reply_text("📅 Sanani kiriting:\nMasalan: 2026-05-23")
        return MANUAL_SANA
    except:
        await update.message.reply_text("❌ Xato! Qaytadan tanlang.")
        return MANUAL_XODIM

async def manual_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['manual_sana'] = update.message.text
    await update.message.reply_text("⏰ Keldi vaqtini kiriting:\nMasalan: 09:15")
    return MANUAL_KELDI

async def manual_keldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['manual_keldi'] = update.message.text
    await update.message.reply_text("⏰ Ketdi vaqtini kiriting:\nMasalan: 18:30")
    return MANUAL_KETDI

async def manual_ketdi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['manual_ketdi'] = update.message.text
    buttons = [["✅ Normal", "📋 Sababli", "❌ Sababsiz"]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text("📋 Holatni tanlang:", reply_markup=markup)
    return MANUAL_HOLAT

async def manual_holat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    holat_map = {"✅ Normal": "normal", "📋 Sababli": "sababli", "❌ Sababsiz": "sababsiz"}
    context.user_data['manual_holat'] = holat_map.get(update.message.text, "normal")
    await update.message.reply_text("📝 Izoh kiriting:")
    return MANUAL_IZOH

async def manual_izoh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    izoh = update.message.text
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT ism FROM xodimlar WHERE telegram_id=%s", (user_id,))
    kiritdi = cur.fetchone()
    cur.close(); conn.close()
    kiritdi_ism = kiritdi[0] if kiritdi else "Admin"
    natija = manual_davomat(context.user_data['manual_xodim_id'], context.user_data['manual_sana'],
        context.user_data['manual_keldi'], context.user_data['manual_ketdi'],
        context.user_data['manual_holat'], izoh, kiritdi_ism, user_id)
    await update.message.reply_text(natija)
    conn2 = connect(); cur2 = conn2.cursor()
    cur2.execute("SELECT admin_id FROM kompaniyalar WHERE id=1")
    admin = cur2.fetchone()
    cur2.close(); conn2.close()
    if admin and admin[0] == user_id:
        await admin_menu(update)
    else:
        await hr_menu(update)
    return ConversationHandler.END

async def sababli_sorov_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Sababli qolish sababini yozing:\n\nMasalan: Kasalman, shifokorga borishim kerak")
    return SABAB_SOROV

async def sababli_sorov_saqlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sabab = update.message.text
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id, ism, lavozim, kompaniya_id FROM xodimlar WHERE telegram_id=%s", (user_id,))
    xodim = cur.fetchone()
    if not xodim:
        cur.close(); conn.close()
        await update.message.reply_text("❌ Siz ro'yxatdan o'tmagansiz!")
        return ConversationHandler.END
    sana = datetime.now().strftime("%Y-%m-%d")
    cur.execute("INSERT INTO sababli_sorovlar (xodim_id, sana, sabab) VALUES (%s, %s, %s) RETURNING id", (xodim[0], sana, sabab))
    sorov_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    await update.message.reply_text("✅ So'rovingiz yuborildi!\nAdmin yoki HR tasdiqlashini kuting.")
    admin_id = get_admin_id()
    hr_ids = get_hr_ids(xodim[3])
    xabar = (f"📋 SABABLI SO'ROV\n━━━━━━━━━━━━━━━\n👤 {xodim[1]}\n💼 {xodim[2]}\n"
             f"📅 Sana: {sana}\n📝 Sabab: {sabab}\n━━━━━━━━━━━━━━━")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"sabab_ha_{sorov_id}_{xodim[0]}"),
         InlineKeyboardButton("❌ Rad etish", callback_data=f"sabab_yoq_{sorov_id}_{xodim[0]}")]
    ])
    bot = update.get_bot()
    if admin_id:
        try: await bot.send_message(admin_id, xabar, reply_markup=keyboard)
        except: pass
    for hr_id in hr_ids:
        try: await bot.send_message(hr_id, xabar, reply_markup=keyboard)
        except: pass
    await xodim_menu(update, xodim[1])
    return ConversationHandler.END

async def sababli_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    holat = data[1]; sorov_id = int(data[2]); xodim_id = int(data[3])
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT sana, sabab FROM sababli_sorovlar WHERE id=%s", (sorov_id,))
    sorov = cur.fetchone()
    cur.execute("SELECT ism, telegram_id FROM xodimlar WHERE id=%s", (xodim_id,))
    xodim = cur.fetchone()
    if holat == "ha":
        cur.execute("UPDATE sababli_sorovlar SET holat='tasdiqlandi' WHERE id=%s", (sorov_id,))
        cur.execute("SELECT id FROM davomat WHERE xodim_id=%s AND sana=%s", (xodim_id, sorov[0]))
        if cur.fetchone():
            cur.execute("UPDATE davomat SET holat='sababli', izoh=%s WHERE xodim_id=%s AND sana=%s", (sorov[1], xodim_id, sorov[0]))
        else:
            cur.execute("INSERT INTO davomat (xodim_id, sana, holat, izoh) VALUES (%s, %s, 'sababli', %s)", (xodim_id, sorov[0], sorov[1]))
        conn.commit(); cur.close(); conn.close()
        await query.edit_message_text(f"✅ {xodim[0]} ning sababli so'rovi tasdiqlandi!")
        if xodim[1]:
            try: await context.bot.send_message(xodim[1], f"✅ Hurmatli {xodim[0]},\nSababli qolish so'rovingiz tasdiqlandi!\n📅 Sana: {sorov[0]}")
            except: pass
    else:
        cur.execute("UPDATE sababli_sorovlar SET holat='rad etildi' WHERE id=%s", (sorov_id,))
        conn.commit(); cur.close(); conn.close()
        await query.edit_message_text(f"❌ {xodim[0]} ning sababli so'rovi rad etildi!")
        if xodim[1]:
            try: await context.bot.send_message(xodim[1], f"❌ Hurmatli {xodim[0]},\nAfsuski, sababli qolish so'rovingiz rad etildi.\n📅 Sana: {sorov[0]}\nRahbariyat bilan bog'laning.")
            except: pass

async def hisobot_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Excel tayyorlanmoqda...")
    fayl = excel_hisobot(1)
    with open(fayl, 'rb') as f:
        await update.message.reply_document(f, filename="hisobot.xlsx")
    os.remove(fayl)

async def mening_davomatim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id, ism FROM xodimlar WHERE telegram_id=%s", (user_id,))
    xodim = cur.fetchone()
    cur.close(); conn.close()
    if not xodim:
        await update.message.reply_text("❌ Siz ro'yxatdan o'tmagansiz!")
        return
    davomatlar = xodim_davomati(xodim[0])
    if not davomatlar:
        await update.message.reply_text("📋 Hozircha davomat yo'q!")
        return
    matn = f"📋 {xodim[1]} — Davomat:\n\n"
    for d in davomatlar[-10:]:
        matn += (f"📅 {d[0]}\n   ✅ Keldi: {d[1] or '—'}\n   🚪 Ketdi: {d[2] or '—'}\n"
                f"   ⏱ Ish vaqti: {soat_format(d[3])}\n   ⚠️ Kechikish: {kechikish_format(d[4])}\n"
                f"   📋 Holat: {d[5] or 'normal'}\n   📝 Izoh: {d[6] or '—'}\n   👤 Kim kiritdi: {d[7] or 'xodim'}\n\n")
    await update.message.reply_text(matn)

async def sozlamalar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT admin_id FROM kompaniyalar WHERE id=1")
    admin = cur.fetchone()
    cur.close(); conn.close()
    if not admin or admin[0] != user_id:
        await update.message.reply_text("❌ Faqat admin sozlay oladi!")
        return ConversationHandler.END
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT nomi, gps_lat, gps_lon, gps_radius FROM kompaniyalar WHERE id=1")
    komp = cur.fetchone()
    cur.close(); conn.close()
    buttons = [["🏢 Korxona nomi", "📍 GPS koordinata"], ["📏 GPS radius", "📱 Admin telefon"], ["🔙 Orqaga"]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text(f"⚙️ Sozlamalar:\n\n🏢 Korxona: {komp[0]}\n📍 GPS: {komp[1]}, {komp[2]}\n📏 Radius: {komp[3]} metr\n", reply_markup=markup)
    return SOZLAMA_TANLASH

async def sozlama_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 Orqaga":
        await admin_menu(update)
        return ConversationHandler.END
    sozlama_map = {
        "🏢 Korxona nomi": ("nomi", "Yangi korxona nomini kiriting:"),
        "📍 GPS koordinata": ("gps", "GPS koordinatani kiriting:\nMasalan: 37.667088,67.02551"),
        "📏 GPS radius": ("gps_radius", "Yangi radiusni kiriting (metr):\nMasalan: 200"),
        "📱 Admin telefon": ("admin_telefon", "Yangi admin telefon raqamini kiriting:"),
    }
    if text in sozlama_map:
        context.user_data['sozlama_maydon'] = sozlama_map[text][0]
        await update.message.reply_text(sozlama_map[text][1])
        return SOZLAMA_QIYMAT
    return SOZLAMA_TANLASH

async def sozlama_qiymat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    maydon = context.user_data.get('sozlama_maydon')
    text = update.message.text
    conn = connect(); cur = conn.cursor()
    if maydon == "gps":
        try:
            lat, lon = text.split(",")
            cur.execute("UPDATE kompaniyalar SET gps_lat=%s, gps_lon=%s WHERE id=1", (float(lat.strip()), float(lon.strip())))
        except:
            await update.message.reply_text("❌ Noto'g'ri format! Masalan: 37.667088,67.02551")
            cur.close(); conn.close()
            return SOZLAMA_QIYMAT
    else:
        cur.execute(f"UPDATE kompaniyalar SET {maydon}=%s WHERE id=1", (text,))
    conn.commit(); cur.close(); conn.close()
    await update.message.reply_text("✅ Sozlama yangilandi!")
    await admin_menu(update)
    return ConversationHandler.END

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ["👥 Xodimlar", "👥 Xodimlar ro'yxati"]:
        await xodimlar_royxat(update, context)
    elif text == "➕ Xodim qo'shish":
        return await xodim_qosh(update, context)
    elif text in ["✅ Keldi", "✅ Keldi belgilash"]:
        return await keldi_gps_sorov(update, context)
    elif text in ["🚪 Ketdi", "🚪 Ketdi belgilash"]:
        return await ketdi_gps_sorov(update, context)
    elif text == "📋 Sababli so'rov":
        return await sababli_sorov_boshlash(update, context)
    elif text == "📋 Sababli so'rovlar":
        await update.message.reply_text("📋 So'rovlar yuqorida ko'rinadi!")
    elif text == "📋 Mening davomatim":
        await mening_davomatim(update, context)
    elif text == "📝 Manual davomat":
        return await manual_boshlash(update, context)
    elif text == "📊 Hisobot":
        await hisobot_excel(update, context)
    elif text == "✏️ Xodim tahrirlash":
        return await tahrirlash_boshlash(update, context)
    elif text == "⚙️ Sozlamalar":
        return await sozlamalar(update, context)
    elif text == "🔙 Orqaga":
        await admin_menu(update)

def main():
    create_tables()
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^➕ Xodim qo'shish$"), xodim_qosh),
            MessageHandler(filters.Regex("^✅ Keldi$"), keldi_gps_sorov),
            MessageHandler(filters.Regex("^✅ Keldi belgilash$"), keldi_gps_sorov),
            MessageHandler(filters.Regex("^🚪 Ketdi$"), ketdi_gps_sorov),
            MessageHandler(filters.Regex("^🚪 Ketdi belgilash$"), ketdi_gps_sorov),
            MessageHandler(filters.Regex("^✏️ Xodim tahrirlash$"), tahrirlash_boshlash),
            MessageHandler(filters.Regex("^📝 Manual davomat$"), manual_boshlash),
            MessageHandler(filters.Regex("^📋 Sababli so'rov$"), sababli_sorov_boshlash),
            MessageHandler(filters.Regex("^⚙️ Sozlamalar$"), sozlamalar),
        ],
        states={
            KOMPANIYA_NOMI: [MessageHandler(filters.TEXT & ~filters.COMMAND, kompaniya_saqlash)],
            TELEFON_TASDIQ: [MessageHandler(filters.CONTACT, telefon_tasdiq)],
            XODIM_KOD_TASDIQ: [MessageHandler(filters.TEXT & ~filters.COMMAND, kod_tasdiq)],
            XODIM_ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, xodim_ism)],
            XODIM_TELEFON: [MessageHandler(filters.TEXT & ~filters.COMMAND, xodim_telefon_input)],
            XODIM_LAVOZIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, xodim_lavozim)],
            XODIM_OYLIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, xodim_oylik)],
            XODIM_ISH_BOSH: [MessageHandler(filters.TEXT & ~filters.COMMAND, xodim_ish_bosh)],
            XODIM_ISH_TUG: [MessageHandler(filters.TEXT & ~filters.COMMAND, xodim_ish_tug)],
            XODIM_ROL: [MessageHandler(filters.TEXT & ~filters.COMMAND, xodim_rol)],
            XODIM_KOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, xodim_kod)],
            KELDI_GPS: [MessageHandler(filters.LOCATION, keldi_gps_tekshir)],
            KELDI_RASM: [MessageHandler(filters.PHOTO, keldi_rasm_olish)],
            KETDI_GPS: [MessageHandler(filters.LOCATION, ketdi_gps_tekshir)],
            KETDI_RASM: [MessageHandler(filters.PHOTO, ketdi_rasm_olish)],
            TAHRIR_TANLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, tahrirlash_tanlash)],
            TAHRIR_QIYMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, tahrirlash_qiymat)],
            MANUAL_XODIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_xodim)],
            MANUAL_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_sana)],
            MANUAL_KELDI: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_keldi)],
            MANUAL_KETDI: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_ketdi)],
            MANUAL_HOLAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_holat)],
            MANUAL_IZOH: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_izoh)],
            SABAB_SOROV: [MessageHandler(filters.TEXT & ~filters.COMMAND, sababli_sorov_saqlash)],
            SOZLAMA_TANLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, sozlama_tanlash)],
            SOZLAMA_QIYMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sozlama_qiymat)],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(sababli_callback, pattern="^sabab_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    print("Bot ishlamoqda...")
    app.run_polling()

if __name__ == "__main__":
    main()