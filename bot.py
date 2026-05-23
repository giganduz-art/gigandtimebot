import os
import math
import logging
from datetime import datetime
import pytz
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)
from database import (
    create_tables, hozir,
    super_admin_tekshir, super_admin_kod_tekshir, super_admin_telegram_saqlash,
    super_admin_id_tekshir, super_admin_kod_ozgartir,
    kompaniya_yaratish, barcha_kompaniyalar, kompaniya_olish,
    kompaniya_holat_ozgartir, kompaniya_funksiya_ozgartir, kompaniya_tahrirlash,
    admin_telefon_orqali_kompaniya, admin_id_saqlash, get_gps,
    xodim_qoshish, kompaniya_xodimlari, xodim_olish, xodim_tahrirlash,
    telegram_id_orqali_xodim, telefon_orqali_xodim, xodim_telegram_saqlash,
    hr_idlari, keldi_belgilash, keldi_rasm_saqlash, ketdi_belgilash,
    ketdi_rasm_saqlash, xodim_davomati, kompaniya_davomati, manual_davomat,
    sababli_sorov_saqlash, sababli_sorov_yangilash,
    super_admin_hisobot, kompaniya_hisobot
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
TASHKENT = pytz.timezone('Asia/Tashkent')

# ==================== STATES ====================
(
    # Kirish
    TELEFON, KOD,
    # Super Admin
    SA_MENU, SA_KOMP_MENU, SA_KOMP_NOMI, SA_KOMP_ADMIN_TEL,
    SA_KOMP_TANLASH, SA_KOMP_TAHRIR, SA_KOMP_TAHRIR_QIYMAT,
    SA_FUNKSIYA_TANLASH, SA_SOZ_MENU,
    # Admin
    ADM_MENU, ADM_XODIM_MENU, ADM_XODIM_ISM, ADM_XODIM_TEL,
    ADM_XODIM_LAVOZIM, ADM_XODIM_OYLIK, ADM_XODIM_ISH_BOSH,
    ADM_XODIM_ISH_TUG, ADM_XODIM_ROL, ADM_XODIM_TANLASH,
    ADM_XODIM_TAHRIR, ADM_XODIM_TAHRIR_QIYMAT,
    ADM_GPS_LAT, ADM_GPS_LON, ADM_GPS_RADIUS,
    # HR
    HR_MENU, HR_MANUAL_XODIM, HR_MANUAL_SANA, HR_MANUAL_KELDI,
    HR_MANUAL_KETDI, HR_MANUAL_HOLAT, HR_MANUAL_IZOH,
    # Xodim
    XOD_MENU, XOD_KELDI_GPS, XOD_KELDI_RASM,
    XOD_KETDI_GPS, XOD_KETDI_RASM,
    XOD_SABAB_SANA, XOD_SABAB_MATN,
) = range(40)

# ==================== YORDAMCHI ====================

def gps_tekshir(lat, lon, komp_lat, komp_lon, radius):
    R = 6371000
    lat1, lon1 = math.radians(lat), math.radians(lon)
    lat2, lon2 = math.radians(komp_lat), math.radians(komp_lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    masofa = R * 2 * math.asin(math.sqrt(a))
    return masofa <= radius, round(masofa)

def random_kod(uzunlik=6):
    import random, string
    return ''.join(random.choices(string.digits, k=uzunlik))

# ==================== /start ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.clear()

    # Super Admin tekshir
    if super_admin_id_tekshir(user_id):
        await update.message.reply_text(
            "👑 Super Admin paneliga xush kelibsiz!",
            reply_markup=super_admin_menu()
        )
        return SA_MENU

    # Xodim/Admin tekshir
    xodim = telegram_id_orqali_xodim(user_id)
    if xodim:
        xodim_id, ism, rol, komp_id = xodim
        context.user_data['xodim_id'] = xodim_id
        context.user_data['ism'] = ism
        context.user_data['rol'] = rol
        context.user_data['komp_id'] = komp_id

        if rol == 'admin':
            await update.message.reply_text(
                f"🏢 Admin paneliga xush kelibsiz, {ism}!",
                reply_markup=admin_menu()
            )
            return ADM_MENU
        elif rol == 'hr':
            await update.message.reply_text(
                f"👔 HR paneliga xush kelibsiz, {ism}!",
                reply_markup=hr_menu()
            )
            return HR_MENU
        else:
            await update.message.reply_text(
                f"👋 Xush kelibsiz, {ism}!",
                reply_markup=xodim_menu()
            )
            return XOD_MENU

    # Yangi foydalanuvchi
    btn = [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]]
    await update.message.reply_text(
        "👋 Xush kelibsiz!\n\nIltimos, telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True)
    )
    return TELEFON

async def telefon_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("❌ Iltimos, tugma orqali telefon yuboring!")
        return TELEFON

    telefon = contact.phone_number
    user_id = update.effective_user.id
    context.user_data['telefon'] = telefon

    # Super admin tekshir
    sa = super_admin_tekshir(telefon)
    if sa:
        await update.message.reply_text(
            "🔐 Super Admin kodni kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['tip'] = 'super_admin'
        return KOD

    # Admin tekshir
    komp = admin_telefon_orqali_kompaniya(telefon)
    if komp:
        komp_id, komp_nomi, holat = komp
        if holat != 'faol':
            await update.message.reply_text("❌ Kompaniya faol emas!")
            return ConversationHandler.END
        await update.message.reply_text(
            f"🏢 {komp_nomi} kompaniyasi admini sifatida kirdingiz.\n\n🔐 Kodni kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['tip'] = 'admin'
        context.user_data['komp_id'] = komp_id
        context.user_data['komp_nomi'] = komp_nomi
        return KOD

    # Xodim tekshir
    xodim = telefon_orqali_xodim(telefon)
    if xodim:
        xodim_id, ism, rol, komp_id = xodim
        await update.message.reply_text(
            f"👋 {ism}, kodni kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['tip'] = rol
        context.user_data['xodim_id'] = xodim_id
        context.user_data['ism'] = ism
        context.user_data['rol'] = rol
        context.user_data['komp_id'] = komp_id
        return KOD

    await update.message.reply_text(
        "❌ Siz tizimda ro'yxatdan o'tmagan ekansiz.\n"
        "Kompaniya adminiga murojaat qiling.",
        reply_markup=ReplyKeyboardRemove()
    )
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
            "✅ Xush kelibsiz, Super Admin!",
            reply_markup=super_admin_menu()
        )
        return SA_MENU

    elif tip in ('admin', 'hr', 'xodim'):
        xodim_id = context.user_data.get('xodim_id')
        if tip == 'admin':
            # Admin uchun kod kompaniya id bilan bog'liq emas, xodimlar jadvalidan
            xodim = xodim_olish(xodim_id)
            if not xodim or xodim[8] != kod:
                await update.message.reply_text("❌ Noto'g'ri kod!")
                return KOD
            komp_id = context.user_data['komp_id']
            admin_id_saqlash(komp_id, user_id)
            xodim_telegram_saqlash(xodim_id, user_id)
            await update.message.reply_text(
                f"✅ Admin sifatida kirdingiz!",
                reply_markup=admin_menu()
            )
            return ADM_MENU
        else:
            xodim = xodim_olish(xodim_id)
            if not xodim or xodim[8] != kod:
                await update.message.reply_text("❌ Noto'g'ri kod!")
                return KOD
            xodim_telegram_saqlash(xodim_id, user_id)
            if tip == 'hr':
                await update.message.reply_text(
                    f"✅ HR sifatida kirdingiz!",
                    reply_markup=hr_menu()
                )
                return HR_MENU
            else:
                await update.message.reply_text(
                    f"✅ Xush kelibsiz, {context.user_data['ism']}!",
                    reply_markup=xodim_menu()
                )
                return XOD_MENU

    await update.message.reply_text("❌ Xatolik!")
    return ConversationHandler.END

# ==================== MENULAR ====================

def super_admin_menu():
    return ReplyKeyboardMarkup([
        ["🏢 Kompaniyalar", "⚙️ Funksiyalar"],
        ["👥 Foydalanuvchilar", "📊 Hisobot"],
        ["🔐 Sozlamalar"]
    ], resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup([
        ["👥 Xodimlar", "📅 Davomat"],
        ["📊 Hisobot", "📍 GPS sozlash"],
        ["🏠 Bosh menu"]
    ], resize_keyboard=True)

def hr_menu():
    return ReplyKeyboardMarkup([
        ["✍️ Manual davomat", "📋 So'rovlar"],
        ["📊 Hisobot", "🏠 Bosh menu"]
    ], resize_keyboard=True)

def xodim_menu():
    return ReplyKeyboardMarkup([
        ["✅ Keldim", "🚪 Ketdim"],
        ["📋 Davomat", "📝 Sababli so'rov"],
        ["🏠 Bosh menu"]
    ], resize_keyboard=True)

# ==================== SUPER ADMIN PANEL ====================

async def sa_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text

    if matn == "🏢 Kompaniyalar":
        kompaniyalar = barcha_kompaniyalar()
        if not kompaniyalar:
            xabar = "📋 Hozircha kompaniya yo'q."
        else:
            xabar = "🏢 *Kompaniyalar ro'yxati:*\n\n"
            for k in kompaniyalar:
                holat_emoji = "✅" if k[3] == 'faol' else "❌"
                xabar += f"{holat_emoji} *{k[1]}*\n"
                xabar += f"   📞 {k[2] or '—'} | 📅 {k[4] or '—'}\n\n"

        await update.message.reply_text(
            xabar,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["➕ Yangi kompaniya", "✏️ Tahrirlash"],
                ["🔛 Faollashtirish", "🔴 To'xtatish"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True)
        )
        return SA_KOMP_MENU

    elif matn == "📊 Hisobot":
        await update.message.reply_text("⏳ Hisobot tayyorlanmoqda...")
        fayl = super_admin_hisobot()
        with open(fayl, 'rb') as f:
            await update.message.reply_document(f, filename=fayl)
        return SA_MENU

    elif matn == "🔐 Sozlamalar":
        await update.message.reply_text(
            "🔐 Sozlamalar:",
            reply_markup=ReplyKeyboardMarkup([
                ["🔑 Kodni o'zgartirish"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True)
        )
        return SA_SOZ_MENU

    elif matn == "🏠 Bosh menu" or matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Super Admin menu:", reply_markup=super_admin_menu())
        return SA_MENU

    return SA_MENU

async def sa_komp_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text

    if matn == "➕ Yangi kompaniya":
        await update.message.reply_text(
            "🏢 Yangi kompaniya nomini kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )
        return SA_KOMP_NOMI

    elif matn == "✏️ Tahrirlash":
        kompaniyalar = barcha_kompaniyalar()
        if not kompaniyalar:
            await update.message.reply_text("❌ Kompaniya yo'q!")
            return SA_KOMP_MENU
        tugmalar = [[f"🏢 {k[1]} (ID:{k[0]})"] for k in kompaniyalar]
        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text(
            "Tahrirlash uchun kompaniya tanlang:",
            reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True)
        )
        context.user_data['amal'] = 'tahrir'
        return SA_KOMP_TANLASH

    elif matn in ("🔛 Faollashtirish", "🔴 To'xtatish"):
        kompaniyalar = barcha_kompaniyalar()
        if not kompaniyalar:
            await update.message.reply_text("❌ Kompaniya yo'q!")
            return SA_KOMP_MENU
        tugmalar = [[f"🏢 {k[1]} (ID:{k[0]})"] for k in kompaniyalar]
        tugmalar.append(["🔙 Orqaga"])
        context.user_data['amal'] = 'faollashtir' if matn == "🔛 Faollashtirish" else 'toxtat'
        await update.message.reply_text(
            "Kompaniya tanlang:",
            reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True)
        )
        return SA_KOMP_TANLASH

    elif matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Super Admin menu:", reply_markup=super_admin_menu())
        return SA_MENU

    return SA_KOMP_MENU

async def sa_komp_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['yangi_komp_nomi'] = update.message.text.strip()
    await update.message.reply_text("📞 Admin telefon raqamini kiriting (+998XXXXXXXXX):")
    return SA_KOMP_ADMIN_TEL

async def sa_komp_admin_tel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telefon = update.message.text.strip()
    nomi = context.user_data['yangi_komp_nomi']
    komp_id = kompaniya_yaratish(nomi, telefon)
    await update.message.reply_text(
        f"✅ Kompaniya yaratildi!\n\n"
        f"🏢 *{nomi}*\n"
        f"📞 Admin: {telefon}\n"
        f"🆔 ID: {komp_id}",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup([
            ["➕ Yangi kompaniya", "✏️ Tahrirlash"],
            ["🔛 Faollashtirish", "🔴 To'xtatish"],
            ["🔙 Orqaga"]
        ], resize_keyboard=True)
    )
    return SA_KOMP_MENU

async def sa_komp_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text(
            "🏢 Kompaniyalar:",
            reply_markup=ReplyKeyboardMarkup([
                ["➕ Yangi kompaniya", "✏️ Tahrirlash"],
                ["🔛 Faollashtirish", "🔴 To'xtatish"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True)
        )
        return SA_KOMP_MENU

    try:
        komp_id = int(matn.split("ID:")[1].replace(")", "").strip())
    except:
        await update.message.reply_text("❌ Xatolik!")
        return SA_KOMP_TANLASH

    amal = context.user_data.get('amal')
    context.user_data['tanlangan_komp_id'] = komp_id

    if amal == 'faollashtir':
        kompaniya_holat_ozgartir(komp_id, 'faol')
        await update.message.reply_text(
            "✅ Kompaniya faollashtirildi!",
            reply_markup=super_admin_menu()
        )
        return SA_MENU

    elif amal == 'toxtat':
        kompaniya_holat_ozgartir(komp_id, 'nofaol')
        await update.message.reply_text(
            "✅ Kompaniya to'xtatildi!",
            reply_markup=super_admin_menu()
        )
        return SA_MENU

    elif amal == 'tahrir':
        await update.message.reply_text(
            "Nimani tahrirlash?",
            reply_markup=ReplyKeyboardMarkup([
                ["📝 Nomi", "📞 Admin telefon"],
                ["🔙 Orqaga"]
            ], resize_keyboard=True)
        )
        return SA_KOMP_TAHRIR

    return SA_KOMP_MENU

async def sa_komp_tahrir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=super_admin_menu())
        return SA_MENU

    if matn == "📝 Nomi":
        context.user_data['tahrir_maydon'] = 'nomi'
        await update.message.reply_text("Yangi nomni kiriting:", reply_markup=ReplyKeyboardRemove())
    elif matn == "📞 Admin telefon":
        context.user_data['tahrir_maydon'] = 'admin_telefon'
        await update.message.reply_text("Yangi telefonni kiriting:", reply_markup=ReplyKeyboardRemove())
    return SA_KOMP_TAHRIR_QIYMAT

async def sa_komp_tahrir_qiymat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qiymat = update.message.text.strip()
    komp_id = context.user_data['tanlangan_komp_id']
    maydon = context.user_data['tahrir_maydon']
    kompaniya_tahrirlash(komp_id, maydon, qiymat)
    await update.message.reply_text("✅ Saqlandi!", reply_markup=super_admin_menu())
    return SA_MENU

async def sa_soz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔑 Kodni o'zgartirish":
        await update.message.reply_text("Yangi kodni kiriting:", reply_markup=ReplyKeyboardRemove())
        context.user_data['soz_amal'] = 'kod'
        return SA_SOZ_MENU
    elif context.user_data.get('soz_amal') == 'kod':
        yangi_kod = matn.strip()
        super_admin_kod_ozgartir(yangi_kod)
        await update.message.reply_text(f"✅ Kod o'zgartirildi: {yangi_kod}", reply_markup=super_admin_menu())
        context.user_data.pop('soz_amal', None)
        return SA_MENU
    elif matn == "🔙 Orqaga":
        await update.message.reply_text("👑 Menu:", reply_markup=super_admin_menu())
        return SA_MENU
    return SA_SOZ_MENU

# ==================== ADMIN PANEL ====================

async def adm_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    komp_id = context.user_data.get('komp_id')

    if matn == "👥 Xodimlar":
        await update.message.reply_text(
            "👥 Xodimlar bo'limi:",
            reply_markup=ReplyKeyboardMarkup([
                ["➕ Xodim qo'shish", "📋 Xodimlar ro'yxati"],
                ["✏️ Tahrirlash", "🔙 Orqaga"]
            ], resize_keyboard=True)
        )
        return ADM_XODIM_MENU

    elif matn == "📅 Davomat":
        davomatlar = kompaniya_davomati(komp_id)
        if not davomatlar:
            xabar = "📅 Davomat ma'lumoti yo'q."
        else:
            xabar = "📅 *Oxirgi davomat:*\n\n"
            for d in davomatlar[-20:]:
                xabar += f"👤 {d[0]} | 📅 {d[1]}\n"
                xabar += f"   ⬅️ {d[2] or '—'} ➡️ {d[3] or '—'}\n\n"
        await update.message.reply_text(xabar, parse_mode='Markdown')
        return ADM_MENU

    elif matn == "📊 Hisobot":
        await update.message.reply_text("⏳ Hisobot tayyorlanmoqda...")
        fayl = kompaniya_hisobot(komp_id)
        with open(fayl, 'rb') as f:
            await update.message.reply_document(f, filename=fayl)
        return ADM_MENU

    elif matn == "📍 GPS sozlash":
        lat, lon, radius = get_gps(komp_id)
        await update.message.reply_text(
            f"📍 *Joriy GPS sozlamalari:*\n\n"
            f"📌 Lat: {lat}\n"
            f"📌 Lon: {lon}\n"
            f"📏 Radius: {radius} metr\n\n"
            f"Yangi latitude kiriting:",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
        return ADM_GPS_LAT

    elif matn == "🏠 Bosh menu":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=admin_menu())
        return ADM_MENU

    return ADM_MENU

async def adm_xodim_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    komp_id = context.user_data.get('komp_id')

    if matn == "➕ Xodim qo'shish":
        await update.message.reply_text(
            "👤 Xodim ismini kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADM_XODIM_ISM

    elif matn == "📋 Xodimlar ro'yxati":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            xabar = "👥 Xodimlar yo'q."
        else:
            xabar = "👥 *Xodimlar:*\n\n"
            for x in xodimlar:
                holat_emoji = "✅" if x[9] == 'faol' else "❌"
                xabar += f"{holat_emoji} *{x[1]}* — {x[2]}\n"
                xabar += f"   📞 {x[3]} | 💰 {x[4]:,.0f} so'm | 🎭 {x[7]}\n\n"
        await update.message.reply_text(xabar, parse_mode='Markdown')
        return ADM_XODIM_MENU

    elif matn == "✏️ Tahrirlash":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!")
            return ADM_XODIM_MENU
        tugmalar = [[f"👤 {x[1]} (ID:{x[0]})"] for x in xodimlar]
        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text(
            "Tahrirlash uchun xodim tanlang:",
            reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True)
        )
        context.user_data['xodim_amal'] = 'tahrir'
        return ADM_XODIM_TANLASH

    elif matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=admin_menu())
        return ADM_MENU

    return ADM_XODIM_MENU

# Xodim qo'shish bosqichlari
async def adm_xodim_ism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_ism'] = update.message.text.strip()
    btn = [[KeyboardButton("📱 Telefon yuborish", request_contact=True)]]
    await update.message.reply_text(
        "📞 Xodim telefon raqamini yuboring yoki yozing:",
        reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True)
    )
    return ADM_XODIM_TEL

async def adm_xodim_tel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        telefon = update.message.contact.phone_number
    else:
        telefon = update.message.text.strip()
    context.user_data['y_tel'] = telefon
    await update.message.reply_text("💼 Lavozimni kiriting:", reply_markup=ReplyKeyboardRemove())
    return ADM_XODIM_LAVOZIM

async def adm_xodim_lavozim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_lavozim'] = update.message.text.strip()
    await update.message.reply_text("💰 Oylik maoshni kiriting (so'mda):")
    return ADM_XODIM_OYLIK

async def adm_xodim_oylik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['y_oylik'] = float(update.message.text.strip().replace(',', '').replace(' ', ''))
    except:
        context.user_data['y_oylik'] = 0
    await update.message.reply_text("⏰ Ish boshlanish vaqti (09:00 formatda):")
    return ADM_XODIM_ISH_BOSH

async def adm_xodim_ish_bosh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_ish_bosh'] = update.message.text.strip()
    await update.message.reply_text("⏰ Ish tugash vaqti (18:00 formatda):")
    return ADM_XODIM_ISH_TUG

async def adm_xodim_ish_tug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['y_ish_tug'] = update.message.text.strip()
    await update.message.reply_text(
        "🎭 Rolni tanlang:",
        reply_markup=ReplyKeyboardMarkup([
            ["xodim", "hr"],
            ["admin"]
        ], resize_keyboard=True, one_time_keyboard=True)
    )
    return ADM_XODIM_ROL

async def adm_xodim_rol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rol = update.message.text.strip().lower()
    if rol not in ('xodim', 'hr', 'admin'):
        await update.message.reply_text("❌ xodim, hr yoki admin tanlang!")
        return ADM_XODIM_ROL

    komp_id = context.user_data['komp_id']
    kod = random_kod()

    xodim_id = xodim_qoshish(
        context.user_data['y_ism'],
        context.user_data['y_tel'],
        context.user_data['y_lavozim'],
        context.user_data['y_oylik'],
        context.user_data['y_ish_bosh'],
        context.user_data['y_ish_tug'],
        komp_id, rol, kod
    )

    await update.message.reply_text(
        f"✅ *Xodim qo'shildi!*\n\n"
        f"👤 {context.user_data['y_ism']}\n"
        f"💼 {context.user_data['y_lavozim']}\n"
        f"🎭 {rol}\n"
        f"🔑 Kirish kodi: `{kod}`\n\n"
        f"Xodimga bu kodni bering!",
        parse_mode='Markdown',
        reply_markup=admin_menu()
    )
    return ADM_MENU

async def adm_xodim_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=admin_menu())
        return ADM_MENU
    try:
        xodim_id = int(matn.split("ID:")[1].replace(")", "").strip())
        context.user_data['tahrir_xodim_id'] = xodim_id
    except:
        await update.message.reply_text("❌ Xatolik!")
        return ADM_XODIM_TANLASH

    await update.message.reply_text(
        "Nimani tahrirlash?",
        reply_markup=ReplyKeyboardMarkup([
            ["📝 Ism", "💼 Lavozim"],
            ["💰 Oylik", "⏰ Ish vaqti"],
            ["🎭 Rol", "🔑 Kod"],
            ["🔙 Orqaga"]
        ], resize_keyboard=True)
    )
    return ADM_XODIM_TAHRIR

async def adm_xodim_tahrir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("🏢 Admin menu:", reply_markup=admin_menu())
        return ADM_MENU

    maydon_map = {
        "📝 Ism": "ism",
        "💼 Lavozim": "lavozim",
        "💰 Oylik": "oylik",
        "🎭 Rol": "rol",
        "🔑 Kod": "kod"
    }
    if matn in maydon_map:
        context.user_data['tahrir_maydon'] = maydon_map[matn]
        await update.message.reply_text(f"Yangi {matn} kiriting:", reply_markup=ReplyKeyboardRemove())
        return ADM_XODIM_TAHRIR_QIYMAT
    elif matn == "⏰ Ish vaqti":
        await update.message.reply_text("Ish boshlanish vaqti (09:00):", reply_markup=ReplyKeyboardRemove())
        context.user_data['tahrir_maydon'] = 'ish_boshlanish'
        return ADM_XODIM_TAHRIR_QIYMAT
    return ADM_XODIM_TAHRIR

async def adm_xodim_tahrir_qiymat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qiymat = update.message.text.strip()
    xodim_id = context.user_data['tahrir_xodim_id']
    maydon = context.user_data['tahrir_maydon']
    xodim_tahrirlash(xodim_id, maydon, qiymat)
    await update.message.reply_text("✅ Saqlandi!", reply_markup=admin_menu())
    return ADM_MENU

# GPS sozlash
async def adm_gps_lat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['gps_lat'] = float(update.message.text.strip())
        await update.message.reply_text("Longitude kiriting:")
        return ADM_GPS_LON
    except:
        await update.message.reply_text("❌ To'g'ri son kiriting (masalan: 41.299496):")
        return ADM_GPS_LAT

async def adm_gps_lon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['gps_lon'] = float(update.message.text.strip())
        await update.message.reply_text("Radius kiriting (metrda, masalan: 200):")
        return ADM_GPS_RADIUS
    except:
        await update.message.reply_text("❌ To'g'ri son kiriting:")
        return ADM_GPS_LON

async def adm_gps_radius(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        radius = int(update.message.text.strip())
        komp_id = context.user_data['komp_id']
        kompaniya_tahrirlash(komp_id, 'gps_lat', context.user_data['gps_lat'])
        kompaniya_tahrirlash(komp_id, 'gps_lon', context.user_data['gps_lon'])
        kompaniya_tahrirlash(komp_id, 'gps_radius', radius)
        await update.message.reply_text(
            f"✅ GPS sozlandi!\n📌 {context.user_data['gps_lat']}, {context.user_data['gps_lon']}\n📏 {radius}m",
            reply_markup=admin_menu()
        )
        return ADM_MENU
    except:
        await update.message.reply_text("❌ To'g'ri son kiriting:")
        return ADM_GPS_RADIUS

# ==================== HR PANEL ====================

async def hr_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    komp_id = context.user_data.get('komp_id')

    if matn == "✍️ Manual davomat":
        xodimlar = kompaniya_xodimlari(komp_id)
        if not xodimlar:
            await update.message.reply_text("❌ Xodim yo'q!")
            return HR_MENU
        tugmalar = [[f"👤 {x[1]} (ID:{x[0]})"] for x in xodimlar]
        tugmalar.append(["🔙 Orqaga"])
        await update.message.reply_text(
            "Xodim tanlang:",
            reply_markup=ReplyKeyboardMarkup(tugmalar, resize_keyboard=True)
        )
        return HR_MANUAL_XODIM

    elif matn == "📊 Hisobot":
        await update.message.reply_text("⏳ Hisobot tayyorlanmoqda...")
        fayl = kompaniya_hisobot(komp_id)
        with open(fayl, 'rb') as f:
            await update.message.reply_document(f, filename=fayl)
        return HR_MENU

    elif matn == "🏠 Bosh menu":
        await update.message.reply_text("👔 HR menu:", reply_markup=hr_menu())
        return HR_MENU

    return HR_MENU

async def hr_manual_xodim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    if matn == "🔙 Orqaga":
        await update.message.reply_text("👔 HR menu:", reply_markup=hr_menu())
        return HR_MENU
    try:
        xodim_id = int(matn.split("ID:")[1].replace(")", "").strip())
        context.user_data['manual_xodim_id'] = xodim_id
    except:
        await update.message.reply_text("❌ Xatolik!")
        return HR_MANUAL_XODIM
    await update.message.reply_text(
        "📅 Sana kiriting (YYYY-MM-DD, masalan: 2026-05-23):",
        reply_markup=ReplyKeyboardRemove()
    )
    return HR_MANUAL_SANA

async def hr_manual_sana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['manual_sana'] = update.message.text.strip()
    await update.message.reply_text("⏰ Keldi vaqti (HH:MM, masalan: 09:00):")
    return HR_MANUAL_KELDI

async def hr_manual_keldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['manual_keldi'] = update.message.text.strip()
    await update.message.reply_text("⏰ Ketdi vaqti (HH:MM, masalan: 18:00):")
    return HR_MANUAL_KETDI

async def hr_manual_ketdi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['manual_ketdi'] = update.message.text.strip()
    await update.message.reply_text(
        "📋 Holat tanlang:",
        reply_markup=ReplyKeyboardMarkup([
            ["normal", "sababli"],
            ["kasal", "ta'til"]
        ], resize_keyboard=True, one_time_keyboard=True)
    )
    return HR_MANUAL_HOLAT

async def hr_manual_holat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['manual_holat'] = update.message.text.strip()
    await update.message.reply_text("📝 Izoh kiriting (yoki - yozing):", reply_markup=ReplyKeyboardRemove())
    return HR_MANUAL_IZOH

async def hr_manual_izoh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    izoh = update.message.text.strip()
    if izoh == '-':
        izoh = ''
    xodim_id = context.user_data['manual_xodim_id']
    komp_id = context.user_data['komp_id']
    xodim = xodim_olish(xodim_id)
    natija = manual_davomat(
        xodim_id, komp_id,
        context.user_data['manual_sana'],
        context.user_data['manual_keldi'],
        context.user_data['manual_ketdi'],
        context.user_data['manual_holat'],
        izoh,
        xodim[1] if xodim else 'HR',
        update.effective_user.id
    )
    await update.message.reply_text(natija, reply_markup=hr_menu())
    return HR_MENU

# ==================== XODIM PANEL ====================

async def xod_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text
    xodim_id = context.user_data.get('xodim_id')
    komp_id = context.user_data.get('komp_id')

    if matn == "✅ Keldim":
        # GPS tekshirish
        komp = kompaniya_olish(komp_id)
        gps_aktiv = komp[9] if komp else True
        if gps_aktiv:
            btn = [[KeyboardButton("📍 GPS yuborish", request_location=True)]]
            await update.message.reply_text(
                "📍 Joylashuvingizni yuboring:",
                reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True)
            )
            return XOD_KELDI_GPS
        else:
            natija = keldi_belgilash(xodim_id, komp_id)
            await update.message.reply_text(natija, reply_markup=xodim_menu())
            return XOD_MENU

    elif matn == "🚪 Ketdim":
        komp = kompaniya_olish(komp_id)
        gps_aktiv = komp[9] if komp else True
        if gps_aktiv:
            btn = [[KeyboardButton("📍 GPS yuborish", request_location=True)]]
            await update.message.reply_text(
                "📍 Joylashuvingizni yuboring:",
                reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True, one_time_keyboard=True)
            )
            return XOD_KETDI_GPS
        else:
            natija = ketdi_belgilash(xodim_id, komp_id)
            await update.message.reply_text(natija, reply_markup=xodim_menu())
            return XOD_MENU

    elif matn == "📋 Davomat":
        davomatlar = xodim_davomati(xodim_id)
        if not davomatlar:
            await update.message.reply_text("📋 Davomat yo'q.")
        else:
            xabar = "📋 *Mening davomatim:*\n\n"
            for d in davomatlar[-15:]:
                holat_emoji = {"normal": "✅", "sababli": "📝", "kasal": "🤒", "ta'til": "🏖"}.get(d[5], "❓")
                xabar += f"{holat_emoji} {d[0]}: {d[1] or '—'} → {d[2] or '—'}\n"
                if d[4] and d[4] > 0:
                    xabar += f"   ⚠️ Kechikish: {d[4]} daqiqa\n"
            await update.message.reply_text(xabar, parse_mode='Markdown')
        return XOD_MENU

    elif matn == "📝 Sababli so'rov":
        await update.message.reply_text(
            "📅 Qaysi kun uchun? (YYYY-MM-DD):",
            reply_markup=ReplyKeyboardRemove()
        )
        return XOD_SABAB_SANA

    elif matn == "🏠 Bosh menu":
        await update.message.reply_text("👋 Menu:", reply_markup=xodim_menu())
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

    komp_lat, komp_lon, radius = get_gps(komp_id)
    ichida, masofa = gps_tekshir(lat, lon, komp_lat, komp_lon, radius)

    if not ichida:
        await update.message.reply_text(
            f"❌ Siz ish joyidan tashqarisiz!\n📏 Masofa: {masofa} metr (ruxsat: {radius} metr)",
            reply_markup=xodim_menu()
        )
        return XOD_MENU

    # Selfie tekshir
    komp = kompaniya_olish(komp_id)
    selfie_aktiv = komp[10] if komp else True
    if selfie_aktiv:
        natija = keldi_belgilash(xodim_id, komp_id)
        await update.message.reply_text(
            f"{natija}\n\n📸 Selfie yuboring:",
            reply_markup=ReplyKeyboardRemove()
        )
        return XOD_KELDI_RASM
    else:
        natija = keldi_belgilash(xodim_id, komp_id)
        await update.message.reply_text(natija, reply_markup=xodim_menu())
        return XOD_MENU

async def xod_keldi_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo and not update.message.video_note:
        await update.message.reply_text("❌ Selfie yoki video yuboring!")
        return XOD_KELDI_RASM

    xodim_id = context.user_data['xodim_id']
    if update.message.photo:
        rasm_id = update.message.photo[-1].file_id
    else:
        rasm_id = update.message.video_note.file_id

    keldi_rasm_saqlash(xodim_id, rasm_id)
    await update.message.reply_text("✅ Davomat qabul qilindi!", reply_markup=xodim_menu())
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
    ichida, masofa = gps_tekshir(lat, lon, komp_lat, komp_lon, radius)

    if not ichida:
        await update.message.reply_text(
            f"❌ Siz ish joyidan tashqarisiz!\n📏 Masofa: {masofa} metr",
            reply_markup=xodim_menu()
        )
        return XOD_MENU

    komp = kompaniya_olish(komp_id)
    selfie_aktiv = komp[10] if komp else True
    if selfie_aktiv:
        natija = ketdi_belgilash(xodim_id, komp_id)
        await update.message.reply_text(
            f"{natija}\n\n📸 Selfie yuboring:",
            reply_markup=ReplyKeyboardRemove()
        )
        return XOD_KETDI_RASM
    else:
        natija = ketdi_belgilash(xodim_id, komp_id)
        await update.message.reply_text(natija, reply_markup=xodim_menu())
        return XOD_MENU

async def xod_ketdi_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo and not update.message.video_note:
        await update.message.reply_text("❌ Selfie yoki video yuboring!")
        return XOD_KETDI_RASM

    xodim_id = context.user_data['xodim_id']
    if update.message.photo:
        rasm_id = update.message.photo[-1].file_id
    else:
        rasm_id = update.message.video_note.file_id

    ketdi_rasm_saqlash(xodim_id, rasm_id)
    await update.message.reply_text("✅ Siz chiqishni belgiladingiz!", reply_markup=xodim_menu())
    return XOD_MENU

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

    # HR larga xabar yuborish
    from telegram import Bot
    bot = context.bot
    hr_list = hr_idlari(komp_id)
    xodim = xodim_olish(xodim_id)
    xodim_ism = xodim[1] if xodim else "Xodim"

    for hr_id in hr_list:
        try:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"sorov_tasdiqlash_{sorov_id}_{xodim_id}_{sana}"),
                    InlineKeyboardButton("❌ Rad etish", callback_data=f"sorov_rad_{sorov_id}_{xodim_id}_{sana}")
                ]
            ])
            await bot.send_message(
                hr_id,
                f"📝 *Sababli so'rov*\n\n"
                f"👤 {xodim_ism}\n"
                f"📅 {sana}\n"
                f"📋 {sabab}",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            pass

    await update.message.reply_text(
        "✅ So'rovingiz HR ga yuborildi!",
        reply_markup=xodim_menu()
    )
    return XOD_MENU

async def sorov_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    # format: sorov_tasdiqlash_ID_XODIM_ID_SANA
    amal = data[1]
    sorov_id = int(data[2])
    xodim_id = int(data[3])
    sana = data[4]

    # Sabab olish
    from database import connect
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT sabab FROM sababli_sorovlar WHERE id=%s", (sorov_id,))
    row = cur.fetchone()
    sabab = row[0] if row else ''
    cur.close()
    conn.close()

    holat = 'tasdiqlandi' if amal == 'tasdiqlash' else 'rad_etildi'
    sababli_sorov_yangilash(sorov_id, holat, xodim_id, sana, sabab)

    emoji = "✅" if amal == 'tasdiqlash' else "❌"
    await query.edit_message_text(
        f"{emoji} So'rov {holat}!\n\n"
        f"📅 {sana}\n"
        f"📋 {sabab}"
    )

# ==================== XATO HANDLER ====================

async def xato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Xato: {context.error}")

# ==================== MAIN ====================

def main():
    create_tables()
    print("Baza tayyor!")

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TELEFON: [MessageHandler(filters.CONTACT | filters.TEXT, telefon_qabul)],
            KOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, kod_tekshir)],

            # Super Admin
            SA_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_menu)],
            SA_KOMP_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_menu)],
            SA_KOMP_NOMI: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_nomi)],
            SA_KOMP_ADMIN_TEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_admin_tel)],
            SA_KOMP_TANLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_tanlash)],
            SA_KOMP_TAHRIR: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_tahrir)],
            SA_KOMP_TAHRIR_QIYMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_komp_tahrir_qiymat)],
            SA_SOZ_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, sa_soz_menu)],

            # Admin
            ADM_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_menu)],
            ADM_XODIM_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_menu)],
            ADM_XODIM_ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_ism)],
            ADM_XODIM_TEL: [MessageHandler(filters.CONTACT | filters.TEXT, adm_xodim_tel)],
            ADM_XODIM_LAVOZIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_lavozim)],
            ADM_XODIM_OYLIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_oylik)],
            ADM_XODIM_ISH_BOSH: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_ish_bosh)],
            ADM_XODIM_ISH_TUG: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_ish_tug)],
            ADM_XODIM_ROL: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_rol)],
            ADM_XODIM_TANLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_tanlash)],
            ADM_XODIM_TAHRIR: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_tahrir)],
            ADM_XODIM_TAHRIR_QIYMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_xodim_tahrir_qiymat)],
            ADM_GPS_LAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_gps_lat)],
            ADM_GPS_LON: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_gps_lon)],
            ADM_GPS_RADIUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_gps_radius)],

            # HR
            HR_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_menu_handler)],
            HR_MANUAL_XODIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_manual_xodim)],
            HR_MANUAL_SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_manual_sana)],
            HR_MANUAL_KELDI: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_manual_keldi)],
            HR_MANUAL_KETDI: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_manual_ketdi)],
            HR_MANUAL_HOLAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_manual_holat)],
            HR_MANUAL_IZOH: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_manual_izoh)],

            # Xodim
            XOD_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, xod_menu)],
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
    app.add_error_handler(xato)

    print("Bot ishlamoqda...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()