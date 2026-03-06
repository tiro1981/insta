import asyncio
import sqlite3
import ccxt
import pandas as pd
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- SOZLAMALAR ---
API_TOKEN = '7977436031:AAG6p4eIgqxBdgQ2FJlrYl9zo9j3FF2eHYw'
CHANNEL_ID = '@taxibotlar'
BINANCE = ccxt.binance({'enableRateLimit': True})

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# --- 1. DATABASE (XOTIRA VA STATISTIKA) ---
def init_db():
    conn = sqlite3.connect('super_ai_final.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS symbols (name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS active_trades 
                 (symbol TEXT UNIQUE, tf TEXT, entry REAL, t1 REAL, t2 REAL, t3 REAL, sl REAL, 
                  confidence INTEGER, msg_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats (win INTEGER, loss INTEGER)''')
    c.execute("INSERT OR IGNORE INTO stats VALUES (0, 0)")
    conn.commit()
    conn.close()

def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect('super_ai_final.db')
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return res

# --- 2. ANALIZ VA BALL TIZIMI ---
def get_signal(symbol, tf):
    try:
        bars = BINANCE.fetch_ohlcv(symbol, timeframe=tf, limit=200)
        df = pd.DataFrame(bars, columns=['time','open','high','low','close','volume'])
        
        # Indikatorlar
        df['ema200'] = df['close'].ewm(span=200).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        l = df.iloc[-1]
        prev = df.iloc[-5]
        
        # 7 ta Filtr (Ball tizimi)
        score = 0
        if l['close'] > l['ema200']: score += 1
        if 45 < l['rsi'] < 65: score += 1
        if l['volume'] > df['volume'].tail(10).mean() * 1.2: score += 1
        if l['close'] > prev['close']: score += 1
        if l['rsi'] > prev['rsi']: score += 1
        if abs(l['rsi'] - 50) < 15: score += 1
        if l['close'] > df['open'].iloc[-1]: score += 1

        if score >= 1:
            conf_map = {1:50, 2:55, 3:65, 4:70, 5:75, 6:80, 7:85}
            entry = l['close']
            return {
                "symbol": symbol.replace('/USDT', ''),
                "tf": tf,
                "entry": round(entry, 4),
                "t1": round(entry * 1.02, 4),
                "t2": round(entry * 1.05, 4),
                "t3": round(entry * 1.10, 4),
                "sl": round(entry * 0.97, 4),
                "conf": conf_map.get(score, 50),
                "score": score
            }
    except: return None

# --- 3. SKANER VA MONITORING ---
async def scan_markets(app: Application):
    symbols = db_query("SELECT name FROM symbols", fetch=True)
    for (sym,) in symbols:
        # 5m olib tashlandi, faqat 15m va 1h qoldi
        for tf in ['15m', '1h']:
            s = get_signal(f"{sym}/USDT", tf)
            if s:
                exists = db_query("SELECT * FROM active_trades WHERE symbol=?", (s['symbol'],), fetch=True)
                if not exists:
                    header = "🟢" if s['conf'] >= 75 else "🟡" if s['conf'] >= 65 else "🔴"
                    text = (f"{header} **TAHLIL ANIQLIGI: {s['conf']}%**\n\n"
                            f"💰 Koin: #{s['symbol']} ({s['tf']})\n"
                            f"📥 Kirish: {s['entry']}\n\n"
                            f"🎯 Maqsadlar:\n"
                            f"1. {s['entry']} - {s['t1']} (+2% 🟢)\n"
                            f"2. {s['entry']} - {s['t2']} (+5% 🟡)\n"
                            f"3. {s['entry']} - {s['t3']} (+10% 🔴)\n\n"
                            f"🛡 Stoploss: {s['sl']}\n"
                            f"📊 Filtrlar: {s['score']}/7")
                    
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📉 Grafikni ko'rish", url=f"https://www.tradingview.com/symbols/{s['symbol']}USDT/")]])
                    
                    msg = await app.bot.send_message(CHANNEL_ID, text, parse_mode='Markdown', reply_markup=kb)
                    db_query("INSERT INTO active_trades VALUES (?,?,?,?,?,?,?,?,?)", 
                             (s['symbol'], s['tf'], s['entry'], s['t1'], s['t2'], s['t3'], s['sl'], s['conf'], msg.message_id))

async def trade_monitor(app: Application):
    trades = db_query("SELECT * FROM active_trades", fetch=True)
    for t in trades:
        try:
            p = BINANCE.fetch_ticker(f"{t[0]}/USDT")['last']
            if p >= t[3]: # Target 1
                await app.bot.send_message(CHANNEL_ID, "✅", reply_to_message_id=t[8])
                db_query("UPDATE stats SET win = win + 1")
                db_query("DELETE FROM active_trades WHERE symbol=?", (t[0],))
            elif p <= t[6]: # Stoploss
                await app.bot.send_message(CHANNEL_ID, "❌", reply_to_message_id=t[8])
                db_query("UPDATE stats SET loss = loss + 1")
                db_query("DELETE FROM active_trades WHERE symbol=?", (t[0],))
        except: continue

# --- 4. HISOBOT VA MENU ---
async def daily_report(app: Application):
    res = db_query("SELECT win, loss FROM stats", fetch=True)[0]
    win, loss = res[0], res[1]
    total = win + loss
    wr = round((win/total*100), 1) if total > 0 else 0
    report = (f"📊 **KUNLIK HISOBOT**\n\n✅ Muvaffaqiyat: {win}\n❌ Zarar: {loss}\n📈 Jami: {total}\n🎯 Winrate: {wr}%")
    await app.bot.send_message(CHANNEL_ID, report, parse_mode='Markdown')
    db_query("UPDATE stats SET win=0, loss=0")

# --- 5. INTERFEIS TUGMALARI (ANALIZ TUGMASI OLIB TASHLANDI) ---
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Paralar ro'yxati", callback_data='list')],
        [InlineKeyboardButton("➕ Para qo'shish", callback_data='add')]
    ])

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("🤖 Boshqaruv Paneli:", reply_markup=main_menu())

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query
    await q.answer()
    
    if q.data == 'main':
        await q.edit_message_text("🤖 Boshqaruv Paneli:", reply_markup=main_menu())
    elif q.data == 'list':
        syms = db_query("SELECT name FROM symbols", fetch=True)
        if not syms:
            await q.edit_message_text("❌ Paralar yo'q.", reply_markup=main_menu())
        else:
            kb = [[InlineKeyboardButton(f"🔸 {s[0]}", callback_data=f"manage_{s[0]}")] for s in syms]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='main')])
            await q.edit_message_text("O'chirish uchun parani tanlang:", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data.startswith('manage_'):
        s = q.data.split('_')[1]
        kb = [[InlineKeyboardButton(f"🗑 {s} ni o'chirish", callback_data=f"del_{s}")], [InlineKeyboardButton("⬅️ Ortga", callback_data='list')]]
        await q.edit_message_text(f"❓ {s} ni o'chirasizmi?", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data.startswith('del_'):
        s = q.data.split('_')[1]
        db_query("DELETE FROM symbols WHERE name=?", (s,))
        await q.edit_message_text(f"✅ {s} o'chirildi.", reply_markup=main_menu())
    elif q.data == 'add':
        c.user_data['wait'] = True
        await q.edit_message_text("📝 Yangi parani kiriting (Masalan: BTC/USDT):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='main')]]))

async def msg_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if c.user_data.get('wait'):
        s = u.message.text.upper().replace('/USDT', '')
        try:
            db_query("INSERT INTO symbols VALUES (?)", (s,))
            await u.message.reply_text(f"✅ {s} qo'shildi!", reply_markup=main_menu())
        except: await u.message.reply_text("❌ Xato yoki mavjud.", reply_markup=main_menu())
        c.user_data['wait'] = False

# --- 6. ISHGA TUSHIRISH ---
async def post_init(app: Application):
    init_db()
    sch = AsyncIOScheduler()
    sch.add_job(scan_markets, 'interval', minutes=2, args=[app])
    sch.add_job(trade_monitor, 'interval', seconds=30, args=[app])
    sch.add_job(daily_report, 'cron', hour=0, minute=0, args=[app])
    sch.start()

if __name__ == '__main__':
    application = Application.builder().token(API_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
    print("Bot 15m/1h rejimida ishlamoqda...")
    application.run_polling()
