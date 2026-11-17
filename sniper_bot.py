import os
import asyncio
import warnings
warnings.filterwarnings('ignore')

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from sklearn.ensemble import GradientBoostingClassifier
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession

# ==============================================================================
# ⚙️ V5.5 PRO DAILY $50 SNIPER ENGINE (3-5 A+ SIGNALS/DAY + SPOT XAU/USD)
# ==============================================================================
ACCOUNT_BALANCE_USD = float(os.getenv("ACCOUNT_BALANCE", "500.0"))
DAILY_TARGET_USD    = float(os.getenv("DAILY_TARGET_USD", "50.0"))
RISK_PER_TRADE_PCT  = float(os.getenv("RISK_PERCENT", "2.0"))
GITHUB_EVENT_NAME   = os.getenv("GITHUB_EVENT_NAME", "manual")

API_ID              = int(os.getenv("API_ID", "0") or "0")
API_HASH            = os.getenv("API_HASH", "").strip()
STRING_SESSION      = os.getenv("STRING_SESSION", "").strip()
BOT_TOKEN           = os.getenv("TELEGRAM_BOT_TOKEN", "8928636596:AAF0vfjan62EL3gq5vGkKvm_Ocfpy9XuM3k").strip()
CHAT_ID             = os.getenv("TELEGRAM_CHAT_ID", "").strip()

async def send_telegram_alert(text):
    sent = False
    user_id = CHAT_ID

    if API_ID and API_HASH and STRING_SESSION:
        try:
            client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
            await client.start()
            me = await client.get_me()
            if not user_id and me:
                user_id = str(me.id)

            await client.send_message("me", text)
            print(f"✅ Sent Sniper Signal to Telegram Saved Messages (User: {me.first_name})")
            sent = True
            await client.disconnect()
        except Exception as e:
            print(f"⚠️ Telethon send warning: {e}")

    if BOT_TOKEN and user_id:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": user_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            r = requests.post(url, data=payload, timeout=15)
            if r.status_code == 200:
                print(f"✅ Sent push notification via Bot API to {user_id}!")
                sent = True
        except Exception as e:
            print(f"⚠️ Bot API send warning: {e}")

    if not sent:
        print(text)

# ==============================================================================
# 🎯 1. EXACT XM SPOT GOLD (XAU/USD) CALIBRATION + MACRO FEEDS
# ==============================================================================
def get_live_spot_xauusd():
    try:
        r = requests.get("https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD", timeout=6)
        if r.status_code == 200:
            data = r.json()
            prices = data[0]['spreadProfilePrices'][0]
            mid = (float(prices['bid']) + float(prices['ask'])) / 2.0
            if mid > 1500:
                return round(mid, 2), "Swissquote Institutional Spot"
    except Exception:
        pass

    try:
        r = requests.get("https://api.gold-api.com/price/XAU", timeout=6)
        if r.status_code == 200:
            mid = float(r.json().get("price", 0))
            if mid > 1500:
                return round(mid, 2), "London Spot XAU/USD"
    except Exception:
        pass

    try:
        r = requests.get("https://data-api.binance.vision/api/v3/ticker/price?symbol=PAXGUSDT", timeout=6)
        if r.status_code == 200:
            mid = float(r.json().get("price", 0))
            if mid > 1500:
                return round(mid, 2), "Spot Gold Index"
    except Exception:
        pass

    return None, "COMEX Futures Adjusted"

def fetch_v5_institutional_data():
    g15   = yf.download("GC=F", period="59d", interval="15m", progress=False)
    g1h   = yf.download("GC=F", period="180d", interval="1h", progress=False)
    dxy   = yf.download("DX-Y.NYB", period="59d", interval="15m", progress=False)
    us10y = yf.download("^TNX", period="59d", interval="1h", progress=False)

    for d in [g15, g1h, dxy, us10y]:
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)

    df = g15[['Open', 'High', 'Low', 'Close', 'Volume']].dropna().copy()
    h1 = g1h[['Open', 'High', 'Low', 'Close']].dropna().copy()

    spot_price, feed_name = get_live_spot_xauusd()
    basis_offset = 0.0
    if spot_price is not None and not df.empty:
        basis_offset = spot_price - float(df['Close'].iloc[-1])
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = df[col] + basis_offset
            h1[col] = h1[col] + basis_offset

    if df.index.tz is not None:
        df.index = df.index.tz_convert('UTC')
    if h1.index.tz is not None:
        h1.index = h1.index.tz_convert('UTC')

    h1['H1_EMA20'] = h1['Close'].ewm(span=20, adjust=False).mean()
    h1['H1_EMA50'] = h1['Close'].ewm(span=50, adjust=False).mean()
    h1['H1_Trend'] = np.where(h1['Close'] > h1['H1_EMA20'], 1, -1)

    h4 = h1['Close'].resample('4h').last().dropna().to_frame()
    h4['H4_EMA20'] = h4['Close'].ewm(span=20, adjust=False).mean()
    h4['H4_Trend'] = np.where(h4['Close'] > h4['H4_EMA20'], 1, -1)

    df = pd.merge_asof(df.sort_index(), h1[['H1_Trend']].sort_index(), left_index=True, right_index=True, direction='backward')
    df = pd.merge_asof(df.sort_index(), h4[['H4_Trend']].sort_index(), left_index=True, right_index=True, direction='backward')

    if not dxy.empty:
        if dxy.index.tz is not None:
            dxy.index = dxy.index.tz_convert('UTC')
        dxy_c = dxy[['Close']].rename(columns={'Close': 'DXY_Close'}).dropna()
        df = pd.merge_asof(df.sort_index(), dxy_c.sort_index(), left_index=True, right_index=True, direction='backward')
        df['DXY_EMA20'] = df['DXY_Close'].ewm(span=20, adjust=False).mean()
        df['DXY_Trend'] = np.where(df['DXY_Close'] < df['DXY_EMA20'], 1, -1)
    else:
        df['DXY_Trend'] = 0

    if not us10y.empty:
        if us10y.index.tz is not None:
            us10y.index = us10y.index.tz_convert('UTC')
        tnx_c = us10y[['Close']].rename(columns={'Close': 'TNX_Close'}).dropna()
        df = pd.merge_asof(df.sort_index(), tnx_c.sort_index(), left_index=True, right_index=True, direction='backward')
        df['TNX_EMA20'] = df['TNX_Close'].ewm(span=20, adjust=False).mean()
        df['TNX_Trend'] = np.where(df['TNX_Close'] < df['TNX_EMA20'], 1, -1)
    else:
        df['TNX_Trend'] = 0

    return df, feed_name, basis_offset

# ==============================================================================
# 🧠 2. MULTI-STRATEGY ICT ENGINE (PULLBACK + LIQUIDITY SWEEP + KILLZONE BREAKOUT)
# ==============================================================================
def compute_v5_features(df):
    df['EMA_9']   = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21']  = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA_50']  = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    high_low   = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close  = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()

    atr_sum_14 = tr.rolling(14).sum()
    max_hi_14  = df['High'].rolling(14).max()
    min_lo_14  = df['Low'].rolling(14).min()
    df['CHOP'] = 100 * np.log10(atr_sum_14 / (max_hi_14 - min_lo_14 + 1e-9)) / np.log10(14)

    up_move   = df['High'].diff()
    down_move = -df['Low'].diff()
    plus_dm   = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm  = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr_smooth = tr.rolling(14).mean()
    plus_di   = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / (tr_smooth + 1e-9))
    minus_di  = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / (tr_smooth + 1e-9))
    dx        = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
    df['ADX'] = dx.rolling(14).mean()

    delta = df['Close'].diff()
    gain  = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD']        = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist']   = df['MACD'] - df['MACD_Signal']

    df['Vol_SMA20'] = df['Volume'].rolling(20).mean()
    df['Vol_Spike'] = (df['Volume'] >= df['Vol_SMA20'] * 0.75).astype(int)

    df['Swing_High_12'] = df['High'].shift(1).rolling(12).max()
    df['Swing_Low_12']  = df['Low'].shift(1).rolling(12).min()

    # Setup 1: Order Block / EMA21 Value Zone Pullback
    df['Bull_Pullback'] = (df['Close'] > df['Open']) & (df['Close'] > df['EMA_9']) & (df['Low'] <= df['EMA_21'] * 1.001) & ((df['Close'] - df['EMA_21']) <= df['ATR'] * 1.25)
    df['Bear_Pullback'] = (df['Close'] < df['Open']) & (df['Close'] < df['EMA_9']) & (df['High'] >= df['EMA_21'] * 0.999) & ((df['EMA_21'] - df['Close']) <= df['ATR'] * 1.25)

    # Setup 2: ICT Liquidity Sweep / Stop-Hunt Reversal (Turtle Soup)
    df['Bull_Sweep'] = ((df['Low'] <= df['Swing_Low_12']) | (df['Low'].shift(1) <= df['Swing_Low_12'].shift(1))) & (df['Close'] > df['Open']) & (df['Close'] > df['EMA_9'])
    df['Bear_Sweep'] = ((df['High'] >= df['Swing_High_12']) | (df['High'].shift(1) >= df['Swing_High_12'].shift(1))) & (df['Close'] < df['Open']) & (df['Close'] < df['EMA_9'])

    # Setup 3: Fair Value Gap (FVG) / Institutional Momentum Displacement
    df['Bull_FVG'] = (df['Low'] > df['High'].shift(2)) & (df['Close'] > df['Open']) & ((df['Close'] - df['EMA_21']) <= df['ATR'] * 1.35)
    df['Bear_FVG'] = (df['High'] < df['Low'].shift(2)) & (df['Close'] < df['Open']) & ((df['EMA_21'] - df['Close']) <= df['ATR'] * 1.35)

    hours = df.index.hour
    df['Killzone_Gate'] = ((hours >= 5) & (hours <= 19)).astype(int)

    df.dropna(subset=['ATR', 'ADX', 'RSI', 'CHOP', 'EMA_200'], inplace=True)
    return df

def run_v5_engine(df):
    future_high = df['High'].shift(-1).rolling(16).max().shift(-15)
    future_low  = df['Low'].shift(-1).rolling(16).min().shift(-15)

    df['Target_Buy']  = ((future_high - df['Close']) >= (df['ATR'] * 0.95)).astype(int)
    df['Target_Sell'] = ((df['Close'] - future_low) >= (df['ATR'] * 0.95)).astype(int)

    df['Dist_EMA21'] = (df['Close'] - df['EMA_21']) / df['ATR']
    df['Dist_EMA50'] = (df['Close'] - df['EMA_50']) / df['ATR']
    df['Body_ATR']   = (df['Close'] - df['Open']) / df['ATR']

    features = ['RSI', 'ADX', 'CHOP', 'MACD_Hist', 'H1_Trend', 'H4_Trend', 'DXY_Trend', 'TNX_Trend', 'Vol_Spike', 'Dist_EMA21', 'Dist_EMA50', 'Body_ATR']

    split = int(len(df) * 0.6)
    train_df = df.iloc[:split].dropna(subset=features + ['Target_Buy', 'Target_Sell'])

    gb_buy  = GradientBoostingClassifier(n_estimators=140, max_depth=3, learning_rate=0.04, random_state=42)
    gb_sell = GradientBoostingClassifier(n_estimators=140, max_depth=3, learning_rate=0.04, random_state=42)

    gb_buy.fit(train_df[features], train_df['Target_Buy'])
    gb_sell.fit(train_df[features], train_df['Target_Sell'])

    df['AI_Buy_Prob']  = gb_buy.predict_proba(df[features])[:, 1] * 100
    df['AI_Sell_Prob'] = gb_sell.predict_proba(df[features])[:, 1] * 100

    # Graduated 100-Point Institutional Confluence Matrix (No more 0/35 cliffs!)
    buy_score  = np.zeros(len(df))
    sell_score = np.zeros(len(df))

    # 1. Multi-Timeframe Structure (Up to 30 pts, graduated)
    buy_score  += np.where(df['H4_Trend'] == 1, 12, 0) + np.where(df['H1_Trend'] == 1, 10, 0) + np.where(df['Close'] > df['EMA_50'], 8, 0)
    sell_score += np.where(df['H4_Trend'] == -1, 12, 0) + np.where(df['H1_Trend'] == -1, 10, 0) + np.where(df['Close'] < df['EMA_50'], 8, 0)

    # 2. ICT Setup Trigger (Pullback OR Liquidity Sweep OR FVG -> 25 pts)
    buy_score  += np.where(df['Bull_Pullback'] | df['Bull_Sweep'] | df['Bull_FVG'], 25, 0)
    sell_score += np.where(df['Bear_Pullback'] | df['Bear_Sweep'] | df['Bear_FVG'], 25, 0)

    # 3. Momentum & Market Regime (Up to 20 pts, graduated)
    buy_score  += np.where(df['CHOP'] < 60.0, 7, 0) + np.where((df['RSI'] >= 46) & (df['RSI'] <= 68), 7, 0) + np.where(df['MACD_Hist'] > df['MACD_Hist'].shift(1), 6, 0)
    sell_score += np.where(df['CHOP'] < 60.0, 7, 0) + np.where((df['RSI'] <= 54) & (df['RSI'] >= 32), 7, 0) + np.where(df['MACD_Hist'] < df['MACD_Hist'].shift(1), 6, 0)

    # 4. Macro Correlation (DXY + US10Y Yields + Volume -> Up to 15 pts)
    buy_score  += np.where(df['DXY_Trend'] == 1, 5, 0) + np.where(df['TNX_Trend'] == 1, 5, 0) + np.where(df['Vol_Spike'] == 1, 5, 0)
    sell_score += np.where(df['DXY_Trend'] == -1, 5, 0) + np.where(df['TNX_Trend'] == -1, 5, 0) + np.where(df['Vol_Spike'] == 1, 5, 0)

    # 5. AI Probability Boost (Up to 10 pts)
    buy_score  += np.where(df['AI_Buy_Prob'] >= 58, 10, np.where(df['AI_Buy_Prob'] >= 50, 5, 0))
    sell_score += np.where(df['AI_Sell_Prob'] >= 58, 10, np.where(df['AI_Sell_Prob'] >= 50, 5, 0))

    # Mandatory Killzone Gate
    buy_score  = np.where(df['Killzone_Gate'] == 1, buy_score, 0)
    sell_score = np.where(df['Killzone_Gate'] == 1, sell_score, 0)

    df['Buy_Confluence']  = buy_score
    df['Sell_Confluence'] = sell_score

    signals = np.full(len(df), "NEUTRAL", dtype=object)
    setup_type = np.full(len(df), "NONE", dtype=object)
    last_idx = -10
    for i in range(len(df)):
        if i - last_idx < 6: # Max 1 signal every 1.5 hours (allows 3-5 sniper setups/day)
            continue
        if buy_score[i] >= 74 and df['Close'].iloc[i] > df['Open'].iloc[i]:
            signals[i] = "BUY"
            if df['Bull_Sweep'].iloc[i]:
                setup_type[i] = "ICT Liquidity Sweep Reversal"
            elif df['Bull_FVG'].iloc[i]:
                setup_type[i] = "Institutional FVG Displacement"
            else:
                setup_type[i] = "Order Block / EMA21 Pullback"
            last_idx = i
        elif sell_score[i] >= 74 and df['Close'].iloc[i] < df['Open'].iloc[i]:
            signals[i] = "SELL"
            if df['Bear_Sweep'].iloc[i]:
                setup_type[i] = "ICT Liquidity Sweep Reversal"
            elif df['Bear_FVG'].iloc[i]:
                setup_type[i] = "Institutional FVG Displacement"
            else:
                setup_type[i] = "Order Block / EMA21 Pullback"
            last_idx = i

    df['Signal'] = signals
    df['Setup_Type'] = setup_type
    return df

def build_signal_message(signal_row, signal_time, current_spot_price, is_live_now=True):
    sig_sl_time = signal_time + timedelta(hours=5, minutes=30)
    direction   = signal_row['Signal']
    setup_name  = signal_row.get('Setup_Type', 'ICT Institutional Setup')
    entry       = float(signal_row['Close'])
    ema21_val   = float(signal_row['EMA_21'])
    atr         = float(signal_row['ATR'])

    sl_dist  = atr * 1.50
    be_dist  = atr * 0.45
    tp1_dist = atr * 0.90
    tp2_dist = atr * 1.80
    tp3_dist = atr * 3.20

    if direction == "BUY":
        limit_pullback = max(entry - (atr * 0.35), ema21_val)
        sl  = entry - sl_dist
        be  = entry + be_dist
        tp1 = entry + tp1_dist
        tp2 = entry + tp2_dist
        tp3 = entry + tp3_dist
        header = "🟢 **XAU/USD V5.5 SNIPER BUY SIGNAL**"
        entry_zone_str = f"`${limit_pullback:,.2f} — ${entry:,.2f}`"
        pnl_now = current_spot_price - entry
    else:
        limit_pullback = min(entry + (atr * 0.35), ema21_val)
        sl  = entry + sl_dist
        be  = entry - be_dist
        tp1 = entry - tp1_dist
        tp2 = entry - tp2_dist
        tp3 = entry - tp3_dist
        header = "🔴 **XAU/USD V5.5 SNIPER SELL SIGNAL**"
        entry_zone_str = f"`${entry:,.2f} — ${limit_pullback:,.2f}`"
        pnl_now = entry - current_spot_price

    risk_usd  = ACCOUNT_BALANCE_USD * (RISK_PER_TRADE_PCT / 100.0)
    safe_lots = max(0.01, round((risk_usd / sl_dist) * 0.01, 2))
    lots_for_25_at_tp1 = max(0.01, round((25.0 / tp1_dist) * 0.01, 2))
    lots_for_50_at_tp2 = max(0.01, round((50.0 / tp2_dist) * 0.01, 2))

    score_val = signal_row['Buy_Confluence'] if direction == "BUY" else signal_row['Sell_Confluence']
    grade = "🔥 A++ GOD-TIER SETUP" if score_val >= 85 else "⭐ A+ INSTITUTIONAL SNIPER"
    status_tag = "🚨 **NEW LIVE CANDLE TRIGGER**" if is_live_now else f"📡 **ACTIVE INTRADAY SIGNAL** (Current Spot: `${current_spot_price:,.2f}` | Move: `{pnl_now:+.2f} USD`)"

    msg = (
        f"{header}\n"
        f"{status_tag}\n"
        f"🎖️ **Grade:** {grade} (`{score_val:.0f}/100`)\n"
        f"🧠 **Strategy:** `{setup_name}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ **Signal Time (SL):** `{sig_sl_time.strftime('%Y-%m-%d %I:%M %p')}`\n"
        f"📌 **Signal Entry Price (XM Spot):** `${entry:,.2f}`\n"
        f"🎯 **Optimal Entry Zone:** {entry_zone_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛡️ **Breakeven Lock (+0.45R):** `${be:,.2f}`\n"
        f"🛑 **Stop Loss (SL):** `${sl:,.2f}` (`${sl_dist:.2f}` risk)\n"
        f"✅ **TP1 (Fast Scalp Lock):** `${tp1:,.2f}` (`+${tp1_dist:.2f}`)\n"
        f"✅ **TP2 (Main Daily Target):** `${tp2:,.2f}` (`+${tp2_dist:.2f}`)\n"
        f"✅ **TP3 (Big Runner):** `${tp3:,.2f}` (`+${tp3_dist:.2f}`)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 **$50/DAY PROFIT LOT CALCULATOR:**\n"
        f"• **Safe Risk ({RISK_PER_TRADE_PCT}%):** `{safe_lots:.2f} Lots`\n"
        f"• **For +$25 at TP1:** `{lots_for_25_at_tp1:.2f} Lots` (2 Trades = $50/day)\n"
        f"• **For +$50 at TP2:** `{lots_for_50_at_tp2:.2f} Lots` (1 Trade = $50/day)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛡️ *Rule: Move SL to Entry (`${entry:,.2f}`) as soon as price touches `${be:,.2f}`!*"
    )
    return msg

async def main():
    print("🚀 Running V5.5 Pro Daily $50 Sniper Engine...")
    df, feed_name, basis_offset = fetch_v5_institutional_data()
    df = compute_v5_features(df)
    df = run_v5_engine(df)

    latest = df.iloc[-1]
    prev   = df.iloc[-2]
    current_spot = float(latest['Close'])

    # 1. Check if a brand-new signal triggered on the latest or just-closed 15m candle
    if latest['Signal'] in ['BUY', 'SELL']:
        msg = build_signal_message(latest, df.index[-1], current_spot, is_live_now=True)
        await send_telegram_alert(msg)
    elif prev['Signal'] in ['BUY', 'SELL']:
        msg = build_signal_message(prev, df.index[-2], current_spot, is_live_now=True)
        await send_telegram_alert(msg)
    # 2. If triggered manually (or testing), ALWAYS send the Full Active Signal Card + Live Instant Bias Setup!
    elif GITHUB_EVENT_NAME == "workflow_dispatch":
        recent_sigs = df[df['Signal'].isin(['BUY', 'SELL'])]
        if not recent_sigs.empty:
            last_row  = recent_sigs.iloc[-1]
            last_time = recent_sigs.index[-1]
            msg = build_signal_message(last_row, last_time, current_spot, is_live_now=False)
            await send_telegram_alert(msg)
    else:
        print(f"ℹ️ V5.5 Scan Complete | Spot XAUUSD: ${current_spot:,.2f} | Buy: {latest['Buy_Confluence']:.0f} | Sell: {latest['Sell_Confluence']:.0f}")

if __name__ == "__main__":
    asyncio.run(main())
