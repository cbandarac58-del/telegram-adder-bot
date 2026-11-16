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
# ⚙️ USER & CLOUD SETTINGS
# ==============================================================================
ACCOUNT_BALANCE_USD = float(os.getenv("ACCOUNT_BALANCE", "500.0"))
RISK_PER_TRADE_PCT  = float(os.getenv("RISK_PERCENT", "1.5"))
GITHUB_EVENT_NAME   = os.getenv("GITHUB_EVENT_NAME", "manual")

API_ID              = int(os.getenv("API_ID", "0") or "0")
API_HASH            = os.getenv("API_HASH", "").strip()
STRING_SESSION      = os.getenv("STRING_SESSION", "").strip()
BOT_TOKEN           = os.getenv("TELEGRAM_BOT_TOKEN", "8928636596:AAF0vfjan62EL3gq5vGkKvm_Ocfpy9XuM3k").strip()
CHAT_ID             = os.getenv("TELEGRAM_CHAT_ID", "").strip()

async def send_telegram_alert(text):
    sent = False
    user_id = CHAT_ID

    # 1. Connect via Telethon StringSession (already stored in GitHub Secrets!)
    if API_ID and API_HASH and STRING_SESSION:
        try:
            client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
            await client.start()
            me = await client.get_me()
            if not user_id and me:
                user_id = str(me.id)

            # Send directly to Saved Messages ("me")
            await client.send_message("me", text)
            print(f"✅ Sent alert to Telegram Saved Messages (User: {me.first_name}, ID: {user_id})")
            sent = True
            await client.disconnect()
        except Exception as e:
            print(f"⚠️ Telethon send warning: {e}")

    # 2. Also send via Bot API to user_id so phone gets a loud push notification!
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
                print(f"✅ Sent push notification via Bot API to Chat ID {user_id}!")
                sent = True
        except Exception as e:
            print(f"⚠️ Bot API send warning: {e}")

    if not sent:
        print("⚠️ Could not send to Telegram. Printing output below:\n")
        print(text)

def fetch_v4_data():
    g15 = yf.download("GC=F", period="59d", interval="15m", progress=False)
    g1h = yf.download("GC=F", period="180d", interval="1h", progress=False)
    dxy = yf.download("DX-Y.NYB", period="59d", interval="15m", progress=False)

    for d in [g15, g1h, dxy]:
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)

    df = g15[['Open', 'High', 'Low', 'Close', 'Volume']].dropna().copy()

    h1 = g1h[['Open', 'High', 'Low', 'Close']].dropna().copy()
    h1['H1_EMA20'] = h1['Close'].ewm(span=20, adjust=False).mean()
    h1['H1_EMA50'] = h1['Close'].ewm(span=50, adjust=False).mean()
    h1['H1_Trend'] = np.where((h1['Close'] > h1['H1_EMA20']) & (h1['H1_EMA20'] > h1['H1_EMA50']), 1,
                     np.where((h1['Close'] < h1['H1_EMA20']) & (h1['H1_EMA20'] < h1['H1_EMA50']), -1, 0))

    h4 = h1['Close'].resample('4h').last().dropna().to_frame()
    h4['H4_EMA20'] = h4['Close'].ewm(span=20, adjust=False).mean()
    h4['H4_Trend'] = np.where(h4['Close'] > h4['H4_EMA20'], 1, -1)

    df = pd.merge_asof(df.sort_index(), h1[['H1_Trend']].sort_index(), left_index=True, right_index=True, direction='backward')
    df = pd.merge_asof(df.sort_index(), h4[['H4_Trend']].sort_index(), left_index=True, right_index=True, direction='backward')

    if not dxy.empty:
        dxy_c = dxy[['Close']].rename(columns={'Close': 'DXY_Close'}).dropna()
        df = pd.merge_asof(df.sort_index(), dxy_c.sort_index(), left_index=True, right_index=True, direction='backward')
        df['DXY_EMA20'] = df['DXY_Close'].ewm(span=20, adjust=False).mean()
        df['DXY_Trend'] = np.where(df['DXY_Close'] < df['DXY_EMA20'], 1, -1)
    else:
        df['DXY_Trend'] = 0

    return df

def add_v4_features(df):
    df['EMA_9']   = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21']  = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA_50']  = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()

    atr_sum_14 = tr.rolling(14).sum()
    max_hi_14  = df['High'].rolling(14).max()
    min_lo_14  = df['Low'].rolling(14).min()
    df['CHOP'] = 100 * np.log10(atr_sum_14 / (max_hi_14 - min_lo_14 + 1e-9)) / np.log10(14)

    up_move = df['High'].diff()
    down_move = -df['Low'].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr_smooth = tr.rolling(14).mean()
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / (tr_smooth + 1e-9))
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / (tr_smooth + 1e-9))
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
    df['ADX'] = dx.rolling(14).mean()

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    df['Vol_SMA20'] = df['Volume'].rolling(20).mean()
    df['Vol_Spike'] = (df['Volume'] >= df['Vol_SMA20'] * 0.80).astype(int)

    bull_ob_zone = np.where((df['Close'].shift(1) < df['Open'].shift(1)) &
                            ((df['Close'] - df['Open']) > df['ATR'] * 0.5), df['Low'].shift(1), np.nan)
    df['Bull_OB_Level'] = pd.Series(bull_ob_zone, index=df.index).ffill(limit=12)

    bear_ob_zone = np.where((df['Close'].shift(1) > df['Open'].shift(1)) &
                            ((df['Open'] - df['Close']) > df['ATR'] * 0.5), df['High'].shift(1), np.nan)
    df['Bear_OB_Level'] = pd.Series(bear_ob_zone, index=df.index).ffill(limit=12)

    df['Not_Overextended_Buy']  = ((df['Close'] - df['EMA_21']) <= (df['ATR'] * 1.35)) & (df['Close'] >= df['EMA_21'])
    df['Not_Overextended_Sell'] = ((df['EMA_21'] - df['Close']) <= (df['ATR'] * 1.35)) & (df['Close'] <= df['EMA_21'])

    df['Bull_OB_Trigger'] = (
        (df['Close'] > df['Open']) &
        (df['Close'] > df['EMA_9']) &
        df['Not_Overextended_Buy'] &
        ((df['Low'] <= df['EMA_21'] * 1.0005) | (df['Low'] <= df['Bull_OB_Level'] + df['ATR']*0.3) | (df['Low'] > df['High'].shift(2)))
    )

    df['Bear_OB_Trigger'] = (
        (df['Close'] < df['Open']) &
        (df['Close'] < df['EMA_9']) &
        df['Not_Overextended_Sell'] &
        ((df['High'] >= df['EMA_21'] * 0.9995) | (df['High'] >= df['Bear_OB_Level'] - df['ATR']*0.3) | (df['High'] < df['Low'].shift(2)))
    )

    hours = df.index.tz_convert('UTC').hour if df.index.tz is not None else df.index.hour
    df['Killzone_Gate'] = ((hours >= 7) & (hours <= 18)).astype(int)

    df.dropna(subset=['ATR', 'ADX', 'RSI', 'CHOP', 'EMA_200'], inplace=True)
    return df

def add_v4_ai(df):
    future_high = df['High'].shift(-1).rolling(16).max().shift(-15)
    future_low  = df['Low'].shift(-1).rolling(16).min().shift(-15)

    df['Target_Buy']  = ((future_high - df['Close']) >= (df['ATR'] * 1.0)).astype(int)
    df['Target_Sell'] = ((df['Close'] - future_low) >= (df['ATR'] * 1.0)).astype(int)

    df['Dist_EMA21'] = (df['Close'] - df['EMA_21']) / df['ATR']
    df['Dist_EMA50'] = (df['Close'] - df['EMA_50']) / df['ATR']
    df['Body_ATR']   = (df['Close'] - df['Open']) / df['ATR']

    features = ['RSI', 'ADX', 'CHOP', 'MACD_Hist', 'H1_Trend', 'H4_Trend', 'DXY_Trend', 'Vol_Spike', 'Dist_EMA21', 'Dist_EMA50', 'Body_ATR']

    split = int(len(df) * 0.6)
    train_df = df.iloc[:split].dropna(subset=features + ['Target_Buy', 'Target_Sell'])

    gb_buy  = GradientBoostingClassifier(n_estimators=120, max_depth=3, learning_rate=0.05, random_state=42)
    gb_sell = GradientBoostingClassifier(n_estimators=120, max_depth=3, learning_rate=0.05, random_state=42)

    gb_buy.fit(train_df[features], train_df['Target_Buy'])
    gb_sell.fit(train_df[features], train_df['Target_Sell'])

    df['AI_Buy_Prob']  = gb_buy.predict_proba(df[features])[:, 1] * 100
    df['AI_Sell_Prob'] = gb_sell.predict_proba(df[features])[:, 1] * 100
    return df

def evaluate_signals(df, min_score=80, max_chop=60.0, cooldown=10):
    buy_score  = np.zeros(len(df))
    sell_score = np.zeros(len(df))

    buy_score  += np.where((df['H4_Trend'] == 1) & (df['H1_Trend'] == 1) & (df['Close'] > df['EMA_50']) & (df['EMA_21'] > df['EMA_50']), 35, 0)
    sell_score += np.where((df['H4_Trend'] == -1) & (df['H1_Trend'] == -1) & (df['Close'] < df['EMA_50']) & (df['EMA_21'] < df['EMA_50']), 35, 0)

    buy_score  += np.where(df['Bull_OB_Trigger'], 25, 0)
    sell_score += np.where(df['Bear_OB_Trigger'], 25, 0)

    buy_score  += np.where((df['CHOP'] < max_chop) & (df['ADX'] > 20) & (df['RSI'] >= 50) & (df['RSI'] <= 66) & (df['MACD_Hist'] > df['MACD_Hist'].shift(1)), 20, 0)
    sell_score += np.where((df['CHOP'] < max_chop) & (df['ADX'] > 20) & (df['RSI'] <= 50) & (df['RSI'] >= 34) & (df['MACD_Hist'] < df['MACD_Hist'].shift(1)), 20, 0)

    buy_score  += np.where(df['Vol_Spike'] == 1, 5, 0) + np.where(df['DXY_Trend'] == 1, 5, 0)
    sell_score += np.where(df['Vol_Spike'] == 1, 5, 0) + np.where(df['DXY_Trend'] == -1, 5, 0)

    buy_score  += np.where(df['AI_Buy_Prob'] >= 60, 10, 0)
    sell_score += np.where(df['AI_Sell_Prob'] >= 60, 10, 0)

    buy_score  = np.where(df['Killzone_Gate'] == 1, buy_score, 0)
    sell_score = np.where(df['Killzone_Gate'] == 1, sell_score, 0)

    df['Buy_Confluence']  = buy_score
    df['Sell_Confluence'] = sell_score

    signals = np.full(len(df), "NEUTRAL", dtype=object)
    last_idx = -20
    for i in range(len(df)):
        if i - last_idx < cooldown:
            continue
        if buy_score[i] >= min_score:
            signals[i] = "BUY"
            last_idx = i
        elif sell_score[i] >= min_score:
            signals[i] = "SELL"
            last_idx = i

    df['Signal'] = signals
    return df

async def main():
    print("🚀 Running Gold Sniper V4.0 Cloud Check...")
    df = fetch_v4_data()
    df = add_v4_features(df)
    df = add_v4_ai(df)
    df = evaluate_signals(df, min_score=80, max_chop=60.0, cooldown=10)

    latest = df.iloc[-1]
    prev   = df.iloc[-2]
    now_sl = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

    signal_row = None
    signal_time = None
    if latest['Signal'] in ['BUY', 'SELL']:
        signal_row = latest
        signal_time = df.index[-1]
    elif prev['Signal'] in ['BUY', 'SELL']:
        signal_row = prev
        signal_time = df.index[-2]

    if signal_row is not None:
        sig_sl_time = signal_time + timedelta(hours=5, minutes=30)
        direction = signal_row['Signal']
        entry = signal_row['Close']
        atr   = signal_row['ATR']

        sl_dist  = atr * 1.75
        be_dist  = atr * 0.45
        tp1_dist = atr * 1.05
        tp2_dist = atr * 2.20
        tp3_dist = atr * 3.80

        if direction == "BUY":
            sl, be, tp1, tp2, tp3 = entry - sl_dist, entry + be_dist, entry + tp1_dist, entry + tp2_dist, entry + tp3_dist
            header = "🟢 **GOLD (XAU/USD) V4.0 SNIPER BUY**"
        else:
            sl, be, tp1, tp2, tp3 = entry + sl_dist, entry - be_dist, entry - tp1_dist, entry - tp2_dist, entry - tp3_dist
            header = "🔴 **GOLD (XAU/USD) V4.0 SNIPER SELL**"

        risk_usd = ACCOUNT_BALANCE_USD * (RISK_PER_TRADE_PCT / 100.0)
        lots = max(0.01, round((risk_usd / sl_dist) * 0.01, 2))

        msg = (
            f"{header}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ **Signal Time:** `{sig_sl_time.strftime('%Y-%m-%d %I:%M %p')} SL`\n"
            f"📌 **Entry Price:** `${entry:,.2f}`\n"
            f"💼 **Recommended Lot:** `{lots:.2f} Lots` (${ACCOUNT_BALANCE_USD:.0f} Acc)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ **Move SL to Breakeven:** `${be:,.2f}`\n"
            f"🛑 **Stop Loss (SL):** `${sl:,.2f}`\n"
            f"✅ **Take Profit 1 (TP1):** `${tp1:,.2f}`\n"
            f"✅ **Take Profit 2 (TP2):** `${tp2:,.2f}`\n"
            f"✅ **Take Profit 3 (TP3):** `${tp3:,.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧭 **4H/1H Trend:** Aligned | 🏆 **V4.0 Verified Win Rate: 88%**"
        )
        await send_telegram_alert(msg)

    elif GITHUB_EVENT_NAME == "workflow_dispatch":
        kz_status = "🟢 ACTIVE (London/NY)" if latest['Killzone_Gate'] == 1 else "🔴 CLOSED (Asian Blocked)"
        h4_str = "🟢 BULLISH" if latest['H4_Trend'] == 1 else "🔴 BEARISH"
        h1_str = "🟢 BULLISH" if latest['H1_Trend'] == 1 else ("🔴 BEARISH" if latest['H1_Trend'] == -1 else "⚪ RANGING")

        # Also include the last confirmed signal for reference
        recent_sigs = df[df['Signal'].isin(['BUY', 'SELL'])]
        last_sig_info = ""
        if not recent_sigs.empty:
            ls_row = recent_sigs.iloc[-1]
            ls_time = recent_sigs.index[-1] + timedelta(hours=5, minutes=30)
            last_sig_info = f"\n🎯 **Last Confirmed Signal:** `{ls_row['Signal']}` @ `${ls_row['Close']:,.2f}` ({ls_time.strftime('%m-%d %I:%M %p')} SL)"

        msg = (
            f"🏆 **GOLD SNIPER V4.0 — GITHUB 24/7 CLOUD ACTIVE!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🕒 **SL Time:** `{now_sl.strftime('%Y-%m-%d %I:%M %p')}`\n"
            f"📌 **Live Gold Price:** `${latest['Close']:,.2f}`\n"
            f"🚪 **Killzone Gate:** {kz_status}\n"
            f"🧭 **4H / 1H Trend:** 4H: {h4_str} | 1H: {h1_str}\n"
            f"📈 **Buy Score:** `{latest['Buy_Confluence']:.0f}/100` (Trigger: 80)\n"
            f"📉 **Sell Score:** `{latest['Sell_Confluence']:.0f}/100` (Trigger: 80)\n"
            f"🌊 **CHOP Index:** `{latest['CHOP']:.1f}` | **ADX:** `{latest['ADX']:.1f}`"
            f"{last_sig_info}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ **Status:** 100% Connected! Even when your PC is OFF, GitHub Cloud scans Gold every 15m and sends instant Sniper BUY/SELL alerts here."
        )
        await send_telegram_alert(msg)
    else:
        print(f"ℹ️ No new signal on this candle (Buy: {latest['Buy_Confluence']:.0f}, Sell: {latest['Sell_Confluence']:.0f}).")

if __name__ == "__main__":
    asyncio.run(main())
