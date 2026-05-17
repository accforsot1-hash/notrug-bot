import sqlite3
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8225017117:AAGt7h2nfzwvDNk0sBYZEc7Kk6BFIKaC44c"
ADMIN_ID = 6365046594
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
}

def init_db():
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        wallet TEXT UNIQUE,
        twitter_done INTEGER DEFAULT 0,
        telegram_done INTEGER DEFAULT 0,
        tweet_like_done INTEGER DEFAULT 0,
        tweet_retweet_done INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        claimed INTEGER DEFAULT 0,
        step TEXT DEFAULT 'start',
        ref_code TEXT UNIQUE,
        referred_by INTEGER,
        last_daily TEXT,
        daily_count INTEGER DEFAULT 0,
        created_at TEXT,
        tweet_comment_done INTEGER DEFAULT 0
    )""")
    try:
        c.execute("ALTER TABLE users ADD COLUMN tweet_comment_done INTEGER DEFAULT 0")
        conn.commit()
    except:
        pass
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
            (telegram_id,username,ref_code,referred_by,created_at) 
            VALUES (?,?,?,?,?)""",
            (tid, username, ref_code, referred_by, datetime.now().isoformat()))
        conn.commit()
    except:
        pass
    conn.close()

def update_user(tid, **kwargs):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    for k, v in kwargs.items():
        c.execute(f"UPDATE users SET {k}=? WHERE telegram_id=?", (v, tid))
    conn.commit()
    conn.close()

def add_points(tid, pts):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("UPDATE users SET points=points+? WHERE telegram_id=?", (pts, tid))
    conn.commit()
    conn.close()

def wallet_exists(wallet, tid):
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users WHERE wallet=? AND telegram_id!=?", (wallet, tid))
    r = c.fetchone()
    conn.close()
    return r is not None

def get_leaderboard():
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 5")
    r = c.fetchall()
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

def get_all_claimed():
    conn = sqlite3.connect("airdrop.db")
    c = conn.cursor()
    c.execute("SELECT username, wallet, points FROM users WHERE claimed=1")
    r = c.fetchall()
    conn.close()
    return r

def gen_ref(tid):
    return "NOTRUG" + str(tid)

def task_keyboard(user):
    buttons = []
    if not user[3]:
        buttons.append([InlineKeyboardButton("🐦 Follow @NOTRUGfun (+25pts)", callback_data="task_twitter")])
    if not user[5]:
        buttons.append([InlineKeyboardButton("❤️ Like Pinned Tweet (+25pts)", callback_data="task_tweet_like")])
    if not user[4]:
        buttons.append([InlineKeyboardButton("✈️ Join Telegram Group (+20pts)", callback_data="task_telegram")])
    if not user[6]:
        buttons.append([InlineKeyboardButton("🔁 Retweet Pinned Tweet (+15pts)", callback_data="task_retweet")])
    # Daily message is now automatic - bot detects group messages
    buttons.append([InlineKeyboardButton("👥 My Referral Link (+10pts/each)", callback_data="task_ref")])
    buttons.append([InlineKeyboardButton("📊 My Points", callback_data="check_points")])
    buttons.append([InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    referred_by = None
    if context.args:
        ref = context.args[0]
        conn = sqlite3.connect("airdrop.db")
        c = conn.cursor()
        c.execute("SELECT telegram_id FROM users WHERE ref_code=?", (ref,))
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
                    text="Someone joined with your referral link! +10 points earned!"
                )
            except:
                pass

    user = get_user(tid)

    msg = (
        "🛡 $NOTRUG Airdrop Bot\n\n"
        "The most honest project in crypto.\n"
        "We will rug you. Just... not yet. 🏖\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Complete tasks to earn 10,000 NOTRUG!\n"
        "Top 5 get +10,000 NOTRUG bonus at launch!\n\n"
        "📊 Your points: " + str(user[7]) + "/100\n\n"
        "Select a task:"
    )
    await update.message.reply_text(msg, reply_markup=task_keyboard(user))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    user = get_user(tid)
    if not user:
        create_user(tid, username, gen_ref(tid))
        user = get_user(tid)

    if query.data == "task_twitter":
        update_user(tid, step="twitter_username")
        await query.edit_message_text(
            "🐦 Follow @NOTRUGfun on X\n\n"
            "1. Go to: " + TWITTER_URL + "\n"
            "2. Follow the account\n"
            "3. Send your Twitter username here\n\n"
            "Type your username (without @):"
        )

    elif query.data == "task_tweet_like":
        update_user(tid, step="tweet_like_link")
        await query.edit_message_text(
            "❤️ Like our Pinned Tweet\n\n"
            "1. Go to: " + PINNED_TWEET + "\n"
            "2. Like the tweet\n"
            "3. Send the tweet link here\n\n"
            "Send the tweet link:"
        )

    elif query.data == "task_retweet":
        update_user(tid, step="retweet_link")
        await query.edit_message_text(
            "🔁 Retweet our Pinned Tweet\n\n"
            "1. Go to: " + PINNED_TWEET + "\n"
            "2. Retweet it\n"
            "3. Send the tweet link here\n\n"
            "Send the tweet link:"
        )

    elif query.data == "task_telegram":
        try:
            member = await context.bot.get_chat_member(GROUP_ID, tid)
            if member.status in ["member", "administrator", "creator"]:
                if not user[4]:
                    update_user(tid, telegram_done=1)
                    add_points(tid, POINTS["telegram_join"])
                    user = get_user(tid)
                    await query.edit_message_text(
                        "Telegram join verified! +20 points\n\n"
                        "Your points: " + str(user[7]) + "/100\n\n"
                        "Complete more tasks:",
                        reply_markup=task_keyboard(user)
                    )
                else:
                    await query.answer("Already done!", show_alert=True)
            else:
                await query.edit_message_text(
                    "Join our group first!\n\nt.me/notrugfun\n\nThen tap again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Back", callback_data="back_tasks")
                    ]])
                )
        except:
            await query.edit_message_text(
                "Join our group first!\n\nt.me/notrugfun\n\nThen tap again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Back", callback_data="back_tasks")
                ]])
            )

    elif query.data == "task_daily":
        today = str(date.today())
        if user[12] == today:
            await query.answer("Already done today! Come back tomorrow.", show_alert=True)
        else:
            update_user(tid, last_daily=today, daily_count=(user[13] or 0) + 1)
            add_points(tid, POINTS["daily_message"])
            user = get_user(tid)
            await query.edit_message_text(
                "Daily message bonus! +10 points\n\n"
                "Your points: " + str(user[7]) + "/100\n\n"
                "Come back tomorrow for more!\n\n"
                "Complete more tasks:",
                reply_markup=task_keyboard(user)
            )

    elif query.data == "task_comment":
        update_user(tid, step="pinned_comment_link")
        await query.edit_message_text(
            "💬 Comment on our Pinned Tweet\n\n"
            "1. Go to: " + PINNED_TWEET + "\n"
            "2. Leave a comment\n"
            "3. Send the tweet link here\n\n"
            "Send the tweet link:"
        )

    elif query.data == "task_new_comment":
        update_user(tid, step="new_comment_link")
        await query.edit_message_text(
            "🗨️ Comment on a New Tweet\n\n"
            "1. Go to @NOTRUGfun on X\n"
            "2. Comment on any tweet\n"
            "3. Send the tweet link here\n\n"
            "Note: Each new tweet link = +10pts\n"
            "Same link cannot be used twice!\n\n"
            "Send the tweet link:"
        )

    elif query.data == "task_ref":
        ref_link = "https://t.me/NOTRUGairdrop_bot?start=" + gen_ref(tid)
        await query.edit_message_text(
            "👥 Your Referral Link\n\n"
            + ref_link + "\n\n"
            "Share this link!\n"
            "Each person who joins = +10 points for you!\n"
            "No limit - more invites = more points!\n\n"
            "Climb to Top 5 for +10,000 NOTRUG bonus!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Back to Tasks", callback_data="back_tasks")
            ]])
        )

    elif query.data == "check_points":
        user = get_user(tid)
        wallet = user[2] or "Not set yet"
        tasks = (
            "Twitter follow: " + ("Done +25pts" if user[3] else "Pending") + "\n"
            "Tweet like: " + ("Done +25pts" if user[5] else "Pending") + "\n"
            "Telegram join: " + ("Done +20pts" if user[4] else "Pending") + "\n"
            "Tweet retweet: " + ("Done +15pts" if user[6] else "Pending") + "\n"
            "Daily messages: " + str(user[13] or 0) + " days x10pts\n"
        )
        msg = (
            "📊 YOUR STATS\n\n"
            "Points: " + str(user[7]) + "/100\n"
            "Wallet: " + str(wallet) + "\n"
            "Claimed: " + ("Yes" if user[8] else "No") + "\n\n"
            "Task Status:\n" + tasks
        )
        if user[7] >= REQUIRED_POINTS and not user[8]:
            if user[2]:
                msg += "\nYou qualify! Type /claim to get your NOTRUG!"
            else:
                msg += "\nYou qualify! Add wallet: /wallet YOUR_ADDRESS"
        await query.edit_message_text(msg, reply_markup=task_keyboard(user))

    elif query.data == "leaderboard":
        lb = get_leaderboard()
        medals = ["🥇", "🥈", "🥉", "4.", "5."]
        text = "🏆 LEADERBOARD - TOP 5\n\n"
        for i, (uname, pts) in enumerate(lb):
            medal = medals[i] if i < len(medals) else str(i+1) + "."
            text += medal + " @" + str(uname) + " - " + str(pts) + " pts\n"
        text += "\nTop 5 get +10,000 NOTRUG bonus at launch!"
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Back to Tasks", callback_data="back_tasks")
            ]])
        )

    elif query.data == "back_tasks":
        user = get_user(tid)
        await query.edit_message_text(
            "Your points: " + str(user[7]) + "/100\n\nComplete tasks:",
            reply_markup=task_keyboard(user)
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.message.chat.type != "private":
        return

    tid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    text = update.message.text.strip()
    user = get_user(tid)
    if not user:
        create_user(tid, username, gen_ref(tid))
        user = get_user(tid)

    step = user[9]

    if step == "twitter_username":
        twitter = text.replace("@", "").strip()
        update_user(tid, twitter_done=1, step="start")
        add_points(tid, POINTS["twitter_follow"])
        user = get_user(tid)
        await update.message.reply_text(
            "Twitter follow verified! +25 points\n\n"
            "Your points: " + str(user[7]) + "/100\n\n"
            "Complete more tasks:",
            reply_markup=task_keyboard(user)
        )
        return

    if step == "tweet_like_link":
        if "x.com" in text or "twitter.com" in text:
            update_user(tid, tweet_like_done=1, step="start")
            add_points(tid, POINTS["tweet_like"])
            user = get_user(tid)
            await update.message.reply_text(
                "Tweet like verified! +25 points\n\n"
                "Your points: " + str(user[7]) + "/100\n\n"
                "Complete more tasks:",
                reply_markup=task_keyboard(user)
            )
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    if step == "retweet_link":
        if "x.com" in text or "twitter.com" in text:
            update_user(tid, tweet_retweet_done=1, step="start")
            add_points(tid, POINTS["tweet_retweet"])
            user = get_user(tid)
            await update.message.reply_text(
                "Retweet verified! +15 points\n\n"
                "Your points: " + str(user[7]) + "/100\n\n"
                "Complete more tasks:",
                reply_markup=task_keyboard(user)
            )
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    if step == "pinned_comment_link":
        if "x.com" in text or "twitter.com" in text:
            update_user(tid, tweet_comment_done=1, step="start")
            add_points(tid, POINTS["tweet_comment"])
            user = get_user(tid)
            await update.message.reply_text(
                "Pinned tweet comment verified! +15 points\n\n"
                "Your points: " + str(user[7]) + "/100\n\n"
                "Complete more tasks:",
                reply_markup=task_keyboard(user)
            )
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    if step == "new_comment_link":
        if "x.com" in text or "twitter.com" in text:
            # Check if link already used
            conn = __import__('sqlite3').connect("airdrop.db")
            c = conn.cursor()
            try:
                c.execute("CREATE TABLE IF NOT EXISTS tweet_comments (telegram_id INTEGER, tweet_url TEXT, UNIQUE(tweet_url))")
                c.execute("INSERT INTO tweet_comments (telegram_id, tweet_url) VALUES (?,?)", (tid, text))
                conn.commit()
                conn.close()
                update_user(tid, step="start")
                add_points(tid, POINTS["new_tweet_comment"])
                user = get_user(tid)
                await update.message.reply_text(
                    "Tweet comment verified! +10 points\n\n"
                    "Your points: " + str(user[7]) + "\n\n"
                    "Comment on more tweets for more points!",
                    reply_markup=task_keyboard(user)
                )
            except:
                conn.close()
                update_user(tid, step="start")
                await update.message.reply_text(
                    "This tweet link was already submitted!\n\n"
                    "Comment on a different tweet for +10 points.",
                    reply_markup=task_keyboard(user)
                )
        else:
            await update.message.reply_text("Please send a valid tweet link (x.com or twitter.com)")
        return

    await start(update, context)

async def wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    user = get_user(tid)
    if not user:
        await update.message.reply_text("Please /start first!")
        return
    if not context.args:
        await update.message.reply_text("Usage: /wallet YOUR_SOLANA_ADDRESS")
        return
    wallet = context.args[0]
    if len(wallet) < 32 or len(wallet) > 44:
        await update.message.reply_text("Invalid Solana address!")
        return
    if wallet_exists(wallet, tid):
        await update.message.reply_text("This wallet is already registered by someone else!")
        return
    update_user(tid, wallet=wallet)
    await update.message.reply_text("Wallet saved: " + wallet[:20] + "...")

async def claim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    user = get_user(tid)
    if not user:
        await update.message.reply_text("Please /start first!")
        return
    if user[7] < REQUIRED_POINTS:
        await update.message.reply_text(
            "You need 100 points to claim!\n"
            "Your points: " + str(user[7]) + "/100\n\n"
            "Use /start to complete tasks."
        )
        return
    if user[8]:
        await update.message.reply_text("You already claimed your NOTRUG!")
        return
    if not user[2]:
        await update.message.reply_text("Add your wallet first!\n\n/wallet YOUR_SOLANA_ADDRESS")
        return

    update_user(tid, claimed=1)
    await update.message.reply_text(
        "Claim submitted!\n\n"
        "Wallet: " + user[2] + "\n"
        "Amount: 10,000 NOTRUG\n\n"
        "We will send within 24 hours!\n\n"
        "Keep earning points - Top 5 get bonus 10,000 NOTRUG at launch!"
    )
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "NEW AIRDROP CLAIM!\n\n"
            "User: @" + str(user[1]) + "\n"
            "ID: " + str(tid) + "\n"
            "Wallet: " + str(user[2]) + "\n"
            "Points: " + str(user[7]) + "\n\n"
            "Send 10,000 NOTRUG manually!"
        )
    )

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lb = get_leaderboard()
    medals = ["🥇", "🥈", "🥉", "4.", "5."]
    text = "🏆 LEADERBOARD - TOP 5\n\n"
    for i, (uname, pts) in enumerate(lb):
        medal = medals[i] if i < len(medals) else str(i+1) + "."
        text += medal + " @" + str(uname) + " - " + str(pts) + " pts\n"
    text += "\nTop 5 get +10,000 NOTRUG bonus at launch!\n\nKeep earning: daily messages + referrals!"
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
    claimed = get_all_claimed()
    if not claimed:
        await update.message.reply_text("No claims yet!")
        return
    text = "CLAIMED WALLETS\n\n"
    for u in claimed:
        text += "@" + str(u[0]) + " | " + str(u[1])[:20] + " | " + str(u[2]) + "pts\n"
    await update.message.reply_text(text)

async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.message.chat.username != "notrugfun":
        return

    tid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    user = get_user(tid)
    if not user:
        return

    today = str(date.today())

    if user[12] == today:
        return

    update_user(tid, last_daily=today, daily_count=(user[13] or 0) + 1)
    add_points(tid, POINTS["daily_message"])

    try:
        user = get_user(tid)
        await context.bot.send_message(
            chat_id=tid,
            text=(
                "Daily message bonus! +10 points\n\n"
                "Your total points: " + str(user[7]) + "\n"
                "Come back tomorrow for more!"
            )
        )
    except:
        pass

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, group_message_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_message))
    print("NOTRUG Airdrop Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
