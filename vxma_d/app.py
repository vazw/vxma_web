import asyncio
import logging
import os
import sqlite3
import time
import warnings
from datetime import datetime as dt
from uuid import uuid4

import bcrypt
import ccxt.async_support as ccxt
import mplfinance as mplf
import pandas as pd
from line_notify import LineNotify

from appdata import risk_manage, ta_table
from vxmatalib import benchmarking as ta_score
from vxmatalib import vxma as ta

launch_uid = uuid4()
pd.set_option("display.max_rows", None)
warnings.filterwarnings("ignore")


logging.basicConfig(
    filename="log.log", format="%(asctime)s - %(message)s", level=logging.INFO
)

rcs = {
    "axes.labelcolor": "none",
    "axes.spines.left": False,
    "axes.spines.right": False,
    "axes.axisbelow": False,
    "axes.grid": True,
    "grid.linestyle": ":",
    "axes.titlesize": "xx-large",
    "axes.titleweight": "bold",
}

# Bot setting
insession = dict(name=False, day=False, hour=False)
# STAT setting
barsC = 1502
msg = ""
# timframe dicts and collum
TIMEFRAMES = [
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1M",
]
TIMEFRAMES_DICT = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
    "3d": "3d",
    "1w": "1w",
    "1M": "1M",
}


def bot_setting():
    symbolist = pd.read_csv("bot_config.csv")
    return symbolist


def config_setting():
    with sqlite3.connect("vxma.db", check_same_thread=False) as con:
        config = pd.read_sql("SELECT * FROM key", con=con)
    return config


def get_config():
    global BNBCZ, notify, min_balance, max_margin, MIN_BALANCE
    config = config_setting()
    if config.empty:
        API_KEY = ""
        API_SECRET = ""
        LINE_TOKEN = ""
        max_margin = "$10"
        MIN_BALANCE = "$50"
    else:
        max_margin = str(config["freeB"][0])
        MIN_BALANCE = str(config["minB"][0])
        API_KEY = str(config["apikey"][0])
        API_SECRET = str(config["apisec"][0])
        LINE_TOKEN = str(config["notify"][0])
    if MIN_BALANCE[0] == "$":
        min_balance = float(MIN_BALANCE[1 : len(MIN_BALANCE)])
    else:
        min_balance = float(MIN_BALANCE)
    if max_margin[0] == "$":
        max_margin = float(max_margin[1 : len(max_margin)])
    else:
        max_margin = float(max_margin)
    if "API_KEY" in os.environ:
        API_KEY = str(os.environ["API_KEY"])
        API_SECRET = str(os.environ["API_SECRET"])
        LINE_TOKEN = str(os.environ["Line_Notify_Token"])
    notify = LineNotify(LINE_TOKEN)
    BNBCZ = {
        "apiKey": "",
        "secret": "",
        "options": {"defaultType": "future"},
        "enableRateLimit": True,
        "adjustForTimeDifference": True,
    }
    return


get_config()


def cooking(id, pwd):
    pepper = f"{id}{pwd}!{barsC}vz{id}"
    bytePwd = pepper.encode("utf-8")
    Salt = bcrypt.gensalt(rounds=12)
    cook = bcrypt.hashpw(bytePwd, Salt)
    return cook


def perf(id, pwd):
    hash1 = "X"
    with sqlite3.connect("vxma.db", check_same_thread=False) as con:
        bata = pd.read_sql("SELECT * FROM user", con=con)
    iid = bata["id"][0]
    if iid == id:
        hash1 = bata["pass"][0]
    egg = f"{id}{pwd}!{barsC}vz{id}"
    bytePwd = egg.encode("utf-8")
    proof = bcrypt.checkpw(bytePwd, hash1)
    return proof


def callbackRate(data):
    m = len(data.index)
    try:
        highest = data["highest"][m - 1]
        lowest = data["lowest"][m - 1]
        rate = round((highest - lowest) / highest * 100, 1)
        if rate > 5:
            rate = 5
        elif rate < 0.1:
            rate = 0.1
        return rate
    except Exception as e:
        print(f"callbackRate is error : {e}")
        return 2.5


async def connect():
    exchange = ccxt.binance(BNBCZ)
    return exchange


async def disconnect(exchange):
    return await exchange.close()


color = mplf.make_marketcolors(
    up="white", down="black", wick="black", edge="black"
)
s = mplf.make_mpf_style(
    rc=rcs,
    y_on_right=True,
    marketcolors=color,
    figcolor="white",
    gridaxis="horizontal",
)


def candle(df, symbol, tf):
    data = df.tail(60)
    titles = f"{symbol}_{tf}"
    try:
        vxma = mplf.make_addplot(
            data.vxma, secondary_y=False, color="blue", linewidths=0.2
        )
        buy = mplf.make_addplot(
            data.buyPrice, secondary_y=False, color="green", scatter=True
        )
        sell = mplf.make_addplot(
            data.sellPrice, secondary_y=False, color="red", scatter=True
        )
        mplf.plot(
            data,
            type="candle",
            title=titles,
            addplot=[vxma, buy, sell],
            style=s,
            volume=True,
            savefig="candle.png",
            tight_layout=True,
            figratio=(9, 9),
            datetime_format="%y/%b/%d %H:%M",
            xrotation=20,
        )
    except Exception as e:
        print(f"{e}")
        mplf.plot(
            data,
            type="candle",
            title=titles,
            style=s,
            volume=True,
            savefig="candle.png",
            tight_layout=True,
            figratio=(9, 9),
            datetime_format="%y/%b/%d %H:%M",
            xrotation=20,
        )
    notify.send(f"info : {titles}", image_path=("./candle.png"))
    asyncio.sleep(0.5)
    return


async def get_symbol():
    symbols = pd.DataFrame()
    get_config()
    symbolist = bot_setting()
    print("fecthing Symbol of Top 10 Volume...")
    exchange = await connect()
    try:
        market = await exchange.fetch_tickers(params={"type": "future"})
    except Exception as e:
        print(e)
        await disconnect(exchange)
        await asyncio.sleep(10)
        logging.info(e)
        exchange = await connect()
        market = await exchange.fetch_tickers(params={"type": "future"})
    await disconnect(exchange)
    for x, y in market.items():
        if y["symbol"][len(y["symbol"]) - 4 : len(y["symbol"])] == "USDT":
            symbols = symbols.append(y, ignore_index=True)
    symbols = symbols.set_index("symbol")
    symbols["datetime"] = pd.to_datetime(
        symbols["timestamp"], unit="ms", utc=True
    ).map(lambda x: x.tz_convert("Asia/Bangkok"))
    symbols = symbols.sort_values(by=["quoteVolume"], ascending=False)
    symbols.drop(["timestamp", "high", "low", "average"], axis=1, inplace=True)
    symbols.drop(
        ["bid", "bidVolume", "ask", "askVolume"], axis=1, inplace=True
    )
    symbols.drop(["vwap", "open", "baseVolume", "info"], axis=1, inplace=True)
    symbols.drop(["close", "previousClose", "datetime"], axis=1, inplace=True)
    symbols = symbols.head(10)
    newsym = []
    if len(symbolist.index) > 0:
        for i in range(len(symbolist.index)):
            newsym.append(symbolist["symbol"][i])
    for symbol in symbols.index:
        newsym.append(symbol)
    newsym = list(dict.fromkeys(newsym))
    print(f"Interested : {newsym}")
    return newsym


# pass
async def fetchbars(symbol, timeframe):
    mess = symbol, timeframe, dt.now().isoformat()
    print(f"Benchmarking new bars for {mess}")
    exchange = await connect()
    try:
        bars = await exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, since=None, limit=barsC
        )
    except Exception as e:
        print(e)
        await disconnect(exchange)
        await asyncio.sleep(10)
        logging.info(e)
        exchange = await connect()
        bars = await exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, since=None, limit=barsC
        )
    await disconnect(exchange)
    df = pd.DataFrame(
        bars[:-1],
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).map(
        lambda x: x.tz_convert("Asia/Bangkok")
    )
    df = df.set_index("timestamp")
    return df


# set leverage pass
async def setleverage(symbol, lev, exchange):
    try:
        await exchange.set_leverage(lev, symbol)
    except Exception as e:
        print(e)
        await disconnect(exchange)
        await asyncio.sleep(10)
        logging.info(e)
        exchange = await connect()
    lever = await exchange.fetch_positions_risk([symbol])
    for x in range(len(lever)):
        if (lever[x]["symbol"]) == symbol:
            lev = round(lever[x]["leverage"], 0)
            print(lev)
            await exchange.set_leverage(int(lev), symbol)
            break
    return round(int(lev), 0)


# Position Sizing
def buysize(df, balance, symbol, exchange, RISK):
    last = len(df.index) - 1
    freeusd = float(balance["free"]["USDT"])
    low = float(df["Lowest"][last])
    if RISK[0] == "$":
        risk = float(RISK[1 : len(RISK)])
    elif RISK[0] == "%":
        percent = float(RISK)
        risk = (percent / 100) * freeusd
    else:
        risk = float(RISK)
    amount = abs(risk / (df["close"][last] - low))
    qty_precision = exchange.amount_to_precision(symbol, amount)
    lot = qty_precision
    return float(lot)


def sellsize(df, balance, symbol, exchange, RISK):
    last = len(df.index) - 1
    freeusd = float(balance["free"]["USDT"])
    high = float(df["Highest"][last])
    if RISK[0] == "$":
        risk = float(RISK[1 : len(RISK)])
    elif RISK[0] == "%":
        percent = float(RISK)
        risk = (percent / 100) * freeusd
    else:
        risk = float(RISK)
    amount = abs(risk / (high - df["close"][last]))
    qty_precision = exchange.amount_to_precision(symbol, amount)
    lot = qty_precision
    return float(lot)


# TP with Risk:Reward
def RRTP(df, direction, step, price, TPRR1, TPRR2):
    m = len(df.index)
    if direction:
        low = float(df["Lowest"][m - 1])
        if step == 1:
            target = price * (1 + ((price - low) / price) * float(TPRR1))
            return float(target)
        if step == 2:
            target = price * (1 + ((price - low) / price) * float(TPRR2))
            return float(target)
    else:
        high = float(df["Highest"][m - 1])
        if step == 1:
            target = price * (1 - ((high - price) / price) * float(TPRR1))
            return float(target)
        if step == 2:
            target = price * (1 - ((high - price) / price) * float(TPRR2))
            return float(target)


def RR1(df, side, price):
    m = len(df.index)
    if side == "buy":
        low = df["Lowest"][m - 1]
        target = price * (1 + ((price - float(low)) / price) * 1)
        return target
    elif side == "sell":
        high = df["Highest"][m - 1]
        target = price * (1 - ((float(high) - price) / price) * 1)
        return target
    else:
        return -1


async def USESLSHORT(
    df, symbol, exchange, bid, amount, high, Sside, Tailing_SL, currentMODE
):
    try:
        if currentMODE["dualSidePosition"]:
            orderSL = await exchange.create_order(
                symbol,
                "stop",
                "buy",
                amount,
                float(high),
                params={
                    "stopPrice": float(high),
                    "triggerPrice": float(high),
                    "positionSide": Sside,
                },
            )
            if Tailing_SL:
                ordertailingSL = await exchange.create_order(
                    symbol,
                    "TRAILING_STOP_MARKET",
                    "buy",
                    amount,
                    params={
                        "activationPrice": float(RR1(df, False, bid)),
                        "callbackRate": float(callbackRate(df)),
                        "positionSide": Sside,
                    },
                )
                logging.info(ordertailingSL)
        else:
            orderSL = await exchange.create_order(
                symbol,
                "stop",
                "buy",
                amount,
                float(high),
                params={
                    "stopPrice": float(high),
                    "triggerPrice": float(high),
                    "reduceOnly": True,
                    "positionSide": Sside,
                },
            )
            if Tailing_SL:
                ordertailingSL = await exchange.create_order(
                    symbol,
                    "TRAILING_STOP_MARKET",
                    "buy",
                    amount,
                    params={
                        "activationPrice": float(RR1(df, False, bid)),
                        "callbackRate": float(callbackRate(df)),
                        "reduceOnly": True,
                        "positionSide": Sside,
                    },
                )
                logging.info(ordertailingSL)
        logging.info(orderSL)
        return
    except Exception as e:
        print(e)
        notify.send(
            "เกิดเตุการณืไม่คาดฝัน Order Stop Loss", f"ทำรายการไม่สำเร็จ {e}"
        )
        logging.info(e)
    return


async def USESLLONG(
    df, symbol, exchange, ask, amount, low, side, Tailing_SL, currentMODE
):
    try:
        if currentMODE["dualSidePosition"]:
            orderSL = await exchange.create_order(
                symbol,
                "stop",
                "sell",
                amount,
                float(low),
                params={
                    "stopPrice": float(low),
                    "triggerPrice": float(low),
                    "positionSide": side,
                },
            )
            if Tailing_SL:
                triggerPrice = RR1(df, side, ask)
                if triggerPrice == -1:
                    return
                else:
                    callbackrate = callbackRate(df)
                    ordertailingSL = await exchange.create_order(
                        symbol,
                        "TRAILING_STOP_MARKET",
                        "sell",
                        amount,
                        params={
                            "activationPrice": triggerPrice,
                            "callbackRate": callbackrate,
                            "positionSide": side,
                        },
                    )
                    logging.info(ordertailingSL)
        else:
            orderSL = await exchange.create_order(
                symbol,
                "stop",
                "sell",
                amount,
                float(low),
                params={
                    "stopPrice": float(low),
                    "triggerPrice": float(low),
                    "reduceOnly": True,
                    "positionSide": side,
                },
            )
            if Tailing_SL:
                triggerPrice = RR1(df, side, ask)
                if triggerPrice == -1:
                    return
                else:
                    callbackrate = callbackRate(df)
                    ordertailingSL = await exchange.create_order(
                        symbol,
                        "TRAILING_STOP_MARKET",
                        "sell",
                        amount,
                        params={
                            "activationPrice": triggerPrice,
                            "callbackRate": callbackrate,
                            "positionSide": side,
                        },
                    )
                    logging.info(ordertailingSL)
        logging.info(orderSL)
        return
    except Exception as e:
        print(e)
        notify.send("เกิดเตุการณืไม่คาดฝัน Order Stop Loss ทำรายการไม่สำเร็จ")
        logging.info(e)
    return


async def USETPLONG(
    symbol, df, exchange, ask, TPRR1, TPRR2, Lside, amttp1, amttp2, USETP2
):
    try:
        stop_price = RRTP(df, True, 1, ask, TPRR1, TPRR2)
        orderTP = await exchange.create_ordee(
            symbol,
            "TAKE_PROFIT_MARKET",
            "sell",
            amttp1,
            stop_price,
            params={
                "stopPrice": stop_price,
                "triggerPrice": stop_price,
                "positionSide": Lside,
            },
        )
        logging.info(orderTP)
        if USETP2:
            triggerPrice = RRTP(df, True, 2, ask, TPRR1, TPRR2)
            orderTP2 = await exchange.create_order(
                symbol,
                "TAKE_PROFIT_MARKET",
                "sell",
                amttp2,
                triggerPrice,
                params={
                    "stopPrice": triggerPrice,
                    "triggerPrice": triggerPrice,
                    "positionSide": Lside,
                },
            )
            logging.info(orderTP2)
        return
    except Exception as e:
        print(e)
        notify.send("เกิดเตุการณืไม่คาดฝัน Order TP  ทำรายการไม่สำเร็จ")
        logging.info(e)
    return


# OpenLong=Buy
async def OpenLong(
    df,
    balance,
    risk_manage,
    exchange,
    currentMODE,
    Lside,
):
    try:
        amount = buysize(
            df, balance, risk_manage.symbol, exchange, risk_manage.RISK
        )
        try:
            info = (await exchange.fetch_bids_asks([risk_manage.symbol]))[
                risk_manage.symbol
            ]["info"]
        except Exception as e:
            print(e)
            await disconnect(exchange)
            await asyncio.sleep(10)
            exchange = await connect()
            info = (await exchange.fetch_bids_asks([risk_manage.symbol]))[
                risk_manage.symbol
            ]["info"]
        ask = float(info["askPrice"])
        print(f"price : {ask}")
        logging.info(
            f"Entry Long {risk_manage.symbol} Long @{ask} qmt:{amount}"
        )
        leve = await setleverage(risk_manage.symbol, risk_manage.lev, exchange)
        if amount * ask > risk_manage.Max_Size * int(leve):
            amount = risk_manage.Max_Size * int(leve) / ask
        free = float(balance["free"]["USDT"])
        amttp1 = amount * (risk_manage.TPPer / 100)
        amttp2 = amount * (risk_manage.TPPer2 / 100)
        low = df["lowest"][len(df.index) - 1]
        if free > min_balance:
            try:
                order = await exchange.create_market_order(
                    risk_manage.symbol,
                    "buy",
                    amount,
                    params={"positionSide": Lside},
                )
                logging.info(order)
            except ccxt.InsufficientFunds as e:
                logging.debug(e)
                notify.send(e)
                return
            if risk_manage.USETP:
                await USETPLONG(
                    risk_manage.symbol,
                    df,
                    exchange,
                    ask,
                    risk_manage.TPRR1,
                    risk_manage.TPRR2,
                    Lside,
                    amttp1,
                    amttp2,
                    risk_manage.USETP2,
                )
            if risk_manage.USESL:
                await USESLLONG(
                    df,
                    risk_manage.symbol,
                    exchange,
                    ask,
                    amount,
                    low,
                    Lside,
                    risk_manage.Tailing_SL,
                    currentMODE,
                )
            await asyncio.sleep(1)
            margin = ask * amount / int(leve)
            total = float(balance["total"]["USDT"])
            msg = (
                "BINANCE:"
                + f"\nCoin        : {risk_manage.symbol}"
                + "\nStatus      : OpenShort[SELL]"
                + f"\nAmount      : {amount}({round((amount * ask), 2)}USDT)"
                + f"\nPrice       : {ask}USDT"
                + f"\nmargin      : {round(margin, 2)}USDT"
                + f"\nBalance     : {round(total, 2)}USDT"
            )
        else:
            msg = (
                f"MARGIN-CALL!!!\nยอดเงินต่ำกว่าที่กำหนดไว้ :{min_balance}USD"
                + f"\nยอดปัจจุบัน  {round(free, 2)}"
                + " USD\nบอทจะทำการยกเลิกการเข้า Position ทั้งหมด"
            )
        notify.send(msg)
        candle(df, risk_manage.symbol, risk_manage.tf)
        return
    except Exception as e:
        print(e)
        logging.info(e)
        notify.send(f"เกิดความผิดพลาดในการเข้า Order {e}")
    return


async def USETPSHORT(
    symbol, df, exchange, bid, TPRR1, TPRR2, Sside, amttp1, amttp2, USETP2
):
    try:
        triggerPrice = RRTP(df, False, 1, bid, TPRR1, TPRR2)
        orderTP = await exchange.create_order(
            symbol,
            "TAKE_PROFIT_MARKET",
            "buy",
            amttp1,
            triggerPrice,
            params={
                "stopPrice": triggerPrice,
                "triggerPrice": triggerPrice,
                "positionSide": Sside,
            },
        )
        logging.info(orderTP)
        if USETP2:
            triggerPrice = RRTP(df, False, 2, bid, TPRR1, TPRR2)
            orderTP2 = await exchange.create_order(
                symbol,
                "TAKE_PROFIT_MARKET",
                "buy",
                amttp2,
                triggerPrice,
                params={
                    "stopPrice": triggerPrice,
                    "triggerPrice": triggerPrice,
                    "positionSide": Sside,
                },
            )
            logging.info(orderTP2)
        return
    except Exception as e:
        print(e)
        notify.send("เกิดเตุการณืไม่คาดฝัน Order TP  ทำรายการไม่สำเร็จ")
        logging.info(e)
    return


# OpenShort=Sell
async def OpenShort(
    df,
    balance,
    risk_manage,
    exchange,
    currentMODE,
    Sside,
):
    try:
        amount = sellsize(
            df, balance, risk_manage.symbol, exchange, risk_manage.RISK
        )
        try:
            info = (await exchange.fetch_bids_asks([risk_manage.symbol]))[
                risk_manage.symbol
            ]["info"]
        except Exception as e:
            print(e)
            await disconnect(exchange)
            await asyncio.sleep(10)
            exchange = await connect()
            info = (await exchange.fetch_bids_asks([risk_manage.symbol]))[
                risk_manage.symbol
            ]["info"]
        bid = float(info["bidPrice"])
        logging.info(
            f"Entry Short {risk_manage.symbol} Short @{bid} qmt:{amount}"
        )
        leve = await setleverage(risk_manage.symbol, risk_manage.lev, exchange)
        if amount * bid > risk_manage.Max_Size * int(leve):
            amount = risk_manage.Max_Size * int(leve) / bid
        free = float(balance["free"]["USDT"])
        amttp1 = amount * (risk_manage.TPPer / 100)
        amttp2 = amount * (risk_manage.TPPer2 / 100)
        high = df["Highest"][len(df.index) - 1]
        if free > min_balance:
            try:
                order = await exchange.create_market_order(
                    risk_manage.symbol,
                    "sell",
                    amount,
                    params={"positionSide": Sside},
                )
                logging.info(order)
            except ccxt.InsufficientFunds as e:
                logging.debug(e)
                notify.send(e)
                return
            if risk_manage.USESL:
                await USESLSHORT(
                    df,
                    risk_manage.symbol,
                    exchange,
                    bid,
                    amount,
                    high,
                    Sside,
                    risk_manage.Tailing_SL,
                    currentMODE,
                )
            if risk_manage.USETP:
                await USETPSHORT(
                    risk_manage.symbol,
                    df,
                    exchange,
                    bid,
                    risk_manage.TPRR1,
                    risk_manage.TPRR2,
                    Sside,
                    amttp1,
                    amttp2,
                    risk_manage.USETP2,
                )
            time.sleep(1)
            margin = bid * amount / int(leve)
            total = float(balance["total"]["USDT"])
            msg = (
                "BINANCE:"
                + f"\nCoin        : {risk_manage.symbol}"
                + "\nStatus      : OpenShort[SELL]"
                + f"\nAmount      : {amount}({round((amount * bid), 2)}USDT)"
                + f"\nPrice       : {bid}USDT"
                + f"\nmargin      : {round(margin, 2)}USDT"
                + f"\nBalance     : {round(total, 2)}USDT"
            )
        else:
            msg = (
                f"MARGIN-CALL!!!\nยอดเงินต่ำกว่าที่กำหนดไว้ :{min_balance}USD"
                + f"\nยอดปัจจุบัน  {round(free, 2)}"
                + " USD\nบอทจะทำการยกเลิกการเข้า Position ทั้งหมด"
            )
        notify.send(msg)
        candle(df, risk_manage.symbol, risk_manage.tf)
    except Exception as e:
        print(e)
        logging.info(e)
        notify.send("เกิดความผิดพลาดในการเข้า Order")
    return


# CloseLong=Sell
async def CloseLong(df, balance, symbol, amt, pnl, exchange, Lside, tf):
    try:
        amount = abs(amt)
        upnl = pnl
        try:
            response = await exchange.fetch_bids_asks([symbol])
            info = response[symbol]["info"]
        except Exception as e:
            print(e)
            logging.info(e)
            await disconnect(exchange)
            await asyncio.sleep(10)
            exchange = await connect()
            response = await exchange.fetch_bids_asks([symbol])
            info = response[symbol]["info"]
        bid = float(info["bidPrice"])
        logging.info(f"Close Long {symbol} @{bid} qmt:{amount}")
        try:
            order = await exchange.create_market_order(
                symbol, "sell", amount, params={"positionSide": Lside}
            )
        except Exception as e:
            print(e)
            await disconnect(exchange)
            await asyncio.sleep(10)
            logging.info(e)
            exchange = await connect()
            order = await exchange.create_market_order(
                symbol, "sell", amount, params={"positionSide": Lside}
            )
        logging.info(order)
        total = float(balance["total"]["USDT"])
        msg = (
            "BINANCE:\n"
            + f"Coin        : {symbol}\n"
            + "Status      : CloseLong[SELL]\n"
            + f"Amount      : {str(amount)}({round((amount * bid), 2)}USDT)\n"
            + f"Price       : {bid} USDT\n"
            + f"Realized P/L:  {round(upnl, 2)}USDT\n"
            + f"Balance     : {round(total, 2)}USDT"
        )
        notify.send(msg)
        candle(df, symbol, tf)
    except Exception as e:
        print(e)
        notify.send(f"เกิดความผิดพลาดในการออก Order {e}")
    return


# CloseShort=Buy
async def CloseShort(df, balance, symbol, amt, pnl, exchange, Sside, tf):
    try:
        amount = abs(amt)
        upnl = pnl
        try:
            info = (await exchange.fetch_bids_asks([symbol]))[symbol]["info"]
        except Exception as e:
            print(e)
            await disconnect(exchange)
            await asyncio.sleep(10)
            logging.info(e)
            exchange = await connect()
            info = (await exchange.fetch_bids_asks([symbol]))[symbol]["info"]
        ask = float(info["askPrice"])
        logging.info(f"Close Short {symbol}  @{ask} qmt:{amount}")
        try:
            order = await exchange.create_market_order(
                symbol, "buy", amount, params={"positionSide": Sside}
            )
        except Exception as e:
            print(e)
            await disconnect(exchange)
            await asyncio.sleep(10)
            logging.info(e)
            exchange = await connect()
            order = await exchange.create_market_order(
                symbol, "buy", amount, params={"positionSide": Sside}
            )
        logging.info(order)
        total = float(balance["total"]["USDT"])
        msg = (
            "BINANCE:\n"
            f"Coin        : {symbol}\n"
            "Status      : CloseLong[SELL]\n"
            f"Amount      : {str(amount)}({round((amount * ask), 2)}USDT)\n"
            f"Price       : {ask} USDT\n"
            f"Realized P/L:  {round(upnl, 2)}USDT\n"
            f"Balance     : {round(total, 2)}USDT"
        )
        notify.send(msg)
        candle(df, symbol, tf)
    except Exception as e:
        print(e)
        notify.send(f"เกิดความผิดพลาดในการออก Order {e}")
    return


async def bot_1(symbol, ta_data, tf):
    try:
        print("Bot 1 is running...")
        data1 = await fetchbars(symbol, tf)
        bot1 = ta(data1, ta_data)
        data1 = bot1.indicator()
        print("Bot 1 is Done!")
        return data1
    except Exception as e:
        print(e)
        pass


async def bot_2(symbol, ta_data, tf):
    try:
        print("Bot 2 is running...")
        data2 = await fetchbars(symbol, tf)
        bot2 = ta(data2, ta_data)
        data2 = bot2.indicator()
        print("Bot 2 is Done!")
        return data2
    except Exception as e:
        print(e)
        pass


async def bot_3(symbol, ta_data, tf):
    try:
        print("Bot 3 is running...")
        data3 = await fetchbars(symbol, tf)
        bot3 = ta(data3, ta_data)
        data3 = bot3.indicator()
        print("Bot 3 is Done!")
        return data3
    except Exception as e:
        print(e)
        pass


async def feed(df, risk_manage):
    is_in_Long = False
    is_in_Short = False
    is_in_position = False
    posim = risk_manage["symbol"].replace("/", "")
    exchange = await connect()
    try:
        balance = await exchange.fetch_balance()
    except Exception as e:
        print(e)
        await disconnect(exchange)
        await asyncio.sleep(10)
        logging.info(e)
        exchange = await connect()
        balance = await exchange.fetch_balance({"type": "future"})
    positions = balance["info"]["positions"]
    current_positions = [
        position
        for position in positions
        if float(position["positionAmt"]) != 0
    ]
    status = pd.DataFrame(
        current_positions,
        columns=[
            "symbol",
            "entryPrice",
            "positionSide",
            "unrealizedProfit",
            "positionAmt",
            "initialMargin",
            "leverage",
        ],
    )
    amt = 0.0
    upnl = 0.0
    margin = 0.0
    netunpl = 0.0
    for i in status.index:
        margin += float(status["initialMargin"][i])
        netunpl += float(status["unrealizedProfit"][i])
    print(f"Margin Used : {margin}")
    print(f"NET unrealizedProfit : {netunpl}")
    try:
        currentMODE = await exchange.fapiPrivate_get_positionside_dual()
    except Exception as e:
        print(e)
        await disconnect(exchange)
        await asyncio.sleep(10)
        logging.info(e)
        exchange = await connect()
        currentMODE = await exchange.fapiPrivate_get_positionside_dual()
    if margin > max_margin:
        notify.send(
            "Margin ที่ใช้สูงเกินไปแล้ว\nMargin : {margin}\n",
            f"ที่กำหนดไว้ : {max_margin}",
            sticker_id=17857,
            package_id=1070,
        )
    for i in status.index:
        if status["symbol"][i] == posim:
            amt = float(status["positionAmt"][i])
            upnl = float(status["unrealizedProfit"][i])
            break
    # NO Position
    if currentMODE["dualSidePosition"]:
        Sside = "SHORT"
        Lside = "LONG"
    else:
        Sside = "BOTH"
        Lside = "BOTH"
    if not status.empty and amt != 0.0:
        is_in_position = True
    # Long position
    if is_in_position and amt > 0.0:
        is_in_Long = True
        is_in_Short = False
    # Short position
    elif is_in_position and amt < 0.0:
        is_in_Short = True
        is_in_Long = False
    else:
        is_in_position = False
        is_in_Short = False
        is_in_Long = False
    last = len(df.index) - 1
    if df["BUY"][last] == 1:
        print("changed to Bullish, buy")
        if is_in_Short:
            print("closeshort")
            await CloseShort(
                df,
                balance,
                risk_manage.symbol,
                amt,
                upnl,
                exchange,
                Sside,
                risk_manage.tf,
            )
        elif not is_in_Long and risk_manage.USELONG:
            await exchange.cancel_all_orders(risk_manage.symbol)
            await OpenLong(
                df,
                balance,
                risk_manage,
                exchange,
                currentMODE,
                Lside,
            )
        else:
            print("already in position, nothing to do")
    if df["SELL"][last] == 1:
        print("changed to Bearish, Sell")
        if is_in_Long:
            print("closelong")
            await CloseLong(
                df,
                balance,
                risk_manage.symbol,
                amt,
                upnl,
                exchange,
                Lside,
                risk_manage.tf,
            )
        elif not is_in_Short and risk_manage.USESHORT:
            await exchange.cancel_all_orders(risk_manage.symbol)
            await OpenShort(
                df,
                balance,
                risk_manage,
                exchange,
                currentMODE,
                Sside,
            )
        else:
            print("already in position, nothing to do")
    await disconnect(exchange)


async def get_dailytasks():
    daycollum = ["Symbol", "LastPirce", "Long-Term", "Mid-Term", "Short-Term"]
    dfday = pd.DataFrame(columns=daycollum)
    symbolist = await get_symbol()
    ta_data = ta_table()
    for symbol in symbolist:
        try:
            df1, df2, df3 = await asyncio.gather(
                bot_1(symbol, ta_data, "1d"),
                bot_2(symbol, ta_data, "6h"),
                bot_3(symbol, ta_data, "1h"),
            )

            candle(df1, symbol, "1d")
            candle(df2, symbol, "6h")
            candle(df3, symbol, "1h")
            if df1 is not None:
                long_term = ta_score(df1)
                mid_term = ta_score(df2)
                short_term = ta_score(df3)
                dfday = dfday.append(
                    pd.Series(
                        [
                            symbol,
                            df3["close"][len(df1.index) - 1],
                            long_term.benchmarking(),
                            mid_term.benchmarking(),
                            short_term.benchmarking(),
                        ],
                        index=daycollum,
                    ),
                    ignore_index=True,
                )
            await asyncio.sleep(0.1)
        except Exception as e:
            print(e)
            logging.info(e)
            pass
    return dfday


async def dailyreport():
    data = await get_dailytasks()
    try:
        todays = str(data)
        logging.info(f"{todays}")
        data = data.set_index("Symbol")
        data.drop(["Mid-Term", "LastPirce"], axis=1, inplace=True)
        msg = str(data)
        notify.send(
            f"คู่เทรดที่น่าสนใจในวันนี้\n{msg}",
            sticker_id=1990,
            package_id=446,
        )
        exchange = await connect()
        try:
            balance = await exchange.fetch_balance()
        except Exception as e:
            print(e)
            await disconnect(exchange)
            await asyncio.sleep(10)
            logging.info(e)
            exchange = await connect()
            balance = await exchange.fetch_balance()
        positions = balance["info"]["positions"]
        current_positions = [
            position
            for position in positions
            if float(position["positionAmt"]) != 0
        ]
        status = pd.DataFrame(
            current_positions,
            columns=[
                "symbol",
                "entryPrice",
                "positionSide",
                "unrealizedProfit",
                "positionAmt",
                "initialMargin",
            ],
        )
        m = status.index
        margin = 0.0
        netunpl = 0.0
        for i in m:
            margin += float(status["initialMargin"][i])
            netunpl += float(status["unrealizedProfit"][i])
        print(f"Margin Used : {margin}")
        print(f"NET unrealizedProfit : {margin}")
        status = status.sort_values(by=["unrealizedProfit"], ascending=False)
        status = status.head(1)
        print(status)
        sim1 = status["symbol"][1]
        upnl = round(float(status["unrealizedProfit"][1]), 2)
        entryP = status["entryPrice"][1]
        metthod = status["positionSide"][1]
        msg2 = f"{sim1} {metthod} at {entryP} \nunrealizedProfit : {upnl}$"
        message = (
            f"Top Performance\n{msg2}\n-----\n"
            + f"Net Margin Used : {round(float(margin),2)}$"
            + f"\nNet unrealizedProfit : {round(float(netunpl),2)}$",
        )
        notify.send(
            message,
            sticker_id=1995,
            package_id=446,
        )
        await disconnect(exchange)
        return
    except Exception as e:
        notify.send(f"เกิดความผิดพลาดในส่วนของแจ้งเตือนรายวัน {e}")
        print(e)
        return


async def main():
    symbolist = bot_setting()
    get_config()
    seconds = time.time()
    local_time = time.ctime(seconds)
    if str(local_time[14:-9]) == "1":
        insession["day"] = False
        insession["hour"] = False
    if str(local_time[12:-9]) == "7:0" and not insession["day"]:
        insession["day"] = True
        insession["hour"] = True
        await asyncio.gather(dailyreport())
    if len(symbolist.index) > 0:
        exchange = await connect()

        try:
            balance = await exchange.fetch_balance()
        except Exception as e:
            print(e)
            await disconnect(exchange)
            await asyncio.sleep(2)
            logging.info(e)
            exchange = await connect()
            balance = await exchange.fetch_balance()
        if str(local_time[14:-9]) == "0" and not insession["hour"]:
            total = round(float(balance["total"]["USDT"]), 2)
            msg = f"Total Balance : {total} USDT"
            notify.send(msg, sticker_id=10863, package_id=789)
            insession["hour"] = True
        exchange.precisionMode = ccxt.DECIMAL_PLACES
        free_balance = float(balance["free"]["USDT"])
        await disconnect(exchange)
        for i in range(len(symbolist.index)):
            try:
                ta_table_data = ta_table(
                    symbolist["ATR"][i],
                    symbolist["ATR_m"][i],
                    symbolist["EMA"][i],
                    symbolist["subhag"][i],
                    symbolist["smooth"][i],
                    symbolist["RSI"][i],
                    symbolist["Andean"][i],
                    symbolist["Pivot"][i],
                )
                risk_manage_data = risk_manage(symbolist[i], free_balance)
                data = await fetchbars(
                    risk_manage_data.symbol, risk_manage_data.timeframe
                )
                bot = ta(data, ta_table_data)
                data = bot.indicator()
                await asyncio.gather(feed(data, risk_manage_data))
                await asyncio.sleep(5)
                print("Bot is running...")
            except Exception as e:
                print(e)
                pass
        await asyncio.sleep(30)
    else:
        await asyncio.sleep(59)
        print("Nothing to do now.....")


async def async_main():
    await asyncio.gather(main())


def run():
    while True:
        asyncio.run(async_main())


if __name__ == "__main__":
    run()
