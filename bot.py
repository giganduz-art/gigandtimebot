import os, math, logging, random, string
from datetime import datetime, time as dtime, timedelta
import pytz
from telegram import (Update, ReplyKeyboardMarkup, KeyboardButton,
                      InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove)
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          CallbackQueryHandler, ConversationHandler, filters, ContextTypes)
from database import *
from flask import Flask, render_template, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TASHKENT = pytz.timezone('Asia/Tashkent')

def random_kod(n=6):
    return ''.join(random.choices(string.digits, k=n))

def masofa_hisob(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2-lat1, lon2-lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return round(R * 2 * math.asin(math.sqrt(a)))

def ketdi_xabar_matni(ism, ish_tugash, ketdi_vaqt, ish_soat):
    try:
        tug = datetime.strptime(ish_tugash, "%H:%M")
        ket = datetime.strptime(ketdi_vaqt, "%H:%M")
        farq = int((ket - tug).total_seconds() / 60)
        s = int(ish_soat); d = int((ish_soat - s) * 60)
        if farq >= 30:
            return (f"🌙 *QOLIB ISHLASH* (+{farq} daqiqa ortiqcha)\n"
                    f"Rahmat, {ism}! Bugun {s} soat {d} daqiqa ishlading.\n"
                    f"Qo'shimcha {farq} daqiqa qolib ishlading! 🏆\n"
                    f"Bunday fidoyilik qadrlanadi!")
        elif farq >= -15:
            return (f"✅ *TO'LIQ ISH KUNI*\n"
                    f"Yaxshi ish kuni, {ism}!\n"
                    f"Bugun {s} soat {d} daqiqa samarali mehnat qildingiz! 💼\n"
                    f"Xayrli oqshom!")
        elif farq >= -30:
            return (f"⚠️ *ERTA KETISH* ({-farq} daqiqa oldin)\n"
                    f"Diqqat, {ism}! Ish vaqti tugamay {-farq} daqiqa oldin ketdingiz.\n"
                    f"Sababini HR ga bildiring! 📋")
        else:
            return (f"❗ *JIDDIY ERTA KETISH* ({-farq} daqiqa oldin)\n"
                    f"Ogohlantirish, {ism}! {-farq} daqiqa oldin ketdingiz.\n"
                    f"Bu intizom buzilishi! Rahbariyat xabardor qilindi! 🚫")
    except:
        return f"🚪 Ketdi vaqti: {ketdi_vaqt}"

# ==================== STATES ====================
(
    TELEFON, KOD,
    SA_MENU, SA_KOMP_LIST, SA_KOMP_NOMI, SA_KOMP_TEL, SA_KOMP_KOD,
    SA_KOMP_TANLASH, SA_KOMP_AMAL, SA_KOMP_TAHRIR_QIYMAT,
    SA_FUNKSIYA, SA_SOZ_MENU,
    SA_ADM_LIST, SA_ADM_QOSH_TEL, SA_ADM_QOSH_ISM,
    SA_KOMP_XODIM_TANLASH, SA_KOMP_XODIM_AMAL, SA_KOMP_XODIM_TAHRIR,
    SA_KOMP_DAV_SANA,
    ADM_MENU, ADM_XODIM_LIST, ADM_XODIM_ISM, ADM_XODIM_TEL,
    ADM_XODIM_LAV, ADM_XODIM_OYLIK, ADM_XODIM_BOSH, ADM_XODIM_TUG,
    ADM_XODIM_ROL, ADM_XODIM_TANLASH, ADM_XODIM_TAHRIR, ADM_XODIM_TAHRIR_Q,
    ADM_GPS_LOK, ADM_GPS_RADIUS,
    ADM_WIFI_AKTIV, ADM_WIFI_SSID,
    ADM_DAV_MENU, ADM_DAV_XODIM, ADM_DAV_SANA, ADM_DAV_KELDI,
    ADM_DAV_KETDI, ADM_DAV_HOLAT, ADM_DAV_IZOH,
    ADM_DAV_TAHRIR_TANLASH, ADM_DAV_TAHRIR_AMAL, ADM_DAV_TAHRIR_Q,
    ADM_HISOBOT_SANA, ADM_HISOBOT_KUN,
    HR_MENU, HR_MAN_XODIM, HR_MAN_SANA, HR_MAN_KELDI,
    HR_MAN_KETDI, HR_MAN_HOLAT, HR_MAN_IZOH,
    XOD_MENU, XOD_KELDI_GPS, XOD_KELDI_RASM,
    XOD_KETDI_GPS, XOD_KETDI_RASM,
    XOD_SABAB_SANA, XOD_SABAB_MATN,
    SA_KOMP_DELETE_KOD,
    SA_HISOBOT_SANA, SA_HISOBOT_KUN,
) = range(64)

# ==================== MENYULAR ====================

def sa_menu_kb():
    return ReplyKeyboardMarkup([
        ["🏢 Kompaniyalar", "👑 Super Adminlar"],
        ["📊 Umumiy hisobot", "📋 Audit Log"],
        ["📸 Barcha rasmlar", "🔐 Sozlamalar"],
    ], resize_keyboard=True)

def adm_menu_kb():
    return ReplyKeyboardMarkup([
        ["👥 Xodimlar", "📅 Davomat"],
        ["📊 Hisobot", "📍 GPS sozlash"],
        ["📡 WiFi sozlash", "📋 Audit Log"],
        ["📸 Rasm log", "🏠 Bosh menu"]
    ], resize_keyboard=True)

def hr_menu_kb():
    return ReplyKeyboardMarkup([
        ["✍️ Manual davomat", "📊 Hisobot"],
        ["🏠 Bosh menu"]
    ], resize_keyboard=True)

def xod_menu_kb():
    return ReplyKeyboardMarkup([
        ["✅ Keldim", "🚪 Ketdim"],
        ["📋 Davomatim", "📊 Statistikam"],
        ["📝 Sababli so'rov", "🏠 Bosh menu"]
    ], resize_keyboard=True)

def xod_wifi_kb(komp_id=None, amal='keldim', xodim_id=None):
    """WiFi prompt inline keyboard with web form"""
    base_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'gigandtimebot.railway.app')
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    wifi_form_url = f"{base_url}/wifi-check?user_id=&komp_id={komp_id}&amal={amal}&xodim_id={xodim_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 WiFi tekshir", url=wifi_form_url),
         InlineKeyboardButton("📍 GPS kerak", callback_data=f"gps_{amal}_{komp_id}")],
        [InlineKeyboardButton("🏠 Orqaga", callback_data="xod_menu")]
    ])


# ==================== START ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.clear()

    if super_admin_id_tekshir(user_id):
        await update.message.reply_text("👑 Super Admin paneliga xush kelibsiz!", reply_markup=sa_menu_kb())
        return SA_MENU

    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT id,nomi,holat FROM kompaniyalar WHERE admin_id=%s", (user_id,))
    adm_komp = cur.fetchone(); cur.close(); conn.close()

    if adm_komp:
        if adm_komp[2] != 'faol':
            await update.message.reply_text("⛔️ Kompaniyangiz faol emas!")
            return ConversationHandler.END
        context.user_data['komp_id'] = adm_komp[0]
        await update.message.reply_text("🏢 Admin paneliga xush kelibsiz!", reply_markup=adm_menu_kb())
        return ADM_MENU

    xodim = telegram_id_orqali_xodim(user_id)
    if xodim:
        komp = kompaniya_olish(xodim[3])
        if not komp or komp[4] != 'faol':
            await update.message.reply_text("⛔️ Kompaniyangiz faol emas!")
            return ConversationHandler.END
        context.user_data.update({'xodim_id': xodim[0], 'ism': xodim[1], 'rol': xodim[2], 'komp_id': xodim[3]})
        if xodim[2] == 'hr':
            await update.message.reply_text(f"👔 HR paneliga xush kelibsiz, {xodim[1]}!", reply_markup=hr_menu_kb())
            return HR_MENU
        else:
            await update.message.reply_text(f"👋 Xush kelibsiz, {xodim[1]}!", reply_markup=xod_menu_kb())
            return XOD_MENU

    murojaat = get_murojaat_raqam()
    btn = [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]]
    await update.message.reply_text(
        f"👋 Xush kelibsiz!\n\n"
        f"Telefon raqamingizni yuboring.\n\n"
        f"❓ Agar tizimda yo'q bo'lsangiz:\n"
        f"📞 Murojaat: +998{murojaat}",
        reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
    return TELEFON

async def boshlash_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """▶️ tugmasi uchun"""
    return await start(update, context)

async def telefon_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("❌ Tugma orqali telefon yuboring!")
        return TELEFON
    telefon = contact.phone_number
    user_id = update.effective_user.id
    context.user_data['telefon'] = telefon

    if super_admin_tekshir(telefon):
        context.user_data['tip'] = 'super_admin'
        await update.message.reply_text("🔐 Super Admin kodini kiriting:", reply_markup=ReplyKeyboardRemove())
        return KOD

    komp = admin_telefon_orqali_kompaniya(telefon)
    if komp:
        komp_id, komp_nomi, holat, admin_kod = komp
        if holat != 'faol':
            await update.message.reply_text("❌ Kompaniya faol emas!")
            return ConversationHandler.END
        context.user_data.update({'tip': 'admin', 'komp_id': komp_id, 'admin_kod': admin_kod})
        await update.message.reply_text(f"🏢 {komp_nomi}\n\n🔐 Admin kodini kiriting:", reply_markup=ReplyKeyboardRemove())
        return KOD

    xodim = telefon_orqali_xodim(telefon)
    if xodim:
        context.user_data.update({'tip': xodim[2], 'xodim_id': xodim[0], 'ism': xodim[1], 'komp_id': xodim[3]})
        await update.message.reply_text(f"👋 {xodim[1]}\n\n🔐 Kodni kiriting:", reply_markup=ReplyKeyboardRemove())
        return KOD

    murojaat = get_murojaat_raqam()
    await update.message.reply_text(
        f"❌ Siz tizimda yo'qsiz.\n\n📞 Murojaat uchun: +998{murojaat}",
        reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def kod_tekshir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kod = update.message.text.strip()
    tip = context.user_data.get('tip')
    user_id = update.effective_user.id
    telefon = context.user_data.get('telefon', '')

    if tip == 'super_admin':
        if not super_admin_kod_tekshir(kod):
            await update.message.reply_text("❌ Noto'g'ri kod!")
            return KOD
        super_admin_telegram_saqlash(telefon, user_id)
        await update.message.reply_text("✅ Xush kelibsiz, Super Admin!", reply_markup=sa_menu_kb())
        return SA_MENU

    elif tip == 'admin':
        if kod != context.user_data.get('admin_kod', ''):
            await update.message.reply_text("❌ Noto'g'ri kod!")
            return KOD
        admin_id_saqlash(context.user_data['komp_id'], user_id)
        await update.message.reply_text("✅ Admin sifatida kirdingiz!", reply_markup=adm_menu_kb())
        return ADM_MENU

    else:
        xodim_id = context.user_data.get('xodim_id')
        xodim = xodim_olish(xodim_id)
        if not xodim or xodim[8] != kod:
            await update.message.reply_text("❌ Noto'g'ri kod!")
            return KOD
        xodim_telegram_saqlash(xodim_id, user_id)
        context.user_data['komp_id'] = xodim[9]
        if tip == 'hr':
            await update.message.reply_text("✅ HR sifatida kirdingiz!", reply_markup=hr_menu_kb())
            return HR_MENU
        else:
            await update.message.reply_text(f"✅ Xush kelibsiz, {context.user_data['ism']}!", reply_markup=xod_menu_kb())
            return XOD_MENU

# ==================== SUPER ADMIN ====================

async def sa_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    user_id = update.effective_user.id

    if matn == "🏢 Kompaniyalar":
        return await sa_kompaniyalar_korsatish(update, context)

    elif matn == "👑 Super Adminlar":
        adminlar = barcha_super_adminlar()
        xabar = "👑 *Super Adminlar:*\n\n"
        for a in adminlar:
            xabar += f"• `{a[0]}` | {a[3]} | {a[1]}\n"
        await update.message.reply_text(xabar, parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["➕ Admin qo'shish", "❌ Admin o'chirish"],
                ["✏️ Mening ma'lumotlarim", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_ADM_LIST

    elif matn == "📊 Umumiy hisobot":
        await update.message.reply_text(
            "📅 Qaysi kun uchun hisobot? (YYYY-MM-DD)\n\n"
            "Masalan: 2026-05-24\n\n"
            "🔔 BARCHA kompaniyalarning hisoboti ko'rsatiladi!",
            reply_markup=ReplyKeyboardRemove())
        return SA_HISOBOT_SANA

    elif matn == "📸 Barcha rasmlar":
        rasmlar = barcha_komp_bugun_rasmlar()
        if not rasmlar:
            await update.message.reply_text(
                "📸 Bugun rasmlar yo'q.",
                reply_markup=sa_menu_kb())
            return SA_MENU

        await update.message.reply_text(
            f"📸 *Barcha kompaniyalarning bugungi rasmlari* ({len(rasmlar)}ta):\n\n"
            "Rasmlar yuborilmoqda...",
            parse_mode='Markdown')

        for komp, ism, lavozim, vaqt, rasm_id, tafsilot in rasmlar:
            try:
                caption = f"🏢 *{komp}*\n👤 {ism}\n💼 {lavozim}\n⏰ {vaqt}"
                if tafsilot:
                    caption += f"\n✅ {tafsilot}"
                await update.message.reply_photo(
                    rasm_id,
                    caption=caption,
                    parse_mode='Markdown')
            except:
                pass

        await update.message.reply_text("✅ Tayyor!", reply_markup=sa_menu_kb())
        return SA_MENU

    elif matn == "📋 Audit Log":
        logs = super_admin_audit_log(limit=20)
        if not logs:
            await update.message.reply_text("📋 Hozircha audit log yo'q.",
                reply_markup=ReplyKeyboardMarkup([["📥 Export Excel", "🔙 Orqaga"]], resize_keyboard=True))
        else:
            xabar = "📋 *OXIRGI 20 AMAL:*\n\n"
            for log in logs:
                komp_nomi, amal, tafsilot, vaqt, user_ism, xodim_id, xodim_ism = log
                xabar += f"🏢 {komp_nomi}\n"
                xabar += f"📌 {amal} | {vaqt}\n"
                xabar += f"👤 {user_ism}\n"
                xabar += f"📝 {tafsilot}\n━━━━━━━━━━━━\n"
            await update.message.reply_text(xabar, parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup([["📥 Export Excel", "🔙 Orqaga"]], resize_keyboard=True))

        context.user_data['audit_view'] = True
        return SA_MENU

    elif matn == "📥 Export Excel" and context.user_data.get('audit_view'):
        await update.message.reply_text("⏳ Excel tayyorlanmoqda...")
        try:
            fayl = export_audit_log_excel()
            with open(fayl, 'rb') as f:
                await update.message.reply_document(f, filename=fayl)
            os.remove(fayl)
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}")
        context.user_data.pop('audit_view', None)
        return SA_MENU

    elif matn == "🔐 Sozlamalar":
        sa = super_admin_olish(user_id)
        murojaat = get_murojaat_raqam()
        await update.message.reply_text(
            f"🔐 *Sozlamalar*\n\n"
            f"👤 Ism: {sa[2] if sa else '—'}\n"
            f"📱 Telefon: {sa[1] if sa else '—'}\n"
            f"📞 Murojaat raqami: {murojaat}",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["🔑 Kodni o'zgartirish", "📱 Telefon o'zgartirish"],
                ["👤 Ism o'zgartirish", "📞 Murojaat raqami"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_SOZ_MENU

    return SA_MENU

async def sa_kompaniyalar_korsatish(update, context):
    kompaniyalar = barcha_kompaniyalar()
    if not kompaniyalar:
        await update.message.reply_text("📋 Hozircha kompaniya yo'q.",
            reply_markup=ReplyKeyboardMarkup([["➕ Yangi kompaniya", "🔙 Orqaga"]], resize_keyboard=True))
    else:
        xabar = "🏢 *Kompaniyalar:*\n\n"
        for k in kompaniyalar:
            emoji = "✅" if k[3] == 'faol' else "🔴"
            xabar += f"{emoji} `{k[0]}`. *{k[1]}*\n"
            xabar += f"   📞 {k[2] or '—'} | 🔑 `{k[9] or '—'}`\n\n"
        tugmalar = [[f"{k[0]}. {k[1]}"] for k in kompaniyalar]
        tugmalar.append(["➕ Yangi kompaniya", "🔙 Orqaga"])
        await update.message.reply_text(xabar, parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
    return SA_KOMP_LIST

async def sa_komp_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Super Admin:", reply_markup=sa_menu_kb())
        return SA_MENU
    if matn == "➕ Yangi kompaniya":
        await update.message.reply_text("🏢 Kompaniya nomini kiriting:", reply_markup=ReplyKeyboardRemove())
        return SA_KOMP_NOMI
    try:
        komp_id = int(matn.split(".")[0].strip())
        komp = kompaniya_olish(komp_id)
        if not komp:
            await update.message.reply_text("❌ Topilmadi!")
            return SA_KOMP_LIST
        context.user_data['sa_komp_id'] = komp_id
        emoji = "✅" if komp[4] == 'faol' else "🔴"
        xabar = (f"🏢 *{komp[1]}*\n━━━━━━━━━━━━━━━\n"
                f"📞 Admin tel: {komp[2] or '—'}\n"
                f"🔑 Admin kodi: `{komp[13] or '—'}`\n"
                f"📍 GPS: {komp[5]}, {komp[6]}\n"
                f"📏 Radius: {komp[7]}m\n"
                f"Holat: {emoji} {komp[4]}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"⚙️ Funksiyalar:\n"
                f"📍GPS:{'✅' if komp[9] else '❌'} "
                f"📡LiveGPS:{'✅' if komp[14] else '❌'} "
                f"🤳Selfie:{'✅' if komp[10] else '❌'} "
                f"👤FaceID:{'✅' if komp[11] else '❌'} "
                f"📷Hikvision:{'✅' if komp[12] else '❌'}")
        await update.message.reply_text(xabar, parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["✏️ Tahrirlash", "⚙️ Funksiyalar"],
                ["✅ Faollashtirish", "🔴 To'xtatish"],
                ["👥 Xodimlar", "📅 Davomat"],
                ["📊 Hisobot", "🗑 O'chirish"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_KOMP_TANLASH
    except:
        await update.message.reply_text("❌ Tanlang!")
        return SA_KOMP_LIST

async def sa_komp_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_nomi'] = update.message.text.strip()
    await update.message.reply_text("📞 Admin telefon raqamini kiriting:")
    return SA_KOMP_TEL

async def sa_komp_tel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_tel'] = update.message.text.strip()
    await update.message.reply_text("🔑 Admin kirish kodini kiriting (masalan: 1234):")
    return SA_KOMP_KOD

async def sa_komp_kod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_kod = update.message.text.strip()
    komp_id = kompaniya_yaratish(context.user_data['y_nomi'], context.user_data['y_tel'], admin_kod)
    await update.message.reply_text(
        f"✅ *Kompaniya yaratildi!*\n\n"
        f"🏢 {context.user_data['y_nomi']}\n"
        f"📞 {context.user_data['y_tel']}\n"
        f"🔑 Admin kodi: `{admin_kod}`\n🆔 ID: {komp_id}",
        parse_mode='Markdown', reply_markup=sa_menu_kb())
    return SA_MENU

async def sa_komp_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    komp_id = context.user_data.get('sa_komp_id')

    if matn == "🔙 Orqaga":
        return await sa_kompaniyalar_korsatish(update, context)

    elif matn == "✅ Faollashtirish":
        kompaniya_holat_ozgartir(komp_id, 'faol')
        await update.message.reply_text("✅ Kompaniya faollashtirildi!", reply_markup=sa_menu_kb())
        return SA_MENU

    elif matn == "🔴 To'xtatish":
        kompaniya_holat_ozgartir(komp_id, 'nofaol')
        await update.message.reply_text("🔴 Kompaniya to'xtatildi!", reply_markup=sa_menu_kb())
        return SA_MENU

    elif matn == "🗑 O'chirish":
        komp = kompaniya_olish(komp_id)
        await update.message.reply_text(
            f"⚠️ *{komp[1]}* kompaniyasini o'chirmoqchisiz!\n\n"
            f"Tasdiqlash uchun *maxfiy kodingizni* kiriting:",
            parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return SA_KOMP_DELETE_KOD

    elif matn == "✏️ Tahrirlash":
        komp = kompaniya_olish(komp_id)
        await update.message.reply_text(
            f"✏️ *{komp[1]}* tahrirlash:", parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["📝 Nomi", "📞 Admin telefon"],
                ["🔑 Admin kodi", "📍 GPS"],
                ["📏 Radius", "📡 WiFi SSID"],
                ["🔗 WiFi MAC", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_KOMP_AMAL

    elif matn == "⚙️ Funksiyalar":
        komp = kompaniya_olish(komp_id)
        await update.message.reply_text(
            f"⚙️ *{komp[1]}* funksiyalari:\n\n"
            f"📍 GPS (oddiy): {'✅' if komp[9] else '❌'}\n"
            f"📡 GPS Live: {'✅' if komp[14] else '❌'}\n"
            f"⏱ 30-daqiqa tekshiruv: {'✅' if komp[15] else '❌'}\n"
            f"🤳 Selfie: {'✅' if komp[10] else '❌'}\n"
            f"👤 Face ID: {'✅' if komp[11] else '❌'}\n"
            f"📷 Hikvision: {'✅' if komp[12] else '❌'}\n"
            f"📡 WiFi: {'✅' if komp[16] else '❌'}",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["📍 GPS", "📡 GPS Live"],
                ["⏱ 30-daqiqa tekshiruv", "🤳 Selfie"],
                ["👤 Face ID", "📷 Hikvision"],
                ["📡 WiFi", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_FUNKSIYA

    elif matn == "👥 Xodimlar":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("👥 Xodimlar yo'q.")
            return SA_KOMP_TANLASH
        xabar = "👥 *Xodimlar:*\n\n"
        tugmalar = []
        for x in xodimlar:
            xabar += f"• `{x[0]}` *{x[1]}* — {x[2]} | 🎭{x[7]}\n"
            tugmalar.append([f"{x[0]}. {x[1]}"])
        tugmalar.append(["➕ Xodim qo'shish", "🔙 Orqaga"])
        await update.message.reply_text(xabar, parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return SA_KOMP_XODIM_TANLASH

    elif matn == "📅 Davomat":
        bugun = hozir().strftime("%Y-%m-%d")
        davomatlar = kompaniya_davomati(komp_id, bugun)
        if not davomatlar:
            await update.message.reply_text(f"📅 Bugun ({bugun}) davomat yo'q.")
        else:
            xabar = f"📅 *Bugungi davomat ({bugun}):*\n\n"
            for d in davomatlar:
                xabar += f"👤 {d[0]}: {d[2] or '—'} → {d[3] or '—'}"
                if d[5] and d[5] > 0:
                    xabar += f" ⚠️{kechikish_format(d[5])}"
                xabar += "\n"
            await update.message.reply_text(xabar, parse_mode='Markdown')
        return SA_KOMP_TANLASH

    elif matn == "📊 Hisobot":
        await update.message.reply_text("⏳ Hisobot tayyorlanmoqda...")
        try:
            fayl = kompaniya_hisobot(komp_id)
            if fayl:
                with open(fayl, 'rb') as f:
                    await update.message.reply_document(f, filename=fayl)
                os.remove(fayl)
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}")
        return SA_KOMP_TANLASH

    return SA_KOMP_TANLASH

async def sa_komp_delete_kod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kod = update.message.text.strip()
    komp_id = context.user_data.get('sa_komp_id')
    if not super_admin_kod_tekshir(kod):
        await update.message.reply_text("❌ Noto'g'ri kod! O'chirish bekor qilindi.", reply_markup=sa_menu_kb())
        return SA_MENU
    komp = kompaniya_olish(komp_id)
    nomi = komp[1] if komp else ''
    kompaniya_ochirish(komp_id)
    await update.message.reply_text(f"🗑 *{nomi}* o'chirildi!", parse_mode='Markdown', reply_markup=sa_menu_kb())
    return SA_MENU

async def sa_komp_amal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    komp_id = context.user_data.get('sa_komp_id')
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    maydon_map = {
        "📝 Nomi": "nomi", "📞 Admin telefon": "admin_telefon",
        "🔑 Admin kodi": "admin_kod", "📏 Radius": "gps_radius",
        "📡 WiFi SSID": "wifi_ssid", "🔗 WiFi MAC": "wifi_mac",
    }
    if matn in maydon_map:
        context.user_data['tahrir_maydon'] = maydon_map[matn]
        await update.message.reply_text(f"Yangi {matn} kiriting:", reply_markup=ReplyKeyboardRemove())
        return SA_KOMP_TAHRIR_QIYMAT
    elif matn == "📍 GPS":
        context.user_data['tahrir_maydon'] = 'gps'
        await update.message.reply_text("GPS lokatsiya yuboring yoki lat,lon kiriting:", reply_markup=ReplyKeyboardRemove())
        return SA_KOMP_TAHRIR_QIYMAT
    return SA_KOMP_AMAL

async def sa_komp_tahrir_qiymat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    komp_id = context.user_data.get('sa_komp_id')
    maydon = context.user_data.get('tahrir_maydon')
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        kompaniya_tahrirlash(komp_id, 'gps_lat', lat)
        kompaniya_tahrirlash(komp_id, 'gps_lon', lon)
        await update.message.reply_text(f"✅ GPS saqlandi: {lat}, {lon}", reply_markup=sa_menu_kb())
        return SA_MENU
    qiymat = update.message.text.strip()
    if maydon == 'gps':
        try:
            lat, lon = qiymat.split(",")
            kompaniya_tahrirlash(komp_id, 'gps_lat', float(lat.strip()))
            kompaniya_tahrirlash(komp_id, 'gps_lon', float(lon.strip()))
        except:
            await update.message.reply_text("❌ Format: lat,lon")
            return SA_KOMP_TAHRIR_QIYMAT
    else:
        kompaniya_tahrirlash(komp_id, maydon, qiymat)
    await update.message.reply_text("✅ Saqlandi!", reply_markup=sa_menu_kb())
    return SA_MENU

async def sa_funksiya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    komp_id = context.user_data.get('sa_komp_id')
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    komp = kompaniya_olish(komp_id)
    funksiya_map = {
        "📍 GPS":               ("gps_aktiv", komp[9]),
        "📡 GPS Live":          ("live_gps_aktiv", komp[14]),
        "⏱ 30-daqiqa tekshiruv": ("live_gps_tekshiruv", komp[15]),
        "🤳 Selfie":            ("selfie_aktiv", komp[10]),
        "👤 Face ID":           ("face_id_aktiv", komp[11]),
        "📷 Hikvision":         ("hikvision_aktiv", komp[12]),
        "📡 WiFi":     ("wifi_aktiv", komp[16]),
    }
    if matn in funksiya_map:
        maydon, hozirgi = funksiya_map[matn]
        kompaniya_funksiya_ozgartir(komp_id, maydon, not hozirgi)
        komp = kompaniya_olish(komp_id)
        await update.message.reply_text(
            f"⚙️ *{komp[1]}* funksiyalari:\n\n"
            f"📍 GPS (oddiy): {'✅' if komp[9] else '❌'}\n"
            f"📡 GPS Live: {'✅' if komp[14] else '❌'}\n"
            f"⏱ 30-daqiqa tekshiruv: {'✅' if komp[15] else '❌'}\n"
            f"🤳 Selfie: {'✅' if komp[10] else '❌'}\n"
            f"👤 Face ID: {'✅' if komp[11] else '❌'}\n"
            f"📷 Hikvision: {'✅' if komp[12] else '❌'}\n"
            f"📡 WiFi: {'✅' if komp[16] else '❌'}",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["📍 GPS", "📡 GPS Live"],
                ["⏱ 30-daqiqa tekshiruv", "🤳 Selfie"],
                ["👤 Face ID", "📷 Hikvision"],
                ["📡 WiFi", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_FUNKSIYA
    return SA_FUNKSIYA

async def sa_komp_xodim_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    komp_id = context.user_data.get('sa_komp_id')
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    if matn == "➕ Xodim qo'shish":
        await update.message.reply_text("👤 Xodim ismini kiriting:", reply_markup=ReplyKeyboardRemove())
        return ADM_XODIM_ISM
    try:
        xodim_id = int(matn.split(".")[0].strip())
        context.user_data['tahrir_xodim_id'] = xodim_id
        x = xodim_olish(xodim_id)
        await update.message.reply_text(
            f"👤 *{x[1]}*\n💼 {x[3]} | 🎭 {x[7]}\n🔐 Kod: `{x[8]}`\n\nNima qilish?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["✏️ Tahrirlash", "🗑 O'chirish"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_KOMP_XODIM_AMAL
    except:
        return SA_KOMP_XODIM_TANLASH

async def sa_komp_xodim_amal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    xodim_id = context.user_data.get('tahrir_xodim_id')
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    elif matn == "🗑 O'chirish":
        komp_id = context.user_data.get('sa_komp_id')
        x = xodim_olish(xodim_id)
        xodim_ism = x[1] if x else 'Unknown'
        xodim_ochirish(xodim_id)

        # AUDIT LOG
        user_id = update.effective_user.id
        user_ism = update.effective_user.first_name or 'Super Admin'
        tafsilot = f"Xodim o'chirildi: {xodim_ism}"
        audit_log_qoshish(komp_id, 'XODIM_O\'CHIRISH', tafsilot, xodim_id, user_id=user_id, user_ism=user_ism)

        await update.message.reply_text("🗑 Xodim o'chirildi!", reply_markup=sa_menu_kb())
        return SA_MENU
    elif matn == "✏️ Tahrirlash":
        await update.message.reply_text("Nimani tahrirlash?",
            reply_markup=ReplyKeyboardMarkup([
                ["📝 Ism", "💼 Lavozim"],
                ["💰 Oylik", "⏰ Ish vaqti"],
                ["🎭 Rol", "🔑 Kod"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_KOMP_XODIM_TAHRIR
    return SA_KOMP_XODIM_AMAL

async def sa_komp_xodim_tahrir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    maydon_map = {"📝 Ism": "ism", "💼 Lavozim": "lavozim", "💰 Oylik": "oylik", "🎭 Rol": "rol", "🔑 Kod": "kod"}
    if matn in maydon_map:
        context.user_data['tahrir_maydon'] = maydon_map[matn]
        await update.message.reply_text(f"Yangi {matn}:", reply_markup=ReplyKeyboardRemove())
        context.user_data['tahrir_qaytish'] = 'sa'
        return ADM_XODIM_TAHRIR_Q
    elif matn == "⏰ Ish vaqti":
        context.user_data['tahrir_maydon'] = 'ish_boshlanish'
        await update.message.reply_text("Ish boshlanish (09:00):", reply_markup=ReplyKeyboardRemove())
        context.user_data['tahrir_qaytish'] = 'sa'
        return ADM_XODIM_TAHRIR_Q
    return SA_KOMP_XODIM_TAHRIR

async def sa_adm_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    user_id = update.effective_user.id
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    elif matn == "➕ Admin qo'shish":
        await update.message.reply_text("📱 Yangi Super Admin telefon raqami:", reply_markup=ReplyKeyboardRemove())
        return SA_ADM_QOSH_TEL
    elif matn == "❌ Admin o'chirish":
        adminlar = barcha_super_adminlar()
        if len(adminlar) <= 1:
            await update.message.reply_text("❌ Kamida 1 ta Super Admin bo'lishi kerak!")
            return SA_ADM_LIST
        tugmalar = [[f"ID:{a[0]} | {a[3]} | {a[1]}"] for a in adminlar if a[2] != user_id]
        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text("O'chirish uchun tanlang:",
            reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        context.user_data['sa_amal'] = 'ochir'
        return SA_ADM_LIST
    elif matn == "✏️ Mening ma'lumotlarim":
        sa = super_admin_olish(user_id)
        await update.message.reply_text(
            f"👤 Ism: {sa[2]}\n📱 Telefon: {sa[1]}\n\nNimani o'zgartirish?",
            reply_markup=ReplyKeyboardMarkup([
                ["📱 Telefonni o'zgartirish", "👤 Ismni o'zgartirish"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        context.user_data['sa_amal'] = 'mening'
        return SA_ADM_LIST
    elif context.user_data.get('sa_amal') == 'ochir':
        try:
            sa_id = int(matn.split("ID:")[1].split("|")[0].strip())
            super_admin_ochirish(sa_id)
            await update.message.reply_text("✅ Admin o'chirildi!", reply_markup=sa_menu_kb())
            context.user_data.pop('sa_amal', None)
            return SA_MENU
        except:
            return SA_ADM_LIST
    elif context.user_data.get('sa_amal') == 'mening':
        if matn == "📱 Telefonni o'zgartirish":
            await update.message.reply_text("Yangi telefon:", reply_markup=ReplyKeyboardRemove())
            context.user_data['sa_tahrir'] = 'telefon'; return SA_ADM_LIST
        elif matn == "👤 Ismni o'zgartirish":
            await update.message.reply_text("Yangi ism:", reply_markup=ReplyKeyboardRemove())
            context.user_data['sa_tahrir'] = 'ism'; return SA_ADM_LIST
        elif context.user_data.get('sa_tahrir') == 'telefon':
            super_admin_telefon_ozgartir(user_id, matn.strip())
            await update.message.reply_text("✅ Telefon o'zgartirildi!", reply_markup=sa_menu_kb())
            context.user_data.pop('sa_amal', None); context.user_data.pop('sa_tahrir', None)
            return SA_MENU
        elif context.user_data.get('sa_tahrir') == 'ism':
            super_admin_ism_ozgartir(user_id, matn.strip())
            await update.message.reply_text("✅ Ism o'zgartirildi!", reply_markup=sa_menu_kb())
            context.user_data.pop('sa_amal', None); context.user_data.pop('sa_tahrir', None)
            return SA_MENU
    return SA_ADM_LIST

async def sa_adm_qosh_tel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['yangi_sa_tel'] = update.message.text.strip()
    await update.message.reply_text("👤 Ism kiriting:")
    return SA_ADM_QOSH_ISM

async def sa_adm_qosh_ism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ism = update.message.text.strip()
    telefon = context.user_data.get('yangi_sa_tel')
    if super_admin_qoshish(telefon, ism):
        await update.message.reply_text(f"✅ Super Admin qo'shildi!\n👤 {ism}\n📱 {telefon}", reply_markup=sa_menu_kb())
    else:
        await update.message.reply_text("⚠️ Bu telefon allaqachon Super Admin!", reply_markup=sa_menu_kb())
    return SA_MENU

async def sa_soz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    user_id = update.effective_user.id
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    elif matn == "🔑 Kodni o'zgartirish":
        await update.message.reply_text("Yangi Super Admin kodini kiriting:", reply_markup=ReplyKeyboardRemove())
        context.user_data['soz_amal'] = 'kod'; return SA_SOZ_MENU
    elif matn == "📱 Telefon o'zgartirish":
        await update.message.reply_text("Yangi telefon raqamini kiriting:", reply_markup=ReplyKeyboardRemove())
        context.user_data['soz_amal'] = 'telefon'; return SA_SOZ_MENU
    elif matn == "👤 Ism o'zgartirish":
        await update.message.reply_text("Yangi ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())
        context.user_data['soz_amal'] = 'ism'; return SA_SOZ_MENU
    elif matn == "📞 Murojaat raqami":
        await update.message.reply_text("Yangi murojaat raqamini kiriting (masalan: 919712222):", reply_markup=ReplyKeyboardRemove())
        context.user_data['soz_amal'] = 'murojaat'; return SA_SOZ_MENU
    elif context.user_data.get('soz_amal') == 'kod':
        super_admin_kod_ozgartir(matn.strip())
        await update.message.reply_text(f"✅ Kod o'zgartirildi: `{matn.strip()}`", parse_mode='Markdown', reply_markup=sa_menu_kb())
        context.user_data.pop('soz_amal', None); return SA_MENU
    elif context.user_data.get('soz_amal') == 'telefon':
        super_admin_telefon_ozgartir(user_id, matn.strip())
        await update.message.reply_text("✅ Telefon o'zgartirildi!", reply_markup=sa_menu_kb())
        context.user_data.pop('soz_amal', None); return SA_MENU
    elif context.user_data.get('soz_amal') == 'ism':
        super_admin_ism_ozgartir(user_id, matn.strip())
        await update.message.reply_text("✅ Ism o'zgartirildi!", reply_markup=sa_menu_kb())
        context.user_data.pop('soz_amal', None); return SA_MENU
    elif context.user_data.get('soz_amal') == 'murojaat':
        set_murojaat_raqam(matn.strip())
        await update.message.reply_text(f"✅ Murojaat raqami o'zgartirildi: {matn.strip()}", reply_markup=sa_menu_kb())
        context.user_data.pop('soz_amal', None); return SA_MENU
    return SA_SOZ_MENU

# ==================== ADMIN PANEL ====================

async def adm_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    user_id = update.effective_user.id
    komp_id = context.user_data.get('komp_id')
    if not komp_id:
        conn = connect(); cur = conn.cursor()
        cur.execute("SELECT id FROM kompaniyalar WHERE admin_id=%s", (user_id,))
        row = cur.fetchone(); cur.close(); conn.close()
        if row: komp_id = row[0]; context.user_data['komp_id'] = komp_id

    komp = kompaniya_olish(komp_id)
    if not komp or komp[4] != 'faol':
        await update.message.reply_text("⛔️ Kompaniyangiz faol emas!")
        return ConversationHandler.END

    if matn == "👥 Xodimlar":
        await update.message.reply_text("👥 Xodimlar:",
            reply_markup=ReplyKeyboardMarkup([
                ["➕ Qo'shish", "📋 Ro'yxat"],
                ["✏️ Tahrirlash", "🗑 O'chirish"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return ADM_XODIM_LIST

    elif matn == "📅 Davomat":
        await update.message.reply_text("📅 Davomat:",
            reply_markup=ReplyKeyboardMarkup([
                ["📋 Bugungi", "📊 Barchasi"],
                ["✍️ Kiritish", "✏️ Tahrirlash"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return ADM_DAV_MENU

    elif matn == "📊 Hisobot":
        await update.message.reply_text(
            "📅 Qaysi kun uchun hisobot? (YYYY-MM-DD)\n\n"
            "Masalan: 2026-05-24",
            reply_markup=ReplyKeyboardRemove())
        return ADM_HISOBOT_SANA

    elif matn == "📍 GPS sozlash":
        lat, lon, radius = get_gps(komp_id)
        btn = [[KeyboardButton("📍 Joriy lokatsiya yuborish", request_location=True)]]
        await update.message.reply_text(
            f"📍 *GPS sozlamalari:*\n\n📌 {lat}, {lon}\n📏 Radius: {radius}m\n\nYangi lokatsiya yuboring:",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
        return ADM_GPS_LOK

    elif matn == "📡 WiFi sozlash":
        wifi_aktiv, wifi_ssid, _ = get_wifi(komp_id)
        macs = wifi_mac_olish(komp_id)
        holat = "✅ YONIQ" if wifi_aktiv else "❌ OCHIQ"

        mac_list = "📡 *WiFi MAC Manzillari:*\n"
        if macs:
            for i, (mac_id, mac, nomi) in enumerate(macs, 1):
                mac_list += f"{i}. {mac} {f'({nomi})' if nomi else ''}\n"
        else:
            mac_list += "(hech qanday MAC yo'q)\n"

        await update.message.reply_text(
            f"📡 *WiFi Sozlamalari*\n\n"
            f"Holati: {holat}\n"
            f"📡 SSID: {wifi_ssid if wifi_ssid else '(belgilanmagan)'}\n\n"
            f"{mac_list}\n"
            f"Qanday qilish kerak?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["✅ Yoqish", "❌ O'chirish"],
                ["✏️ SSID o'zgartirish", "➕ MAC qo'shish"],
                ["📋 MAC ro'yxati", "🔙 Orqaga"]
            ], resize_keyboard=True))
        context.user_data['wifi_macs'] = macs
        return ADM_WIFI_AKTIV

    elif matn == "📋 Audit Log":
        komp_id = context.user_data.get('komp_id')
        logs = audit_log_olish(komp_id, limit=15)
        if not logs:
            await update.message.reply_text("📋 Hozircha audit log yo'q.",
                reply_markup=ReplyKeyboardMarkup([["📥 Export Excel", "🔙 Orqaga"]], resize_keyboard=True))
        else:
            xabar = "📋 *OXIRGI 15 AMAL:*\n\n"
            for log in logs:
                xodim_id, amal, tafsilot, vaqt, rasm_id, video_id, user_ism = log
                xabar += f"📌 {amal} | {vaqt}\n"
                xabar += f"👤 {user_ism}\n"
                xabar += f"📝 {tafsilot}\n━━━━━━━━━━━━\n"
            await update.message.reply_text(xabar, parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup([["📥 Export Excel", "🔙 Orqaga"]], resize_keyboard=True))
        context.user_data['audit_view'] = 'adm'
        return ADM_MENU

    elif matn == "📸 Rasm log":
        komp_id = context.user_data.get('komp_id')
        rasmlar = komp_bugun_rasmlar(komp_id)
        if not rasmlar:
            await update.message.reply_text(
                "📸 Bugun rasmlar yo'q.",
                reply_markup=adm_menu_kb())
            return ADM_MENU

        await update.message.reply_text(
            f"📸 *Bugungi rasmlar* ({len(rasmlar)}ta):\n\n"
            "Rasmlar yuborilmoqda...",
            parse_mode='Markdown')

        for xodim_id, ism, lavozim, vaqt, rasm_id, tafsilot in rasmlar:
            try:
                caption = f"👤 *{ism}*\n💼 {lavozim}\n⏰ {vaqt}"
                if tafsilot:
                    caption += f"\n✅ {tafsilot}"
                await update.message.reply_photo(
                    rasm_id,
                    caption=caption,
                    parse_mode='Markdown')
            except:
                pass

        await update.message.reply_text("✅ Tayyor!", reply_markup=adm_menu_kb())
        return ADM_MENU

    elif matn == "📥 Export Excel" and context.user_data.get('audit_view') == 'adm':
        komp_id = context.user_data.get('komp_id')
        await update.message.reply_text("⏳ Excel tayyorlanmoqda...")
        try:
            fayl = export_audit_log_excel(komp_id)
            with open(fayl, 'rb') as f:
                await update.message.reply_document(f, filename=fayl)
            os.remove(fayl)
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}")
        context.user_data.pop('audit_view', None)
        return ADM_MENU

    elif matn == "🏠 Bosh menu":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU

    return ADM_MENU

async def adm_gps_lok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    komp_id = context.user_data.get('komp_id')
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        kompaniya_tahrirlash(komp_id, 'gps_lat', lat)
        kompaniya_tahrirlash(komp_id, 'gps_lon', lon)
        await update.message.reply_text(f"✅ GPS saqlandi: {lat}, {lon}\n\n📏 Ruxsat etilgan radius (metrda):", reply_markup=ReplyKeyboardRemove())
        return ADM_GPS_RADIUS
    await update.message.reply_text("❌ Lokatsiya yuboring!")
    return ADM_GPS_LOK

async def adm_gps_radius(update: Update, context: ContextTypes.DEFAULT_TYPE):
    komp_id = context.user_data.get('komp_id')
    try:
        radius = int(update.message.text.strip())
        kompaniya_tahrirlash(komp_id, 'gps_radius', radius)
        await update.message.reply_text(f"✅ GPS sozlandi! Radius: {radius}m", reply_markup=adm_menu_kb())
        return ADM_MENU
    except:
        await update.message.reply_text("❌ Raqam kiriting:")
        return ADM_GPS_RADIUS

async def adm_xodim_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    komp_id = context.user_data.get('komp_id')
    if matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU
    elif matn == "📋 Ro'yxat":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("👥 Xodimlar yo'q.")
        else:
            xabar = "👥 *Xodimlar ro'yxati:*\n\n"
            for x in xodimlar:
                xabar += f"• *{x[1]}* — {x[2]}\n  📞 {x[3]} | 💰 {x[4]:,.0f} | 🎭 {x[7]}\n  ⏰ {x[5]}-{x[6]} | 🔐 `{x[8]}`\n\n"
            await update.message.reply_text(xabar, parse_mode='Markdown')
        return ADM_XODIM_LIST
    elif matn == "➕ Qo'shish":
        await update.message.reply_text("👤 Xodim ismini kiriting:", reply_markup=ReplyKeyboardRemove())
        return ADM_XODIM_ISM
    elif matn in ("✏️ Tahrirlash", "🗑 O'chirish"):
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!")
            return ADM_XODIM_LIST
        context.user_data['xodim_amal'] = 'tahrir' if matn == "✏️ Tahrirlash" else 'ochir'
        tugmalar = [[f"{x[0]}. {x[1]}"] for x in xodimlar]
        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text("Xodim tanlang:", reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return ADM_XODIM_TANLASH
    return ADM_XODIM_LIST

async def adm_xodim_ism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_ism'] = update.message.text.strip()
    btn = [[KeyboardButton("📱 Telefon yuborish", request_contact=True)]]
    await update.message.reply_text("📞 Telefon:", reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
    return ADM_XODIM_TEL

async def adm_xodim_tel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_tel'] = update.message.contact.phone_number if update.message.contact else update.message.text.strip()
    await update.message.reply_text("💼 Lavozim:", reply_markup=ReplyKeyboardRemove())
    return ADM_XODIM_LAV

async def adm_xodim_lav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_lav'] = update.message.text.strip()
    await update.message.reply_text("💰 Oylik (so'm):")
    return ADM_XODIM_OYLIK

async def adm_xodim_oylik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: context.user_data['y_oylik'] = float(update.message.text.strip().replace(',','').replace(' ',''))
    except: context.user_data['y_oylik'] = 0
    await update.message.reply_text("⏰ Ish boshlanish (09:00):")
    return ADM_XODIM_BOSH

async def adm_xodim_bosh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_bosh'] = update.message.text.strip()
    await update.message.reply_text("⏰ Ish tugash (18:00):")
    return ADM_XODIM_TUG

async def adm_xodim_tug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_tug'] = update.message.text.strip()
    await update.message.reply_text("🎭 Rol:", reply_markup=ReplyKeyboardMarkup([["xodim", "hr"]], resize_keyboard=True, one_time_keyboard=True))
    return ADM_XODIM_ROL

async def adm_xodim_rol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rol = update.message.text.strip().lower()
    if rol not in ('xodim', 'hr'):
        await update.message.reply_text("❌ xodim yoki hr tanlang!")
        return ADM_XODIM_ROL
    komp_id = context.user_data.get('komp_id')
    kod = random_kod()
    xodim_id = xodim_qoshish(context.user_data['y_ism'], context.user_data['y_tel'],
                  context.user_data['y_lav'], context.user_data['y_oylik'],
                  context.user_data['y_bosh'], context.user_data['y_tug'],
                  komp_id, rol, kod)

    # AUDIT LOG
    user_id = update.effective_user.id
    user_ism = update.effective_user.first_name or 'Admin'
    tafsilot = f"Yangi xodim: {context.user_data['y_ism']} | Tel: {context.user_data['y_tel']} | Rol: {rol}"
    audit_log_qoshish(komp_id, 'XODIM_QO\'SHISH', tafsilot, xodim_id, user_id=user_id, user_ism=user_ism)

    await update.message.reply_text(
        f"✅ *Xodim qo'shildi!*\n\n👤 {context.user_data['y_ism']}\n"
        f"💼 {context.user_data['y_lav']}\n🎭 {rol}\n🔑 Kod: `{kod}`\n\n⚠️ Kodni xodimga bering!",
        parse_mode='Markdown', reply_markup=adm_menu_kb())
    return ADM_MENU

async def adm_xodim_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU
    try:
        xodim_id = int(matn.split(".")[0].strip())
        context.user_data['tahrir_xodim_id'] = xodim_id
        amal = context.user_data.get('xodim_amal')
        if amal == 'ochir':
            komp_id = context.user_data.get('komp_id')
            x = xodim_olish(xodim_id)
            xodim_ism = x[1] if x else 'Unknown'
            xodim_ochirish(xodim_id)

            # AUDIT LOG
            user_id = update.effective_user.id
            user_ism = update.effective_user.first_name or 'Admin'
            tafsilot = f"Xodim o'chirildi: {xodim_ism}"
            audit_log_qoshish(komp_id, 'XODIM_O\'CHIRISH', tafsilot, xodim_id, user_id=user_id, user_ism=user_ism)

            await update.message.reply_text("🗑 Xodim o'chirildi!", reply_markup=adm_menu_kb())
            return ADM_MENU
        x = xodim_olish(xodim_id)
        await update.message.reply_text(
            f"✏️ *{x[1]}*\n💼 {x[3]} | 🎭 {x[7]}\n🔐 `{x[8]}`\n\nNimani tahrirlash?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["📝 Ism", "💼 Lavozim"],
                ["💰 Oylik", "⏰ Ish vaqti"],
                ["🎭 Rol", "🔑 Kod"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return ADM_XODIM_TAHRIR
    except:
        return ADM_XODIM_TANLASH

async def adm_xodim_tahrir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU
    maydon_map = {"📝 Ism": "ism", "💼 Lavozim": "lavozim", "💰 Oylik": "oylik", "🎭 Rol": "rol", "🔑 Kod": "kod"}
    if matn in maydon_map:
        context.user_data['tahrir_maydon'] = maydon_map[matn]
        context.user_data['tahrir_qaytish'] = 'adm'
        await update.message.reply_text(f"Yangi {matn}:", reply_markup=ReplyKeyboardRemove())
        return ADM_XODIM_TAHRIR_Q
    elif matn == "⏰ Ish vaqti":
        context.user_data['tahrir_maydon'] = 'ish_boshlanish'
        context.user_data['tahrir_qaytish'] = 'adm'
        await update.message.reply_text("Ish boshlanish (09:00):", reply_markup=ReplyKeyboardRemove())
        return ADM_XODIM_TAHRIR_Q
    return ADM_XODIM_TAHRIR

async def adm_xodim_tahrir_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qiymat = update.message.text.strip()
    xodim_id = context.user_data.get('tahrir_xodim_id')
    maydon = context.user_data.get('tahrir_maydon')
    xodim_tahrirlash(xodim_id, maydon, qiymat)
    qaytish = context.user_data.get('tahrir_qaytish', 'adm')
    if qaytish == 'sa':
        await update.message.reply_text("✅ Saqlandi!", reply_markup=sa_menu_kb())
        return SA_MENU
    await update.message.reply_text("✅ Saqlandi!", reply_markup=adm_menu_kb())
    return ADM_MENU

async def adm_dav_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    komp_id = context.user_data.get('komp_id')
    if matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU
    elif matn == "📋 Bugungi":
        bugun = hozir().strftime("%Y-%m-%d")
        davomatlar = kompaniya_davomati(komp_id, bugun)
        if not davomatlar:
            await update.message.reply_text(f"📋 Bugun ({bugun}) davomat yo'q.")
        else:
            xabar = f"📋 *Bugungi davomat ({bugun}):*\n\n"
            for d in davomatlar:
                xabar += f"👤 {d[0]}: {d[2] or '—'} → {d[3] or '—'}"
                if d[5] and d[5] > 0: xabar += f" ⚠️{kechikish_format(d[5])}"
                xabar += "\n"
            await update.message.reply_text(xabar, parse_mode='Markdown')
        return ADM_DAV_MENU
    elif matn == "📊 Barchasi":
        davomatlar = kompaniya_davomati(komp_id)
        if not davomatlar:
            await update.message.reply_text("📊 Davomat yo'q.")
        else:
            xabar = "📊 *Barcha davomat:*\n\n"
            for d in davomatlar[:20]:
                xabar += f"👤 {d[0]} | 📅 {d[1]}: {d[2] or '—'} → {d[3] or '—'}\n"
            if len(davomatlar) > 20: xabar += f"\n... va yana {len(davomatlar)-20} ta"
            await update.message.reply_text(xabar, parse_mode='Markdown')
        return ADM_DAV_MENU
    elif matn == "✍️ Kiritish":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!"); return ADM_DAV_MENU
        tugmalar = [[f"{x[0]}. {x[1]}"] for x in xodimlar]
        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text("Xodim tanlang:", reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        context.user_data['dav_amal'] = 'kiritish'; return ADM_DAV_XODIM
    elif matn == "✏️ Tahrirlash":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!"); return ADM_DAV_MENU
        tugmalar = [[f"{x[0]}. {x[1]}"] for x in xodimlar]
        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text("Xodim tanlang:", reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        context.user_data['dav_amal'] = 'tahrirlash'; return ADM_DAV_XODIM
    return ADM_DAV_MENU

async def adm_dav_xodim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("📅 Davomat:", reply_markup=ReplyKeyboardMarkup([
            ["📋 Bugungi","📊 Barchasi"],["✍️ Kiritish","✏️ Tahrirlash"],["🔙 Orqaga"]
        ], resize_keyboard=True))
        return ADM_DAV_MENU
    try:
        xodim_id = int(matn.split(".")[0].strip())
        context.user_data['dav_xodim_id'] = xodim_id
        if context.user_data.get('dav_amal') == 'tahrirlash':
            davomatlar = xodim_davomati(xodim_id)
            if not davomatlar:
                await update.message.reply_text("❌ Davomat yo'q!"); return ADM_DAV_MENU
            xabar = "📋 *Davomat:*\n\n"
            tugmalar = []
            for d in davomatlar[:15]:
                xabar += f"`{d[0]}` | {d[1]}: {d[2] or '—'}→{d[3] or '—'}\n"
                tugmalar.append([f"ID:{d[0]} | {d[1]}"])
            tugmalar.append(["🔙 Orqaga"])
            await update.message.reply_text(xabar, parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
            return ADM_DAV_TAHRIR_TANLASH
        await update.message.reply_text("📅 Sana kiriting (YYYY-MM-DD):", reply_markup=ReplyKeyboardRemove())
        return ADM_DAV_SANA
    except: return ADM_DAV_XODIM

async def adm_dav_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dav_sana'] = update.message.text.strip()
    await update.message.reply_text("⏰ Keldi vaqti (09:00):")
    return ADM_DAV_KELDI

async def adm_dav_keldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dav_keldi'] = update.message.text.strip()
    await update.message.reply_text("⏰ Ketdi vaqti (18:00):")
    return ADM_DAV_KETDI

async def adm_dav_ketdi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dav_ketdi'] = update.message.text.strip()
    await update.message.reply_text("📋 Holat:", reply_markup=ReplyKeyboardMarkup([
        ["normal","sababli"],["kasal","ta'til"]], resize_keyboard=True, one_time_keyboard=True))
    return ADM_DAV_HOLAT

async def adm_dav_holat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dav_holat'] = update.message.text.strip()
    await update.message.reply_text("📝 Izoh (yoki - kiriting):", reply_markup=ReplyKeyboardRemove())
    return ADM_DAV_IZOH

async def adm_dav_izoh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    izoh = update.message.text.strip()
    if izoh == '-': izoh = ''
    xodim_id = context.user_data['dav_xodim_id']
    komp_id = context.user_data['komp_id']
    xodim = xodim_olish(xodim_id)
    natija = manual_davomat(xodim_id, komp_id, context.user_data['dav_sana'],
        context.user_data['dav_keldi'], context.user_data['dav_ketdi'],
        context.user_data['dav_holat'], izoh, xodim[1] if xodim else 'Admin', update.effective_user.id)
    await update.message.reply_text(natija, reply_markup=adm_menu_kb())
    return ADM_MENU

async def adm_dav_tahrir_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU
    try:
        dav_id = int(matn.split("ID:")[1].split("|")[0].strip())
        context.user_data['dav_id'] = dav_id
        await update.message.reply_text("Nimani tahrirlash?", reply_markup=ReplyKeyboardMarkup([
            ["⏰ Keldi vaqti","⏰ Ketdi vaqti"],["📋 Holat","📝 Izoh"],["🔙 Orqaga"]
        ], resize_keyboard=True))
        return ADM_DAV_TAHRIR_AMAL
    except: return ADM_DAV_TAHRIR_TANLASH

async def adm_dav_tahrir_amal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU
    maydon_map = {"⏰ Keldi vaqti":"keldi","⏰ Ketdi vaqti":"ketdi","📋 Holat":"holat","📝 Izoh":"izoh"}
    if matn in maydon_map:
        context.user_data['dav_tahrir_maydon'] = maydon_map[matn]
        await update.message.reply_text(f"Yangi {matn}:", reply_markup=ReplyKeyboardRemove())
        return ADM_DAV_TAHRIR_Q
    return ADM_DAV_TAHRIR_AMAL

async def adm_dav_tahrir_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    davomat_tahrirlash(context.user_data.get('dav_id'), context.user_data.get('dav_tahrir_maydon'), update.message.text.strip())
    await update.message.reply_text("✅ Davomat yangilandi!", reply_markup=adm_menu_kb())
    return ADM_MENU

# ==================== ADMIN DAILY REPORT ====================

async def adm_hisobot_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sana = update.message.text.strip()
    try:
        datetime.strptime(sana, "%Y-%m-%d")
        context.user_data['hisobot_sana'] = sana
        komp_id = context.user_data.get('komp_id')
        conn = connect(); cur = conn.cursor()
        cur.execute('''SELECT x.id,x.ism,x.lavozim,d.keldi,d.ketdi,d.ish_soat,d.kechikish,d.keldi_rasm,d.ketdi_rasm
                      FROM xodimlar x LEFT JOIN davomat d ON x.id=d.xodim_id AND d.sana=%s
                      WHERE x.kompaniya_id=%s ORDER BY x.ism''', (sana, komp_id))
        davomatlar = cur.fetchall(); cur.close(); conn.close()

        context.user_data['davomatlar'] = davomatlar
        context.user_data['dav_index'] = 0
        await adm_hisobot_kun_display(update, context)
        return ADM_HISOBOT_KUN
    except ValueError:
        await update.message.reply_text("❌ Format xato! (YYYY-MM-DD)")
        return ADM_HISOBOT_SANA

async def adm_hisobot_kun_display(update: Update, context: ContextTypes.DEFAULT_TYPE):
    davomatlar = context.user_data.get('davomatlar', [])
    sana = context.user_data.get('hisobot_sana')

    if not davomatlar:
        await update.message.reply_text(
            f"📅 {sana}\n❌ Bu kun ma'lumot yo'q!",
            reply_markup=adm_menu_kb())
        return ADM_MENU

    xabar = f"📊 *{sana} KUNINING HISOBOTI*\n━━━━━━━━━━━━━━━\n\n"

    for i, dav in enumerate(davomatlar, 1):
        xodim_id, ism, lavozim, keldi, ketdi, ish_soat, kechikish, rasm_keldi, rasm_ketdi = dav
        s = int(float(ish_soat or 0)); d = int((float(ish_soat or 0) - s) * 60)
        kech = kechikish_format(int(kechikish or 0))

        xabar += (f"{i}. 👤 *{ism}* ({lavozim})\n"
                  f"   📍 Keldi: {keldi or '—'}\n"
                  f"   📍 Ketdi: {ketdi or '—'}\n"
                  f"   ⏱ Ish: {s}s {d}d | ⚠️ {kech}\n\n")

    await update.message.reply_text(xabar, parse_mode='Markdown')

    # Rasmlarni alohida yubor
    for i, dav in enumerate(davomatlar, 1):
        xodim_id, ism, lavozim, keldi, ketdi, ish_soat, kechikish, rasm_keldi, rasm_ketdi = dav
        if rasm_keldi or rasm_ketdi:
            await update.message.reply_text(f"{i}. {ism} - Rasmlar:", parse_mode='Markdown')
            if rasm_keldi:
                try:
                    await context.bot.send_photo(update.effective_chat.id, rasm_keldi, caption="📸 Keldi")
                except:
                    pass
            if rasm_ketdi:
                try:
                    await context.bot.send_photo(update.effective_chat.id, rasm_ketdi, caption="📸 Ketdi")
                except:
                    pass

    await update.message.reply_text("✅ Hisobot yakunlandi!", reply_markup=adm_menu_kb())
    return ADM_MENU

# ==================== ADMIN WiFi SETTINGS ====================

async def adm_wifi_aktiv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """WiFi IP Adres yoq/on"""
    komp_id = context.user_data.get('komp_id')
    matn = update.message.text.strip()

    if matn == "✅ Yoqish":
        wifi_aktiv, wifi_ssid, wifi_mac = get_wifi(komp_id)
        if not wifi_ssid or not wifi_mac:
            await update.message.reply_text(
                "📡 WiFi nomini kiriting (SSID):\n\n"
                "Masalan: GIGAND_OFFICE",
                reply_markup=ReplyKeyboardRemove())
            context.user_data['wifi_step'] = 'ssid'
            return ADM_WIFI_SSID
        wifi_sozla(komp_id, True, wifi_ssid, wifi_mac)
        await update.message.reply_text(
            f"✅ WiFi yoqildi!\n📡 SSID: {wifi_ssid}\n🔗 MAC: {wifi_mac}",
            reply_markup=adm_menu_kb())
        return ADM_MENU

    elif matn == "❌ O'chirish":
        wifi_sozla(komp_id, False, "", "")
        await update.message.reply_text("✅ WiFi o'chirildi!", reply_markup=adm_menu_kb())
        return ADM_MENU

    elif matn == "✏️ SSID nomini o'zgartirish":
        await update.message.reply_text(
            "📡 Yangi WiFi nomini kiriting (SSID):\n\n"
            "Masalan: 112233",
            reply_markup=ReplyKeyboardRemove())
        context.user_data['wifi_step'] = 'ssid'
        return ADM_WIFI_SSID

    elif matn == "✏️ MAC manzilini o'zgartirish":
        await update.message.reply_text(
            "🔗 Yangi MAC manzilini kiriting:\n\n"
            "Masalan: 00:1A:2B:3C:4D:5E",
            reply_markup=ReplyKeyboardRemove())
        context.user_data['wifi_step'] = 'mac'
        return ADM_WIFI_SSID

    elif matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU

    return ADM_WIFI_AKTIV

async def adm_wifi_ssid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """WiFi SSID va IP address o'rnatish"""
    komp_id = context.user_data.get('komp_id')
    wifi_step = context.user_data.get('wifi_step', 'ssid')
    matn = update.message.text.strip()

    if wifi_step == 'ssid':
        if not matn or len(matn) < 2:
            await update.message.reply_text("❌ Haqiqiy WiFi nomini kiriting!")
            return ADM_WIFI_SSID

        context.user_data['temp_wifi_ssid'] = matn
        context.user_data['wifi_step'] = 'mac'
        await update.message.reply_text(
            "🔗 Endi WiFi MAC manzilini kiriting:\n\n"
            "Masalan: 00:1A:2B:3C:4D:5E",
            reply_markup=ReplyKeyboardRemove())
        return ADM_WIFI_SSID

    elif wifi_step == 'mac':
        if not matn or len(matn) < 17:
            await update.message.reply_text("❌ Haqiqiy MAC manzilini kiriting! (Format: 00:1A:2B:3C:4D:5E)")
            return ADM_WIFI_SSID

        wifi_aktiv, wifi_ssid, _ = get_wifi(komp_id)

        # Agar temp SSID mavjud bo'lsa (yangi setup) uni ishlatsin, yoki mavjud SSIDni saqlasin (MAC tahrirlash)
        ssid = context.user_data.get('temp_wifi_ssid', '') or wifi_ssid

        wifi_sozla(komp_id, wifi_aktiv or True, ssid, matn)

        await update.message.reply_text(
            f"✅ WiFi saqlandi!\n📡 SSID: {ssid}\n🔗 MAC: {matn}\n"
            f"Holati: {'✅ YONIQ' if wifi_aktiv else '✅ YOQILDI'}",
            reply_markup=adm_menu_kb())
        context.user_data.pop('temp_wifi_ssid', None)
        context.user_data.pop('wifi_step', None)
    return ADM_MENU

# ==================== HR PANEL ====================

async def hr_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    komp_id = context.user_data.get('komp_id')
    if matn == "✍️ Manual davomat":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!"); return HR_MENU
        tugmalar = [[f"{x[0]}. {x[1]}"] for x in xodimlar]
        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text("Xodim tanlang:", reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return HR_MAN_XODIM
    elif matn == "📊 Hisobot":
        await update.message.reply_text("⏳ Hisobot tayyorlanmoqda...")
        try:
            fayl = kompaniya_hisobot(komp_id)
            if fayl:
                with open(fayl, 'rb') as f:
                    await update.message.reply_document(f, filename=fayl)
                os.remove(fayl)
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}")
        return HR_MENU
    elif matn == "🏠 Bosh menu":
        await update.message.reply_text("👔 HR menu:", reply_markup=hr_menu_kb())
        return HR_MENU
    return HR_MENU

async def hr_man_xodim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👔 HR menu:", reply_markup=hr_menu_kb())
        return HR_MENU
    try:
        xodim_id = int(matn.split(".")[0].strip())
        context.user_data['dav_xodim_id'] = xodim_id
        await update.message.reply_text("📅 Sana (YYYY-MM-DD):", reply_markup=ReplyKeyboardRemove())
        return HR_MAN_SANA
    except: return HR_MAN_XODIM

async def hr_man_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dav_sana'] = update.message.text.strip()
    await update.message.reply_text("⏰ Keldi vaqti (09:00):")
    return HR_MAN_KELDI

async def hr_man_keldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dav_keldi'] = update.message.text.strip()
    await update.message.reply_text("⏰ Ketdi vaqti (18:00):")
    return HR_MAN_KETDI

async def hr_man_ketdi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dav_ketdi'] = update.message.text.strip()
    await update.message.reply_text("📋 Holat:", reply_markup=ReplyKeyboardMarkup([
        ["normal","sababli"],["kasal","ta'til"]], resize_keyboard=True, one_time_keyboard=True))
    return HR_MAN_HOLAT

async def hr_man_holat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dav_holat'] = update.message.text.strip()
    await update.message.reply_text("📝 Izoh (yoki -):", reply_markup=ReplyKeyboardRemove())
    return HR_MAN_IZOH

async def hr_man_izoh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    izoh = update.message.text.strip()
    if izoh == '-': izoh = ''
    xodim_id = context.user_data['dav_xodim_id']
    komp_id = context.user_data['komp_id']
    xodim = xodim_olish(xodim_id)
    natija = manual_davomat(xodim_id, komp_id, context.user_data['dav_sana'],
        context.user_data['dav_keldi'], context.user_data['dav_ketdi'],
        context.user_data['dav_holat'], izoh, xodim[1] if xodim else 'HR', update.effective_user.id)
    await update.message.reply_text(natija, reply_markup=hr_menu_kb())
    return HR_MENU

# ==================== XODIM PANEL ====================

async def xod_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')
    komp = kompaniya_olish(komp_id)
    if not komp or komp[4] != 'faol':
        await update.message.reply_text("⛔️ Kompaniyangiz faol emas!")
        return ConversationHandler.END

    if matn == "✅ Keldim":
        xodim_id = context.user_data.get('xodim_id')
        wifi_aktiv, wifi_ssid, wifi_mac = get_wifi(komp_id)

        if wifi_aktiv and wifi_mac:  # WiFi MAC aktiv
            await update.message.reply_text(
                f"📡 *WiFi TEKSHIRUVI*\n\n"
                f"Ish joyining WiFi MAC: *{wifi_mac}*\n\n"
                f"🔗 Tugmani bosing va MAC manzilini tasdiqlang",
                parse_mode='Markdown',
                reply_markup=xod_wifi_kb(komp_id, 'keldim', xodim_id))
            context.user_data['wifi_waiting'] = True
            return XOD_MENU

        if komp[9] or komp[14]:  # GPS yoki Live GPS aktiv
            if komp[14]:  # Live GPS REQUIRED
                btn = [[KeyboardButton("📡 LIVE lokatsiya yuborish (DOIMIY)", request_location=True)]]
                await update.message.reply_text(
                    "🚨 *LIVE LOKATSIYA KERAK!*\n\n"
                    "1️⃣ Lokatsiya tugmasini bosing\n"
                    "2️⃣ Telegram-da '📍 Real vaqt lokatsiyasi' ni tanlang\n"
                    "3️⃣ Doimiy ishlaydi (ketdi belgilagunga qadar)\n\n"
                    "⚠️ Oddiy lokatsiya QABUL QILINMAYDI!",
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
            else:
                btn = [[KeyboardButton("📍 Lokatsiya yuborish", request_location=True)]]
                await update.message.reply_text(
                    "📍 Joylashuvingizni yuboring:",
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
            return XOD_KELDI_GPS
        else:
            # GPS o'chirilgan, lekin selfie kerak
            natija = keldi_belgilash(xodim_id, komp_id)
            if natija == "already":
                await update.message.reply_text("⚠️ Bugun allaqachon belgilangan!", reply_markup=xod_menu_kb())
                return XOD_MENU
            _, vaqt, kechikish = natija.split("|")
            msg = f"✅ Keldi vaqti: {vaqt}"
            if int(kechikish) > 0: msg += f"\n⚠️ Kechikish: {kechikish_format(int(kechikish))}"

            # Selfie yoki video so'ra
            context.user_data['keldi_m'] = 0
            await update.message.reply_text(
                f"{msg}\n\n📸 Selfie yoki 🎥 video yuboring:",
                reply_markup=ReplyKeyboardRemove())
            return XOD_KELDI_RASM

    elif matn == "🚪 Ketdim":
        xodim_id = context.user_data.get('xodim_id')
        wifi_aktiv, wifi_ssid, wifi_mac = get_wifi(komp_id)

        if wifi_aktiv and wifi_mac:  # WiFi MAC aktiv
            await update.message.reply_text(
                f"📡 *WiFi TEKSHIRUVI*\n\n"
                f"Ish joyining WiFi MAC: *{wifi_mac}*\n\n"
                f"🔗 Tugmani bosing va MAC manzilini tasdiqlang",
                parse_mode='Markdown',
                reply_markup=xod_wifi_kb(komp_id, 'ketdi', xodim_id))
            context.user_data['wifi_waiting_ketdi'] = True
            return XOD_MENU

        if komp[9] or komp[14]:
            if komp[14]:  # Live GPS REQUIRED
                btn = [[KeyboardButton("📡 LIVE lokatsiya yuborish (DOIMIY)", request_location=True)]]
                await update.message.reply_text(
                    "🚨 *LIVE LOKATSIYA KERAK!*\n\n"
                    "1️⃣ Lokatsiya tugmasini bosing\n"
                    "2️⃣ Telegram-da '📍 Real vaqt lokatsiyasi' ni tanlang\n"
                    "3️⃣ Doimiy ishlaydi (ketdi belgilagunga qadar)\n\n"
                    "⚠️ Oddiy lokatsiya QABUL QILINMAYDI!",
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
            else:
                btn = [[KeyboardButton("📍 Lokatsiya yuborish", request_location=True)]]
                await update.message.reply_text("📍 Joylashuvingizni yuboring:",
                    reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
            return XOD_KETDI_GPS
        else:
            natija = ketdi_belgilash(xodim_id, komp_id)
            if natija == "nokeldi":
                await update.message.reply_text("❌ Avval keldi belgilanmagan!", reply_markup=xod_menu_kb())
                return XOD_MENU
            _, vaqt, ish_soat, ish_tugash = natija.split("|")
            context.user_data['ketdi_vaqt'] = vaqt
            context.user_data['ketdi_ish_soat'] = ish_soat
            context.user_data['ketdi_ish_tugash'] = ish_tugash

            # Selfie yoki video so'ra
            context.user_data['ketdi_m'] = 0
            await update.message.reply_text(
                f"✅ Ketdi vaqti: {vaqt}\n\n📸 Selfie yoki 🎥 video yuboring:",
                reply_markup=ReplyKeyboardRemove())
            return XOD_KETDI_RASM

    elif matn == "📋 Davomatim":
        davomatlar = xodim_davomati(xodim_id)
        if not davomatlar:
            await update.message.reply_text("📋 Davomat yo'q.")
        else:
            xabar = "📋 *Mening davomatim:*\n\n"
            for d in davomatlar[:15]:
                holat_e = {"normal":"✅","sababli":"📝","kasal":"🤒","ta'til":"🏖"}.get(d[6],"❓")
                xabar += f"{holat_e} {d[1]}: {d[2] or '—'} → {d[3] or '—'}"
                if d[5] and d[5] > 0: xabar += f" ⚠️{kechikish_format(d[5])}"
                xabar += "\n"
            await update.message.reply_text(xabar, parse_mode='Markdown')
        return XOD_MENU

    elif matn == "📊 Statistikam":
        oy = hozir().strftime("%Y-%m")
        stat = xodim_oy_statistika(xodim_id, oy)
        xodim = xodim_olish(xodim_id)
        komp_id = context.user_data.get('komp_id')
        streak = xodim_streak_olish(xodim_id)

        if stat:
            kun, jami_soat, kechikish_kun, jami_kechikish, sababli, sababsiz = stat
            s = int(float(jami_soat)); d = int((float(jami_soat) - s) * 60)
            xabar = (f"📊 *{oy} oy statistikasi*\n"
                    f"👤 {xodim[1] if xodim else ''}\n\n"
                    f"📅 Kelgan kunlar: {kun}\n"
                    f"⏱ Jami ish vaqti: {s} soat {d} daqiqa\n"
                    f"⚠️ Kechikkan kunlar: {kechikish_kun}\n"
                    f"🕐 Jami kechikish: {kechikish_format(jami_kechikish)}\n"
                    f"📝 Sababli: {sababli} kun\n"
                    f"❌ Sababsiz: {sababsiz} kun")

            # Streak va reyting
            if streak > 0: xabar += f"\n\n🔥 *Streakingiz: {streak} kun!*"
            if kechikish_kun == 0 and kun > 0: xabar += f"\n🏅 *Bu oy 0 kechikish!* Ajoyib!"

            # Haftalik reyting
            rating = haftalik_reyting_xodimlar(komp_id)
            if rating:
                xabar += f"\n\n🏆 *HAFTALIK TOP 5 XODIMLAR:*\n"
                for i, r in enumerate(rating, 1):
                    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
                    ort_kech = r[6] if r[6] else 0
                    xabar += f"{medal} {r[1]} - {kechikish_format(int(ort_kech))} ort.kechikish\n"

            await update.message.reply_text(xabar, parse_mode='Markdown')
        else:
            await update.message.reply_text("📊 Bu oy ma'lumot yo'q.")
        return XOD_MENU

    elif matn == "📝 Sababli so'rov":
        await update.message.reply_text("📅 Qaysi kun? (YYYY-MM-DD):", reply_markup=ReplyKeyboardRemove())
        return XOD_SABAB_SANA

    elif matn == "📡 WiFi ulangan":
        xodim_id = context.user_data.get('xodim_id')
        komp_id = context.user_data.get('komp_id')
        komp = kompaniya_olish(komp_id)

        if context.user_data.get('wifi_waiting'):
            # Keldim WiFi bilan
            natija = keldi_belgilash(xodim_id, komp_id)
            if natija == "already":
                await update.message.reply_text("⚠️ Bugun allaqachon belgilangan!", reply_markup=xod_menu_kb())
                return XOD_MENU
            _, vaqt, kechikish = natija.split("|")
            msg = f"✅ Keldi vaqti: {vaqt}"
            if int(kechikish) > 0: msg += f"\n⚠️ Kechikish: {kechikish_format(int(kechikish))}"
            msg += "\n\n📡 WiFi orqali qabul qilindi!"

            # AUDIT LOG
            user_id = update.effective_user.id
            user_ism = update.effective_user.first_name or 'Xodim'
            audit_log_qoshish(komp_id, 'KELDI', f"WiFi orqali: {vaqt}", xodim_id, None, None, user_id, user_ism)

            await _admin_xabar(context, xodim_id, komp_id, komp, 'keldi', 0, None, True)
            await update.message.reply_text(msg, reply_markup=xod_menu_kb())
            context.user_data['wifi_waiting'] = False
            return XOD_MENU

        elif context.user_data.get('wifi_waiting_ketdi'):
            # Ketdi WiFi bilan
            natija = ketdi_belgilash(xodim_id, komp_id)
            if natija == "nokeldi":
                await update.message.reply_text("❌ Avval keldi belgilanmagan!", reply_markup=xod_menu_kb())
                return XOD_MENU
            _, vaqt, ish_soat, ish_tugash = natija.split("|")
            xodim = xodim_olish(xodim_id)
            s = int(float(ish_soat)); d = int((float(ish_soat) - s) * 60)
            msg = f"✅ Ketdi vaqti: {vaqt}\n⏱ Ish vaqti: {s} soat {d} daqiqa\n\n📡 WiFi orqali qabul qilindi!"

            # AUDIT LOG
            user_id = update.effective_user.id
            user_ism = update.effective_user.first_name or 'Xodim'
            audit_log_qoshish(komp_id, 'KETDI', f"WiFi orqali: {vaqt}", xodim_id, None, None, user_id, user_ism)

            await _admin_xabar(context, xodim_id, komp_id, komp, 'ketdi', 0, None, True)
            await update.message.reply_text(msg, reply_markup=xod_menu_kb())
            context.user_data['wifi_waiting_ketdi'] = False
            live_lokatsiya_ochirish(xodim_id)
            return XOD_MENU

    elif matn == "🏠 Bosh menu":
        await update.message.reply_text("👋 Menu:", reply_markup=xod_menu_kb())
        return XOD_MENU

    return XOD_MENU

async def xod_keldi_gps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.location:
        await update.message.reply_text("❌ GPS yuboring!")
        return XOD_KELDI_GPS
    xodim_id = context.user_data['xodim_id']
    komp_id = context.user_data['komp_id']
    lat = update.message.location.latitude
    lon = update.message.location.longitude
    live_period = getattr(update.message.location, 'live_period', None)
    komp = kompaniya_olish(komp_id)

    # FIX 1: Live GPS yoqilgan bo'lsa, oddiy lokatsiyani qabul qilma
    if komp and komp[14] and not live_period:
        btn = [[KeyboardButton("📍 Lokatsiya yuborish", request_location=True)]]
        await update.message.reply_text(
            "❌ Bu kompaniya uchun 📡 *Live lokatsiya* kerak!\n\n"
            "📌 Lokatsiya yuborishda *'Real vaqt lokatsiyasi'* (8 soat) tugmasini tanlang!",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
        return XOD_KELDI_GPS

    komp_lat, komp_lon, radius = get_gps(komp_id)
    m = masofa_hisob(lat, lon, komp_lat, komp_lon)
    if m > radius:
        await update.message.reply_text(
            f"❌ Ish joyidan tashqarisiz!\n📏 {m}m (ruxsat: {radius}m)",
            reply_markup=xod_menu_kb())
        return XOD_MENU

    # Live lokatsiyani saqlash
    if live_period and komp and komp[14]:
        live_lokatsiya_saqlash(xodim_id, komp_id, lat, lon)

    natija = keldi_belgilash(xodim_id, komp_id)
    if natija == "already":
        await update.message.reply_text("⚠️ Bugun allaqachon belgilangan!", reply_markup=xod_menu_kb())
        return XOD_MENU
    _, vaqt, kechikish = natija.split("|")
    msg = f"✅ Keldi vaqti: {vaqt}\n📏 {m}m"
    if int(kechikish) > 0: msg += f"\n⚠️ Kechikish: {kechikish_format(int(kechikish))}"
    if live_period and komp and komp[14]: msg += "\n📡 Live lokatsiya faol"

    # FIX 2: DOIM selfie/video so'ra (komp[10] dan qat'iy nazar)
    context.user_data['keldi_m'] = m
    await update.message.reply_text(
        f"{msg}\n\n📸 Selfie yoki 🎥 video yuboring:",
        reply_markup=ReplyKeyboardRemove())
    return XOD_KELDI_RASM

async def xod_keldi_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo and not update.message.video_note:
        await update.message.reply_text("❌ Selfie yoki dumaloq video yuboring!")
        return XOD_KELDI_RASM
    xodim_id = context.user_data['xodim_id']
    komp_id = context.user_data['komp_id']
    is_photo = bool(update.message.photo)  # FIX: to'g'ri tekshiruv
    rasm_id = update.message.photo[-1].file_id if is_photo else update.message.video_note.file_id
    keldi_rasm_saqlash(xodim_id, rasm_id)
    komp = kompaniya_olish(komp_id)
    m = context.user_data.get('keldi_m', 0)

    # MOTIVATSIYA: Streakni olish va motivatsiya matni yaratish
    xodim = xodim_olish(xodim_id)
    stat = xodim_bugun_statistika(xodim_id)
    streak = xodim_streak_olish(xodim_id)
    kechikish = int(stat[3]) if stat and stat[3] else 0

    motivatsiya = generate_keldi_motivation(xodim, kechikish, streak)

    # AUDIT LOG
    user_id = update.effective_user.id
    user_ism = update.effective_user.first_name or 'Xodim'
    tafsilot = f"Keldi: {stat[0] if stat else 'N/A'} | Masofa: {m}m"
    audit_log_qoshish(komp_id, 'KELDI', tafsilot, xodim_id, rasm_id if is_photo else None,
                     rasm_id if not is_photo else None, user_id, user_ism)

    await _admin_xabar(context, xodim_id, komp_id, komp, 'keldi', m, rasm_id, is_photo)
    await update.message.reply_text(f"✅ Davomat qabul qilindi!\n\n{motivatsiya}",
                                     parse_mode='Markdown', reply_markup=xod_menu_kb())
    return XOD_MENU

async def xod_ketdi_gps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.location:
        await update.message.reply_text("❌ GPS yuboring!")
        return XOD_KETDI_GPS
    xodim_id = context.user_data['xodim_id']
    komp_id = context.user_data['komp_id']
    lat = update.message.location.latitude
    lon = update.message.location.longitude
    komp_lat, komp_lon, radius = get_gps(komp_id)
    m = masofa_hisob(lat, lon, komp_lat, komp_lon)
    if m > radius:
        await update.message.reply_text(
            f"❌ Ish joyidan tashqarisiz!\n📏 {m}m (ruxsat: {radius}m)",
            reply_markup=xod_menu_kb())
        return XOD_MENU
    komp = kompaniya_olish(komp_id)
    natija = ketdi_belgilash(xodim_id, komp_id)
    if natija == "nokeldi":
        await update.message.reply_text("❌ Avval keldi belgilanmagan!", reply_markup=xod_menu_kb())
        return XOD_MENU
    _, vaqt, ish_soat, ish_tugash = natija.split("|")
    xodim = xodim_olish(xodim_id)
    xabar = ketdi_xabar_matni(xodim[1] if xodim else '', ish_tugash, vaqt, float(ish_soat))
    xabar += f"\n📏 {m}m"
    live_lokatsiya_ochirish(xodim_id)

    # FIX 2+3: DOIM selfie/video so'ra + parse_mode='Markdown' qo'sh
    context.user_data['ketdi_m'] = m
    await update.message.reply_text(
        f"{xabar}\n\n📸 Selfie yoki 🎥 video yuboring:",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove())
    return XOD_KETDI_RASM

async def xod_ketdi_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo and not update.message.video_note:
        await update.message.reply_text("❌ Selfie yoki dumaloq video yuboring!")
        return XOD_KETDI_RASM
    xodim_id = context.user_data['xodim_id']
    komp_id = context.user_data['komp_id']
    is_photo = bool(update.message.photo)  # FIX: to'g'ri tekshiruv
    rasm_id = update.message.photo[-1].file_id if is_photo else update.message.video_note.file_id
    ketdi_rasm_saqlash(xodim_id, rasm_id)
    komp = kompaniya_olish(komp_id)
    m = context.user_data.get('ketdi_m', 0)

    # MOTIVATSIYA: Bugungi statistika va motivatsiya matni
    xodim = xodim_olish(xodim_id)
    streak = xodim_streak_olish(xodim_id)
    ish_tugash = context.user_data.get('ketdi_ish_tugash') or (xodim[6] if xodim else "18:00")
    ketdi_vaqt = context.user_data.get('ketdi_vaqt') or hozir().strftime("%H:%M")
    ish_soat = float(context.user_data.get('ketdi_ish_soat', 0))

    motivatsiya = generate_ketdi_motivation(xodim, ish_tugash, ketdi_vaqt, ish_soat, streak)

    # AUDIT LOG
    user_id = update.effective_user.id
    user_ism = update.effective_user.first_name or 'Xodim'
    s = int(ish_soat); d = int((ish_soat - s) * 60)
    tafsilot = f"Ketdi: {ketdi_vaqt} | Ish vaqti: {s}s {d}d | Masofa: {m}m"
    audit_log_qoshish(komp_id, 'KETDI', tafsilot, xodim_id, rasm_id if is_photo else None,
                     rasm_id if not is_photo else None, user_id, user_ism)

    await _admin_xabar(context, xodim_id, komp_id, komp, 'ketdi', m, rasm_id, is_photo)
    await update.message.reply_text(f"✅ Chiqish belgilandi!\n\n{motivatsiya}",
                                     parse_mode='Markdown', reply_markup=xod_menu_kb())
    return XOD_MENU

async def _admin_xabar(context, xodim_id, komp_id, komp, tur, masofa=0, rasm_id=None, foto=True):
    xodim = xodim_olish(xodim_id)
    if not xodim or not komp: return
    vaqt = hozir().strftime("%H:%M")
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT kechikish FROM davomat WHERE xodim_id=%s AND sana=%s",
                (xodim_id, hozir().strftime("%Y-%m-%d")))
    dav = cur.fetchone(); cur.close(); conn.close()
    kechikish = dav[0] if dav else 0
    emoji = "📨" if tur == 'keldi' else "🚪"
    xabar = (f"{emoji} *{'KELDI' if tur=='keldi' else 'KETDI'} XABARI*\n"
             f"━━━━━━━━━━━━━━━\n"
             f"🏢 {komp[1]}\n👤 {xodim[1]}\n💼 {xodim[3]}\n⏰ {vaqt}\n")
    if kechikish > 0: xabar += f"⚠️ Kechikish: {kechikish_format(kechikish)}\n"
    if masofa > 0: xabar += f"📏 Masofa: {masofa}m\n"
    xabar += "━━━━━━━━━━━━━━━"

    # ALERT: Jiddiy kechikish uchun warning
    ogohlantirish = ""
    if tur == 'keldi' and kechikish > 60:
        ogohlantirish = f"\n\n🚨 *JIDDIY OGOHLANTIRISH!*\n{xodim[1]} 1 soatdan ko'p kechiktildi!"
    elif tur == 'ketdi' and kechikish < -30:
        ogohlantirish = f"\n\n🚨 *XODIM ERTA KETDI!*\n30+ daqiqa oldin ish joyini tark etdi!"

    admin_id = komp[3]
    hr_list = hr_idlari(komp_id)
    sa_list = barcha_super_admin_idlar()
    # Takrorlanmasin
    barcha = list(set(([admin_id] if admin_id else []) + hr_list + sa_list))
    logger.info(f"_admin_xabar: {tur} | xodim={xodim[1]} | recipients={barcha} | rasm_id={rasm_id}")
    for aid in barcha:
        # FIX 4+5: Matn va rasm uchun alohida try-except — biri xato bo'lsa ikkinchisi ishlaydi
        try:
            xabar_final = xabar + ogohlantirish
            await context.bot.send_message(aid, xabar_final, parse_mode='Markdown')
        except Exception as e:
            logger.warning(f"Matn yuborishda xato (chat_id={aid}): {e}")
            try:
                # Markdown xatosi bo'lsa, formatsiz matn
                xabar_oddiy = xabar.replace('*', '').replace('_', '').replace('`', '')
                await context.bot.send_message(aid, xabar_oddiy)
            except Exception as e2:
                logger.error(f"Oddiy matn ham yuborilmadi (chat_id={aid}): {e2}")
        if rasm_id:
            try:
                if foto:
                    await context.bot.send_photo(aid, rasm_id)
                else:
                    try:
                        await context.bot.send_video_note(aid, rasm_id)
                    except:
                        await context.bot.send_video(aid, rasm_id)
            except Exception as e:
                logger.warning(f"Rasm/video yuborishda xato (chat_id={aid}): {e}")

async def xod_sabab_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sabab_sana'] = update.message.text.strip()
    await update.message.reply_text("📝 Sabab matnini kiriting:")
    return XOD_SABAB_MATN

async def xod_sabab_matn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sabab = update.message.text.strip()
    xodim_id = context.user_data['xodim_id']
    komp_id = context.user_data['komp_id']
    sana = context.user_data['sabab_sana']
    sorov_id = sababli_sorov_saqlash(xodim_id, komp_id, sana, sabab)
    xodim = xodim_olish(xodim_id)
    komp = kompaniya_olish(komp_id)
    xabar = (f"📝 *Sababli so'rov*\n\n🏢 {komp[1] if komp else ''}\n"
             f"👤 {xodim[1] if xodim else ''}\n📅 {sana}\n📋 {sabab}")
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"sorov_ha_{sorov_id}_{xodim_id}_{sana}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"sorov_yoq_{sorov_id}_{xodim_id}_{sana}")
    ]])
    admin_id = komp[3] if komp else None
    hr_list = hr_idlari(komp_id)
    for aid in (([admin_id] if admin_id else []) + hr_list):
        try:
            await context.bot.send_message(aid, xabar, parse_mode='Markdown', reply_markup=keyboard)
        except: pass
    await update.message.reply_text("✅ So'rovingiz yuborildi!", reply_markup=xod_menu_kb())
    return XOD_MENU

async def sorov_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    amal, sorov_id, xodim_id, sana = data[1], int(data[2]), int(data[3]), data[4]
    conn = connect(); cur = conn.cursor()
    cur.execute("SELECT sabab FROM sababli_sorovlar WHERE id=%s", (sorov_id,))
    row = cur.fetchone()
    cur.execute("SELECT ism,telegram_id FROM xodimlar WHERE id=%s", (xodim_id,))
    xodim = cur.fetchone(); cur.close(); conn.close()
    sabab = row[0] if row else ''
    holat = 'tasdiqlandi' if amal == 'ha' else 'rad_etildi'
    sababli_sorov_yangilash(sorov_id, holat, xodim_id, sana, sabab)
    emoji = "✅" if amal == 'ha' else "❌"
    await query.edit_message_text(f"{emoji} So'rov {holat}!\n📅 {sana}\n📋 {sabab}")
    if xodim and xodim[1]:
        try:
            await context.bot.send_message(xodim[1],
                f"{emoji} Hurmatli {xodim[0]},\nSababli so'rovingiz {holat}!\n📅 {sana}")
        except: pass

# ==================== SUPER ADMIN DAILY REPORT ====================

async def sa_hisobot_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sana = update.message.text.strip()
    try:
        datetime.strptime(sana, "%Y-%m-%d")
        context.user_data['hisobot_sana'] = sana
        conn = connect(); cur = conn.cursor()
        cur.execute('''SELECT k.nomi,x.ism,x.lavozim,d.keldi,d.ketdi,d.ish_soat,d.kechikish,d.keldi_rasm,d.ketdi_rasm
                      FROM davomat d
                      JOIN xodimlar x ON d.xodim_id=x.id
                      JOIN kompaniyalar k ON d.kompaniya_id=k.id
                      WHERE d.sana=%s
                      ORDER BY k.nomi,x.ism''', (sana,))
        davomatlar = cur.fetchall(); cur.close(); conn.close()

        context.user_data['sa_davomatlar'] = davomatlar

        if not davomatlar:
            await update.message.reply_text(
                f"📅 {sana}\n❌ Bu kun ma'lumot yo'q!",
                reply_markup=sa_menu_kb())
            return SA_MENU

        xabar = f"📊 *{sana} - BARCHA KOMPANIYALAR HISOBOTI*\n" + "="*50 + "\n\n"

        komp_name = ""
        for i, dav in enumerate(davomatlar, 1):
            komp, ism, lavozim, keldi, ketdi, ish_soat, kechikish, rasm_keldi, rasm_ketdi = dav
            if komp != komp_name:
                xabar += f"\n🏢 *{komp}*\n" + "-"*40 + "\n"
                komp_name = komp

            s = int(float(ish_soat or 0)); d = int((float(ish_soat or 0) - s) * 60)
            kech = kechikish_format(int(kechikish or 0))
            xabar += (f"👤 {ism} ({lavozim})\n"
                      f"   📍 {keldi or '—'} → {ketdi or '—'} | "
                      f"⏱ {s}s {d}d | ⚠️ {kech}\n")

        await update.message.reply_text(xabar, parse_mode='Markdown')

        # Rasmlarni alohida yubor
        for dav in davomatlar:
            komp, ism, lavozim, keldi, ketdi, ish_soat, kechikish, rasm_keldi, rasm_ketdi = dav
            if rasm_keldi or rasm_ketdi:
                await update.message.reply_text(f"🏢 {komp} - {ism}: Rasmlar")
                if rasm_keldi:
                    try:
                        await context.bot.send_photo(update.effective_chat.id, rasm_keldi, caption="📸 Keldi")
                    except:
                        pass
                if rasm_ketdi:
                    try:
                        await context.bot.send_photo(update.effective_chat.id, rasm_ketdi, caption="📸 Ketdi")
                    except:
                        pass

        await update.message.reply_text("✅ Hisobot yakunlandi!", reply_markup=sa_menu_kb())
        return SA_MENU
    except ValueError:
        await update.message.reply_text("❌ Format xato! (YYYY-MM-DD)")
        return SA_HISOBOT_SANA

# ==================== LIVE LOKATSIYA UPDATE ====================

async def live_location_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edited message orqali live lokatsiya yangilanishi"""
    msg = update.edited_message
    if not msg or not msg.location: return
    user_id = msg.from_user.id
    xodim = telegram_id_orqali_xodim(user_id)
    if not xodim: return
    xodim_id = xodim[0]
    komp_id = xodim[3]
    komp = kompaniya_olish(komp_id)
    if not komp or not komp[14]: return  # live_gps_aktiv
    live_lokatsiya_saqlash(xodim_id, komp_id, msg.location.latitude, msg.location.longitude)

# ==================== JOB HANDLERS ====================

async def tekshiruv_job(context: ContextTypes.DEFAULT_TYPE):
    """Har 30 daqiqada xodimlar joylashuvini tekshirish"""
    try:
        xodimlar = barcha_live_xodimlar()
        logger.info(f"🔍 Tekshiruv job: {len(xodimlar)} xodim topildi")

        for x in xodimlar:
            xodim_id, komp_id, lat, lon, ism, telegram_id, k_lat, k_lon, k_radius, admin_id, komp_nomi = x
            if not lat or not lon: continue
            masofa = masofa_hisob(lat, lon, k_lat, k_lon)
            logger.info(f"📍 {ism}: {masofa}m (limit: {k_radius}m)")

            if masofa > k_radius:
                vaqt = hozir().strftime("%H:%M")
                xabar = (f"⚠️ *XODIM ISH JOYIDA YO'Q!*\n\n"
                        f"🏢 {komp_nomi}\n👤 {ism}\n"
                        f"📏 Masofa: {masofa}m (ruxsat: {k_radius}m)\n"
                        f"⏰ Vaqt: {vaqt}")
                hr_list = hr_idlari(komp_id)
                sa_list = barcha_super_admin_idlar()
                for aid in list(set(([admin_id] if admin_id else []) + hr_list + sa_list)):
                    try:
                        await context.bot.send_message(aid, xabar, parse_mode='Markdown')
                        logger.info(f"✅ Xabar yuborildi: {aid}")
                    except Exception as e:
                        logger.error(f"❌ Xabar yuborishmadi {aid}: {e}")
    except Exception as e:
        logger.error(f"❌ Tekshiruv job xatosi: {e}")

async def live_location_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    """Ketdi belgilangan xodimlarning live lokatsiyalarini o'chirish"""
    conn = connect(); cur = conn.cursor()
    sana = hozir().strftime("%Y-%m-%d")
    # Ketdi belgilangan xodimlarni topib, lokatsiyalarini o'chir
    cur.execute('''UPDATE live_lokatsiyalar SET faol=FALSE
                  WHERE faol=TRUE AND xodim_id IN (
                    SELECT id FROM davomat d
                    JOIN xodimlar x ON d.xodim_id=x.id
                    WHERE d.sana=%s AND d.ketdi IS NOT NULL
                  )''', (sana,))
    conn.commit(); cur.close(); conn.close()
    logger.info(f"✅ Live lokatsiyalar o'chirildi (ketdi belgilangan xodimlar)")

async def haftalik_hisobot_job(context: ContextTypes.DEFAULT_TYPE):
    """Juma kuni haftalik hisobot"""
    kompaniyalar = haftalik_davomat_kompaniyalar()
    for k in kompaniyalar:
        komp_id, nomi, admin_id = k
        stat = kompaniya_haftalik_stat(komp_id)
        if not stat: continue
        kelgan, kun, jami_soat, ort_kechikish = stat
        s = int(float(jami_soat)); d = int((float(jami_soat) - s) * 60)
        xabar = (f"📊 *HAFTALIK HISOBOT*\n🏢 {nomi}\n\n"
                f"👥 Bu hafta {kelgan} xodim keldi\n"
                f"📅 Jami {kun} ish kuni\n"
                f"⏱ Jami ish vaqti: {s} soat {d} daqiqa\n"
                f"⚠️ O'rtacha kechikish: {kechikish_format(ort_kechikish)}")
        # Reyting top-3
        reyting = kompaniya_reyting(komp_id)
        if reyting:
            xabar += "\n\n🏆 *Hafta reytingi (Top 3):*\n"
            for i, r in enumerate(reyting[:3], 1):
                medal = ["🥇","🥈","🥉"][i-1]
                xabar += f"{medal} {r[0]} — {kechikish_format(r[4])} kechikish\n"
        hr_list = hr_idlari(komp_id)
        sa_list = barcha_super_admin_idlar()
        for aid in list(set(([admin_id] if admin_id else []) + hr_list + sa_list)):
            try:
                await context.bot.send_message(aid, xabar, parse_mode='Markdown')
            except: pass

async def eslatma_job(context: ContextTypes.DEFAULT_TYPE):
    """Har daqiqa ish boshlanishidan 30 daqiqa oldin eslatma"""
    hozir_v = hozir()
    xodimlar = barcha_xodimlar_eslatma()
    for x in xodimlar:
        xodim_id, telegram_id, ism, ish_bosh, tugilgan_kun, komp_id = x
        if not telegram_id: continue
        # Tug'ilgan kun tabrik
        if tugilgan_kun:
            bugun = hozir_v.strftime("%m-%d")
            try:
                if tugilgan_kun[5:] == bugun and hozir_v.hour == 9 and hozir_v.minute == 0:
                    await context.bot.send_message(telegram_id,
                        f"🎂 *Tug'ilgan kuningiz muborak, {ism}!*\n\nSizga sog'lik, baxt va omad tilaymiz! 🎉",
                        parse_mode='Markdown')
            except: pass
        # Ish boshlanish eslatmasi
        try:
            ish_dt = datetime.strptime(ish_bosh, "%H:%M")
            farq_daqiqa = (ish_dt.hour * 60 + ish_dt.minute) - (hozir_v.hour * 60 + hozir_v.minute)
            if farq_daqiqa == 30:
                await context.bot.send_message(telegram_id,
                    f"⏰ *Eslatma!*\n\n{ism}, ish boshlanishiga *30 daqiqa* qoldi!\nIsh vaqti: {ish_bosh} 🏃",
                    parse_mode='Markdown')
        except: pass

# ==================== WIFI/GPS CALLBACK ====================

async def gps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """GPS button callback handler - ask for location"""
    query = update.callback_query
    data = query.data

    # Parse callback data: gps_keldim_komp_id or gps_ketdi_komp_id
    parts = data.split("_")
    if len(parts) < 3:
        return

    amal = parts[1]  # 'keldim' or 'ketdi'
    komp_id = int(parts[2])

    try:
        await query.answer()

        if amal == 'keldim':
            btn = [[KeyboardButton("📍 GPS yuborish", request_location=True)]]
            await query.edit_message_text(
                "📍 *GPS lokatsiya yuboring:*\n\n"
                "Telegram'da 'Joylashuv' tugmasini bosing",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
            context.user_data['wifi_waiting'] = False
            return

        elif amal == 'ketdi':
            btn = [[KeyboardButton("📍 GPS yuborish", request_location=True)]]
            await query.edit_message_text(
                "📍 *GPS lokatsiya yuboring:*\n\n"
                "Telegram'da 'Joylashuv' tugmasini bosing",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
            context.user_data['wifi_waiting_ketdi'] = False
            return

    except Exception as e:
        await query.answer(f"❌ Xatolik: {e}", show_alert=True)

async def wifi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """WiFi button callback handler"""
    query = update.callback_query
    data = query.data

    # Parse callback data: wifi_keldim_komp_id or wifi_ketdi_komp_id
    parts = data.split("_")
    if len(parts) < 3:
        return

    amal = parts[1]  # 'keldim' or 'ketdi'
    komp_id = int(parts[2])

    xodim_id = context.user_data.get('xodim_id')
    if not xodim_id:
        await query.answer("❌ Sessiya tugadi, qayta /start bosing", show_alert=True)
        return

    komp = kompaniya_olish(komp_id)

    try:
        await query.answer()  # No notification

        if amal == 'keldim':
            natija = keldi_belgilash(xodim_id, komp_id)
            if natija == "already":
                await query.edit_message_text("⚠️ Bugun allaqachon belgilangan!")
                return

            _, vaqt, kechikish = natija.split("|")
            msg = f"✅ Keldi vaqti: {vaqt}"
            if int(kechikish) > 0:
                msg += f"\n⚠️ Kechikish: {kechikish_format(int(kechikish))}"
            msg += "\n\n📡 WiFi orqali qabul qilindi!"

            # AUDIT LOG
            user_id = update.effective_user.id
            user_ism = update.effective_user.first_name or 'Xodim'
            audit_log_qoshish(komp_id, 'KELDI', f"WiFi orqali: {vaqt}", xodim_id, None, None, user_id, user_ism)

            context.user_data['wifi_waiting'] = False

        elif amal == 'ketdi':
            natija = ketdi_belgilash(xodim_id, komp_id)
            if natija == "nokeldi":
                await query.edit_message_text("❌ Avval keldi belgilanmagan!")
                return

            _, vaqt, ish_soat, ish_tugash = natija.split("|")
            s = int(float(ish_soat))
            d = int((float(ish_soat) - s) * 60)
            msg = f"✅ Ketdi vaqti: {vaqt}\n⏱ Ish vaqti: {s} soat {d} daqiqa\n\n📡 WiFi orqali qabul qilindi!"

            # AUDIT LOG
            user_id = update.effective_user.id
            user_ism = update.effective_user.first_name or 'Xodim'
            audit_log_qoshish(komp_id, 'KETDI', f"WiFi orqali: {vaqt}", xodim_id, None, None, user_id, user_ism)

            context.user_data['wifi_waiting_ketdi'] = False
            live_lokatsiya_ochirish(xodim_id)

        await query.edit_message_text(msg)

        # Admin notification (async, don't await)
        try:
            await _admin_xabar(context, xodim_id, komp_id, komp, amal, 0, None, True)
        except:
            pass

    except Exception as e:
        await query.answer(f"❌ Xatolik: {e}", show_alert=True)

# ==================== XATO ====================

async def xato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Xato: {context.error}", exc_info=context.error)

# ==================== FLASK WEB SERVER ====================

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
flask_app = Flask(__name__, template_folder=template_dir)

@flask_app.route('/wifi-check', methods=['GET'])
def wifi_check_page():
    user_id = request.args.get('user_id')
    komp_id = request.args.get('komp_id')
    amal = request.args.get('amal', 'keldim')
    xodim_id = request.args.get('xodim_id')

    return render_template('wifi_check.html', user_id=user_id, komp_id=komp_id,
                         amal=amal, xodim_id=xodim_id)

@flask_app.route('/wifi-verify', methods=['POST'])
def wifi_verify():
    try:
        data = request.get_json()
        xodim_id = data.get('xodim_id')
        komp_id = data.get('komp_id')
        wifi_mac = data.get('wifi_mac', '').strip().upper()
        amal = data.get('amal', 'keldim')

        if not all([xodim_id, komp_id, wifi_mac]):
            return jsonify({'status': 'error', 'message': '❌ Ma\'lumot to\'liq emas!'})

        wifi_aktiv, komp_ssid = get_wifi_mac(int(komp_id))

        if not wifi_aktiv:
            return jsonify({'status': 'error', 'message': '❌ Tashkilotning WiFi sozlamalari yo\'q!'})

        # Bir nechta MAC ro'yxatini tekshirish
        mac_match = wifi_mac_tekshir(int(komp_id), wifi_mac)

        if mac_match:
            try:
                if amal == 'keldim':
                    natija = keldi_belgilash(int(xodim_id), int(komp_id))
                    if natija == "already":
                        return jsonify({'status': 'error', 'message': '⚠️ Bugun allaqachon belgilangan!'})
                    _, vaqt, kechikish = natija.split("|")
                    audit_log_qoshish(int(komp_id), 'KELDI', f"WiFi orqali: {vaqt}", int(xodim_id), None, None, None, 'WiFi Form')
                    return jsonify({'status': 'success', 'message': f'✅ Keldi: {vaqt}'})
                else:
                    natija = ketdi_belgilash(int(xodim_id), int(komp_id))
                    if natija == "nokeldi":
                        return jsonify({'status': 'error', 'message': '❌ Avval keldi belgilanmagan!'})
                    _, vaqt, ish_soat, ish_tugash = natija.split("|")
                    audit_log_qoshish(int(komp_id), 'KETDI', f"WiFi orqali: {vaqt}", int(xodim_id), None, None, None, 'WiFi Form')
                    return jsonify({'status': 'success', 'message': f'✅ Ketdi: {vaqt}'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'❌ Xato: {str(e)}'})
        else:
            return jsonify({'status': 'failed', 'message': '❌ MAC manzil mos kelmadi! GPS kerak.'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'❌ Server xatosi: {str(e)}'})

# Flask app will be run by Gunicorn in production
# (no need to run it manually here)

# ==================== MAIN ====================

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")
    create_tables()
    print("Baza tayyor!")
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.TEXT & filters.Regex("^▶️ Botni ishga tushirish$"), boshlash_handler),
        ],
        states={
            TELEFON: [MessageHandler(filters.CONTACT | filters.TEXT, telefon_qabul)],
            KOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, kod_tekshir)],
            SA_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_menu)],
            SA_KOMP_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_list)],
            SA_KOMP_NOMI: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_nomi)],
            SA_KOMP_TEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_tel)],
            SA_KOMP_KOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_kod)],
            SA_KOMP_TANLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_tanlash)],
            SA_KOMP_AMAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_amal)],
            SA_KOMP_TAHRIR_QIYMAT: [
                MessageHandler(filters.LOCATION, sa_komp_tahrir_qiymat),
                MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_tahrir_qiymat),
            ],
            SA_FUNKSIYA: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_funksiya)],
            SA_SOZ_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_soz_menu)],
            SA_ADM_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_adm_list)],
            SA_ADM_QOSH_TEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_adm_qosh_tel)],
            SA_ADM_QOSH_ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_adm_qosh_ism)],
            SA_KOMP_XODIM_TANLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_xodim_tanlash)],
            SA_KOMP_XODIM_AMAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_xodim_amal)],
            SA_KOMP_XODIM_TAHRIR: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_xodim_tahrir)],
            SA_KOMP_DELETE_KOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_delete_kod)],
            SA_HISOBOT_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_hisobot_sana)],
            SA_HISOBOT_KUN: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_hisobot_sana)],
            ADM_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_menu)],
            ADM_XODIM_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_list)],
            ADM_XODIM_ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_ism)],
            ADM_XODIM_TEL: [MessageHandler(filters.CONTACT | filters.TEXT, adm_xodim_tel)],
            ADM_XODIM_LAV: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_lav)],
            ADM_XODIM_OYLIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_oylik)],
            ADM_XODIM_BOSH: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_bosh)],
            ADM_XODIM_TUG: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_tug)],
            ADM_XODIM_ROL: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_rol)],
            ADM_XODIM_TANLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_tanlash)],
            ADM_XODIM_TAHRIR: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_tahrir)],
            ADM_XODIM_TAHRIR_Q: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_tahrir_q)],
            ADM_GPS_LOK: [
                MessageHandler(filters.LOCATION, adm_gps_lok),
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm_gps_lok),
            ],
            ADM_GPS_RADIUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_gps_radius)],
            ADM_WIFI_AKTIV: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_wifi_aktiv)],
            ADM_WIFI_SSID: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_wifi_ssid)],
            ADM_DAV_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_dav_menu)],
            ADM_DAV_XODIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_dav_xodim)],
            ADM_DAV_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_dav_sana)],
            ADM_DAV_KELDI: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_dav_keldi)],
            ADM_DAV_KETDI: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_dav_ketdi)],
            ADM_DAV_HOLAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_dav_holat)],
            ADM_DAV_IZOH: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_dav_izoh)],
            ADM_DAV_TAHRIR_TANLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_dav_tahrir_tanlash)],
            ADM_DAV_TAHRIR_AMAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_dav_tahrir_amal)],
            ADM_DAV_TAHRIR_Q: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_dav_tahrir_q)],
            ADM_HISOBOT_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_hisobot_sana)],
            ADM_HISOBOT_KUN: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_hisobot_sana)],
            HR_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_menu_handler)],
            HR_MAN_XODIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_man_xodim)],
            HR_MAN_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_man_sana)],
            HR_MAN_KELDI: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_man_keldi)],
            HR_MAN_KETDI: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_man_ketdi)],
            HR_MAN_HOLAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_man_holat)],
            HR_MAN_IZOH: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_man_izoh)],
            XOD_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_menu_handler)],
            XOD_KELDI_GPS: [MessageHandler(filters.LOCATION, xod_keldi_gps)],
            XOD_KELDI_RASM: [MessageHandler(filters.PHOTO | filters.VIDEO_NOTE, xod_keldi_rasm)],
            XOD_KETDI_GPS: [MessageHandler(filters.LOCATION, xod_ketdi_gps)],
            XOD_KETDI_RASM: [MessageHandler(filters.PHOTO | filters.VIDEO_NOTE, xod_ketdi_rasm)],
            XOD_SABAB_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_sabab_sana)],
            XOD_SABAB_MATN: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_sabab_matn)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(sorov_callback, pattern=r'^sorov_'))
    app.add_handler(CallbackQueryHandler(wifi_callback, pattern=r'^wifi_'))
    app.add_handler(CallbackQueryHandler(gps_callback, pattern=r'^gps_'))
    # Live lokatsiya yangilanishi (edited_message)
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.LOCATION, live_location_update))
    app.add_error_handler(xato)

    # Job Queue — schedulerlar
    jq = app.job_queue
    # Har 30 daqiqada joylashuv tekshiruvi
    jq.run_repeating(tekshiruv_job, interval=1800, first=60)
    # 8 soat live location timeout
    jq.run_repeating(live_location_timeout_job, interval=600, first=60)
    # Har daqiqa eslatma (ish boshlanishi va tug'ilgan kun)
    jq.run_repeating(eslatma_job, interval=60, first=30)
    # Juma kuni soat 18:00 da haftalik hisobot
    jq.run_daily(haftalik_hisobot_job,
                 time=dtime(hour=18, minute=0, second=0, tzinfo=TASHKENT),
                 days=(4,))  # 4 = Juma

    print("Bot ishlamoqda...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
