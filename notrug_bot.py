import sqlite3
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8225017117:AAGt7h2nfzwvDNk0sBYZEc7Kk6BFIKaC44c"
ADMIN_ID = 6365046594
GROUP_USERNAME = "notrugfun"
GROUP_ID = "@notrugfun"
TWITTER_URL = "https://twitter.com/NOTRUGfun"
PINNED_TWEET = "https://x.com/NOTRUGfun/status/2055699214861017091"
NOTRUG_AMOUNT = 10000
TOP5_BONUS = 10000
REQUIRED_POINTS = 100

POINTS = {
    "twitter_follow": 25,
    "tweet_like": 25,
    "telegram_join": 20,
    "tweet_retweet": 15,
    "tweet_comment": 15,
    "new_tweet_comment": 10,
    "daily_message": 10,
    "referral": 10,
    "twitter_bio": 10,
    "share_link": 10,
}

def init_db():
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        telegram_id      INTEGER PRIMARY KEY,
        username         TEXT,
        wallet           TEXT,
        twitter_done     INTEGER DEFAULT 0,
        telegram_done    INTEGER DEFAULT 0,
        tweet_like_done  INTEGER DEFAULT 0,
        tweet_rt_done    INTEGER DEFAULT 0,
        tweet_cmt_done   INTEGER DEFAULT 0,
        twitter_bio_done INTEGER DEFAULT 0,
        share_link_done  INTEGER DEFAULT 0,
        points           INTEGER DEFAULT 0,
        claimed          INTEGER DEFAULT 0,
        step             TEXT DEFAULT 'idle',
        ref_code         TEXT UNIQUE,
        referred_by      INTEGER,
        last_daily       TEXT,
        daily_count      INTEGER DEFAULT 0,
        created_at       TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS tweet_comments (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        tweet_url   TEXT UNIQUE,
        created_at  TEXT
    )""")
    conn.commit()
    conn.close()

def get_user(tid):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
    r = c.fetchone()
    conn.close()
    return r

def create_user(tid, username, ref_code, referred_by=None):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO users (telegram_id,username,ref_code,referred_by,created_at)
                     VALUES (?,?,?,?,?)""",
                  (tid, username, ref_code, referred_by, datetime.now().isoformat()))
        conn.commit()
    except:
        pass
    conn.close()

def set_field(tid, field, value):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE telegram_id=?", (value, tid))
    conn.commit()
    conn.close()

def add_points(tid, pts):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("UPDATE users SET points=points+? WHERE telegram_id=?", (pts, tid))
    conn.commit()
    conn.close()

def wallet_taken(wallet, tid):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users WHERE wallet=? AND telegram_id!=?", (wallet, tid))
    r = c.fetchone()
    conn.close()
    return r is not None

def tweet_used(url):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT id FROM tweet_comments WHERE tweet_url=?", (url,))
    r = c.fetchone()
    conn.close()
    return r is not None

def save_tweet(tid, url):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO tweet_comments (telegram_id,tweet_url,created_at) VALUES (?,?,?)",
                  (tid, url, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def get_leaderboard():
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 5")
    r = c.fetchall()
    conn.close()
    return r

def get_rank(tid):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*)+1 FROM users WHERE points > (SELECT points FROM users WHERE telegram_id=?)", (tid,))
    r = c.fetchone()[0]
    conn.close()
    return r

def get_stats():
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE claimed=1")
    claimed = c.fetchone()[0]
    conn.close()
    return total, claimed

def can_daily(user):
    if not user[15]:
        return True
    last = datetime.fromisoformat(user[15])
    return datetime.now() - last >= timedelta(hours=24)

def gen_ref(tid):
    return "NOTRUG" + str(tid)

# ==================== CHECK 100 POINTS ====================
async def check_hundred(context, tid):
    user = get_user(tid)
    if not user:
        return
    # 100 puana ulasti ve henuz claim etmemis
    if user[10] >= REQUIRED_POINTS and not user[11]:
        if not user[2]:
            # Wallet yok - iste
            set_field(tid, "step", "auto_wallet")
            await context.bot.send_message(
                chat_id=tid,
                text=(
                    "Tebrikler! 100 puana ulastın! 🎉\n\n"
                    "10,000 NOTRUG kazanmaya hak kazandın!\n\n"
                    "Lutfen Solana (Phantom) cuzdan adresini gonder:\n\n"
                    "Send your Phantom wallet address:"
                )
            )
        else:
            # Wallet var - direkt claim et
            set_field(tid, "claimed", 1)
            rank = get_rank(tid)
            await context.bot.send_message(
                chat_id=tid,
                text=(
                    "Tebrikler! 100 puana ulastın! 🎉\n\n"
                    "Airdrop islemi tamamlandi!\n"
                    "Wallet: " + str(user[2])[:20] + "...\n"
                    "Amount: 10,000 NOTRUG\n\n"
                    "Hesabiniza 1-2 saat icinde tanimlanacak!\n\n"
                    "Rank: #" + str(rank) + "\n"
                    "Top 5 icin puan kazanmaya devam et! 🏆"
                )
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "NEW AIRDROP CLAIM!\n\n"
                    "User: @" + str(user[1]) + "\n"
                    "ID: " + str(tid) + "\n"
                    "Wallet: " + str(user[2]) + "\n"
                    "Points: " + str(user[10]) + "\n"
                    "Rank: #" + str(rank) + "\n\n"
                    "Send 10,000 NOTRUG manually!"
                )
            )

# ==================== KEYBOARDS ====================
def main_keyboard(user):
    buttons = []
    if not user[3]:
        buttons.append([InlineKeyboardButton("🐦 Follow @NOTRUGfun on X (+25pts)", callback_data="t_follow")])
    if not user[5]:
        buttons.append([InlineKeyboardButton("❤️ Like Pinned Tweet (+25pts)", callback_data="t_like")])
    if not user[4]:
        buttons.append([InlineKeyboardButton("✈️ Join Telegram Group (+20pts)", callback_data="t_telegram")])
    if not user[6]:
        buttons.append([InlineKeyboardButton("🔁 Retweet Pinned Tweet (+15pts)", callback_data="t_retweet")])
    if not user[7]:
        buttons.append([InlineKeyboardButton("💬 Comment Pinned Tweet (+15pts)", callback_data="t_comment")])
    if not user[8]:
        buttons.append([InlineKeyboardButton("🔗 Add $NOTRUG to X Bio (+10pts)", callback_data="t_bio")])
    if not user[9]:
        buttons.append([InlineKeyboardButton("📢 Share Bot Link (+10pts)", callback_data="t_share")])
    buttons.append([InlineKeyboardButton("🗨️ Comment on New Tweet (+10pts each)", callback_data="t_new_comment")])
    daily_label = "💬 Daily Group Msg (+10pts)" + (" ✅" if not can_daily(user) else "")
    buttons.append([InlineKeyboardButton(daily_label, callback_data="t_daily_info")])
    buttons.append([InlineKeyboardButton("👥 My Referral Link (+10pts/invite)", callback_data="t_ref")])
    buttons.append([
        InlineKeyboardButton("📊 My Points", callback_data="my_points"),
        InlineKeyboardButton("🏆 Top 5", callback_data="leaderboard")
    ])
    return InlineKeyboardMarkup(buttons)

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Tasks", callback_data="back")]])

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    referred_by = None
    if context.args:
        conn = sqlite3.connect("airdrop.db")
        c = conn.cursor()
        c.execute("SELECT telegram_id FROM users WHERE ref_code=?", (context.args[0],))
        row = c.fetchone()
        conn.close()
        if row and row[0] != tid:
            referred_by = row[0]

    existing = get_user(tid)
    if not existing:
        create_user(tid, username, gen_ref(tid), referred_by)
        if referred_by:
            add_points(referred_by, POINTS["referral"])
            try:
                await context.bot.send_message(
                    chat_id=referred_by,
                    text="Someone joined with your referral! +10 points!"
                )
            except:
                pass

    user = get_user(tid)
    rank = get_rank(tid)
    msg = (
        "🛡 $NOTRUG Airdrop Bot\n\n"
        "The most honest project in crypto.\n"
        "We will rug you. Just... not yet. 🏖\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Complete tasks → Earn 10,000 NOTRUG!\n"
        "Top 5 → +10,000 NOTRUG BONUS at launch! 🏆\n\n"
        "📊 Your points: " + str(user[10]) + " / 100\n"
        "🏅 Your rank: #" + str(rank) + "\n\n"
        "Select a task:"
    )
    await update.message.reply_text(msg, reply_markup=main_keyboard(user))

# ==================== BUTTON HANDLER ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    user = get_user(tid)
    if not user:
        create_user(tid, username, gen_ref(tid))
        user = get_user(tid)

    if query.data == "t_follow":
        set_field(tid, "step", "twitter_username")
        await query.edit_message_text(
            "🐦 Follow @NOTRUGfun on X\n\n"
            "1. Go to: " + TWITTER_URL + "\n"
            "2. Follow the account\n"
            "3. Send your Twitter username here\n\n"
            "Type your username (without @):"
        )

    elif query.data == "t_like":
        set_field(tid, "step", "tweet_like")
        await query.edit_message_text(
            "❤️ Like our Pinned Tweet\n\n"
            "1. Go to: " + PINNED_TWEET + "\n"
            "2. Like the tweet\n"
            "3. Send the tweet link here\n\n"
            "Send the tweet link:"
        )

    elif query.data == "t_retweet":
        set_field(tid, "step", "tweet_retweet")
        await query.edit_message_text(
            "🔁 Retweet our Pinned Tweet\n\n"
            "1. Go to: " + PINNED_TWEET + "\n"
            "2. Retweet it\n"
            "3. Send the tweet link here\n\n"
            "Send the tweet link:"
        )

    elif query.data == "t_comment":
        set_field(tid, "step", "tweet_comment")
        await query.edit_message_text(
            "💬 Comment on Pinned Tweet\n\n"
            "1. Go to: " + PINNED_TWEET + "\n"
            "2. Leave a comment\n"
            "3. Send the tweet link here\n\n"
            "Send the tweet link:"
        )

    elif query.data == "t_new_comment":
        set_field(tid, "step", "new_comment")
        await query.edit_message_text(
            "🗨️ Comment on any $NOTRUG tweet\n\n"
            "1. Go to @NOTRUGfun on X\n"
            "2. Comment on any tweet\n"
            "3. Send the tweet link here\n\n"
            "Each unique tweet = +10pts (unlimited)\n\n"
            "Send the tweet link:"
        )

    elif query.data == "t_bio":
        set_field(tid, "step", "twitter_bio")
        await query.edit_message_text(
            "🔗 Add $NOTRUG to your X Bio\n\n"
            "1. Edit your X profile bio\n"
            "2. Add '$NOTRUG' or 'notrug.fun'\n"
            "3. Send your X profile link here\n\n"
            "Send your profile link:"
        )

    elif query.data == "t_share":
        set_field(tid, "step", "share_link")
        await query.edit_message_text(
            "📢 Share our bot link\n\n"
            "Share this anywhere:\n"
            "t.me/NOTRUGairdrop_bot\n\n"
            "Then send a screenshot or link here:"
        )

    elif query.data == "t_telegram":
        try:
            member = await context.bot.get_chat_member(GROUP_ID, tid)
            if member.status in ["member", "administrator", "creator"]:
                if not user[4]:
                    set_field(tid, "telegram_done", 1)
                    add_points(tid, POINTS["telegram_join"])
                    user = get_user(tid)
                    await query.edit_message_text(
                        "Telegram join verified! +20 points\n\n"
                        "Your points: " + str(user[10]) + " / 100\n\n"
                        "Complete more tasks:",
                        reply_markup=main_keyboard(user)
                    )
                    await check_hundred(context, tid)
                else:
                    await query.answer("Already done!", show_alert=True)
            else:
                await query.edit_message_text(
                    "Join our group first!\n\nt.me/notrugfun\n\nThen tap again.",
                    reply_markup=back_kb()
                )
        except:
            await query.edit_message_text(
                "Join our group first!\n\nt.me/notrugfun\n\nThen tap again.",
                reply_markup=back_kb()
            )

    elif query.data == "t_daily_info":
        if can_daily(user):
            await query.answer("Write a message in @notrugfun group to earn +10pts daily!", show_alert=True)
        else:
            last = datetime.fromisoformat(user[15])
            next_time = last + timedelta(hours=24)
            remaining = next_time - datetime.now()
            h = int(remaining.total_seconds() // 3600)
            m = int((remaining.total_seconds() % 3600) // 60)
            await query.answer("Already done today! Next in " + str(h) + "h " + str(m) + "m", show_alert=True)

    elif query.data == "t_ref":
        ref_link = "https://t.me/NOTRUGairdrop_bot?start=" + gen_ref(tid)
        await query.edit_message_text(
            "👥 Your Referral Link\n\n"
            + ref_link + "\n\n"
            "Share everywhere!\n"
            "Each person who joins = +10pts for you\n"
            "No limit — more invites = more points!\n\n"
            "Climb to Top 5 for +10,000 NOTRUG bonus! 🏆",
            reply_markup=back_kb()
        )

    elif query.data == "my_points":
        user = get_user(tid)
        rank = get_rank(tid)
        wallet = user[2] or "Not set yet"
        tasks = (
            "Twitter follow: " + ("Done +25pts" if user[3] else "Pending") + "\n"
            "Tweet like: " + ("Done +25pts" if user[5] else "Pending") + "\n"
            "Telegram join: " + ("Done +20pts" if user[4] else "Pending") + "\n"
            "Tweet retweet: " + ("Done +15pts" if user[6] else "Pending") + "\n"
            "Tweet comment: " + ("Done +15pts" if user[7] else "Pending") + "\n"
            "Twitter bio: " + ("Done +10pts" if user[8] else "Pending") + "\n"
            "Share link: " + ("Done +10pts" if user[9] else "Pending") + "\n"
            "Daily messages: " + str(user[16]) + " days x10pts\n"
        )
        extra = ""
        if user[10] >= REQUIRED_POINTS and not user[11]:
            extra = "\nYou qualify! Type /claim or add wallet to receive NOTRUG!"
        await query.edit_message_text(
            "📊 YOUR STATS\n\n"
            "Points: " + str(user[10]) + " / 100\n"
            "Rank: #" + str(rank) + "\n"
            "Wallet: " + wallet + "\n"
            "Claimed: " + ("Yes" if user[11] else "No") + "\n\n"
            "Task Status:\n" + tasks + extra,
            reply_markup=back_kb()
        )

    elif query.data == "leaderboard":
        lb = get_leaderboard()
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        text = "🏆 LEADERBOARD — TOP 5\n\n"
        for i, (uname, pts) in enumerate(lb):
            text += medals[i] + " @" + str(uname) + " — " + str(pts) + " pts\n"
        user = get_user(tid)
        rank = get_rank(tid)
        text += "\nYour rank: #" + str(rank) + " (" + str(user[10]) + " pts)\n\nTop 5 get +10,000 NOTRUG bonus at launch!"
        await query.edit_message_text(text, reply_markup=back_kb())

    elif query.data == "back":
        user = get_user(tid)
        rank = get_rank(tid)
        await query.edit_message_text(
            "📊 Points: " + str(user[10]) + " / 100  |  Rank: #" + str(rank) + "\n\nSelect a task:",
            reply_markup=main_keyboard(user)
        )

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    tid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    text = update.message.text.strip()
    chat_type = update.message.chat.type

    # GROUP → Daily points
    if chat_type in ["group", "supergroup"]:
        if update.message.chat.username == GROUP_USERNAME:
            user = get_user(tid)
            if not user:
                return
            if can_daily(user):
                set_field(tid, "last_daily", datetime.now().isoformat())
                set_field(tid, "daily_count", (user[16] or 0) + 1)
                add_points(tid, POINTS["daily_message"])
                user = get_user(tid)
                try:
                    await context.bot.send_message(
                        chat_id=tid,
                        text=(
                            "Daily message bonus! +10 points\n\n"
                            "Your points: " + str(user[10]) + "\n"
                            "Rank: #" + str(get_rank(tid)) + "\n\n"
                            "Come back tomorrow for more!"
                        )
                    )
                    await check_hundred(context, tid)
                except:
                    pass
        return

    # DM
    user = get_user(tid)
    if not user:
        create_user(tid, username, gen_ref(tid))
        user = get_user(tid)

    step = user[12]

    # AUTO WALLET - 100 puan sonrası
    if step == "auto_wallet":
        wallet = text
        if len(wallet) < 32 or len(wallet) > 44:
            await update.message.reply_text(
                "Invalid Solana address! Please check.\n\nSend your Phantom wallet address:"
            )
            return
        if wallet_taken(wallet, tid):
            await update.message.reply_text(
                "This wallet is already registered!\n\nSend a different wallet address:"
            )
            return
        set_field(tid, "wallet", wallet)
        set_field(tid, "claimed", 1)
        set_field(tid, "step", "idle")
        user = get_user(tid)
        rank = get_rank(tid)
        await update.message.reply_text(
            "Airdrop islemi tamamlandi! 🎉\n\n"
            "Wallet: " + wallet[:20] + "...\n"
            "Amount: 10,000 NOTRUG\n\n"
            "Hesabiniza 1-2 saat icinde tanimlanacak!\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Rank: #" + str(rank) + "\n"
            "Top 5 icin puan kazanmaya devam et!\n"
            "Top 5 = +10,000 NOTRUG BONUS launch gunu! 🏆\n\n"
            "Gunluk mesaj at, arkadas davet et, tweet yorumla!"
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "NEW AIRDROP CLAIM!\n\n"
                "User: @" + str(user[1]) + "\n"
                "ID: " + str(tid) + "\n"
                "Wallet: " + str(wallet) + "\n"
                "Points: " + str(user[10]) + "\n"
                "Rank: #" + str(rank) + "\n\n"
                "Send 10,000 NOTRUG manually!"
            )
        )
        return

    # TWITTER FOLLOW
    if step == "twitter_username":
        set_field(tid, "twitter_done", 1)
        set_field(tid, "step", "idle")
        add_points(tid, POINTS["twitter_follow"])
        user = get_user(tid)
        await update.message.reply_text(
            "Twitter follow verified! +25 points\n\n"
            "Your points: " + str(user[10]) + " / 100\n\n"
            "Complete more tasks:",
            reply_markup=main_keyboard(user)
        )
        await check_hundred(context, tid)
        return

    # TWEET LIKE
    if step == "tweet_like":
        if "x.com" in text or "twitter.com" in text:
            set_field(tid, "tweet_like_done", 1)
            set_field(tid, "step", "idle")
            add_points(tid, POINTS["tweet_like"])
            user = get_user(tid)
            await update.message.reply_text(
                "Tweet like verified! +25 points\n\n"
                "Your points: " + str(user[10]) + " / 100\n\n"
                "Complete more tasks:",
                reply_markup=main_keyboard(user)
            )
            await check_hundred(context, tid)
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    # TWEET RETWEET
    if step == "tweet_retweet":
        if "x.com" in text or "twitter.com" in text:
            set_field(tid, "tweet_rt_done", 1)
            set_field(tid, "step", "idle")
            add_points(tid, POINTS["tweet_retweet"])
            user = get_user(tid)
            await update.message.reply_text(
                "Retweet verified! +15 points\n\n"
                "Your points: " + str(user[10]) + " / 100\n\n"
                "Complete more tasks:",
                reply_markup=main_keyboard(user)
            )
            await check_hundred(context, tid)
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    # TWEET COMMENT (pinned)
    if step == "tweet_comment":
        if "x.com" in text or "twitter.com" in text:
            set_field(tid, "tweet_cmt_done", 1)
            set_field(tid, "step", "idle")
            add_points(tid, POINTS["tweet_comment"])
            user = get_user(tid)
            await update.message.reply_text(
                "Tweet comment verified! +15 points\n\n"
                "Your points: " + str(user[10]) + " / 100\n\n"
                "Complete more tasks:",
                reply_markup=main_keyboard(user)
            )
            await check_hundred(context, tid)
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    # NEW TWEET COMMENT
    if step == "new_comment":
        if "x.com" in text or "twitter.com" in text:
            if tweet_used(text):
                set_field(tid, "step", "idle")
                await update.message.reply_text(
                    "This link was already submitted!\n\nComment on a different tweet for +10pts.",
                    reply_markup=main_keyboard(user)
                )
            else:
                save_tweet(tid, text)
                set_field(tid, "step", "idle")
                add_points(tid, POINTS["new_tweet_comment"])
                user = get_user(tid)
                await update.message.reply_text(
                    "Tweet comment verified! +10 points\n\n"
                    "Your points: " + str(user[10]) + "\n\n"
                    "Comment on more tweets for more points!",
                    reply_markup=main_keyboard(user)
                )
                await check_hundred(context, tid)
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    # TWITTER BIO
    if step == "twitter_bio":
        set_field(tid, "twitter_bio_done", 1)
        set_field(tid, "step", "idle")
        add_points(tid, POINTS["twitter_bio"])
        user = get_user(tid)
        await update.message.reply_text(
            "Twitter bio verified! +10 points\n\n"
            "Your points: " + str(user[10]) + " / 100\n\n"
            "Complete more tasks:",
            reply_markup=main_keyboard(user)
        )
        await check_hundred(context, tid)
        return

    # SHARE LINK
    if step == "share_link":
        set_field(tid, "share_link_done", 1)
        set_field(tid, "step", "idle")
        add_points(tid, POINTS["share_link"])
        user = get_user(tid)
        await update.message.reply_text(
            "Share verified! +10 points\n\n"
            "Your points: " + str(user[10]) + " / 100\n\n"
            "Complete more tasks:",
            reply_markup=main_keyboard(user)
        )
        await check_hundred(context, tid)
        return

    # DEFAULT
    await start(update, context)

# ==================== COMMANDS ====================
async def wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    user = get_user(tid)
    if not user:
        await update.message.reply_text("Please /start first!")
        return
    if not context.args:
        await update.message.reply_text(
            "Your wallet: " + (user[2] or "Not set") + "\n\nTo set: /wallet YOUR_SOLANA_ADDRESS"
        )
        return
    wallet = context.args[0]
    if len(wallet) < 32 or len(wallet) > 44:
        await update.message.reply_text("Invalid Solana address!")
        return
    if wallet_taken(wallet, tid):
        await update.message.reply_text("This wallet is already registered!")
        return
    set_field(tid, "wallet", wallet)
    await update.message.reply_text("Wallet saved! " + wallet[:20] + "...")

async def claim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    user = get_user(tid)
    if not user:
        await update.message.reply_text("Please /start first!")
        return
    if user[10] < REQUIRED_POINTS:
        await update.message.reply_text(
            "You need 100 points!\nYour points: " + str(user[10]) + " / 100"
        )
        return
    if user[11]:
        await update.message.reply_text(
            "Already claimed! Keep earning for Top 5 bonus!"
        )
        return
    if not user[2]:
        await update.message.reply_text("Add your wallet first!\n/wallet YOUR_SOLANA_ADDRESS")
        return
    set_field(tid, "claimed", 1)
    rank = get_rank(tid)
    await update.message.reply_text(
        "Claim submitted!\n\n"
        "Wallet: " + user[2] + "\n"
        "Amount: 10,000 NOTRUG\n\n"
        "We will send within 24 hours!\n\n"
        "Keep earning for Top 5 bonus!\n"
        "Your rank: #" + str(rank)
    )
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "NEW AIRDROP CLAIM!\n\n"
            "User: @" + str(user[1]) + "\n"
            "ID: " + str(tid) + "\n"
            "Wallet: " + str(user[2]) + "\n"
            "Points: " + str(user[10]) + "\n"
            "Rank: #" + str(rank) + "\n\n"
            "Send 10,000 NOTRUG manually!"
        )
    )

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lb = get_leaderboard()
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    text = "🏆 LEADERBOARD — TOP 5\n\n"
    for i, (uname, pts) in enumerate(lb):
        text += medals[i] + " @" + str(uname) + " — " + str(pts) + " pts\n"
    tid = update.effective_user.id
    user = get_user(tid)
    if user:
        text += "\nYour rank: #" + str(get_rank(tid)) + " (" + str(user[10]) + " pts)"
    text += "\n\nTop 5 get +10,000 NOTRUG bonus at launch!"
    await update.message.reply_text(text)

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    total, claimed = get_stats()
    await update.message.reply_text(
        "AIRDROP STATS\n\nTotal: " + str(total) + "\nClaimed: " + str(claimed) + "\nPending: " + str(total - claimed)
    )

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT username, wallet, points FROM users WHERE claimed=1 ORDER BY points DESC")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("No claims yet!")
        return
    text = "CLAIMED WALLETS\n\n"
    for r in rows:
        text += "@" + str(r[0]) + " | " + str(r[1])[:20] + "... | " + str(r[2]) + "pts\n"
    await update.message.reply_text(text)

# ==================== MAIN ====================
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wallet", wallet_cmd))
    app.add_handler(CommandHandler("claim", claim_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        handle_message
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_message
    ))
    print("NOTRUG Airdrop Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
