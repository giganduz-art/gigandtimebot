import os, math, logging, random, string, threading
from datetime import datetime, time as dtime, timedelta
import pytz
from telegram import (Update, ReplyKeyboardMarkup, KeyboardButton,
                      InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, WebAppInfo,
                      BotCommand)
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
        farq_fmt = kechikish_format(abs(farq))
        s = int(ish_soat); d = int((ish_soat - s) * 60)
        if farq >= 30:
            return (f"🌙 *QOLIB ISHLASH* (+{farq_fmt} ortiqcha)\n"
                    f"Rahmat, {ism}! Bugun {s} soat {d} daqiqa ishlading.\n"
                    f"Qo'shimcha {farq_fmt} qolib ishlading! 🏆\n"
                    f"Bunday fidoyilik qadrlanadi!")
        elif farq >= -15:
            return (f"✅ *TO'LIQ ISH KUNI*\n"
                    f"Yaxshi ish kuni, {ism}!\n"
                    f"Bugun {s} soat {d} daqiqa samarali mehnat qildingiz! 💼\n"
                    f"Xayrli oqshom!")
        elif farq >= -30:
            return (f"⚠️ *ERTA KETISH* ({farq_fmt} oldin)\n"
                    f"Diqqat, {ism}! Ish vaqti tugamay {farq_fmt} oldin ketdingiz.\n"
                    f"Sababini HR ga bildiring! 📋")
        else:
            return (f"❗ *JIDDIY ERTA KETISH* ({farq_fmt} oldin)\n"
                    f"Ogohlantirish, {ism}! {farq_fmt} oldin ketdingiz.\n"
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
    SA_KOMP_XODIM_VIEW_SANA, SA_KOMP_XODIM_STAT_FORMAT, SA_KOMP_XODIM_STAT_SANA_1, SA_KOMP_XODIM_STAT_SANA_2,
    SA_KOMP_DAV_SANA,
    ADM_MENU, ADM_XODIM_LIST, ADM_XODIM_ISM, ADM_XODIM_TEL,
    ADM_XODIM_LAV, ADM_XODIM_OYLIK, ADM_XODIM_BOSH, ADM_XODIM_TUG,
    ADM_XODIM_ROL, ADM_XODIM_TANLASH, ADM_XODIM_TAHRIR, ADM_XODIM_TAHRIR_Q,
    ADM_KOMP_XODIM_VIEW_SANA, ADM_KOMP_XODIM_STAT_FORMAT, ADM_KOMP_XODIM_STAT_SANA_1, ADM_KOMP_XODIM_STAT_SANA_2,
    ADM_GPS_LOK, ADM_GPS_RADIUS,
    ADM_WIFI_AKTIV, ADM_WIFI_SSID,
    ADM_DAV_MENU, ADM_DAV_XODIM, ADM_DAV_SANA, ADM_DAV_KELDI,
    ADM_DAV_KETDI, ADM_DAV_HOLAT, ADM_DAV_IZOH,
    ADM_DAV_TAHRIR_TANLASH, ADM_DAV_TAHRIR_AMAL, ADM_DAV_TAHRIR_Q,
    ADM_HISOBOT_SANA, ADM_HISOBOT_KUN,
    HR_MENU, HR_MAN_XODIM, HR_MAN_SANA, HR_MAN_KELDI,
    HR_MAN_KETDI, HR_MAN_HOLAT, HR_MAN_IZOH,
    HR_VIEW_XODIM, HR_VIEW_SANA,
    XOD_MENU, XOD_KELDI_ACTION, XOD_KELDI_GPS, XOD_KELDI_RASM, XOD_KELDI_AUDIO,
    XOD_KETDI_ACTION, XOD_KETDI_GPS, XOD_KETDI_RASM, XOD_KETDI_AUDIO,
    XOD_SABAB_SANA, XOD_SABAB_MATN,
    SA_KOMP_DELETE_KOD,
    SA_HISOBOT_SANA, SA_HISOBOT_KUN,
    SA_XODIM_DELETE_KOD, ADM_XODIM_DELETE_KOD,
    # New hisobot states
    ADM_HISOBOT_FORMAT, ADM_HISOBOT_YIL_OY, ADM_HISOBOT_SANA_1, ADM_HISOBOT_SANA_2,
    SA_HISOBOT_FORMAT, SA_HISOBOT_YIL_OY, SA_HISOBOT_SANA_1, SA_HISOBOT_SANA_2,
    # Xabar states
    SA_XABAR_MENU, SA_XABAR_TASHKILOT, SA_XABAR_RECIPIENT, SA_XABAR_SUBJECT, SA_XABAR_MATN, SA_XABAR_INBOX, SA_XABAR_HISTORY,
    ADM_XABAR_MENU, ADM_XABAR_RECIPIENT, ADM_XABAR_SUBJECT, ADM_XABAR_MATN, ADM_XABAR_INBOX, ADM_XABAR_HISTORY,
    HR_XABAR_MENU, HR_XABAR_RECIPIENT, HR_XABAR_SUBJECT, HR_XABAR_MATN, HR_XABAR_INBOX, HR_XABAR_HISTORY,
    XOD_XABAR_MENU, XOD_XABAR_RECIPIENT, XOD_XABAR_SUBJECT, XOD_XABAR_MATN, XOD_XABAR_INBOX, XOD_XABAR_HISTORY,
    # Kirm/Chiqim states
    XOD_KIRM_MENU, XOD_KIRM_TURI, XOD_KIRM_SUMMA, XOD_KIRM_IZOH,
    XOD_CHIQIM_MENU, XOD_CHIQIM_TURI, XOD_CHIQIM_SUMMA, XOD_CHIQIM_IZOH,
) = range(121)

# ==================== MENYULAR ====================

def sa_menu_kb():
    return ReplyKeyboardMarkup([
        ["🏢 Bizneslar", "👑 Super Adminlar"],
        ["📊 Umumiy hisobot", "📋 Audit Log"],
        ["📸 Barcha rasmlar", "💬 Xabar"],
        ["🔐 Sozlamalar", "☰ Menu"]
    ], resize_keyboard=True)

def adm_menu_kb():
    return ReplyKeyboardMarkup([
        ["👥 Xodimlar", "📅 Davomat"],
        ["📊 Hisobot", "💬 Xabar"],
        ["📍 GPS sozlash", "📡 WiFi sozlash"],
        ["📋 Audit Log", "📸 Rasm log", "☰ Menu"]
    ], resize_keyboard=True)

def hr_menu_kb():
    return ReplyKeyboardMarkup([
        ["✅ Keldim", "🚪 Ketdim"],
        ["✍️ Manual davomat", "👁️ Davomatni ko'rish"],
        ["📊 Hisobot", "💬 Xabar"],
        ["☰ Menu"]
    ], resize_keyboard=True)

def xod_menu_kb():
    return ReplyKeyboardMarkup([
        ["✅ Keldim", "🚪 Ketdim"],
        ["💰 Kirm Xisobim", "💰 Chiqim Xisobim"],
        ["📄 Xisoobotlarim", "📝 Sababli so'rov"],
        ["💬 Xabar", "☰ Menu"]
    ], resize_keyboard=True)

def restart_kb():
    """Keyboard with restart/home menu button"""
    return ReplyKeyboardMarkup([
        ["☰ Menu"]
    ], resize_keyboard=True)

def menu_restart_kb():
    """Single restart button for menu"""
    return ReplyKeyboardMarkup([
        ["🔄 Restart / Boshla"]
    ], resize_keyboard=True)

def xod_wifi_kb(komp_id=None, amal='keldim', xodim_id=None):
    """WiFi prompt with Telegram WebApp"""
    base_url = os.environ.get('APP_URL', 'https://gigandtimebot-production.up.railway.app')
    wifi_app_url = f"{base_url}/wifi-app?xodim_id={xodim_id}&komp_id={komp_id}&amal={amal}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 WiFi tekshir", web_app=WebAppInfo(url=wifi_app_url))],
        [InlineKeyboardButton("📍 GPS kerak", callback_data=f"gps_{amal}_{komp_id}")],
        [InlineKeyboardButton("🏠 Orqaga", callback_data="xod_menu")]
    ])


# ==================== HELPER FUNCTIONS ====================

async def show_statistics(update: Update, xodim_ism: str, stats: dict, sana_1: str, sana_2: str):
    """Display attendance statistics"""
    days_in_range = stats['days_in_range']
    total_entries = stats['total_entries']
    normal_days = stats['normal_days']
    absent_days = stats['absent_days']
    reason_days = stats['reason_days']
    sick_days = stats['sick_days']
    vacation_days = stats['vacation_days']
    late_days = stats['late_days']
    avg_delay = stats['avg_delay']

    # Calculate percentages
    attendance_pct = (total_entries / days_in_range * 100) if days_in_range > 0 else 0

    xabar = f"📊 *{xodim_ism}* — STATISTIKA\n"
    xabar += f"📅 {sana_1} → {sana_2}\n"
    xabar += f"━━━━━━━━━━━━━━━━━━\n\n"

    xabar += f"📈 *DAVOMATLAR*\n"
    xabar += f"• Jami kunlar: {days_in_range}\n"
    xabar += f"• ✅ Kelgan: {normal_days} ({normal_days/days_in_range*100:.1f}%)\n"
    xabar += f"• ❌ Kelmagan (sabsiz): {absent_days}\n"
    xabar += f"• 📋 Boshqa sababli: {reason_days}\n"
    xabar += f"  - 🤒 Kasal: {sick_days}\n"
    xabar += f"  - 🎉 Ta'til: {vacation_days}\n"
    xabar += f"• ⚠️ Kechikish: {late_days}\n"

    if avg_delay > 0:
        xabar += f"• ⏱️ O'rtacha kechikish: {kechikish_format(int(avg_delay))}\n"

    xabar += f"\n📊 *DAVOMATLIK*: {attendance_pct:.1f}%\n"

    await update.message.reply_text(xabar, parse_mode='Markdown')

# ==================== START ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boshidan - Professional main menu for all user types"""
    user_id = update.effective_user.id
    context.user_data.clear()

    try:
        # Check if super admin
        if super_admin_id_tekshir(user_id):
            await update.message.reply_text(
                "👑 *Super Admin Paneli*\n\n"
                "Boshidan - Asosiy menyuga xush kelibsiz!",
                parse_mode='Markdown',
                reply_markup=sa_menu_kb())
            return SA_MENU

        # Check if admin
        conn = connect(); cur = conn.cursor()
        cur.execute("SELECT id,nomi,holat FROM kompaniyalar WHERE admin_id=%s", (user_id,))
        adm_komp = cur.fetchone(); cur.close(); conn.close()

        if adm_komp:
            if adm_komp[2] != 'faol':
                await update.message.reply_text(
                    "⛔️ *Kompaniyangiz faol emas*\n\n"
                    "Tizim bilan bog'lanish uchun murojaat qiling.",
                    parse_mode='Markdown')
                return ConversationHandler.END
            context.user_data['komp_id'] = adm_komp[0]
            await update.message.reply_text(
                f"🏢 *Admin Paneli*\n\n"
                f"Kompaniya: {adm_komp[1]}\n"
                f"Boshidan - Asosiy menyuga xush kelibsiz!",
                parse_mode='Markdown',
                reply_markup=adm_menu_kb())
            return ADM_MENU

        # Check if xodim/HR
        xodim = telegram_id_orqali_xodim(user_id)
        if xodim:
            komp = kompaniya_olish(xodim[3])
            if not komp or komp[4] != 'faol':
                await update.message.reply_text(
                    "⛔️ *Kompaniyangiz faol emas*\n\n"
                    "Tizim bilan bog'lanish uchun murojaat qiling.",
                    parse_mode='Markdown')
                return ConversationHandler.END
            context.user_data.update({'xodim_id': xodim[0], 'ism': xodim[1], 'rol': xodim[2], 'komp_id': xodim[3]})
            if xodim[2] == 'hr':
                await update.message.reply_text(
                    f"👔 *HR Paneli*\n\n"
                    f"Xush kelibsiz, {xodim[1]}!\n"
                    f"Boshidan - Asosiy menyuga xush kelibsiz!",
                    parse_mode='Markdown',
                    reply_markup=hr_menu_kb())
                return HR_MENU
            else:
                await update.message.reply_text(
                    f"👋 *Xodim Paneli*\n\n"
                    f"Xush kelibsiz, {xodim[1]}!\n"
                    f"Boshidan - Asosiy menyuga xush kelibsiz!",
                    parse_mode='Markdown',
                    reply_markup=xod_menu_kb())
                return XOD_MENU

        # New user - request phone
        murojaat = get_murojaat_raqam()
        btn = [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]]
        await update.message.reply_text(
            f"👋 *Xush Kelibsiz!*\n\n"
            f"Tizimga kirish uchun telefon raqamingizni yuboring.\n\n"
            f"❓ *Agar tizimda yo'q bo'lsangiz:*\n"
            f"📞 Murojaat: +998{murojaat}",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
        return TELEFON

    except Exception as e:
        logger.error(f"Start handler error: {e}")
        await update.message.reply_text(
            "❌ *Xatolik yuz berdi*\n\n"
            "Iltimos, keyinroq qayta urinib ko'ring yoki murojaat qiling.",
            parse_mode='Markdown')
        return ConversationHandler.END

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
        await update.message.reply_text(
            "👑 *Super Admin Paneli*\n\n"
            "✅ Kodingiz tasdiqlandi.\n"
            "Boshidan - Asosiy menyuga xush kelibsiz!",
            parse_mode='Markdown',
            reply_markup=sa_menu_kb())
        return SA_MENU

    elif tip == 'admin':
        if kod != context.user_data.get('admin_kod', ''):
            await update.message.reply_text("❌ Noto'g'ri kod!")
            return KOD
        admin_id_saqlash(context.user_data['komp_id'], user_id)
        komp_nomi = context.user_data.get('komp_nomi', 'Kompaniya')
        await update.message.reply_text(
            f"🏢 *Admin Paneli*\n\n"
            f"✅ Kodingiz tasdiqlandi.\n"
            f"Boshidan - Asosiy menyuga xush kelibsiz!",
            parse_mode='Markdown',
            reply_markup=adm_menu_kb())
        return ADM_MENU

    else:
        xodim_id = context.user_data.get('xodim_id')
        xodim = xodim_olish(xodim_id)
        if not xodim or xodim[8] != kod:
            await update.message.reply_text("❌ Noto'g'ri kod!")
            return KOD
        xodim_telegram_saqlash(xodim_id, user_id)
        context.user_data['komp_id'] = xodim[9]
        ism = context.user_data.get('ism', 'Xodim')
        if tip == 'hr':
            await update.message.reply_text(
                f"👔 *HR Paneli*\n\n"
                f"✅ Kodingiz tasdiqlandi.\n"
                f"Xush kelibsiz, {ism}!\n"
                f"Boshidan - Asosiy menyuga xush kelibsiz!",
                parse_mode='Markdown',
                reply_markup=hr_menu_kb())
            return HR_MENU
        else:
            await update.message.reply_text(
                f"👋 *Xodim Paneli*\n\n"
                f"✅ Kodingiz tasdiqlandi.\n"
                f"Xush kelibsiz, {ism}!\n"
                f"Boshidan - Asosiy menyuga xush kelibsiz!",
                parse_mode='Markdown',
                reply_markup=xod_menu_kb())
            return XOD_MENU

# ==================== SUPER ADMIN ====================

async def sa_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    user_id = update.effective_user.id

    if matn == "🏢 Bizneslar":
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
            "📊 Qaysi vaqt oralig'i uchun hisobot?",
            reply_markup=ReplyKeyboardMarkup([
                ["📅 Oylik"],
                ["📆 Yillik"],
                ["🔍 Custom sana"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_HISOBOT_FORMAT

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

    elif matn == "💬 Xabar":
        return await sa_xabar_menu(update, context)

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

    elif matn == "☰ Menu" or matn == "🏠 Bosh menu":
        await update.message.reply_text("Boshidan boshlash uchun:", reply_markup=menu_restart_kb())
        return SA_MENU

    elif matn == "🔄 Restart / Boshla":
        return await start(update, context)

    return SA_MENU

async def sa_kompaniyalar_korsatish(update, context):
    kompaniyalar = barcha_kompaniyalar()
    if not kompaniyalar:
        await update.message.reply_text("📋 Hozircha kompaniya yo'q.",
            reply_markup=ReplyKeyboardMarkup([["➕ Yangi kompaniya", "🔙 Orqaga"]], resize_keyboard=True))
    else:
        xabar = "🏢 *Bizneslar:*\n\n"
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
                ["📆 Sana bo'yicha", "📊 Hisobot"],
                ["🗑 O'chirish", "🔙 Orqaga"]
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
        try:
            logger.info(f"Faollashtirish: Toggling company {komp_id} to faol")
            result = kompaniya_holat_ozgartir(komp_id, 'faol')

            # Verify the status was actually changed
            komp = kompaniya_olish(komp_id)
            if not komp:
                logger.error(f"Faollashtirish: Company {komp_id} not found after update")
                raise Exception("Kompaniya topilmadi")

            if komp[4] != 'faol':
                logger.error(f"Faollashtirish: Company status is {komp[4]}, expected 'faol'")
                raise Exception(f"Holat o'zgartirmadi: {komp[4]}")

            logger.info(f"Faollashtirish: Company {komp_id} successfully set to faol")

            emoji = "✅" if komp[4] == 'faol' else "🔴"
            xabar = (f"✅ FAOLLASHTIRILDI!\n\n"
                    f"🏢 *{komp[1]}*\n"
                    f"Holat: {emoji} {komp[4]}\n\n"
                    f"✅ Status o'zgartirildi, xodim qo'shishni boshlashingiz mumkin")
            await update.message.reply_text(xabar, parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup([
                    ["✏️ Tahrirlash", "⚙️ Funksiyalar"],
                    ["✅ Faollashtirish", "🔴 To'xtatish"],
                    ["👥 Xodimlar", "📅 Davomat"],
                    ["📆 Sana bo'yicha", "📊 Hisobot"],
                    ["🗑 O'chirish", "🔙 Orqaga"]
                ], resize_keyboard=True))
            return SA_KOMP_TANLASH
        except Exception as e:
            logger.error(f"Faollashtirish xatosi: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Xatolik: {str(e)}", reply_markup=sa_menu_kb())
            return SA_MENU

    elif matn == "🔴 To'xtatish":
        try:
            logger.info(f"To'xtatish: Toggling company {komp_id} to nofaol")
            result = kompaniya_holat_ozgartir(komp_id, 'nofaol')

            # Verify the status was actually changed
            komp = kompaniya_olish(komp_id)
            if not komp:
                logger.error(f"To'xtatish: Company {komp_id} not found after update")
                raise Exception("Kompaniya topilmadi")

            if komp[4] != 'nofaol':
                logger.error(f"To'xtatish: Company status is {komp[4]}, expected 'nofaol'")
                raise Exception(f"Holat o'zgartirmadi: {komp[4]}")

            logger.info(f"To'xtatish: Company {komp_id} successfully set to nofaol")

            emoji = "✅" if komp[4] == 'faol' else "🔴"
            xabar = (f"🔴 TO'XTATILDI!\n\n"
                    f"🏢 *{komp[1]}*\n"
                    f"Holat: {emoji} {komp[4]}\n\n"
                    f"⚠️ Ushbu kompaniya faollashtiriguncha xodimlar qo'shilmaydi")
            await update.message.reply_text(xabar, parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup([
                    ["✏️ Tahrirlash", "⚙️ Funksiyalar"],
                    ["✅ Faollashtirish", "🔴 To'xtatish"],
                    ["👥 Xodimlar", "📅 Davomat"],
                    ["📆 Sana bo'yicha", "📊 Hisobot"],
                    ["🗑 O'chirish", "🔙 Orqaga"]
                ], resize_keyboard=True))
            return SA_KOMP_TANLASH
        except Exception as e:
            logger.error(f"To'xtatish xatosi: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Xatolik: {str(e)}", reply_markup=sa_menu_kb())
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
        xodim_id_map = {}  # Display nomeri → Actual ID mapping

        if not xodimlar:
            xabar = "👥 *Xodimlar yo'q.*\n\n➕ Yangi xodim qo'shishni boshlang!"
        else:
            xabar = "👥 *Xodimlar:*\n\n"
            for i, x in enumerate(xodimlar, 1):
                xabar += f"• `{i}` *{x[1]}* (ID:{x[0]}) — {x[2]} | 🎭{x[7]}\n"
                xodim_id_map[str(i)] = x[0]  # Map display number to actual ID

        context.user_data['xodim_id_map'] = xodim_id_map
        tugmalar = [["➕ Xodim qo'shish", "🔙 Orqaga"]]

        if xodimlar:
            tugmalar = []
            for i, x in enumerate(xodimlar, 1):
                tugmalar.append([f"{i}. {x[1]}"])
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

    elif matn == "📆 Sana bo'yicha":
        await update.message.reply_text(
            "📅 Sana kiriting (YYYY-MM-DD):\n\n"
            "Misol: 2026-05-24",
            reply_markup=ReplyKeyboardRemove())
        return SA_KOMP_DAV_SANA

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

async def sa_komp_dav_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin - View attendance for a specific date"""
    sana_matn = update.message.text.strip()
    komp_id = context.user_data.get('sa_komp_id')
    komp = kompaniya_olish(komp_id)
    komp_nomi = komp[1] if komp else "Noma'lum"

    # Validate date format
    if len(sana_matn) != 10 or sana_matn[4] != '-' or sana_matn[7] != '-':
        await update.message.reply_text(
            f"❌ Noto'g'ri format!\n\n"
            f"Iltimos format shunga mos kelsin: YYYY-MM-DD\n"
            f"Misol: 2026-05-24",
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return SA_KOMP_DAV_SANA

    try:
        davomatlar = kompaniya_davomati(komp_id, sana_matn)

        if not davomatlar:
            await update.message.reply_text(
                f"❌ {komp_nomi} kompaniyada {sana_matn} sanada davomat yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return SA_KOMP_DAV_SANA

        xabar = f"📅 *{sana_matn} - {komp_nomi}:*\n\n"
        xabar += f"👥 Jami: {len(davomatlar)} ta xodim\n\n"

        for d in davomatlar:
            ism, sana, keldi, ketdi, ish_soat, kechikish, holat = d[0], d[1], d[2], d[3], d[4], d[5], d[6]
            xabar += f"👤 *{ism}*\n"
            xabar += f"  ✅ Keldi: {keldi or '—'}\n"
            xabar += f"  🚪 Ketdi: {ketdi or '—'}\n"
            if ish_soat:
                soat = int(ish_soat)
                minut = int((ish_soat - soat) * 60)
                xabar += f"  ⏱️ Ish soati: {soat}h {minut}m\n"
            if kechikish and kechikish > 0:
                xabar += f"  ⚠️ Kechikish: {kechikish_format(kechikish)}\n"
            xabar += f"  📊 Holat: {holat}\n\n"

        await update.message.reply_text(xabar, parse_mode='Markdown', reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return SA_KOMP_DAV_SANA
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return SA_KOMP_DAV_SANA

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
        # Go back to company menu
        komp = kompaniya_olish(komp_id)
        emoji = "✅" if komp[4] == 'faol' else "🔴"
        xabar = (f"🏢 *{komp[1]}*\n━━━━━━━━━━━━━━━\n"
                f"📞 Admin tel: {komp[2] or '—'}\n"
                f"🔑 Admin kodi: `{komp[13] or '—'}`\n"
                f"📍 GPS: {komp[5]}, {komp[6]}\n"
                f"📏 Radius: {komp[7]}m\n"
                f"Holat: {emoji} {komp[4]}\n"
                f"━━━━━━━━━━━━━━━")
        await update.message.reply_text(xabar, parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["✏️ Tahrirlash", "⚙️ Funksiyalar"],
                ["✅ Faollashtirish", "🔴 To'xtatish"],
                ["👥 Xodimlar", "📅 Davomat"],
                ["📆 Sana bo'yicha", "📊 Hisobot"],
                ["🗑 O'chirish", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_KOMP_TANLASH
    if matn == "➕ Xodim qo'shish":
        # FIX: Set komp_id for the shared employee adding flow
        context.user_data['komp_id'] = komp_id
        await update.message.reply_text("👤 Xodim ismini kiriting:", reply_markup=ReplyKeyboardRemove())
        return ADM_XODIM_ISM
    try:
        # Get actual xodim_id from mapping (display number → actual ID)
        display_num = matn.split(".")[0].strip()
        xodim_id_map = context.user_data.get('xodim_id_map', {})
        xodim_id = xodim_id_map.get(display_num, int(display_num))  # Fallback to direct parse if no mapping
        context.user_data['tahrir_xodim_id'] = xodim_id
        x = xodim_olish(xodim_id)
        await update.message.reply_text(
            f"👤 *{x[1]}*\n💼 {x[3]} | 🎭 {x[7]}\n🔐 Kod: `{x[8]}`\n\nNima qilish?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["✏️ Tahrirlash", "🗑 O'chirish"],
                ["📅 Davomatni ko'rish", "📊 Statistika"],
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
    elif matn == "📅 Davomatni ko'rish":
        context.user_data['view_xodim_id'] = xodim_id
        await update.message.reply_text(
            f"📅 Sana (YYYY-MM-DD) yoki oy (YYYY-MM):\n\nMisol: 2026-05-24 yoki 2026-05",
            reply_markup=ReplyKeyboardRemove())
        return SA_KOMP_XODIM_VIEW_SANA
    elif matn == "📊 Statistika":
        context.user_data['stat_xodim_id'] = xodim_id
        await update.message.reply_text(
            "📊 Davr tanlang:",
            reply_markup=ReplyKeyboardMarkup([
                ["📅 Oylik", "📆 Yillik"],
                ["📍 Custom sana", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_KOMP_XODIM_STAT_FORMAT
    elif matn == "🗑 O'chirish":
        komp_id = context.user_data.get('sa_komp_id')
        x = xodim_olish(xodim_id)

        # Security check: xodim kompaniyaga tegishli ekanligini tekshir
        if not x or x[9] != komp_id:
            await update.message.reply_text("❌ Bu xodim bu kompaniyaga tegishli emas!", reply_markup=sa_menu_kb())
            return SA_MENU

        context.user_data['delete_xodim_ism'] = x[1]
        await update.message.reply_text(
            f"⚠️ *{x[1]}* xodimni o'chirmoqchisiz!\n\n"
            f"Tasdiqlash uchun *sizning maxfiy kodingizni* kiriting:",
            parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return SA_XODIM_DELETE_KOD
    elif matn == "✏️ Tahrirlash":
        await update.message.reply_text("Nimani tahrirlash?",
            reply_markup=ReplyKeyboardMarkup([
                ["📝 Ism", "💼 Lavozim"],
                ["📱 Telefon", "💰 Oylik"],
                ["⏰ Ish vaqti", "🎭 Rol"],
                ["🔑 Kod", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_KOMP_XODIM_TAHRIR
    return SA_KOMP_XODIM_AMAL

async def sa_xodim_delete_kod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin o'chirish kodi tekshiruvi"""
    try:
        kod = update.message.text.strip()
        user_id = update.effective_user.id

        # Super Admin kodini tekshir
        if not super_admin_kod_tekshir(kod):
            await update.message.reply_text("❌ Noto'g'ri kod! O'chirish bekor qilindi.", reply_markup=sa_menu_kb())
            return SA_MENU

        # Kod to'g'ri, xodimni o'chir
        komp_id = context.user_data.get('sa_komp_id')
        xodim_id = context.user_data.get('tahrir_xodim_id')
        xodim_ism = context.user_data.get('delete_xodim_ism', 'Unknown')

        if not xodim_id or not komp_id:
            await update.message.reply_text("❌ Xatolik: Ma'lumot yo'q!", reply_markup=sa_menu_kb())
            return SA_MENU

        # AUDIT LOG - FIRST (before delete!)
        user_ism = update.effective_user.first_name or 'Super Admin'
        tafsilot = f"Xodim o'chirildi: {xodim_ism}"
        audit_log_qoshish(komp_id, 'XODIM_O\'CHIRISH', tafsilot, xodim_id, user_id=user_id, user_ism=user_ism)

        # Then delete xodim
        xodim_ochirish(xodim_id)

        # Show xodim list again
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("🗑 Xodim o'chirildi! ✅\n\n👥 Boshqa xodim yo'q.", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return SA_KOMP_XODIM_TANLASH

        xabar = "🗑 Xodim o'chirildi! ✅\n\n👥 *Xodimlar:*\n\n"
        tugmalar = []
        xodim_id_map = {}  # Display nomeri → Actual ID mapping
        for i, x in enumerate(xodimlar, 1):
            xabar += f"• `{i}` *{x[1]}* — {x[2]} | 🎭{x[7]}\n"
            tugmalar.append([f"{i}. {x[1]}"])
            xodim_id_map[str(i)] = x[0]  # Map display number to actual ID
        context.user_data['xodim_id_map'] = xodim_id_map
        tugmalar.append(["➕ Xodim qo'shish", "🔙 Orqaga"])
        await update.message.reply_text(xabar, parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return SA_KOMP_XODIM_TANLASH
    except Exception as e:
        logger.error(f"Super Admin xodim o'chirish xatosi: {e}")
        await update.message.reply_text(f"❌ Xatolik: {e}", reply_markup=sa_menu_kb())
        return SA_MENU

async def sa_komp_xodim_tahrir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    maydon_map = {"📝 Ism": "ism", "💼 Lavozim": "lavozim", "📱 Telefon": "telefon", "💰 Oylik": "oylik", "🎭 Rol": "rol", "🔑 Kod": "kod"}
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

async def sa_komp_xodim_view_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin - View specific employee attendance"""
    matn = update.message.text.strip()

    if matn == "🔙 Orqaga":
        komp_id = context.user_data.get('sa_komp_id')
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("👥 *Xodimlar yo'q*\n\nYangi xodim qo'shing:",
                reply_markup=ReplyKeyboardMarkup([["➕ Xodim qo'shish", "🔙 Orqaga"]], resize_keyboard=True))
            return SA_KOMP_XODIM_TANLASH

        xabar = "👥 *Xodimlar:*\n\n"
        tugmalar = []
        xodim_id_map = {}
        for i, x in enumerate(xodimlar, 1):
            xabar += f"• `{i}` *{x[1]}* (ID:{x[0]}) — {x[2]} | 🎭{x[7]}\n"
            tugmalar.append([f"{i}. {x[1]}"])
            xodim_id_map[str(i)] = x[0]
        context.user_data['xodim_id_map'] = xodim_id_map
        tugmalar.append(["➕ Xodim qo'shish", "🔙 Orqaga"])
        await update.message.reply_text(xabar, parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return SA_KOMP_XODIM_TANLASH

    sana_matn = matn
    xodim_id = context.user_data.get('view_xodim_id')
    xodim = xodim_olish(xodim_id)
    xodim_ism = xodim[1] if xodim else "Noma'lum"

    # Validate date format
    if not (len(sana_matn) == 7 or len(sana_matn) == 10):  # YYYY-MM or YYYY-MM-DD
        await update.message.reply_text(
            f"❌ Noto'g'ri format!\n\n"
            f"Iltimos, format shunga mos kelsin:\n"
            f"• Oy uchun: 2026-05\n"
            f"• Kun uchun: 2026-05-24",
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return SA_KOMP_XODIM_VIEW_SANA

    try:
        davomatlar = xodim_davomati(xodim_id, sana_matn if len(sana_matn) == 7 else None)

        # Filter by specific date if provided
        if len(sana_matn) == 10:
            davomatlar = [d for d in davomatlar if d[1] == sana_matn]

        if not davomatlar:
            await update.message.reply_text(
                f"❌ {xodim_ism} uchun {sana_matn} davomati yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return SA_KOMP_XODIM_VIEW_SANA

        xabar = f"📅 *{xodim_ism}* — {sana_matn}:\n\n"
        xabar += f"👥 Jami: {len(davomatlar)} ta\n\n"

        for d in davomatlar:
            sana, keldi, ketdi, ish_soat, kechikish, holat = d[1], d[2], d[3], d[4], d[5], d[6]
            xabar += f"📅 *{sana}*\n"
            xabar += f"  ⏰ {keldi or '—'} → {ketdi or '—'}"
            if kechikish and kechikish > 0:
                xabar += f" ⚠️{kechikish_format(kechikish)}"
            xabar += f"\n  📋 {holat}\n\n"

        await update.message.reply_text(xabar, parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return SA_KOMP_XODIM_VIEW_SANA
    except Exception as e:
        logger.error(f"SA xodim davomati ko'rish xatosi: {e}")
        await update.message.reply_text(f"❌ Xatolik: {e}",
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return SA_KOMP_XODIM_VIEW_SANA

async def sa_komp_xodim_stat_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin - Select statistics period format"""
    matn = update.message.text
    xodim_id = context.user_data.get('stat_xodim_id')
    xodim = xodim_olish(xodim_id)
    xodim_ism = xodim[1] if xodim else "Noma'lum"

    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    elif matn == "📅 Oylik":
        await update.message.reply_text(
            f"📅 Oy kiriting (YYYY-MM):\n\nMisol: 2026-05",
            reply_markup=ReplyKeyboardRemove())
        context.user_data['stat_format'] = 'monthly'
        return SA_KOMP_XODIM_STAT_SANA_1
    elif matn == "📆 Yillik":
        bugun = hozir()
        sana1 = bugun.replace(month=1, day=1).strftime("%Y-%m-%d")
        sana2 = bugun.strftime("%Y-%m-%d")
        stats = xodim_statistika(xodim_id, sana1, sana2)
        await show_statistics(update, xodim_ism, stats, sana1, sana2)
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    elif matn == "📍 Custom sana":
        await update.message.reply_text(
            f"📅 Boshlang'ich sana (YYYY-MM-DD):\n\nMisol: 2026-01-01",
            reply_markup=ReplyKeyboardRemove())
        context.user_data['stat_format'] = 'custom'
        return SA_KOMP_XODIM_STAT_SANA_1
    return SA_KOMP_XODIM_STAT_FORMAT

async def sa_komp_xodim_stat_sana_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin - Statistics first date input"""
    sana_matn = update.message.text.strip()
    xodim_id = context.user_data.get('stat_xodim_id')
    xodim = xodim_olish(xodim_id)
    xodim_ism = xodim[1] if xodim else "Noma'lum"
    stat_format = context.user_data.get('stat_format')

    try:
        if stat_format == 'monthly':
            if len(sana_matn) != 7 or sana_matn[4] != '-':
                raise ValueError("Invalid format")
            sana1 = f"{sana_matn}-01"
            yil, oy = sana_matn.split('-')
            # Get last day of month
            if oy == '12':
                sana2 = f"{int(yil)+1}-01-01"
            else:
                sana2 = f"{yil}-{str(int(oy)+1).zfill(2)}-01"
            sana2 = (datetime.strptime(sana2, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            stats = xodim_statistika(xodim_id, sana1, sana2)
            await show_statistics(update, xodim_ism, stats, sana1, sana2)
            await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
            return SA_MENU
        else:  # custom
            if len(sana_matn) != 10 or sana_matn[4] != '-' or sana_matn[7] != '-':
                raise ValueError("Invalid format")
            context.user_data['stat_sana_1'] = sana_matn
            await update.message.reply_text(
                f"📅 Tugatish sanasi (YYYY-MM-DD):\n\nMisol: 2026-12-31",
                reply_markup=ReplyKeyboardRemove())
            return SA_KOMP_XODIM_STAT_SANA_2
    except:
        await update.message.reply_text(
            f"❌ Noto'g'ri format!\n\nIltimos shunga mos kelsin: YYYY-MM-DD",
            reply_markup=ReplyKeyboardRemove())
        return SA_KOMP_XODIM_STAT_SANA_1

async def sa_komp_xodim_stat_sana_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin - Statistics second date input (custom range end)"""
    sana_matn = update.message.text.strip()
    xodim_id = context.user_data.get('stat_xodim_id')
    sana1 = context.user_data.get('stat_sana_1')
    xodim = xodim_olish(xodim_id)
    xodim_ism = xodim[1] if xodim else "Noma'lum"

    try:
        if len(sana_matn) != 10 or sana_matn[4] != '-' or sana_matn[7] != '-':
            raise ValueError("Invalid format")
        stats = xodim_statistika(xodim_id, sana1, sana_matn)
        await show_statistics(update, xodim_ism, stats, sana1, sana_matn)
        await update.message.reply_text("👑 Menu:", reply_markup=sa_menu_kb())
        return SA_MENU
    except:
        await update.message.reply_text(
            f"❌ Noto'g'ri format!\n\nIltimos shunga mos kelsin: YYYY-MM-DD",
            reply_markup=ReplyKeyboardRemove())
        return SA_KOMP_XODIM_STAT_SANA_2

async def sa_adm_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    user_id = update.effective_user.id

    # KOD CHECK AVVAL! (Bu boshqa hammasidan OLDIN tekshirilishi kerak)
    if context.user_data.get('sa_kod_amal') == 'qosh':
        # Super Admin yaratish uchun kod tasdiqlash
        from database import super_admin_kod_tekshir
        telefon = context.user_data.get('yangi_sa_tel')
        ism = context.user_data.get('yangi_sa_ism')
        if super_admin_kod_tekshir(matn.strip()):
            if super_admin_qoshish(telefon, ism):
                await update.message.reply_text(f"✅ Super Admin qo'shildi!\n👤 {ism}\n📱 {telefon}", reply_markup=sa_menu_kb())
                context.user_data.pop('sa_kod_amal', None)
                context.user_data.pop('yangi_sa_tel', None)
                context.user_data.pop('yangi_sa_ism', None)
                return SA_MENU
            else:
                await update.message.reply_text("⚠️ Bu telefon allaqachon Super Admin!", reply_markup=sa_menu_kb())
                context.user_data.pop('sa_kod_amal', None)
                return SA_MENU
        else:
            await update.message.reply_text("❌ Kod noto'g'ri!", reply_markup=ReplyKeyboardRemove())
            return SA_ADM_LIST
    elif context.user_data.get('sa_kod_amal') == 'ochir':
        # Super Admin o'chirish uchun kod tasdiqlash
        from database import super_admin_kod_tekshir
        if super_admin_kod_tekshir(matn.strip()):
            sa_id = context.user_data.get('ochir_sa_id')
            super_admin_ochirish(sa_id)
            await update.message.reply_text("✅ Admin o'chirildi!", reply_markup=sa_menu_kb())
            context.user_data.pop('sa_amal', None)
            context.user_data.pop('sa_kod_amal', None)
            context.user_data.pop('ochir_sa_id', None)
            return SA_MENU
        else:
            await update.message.reply_text("❌ Kod noto'g'ri!", reply_markup=ReplyKeyboardRemove())
            return SA_ADM_LIST

    # Qolgan button presslar
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
            context.user_data['ochir_sa_id'] = sa_id
            # Kod talab qilish - xavfsizlik
            await update.message.reply_text("🔐 O'chiring tasdiqlamasligi uchun kod kiriting:", reply_markup=ReplyKeyboardRemove())
            context.user_data['sa_kod_amal'] = 'ochir'
            return SA_ADM_LIST
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
    context.user_data['yangi_sa_ism'] = ism
    # Kod talab qilish - xavfsizlik
    await update.message.reply_text("🔐 Tasdiqlovchi kod kiriting (Super Admin kodi):", reply_markup=ReplyKeyboardRemove())
    context.user_data['sa_kod_amal'] = 'qosh'
    return SA_ADM_LIST

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
            "📊 Qaysi vaqt oralig'i uchun hisobot?",
            reply_markup=ReplyKeyboardMarkup([
                ["📅 Oylik"],
                ["📆 Yillik"],
                ["🔍 Custom sana"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return ADM_HISOBOT_FORMAT

    elif matn == "💬 Xabar":
        return await adm_xabar_menu(update, context)

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

    elif matn == "☰ Menu" or matn == "🏠 Bosh menu":
        await update.message.reply_text("Boshidan boshlash uchun:", reply_markup=menu_restart_kb())
        return ADM_MENU

    elif matn == "🔄 Restart / Boshla":
        return await start(update, context)

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
                xabar += f"• `ID:{x[0]}` *{x[1]}* — {x[2]}\n  📞 {x[3]} | 💰 {x[4]:,.0f} | 🎭 {x[7]}\n  ⏰ {x[5]}-{x[6]} | 🔐 `{x[8]}`\n\n"
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

        # Sequential numbering with ID mapping
        tugmalar = []
        xodim_id_map = {}
        for i, x in enumerate(xodimlar, 1):
            tugmalar.append([f"{i}. {x[1]}"])
            xodim_id_map[str(i)] = x[0]  # Map display number to actual ID
        context.user_data['xodim_id_map'] = xodim_id_map

        tugmalar.append(["➕ Xodim qo'shish", "🔙 Orqaga"])
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

    try:
        komp_id = context.user_data.get('komp_id')

        # Validate komp_id is set
        if not komp_id:
            logger.error("ADM_XODIM_ROL: komp_id not set in context!")
            await update.message.reply_text("❌ Xatolik: Kompaniya tanlangan emas!", reply_markup=adm_menu_kb())
            return ADM_MENU

        # Verify company exists and is faol
        komp = kompaniya_olish(komp_id)
        if not komp:
            logger.error(f"ADM_XODIM_ROL: Company {komp_id} not found!")
            await update.message.reply_text("❌ Xatolik: Kompaniya topilmadi!", reply_markup=adm_menu_kb())
            return ADM_MENU

        if komp[4] != 'faol':
            logger.warning(f"ADM_XODIM_ROL: Company {komp_id} is not faol (status: {komp[4]})")
            await update.message.reply_text(
                f"❌ Xatolik: Kompaniya faol emas!\n\n"
                f"Holat: 🔴 {komp[4]}\n\n"
                f"Iltimos, kompaniyani faollashtiring va qayta urinib ko'ring.",
                reply_markup=adm_menu_kb())
            return ADM_MENU

        kod = random_kod()
        logger.info(f"ADM_XODIM_ROL: Adding employee {context.user_data['y_ism']} to company {komp_id} (status: {komp[4]})")

        xodim_id = xodim_qoshish(context.user_data['y_ism'], context.user_data['y_tel'],
                      context.user_data['y_lav'], context.user_data['y_oylik'],
                      context.user_data['y_bosh'], context.user_data['y_tug'],
                      komp_id, rol, kod)

        if not xodim_id:
            logger.error(f"ADM_XODIM_ROL: xodim_qoshish returned None for {context.user_data['y_ism']}")
            await update.message.reply_text("❌ Xatolik: Xodim qo'shilmadi!", reply_markup=adm_menu_kb())
            return ADM_MENU

        # AUDIT LOG
        user_id = update.effective_user.id
        user_ism = update.effective_user.first_name or 'Admin'
        tafsilot = f"Yangi xodim: {context.user_data['y_ism']} | Tel: {context.user_data['y_tel']} | Rol: {rol}"
        audit_log_qoshish(komp_id, 'XODIM_QO\'SHISH', tafsilot, xodim_id, user_id=user_id, user_ism=user_ism)

        # Check if Super Admin (sa_komp_id set) or regular Admin (komp_id set)
        is_sa = context.user_data.get('sa_komp_id') is not None

        logger.info(f"ADM_XODIM_ROL: Employee {xodim_id} added successfully, is_sa={is_sa}")

        await update.message.reply_text(
            f"✅ *Xodim qo'shildi!*\n\n👤 {context.user_data['y_ism']}\n"
            f"💼 {context.user_data['y_lav']}\n🎭 {rol}\n🔑 Kod: `{kod}`\n\n⚠️ Kodni xodimga bering!",
            parse_mode='Markdown', reply_markup=sa_menu_kb() if is_sa else adm_menu_kb())
        return SA_MENU if is_sa else ADM_MENU

    except Exception as e:
        logger.error(f"ADM_XODIM_ROL Error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Xatolik: {str(e)}", reply_markup=adm_menu_kb())
        return ADM_MENU

async def adm_xodim_delete_kod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin o'chirish kodi tekshiruvi"""
    try:
        kod = update.message.text.strip()
        user_id = update.effective_user.id
        komp_id = context.user_data.get('komp_id')
        xodim_id = context.user_data.get('tahrir_xodim_id')
        xodim_ism = context.user_data.get('delete_xodim_ism', 'Unknown')

        if not xodim_id or not komp_id:
            await update.message.reply_text("❌ Xatolik: Ma'lumot yo'q!", reply_markup=adm_menu_kb())
            return ADM_MENU

        # Admin kodini tekshir
        conn = connect(); cur = conn.cursor()
        cur.execute("SELECT admin_kod FROM kompaniyalar WHERE id=%s", (komp_id,))
        row = cur.fetchone(); cur.close(); conn.close()

        if not row or row[0] != kod:
            await update.message.reply_text("❌ Noto'g'ri kod! O'chirish bekor qilindi.", reply_markup=adm_menu_kb())
            return ADM_MENU

        # AUDIT LOG - FIRST (before delete!)
        user_ism = update.effective_user.first_name or 'Admin'
        tafsilot = f"Xodim o'chirildi: {xodim_ism}"
        audit_log_qoshish(komp_id, 'XODIM_O\'CHIRISH', tafsilot, xodim_id, user_id=user_id, user_ism=user_ism)

        # Then delete xodim
        xodim_ochirish(xodim_id)

        # Show updated xodim list with sequential numbering
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("🗑 Xodim o'chirildi! ✅\n\n👥 Boshqa xodim yo'q.", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_XODIM_TANLASH

        tugmalar = []
        xodim_id_map = {}
        for i, x in enumerate(xodimlar, 1):
            tugmalar.append([f"{i}. {x[1]}"])
            xodim_id_map[str(i)] = x[0]
        context.user_data['xodim_id_map'] = xodim_id_map
        tugmalar.append(["➕ Xodim qo'shish", "🔙 Orqaga"])
        await update.message.reply_text("🗑 Xodim o'chirildi! ✅\n\n👥 *Xodimlar:*\n" +
            "\n".join([f"• `{i}` *{x[1]}*" for i, x in enumerate(xodimlar, 1)]),
            parse_mode='Markdown', reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return ADM_XODIM_TANLASH
    except Exception as e:
        logger.error(f"Admin xodim o'chirish xatosi: {e}")
        await update.message.reply_text(f"❌ Xatolik: {e}", reply_markup=adm_menu_kb())
        return ADM_MENU

async def adm_xodim_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU
    if matn == "➕ Xodim qo'shish":
        await update.message.reply_text("👤 Xodim ismini kiriting:", reply_markup=ReplyKeyboardRemove())
        return ADM_XODIM_ISM
    try:
        # Get actual xodim_id from mapping (display number → actual ID)
        display_num = matn.split(".")[0].strip()
        xodim_id_map = context.user_data.get('xodim_id_map', {})
        xodim_id = xodim_id_map.get(display_num, int(display_num))  # Fallback to direct parse if no mapping
        context.user_data['tahrir_xodim_id'] = xodim_id
        amal = context.user_data.get('xodim_amal')
        if amal == 'ochir':
            komp_id = context.user_data.get('komp_id')
            x = xodim_olish(xodim_id)

            # Security check: xodim admin'ning tashkilotiga tegishli ekanligini tekshir
            if not x or x[9] != komp_id:
                await update.message.reply_text("❌ Bu xodim sizning tashkilotingizga tegishli emas!", reply_markup=adm_menu_kb())
                return ADM_MENU

            context.user_data['delete_xodim_ism'] = x[1]
            await update.message.reply_text(
                f"⚠️ *{x[1]}* xodimni o'chirmoqchisiz!\n\n"
                f"Tasdiqlash uchun *sizning maxfiy kodingizni* kiriting:",
                parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
            return ADM_XODIM_DELETE_KOD
        x = xodim_olish(xodim_id)
        await update.message.reply_text(
            f"✏️ *{x[1]}*\n💼 {x[3]} | 🎭 {x[7]}\n🔐 `{x[8]}`\n\nNimani tahrirlash?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["📝 Ism", "💼 Lavozim"],
                ["📱 Telefon", "💰 Oylik"],
                ["⏰ Ish vaqti", "🎭 Rol"],
                ["🔑 Kod"],
                ["📅 Davomatni ko'rish", "📊 Statistika"],
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
    elif matn == "📅 Davomatni ko'rish":
        xodim_id = context.user_data.get('tahrir_xodim_id')
        context.user_data['view_xodim_id'] = xodim_id
        await update.message.reply_text(
            f"📅 Sana (YYYY-MM-DD) yoki oy (YYYY-MM):\n\nMisol: 2026-05-24 yoki 2026-05",
            reply_markup=ReplyKeyboardRemove())
        return ADM_KOMP_XODIM_VIEW_SANA
    elif matn == "📊 Statistika":
        xodim_id = context.user_data.get('tahrir_xodim_id')
        context.user_data['stat_xodim_id'] = xodim_id
        await update.message.reply_text(
            "📊 Davr tanlang:",
            reply_markup=ReplyKeyboardMarkup([
                ["📅 Oylik", "📆 Yillik"],
                ["📍 Custom sana", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return ADM_KOMP_XODIM_STAT_FORMAT
    maydon_map = {"📝 Ism": "ism", "💼 Lavozim": "lavozim", "📱 Telefon": "telefon", "💰 Oylik": "oylik", "🎭 Rol": "rol", "🔑 Kod": "kod"}
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

async def adm_komp_xodim_view_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin - View specific employee attendance"""
    matn = update.message.text.strip()

    if matn == "🔙 Orqaga":
        komp_id = context.user_data.get('komp_id')
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("👥 *Xodimlar yo'q*\n\nYangi xodim qo'shing:",
                reply_markup=ReplyKeyboardMarkup([["➕ Xodim qo'shish", "🔙 Orqaga"]], resize_keyboard=True))
            return ADM_XODIM_TANLASH

        xabar = "👥 *Xodimlar:*\n\n"
        tugmalar = []
        xodim_id_map = {}
        for i, x in enumerate(xodimlar, 1):
            xabar += f"• `{i}` *{x[1]}* (ID:{x[0]}) — {x[2]} | 🎭{x[7]}\n"
            tugmalar.append([f"{i}. {x[1]}"])
            xodim_id_map[str(i)] = x[0]
        context.user_data['xodim_id_map'] = xodim_id_map
        tugmalar.append(["➕ Xodim qo'shish", "🔙 Orqaga"])
        await update.message.reply_text(xabar, parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return ADM_XODIM_TANLASH

    sana_matn = matn
    xodim_id = context.user_data.get('view_xodim_id')
    xodim = xodim_olish(xodim_id)
    xodim_ism = xodim[1] if xodim else "Noma'lum"

    # Validate date format
    if not (len(sana_matn) == 7 or len(sana_matn) == 10):  # YYYY-MM or YYYY-MM-DD
        await update.message.reply_text(
            f"❌ Noto'g'ri format!\n\n"
            f"Iltimos, format shunga mos kelsin:\n"
            f"• Oy uchun: 2026-05\n"
            f"• Kun uchun: 2026-05-24",
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return ADM_KOMP_XODIM_VIEW_SANA

    try:
        davomatlar = xodim_davomati(xodim_id, sana_matn if len(sana_matn) == 7 else None)

        # Filter by specific date if provided
        if len(sana_matn) == 10:
            davomatlar = [d for d in davomatlar if d[1] == sana_matn]

        if not davomatlar:
            await update.message.reply_text(
                f"❌ {xodim_ism} uchun {sana_matn} davomati yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_KOMP_XODIM_VIEW_SANA

        xabar = f"📅 *{xodim_ism}* — {sana_matn}:\n\n"
        xabar += f"👥 Jami: {len(davomatlar)} ta\n\n"

        for d in davomatlar:
            sana, keldi, ketdi, ish_soat, kechikish, holat = d[1], d[2], d[3], d[4], d[5], d[6]
            xabar += f"📅 *{sana}*\n"
            xabar += f"  ⏰ {keldi or '—'} → {ketdi or '—'}"
            if kechikish and kechikish > 0:
                xabar += f" ⚠️{kechikish_format(kechikish)}"
            xabar += f"\n  📋 {holat}\n\n"

        await update.message.reply_text(xabar, parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return ADM_KOMP_XODIM_VIEW_SANA
    except Exception as e:
        logger.error(f"Admin xodim davomati ko'rish xatosi: {e}")
        await update.message.reply_text(f"❌ Xatolik: {e}",
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return ADM_KOMP_XODIM_VIEW_SANA

async def adm_komp_xodim_stat_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin - Select statistics period format"""
    matn = update.message.text
    xodim_id = context.user_data.get('stat_xodim_id')
    xodim = xodim_olish(xodim_id)
    xodim_ism = xodim[1] if xodim else "Noma'lum"

    if matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU
    elif matn == "📅 Oylik":
        await update.message.reply_text(
            f"📅 Oy kiriting (YYYY-MM):\n\nMisol: 2026-05",
            reply_markup=ReplyKeyboardRemove())
        context.user_data['stat_format'] = 'monthly'
        return ADM_KOMP_XODIM_STAT_SANA_1
    elif matn == "📆 Yillik":
        bugun = hozir()
        sana1 = bugun.replace(month=1, day=1).strftime("%Y-%m-%d")
        sana2 = bugun.strftime("%Y-%m-%d")
        stats = xodim_statistika(xodim_id, sana1, sana2)
        await show_statistics(update, xodim_ism, stats, sana1, sana2)
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU
    elif matn == "📍 Custom sana":
        await update.message.reply_text(
            f"📅 Boshlang'ich sana (YYYY-MM-DD):\n\nMisol: 2026-01-01",
            reply_markup=ReplyKeyboardRemove())
        context.user_data['stat_format'] = 'custom'
        return ADM_KOMP_XODIM_STAT_SANA_1
    return ADM_KOMP_XODIM_STAT_FORMAT

async def adm_komp_xodim_stat_sana_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin - Statistics first date input"""
    sana_matn = update.message.text.strip()
    xodim_id = context.user_data.get('stat_xodim_id')
    xodim = xodim_olish(xodim_id)
    xodim_ism = xodim[1] if xodim else "Noma'lum"
    stat_format = context.user_data.get('stat_format')

    try:
        if stat_format == 'monthly':
            if len(sana_matn) != 7 or sana_matn[4] != '-':
                raise ValueError("Invalid format")
            sana1 = f"{sana_matn}-01"
            yil, oy = sana_matn.split('-')
            # Get last day of month
            if oy == '12':
                sana2 = f"{int(yil)+1}-01-01"
            else:
                sana2 = f"{yil}-{str(int(oy)+1).zfill(2)}-01"
            sana2 = (datetime.strptime(sana2, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            stats = xodim_statistika(xodim_id, sana1, sana2)
            await show_statistics(update, xodim_ism, stats, sana1, sana2)
            await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
            return ADM_MENU
        else:  # custom
            if len(sana_matn) != 10 or sana_matn[4] != '-' or sana_matn[7] != '-':
                raise ValueError("Invalid format")
            context.user_data['stat_sana_1'] = sana_matn
            await update.message.reply_text(
                f"📅 Tugatish sanasi (YYYY-MM-DD):\n\nMisol: 2026-12-31",
                reply_markup=ReplyKeyboardRemove())
            return ADM_KOMP_XODIM_STAT_SANA_2
    except:
        await update.message.reply_text(
            f"❌ Noto'g'ri format!\n\nIltimos shunga mos kelsin: YYYY-MM-DD",
            reply_markup=ReplyKeyboardRemove())
        return ADM_KOMP_XODIM_STAT_SANA_1

async def adm_komp_xodim_stat_sana_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin - Statistics second date input (custom range end)"""
    sana_matn = update.message.text.strip()
    xodim_id = context.user_data.get('stat_xodim_id')
    sana1 = context.user_data.get('stat_sana_1')
    xodim = xodim_olish(xodim_id)
    xodim_ism = xodim[1] if xodim else "Noma'lum"

    try:
        if len(sana_matn) != 10 or sana_matn[4] != '-' or sana_matn[7] != '-':
            raise ValueError("Invalid format")
        stats = xodim_statistika(xodim_id, sana1, sana_matn)
        await show_statistics(update, xodim_ism, stats, sana1, sana_matn)
        await update.message.reply_text("🏢 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU
    except:
        await update.message.reply_text(
            f"❌ Noto'g'ri format!\n\nIltimos shunga mos kelsin: YYYY-MM-DD",
            reply_markup=ReplyKeyboardRemove())
        return ADM_KOMP_XODIM_STAT_SANA_2

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
    elif matn == "📆 Sana bo'yicha":
        await update.message.reply_text(
            "📅 Sana kiriting (YYYY-MM-DD):\n\n"
            "Misol: 2026-05-24",
            reply_markup=ReplyKeyboardRemove())
        context.user_data['dav_amal'] = 'sana_boyicha'
        return ADM_DAV_SANA
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

        # Sequential numbering with ID mapping
        tugmalar = []
        xodim_id_map = {}
        for i, x in enumerate(xodimlar, 1):
            tugmalar.append([f"{i}. {x[1]}"])
            xodim_id_map[str(i)] = x[0]
        context.user_data['xodim_id_map'] = xodim_id_map

        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text("Xodim tanlang:", reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        context.user_data['dav_amal'] = 'kiritish'; return ADM_DAV_XODIM
    elif matn == "✏️ Tahrirlash":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!"); return ADM_DAV_MENU

        # Sequential numbering with ID mapping
        tugmalar = []
        xodim_id_map = {}
        for i, x in enumerate(xodimlar, 1):
            tugmalar.append([f"{i}. {x[1]}"])
            xodim_id_map[str(i)] = x[0]
        context.user_data['xodim_id_map'] = xodim_id_map

        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text("Xodim tanlang:", reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        context.user_data['dav_amal'] = 'tahrirlash'; return ADM_DAV_XODIM
    return ADM_DAV_MENU

async def adm_dav_xodim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("📅 Davomat:", reply_markup=ReplyKeyboardMarkup([
            ["📋 Bugungi","📊 Barchasi"],["📆 Sana bo'yicha","✍️ Kiritish"],
            ["✏️ Tahrirlash","🔙 Orqaga"]
        ], resize_keyboard=True))
        return ADM_DAV_MENU
    try:
        # Get actual xodim_id from mapping (display number → actual ID)
        display_num = matn.split(".")[0].strip()
        xodim_id_map = context.user_data.get('xodim_id_map', {})
        xodim_id = xodim_id_map.get(display_num, int(display_num))  # Fallback to direct parse if no mapping
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
    sana_matn = update.message.text.strip()

    # Handle date-based view
    if context.user_data.get('dav_amal') == 'sana_boyicha':
        komp_id = context.user_data.get('komp_id')
        komp = kompaniya_olish(komp_id)
        komp_nomi = komp[1] if komp else "Noma'lum"

        # Validate date format
        if len(sana_matn) != 10 or sana_matn[4] != '-' or sana_matn[7] != '-':
            await update.message.reply_text(
                f"❌ Noto'g'ri format!\n\n"
                f"Iltimos format shunga mos kelsin: YYYY-MM-DD\n"
                f"Misol: 2026-05-24",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_DAV_SANA

        try:
            davomatlar = kompaniya_davomati(komp_id, sana_matn)

            if not davomatlar:
                await update.message.reply_text(
                    f"❌ {sana_matn} sanada davomat yo'q!",
                    reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
                return ADM_DAV_SANA

            xabar = f"📅 *{sana_matn}:*\n\n"
            xabar += f"👥 Jami: {len(davomatlar)} ta xodim\n\n"

            for d in davomatlar:
                ism, sana, keldi, ketdi, ish_soat, kechikish, holat = d[0], d[1], d[2], d[3], d[4], d[5], d[6]
                xabar += f"👤 *{ism}*: {keldi or '—'} → {ketdi or '—'}"
                if kechikish and kechikish > 0:
                    xabar += f" ⚠️{kechikish_format(kechikish)}"
                xabar += "\n"

            await update.message.reply_text(xabar, parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_DAV_SANA
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_DAV_SANA

    # Handle manual entry - original behavior
    context.user_data['dav_sana'] = sana_matn
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
    matn = update.message.text.strip()
    komp_id = context.user_data.get('komp_id')

    if matn == "📥 Excel yuklab ol":
        await update.message.reply_text("⏳ Excel tayyorlanmoqda...")
        try:
            fayl = kompaniya_hisobot(komp_id)
            if fayl:
                with open(fayl, 'rb') as f:
                    await update.message.reply_document(f, filename=fayl)
                os.remove(fayl)
            else:
                await update.message.reply_text("❌ Hisobot tayyorlashda xatolik!")
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}")
        await update.message.reply_text("Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU

    elif matn == "🔎 Kun bo'yicha":
        await update.message.reply_text(
            "📅 Qaysi kun uchun hisobot? (YYYY-MM-DD)\n\n"
            "Masalan: 2026-05-24",
            reply_markup=ReplyKeyboardRemove())
        return ADM_HISOBOT_KUN

    elif matn == "🔙 Orqaga":
        await update.message.reply_text("Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU

    # Handle date input for "Kun bo'yicha" option
    try:
        datetime.strptime(matn, "%Y-%m-%d")
        context.user_data['hisobot_sana'] = matn
        conn = connect(); cur = conn.cursor()
        cur.execute('''SELECT x.id,x.ism,x.lavozim,d.keldi,d.ketdi,d.ish_soat,d.kechikish,d.keldi_rasm,d.ketdi_rasm
                      FROM xodimlar x LEFT JOIN davomat d ON x.id=d.xodim_id AND d.sana=%s
                      WHERE x.kompaniya_id=%s ORDER BY x.ism''', (matn, komp_id))
        davomatlar = cur.fetchall(); cur.close(); conn.close()

        context.user_data['davomatlar'] = davomatlar
        context.user_data['dav_index'] = 0
        await adm_hisobot_kun_display(update, context)
        return ADM_HISOBOT_KUN
    except ValueError:
        await update.message.reply_text("❌ Format xato! (YYYY-MM-DD)\n\nMasalan: 2026-05-24")
        return ADM_HISOBOT_KUN

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
                  f"   ⏱ Ish: {s} soat {d} daqiqa | ⚠️ {kech}\n\n")

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

# ==================== NEW HISOBOT SYSTEM ====================

async def adm_hisobot_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin - Hisobot formati tanlash"""
    matn = update.message.text.strip()

    if matn == "🔙 Orqaga":
        await update.message.reply_text("Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU

    elif matn == "📅 Oylik":
        context.user_data['hisobot_format'] = 'oylik'
        await update.message.reply_text(
            "📅 Oy va yilni kiriting (MM-YYYY)\n\n"
            "Masalan: 05-2026",
            reply_markup=ReplyKeyboardRemove())
        return ADM_HISOBOT_YIL_OY

    elif matn == "📆 Yillik":
        context.user_data['hisobot_format'] = 'yillik'
        await update.message.reply_text(
            "📆 Yilni kiriting (YYYY)\n\n"
            "Masalan: 2026",
            reply_markup=ReplyKeyboardRemove())
        return ADM_HISOBOT_YIL_OY

    elif matn == "🔍 Custom sana":
        context.user_data['hisobot_format'] = 'custom'
        await update.message.reply_text(
            "📅 Boshlang'ich sanani kiriting (YYYY-MM-DD)\n\n"
            "Masalan: 2026-05-01",
            reply_markup=ReplyKeyboardRemove())
        return ADM_HISOBOT_SANA_1

    return ADM_HISOBOT_FORMAT

async def adm_hisobot_yil_oy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin - Oy/Yil kiritish"""
    matn = update.message.text.strip()
    komp_id = context.user_data.get('komp_id')
    format_type = context.user_data.get('hisobot_format')

    try:
        if format_type == 'oylik':
            parts = matn.split('-')
            if len(parts) != 2:
                await update.message.reply_text("❌ Format xato! MM-YYYY formatida kiriting")
                return ADM_HISOBOT_YIL_OY
            oy, yil = int(parts[0]), int(parts[1])
            if oy < 1 or oy > 12:
                await update.message.reply_text("❌ Oy 01-12 orasida bo'lishi kerak!")
                return ADM_HISOBOT_YIL_OY
            # Oyning boshlanishi va tugashi
            sana_from = f"{yil:04d}-{oy:02d}-01"
            # Keyingi oyning boshlanishi
            from datetime import date
            first_day = date(yil, oy, 1)
            next_month = first_day.replace(day=28) + timedelta(days=4)
            last_day = (next_month - timedelta(days=next_month.day)).strftime('%Y-%m-%d')
            sana_to = last_day

        elif format_type == 'yillik':
            yil = int(matn)
            sana_from = f"{yil:04d}-01-01"
            sana_to = f"{yil:04d}-12-31"

        context.user_data['sana_from'] = sana_from
        context.user_data['sana_to'] = sana_to

        # Excel yaratish
        await update.message.reply_text("⏳ Hisobot tayyorlanmoqda...")
        try:
            fayl = hisobot_row_format(komp_id=komp_id, sana_from=sana_from, sana_to=sana_to, super_admin=False)
            if fayl and os.path.exists(fayl):
                with open(fayl, 'rb') as f:
                    await update.message.reply_document(f, filename=fayl)
                os.remove(fayl)
                await update.message.reply_text(
                    f"✅ Hisobot yuklandi!\n\n"
                    f"Sana: {sana_from} dan {sana_to} gacha",
                    reply_markup=adm_menu_kb())
            else:
                await update.message.reply_text("❌ Hisobot tayyorlashda xatolik!", reply_markup=adm_menu_kb())
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}", reply_markup=adm_menu_kb())

        return ADM_MENU

    except ValueError:
        if format_type == 'oylik':
            await update.message.reply_text("❌ Format xato! MM-YYYY formatida kiriting")
            return ADM_HISOBOT_YIL_OY
        else:
            await update.message.reply_text("❌ Yil raqam bo'lishi kerak! (YYYY)")
            return ADM_HISOBOT_YIL_OY

async def adm_hisobot_sana_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin - Custom sana (boshlang'ich)"""
    matn = update.message.text.strip()
    komp_id = context.user_data.get('komp_id')

    try:
        datetime.strptime(matn, "%Y-%m-%d")
        context.user_data['sana_from'] = matn
        await update.message.reply_text(
            "📅 Tugash sanani kiriting (YYYY-MM-DD)\n\n"
            "Masalan: 2026-05-31",
            reply_markup=ReplyKeyboardRemove())
        return ADM_HISOBOT_SANA_2
    except ValueError:
        await update.message.reply_text("❌ Format xato! YYYY-MM-DD formatida kiriting")
        return ADM_HISOBOT_SANA_1

async def adm_hisobot_sana_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin - Custom sana (tugash)"""
    matn = update.message.text.strip()
    komp_id = context.user_data.get('komp_id')
    sana_from = context.user_data.get('sana_from')

    try:
        datetime.strptime(matn, "%Y-%m-%d")
        sana_to = matn

        # Excel yaratish
        await update.message.reply_text("⏳ Hisobot tayyorlanmoqda...")
        try:
            fayl = hisobot_row_format(komp_id=komp_id, sana_from=sana_from, sana_to=sana_to, super_admin=False)
            if fayl and os.path.exists(fayl):
                with open(fayl, 'rb') as f:
                    await update.message.reply_document(f, filename=fayl)
                os.remove(fayl)
                await update.message.reply_text(
                    f"✅ Hisobot yuklandi!\n\n"
                    f"Sana: {sana_from} dan {sana_to} gacha",
                    reply_markup=adm_menu_kb())
            else:
                await update.message.reply_text("❌ Hisobot tayyorlashda xatolik!", reply_markup=adm_menu_kb())
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}", reply_markup=adm_menu_kb())

        return ADM_MENU
    except ValueError:
        await update.message.reply_text("❌ Format xato! YYYY-MM-DD formatida kiriting")
        return ADM_HISOBOT_SANA_2

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
    xodim_id = context.user_data.get('xodim_id')
    komp = kompaniya_olish(komp_id)

    # Check company status
    if not komp or komp[4] != 'faol':
        await update.message.reply_text("⛔️ Kompaniyangiz faol emas!")
        return HR_MENU

    # HR user marking their own attendance
    if matn == "✅ Keldim":
        wifi_aktiv, wifi_ssid, wifi_mac = get_wifi(komp_id)

        if wifi_aktiv and wifi_mac:  # WiFi MAC aktiv
            await update.message.reply_text(
                f"📡 *WiFi TEKSHIRUVI*\n\n"
                f"Ish joyining WiFi MAC: *{wifi_mac}*\n\n"
                f"🔗 Tugmani bosing va MAC manzilini tasdiqlang",
                parse_mode='Markdown',
                reply_markup=xod_wifi_kb(komp_id, 'keldim', xodim_id))
            context.user_data['wifi_waiting'] = True
            return HR_MENU

        if komp[9] or komp[14]:  # GPS yoki Live GPS aktiv
            btn = [[KeyboardButton("📍 Joylashuvni yuboring", request_location=True)]]
            await update.message.reply_text(
                "📍 Joylashuvingizni yuboring:",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
            return XOD_KELDI_GPS
        else:
            natija = keldi_belgilash(xodim_id, komp_id)
            if natija == "already":
                await update.message.reply_text("⚠️ Bugun allaqachon belgilangan!", reply_markup=hr_menu_kb())
                return HR_MENU
            _, vaqt, kechikish = natija.split("|")
            msg = f"✅ Keldi vaqti: {vaqt}"
            if int(kechikish) > 0: msg += f"\n⚠️ Kechikish: {kechikish_format(int(kechikish))}"
            # FAQAT VIDEO BUTTON
            video_kb = ReplyKeyboardMarkup([
                ["📹 Video yubor"],
                ["❌ Bekor"]
            ], resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(f"{msg}\n\n📹 Video yuboring (dumaloq video yoki selfie):", reply_markup=video_kb)
            context.user_data['keldi_m'] = 0
            context.user_data['keldi_rasm_waiting'] = True
            return XOD_KELDI_RASM

    elif matn == "🚪 Ketdim":
        wifi_aktiv, wifi_ssid, wifi_mac = get_wifi(komp_id)

        if wifi_aktiv and wifi_mac:  # WiFi MAC aktiv
            await update.message.reply_text(
                f"📡 *WiFi TEKSHIRUVI*\n\n"
                f"Ish joyining WiFi MAC: *{wifi_mac}*\n\n"
                f"🔗 Tugmani bosing va MAC manzilini tasdiqlang",
                parse_mode='Markdown',
                reply_markup=xod_wifi_kb(komp_id, 'ketdi', xodim_id))
            context.user_data['wifi_waiting_ketdi'] = True
            return HR_MENU

        if komp[9] or komp[14]:
            btn = [[KeyboardButton("📍 Joylashuvni yuboring", request_location=True)]]
            await update.message.reply_text("📍 Joylashuvingizni yuboring:",
                reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True))
            return XOD_KETDI_GPS
        else:
            natija = ketdi_belgilash(xodim_id, komp_id)
            if natija == "nokeldi":
                await update.message.reply_text("❌ Avval keldi belgilanmagan!", reply_markup=hr_menu_kb())
                return HR_MENU
            _, vaqt, ish_soat, ish_tugash = natija.split("|")
            xodim = xodim_olish(xodim_id)
            s = int(float(ish_soat)); d = int((float(ish_soat) - s) * 60)
            msg = f"✅ Ketdi vaqti: {vaqt}\n⏱ Ish vaqti: {s} soat {d} daqiqa"
            # FAQAT VIDEO BUTTON
            video_kb = ReplyKeyboardMarkup([
                ["📹 Video yubor"],
                ["❌ Bekor"]
            ], resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(f"{msg}\n\n📹 Video yuboring (dumaloq video yoki selfie):", reply_markup=video_kb)
            context.user_data['ketdi_m'] = 0
            context.user_data['ketdi_rasm_waiting'] = True
            return XOD_KETDI_RASM

    if matn == "✍️ Manual davomat":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!"); return HR_MENU

        # Sequential numbering with ID mapping
        tugmalar = []
        xodim_id_map = {}
        for i, x in enumerate(xodimlar, 1):
            tugmalar.append([f"{i}. {x[1]}"])
            xodim_id_map[str(i)] = x[0]
        context.user_data['xodim_id_map'] = xodim_id_map

        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text("Xodim tanlang:", reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return HR_MAN_XODIM
    elif matn == "👁️ Davomatni ko'rish":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!"); return HR_MENU

        # Sequential numbering with ID mapping
        tugmalar = []
        xodim_id_map = {}
        for i, x in enumerate(xodimlar, 1):
            tugmalar.append([f"{i}. {x[1]}"])
            xodim_id_map[str(i)] = x[0]
        context.user_data['xodim_id_map'] = xodim_id_map

        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text("Xodim tanlang:", reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return HR_VIEW_XODIM
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
    elif matn == "💬 Xabar":
        return await hr_xabar_menu(update, context)
    elif matn == "☰ Menu" or matn == "🏠 Bosh menu":
        await update.message.reply_text("Boshidan boshlash uchun:", reply_markup=menu_restart_kb())
        return HR_MENU

    elif matn == "🔄 Restart / Boshla":
        return await start(update, context)

    return HR_MENU

async def hr_man_xodim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👔 HR menu:", reply_markup=hr_menu_kb())
        return HR_MENU
    try:
        # Get actual xodim_id from mapping (display number → actual ID)
        display_num = matn.split(".")[0].strip()
        xodim_id_map = context.user_data.get('xodim_id_map', {})
        xodim_id = xodim_id_map.get(display_num, int(display_num))  # Fallback to direct parse if no mapping
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

async def hr_view_xodim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👔 HR menu:", reply_markup=hr_menu_kb())
        return HR_MENU
    try:
        # Get actual xodim_id from mapping (display number → actual ID)
        display_num = matn.split(".")[0].strip()
        xodim_id_map = context.user_data.get('xodim_id_map', {})
        xodim_id = xodim_id_map.get(display_num, int(display_num))  # Fallback to direct parse if no mapping
        context.user_data['view_xodim_id'] = xodim_id
        xodim = xodim_olish(xodim_id)
        await update.message.reply_text(f"📅 Sana (YYYY-MM-DD) yoki oy (YYYY-MM):\n\nMisol: 2026-05-24 yoki 2026-05", reply_markup=ReplyKeyboardRemove())
        return HR_VIEW_SANA
    except: return HR_VIEW_XODIM

async def hr_view_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sana_matn = update.message.text.strip()
    xodim_id = context.user_data['view_xodim_id']
    xodim = xodim_olish(xodim_id)
    xodim_ism = xodim[1] if xodim else "Noma'lum"

    # Validate date format
    if not (len(sana_matn) == 7 or len(sana_matn) == 10):  # YYYY-MM or YYYY-MM-DD
        await update.message.reply_text(
            f"❌ Noto'g'ri format!\n\n"
            f"Iltimos, format shunga mos kelsin:\n"
            f"• Oy uchun: 2026-05\n"
            f"• Kun uchun: 2026-05-24",
            reply_markup=hr_menu_kb())
        return HR_MENU

    try:
        # SECURITY: Use text-only version to prevent any media/video IDs from being displayed
        davomatlar = xodim_davomati_text_only(xodim_id, sana_matn)

        if not davomatlar:
            await update.message.reply_text(f"❌ {xodim_ism} uchun bu davomatda ma'lumot topilmadi!", reply_markup=hr_menu_kb())
            return HR_MENU

        xabar = f"📋 *{xodim_ism} Davomati*\n\n"

        for dav in davomatlar:
            # SECURITY: Only extract text fields, SKIP izoh (index 7) and kiritdi (index 8)
            # to prevent any video_ids or media references from being displayed
            sana, keldi, ketdi, ish_soat, kechikish, holat = dav[1], dav[2], dav[3], dav[4], dav[5], dav[6]

            xabar += f"📅 *{sana}*\n"
            xabar += f"  ✅ Keldi: {keldi or '—'}\n"
            xabar += f"  🚪 Ketdi: {ketdi or '—'}\n"
            if ish_soat:
                soat = int(ish_soat)
                minut = int((ish_soat - soat) * 60)
                xabar += f"  ⏱️  Ish soati: {soat} soat {minut} daqiqa\n"
            if kechikish:
                xabar += f"  ⚠️  Kechikish: {kechikish} daqiqa\n"
            xabar += f"  📊 Holat: {holat}\n\n"

        # SECURITY: Use reply_text ONLY - never reply_photo or reply_video
        await update.message.reply_text(xabar, parse_mode='Markdown', reply_markup=hr_menu_kb())
        return HR_MENU
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}", reply_markup=hr_menu_kb())
        return HR_MENU

# ==================== XODIM PANEL ====================

async def xod_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')
    logger.info(f"XOD_MENU: matn='{matn}' xodim_id={xodim_id} komp_id={komp_id}")
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

        # SODDA: Darhol mark va malumot so'ra
        natija = keldi_belgilash(xodim_id, komp_id)
        if natija == "already":
            await update.message.reply_text("⚠️ Bugun allaqachon belgilangan!", reply_markup=xod_menu_kb())
            return XOD_MENU
        _, vaqt, kechikish = natija.split("|")
        msg = f"✅ Keldi vaqti: {vaqt}"
        if int(kechikish) > 0: msg += f"\n⚠️ Kechikish: {kechikish_format(int(kechikish))}"

        # Sodda tugmalar - xodim tanlaydi
        tugmalar = [
            ["📍 Lokatsiya", "📹 Video"],
            ["🎤 Audio", "📝 Matn"],
            ["🔙 Menyu"]
        ]
        context.user_data['keldi_data'] = {'xodim_id': xodim_id, 'komp_id': komp_id, 'vaqt': vaqt}
        await update.message.reply_text(f"{msg}\n\n📸 Qanday malumot?", reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return XOD_KELDI_ACTION

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

        # SODDA: Darhol mark va malumot so'ra
        natija = ketdi_belgilash(xodim_id, komp_id)
        if natija == "nokeldi":
            await update.message.reply_text("❌ Avval keldi belgilanmagan!", reply_markup=xod_menu_kb())
            return XOD_MENU
        _, vaqt, ish_soat, ish_tugash = natija.split("|")
        s = int(float(ish_soat)); d = int((float(ish_soat) - s) * 60)
        msg = f"✅ Ketdi vaqti: {vaqt}\n⏱ Ish vaqti: {s} soat {d} daqiqa"

        # Sodda tugmalar - xodim tanlaydi
        tugmalar = [
            ["📍 Lokatsiya", "📹 Video"],
            ["🎤 Audio", "📝 Matn"],
            ["🔙 Menyu"]
        ]
        context.user_data['ketdi_data'] = {'xodim_id': xodim_id, 'komp_id': komp_id, 'vaqt': vaqt, 'ish_soat': ish_soat}
        await update.message.reply_text(f"{msg}\n\n📸 Qanday malumot?", reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True))
        return XOD_KETDI_ACTION

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

    elif matn == "📝 Sababli so'rov":
        await update.message.reply_text("📅 Qaysi kun? (YYYY-MM-DD):", reply_markup=ReplyKeyboardRemove())
        return XOD_SABAB_SANA

    elif matn == "💬 Xabar":
        return await xod_xabar_menu(update, context)

    elif matn == "💰 Kirm Xisobim":
        return await xod_kirm_menu(update, context)

    elif matn == "💰 Chiqim Xisobim":
        return await xod_chiqim_menu(update, context)

    elif matn == "📄 Xisoobotlarim":
        return await xod_xisobotlarim(update, context)

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

    elif matn == "☰ Menu" or matn == "🏠 Bosh menu":
        await update.message.reply_text("👤 Xodim menu:", reply_markup=xod_menu_kb())
        return XOD_MENU

    elif matn == "🔄 Restart / Boshla":
        return await start(update, context)

    return XOD_MENU

async def xod_keldi_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button selection after Keldim"""
    matn = update.message.text
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')

    # Check if waiting for text (Matn)
    if context.user_data.get('keldi_matn_waiting'):
        if matn == "🔙 Menyu":
            context.user_data['keldi_matn_waiting'] = False
            await update.message.reply_text("👤 Xodim menu:", reply_markup=xod_menu_kb())
            return XOD_MENU
        # Save text and notify
        keldi_rasm_saqlash(xodim_id, matn)
        context.user_data['keldi_matn_waiting'] = False
        komp = kompaniya_olish(komp_id)
        await _admin_xabar(context, xodim_id, komp_id, komp, 'keldi', 0, matn, False)
        await update.message.reply_text(f"✅ Qabul qilindi!", reply_markup=xod_menu_kb())
        return XOD_MENU

    # Button selections
    if matn == "🔙 Menyu":
        await update.message.reply_text("👤 Xodim menu:", reply_markup=xod_menu_kb())
        return XOD_MENU
    elif matn == "📍 Lokatsiya":
        await update.message.reply_text("📍 Lokatsiyani yuboring! (Telegram'dagi 📎 dan tanla)", reply_markup=ReplyKeyboardMarkup([["🔙 Menyu"]], resize_keyboard=True))
        return XOD_KELDI_GPS
    elif matn == "📹 Video":
        context.user_data['keldi_rasm_waiting'] = True
        await update.message.reply_text("📹 Video yuboring!", reply_markup=ReplyKeyboardMarkup([["🔙 Menyu"]], resize_keyboard=True))
        return XOD_KELDI_RASM
    elif matn == "🎤 Audio":
        await update.message.reply_text("🎤 Audio yuboring!", reply_markup=ReplyKeyboardMarkup([["🔙 Menyu"]], resize_keyboard=True))
        return XOD_KELDI_AUDIO
    elif matn == "📝 Matn":
        context.user_data['keldi_matn_waiting'] = True
        await update.message.reply_text("📝 Matn yuboring:", reply_markup=ReplyKeyboardMarkup([["🔙 Menyu"]], resize_keyboard=True))
        return XOD_KELDI_ACTION
    else:
        await update.message.reply_text("📸 Qanday malumot?", reply_markup=ReplyKeyboardMarkup([["📍 Lokatsiya", "📹 Video"], ["🎤 Audio", "📝 Matn"], ["🔙 Menyu"]], resize_keyboard=True))
        return XOD_KELDI_ACTION

async def xod_ketdi_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button selection after Ketdim"""
    matn = update.message.text
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')

    # Check if waiting for text (Matn)
    if context.user_data.get('ketdi_matn_waiting'):
        if matn == "🔙 Menyu":
            context.user_data['ketdi_matn_waiting'] = False
            await update.message.reply_text("👤 Xodim menu:", reply_markup=xod_menu_kb())
            return XOD_MENU
        # Save text and notify
        keldi_rasm_saqlash(xodim_id, matn)
        context.user_data['ketdi_matn_waiting'] = False
        komp = kompaniya_olish(komp_id)
        await _admin_xabar(context, xodim_id, komp_id, komp, 'ketdi', 0, matn, False)
        await update.message.reply_text(f"✅ Qabul qilindi!", reply_markup=xod_menu_kb())
        return XOD_MENU

    # Button selections
    if matn == "🔙 Menyu":
        await update.message.reply_text("👤 Xodim menu:", reply_markup=xod_menu_kb())
        return XOD_MENU
    elif matn == "📍 Lokatsiya":
        await update.message.reply_text("📍 Lokatsiyani yuboring! (Telegram'dagi 📎 dan tanla)", reply_markup=ReplyKeyboardMarkup([["🔙 Menyu"]], resize_keyboard=True))
        return XOD_KETDI_GPS
    elif matn == "📹 Video":
        context.user_data['ketdi_rasm_waiting'] = True
        await update.message.reply_text("📹 Video yuboring!", reply_markup=ReplyKeyboardMarkup([["🔙 Menyu"]], resize_keyboard=True))
        return XOD_KETDI_RASM
    elif matn == "🎤 Audio":
        await update.message.reply_text("🎤 Audio yuboring!", reply_markup=ReplyKeyboardMarkup([["🔙 Menyu"]], resize_keyboard=True))
        return XOD_KETDI_AUDIO
    elif matn == "📝 Matn":
        context.user_data['ketdi_matn_waiting'] = True
        await update.message.reply_text("📝 Matn yuboring:", reply_markup=ReplyKeyboardMarkup([["🔙 Menyu"]], resize_keyboard=True))
        return XOD_KETDI_ACTION
    else:
        await update.message.reply_text("📸 Qanday malumot?", reply_markup=ReplyKeyboardMarkup([["📍 Lokatsiya", "📹 Video"], ["🎤 Audio", "📝 Matn"], ["🔙 Menyu"]], resize_keyboard=True))
        return XOD_KETDI_ACTION

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

    # Accept BOTH live location and regular location

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

    # Check if we're coming from the simplified "Keldim" flow (already marked)
    if context.user_data.get('keldi_data'):
        # Attendance already marked, just save location data
        xodim = xodim_olish(xodim_id)
        msg = f"✅ Lokatsiya qabul qilindi\n📏 {m}m"

        # Notify admin about location
        await _admin_xabar(context, xodim_id, komp_id, komp, 'keldi', 0, f"Lokatsiya: {m}m", False)

        # AUDIT LOG
        user_id = update.effective_user.id
        user_ism = update.effective_user.first_name or 'Xodim'
        audit_log_qoshish(komp_id, 'KELDI_GPS', f"Lokatsiya: {m}m", xodim_id, None, None, user_id, user_ism)

        await update.message.reply_text(msg, reply_markup=xod_menu_kb())
        return XOD_MENU

    # Old flow: attendance not yet marked
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
        reply_markup=restart_kb())
    return XOD_KELDI_RASM

async def xod_reject_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject audio/voice messages - only video/photo allowed"""
    await update.message.reply_text(
        "❌ Audio/ovoz qabul qilinmaydi!\n\n"
        "📸 Faqat: Selfie yoki dumaloq video yuboring",
        reply_markup=ReplyKeyboardRemove())
    # Return to the appropriate state based on which rasm we're waiting for
    if context.user_data.get('keldi_rasm_waiting'):
        return XOD_KELDI_RASM
    elif context.user_data.get('ketdi_rasm_waiting'):
        return XOD_KETDI_RASM
    else:
        return XOD_MENU

async def xod_keldi_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "☰ Menu" or matn == "🏠 Bosh menu" or matn == "🔙 Menyu":
        context.user_data['keldi_rasm_waiting'] = False
        return await start(update, context)

    # Cancel button
    if matn == "❌ Bekor":
        context.user_data['keldi_rasm_waiting'] = False
        await update.message.reply_text("❌ Bekor qilindi", reply_markup=xod_menu_kb())
        return XOD_MENU

    if not update.message.photo and not update.message.video_note:
        # For simplified flow, show our custom buttons instead of restart_kb()
        if context.user_data.get('keldi_data'):
            await update.message.reply_text("❌ Faqat video yuboring!", reply_markup=ReplyKeyboardMarkup([
                ["📹 Rasm/Video"],
                ["🔙 Menyu"]
            ], resize_keyboard=True, one_time_keyboard=True))
        else:
            await update.message.reply_text("❌ Faqat video yuboring!", reply_markup=ReplyKeyboardMarkup([
                ["📹 Video yubor"],
                ["❌ Bekor"]
            ], resize_keyboard=True, one_time_keyboard=True))
        return XOD_KELDI_RASM
    xodim_id = context.user_data['xodim_id']
    komp_id = context.user_data['komp_id']
    is_photo = bool(update.message.photo)  # FIX: to'g'ri tekshiruv
    rasm_id = update.message.photo[-1].file_id if is_photo else update.message.video_note.file_id
    keldi_rasm_saqlash(xodim_id, rasm_id)
    komp = kompaniya_olish(komp_id)
    m = context.user_data.get('keldi_m', 0)
    context.user_data['keldi_rasm_waiting'] = False

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

    # Check if we're coming from the simplified "Ketdim" flow (already marked)
    if context.user_data.get('ketdi_data'):
        # Attendance already marked, just save location data
        msg = f"✅ Lokatsiya qabul qilindi\n📏 {m}m"

        # Notify admin about location
        await _admin_xabar(context, xodim_id, komp_id, komp, 'ketdi', 0, f"Lokatsiya: {m}m", False)

        # AUDIT LOG
        user_id = update.effective_user.id
        user_ism = update.effective_user.first_name or 'Xodim'
        audit_log_qoshish(komp_id, 'KETDI_GPS', f"Lokatsiya: {m}m", xodim_id, None, None, user_id, user_ism)

        await update.message.reply_text(msg, reply_markup=xod_menu_kb())
        return XOD_MENU

    # Old flow: attendance not yet marked
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
        reply_markup=restart_kb())
    return XOD_KETDI_RASM

async def xod_ketdi_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "☰ Menu" or matn == "🏠 Bosh menu" or matn == "🔙 Menyu":
        context.user_data['ketdi_rasm_waiting'] = False
        return await start(update, context)

    # Cancel button
    if matn == "❌ Bekor":
        context.user_data['ketdi_rasm_waiting'] = False
        await update.message.reply_text("❌ Bekor qilindi", reply_markup=xod_menu_kb())
        return XOD_MENU

    if not update.message.photo and not update.message.video_note:
        # For simplified flow, show our custom buttons instead of restart_kb()
        if context.user_data.get('ketdi_data'):
            await update.message.reply_text("❌ Faqat video yuboring!", reply_markup=ReplyKeyboardMarkup([
                ["📹 Rasm/Video"],
                ["🔙 Menyu"]
            ], resize_keyboard=True, one_time_keyboard=True))
        else:
            await update.message.reply_text("❌ Faqat video yuboring!", reply_markup=ReplyKeyboardMarkup([
                ["📹 Video yubor"],
                ["❌ Bekor"]
            ], resize_keyboard=True, one_time_keyboard=True))
        return XOD_KETDI_RASM
    xodim_id = context.user_data['xodim_id']
    komp_id = context.user_data['komp_id']
    is_photo = bool(update.message.photo)  # FIX: to'g'ri tekshiruv
    rasm_id = update.message.photo[-1].file_id if is_photo else update.message.video_note.file_id
    ketdi_rasm_saqlash(xodim_id, rasm_id)
    komp = kompaniya_olish(komp_id)
    m = context.user_data.get('ketdi_m', 0)
    context.user_data['ketdi_rasm_waiting'] = False

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
    tafsilot = f"Ketdi: {ketdi_vaqt} | Ish vaqti: {s} soat {d} daqiqa | Masofa: {m}m"
    audit_log_qoshish(komp_id, 'KETDI', tafsilot, xodim_id, rasm_id if is_photo else None,
                     rasm_id if not is_photo else None, user_id, user_ism)

    await _admin_xabar(context, xodim_id, komp_id, komp, 'ketdi', m, rasm_id, is_photo)
    await update.message.reply_text(f"✅ Chiqish belgilandi!\n\n{motivatsiya}",
                                     parse_mode='Markdown', reply_markup=xod_menu_kb())
    return XOD_MENU

# ==================== XABAR (MESSAGING) HANDLERS ====================

async def sa_xabar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin messaging menu"""
    matn = update.message.text
    sa_id = update.effective_user.id
    komp_id = context.user_data.get('komp_id')

    if matn == "💬 Xabar" or matn == "🔙 Orqaga":
        await update.message.reply_text(
            "💬 *Xabar yuborish:*\n\n"
            "Nimalarga xabar yuborasiz?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["📤 Xabar yuborish", "📥 Kirgan xabarlar"],
                ["📊 Xabar tarixhi", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return SA_XABAR_MENU

    elif matn == "📤 Xabar yuborish":
        # Get all organizations for Super Admin
        kompaniyalar = barcha_kompaniyalar()
        if not kompaniyalar:
            await update.message.reply_text("❌ Tashkilot yo'q!", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return SA_XABAR_MENU

        context.user_data['xabar_recipients'] = []
        context.user_data['xabar_org_list'] = kompaniyalar
        buttons = [[f"🏢 {komp[1]} (ID: {komp[0]})"] for komp in kompaniyalar[:20]]
        buttons.append(["🔙 Orqaga"])
        await update.message.reply_text(
            "🏢 Tashkilot tanlang:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        context.user_data['selecting_org'] = True
        return SA_XABAR_TASHKILOT

    elif matn == "📥 Kirgan xabarlar":
        inbox = xabar_inbox_olish(sa_id, 0)  # org_id=0 for Super Admin system messages
        if not inbox:
            await update.message.reply_text(
                "📥 Kirgan xabarlar yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return SA_XABAR_MENU

        xabar = "📥 *Kirgan xabarlar:*\n\n"
        for idx, (q_id, x_id, from_user, from_role, subject, body, created, holat) in enumerate(inbox[:10], 1):
            status = "✅" if holat == "o'qildi" else "🆕"
            xabar += f"{status} {idx}. {subject}\n"
            xabar += f"   👤 {from_user} ({from_role})\n"
            xabar += f"   ⏰ {created}\n\n"

        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return SA_XABAR_MENU

    elif matn == "📊 Xabar tarixhi":
        history = xabar_history_olish(0)  # org_id=0 for Super Admin
        if not history:
            await update.message.reply_text(
                "📊 Xabar tarixhi yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return SA_XABAR_MENU

        xabar = "📊 *Xabar tarixhi (Oxirgi 20):*\n\n"
        for idx, (x_id, from_user, from_role, subject, body, created) in enumerate(history[:20], 1):
            xabar += f"{idx}. {subject}\n"
            xabar += f"   👤 {from_user} ({from_role})\n"
            xabar += f"   ⏰ {created}\n\n"

        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return SA_XABAR_MENU

    elif matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Super Admin menu:", reply_markup=sa_menu_kb())
        return SA_MENU

    return SA_XABAR_MENU

async def adm_xabar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin messaging menu"""
    matn = update.message.text
    admin_id = update.effective_user.id
    komp_id = context.user_data.get('komp_id')

    if matn == "💬 Xabar" or matn == "🔙 Orqaga":
        await update.message.reply_text(
            "💬 *Xabar yuborish:*\n\n"
            "Nimalarga xabar yuborasiz?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["📤 Hammaga", "📤 Bolim tanlash"],
                ["📤 Biror kishiga", "📥 Kirgan xabarlar"],
                ["📊 Tarixhi", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return ADM_XABAR_MENU

    elif matn == "📤 Hammaga":
        # Send to ALL employees
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_XABAR_MENU

        # Store all recipients
        context.user_data['xabar_recipients'] = [(x[0], x[1], x[7], komp_id) for x in xodimlar]
        context.user_data['xabar_send_all'] = True

        await update.message.reply_text(
            f"📤 *Hammaga xabar yuborish*\n\n"
            f"Jami xodim: {len(xodimlar)} ta\n\n"
            f"Mavzu kiriting:",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove())
        return ADM_XABAR_SUBJECT

    elif matn == "📤 Bolim tanlash":
        # Get unique departments
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_XABAR_MENU

        # Get unique departments (lavozim)
        departments = {}
        for xod in xodimlar:
            dept = xod[2]  # lavozim
            if dept not in departments:
                departments[dept] = []
            departments[dept].append(xod)

        buttons = []
        for dept in departments.keys():
            count = len(departments[dept])
            buttons.append([f"💼 {dept} ({count})"])
        buttons.append(["🔙 Orqaga"])

        context.user_data['xabar_departments'] = departments
        await update.message.reply_text(
            "💼 Bolim tanlang:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return ADM_XABAR_MENU

    elif matn.startswith("💼 ") and "(" in matn:
        # Department selected
        dept_name = matn.split(" (")[0].replace("💼 ", "")
        departments = context.user_data.get('xabar_departments', {})

        if dept_name not in departments:
            await update.message.reply_text("❌ Bolim topilmadi!", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_XABAR_MENU

        xodimlar = departments[dept_name]
        context.user_data['xabar_recipients'] = [(x[0], x[1], x[7], komp_id) for x in xodimlar]
        context.user_data['xabar_send_all'] = False

        await update.message.reply_text(
            f"💼 *{dept_name} bolimiga xabar*\n\n"
            f"Jami: {len(xodimlar)} ta xodim\n\n"
            f"Mavzu kiriting:",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove())
        return ADM_XABAR_SUBJECT

    elif matn == "📤 Biror kishiga":
        # Get all employees in this organization
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_XABAR_MENU

        context.user_data['xabar_recipients'] = []
        buttons = []
        for xod in xodimlar[:30]:
            buttons.append([f"👤 {xod[1]} (ID: {xod[0]})"])
        buttons.append(["🔙 Orqaga"])

        await update.message.reply_text(
            "👤 Qabul qiluvchi tanlang:\n\n(Bitta yoki ko'p tanlashingiz mumkin)",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        context.user_data['xabar_xodim_list'] = xodimlar
        context.user_data['selecting_recipient'] = True
        return ADM_XABAR_RECIPIENT

    elif matn == "📥 Kirgan xabarlar":
        inbox = xabar_inbox_olish(admin_id, komp_id)
        if not inbox:
            await update.message.reply_text(
                "📥 Kirgan xabarlar yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_XABAR_MENU

        xabar = "📥 *Kirgan xabarlar:*\n\n"
        for idx, (q_id, x_id, from_user, from_role, subject, body, created, holat) in enumerate(inbox[:10], 1):
            status = "✅" if holat == "o'qildi" else "🆕"
            xabar += f"{status} {idx}. {subject}\n"
            xabar += f"   👤 {from_user} ({from_role})\n"
            xabar += f"   ⏰ {created}\n\n"

        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return ADM_XABAR_MENU

    elif matn == "📊 Xabar tarixhi":
        history = xabar_history_olish(komp_id)
        if not history:
            await update.message.reply_text(
                "📊 Xabar tarixhi yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return ADM_XABAR_MENU

        xabar = "📊 *Xabar tarixhi (Oxirgi 20):*\n\n"
        for idx, (x_id, from_user, from_role, subject, body, created) in enumerate(history[:20], 1):
            xabar += f"{idx}. {subject}\n"
            xabar += f"   👤 {from_user} ({from_role})\n"
            xabar += f"   ⏰ {created}\n\n"

        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return ADM_XABAR_MENU

    elif matn == "🔙 Orqaga":
        await update.message.reply_text("📋 Admin menu:", reply_markup=adm_menu_kb())
        return ADM_MENU

    return ADM_XABAR_MENU

async def hr_xabar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """HR messaging menu"""
    matn = update.message.text
    hr_id = update.effective_user.id
    komp_id = context.user_data.get('komp_id')

    if matn == "💬 Xabar" or matn == "🔙 Orqaga":
        await update.message.reply_text(
            "💬 *Xabar yuborish:*\n\n"
            "Nimalarga xabar yuborasiz?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["📤 Hammaga", "📤 Bolim tanlash"],
                ["📤 Biror kishiga", "📥 Kirgan xabarlar"],
                ["📊 Tarixhi", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return HR_XABAR_MENU

    elif matn == "📤 Hammaga":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return HR_XABAR_MENU

        context.user_data['xabar_recipients'] = [(x[0], x[1], x[7], komp_id) for x in xodimlar]
        context.user_data['xabar_send_all'] = True

        await update.message.reply_text(
            f"📤 *Hammaga xabar yuborish*\n\n"
            f"Jami xodim: {len(xodimlar)} ta\n\n"
            f"Mavzu kiriting:",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove())
        return HR_XABAR_SUBJECT

    elif matn == "📤 Bolim tanlash":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return HR_XABAR_MENU

        departments = {}
        for xod in xodimlar:
            dept = xod[2]
            if dept not in departments:
                departments[dept] = []
            departments[dept].append(xod)

        buttons = []
        for dept in departments.keys():
            count = len(departments[dept])
            buttons.append([f"💼 {dept} ({count})"])
        buttons.append(["🔙 Orqaga"])

        context.user_data['xabar_departments'] = departments
        await update.message.reply_text(
            "💼 Bolim tanlang:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return HR_XABAR_MENU

    elif matn.startswith("💼 ") and "(" in matn:
        dept_name = matn.split(" (")[0].replace("💼 ", "")
        departments = context.user_data.get('xabar_departments', {})

        if dept_name not in departments:
            await update.message.reply_text("❌ Bolim topilmadi!", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return HR_XABAR_MENU

        xodimlar = departments[dept_name]
        context.user_data['xabar_recipients'] = [(x[0], x[1], x[7], komp_id) for x in xodimlar]
        context.user_data['xabar_send_all'] = False

        await update.message.reply_text(
            f"💼 *{dept_name} bolimiga xabar*\n\n"
            f"Jami: {len(xodimlar)} ta xodim\n\n"
            f"Mavzu kiriting:",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove())
        return HR_XABAR_SUBJECT

    elif matn == "📤 Biror kishiga":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return HR_XABAR_MENU

        context.user_data['xabar_recipients'] = []
        buttons = []
        for xod in xodimlar[:30]:
            buttons.append([f"👤 {xod[1]} (ID: {xod[0]})"])
        buttons.append(["🔙 Orqaga"])

        await update.message.reply_text(
            "👤 Qabul qiluvchi tanlang:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        context.user_data['xabar_xodim_list'] = xodimlar
        context.user_data['selecting_recipient'] = True
        return HR_XABAR_RECIPIENT

    elif matn == "📥 Kirgan xabarlar":
        inbox = xabar_inbox_olish(hr_id, komp_id)
        if not inbox:
            await update.message.reply_text(
                "📥 Kirgan xabarlar yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return HR_XABAR_MENU

        xabar = "📥 *Kirgan xabarlar:*\n\n"
        for idx, (q_id, x_id, from_user, from_role, subject, body, created, holat) in enumerate(inbox[:10], 1):
            status = "✅" if holat == "o'qildi" else "🆕"
            xabar += f"{status} {idx}. {subject}\n"
            xabar += f"   👤 {from_user} ({from_role})\n"
            xabar += f"   ⏰ {created}\n\n"

        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return HR_XABAR_MENU

    elif matn == "📊 Xabar tarixhi":
        history = xabar_history_olish(komp_id)
        if not history:
            await update.message.reply_text(
                "📊 Xabar tarixhi yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return HR_XABAR_MENU

        xabar = "📊 *Xabar tarixhi (Oxirgi 20):*\n\n"
        for idx, (x_id, from_user, from_role, subject, body, created) in enumerate(history[:20], 1):
            xabar += f"{idx}. {subject}\n"
            xabar += f"   👤 {from_user} ({from_role})\n"
            xabar += f"   ⏰ {created}\n\n"

        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return HR_XABAR_MENU

    elif matn == "🔙 Orqaga":
        await update.message.reply_text("📋 HR menu:", reply_markup=hr_menu_kb())
        return HR_MENU

    return HR_XABAR_MENU

async def xod_xabar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Employee messaging menu"""
    matn = update.message.text
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')

    if matn == "💬 Xabar" or matn == "🔙 Orqaga":
        await update.message.reply_text(
            "💬 *Xabar yuborish:*\n\n"
            "Nimalarga xabar yuborasiz?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["📤 Xabar yuborish", "📥 Kirgan xabarlar"],
                ["📊 Xabar tarixhi", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return XOD_XABAR_MENU

    elif matn == "📤 Xabar yuborish":
        # Employees can send to Admin and HR only
        komp = kompaniya_olish(komp_id)
        hr_list = hr_idlari(komp_id)

        recipients = []
        buttons = []

        # Add Admin
        if komp and komp[3]:  # admin_id
            recipients.append((komp[3], komp[1], 'Admin', komp_id))
            buttons.append([f"👤 Admin ({komp[1]})"])

        # Add HR members
        xodimlar = kompaniya_xodimlari(komp_id)
        for xod in xodimlar:
            if xod[7] == 'hr':  # rol
                recipients.append((xod[0], xod[1], 'HR', komp_id))
                buttons.append([f"👤 {xod[1]} (HR)"])

        buttons.append(["🔙 Orqaga"])

        if not recipients:
            await update.message.reply_text("❌ Qabul qiluvchi yo'q!", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return XOD_XABAR_MENU

        context.user_data['xabar_recipients'] = recipients
        await update.message.reply_text(
            "👤 Qabul qiluvchi tanlang:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        context.user_data['selecting_recipient'] = True
        return XOD_XABAR_RECIPIENT

    elif matn == "📥 Kirgan xabarlar":
        inbox = xabar_inbox_olish(xodim_id, komp_id)
        if not inbox:
            await update.message.reply_text(
                "📥 Kirgan xabarlar yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return XOD_XABAR_MENU

        xabar = "📥 *Kirgan xabarlar:*\n\n"
        for idx, (q_id, x_id, from_user, from_role, subject, body, created, holat) in enumerate(inbox[:10], 1):
            status = "✅" if holat == "o'qildi" else "🆕"
            xabar += f"{status} {idx}. {subject}\n"
            xabar += f"   👤 {from_user} ({from_role})\n"
            xabar += f"   ⏰ {created}\n\n"

        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return XOD_XABAR_MENU

    elif matn == "📊 Xabar tarixhi":
        history = xabar_history_olish(komp_id)
        if not history:
            await update.message.reply_text(
                "📊 Xabar tarixhi yo'q!",
                reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
            return XOD_XABAR_MENU

        xabar = "📊 *Xabar tarixhi (Oxirgi 20):*\n\n"
        for idx, (x_id, from_user, from_role, subject, body, created) in enumerate(history[:20], 1):
            xabar += f"{idx}. {subject}\n"
            xabar += f"   👤 {from_user} ({from_role})\n"
            xabar += f"   ⏰ {created}\n\n"

        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return XOD_XABAR_MENU

    elif matn == "🔙 Orqaga":
        await update.message.reply_text("👤 Xodim menu:", reply_markup=xod_menu_kb())
        return XOD_MENU

    return XOD_XABAR_MENU

# ==================== XABAR RECIPIENT HANDLERS ====================

async def sa_xabar_tashkilot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin organization selection for messaging"""
    matn = update.message.text
    if "🏢" not in matn:
        await update.message.reply_text("❌ Tashkilot tanlang!")
        return SA_XABAR_TASHKILOT

    komp_id = int(matn.split("ID: ")[1].rstrip(")"))
    context.user_data['xabar_komp_id'] = komp_id

    # Now get recipients (can be anyone in the org)
    xodimlar = kompaniya_xodimlari(komp_id)
    buttons = []
    for xod in xodimlar[:50]:
        buttons.append([f"👤 {xod[1]} ({xod[7]}) - ID:{xod[0]}"])
    buttons.append(["🔙 Orqaga"])

    await update.message.reply_text("👤 Qabul qiluvchi(lar)ni tanlang:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    context.user_data['xabar_recipients_list'] = [(x[0], x[1], x[7], komp_id) for x in xodimlar]
    return SA_XABAR_RECIPIENT

async def sa_xabar_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin recipient selection"""
    matn = update.message.text
    if matn == "🔙 Orqaga":
        return await sa_xabar_menu(update, context)

    if "👤" not in matn:
        await update.message.reply_text("❌ Qabul qiluvchi tanlang!")
        return SA_XABAR_RECIPIENT

    xodim_id = int(matn.split("ID:")[1].rstrip(")"))
    recipients_list = context.user_data.get('xabar_recipients_list', [])
    recipient = next((r for r in recipients_list if r[0] == xodim_id), None)

    if not recipient:
        await update.message.reply_text("❌ Qabul qiluvchi topilmadi!")
        return SA_XABAR_RECIPIENT

    context.user_data['xabar_to_id'] = xodim_id
    context.user_data['xabar_to_name'] = recipient[1]
    context.user_data['xabar_to_role'] = recipient[2]

    await update.message.reply_text("📌 Xabar mavzusini kiriting:", reply_markup=ReplyKeyboardRemove())
    return SA_XABAR_SUBJECT

async def sa_xabar_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin message subject"""
    subject = update.message.text.strip()
    if not subject or len(subject) > 100:
        await update.message.reply_text("❌ Mavzu 1-100 belgidan iborat bo'lsin!")
        return SA_XABAR_SUBJECT

    context.user_data['xabar_subject'] = subject
    await update.message.reply_text("📝 Xabar matnini kiriting:", reply_markup=ReplyKeyboardRemove())
    return SA_XABAR_MATN

async def sa_xabar_matn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin send message"""
    xabar_text = update.message.text.strip()
    if not xabar_text:
        await update.message.reply_text("❌ Xabar matni bo'sh bo'lmasin!")
        return SA_XABAR_MATN

    try:
        sa_id = update.effective_user.id
        komp_id = context.user_data.get('xabar_komp_id', 0)
        to_id = context.user_data.get('xabar_to_id')
        to_name = context.user_data.get('xabar_to_name')
        to_role = context.user_data.get('xabar_to_role')
        subject = context.user_data.get('xabar_subject')

        sa_info = super_admin_olish(sa_id)
        sa_name = sa_info[2] if sa_info else "Super Admin"

        xabar_yuborish(
            sa_id, sa_name, 'super_admin', 0,
            [(to_id, to_name, to_role, komp_id)],
            subject, xabar_text, komp_id
        )

        await update.message.reply_text(
            f"✅ Xabar yuborildi!\n\n"
            f"📌 {subject}\n"
            f"👤 {to_name} ({to_role})",
            reply_markup=sa_menu_kb())

        # Clear context
        for key in ['xabar_komp_id', 'xabar_to_id', 'xabar_to_name', 'xabar_to_role', 'xabar_subject', 'xabar_recipients_list']:
            context.user_data.pop(key, None)

        return SA_MENU
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {str(e)}", reply_markup=sa_menu_kb())
        return SA_MENU

# ADM handlers
async def adm_xabar_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin recipient selection"""
    matn = update.message.text
    if matn == "🔙 Orqaga":
        return await adm_xabar_menu(update, context)

    if "👤" not in matn:
        await update.message.reply_text("❌ Qabul qiluvchi tanlang!")
        return ADM_XABAR_RECIPIENT

    xodim_id = int(matn.split("ID:")[1].rstrip(")"))
    context.user_data['xabar_to_id'] = xodim_id
    context.user_data['xabar_to_name'] = matn.split(" (")[0].replace("👤 ", "")
    context.user_data['xabar_to_role'] = 'xodim'

    await update.message.reply_text("📌 Xabar mavzusini kiriting:", reply_markup=ReplyKeyboardRemove())
    return ADM_XABAR_SUBJECT

async def adm_xabar_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin message subject"""
    subject = update.message.text.strip()
    if not subject or len(subject) > 100:
        await update.message.reply_text("❌ Mavzu 1-100 belgidan iborat bo'lsin!")
        return ADM_XABAR_SUBJECT

    context.user_data['xabar_subject'] = subject
    await update.message.reply_text("📝 Xabar matnini kiriting:", reply_markup=ReplyKeyboardRemove())
    return ADM_XABAR_MATN

async def adm_xabar_matn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin send message"""
    xabar_text = update.message.text.strip()
    if not xabar_text:
        await update.message.reply_text("❌ Xabar matni bo'sh bo'lmasin!")
        return ADM_XABAR_MATN

    try:
        admin_id = update.effective_user.id
        komp_id = context.user_data.get('komp_id')
        to_id = context.user_data.get('xabar_to_id')
        to_name = context.user_data.get('xabar_to_name')
        to_role = context.user_data.get('xabar_to_role')
        subject = context.user_data.get('xabar_subject')

        komp = kompaniya_olish(komp_id)
        admin_name = komp[1] + " (Admin)" if komp else "Admin"

        xabar_yuborish(
            admin_id, admin_name, 'admin', komp_id,
            [(to_id, to_name, to_role, komp_id)],
            subject, xabar_text, komp_id
        )

        await update.message.reply_text(
            f"✅ Xabar yuborildi!\n\n"
            f"📌 {subject}\n"
            f"👤 {to_name}",
            reply_markup=adm_menu_kb())

        for key in ['xabar_to_id', 'xabar_to_name', 'xabar_to_role', 'xabar_subject']:
            context.user_data.pop(key, None)

        return ADM_MENU
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {str(e)}", reply_markup=adm_menu_kb())
        return ADM_MENU

# HR handlers
async def hr_xabar_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """HR recipient selection"""
    matn = update.message.text
    if matn == "🔙 Orqaga":
        return await hr_xabar_menu(update, context)

    if "👤" not in matn:
        await update.message.reply_text("❌ Qabul qiluvchi tanlang!")
        return HR_XABAR_RECIPIENT

    xodim_id = int(matn.split("ID:")[1].rstrip(")"))
    context.user_data['xabar_to_id'] = xodim_id
    context.user_data['xabar_to_name'] = matn.split(" (")[0].replace("👤 ", "")
    context.user_data['xabar_to_role'] = 'xodim'

    await update.message.reply_text("📌 Xabar mavzusini kiriting:", reply_markup=ReplyKeyboardRemove())
    return HR_XABAR_SUBJECT

async def hr_xabar_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """HR message subject"""
    subject = update.message.text.strip()
    if not subject or len(subject) > 100:
        await update.message.reply_text("❌ Mavzu 1-100 belgidan iborat bo'lsin!")
        return HR_XABAR_SUBJECT

    context.user_data['xabar_subject'] = subject
    await update.message.reply_text("📝 Xabar matnini kiriting:", reply_markup=ReplyKeyboardRemove())
    return HR_XABAR_MATN

async def hr_xabar_matn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """HR send message"""
    xabar_text = update.message.text.strip()
    if not xabar_text:
        await update.message.reply_text("❌ Xabar matni bo'sh bo'lmasin!")
        return HR_XABAR_MATN

    try:
        hr_id = update.effective_user.id
        komp_id = context.user_data.get('komp_id')
        to_id = context.user_data.get('xabar_to_id')
        to_name = context.user_data.get('xabar_to_name')
        to_role = context.user_data.get('xabar_to_role')
        subject = context.user_data.get('xabar_subject')

        xodim = xodim_olish(hr_id)
        hr_name = xodim[1] if xodim else "HR"

        xabar_yuborish(
            hr_id, hr_name, 'hr', komp_id,
            [(to_id, to_name, to_role, komp_id)],
            subject, xabar_text, komp_id
        )

        await update.message.reply_text(
            f"✅ Xabar yuborildi!\n\n"
            f"📌 {subject}\n"
            f"👤 {to_name}",
            reply_markup=hr_menu_kb())

        for key in ['xabar_to_id', 'xabar_to_name', 'xabar_to_role', 'xabar_subject']:
            context.user_data.pop(key, None)

        return HR_MENU
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {str(e)}", reply_markup=hr_menu_kb())
        return HR_MENU

# XOD (Employee) handlers
async def xod_xabar_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Employee recipient selection"""
    matn = update.message.text
    if matn == "🔙 Orqaga":
        return await xod_xabar_menu(update, context)

    if "👤" not in matn:
        await update.message.reply_text("❌ Qabul qiluvchi tanlang!")
        return XOD_XABAR_RECIPIENT

    context.user_data['xabar_to_name'] = matn.split(" (")[0].replace("👤 ", "")
    context.user_data['xabar_to_role'] = 'Admin' if 'Admin' in matn else 'HR'

    # Get the recipient ID from the recipients list
    recipients = context.user_data.get('xabar_recipients', [])
    for r in recipients:
        if r[1] == context.user_data['xabar_to_name'] and r[2] == context.user_data['xabar_to_role']:
            context.user_data['xabar_to_id'] = r[0]
            break

    await update.message.reply_text("📌 Xabar mavzusini kiriting:", reply_markup=ReplyKeyboardRemove())
    return XOD_XABAR_SUBJECT

async def xod_xabar_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Employee message subject"""
    subject = update.message.text.strip()
    if not subject or len(subject) > 100:
        await update.message.reply_text("❌ Mavzu 1-100 belgidan iborat bo'lsin!")
        return XOD_XABAR_SUBJECT

    context.user_data['xabar_subject'] = subject
    await update.message.reply_text("📝 Xabar matnini kiriting:", reply_markup=ReplyKeyboardRemove())
    return XOD_XABAR_MATN

async def xod_xabar_matn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Employee send message"""
    xabar_text = update.message.text.strip()
    if not xabar_text:
        await update.message.reply_text("❌ Xabar matni bo'sh bo'lmasin!")
        return XOD_XABAR_MATN

    try:
        xodim_id = context.user_data.get('xodim_id')
        komp_id = context.user_data.get('komp_id')
        to_id = context.user_data.get('xabar_to_id')
        to_name = context.user_data.get('xabar_to_name')
        to_role = context.user_data.get('xabar_to_role')
        subject = context.user_data.get('xabar_subject')

        xodim = xodim_olish(xodim_id)
        xodim_name = xodim[1] if xodim else "Xodim"

        xabar_yuborish(
            xodim_id, xodim_name, 'xodim', komp_id,
            [(to_id, to_name, to_role, komp_id)],
            subject, xabar_text, komp_id
        )

        await update.message.reply_text(
            f"✅ Xabar yuborildi!\n\n"
            f"📌 {subject}\n"
            f"👤 {to_name} ({to_role})",
            reply_markup=xod_menu_kb())

        for key in ['xabar_to_id', 'xabar_to_name', 'xabar_to_role', 'xabar_subject', 'xabar_recipients']:
            context.user_data.pop(key, None)

        return XOD_MENU
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {str(e)}", reply_markup=xod_menu_kb())
        return XOD_MENU

# ==================== KIRM/CHIQIM (FINANCIAL) HANDLERS ====================

async def xod_kirm_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xodim income menu"""
    matn = update.message.text
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')

    if matn == "💰 Kirm Xisobim":
        # Show current balance and options
        jami_kirm = kirm_jami(xodim_id, komp_id)
        await update.message.reply_text(
            f"💰 *KIRM XISOBIM*\n\n"
            f"📊 Jami kirm: {jami_kirm:,.2f} so'm\n\n"
            f"Nimalarga kirm qo'shish kerak?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["💵 NAQT (Pul)", "💳 KARTA (O'tkazma)"],
                ["📦 TAVAR (Tovar)", "🎁 BONUS (Bonusiya)"],
                ["📋 Ko'rish", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return XOD_KIRM_MENU

    elif matn == "📋 Ko'rish":
        kirm_list = kirm_olish(xodim_id, komp_id)
        if not kirm_list:
            await update.message.reply_text(
                "📋 Kirm yozuvi yo'q!",
                reply_markup=ReplyKeyboardMarkup([
                    ["💵 NAQT (Pul)", "💳 KARTA (O'tkazma)"],
                    ["📦 TAVAR (Tovar)", "🎁 BONUS (Bonusiya)"],
                    ["🔙 Orqaga"]
                ], resize_keyboard=True))
            return XOD_KIRM_MENU

        xabar = "💰 *KIRM YOZUVLARI (Oxirgi 15):*\n\n"
        jami = 0
        for idx, (k_id, turi, summa, izoh, sana, vaqt, yaratilgan, by_name) in enumerate(kirm_list[:15], 1):
            jami += float(summa)
            turi_emoji = {"NAQT": "💵", "KARTA": "💳", "TAVAR": "📦", "BONUS": "🎁"}.get(turi, "📄")
            xabar += f"{idx}. {turi_emoji} {turi}\n"
            xabar += f"   💰 {summa:,.2f} so'm | {sana}\n"
            if izoh:
                xabar += f"   📝 {izoh}\n"
            xabar += "\n"

        xabar += f"\n📊 *Jami: {jami:,.2f} so'm*"
        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["💵 NAQT (Pul)", "💳 KARTA (O'tkazma)"],
                ["📦 TAVAR (Tovar)", "🎁 BONUS (Bonusiya)"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return XOD_KIRM_MENU

    elif matn == "🔙 Orqaga":
        await update.message.reply_text("👤 Xodim menu:", reply_markup=xod_menu_kb())
        return XOD_MENU

    elif matn in ["💵 NAQT (Pul)", "💳 KARTA (O'tkazma)", "📦 TAVAR (Tovar)", "🎁 BONUS (Bonusiya)"]:
        context.user_data['kirm_turi'] = matn.split(" ")[0]  # Get emoji
        await update.message.reply_text(
            "💰 Summa (so'm)ni kiriting:",
            reply_markup=ReplyKeyboardRemove())
        return XOD_KIRM_SUMMA

    return XOD_KIRM_MENU

async def xod_kirm_summa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Income amount input"""
    try:
        summa = float(update.message.text.replace(",", "").strip())
        if summa <= 0:
            await update.message.reply_text("❌ Summa musbat bo'lsin!")
            return XOD_KIRM_SUMMA
        context.user_data['kirm_summa'] = summa
        await update.message.reply_text(
            "📝 Izoh (ixtiyoriy, tyex - tasvir/tafsilot):",
            reply_markup=ReplyKeyboardRemove())
        return XOD_KIRM_IZOH
    except:
        await update.message.reply_text("❌ Raqam kiriting!")
        return XOD_KIRM_SUMMA

async def xod_kirm_izoh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Income note and save"""
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')
    xodim = xodim_olish(xodim_id)

    izoh = update.message.text.strip() if update.message.text else None
    turi = context.user_data.get('kirm_turi', '💵')
    summa = context.user_data.get('kirm_summa', 0)
    sana = hozir().strftime("%Y-%m-%d")
    vaqt = hozir().strftime("%H:%M")

    try:
        kirm_qoshish(
            xodim_id, komp_id, turi, summa, izoh,
            sana, vaqt, 'xodim', xodim[1] if xodim else 'Xodim'
        )

        jami_kirm = kirm_jami(xodim_id, komp_id)
        await update.message.reply_text(
            f"✅ Kirm saqlandi!\n\n"
            f"{turi} {summa:,.2f} so'm\n"
            f"📊 Jami kirm: {jami_kirm:,.2f} so'm",
            reply_markup=xod_menu_kb())

        for key in ['kirm_turi', 'kirm_summa']:
            context.user_data.pop(key, None)

        return XOD_MENU
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {str(e)}", reply_markup=xod_menu_kb())
        return XOD_MENU

async def xod_chiqim_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xodim expense menu"""
    matn = update.message.text
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')

    if matn == "💰 Chiqim Xisobim":
        # Show current expenses and options
        jami_chiqim = chiqim_jami(xodim_id, komp_id)
        await update.message.reply_text(
            f"💸 *CHIQIM XISOBIM*\n\n"
            f"📊 Jami chiqim: {jami_chiqim:,.2f} so'm\n\n"
            f"Nimalarga chiqim qo'shish kerak?",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["💵 NAQT (Pul)", "💳 KARTA (O'tkazma)"],
                ["📦 TAVAR (Tovar)", "⚠️ JARIMA (Штраф)"],
                ["📋 Ko'rish", "🔙 Orqaga"]
            ], resize_keyboard=True))
        return XOD_CHIQIM_MENU

    elif matn == "📋 Ko'rish":
        chiqim_list = chiqim_olish(xodim_id, komp_id)
        if not chiqim_list:
            await update.message.reply_text(
                "📋 Chiqim yozuvi yo'q!",
                reply_markup=ReplyKeyboardMarkup([
                    ["💵 NAQT (Pul)", "💳 KARTA (O'tkazma)"],
                    ["📦 TAVAR (Tovar)", "⚠️ JARIMA (Штраф)"],
                    ["🔙 Orqaga"]
                ], resize_keyboard=True))
            return XOD_CHIQIM_MENU

        xabar = "💸 *CHIQIM YOZUVLARI (Oxirgi 15):*\n\n"
        jami = 0
        for idx, (c_id, turi, summa, izoh, sana, vaqt, yaratilgan, by_name) in enumerate(chiqim_list[:15], 1):
            jami += float(summa)
            turi_emoji = {"NAQT": "💵", "KARTA": "💳", "TAVAR": "📦", "JARIMA": "⚠️"}.get(turi, "📄")
            xabar += f"{idx}. {turi_emoji} {turi}\n"
            xabar += f"   💸 -{summa:,.2f} so'm | {sana}\n"
            if izoh:
                xabar += f"   📝 {izoh}\n"
            xabar += "\n"

        xabar += f"\n📊 *Jami: -{jami:,.2f} so'm*"
        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["💵 NAQT (Pul)", "💳 KARTA (O'tkazma)"],
                ["📦 TAVAR (Tovar)", "⚠️ JARIMA (Штраф)"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True))
        return XOD_CHIQIM_MENU

    elif matn == "🔙 Orqaga":
        await update.message.reply_text("👤 Xodim menu:", reply_markup=xod_menu_kb())
        return XOD_MENU

    elif matn in ["💵 NAQT (Pul)", "💳 KARTA (O'tkazma)", "📦 TAVAR (Tovar)", "⚠️ JARIMA (Штраф)"]:
        context.user_data['chiqim_turi'] = matn.split(" ")[0]
        await update.message.reply_text(
            "💸 Summa (so'm)ni kiriting:",
            reply_markup=ReplyKeyboardRemove())
        return XOD_CHIQIM_SUMMA

    return XOD_CHIQIM_MENU

async def xod_chiqim_summa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Expense amount input"""
    try:
        summa = float(update.message.text.replace(",", "").strip())
        if summa <= 0:
            await update.message.reply_text("❌ Summa musbat bo'lsin!")
            return XOD_CHIQIM_SUMMA
        context.user_data['chiqim_summa'] = summa
        await update.message.reply_text(
            "📝 Izoh (ixtiyoriy):",
            reply_markup=ReplyKeyboardRemove())
        return XOD_CHIQIM_IZOH
    except:
        await update.message.reply_text("❌ Raqam kiriting!")
        return XOD_CHIQIM_SUMMA

async def xod_chiqim_izoh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Expense note and save"""
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')
    xodim = xodim_olish(xodim_id)

    izoh = update.message.text.strip() if update.message.text else None
    turi = context.user_data.get('chiqim_turi', '💵')
    summa = context.user_data.get('chiqim_summa', 0)
    sana = hozir().strftime("%Y-%m-%d")
    vaqt = hozir().strftime("%H:%M")

    try:
        chiqim_qoshish(
            xodim_id, komp_id, turi, summa, izoh,
            sana, vaqt, 'xodim', xodim[1] if xodim else 'Xodim'
        )

        jami_chiqim = chiqim_jami(xodim_id, komp_id)
        await update.message.reply_text(
            f"✅ Chiqim saqlandi!\n\n"
            f"{turi} {summa:,.2f} so'm\n"
            f"📊 Jami chiqim: {jami_chiqim:,.2f} so'm",
            reply_markup=xod_menu_kb())

        for key in ['chiqim_turi', 'chiqim_summa']:
            context.user_data.pop(key, None)

        return XOD_MENU
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {str(e)}", reply_markup=xod_menu_kb())
        return XOD_MENU

async def xod_xisobotlarim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xodim financial report"""
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')

    jami_kirm = kirm_jami(xodim_id, komp_id)
    jami_chiqim = chiqim_jami(xodim_id, komp_id)
    balans = jami_kirm - jami_chiqim

    xabar = f"📄 *MENING XISOOBOTIM*\n\n"
    xabar += f"💰 Jami kirm: +{jami_kirm:,.2f} so'm\n"
    xabar += f"💸 Jami chiqim: -{jami_chiqim:,.2f} so'm\n"
    xabar += f"━━━━━━━━━━━━━━━\n"
    xabar += f"💼 Balans: {balans:+,.2f} so'm"

    if balans > 0:
        xabar += " ✅"
    elif balans < 0:
        xabar += " ❌"

    await update.message.reply_text(
        xabar,
        parse_mode='Markdown',
        reply_markup=xod_menu_kb())

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

    # SECURITY: Build HR list to avoid sending media to HR
    hr_set = set(hr_list)

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

        # SECURITY: Send photos/videos ONLY to Admin and Super Admin, NOT to HR
        if rasm_id and aid not in hr_set:
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
                      f"⏱ {s} soat {d} daqiqa | ⚠️ {kech}\n")

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

# ==================== NEW SUPER ADMIN HISOBOT ====================

async def sa_hisobot_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin - Hisobot formati tanlash"""
    matn = update.message.text.strip()

    if matn == "🔙 Orqaga":
        await update.message.reply_text("Super Admin menu:", reply_markup=sa_menu_kb())
        return SA_MENU

    elif matn == "📅 Oylik":
        context.user_data['hisobot_format'] = 'oylik'
        await update.message.reply_text(
            "📅 Oy va yilni kiriting (MM-YYYY)\n\n"
            "Masalan: 05-2026",
            reply_markup=ReplyKeyboardRemove())
        return SA_HISOBOT_YIL_OY

    elif matn == "📆 Yillik":
        context.user_data['hisobot_format'] = 'yillik'
        await update.message.reply_text(
            "📆 Yilni kiriting (YYYY)\n\n"
            "Masalan: 2026",
            reply_markup=ReplyKeyboardRemove())
        return SA_HISOBOT_YIL_OY

    elif matn == "🔍 Custom sana":
        context.user_data['hisobot_format'] = 'custom'
        await update.message.reply_text(
            "📅 Boshlang'ich sanani kiriting (YYYY-MM-DD)\n\n"
            "Masalan: 2026-05-01",
            reply_markup=ReplyKeyboardRemove())
        return SA_HISOBOT_SANA_1

    return SA_HISOBOT_FORMAT

async def sa_hisobot_yil_oy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin - Oy/Yil kiritish"""
    matn = update.message.text.strip()
    format_type = context.user_data.get('hisobot_format')

    try:
        if format_type == 'oylik':
            parts = matn.split('-')
            if len(parts) != 2:
                await update.message.reply_text("❌ Format xato! MM-YYYY formatida kiriting")
                return SA_HISOBOT_YIL_OY
            oy, yil = int(parts[0]), int(parts[1])
            if oy < 1 or oy > 12:
                await update.message.reply_text("❌ Oy 01-12 orasida bo'lishi kerak!")
                return SA_HISOBOT_YIL_OY
            sana_from = f"{yil:04d}-{oy:02d}-01"
            from datetime import date
            first_day = date(yil, oy, 1)
            next_month = first_day.replace(day=28) + timedelta(days=4)
            last_day = (next_month - timedelta(days=next_month.day)).strftime('%Y-%m-%d')
            sana_to = last_day

        elif format_type == 'yillik':
            yil = int(matn)
            sana_from = f"{yil:04d}-01-01"
            sana_to = f"{yil:04d}-12-31"

        context.user_data['sana_from'] = sana_from
        context.user_data['sana_to'] = sana_to

        # Excel yaratish
        await update.message.reply_text("⏳ Hisobot tayyorlanmoqda...")
        try:
            fayl = hisobot_row_format(komp_id=None, sana_from=sana_from, sana_to=sana_to, super_admin=True)
            if fayl and os.path.exists(fayl):
                with open(fayl, 'rb') as f:
                    await update.message.reply_document(f, filename=fayl)
                os.remove(fayl)
                await update.message.reply_text(
                    f"✅ Hisobot yuklandi!\n\n"
                    f"Sana: {sana_from} dan {sana_to} gacha\n"
                    f"📊 BARCHA KOMPANIYALAR",
                    reply_markup=sa_menu_kb())
            else:
                await update.message.reply_text("❌ Hisobot tayyorlashda xatolik!", reply_markup=sa_menu_kb())
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}", reply_markup=sa_menu_kb())

        return SA_MENU

    except ValueError:
        if format_type == 'oylik':
            await update.message.reply_text("❌ Format xato! MM-YYYY formatida kiriting")
            return SA_HISOBOT_YIL_OY
        else:
            await update.message.reply_text("❌ Yil raqam bo'lishi kerak! (YYYY)")
            return SA_HISOBOT_YIL_OY

async def sa_hisobot_sana_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin - Custom sana (boshlang'ich)"""
    matn = update.message.text.strip()

    try:
        datetime.strptime(matn, "%Y-%m-%d")
        context.user_data['sana_from'] = matn
        await update.message.reply_text(
            "📅 Tugash sanani kiriting (YYYY-MM-DD)\n\n"
            "Masalan: 2026-05-31",
            reply_markup=ReplyKeyboardRemove())
        return SA_HISOBOT_SANA_2
    except ValueError:
        await update.message.reply_text("❌ Format xato! YYYY-MM-DD formatida kiriting")
        return SA_HISOBOT_SANA_1

async def sa_hisobot_sana_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super Admin - Custom sana (tugash)"""
    matn = update.message.text.strip()
    sana_from = context.user_data.get('sana_from')

    try:
        datetime.strptime(matn, "%Y-%m-%d")
        sana_to = matn

        # Excel yaratish
        await update.message.reply_text("⏳ Hisobot tayyorlanmoqda...")
        try:
            fayl = hisobot_row_format(komp_id=None, sana_from=sana_from, sana_to=sana_to, super_admin=True)
            if fayl and os.path.exists(fayl):
                with open(fayl, 'rb') as f:
                    await update.message.reply_document(f, filename=fayl)
                os.remove(fayl)
                await update.message.reply_text(
                    f"✅ Hisobot yuklandi!\n\n"
                    f"Sana: {sana_from} dan {sana_to} gacha\n"
                    f"📊 BARCHA KOMPANIYALAR",
                    reply_markup=sa_menu_kb())
            else:
                await update.message.reply_text("❌ Hisobot tayyorlashda xatolik!", reply_markup=sa_menu_kb())
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}", reply_markup=sa_menu_kb())

        return SA_MENU
    except ValueError:
        await update.message.reply_text("❌ Format xato! YYYY-MM-DD formatida kiriting")
        return SA_HISOBOT_SANA_2

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

@flask_app.route('/wifi-app')
def wifi_app():
    return render_template('wifi_app.html')

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

async def post_init(app: Application):
    """Setup bot commands"""
    try:
        commands = [
            BotCommand("start", "🏠 Boshlash / Start"),
        ]
        await app.bot.set_my_commands(commands)
        logger.info("Bot commands configured successfully")
    except Exception as e:
        logger.error(f"Error setting bot commands: {e}")

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")
    create_tables()
    print("Baza tayyor!")
    app = Application.builder().token(BOT_TOKEN).build()
    app.post_init = post_init

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
            SA_KOMP_DAV_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_dav_sana)],
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
            SA_KOMP_XODIM_VIEW_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_xodim_view_sana)],
            SA_KOMP_XODIM_STAT_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_xodim_stat_format)],
            SA_KOMP_XODIM_STAT_SANA_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_xodim_stat_sana_1)],
            SA_KOMP_XODIM_STAT_SANA_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_xodim_stat_sana_2)],
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
            ADM_KOMP_XODIM_VIEW_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_komp_xodim_view_sana)],
            ADM_KOMP_XODIM_STAT_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_komp_xodim_stat_format)],
            ADM_KOMP_XODIM_STAT_SANA_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_komp_xodim_stat_sana_1)],
            ADM_KOMP_XODIM_STAT_SANA_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_komp_xodim_stat_sana_2)],
            SA_XODIM_DELETE_KOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_xodim_delete_kod)],
            ADM_XODIM_DELETE_KOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_delete_kod)],
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
            HR_VIEW_XODIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_view_xodim)],
            HR_VIEW_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_view_sana)],
            XOD_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_menu_handler)],
            XOD_KELDI_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_keldi_action)],
            XOD_KELDI_GPS: [MessageHandler(filters.LOCATION, xod_keldi_gps)],
            XOD_KELDI_RASM: [MessageHandler(filters.PHOTO | filters.VIDEO_NOTE, xod_keldi_rasm)],
            XOD_KELDI_AUDIO: [MessageHandler(filters.VOICE | filters.AUDIO, xod_reject_audio)],
            XOD_KETDI_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_ketdi_action)],
            XOD_KETDI_GPS: [MessageHandler(filters.LOCATION, xod_ketdi_gps)],
            XOD_KETDI_RASM: [MessageHandler(filters.PHOTO | filters.VIDEO_NOTE, xod_ketdi_rasm)],
            XOD_KETDI_AUDIO: [MessageHandler(filters.VOICE | filters.AUDIO, xod_reject_audio)],
            XOD_SABAB_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_sabab_sana)],
            XOD_SABAB_MATN: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_sabab_matn)],
            # New hisobot states
            ADM_HISOBOT_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_hisobot_format)],
            ADM_HISOBOT_YIL_OY: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_hisobot_yil_oy)],
            ADM_HISOBOT_SANA_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_hisobot_sana_1)],
            ADM_HISOBOT_SANA_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_hisobot_sana_2)],
            SA_HISOBOT_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_hisobot_format)],
            SA_HISOBOT_YIL_OY: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_hisobot_yil_oy)],
            SA_HISOBOT_SANA_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_hisobot_sana_1)],
            SA_HISOBOT_SANA_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_hisobot_sana_2)],
            # Xabar states
            SA_XABAR_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_xabar_menu)],
            SA_XABAR_TASHKILOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_xabar_tashkilot)],
            SA_XABAR_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_xabar_recipient)],
            SA_XABAR_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_xabar_subject)],
            SA_XABAR_MATN: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_xabar_matn)],
            ADM_XABAR_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xabar_menu)],
            ADM_XABAR_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xabar_recipient)],
            ADM_XABAR_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xabar_subject)],
            ADM_XABAR_MATN: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xabar_matn)],
            HR_XABAR_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_xabar_menu)],
            HR_XABAR_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_xabar_recipient)],
            HR_XABAR_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_xabar_subject)],
            HR_XABAR_MATN: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_xabar_matn)],
            XOD_XABAR_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_xabar_menu)],
            XOD_XABAR_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_xabar_recipient)],
            XOD_XABAR_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_xabar_subject)],
            XOD_XABAR_MATN: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_xabar_matn)],
            # Kirm/Chiqim states
            XOD_KIRM_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_kirm_menu)],
            XOD_KIRM_SUMMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_kirm_summa)],
            XOD_KIRM_IZOH: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_kirm_izoh)],
            XOD_CHIQIM_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_chiqim_menu)],
            XOD_CHIQIM_SUMMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_chiqim_summa)],
            XOD_CHIQIM_IZOH: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_chiqim_izoh)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(sorov_callback, pattern=r'^sorov_'))
    app.add_handler(CallbackQueryHandler(wifi_callback, pattern=r'^wifi_'))
    app.add_handler(CallbackQueryHandler(gps_callback, pattern=r'^gps_'))
    # Live lokatsiya yangilanishi (edited_message) - live location updates
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

    # ==================== FLASK & POLLING ====================

    # Start Flask in a background thread
    port = os.environ.get("PORT", 8080)
    flask_thread = threading.Thread(
        target=lambda: flask_app.run(host='0.0.0.0', port=int(port), debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    print(f"Flask started on port {port}")

    print("Bot ishlamoqda...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
