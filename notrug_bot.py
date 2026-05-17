import sqlite3
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ==================== SETTINGS ====================
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

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        telegram_id     INTEGER PRIMARY KEY,
        username        TEXT,
        wallet          TEXT,
        twitter_done    INTEGER DEFAULT 0,
        telegram_done   INTEGER DEFAULT 0,
        tweet_like_done INTEGER DEFAULT 0,
        tweet_rt_done   INTEGER DEFAULT 0,
        tweet_cmt_done  INTEGER DEFAULT 0,
        twitter_bio_done INTEGER DEFAULT 0,
        share_link_done INTEGER DEFAULT 0,
        points          INTEGER DEFAULT 0,
        claimed         INTEGER DEFAULT 0,
        step            TEXT DEFAULT 'idle',
        ref_code        TEXT UNIQUE,
        referred_by     INTEGER,
        last_daily      TEXT,
        daily_count     INTEGER DEFAULT 0,
        created_at      TEXT
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
        c.execute("""INSERT INTO users 
            (telegram_id, username, ref_code, referred_by, created_at)
            VALUES (?,?,?,?,?)""",
            (tid, username, ref_code, referred_by, datetime.now().isoformat()))
        conn.commit()
    except:
        pass
    conn.close()

def update_field(tid, field, value):
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

def tweet_comment_exists(url):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT id FROM tweet_comments WHERE tweet_url=?", (url,))
    r = c.fetchone()
    conn.close()
    return r is not None

def save_tweet_comment(tid, url):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO tweet_comments (telegram_id, tweet_url, created_at) VALUES (?,?,?)",
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

def get_user_rank(tid):
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

def get_claimed_list():
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT username, wallet, points FROM users WHERE claimed=1 ORDER BY points DESC")
    r = c.fetchall()
    conn.close()
    return r

def gen_ref(tid):
    return "NOTRUG" + str(tid)

def can_daily(user):
    if not user[15]:
        return True
    last = datetime.fromisoformat(user[15])
    return datetime.now() - last >= timedelta(hours=24)

# ==================== KEYBOARDS ====================
def main_keyboard(user):
    pts = user[10]
    buttons = []

    # X Tasks
    if not user[3]:
        buttons.append([InlineKeyboardButton("🐦 Follow @NOTRUGfun on X  (+25pts)", callback_data="t_follow")])
    if not user[5]:
        buttons.append([InlineKeyboardButton("❤️ Like Pinned Tweet  (+25pts)", callback_data="t_like")])
    if not user[6]:
        buttons.append([InlineKeyboardButton("🔁 Retweet Pinned Tweet  (+15pts)", callback_data="t_retweet")])
    if not user[7]:
        buttons.append([InlineKeyboardButton("💬 Comment Pinned Tweet  (+15pts)", callback_data="t_comment")])
    if not user[8]:
        buttons.append([InlineKeyboardButton("🔗 Add $NOTRUG to X Bio  (+10pts)", callback_data="t_bio")])
    buttons.append([InlineKeyboardButton("🗨️ Comment on New Tweet  (+10pts each)", callback_data="t_new_comment")])

    # Telegram Tasks
    if not user[4]:
        buttons.append([InlineKeyboardButton("✈️ Join Telegram Group  (+20pts)", callback_data="t_telegram")])
    if not user[9]:
        buttons.append([InlineKeyboardButton("📢 Share Bot Link  (+10pts)", callback_data="t_share")])

    # Daily & Ref
    daily_txt = "💬 Daily Group Message  (+10pts)" + (" ✅ Done today" if not can_daily(user) else "")
    buttons.append([InlineKeyboardButton(daily_txt, callback_data="t_daily_info")])
    buttons.append([InlineKeyboardButton("👥 My Referral Link  (+10pts/invite)", callback_data="t_ref")])

    # Stats
    buttons.append([
        InlineKeyboardButton("📊 My Points", callback_data="my_points"),
        InlineKeyboardButton("🏆 Top 5", callback_data="leaderboard")
    ])
    return InlineKeyboardMarkup(buttons)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Tasks", callback_data="back")]])

# ==================== HANDLERS ====================
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
                    text="Someone joined with your referral! +10 points earned!"
                )
            except:
                pass

    user = get_user(tid)
    rank = get_user_rank(tid)

    msg = (
        "🛡 $NOTRUG Airdrop Bot\n\n"
        "The most honest project in crypto.\n"
        "We will rug you. Just... not yet. 🏖\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 Complete tasks → Earn points → Get NOTRUG!\n\n"
        "🏆 Max: 10,000 NOTRUG per user\n"
        "🥇 Top 5 → +10,000 NOTRUG BONUS at launch!\n\n"
        "📊 Your points: " + str(user[10]) + " / 100\n"
        "🏅 Your rank: #" + str(rank) + "\n\n"
        "Select a task below:"
    )
    await update.message.reply_text(msg, reply_markup=main_keyboard(user))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    user = get_user(tid)
    if not user:
        create_user(tid, username, gen_ref(tid))
        user = get_user(tid)

    # ---- TWITTER FOLLOW ----
    if query.data == "t_follow":
        update_field(tid, "step", "twitter_username")
        await query.edit_message_text(
            "🐦 Follow @NOTRUGfun on X\n\n"
            "1. Go to: " + TWITTER_URL + "\n"
            "2. Follow the account\n"
            "3. Send your Twitter username here\n\n"
            "Type your username (without @):"
        )

    # ---- TWEET LIKE ----
    elif query.data == "t_like":
        update_field(tid, "step", "tweet_like")
        await query.edit_message_text(
            "❤️ Like our Pinned Tweet\n\n"
            "1. Go to: " + PINNED_TWEET + "\n"
            "2. Like the tweet\n"
            "3. Send the tweet link here\n\n"
            "Send the tweet link:"
        )

    # ---- TWEET RETWEET ----
    elif query.data == "t_retweet":
        update_field(tid, "step", "tweet_retweet")
        await query.edit_message_text(
            "🔁 Retweet our Pinned Tweet\n\n"
            "1. Go to: " + PINNED_TWEET + "\n"
            "2. Retweet it\n"
            "3. Send the tweet link here\n\n"
            "Send the tweet link:"
        )

    # ---- TWEET COMMENT ----
    elif query.data == "t_comment":
        update_field(tid, "step", "tweet_comment")
        await query.edit_message_text(
            "💬 Comment on Pinned Tweet\n\n"
            "1. Go to: " + PINNED_TWEET + "\n"
            "2. Leave a comment\n"
            "3. Send the tweet link here\n\n"
            "Send the tweet link:"
        )

    # ---- NEW TWEET COMMENT ----
    elif query.data == "t_new_comment":
        update_field(tid, "step", "new_comment")
        await query.edit_message_text(
            "🗨️ Comment on any $NOTRUG tweet\n\n"
            "1. Go to @NOTRUGfun on X\n"
            "2. Comment on any tweet\n"
            "3. Send the tweet link here\n\n"
            "Each unique tweet link = +10pts\n"
            "Same link cannot be used twice!\n\n"
            "Send the tweet link:"
        )

    # ---- TWITTER BIO ----
    elif query.data == "t_bio":
        update_field(tid, "step", "twitter_bio")
        await query.edit_message_text(
            "🔗 Add $NOTRUG to your X Bio\n\n"
            "1. Go to your X profile\n"
            "2. Edit bio → Add '$NOTRUG' or 'notrug.fun'\n"
            "3. Send your X profile link here\n\n"
            "Send your profile link:"
        )

    # ---- TELEGRAM JOIN ----
    elif query.data == "t_telegram":
        try:
            member = await context.bot.get_chat_member(GROUP_ID, tid)
            if member.status in ["member", "administrator", "creator"]:
                if not user[4]:
                    update_field(tid, "telegram_done", 1)
                    add_points(tid, POINTS["telegram_join"])
                    user = get_user(tid)
                    await query.edit_message_text(
                        "Telegram join verified! +20 points\n\n"
                        "Your points: " + str(user[10]) + " / 100\n\n"
                        "Complete more tasks:",
                        reply_markup=main_keyboard(user)
                    )
                    await check_hundred(query, context, user)
                else:
                    await query.answer("Already done!", show_alert=True)
            else:
                await query.edit_message_text(
                    "Join our group first!\n\nt.me/notrugfun\n\nThen tap again.",
                    reply_markup=back_keyboard()
                )
        except:
            await query.edit_message_text(
                "Join our group first!\n\nt.me/notrugfun\n\nThen tap again.",
                reply_markup=back_keyboard()
            )

    # ---- SHARE LINK ----
    elif query.data == "t_share":
        update_field(tid, "step", "share_link")
        await query.edit_message_text(
            "📢 Share our bot link\n\n"
            "Share this link on any platform:\n"
            "t.me/NOTRUGairdrop_bot\n\n"
            "Then send a screenshot or the platform link here:"
        )

    # ---- DAILY INFO ----
    elif query.data == "t_daily_info":
        if can_daily(user):
            await query.answer(
                "Write a message in @notrugfun group to earn +10pts daily!",
                show_alert=True
            )
        else:
            last = datetime.fromisoformat(user[15])
            next_time = last + timedelta(hours=24)
            remaining = next_time - datetime.now()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await query.answer(
                "Already done today!\nNext reward in " + str(hours) + "h " + str(minutes) + "m",
                show_alert=True
            )

    # ---- REFERRAL ----
    elif query.data == "t_ref":
        ref_link = "https://t.me/NOTRUGairdrop_bot?start=" + gen_ref(tid)
        await query.edit_message_text(
            "👥 Your Referral Link\n\n"
            + ref_link + "\n\n"
            "Share this link everywhere!\n"
            "Each person who joins = +10 points for you\n"
            "No limit — more invites = more points!\n\n"
            "Keep climbing the leaderboard for\n"
            "+10,000 NOTRUG bonus at launch! 🏆",
            reply_markup=back_keyboard()
        )

    # ---- MY POINTS ----
    elif query.data == "my_points":
        user = get_user(tid)
        rank = get_user_rank(tid)
        wallet = user[2] or "Not set (/wallet YOUR_ADDRESS)"
        tasks = (
            ("Twitter follow: " + ("Done +25pts" if user[3] else "Pending")) + "\n"
            + ("Tweet like: " + ("Done +25pts" if user[5] else "Pending")) + "\n"
            + ("Tweet retweet: " + ("Done +15pts" if user[6] else "Pending")) + "\n"
            + ("Tweet comment: " + ("Done +15pts" if user[7] else "Pending")) + "\n"
            + ("Twitter bio: " + ("Done +10pts" if user[8] else "Pending")) + "\n"
            + ("Telegram join: " + ("Done +20pts" if user[4] else "Pending")) + "\n"
            + ("Share link: " + ("Done +10pts" if user[9] else "Pending")) + "\n"
            + ("Daily messages: " + str(user[16]) + " days (+10pts each)\n")
        )
        qualify = ""
        if user[10] >= REQUIRED_POINTS and not user[11]:
            if user[2]:
                qualify = "\nYou qualify for 10,000 NOTRUG!\nType /claim to receive it!"
            else:
                qualify = "\nYou qualify! Add wallet: /wallet YOUR_ADDRESS"

        msg = (
            "📊 YOUR STATS\n\n"
            "Points: " + str(user[10]) + " / 100\n"
            "Rank: #" + str(rank) + "\n"
            "Wallet: " + wallet + "\n"
            "Claimed: " + ("Yes" if user[11] else "No") + "\n\n"
            "Task Status:\n" + tasks
            + qualify
        )
        await query.edit_message_text(msg, reply_markup=back_keyboard())

    # ---- LEADERBOARD ----
    elif query.data == "leaderboard":
        lb = get_leaderboard()
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        text = "🏆 LEADERBOARD — TOP 5\n\n"
        for i, (uname, pts) in enumerate(lb):
            m = medals[i] if i < len(medals) else str(i+1) + "."
            text += m + " @" + str(uname) + " — " + str(pts) + " pts\n"
        rank = get_user_rank(tid)
        user = get_user(tid)
        text += (
            "\nYour rank: #" + str(rank) + " (" + str(user[10]) + " pts)\n\n"
            "Top 5 get +10,000 NOTRUG bonus at launch!\n"
            "Keep earning: daily messages + referrals!"
        )
        await query.edit_message_text(text, reply_markup=back_keyboard())

    # ---- BACK ----
    elif query.data == "back":
        user = get_user(tid)
        rank = get_user_rank(tid)
        await query.edit_message_text(
            "📊 Your points: " + str(user[10]) + " / 100\n"
            "🏅 Rank: #" + str(rank) + "\n\n"
            "Select a task:",
            reply_markup=main_keyboard(user)
        )

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    msg_chat = update.message.chat
    tid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    text = update.message.text.strip()

    # GROUP MESSAGE → Daily points
    if msg_chat.type in ["group", "supergroup"]:
        if msg_chat.username == GROUP_USERNAME:
            user = get_user(tid)
            if not user:
                return
            if can_daily(user):
                update_field(tid, "last_daily", datetime.now().isoformat())
                update_field(tid, "daily_count", (user[16] or 0) + 1)
                add_points(tid, POINTS["daily_message"])
                user = get_user(tid)
                try:
                    await context.bot.send_message(
                        chat_id=tid,
                        text=(
                            "Daily message bonus! +10 points\n\n"
                            "Your points: " + str(user[10]) + "\n"
                            "Rank: #" + str(get_user_rank(tid)) + "\n\n"
                            "Come back tomorrow for more!"
                        )
                    )
                except:
                    pass
        return

    # DM MESSAGES
    user = get_user(tid)
    if not user:
        create_user(tid, username, gen_ref(tid))
        user = get_user(tid)

    step = user[12]

    # TWITTER FOLLOW
    if step == "twitter_username":
        update_field(tid, "twitter_done", 1)
        update_field(tid, "step", "idle")
        add_points(tid, POINTS["twitter_follow"])
        user = get_user(tid)
        await update.message.reply_text(
            "Twitter follow verified! +25 points\n\n"
            "Your points: " + str(user[10]) + " / 100\n\n"
            "Complete more tasks:",
            reply_markup=main_keyboard(user)
        )
        await check_hundred(update, context, user)
        return

    # TWEET LIKE
    if step == "tweet_like":
        if "x.com" in text or "twitter.com" in text:
            update_field(tid, "tweet_like_done", 1)
            update_field(tid, "step", "idle")
            add_points(tid, POINTS["tweet_like"])
            user = get_user(tid)
            await update.message.reply_text(
                "Tweet like verified! +25 points\n\n"
                "Your points: " + str(user[10]) + " / 100\n\n"
                "Complete more tasks:",
                reply_markup=main_keyboard(user)
            )
            await check_hundred(update, context, user)
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    # TWEET RETWEET
    if step == "tweet_retweet":
        if "x.com" in text or "twitter.com" in text:
            update_field(tid, "tweet_rt_done", 1)
            update_field(tid, "step", "idle")
            add_points(tid, POINTS["tweet_retweet"])
            user = get_user(tid)
            await update.message.reply_text(
                "Retweet verified! +15 points\n\n"
                "Your points: " + str(user[10]) + " / 100\n\n"
                "Complete more tasks:",
                reply_markup=main_keyboard(user)
            )
            await check_hundred(update, context, user)
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    # TWEET COMMENT (pinned)
    if step == "tweet_comment":
        if "x.com" in text or "twitter.com" in text:
            update_field(tid, "tweet_cmt_done", 1)
            update_field(tid, "step", "idle")
            add_points(tid, POINTS["tweet_comment"])
            user = get_user(tid)
            await update.message.reply_text(
                "Tweet comment verified! +15 points\n\n"
                "Your points: " + str(user[10]) + " / 100\n\n"
                "Complete more tasks:",
                reply_markup=main_keyboard(user)
            )
            await check_hundred(update, context, user)
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    # NEW TWEET COMMENT
    if step == "new_comment":
        if "x.com" in text or "twitter.com" in text:
            if tweet_comment_exists(text):
                update_field(tid, "step", "idle")
                await update.message.reply_text(
                    "This tweet link was already submitted!\n\n"
                    "Comment on a DIFFERENT tweet for +10pts.",
                    reply_markup=main_keyboard(user)
                )
            else:
                save_tweet_comment(tid, text)
                update_field(tid, "step", "idle")
                add_points(tid, POINTS["new_tweet_comment"])
                user = get_user(tid)
                await update.message.reply_text(
                    "Tweet comment verified! +10 points\n\n"
                    "Your points: " + str(user[10]) + "\n\n"
                    "Comment on more tweets for more points!",
                    reply_markup=main_keyboard(user)
                )
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    # TWITTER BIO
    if step == "twitter_bio":
        if "x.com" in text or "twitter.com" in text or "notrug" in text.lower():
            update_field(tid, "twitter_bio_done", 1)
            update_field(tid, "step", "idle")
            add_points(tid, POINTS["twitter_bio"])
            user = get_user(tid)
            await update.message.reply_text(
                "Twitter bio verified! +10 points\n\n"
                "Your points: " + str(user[10]) + " / 100\n\n"
                "Complete more tasks:",
                reply_markup=main_keyboard(user)
            )
        else:
            await update.message.reply_text("Please send your X profile link or confirm you added $NOTRUG to your bio")
        return

    # SHARE LINK
    if step == "share_link":
        update_field(tid, "share_link_done", 1)
        update_field(tid, "step", "idle")
        add_points(tid, POINTS["share_link"])
        user = get_user(tid)
        await update.message.reply_text(
            "Share verified! +10 points\n\n"
            "Your points: " + str(user[10]) + " / 100\n\n"
            "Complete more tasks:",
            reply_markup=main_keyboard(user)
        )
        await check_hundred(update, context, user)
        return

    # AUTO WALLET after 100 points
    if step == "auto_wallet":
        wallet = text.strip()
        if len(wallet) < 32 or len(wallet) > 44:
            await update.message.reply_text(
                "Invalid Solana address! Please check and try again.\n\n"
                "Send your Phantom wallet address:"
            )
            return
        if wallet_taken(wallet, tid):
            await update.message.reply_text(
                "This wallet is already registered by another user!\n\n"
                "Please send a different wallet address:"
            )
            return
        update_field(tid, "wallet", wallet)
        update_field(tid, "claimed", 1)
        update_field(tid, "step", "idle")
        user = get_user(tid)
        rank = get_user_rank(tid)
        await update.message.reply_text(
            "Airdrop islemi tamamlandi! 🎉\n\n"
            "Wallet: " + wallet[:20] + "...\n"
            "Amount: 10,000 NOTRUG\n\n"
            "Hesabiniza 1-2 saat icinde tanimlanacak!\n\n"
            "Rank: #" + str(rank) + "\n"
            "Top 5 icin puan kazanmaya devam edebilirsin!\n"
            "Top 5 = +10,000 NOTRUG BONUS launch gunu! 🏆"
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
        current = user[2] or "Not set"
        await update.message.reply_text(
            "Your wallet: " + current + "\n\n"
            "To set/update: /wallet YOUR_SOLANA_ADDRESS"
        )
        return
    wallet = context.args[0]
    if len(wallet) < 32 or len(wallet) > 44:
        await update.message.reply_text("Invalid Solana address! Please check and try again.")
        return
    if wallet_taken(wallet, tid):
        await update.message.reply_text("This wallet is already registered by another user!")
        return
    update_field(tid, "wallet", wallet)
    user = get_user(tid)
    if user[10] >= REQUIRED_POINTS and not user[11]:
        update_field(tid, "claimed", 1)
        rank = get_user_rank(tid)
        await update.message.reply_text(
            "Wallet saved!\n\n" + wallet[:20] + "...\n\n"
            "Airdrop tamamlandi! 🎉\n\n"
            "10,000 NOTRUG hesabiniza 1-2 saat icinde tanimlanacak!\n\n"
            "Rank: #" + str(rank) + "\n"
            "Top 5 icin puan kazanmaya devam edebilirsin!\n"
            "Top 5 = +10,000 NOTRUG bonus launch'ta! 🏆"
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
    else:
        await update.message.reply_text(
            "Wallet saved!\n\n" + wallet[:20] + "...\n\n"
            "Type /claim when you reach 100 points!"
        )

async def claim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    user = get_user(tid)
    if not user:
        await update.message.reply_text("Please /start first!")
        return
    if user[10] < REQUIRED_POINTS:
        await update.message.reply_text(
            "You need 100 points to claim!\n"
            "Your points: " + str(user[10]) + " / 100\n\n"
            "Use /start to complete more tasks."
        )
        return
    if user[11]:
        await update.message.reply_text(
            "You already claimed your NOTRUG!\n\n"
            "Keep earning points for the Top 5 bonus!"
        )
        return
    if not user[2]:
        await update.message.reply_text(
            "Add your wallet first!\n\n"
            "/wallet YOUR_SOLANA_ADDRESS"
        )
        return

    update_field(tid, "claimed", 1)
    rank = get_user_rank(tid)

    await update.message.reply_text(
        "Claim submitted!\n\n"
        "Wallet: " + user[2] + "\n"
        "Amount: 10,000 NOTRUG\n\n"
        "We will send within 24 hours!\n\n"
        "Keep earning points for Top 5 bonus!\n"
        "Your rank: #" + str(rank) + "\n"
        "Top 5 get +10,000 NOTRUG at launch!"
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
    tid = update.effective_user.id
    user = get_user(tid)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    text = "🏆 LEADERBOARD — TOP 5\n\n"
    for i, (uname, pts) in enumerate(lb):
        m = medals[i] if i < len(medals) else str(i+1) + "."
        text += m + " @" + str(uname) + " — " + str(pts) + " pts\n"
    rank = get_user_rank(tid)
    pts = user[10] if user else 0
    text += (
        "\nYour rank: #" + str(rank) + " (" + str(pts) + " pts)\n\n"
        "Top 5 get +10,000 NOTRUG bonus at launch!\n"
        "Earn more: daily messages + referrals!"
    )
    await update.message.reply_text(text)

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    total, claimed = get_stats()
    await update.message.reply_text(
        "AIRDROP STATS\n\n"
        "Total users: " + str(total) + "\n"
        "Claimed: " + str(claimed) + "\n"
        "Pending: " + str(total - claimed)
    )

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    claimed = get_claimed_list()
    if not claimed:
        await update.message.reply_text("No claims yet!")
        return
    text = "CLAIMED WALLETS\n\n"
    for u in claimed:
        text += "@" + str(u[0]) + " | " + str(u[1])[:20] + "... | " + str(u[2]) + "pts\n"
    await update.message.reply_text(text)

# ==================== AUTO CLAIM CHECK ====================
async def check_hundred(update_obj, context, user):
    tid = user[0]
    if user[10] >= REQUIRED_POINTS and not user[11] and not user[2]:
        update_field(tid, "step", "auto_wallet")
        await context.bot.send_message(
            chat_id=tid,
            text=(
                "Congratulations! You reached 100 points! 🎉\n\n"
                "You qualify for 10,000 NOTRUG!\n\n"
                "Please send your Solana (Phantom) wallet address\n"
                "to complete your airdrop claim:\n\n"
                "Send your wallet address now:"
            )
        )

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
