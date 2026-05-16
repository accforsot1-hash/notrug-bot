import os
import sqlite3
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ==================== AYARLAR ====================
BOT_TOKEN = "8225017117:AAGt7h2nfzwvDNk0sBYZEc7Kk6BFIKaC44c"
TELEGRAM_GROUP_ID = "@notrugfun"  # Grubun kullanıcı adı
TWITTER_USERNAME = "NOTRUGfun"
PINNED_TWEET_ID = "BURAYA_PINNED_TWEET_ID_YAZ"  # Tweet ID'sini yaz
MAX_POINTS = 100
MAX_TOKENS = 2000
MIN_TOKENS = 500
LEADERBOARD_BONUS = 10000
LEADERBOARD_SIZE = 5
LAUNCH_DATE = None  # Launch günü "2026-06-01" gibi yaz

# Puan tablosu
POINTS = {
    "twitter_follow": 20,
    "pinned_retweet": 25,
    "pinned_comment": 15,
    "telegram_join": 10,
    "telegram_invite": 15,
    "tweet_comment": 10,
}

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect("notrug.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 0,
            tokens INTEGER DEFAULT 0,
            wallet TEXT,
            twitter_username TEXT,
            ref_code TEXT UNIQUE,
            referred_by INTEGER,
            twitter_follow INTEGER DEFAULT 0,
            pinned_retweet INTEGER DEFAULT 0,
            pinned_comment INTEGER DEFAULT 0,
            telegram_join INTEGER DEFAULT 0,
            claimed INTEGER DEFAULT 0,
            joined_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            tweet_url TEXT,
            points_given INTEGER,
            submitted_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user(telegram_id):
    conn = sqlite3.connect("notrug.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(telegram_id, username, ref_code, referred_by=None):
    conn = sqlite3.connect("notrug.db")
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO users (telegram_id, username, ref_code, referred_by, joined_at)
            VALUES (?, ?, ?, ?, ?)
        """, (telegram_id, username, ref_code, referred_by, datetime.now().isoformat()))
        conn.commit()
    except:
        pass
    conn.close()

def update_points(telegram_id, points, field=None):
    conn = sqlite3.connect("notrug.db")
    c = conn.cursor()
    if field:
        c.execute(f"UPDATE users SET points = points + ?, {field} = 1 WHERE telegram_id = ?",
                  (points, telegram_id))
    else:
        c.execute("UPDATE users SET points = points + ? WHERE telegram_id = ?",
                  (points, telegram_id))
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = sqlite3.connect("notrug.db")
    c = conn.cursor()
    c.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT ?",
              (LEADERBOARD_SIZE,))
    result = c.fetchall()
    conn.close()
    return result

def get_total_users():
    conn = sqlite3.connect("notrug.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    result = c.fetchone()[0]
    conn.close()
    return result

def add_submission(telegram_id, tweet_url, points):
    conn = sqlite3.connect("notrug.db")
    c = conn.cursor()
    # Aynı tweet daha önce gönderilmiş mi?
    c.execute("SELECT id FROM submissions WHERE tweet_url = ?", (tweet_url,))
    exists = c.fetchone()
    if exists:
        conn.close()
        return False
    c.execute("""
        INSERT INTO submissions (telegram_id, tweet_url, points_given, submitted_at)
        VALUES (?, ?, ?, ?)
    """, (telegram_id, tweet_url, points, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return True

def calculate_tokens(points):
    if points >= 100:
        return MAX_TOKENS
    elif points >= 50:
        return MIN_TOKENS
    return 0

# ==================== HELPERS ====================
def generate_ref_code(telegram_id):
    return f"NOTRUG{telegram_id}"

def verify_tweet(tweet_url, twitter_username=None):
    """Tweet URL'sinin geçerli olup olmadığını kontrol et"""
    if not tweet_url:
        return False
    if "twitter.com" not in tweet_url and "x.com" not in tweet_url:
        return False
    if "/status/" not in tweet_url:
        return False
    return True

def get_tweet_id_from_url(url):
    """Tweet URL'sinden ID çıkar"""
    try:
        parts = url.split("/status/")
        if len(parts) > 1:
            tweet_id = parts[1].split("?")[0].split("/")[0]
            return tweet_id
    except:
        pass
    return None

# ==================== KOMUTLAR ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    username = update.effective_user.username or f"user{telegram_id}"

    # Referral kontrolü
    referred_by = None
    if context.args:
        ref_code = context.args[0]
        conn = sqlite3.connect("notrug.db")
        c = conn.cursor()
        c.execute("SELECT telegram_id FROM users WHERE ref_code = ?", (ref_code,))
        referrer = c.fetchone()
        conn.close()
        if referrer and referrer[0] != telegram_id:
            referred_by = referrer[0]

    # Kullanıcı var mı?
    user = get_user(telegram_id)
    if not user:
        ref_code = generate_ref_code(telegram_id)
        create_user(telegram_id, username, ref_code, referred_by)

        # Referral bonusu ver
        if referred_by:
            referrer_user = get_user(referred_by)
            if referrer_user and referrer_user[7] < MAX_POINTS:
                update_points(referred_by, POINTS["telegram_invite"])
                try:
                    await context.bot.send_message(
                        chat_id=referred_by,
                        text=f"🎉 Birisi davet linkinle katıldı! +{POINTS['telegram_invite']} puan kazandın!"
                    )
                except:
                    pass

    user = get_user(telegram_id)
    ref_code = user[6] if user else generate_ref_code(telegram_id)

    welcome_text = f"""
🛡️ *Welcome to $NOTRUG Airdrop Bot!*

The most honest project in crypto.
We will rug you. Just... not yet. 🏖️

━━━━━━━━━━━━━━━━━━━━
📋 *GÖREV SİSTEMİ*

Görev yap → Puan kazan → Token al!

🏆 *Max 2,000 NOTRUG* kazanabilirsin
🥇 *İlk 5'e gir* → +10,000 NOTRUG bonus!

━━━━━━━━━━━━━━━━━━━━
🚀 *BAŞLAMAK İÇİN:*

/tasks → Görev listesi
/points → Puanın
/ref → Davet linkin
/wallet → Cüzdan adresi ekle
/top → Leaderboard
/help → Yardım

━━━━━━━━━━━━━━━━━━━━
🌐 notrug.fun
"""

    keyboard = [
        [InlineKeyboardButton("📋 Görevler", callback_data="tasks"),
         InlineKeyboardButton("📊 Puanım", callback_data="points")],
        [InlineKeyboardButton("🔗 Davet Linkim", callback_data="ref"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="top")],
        [InlineKeyboardButton("🌐 notrug.fun", url="https://notrug.fun")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, parse_mode="Markdown",
                                     reply_markup=reply_markup)

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user:
        await update.message.reply_text("Önce /start yaz!")
        return

    points = user[2]
    twitter_follow = user[8]
    pinned_retweet = user[9]
    pinned_comment = user[10]
    telegram_join = user[11]

    def check(done):
        return "✅" if done else "⬜"

    tasks_text = f"""
📋 *$NOTRUG GÖREV LİSTESİ*

Toplam puanın: *{points}/{MAX_POINTS}*

━━━━━━━━━━━━━━━━━━━━
🐦 *TWITTER GÖREVLERİ*

{check(twitter_follow)} @NOTRUGfun takip et → *+20 puan*
→ /submit\\_follow Twitter\\_kullanici\\_adin

{check(pinned_retweet)} Pinned tweet'i retweet et → *+25 puan*
→ /submit\\_retweet tweet\\_linki

{check(pinned_comment)} Pinned tweet'e yorum at → *+15 puan*
→ /submit\\_comment tweet\\_linki

💬 Yeni tweet'lere yorum at → *+10 puan* (sınırsız)
→ /submit\\_comment tweet\\_linki

━━━━━━━━━━━━━━━━━━━━
✈️ *TELEGRAM GÖREVLERİ*

{check(telegram_join)} Gruba katıl → *+10 puan*
→ /submit\\_join

👥 Arkadaş davet et → *+15 puan* (her biri)
→ /ref linkini paylaş

━━━━━━━━━━━━━━━━━━━━
🏆 *ÖDÜLLER*

50-99 puan → 500 NOTRUG
100 puan → 2,000 NOTRUG
İlk 5 → +10,000 NOTRUG BONUS!

━━━━━━━━━━━━━━━━━━━━
🌐 notrug.fun | @NOTRUGfun
"""

    await update.message.reply_text(tasks_text, parse_mode="Markdown")

async def points_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user:
        await update.message.reply_text("Önce /start yaz!")
        return

    points = user[2]
    tokens = calculate_tokens(points)
    wallet = user[4] or "Eklenmedi"

    # Leaderboard sırası
    lb = get_leaderboard()
    rank = "Top 5 dışı"
    for i, (uname, pts) in enumerate(lb):
        if uname == user[1]:
            rank = f"#{i+1} 🏆"
            break

    text = f"""
📊 *PUAN DURUMUN*

👤 @{user[1]}
⭐ Puan: *{points}/{MAX_POINTS}*
🪙 Kazanılacak token: *{tokens} NOTRUG*
🏆 Sıralama: *{rank}*
💼 Cüzdan: `{wallet}`

━━━━━━━━━━━━━━━━━━━━
{'✅ Max puana ulaştın!' if points >= MAX_POINTS else f'📈 {MAX_POINTS - points} puan daha topla!'}
{'🎯 2,000 NOTRUG kazanacaksın!' if points >= MAX_POINTS else ''}

Cüzdan eklemek için:
/wallet CUZDAN\\_ADRESIN
"""

    await update.message.reply_text(text, parse_mode="Markdown")

async def ref_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user:
        await update.message.reply_text("Önce /start yaz!")
        return

    ref_code = user[6]
    ref_link = f"https://t.me/NOTRUGairdrop_bot?start={ref_code}"

    text = f"""
🔗 *DAVET LİNKİN*

`{ref_link}`

━━━━━━━━━━━━━━━━━━━━
Bu linki paylaş:
• Her katılan kişi → *+15 puan* kazanırsın
• Sınır yok, ne kadar davet o kadar puan!
• Leaderboard'da üste çık → *+10,000 NOTRUG bonus!*

━━━━━━━━━━━━━━━━━━━━
💡 WhatsApp, Twitter, Instagram'da paylaş!
"""

    await update.message.reply_text(text, parse_mode="Markdown")

async def wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user:
        await update.message.reply_text("Önce /start yaz!")
        return

    if not context.args:
        await update.message.reply_text(
            "💼 Solana cüzdan adresini ekle:\n\n/wallet CUZDAN\\_ADRESIN",
            parse_mode="Markdown"
        )
        return

    wallet = context.args[0]

    # Basit Solana adres kontrolü
    if len(wallet) < 32 or len(wallet) > 44:
        await update.message.reply_text("❌ Geçersiz Solana adresi! Kontrol et.")
        return

    conn = sqlite3.connect("notrug.db")
    c = conn.cursor()
    c.execute("UPDATE users SET wallet = ? WHERE telegram_id = ?", (wallet, telegram_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ Cüzdan adresi kaydedildi!\n\n`{wallet}`",
        parse_mode="Markdown"
    )

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lb = get_leaderboard()
    total = get_total_users()

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    text = "🏆 *LEADERBOARD — İLK 5*\n\n"
    text += f"Toplam katılımcı: *{total}*\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"

    for i, (username, pts) in enumerate(lb):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        text += f"{medal} @{username} — *{pts} puan*\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += "İlk 5'e gir → *+10,000 NOTRUG bonus!* 🎁\n\n"
    text += "Puan toplamaya devam et:\n"
    text += "• Yeni tweetlere yorum at\n"
    text += "• Arkadaş davet et\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def submit_follow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user:
        await update.message.reply_text("Önce /start yaz!")
        return

    if user[8]:  # Zaten yapılmış
        await update.message.reply_text("✅ Bu görevi zaten tamamladın!")
        return

    if not context.args:
        await update.message.reply_text(
            "Twitter kullanıcı adını yaz:\n\n/submit\\_follow kullanici\\_adin",
            parse_mode="Markdown"
        )
        return

    twitter_username = context.args[0].replace("@", "")

    conn = sqlite3.connect("notrug.db")
    c = conn.cursor()
    c.execute("UPDATE users SET twitter_username = ?, twitter_follow = 1, points = points + ? WHERE telegram_id = ?",
              (twitter_username, POINTS["twitter_follow"], telegram_id))
    conn.commit()
    conn.close()

    user = get_user(telegram_id)
    tokens = calculate_tokens(user[2])

    await update.message.reply_text(
        f"✅ *Twitter takip görevi tamamlandı!*\n\n"
        f"+{POINTS['twitter_follow']} puan eklendi!\n"
        f"Toplam puan: *{user[2]}*\n"
        f"Kazanılacak token: *{tokens} NOTRUG*",
        parse_mode="Markdown"
    )

async def submit_retweet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user:
        await update.message.reply_text("Önce /start yaz!")
        return

    if user[9]:  # Zaten yapılmış
        await update.message.reply_text("✅ Bu görevi zaten tamamladın!")
        return

    if not context.args:
        await update.message.reply_text(
            "Retweet linkini gönder:\n\n/submit\\_retweet tweet\\_linki",
            parse_mode="Markdown"
        )
        return

    tweet_url = context.args[0]

    if not verify_tweet(tweet_url):
        await update.message.reply_text("❌ Geçersiz tweet linki!")
        return

    conn = sqlite3.connect("notrug.db")
    c = conn.cursor()
    c.execute("UPDATE users SET pinned_retweet = 1, points = points + ? WHERE telegram_id = ?",
              (POINTS["pinned_retweet"], telegram_id))
    conn.commit()
    conn.close()

    user = get_user(telegram_id)
    tokens = calculate_tokens(user[2])

    await update.message.reply_text(
        f"✅ *Retweet görevi tamamlandı!*\n\n"
        f"+{POINTS['pinned_retweet']} puan eklendi!\n"
        f"Toplam puan: *{user[2]}*\n"
        f"Kazanılacak token: *{tokens} NOTRUG*",
        parse_mode="Markdown"
    )

async def submit_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user:
        await update.message.reply_text("Önce /start yaz!")
        return

    if not context.args:
        await update.message.reply_text(
            "Yorum attığın tweet linkini gönder:\n\n/submit\\_comment tweet\\_linki",
            parse_mode="Markdown"
        )
        return

    tweet_url = context.args[0]

    if not verify_tweet(tweet_url):
        await update.message.reply_text("❌ Geçersiz tweet linki!")
        return

    # Aynı tweet daha önce gönderilmiş mi?
    ok = add_submission(telegram_id, tweet_url, POINTS["tweet_comment"])
    if not ok:
        await update.message.reply_text("❌ Bu tweet zaten gönderilmiş!")
        return

    # Max puan kontrolü
    current_points = user[2]
    if current_points >= MAX_POINTS:
        await update.message.reply_text(
            "🏆 Max puana ulaştın! Ama leaderboard için puan toplamaya devam edebilirsin!"
        )
        # Leaderboard için puanı yine de ver
        update_points(telegram_id, POINTS["tweet_comment"])
    else:
        update_points(telegram_id, POINTS["tweet_comment"])

    # Pinned comment mi?
    tweet_id = get_tweet_id_from_url(tweet_url)
    is_pinned = tweet_id == PINNED_TWEET_ID

    points_given = POINTS["pinned_comment"] if is_pinned else POINTS["tweet_comment"]
    if is_pinned and not user[10]:
        conn = sqlite3.connect("notrug.db")
        c = conn.cursor()
        c.execute("UPDATE users SET pinned_comment = 1 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        conn.close()

    user = get_user(telegram_id)
    tokens = calculate_tokens(user[2])

    await update.message.reply_text(
        f"✅ *Yorum görevi tamamlandı!*\n\n"
        f"+{points_given} puan eklendi!\n"
        f"Toplam puan: *{user[2]}*\n"
        f"Kazanılacak token: *{tokens} NOTRUG*",
        parse_mode="Markdown"
    )

async def submit_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user:
        await update.message.reply_text("Önce /start yaz!")
        return

    if user[11]:  # Zaten yapılmış
        await update.message.reply_text("✅ Bu görevi zaten tamamladın!")
        return

    # Grupta mı kontrol et
    try:
        member = await context.bot.get_chat_member(TELEGRAM_GROUP_ID, telegram_id)
        if member.status in ["member", "administrator", "creator"]:
            conn = sqlite3.connect("notrug.db")
            c = conn.cursor()
            c.execute("UPDATE users SET telegram_join = 1, points = points + ? WHERE telegram_id = ?",
                      (POINTS["telegram_join"], telegram_id))
            conn.commit()
            conn.close()

            user = get_user(telegram_id)
            tokens = calculate_tokens(user[2])

            await update.message.reply_text(
                f"✅ *Telegram katılım görevi tamamlandı!*\n\n"
                f"+{POINTS['telegram_join']} puan eklendi!\n"
                f"Toplam puan: *{user[2]}*\n"
                f"Kazanılacak token: *{tokens} NOTRUG*",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Önce gruba katıl!\n\nt.me/notrugfun"
            )
    except:
        await update.message.reply_text(
            f"❌ Önce gruba katıl!\n\nt.me/notrugfun"
        )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🛡️ *$NOTRUG BOT YARDIM*

━━━━━━━━━━━━━━━━━━━━
📋 *KOMUTLAR*

/start → Botu başlat
/tasks → Görev listesi
/points → Puan durumun
/ref → Davet linkin
/wallet ADRES → Cüzdan ekle
/top → Leaderboard

━━━━━━━━━━━━━━━━━━━━
📤 *GÖREV GÖNDER*

/submit\\_follow kullanici\\_adin
/submit\\_retweet tweet\\_linki
/submit\\_comment tweet\\_linki
/submit\\_join

━━━━━━━━━━━━━━━━━━━━
🌐 notrug.fun | @NOTRUGfun
"""
    await update.message.reply_text(text, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "tasks":
        update.message = query.message
        update.effective_user = query.from_user
        await tasks(update, context)
    elif query.data == "points":
        update.message = query.message
        update.effective_user = query.from_user
        await points_cmd(update, context)
    elif query.data == "ref":
        update.message = query.message
        update.effective_user = query.from_user
        await ref_cmd(update, context)
    elif query.data == "top":
        update.message = query.message
        update.effective_user = query.from_user
        await top_cmd(update, context)

# ==================== MAIN ====================
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("points", points_cmd))
    app.add_handler(CommandHandler("ref", ref_cmd))
    app.add_handler(CommandHandler("wallet", wallet_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("submit_follow", submit_follow))
    app.add_handler(CommandHandler("submit_retweet", submit_retweet))
    app.add_handler(CommandHandler("submit_comment", submit_comment))
    app.add_handler(CommandHandler("submit_join", submit_join))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🛡️ NOTRUG Airdrop Bot başladı!")
    app.run_polling()

if __name__ == "__main__":
    main()
