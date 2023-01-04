import asyncio  # pyright: ignore # noqa:
import logging
from datetime import datetime as dt

import ccxt.async_support as ccxt
import pandas as pd

from vxma_d.AppData import currentMode, lastUpdate
from vxma_d.AppData.Appdata import AppConfig, bot_setting, candle, notify_send

barsC = 1502


def callbackRate(data):
    m = len(data.index)
    try:
        highest = data["highest"][m - 1]
        lowest = data["lowest"][m - 1]
        rate = round((highest - lowest) / highest * 100, 1)
        if rate > 5.0:
            return 5.0
        elif rate < 0.1:
            return 0.1
        else:
            return rate
    except Exception as e:
        logging.info(e)
        lastUpdate.status = f"callbackRate is error : {e}"
        return 2.5


# TP with Risk:Reward
def RRTP(df, direction, step, price, TPRR1, TPRR2):
    m = len(df.index)
    if direction:
        low = float(df["lowest"][m - 1])
        if step == 1:
            return price * (1 + ((price - low) / price) * float(TPRR1))
        if step == 2:
            return price * (1 + ((price - low) / price) * float(TPRR2))
    else:
        high = float(df["highest"][m - 1])
        if step == 1:
            return price * (1 - ((high - price) / price) * float(TPRR1))
        if step == 2:
            return price * (1 - ((high - price) / price) * float(TPRR2))


async def connect():
    config = AppConfig()
    exchange = ccxt.binance(config.BNBCZ)
    return exchange


async def connect_loads():
    config = AppConfig()
    exchange = ccxt.binance(config.BNBCZ)
    await exchange.load_markets(reload=True)
    return exchange


async def disconnect(exchange):
    return await exchange.close()


async def get_bidask(symbol, bidask="askPrice"):
    exchange = await connect()
    try:
        info = (await exchange.fetch_bids_asks([symbol]))[symbol]["info"]
        await disconnect(exchange)
        return float(info[bidask])
    except Exception as e:
        logging.info(e)
        lastUpdate.status = f"{e}"
        await disconnect(exchange)
        exchange = await connect()
        info = (await exchange.fetch_bids_asks([symbol]))[symbol]["info"]
        await disconnect(exchange)
        return float(info[bidask])


async def get_symbol():
    """
    get top 10 volume symbol of the day
    """
    symbols = pd.DataFrame()
    symbolist = bot_setting()
    lastUpdate.status = "fecthing Symbol of Top 10 Volume..."
    exchange = await connect()
    try:
        market = await exchange.fetch_tickers(params={"type": "future"})
    except Exception as e:
        lastUpdate.status = f"{e}"
        await disconnect(exchange)
        logging.info(e)
        exchange = await connect()
        market = await exchange.fetch_tickers(params={"type": "future"})
    await disconnect(exchange)
    for x, y in market.items():  # pyright: ignore
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


async def getAllsymbol():
    """
    Get all symbols
    """
    symbols = pd.DataFrame()
    symbolist = bot_setting()
    exchange = await connect()
    try:
        market = await exchange.fetch_tickers(params={"type": "future"})
    except Exception as e:
        lastUpdate.status = f"{e}"
        await disconnect(exchange)

        logging.info(e)
        exchange = await connect()
        market = await exchange.fetch_tickers(params={"type": "future"})
    await disconnect(exchange)
    for x, y in market.items():  # pyright: ignore
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
    newsym = []
    if not symbolist.empty:
        for i in range(len(symbolist.index)):
            newsym.append(symbolist["symbol"][i])
    for symbol in symbols.index:
        newsym.append(symbol)
    newsym = list(dict.fromkeys(newsym))
    return newsym


async def fetchbars(symbol, timeframe):
    """
    get candle from exchange
    """
    exchange = await connect()
    try:
        bars = await exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, since=None, limit=barsC
        )
    except Exception as e:
        lastUpdate.status = f"{e}"
        await disconnect(exchange)

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
    lastUpdate.candle = f"{dt.now().isoformat()}"
    return df


# set leverage pass
async def setleverage(symbol, lev):
    exchange = await connect_loads()
    try:
        await exchange.set_leverage(lev, symbol)
    except Exception as e:
        lastUpdate.status = f"{e}"
        await disconnect(exchange)
        logging.info(e)
        exchange = await connect_loads()
    lever = await exchange.fetch_positions_risk([symbol])
    for x in range(len(lever)):
        if (lever[x]["symbol"]) == symbol:
            lev = round(lever[x]["leverage"], 0)
            await exchange.set_leverage(int(lev), symbol)
            break
    await disconnect(exchange)
    return round(int(lev), 0)


def RR1(stop, side, price):
    if side:
        target = price * (1 + ((price - float(stop)) / price) * 1)
        return target
    elif not side:
        target = price * (1 - ((float(stop) - price) / price) * 1)
        return target
    else:
        return None


async def USESLSHORT(
    df, symbol, exchange, bid, amount, high, Sside, Tailing_SL
):
    try:
        if currentMode.dualSidePosition:
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
            msg = (
                "BINANCE:"
                + f"\nCoin        : {symbol}"
                + "\nStatus      : Order-StopLoss"
                + f"\nAmount      : {amount}"
                + f"\nPrice       : {high}USDT"
            )
            notify_send(msg)
            if Tailing_SL:
                triggerPrice = RR1(high, False, bid)
                if triggerPrice is None:
                    return
                callbackrate = callbackRate(df)
                ordertailingSL = await exchange.create_order(
                    symbol,
                    "TRAILING_STOP_MARKET",
                    "buy",
                    amount,
                    params={
                        "activationPrice": triggerPrice,
                        "callbackRate": callbackrate,
                        "positionSide": Sside,
                    },
                )
                msg2 = (
                    "BINANCE:"
                    + f"\nCoin        : {symbol}"
                    + "\nStatus      : Tailing-StopLoss"
                    + f"\nAmount      : {amount}"
                    + f"\nCallbackRate: {callbackrate}%"
                    + f"\ntriggerPrice: {triggerPrice}"
                )
                notify_send(msg2)
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
            msg = (
                "BINANCE:"
                + f"\nCoin        : {symbol}"
                + "\nStatus      : Order-StopLoss"
                + f"\nAmount      : {amount}"
                + f"\nPrice       : {high}USDT"
            )
            notify_send(msg)
            if Tailing_SL:
                triggerPrice = RR1(high, False, bid)
                if triggerPrice is None:
                    return
                callbackrate = callbackRate(df)
                ordertailingSL = await exchange.create_order(
                    symbol,
                    "TRAILING_STOP_MARKET",
                    "buy",
                    amount,
                    params={
                        "activationPrice": triggerPrice,
                        "callbackRate": callbackrate,
                        "reduceOnly": True,
                        "positionSide": Sside,
                    },
                )
                msg2 = (
                    "BINANCE:"
                    + f"\nCoin        : {symbol}"
                    + "\nStatus      : Tailing-StopLoss"
                    + f"\nAmount      : {amount}"
                    + f"\nCallbackRate: {callbackrate}%"
                    + f"\ntriggerPrice: {triggerPrice}"
                )
                notify_send(msg2)
                logging.info(ordertailingSL)
        logging.info(orderSL)
        return
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send(
            "เกิดเตุการณืไม่คาดฝัน Order Stop Loss" + f"ทำรายการไม่สำเร็จ {e}"
        )
        logging.info(e)
    return


async def USESLLONG(df, symbol, exchange, ask, amount, low, side, Tailing_SL):
    try:
        if currentMode.dualSidePosition:
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
            msg = (
                "BINANCE:"
                + f"\nCoin        : {symbol}"
                + "\nStatus      : Order-StopLoss"
                + f"\nAmount      : {amount}"
                + f"\nPrice       : {low}USDT"
            )
            notify_send(msg)
            if Tailing_SL:
                triggerPrice = RR1(low, True, ask)
                if triggerPrice is None:
                    return
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
                msg2 = (
                    "BINANCE:"
                    + f"\nCoin        : {symbol}"
                    + "\nStatus      : Tailing-StopLoss"
                    + f"\nAmount      : {amount}"
                    + f"\nCallbackRate: {callbackrate}%"
                    + f"\ntriggerPrice: {triggerPrice}"
                )
                notify_send(msg2)
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
            msg = (
                "BINANCE:"
                + f"\nCoin        : {symbol}"
                + "\nStatus      : Order-StopLoss"
                + f"\nAmount      : {amount}"
                + f"\nPrice       : {low}USDT"
            )
            notify_send(msg)
            if Tailing_SL:
                triggerPrice = RR1(low, True, ask)
                if triggerPrice is None:
                    return
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
                msg2 = (
                    "BINANCE:"
                    + f"\nCoin        : {symbol}"
                    + "\nStatus      : Tailing-StopLoss"
                    + f"\nAmount      : {amount}"
                    + f"\nCallbackRate: {callbackrate}%"
                    + f"\ntriggerPrice: {triggerPrice}"
                )
                notify_send(msg2)
                logging.info(ordertailingSL)
        logging.info(orderSL)
        return
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send("เกิดเตุการณืไม่คาดฝัน Order Stop Loss ทำรายการไม่สำเร็จ")
        logging.info(e)
    return


async def USETPLONG(
    symbol, df, exchange, ask, TPRR1, TPRR2, Lside, amttp1, amttp2, USETP2
):
    try:
        stop_price = RRTP(df, True, 1, ask, TPRR1, TPRR2)
        orderTP = await exchange.create_order(
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
        msg = (
            "BINANCE:"
            + f"\nCoin        : {symbol}"
            + "\nStatus      : Order-TP1"
            + f"\nAmount      : {amttp1}"
            + f"\nPrice       : {stop_price}USDT"
        )
        notify_send(msg)
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
            msg2 = (
                "BINANCE:"
                + f"\nCoin        : {symbol}"
                + "\nStatus      : Order-TP2"
                + f"\nAmount      : {amttp2}"
                + f"\nPrice       : {triggerPrice}"
            )
            notify_send(msg2)
            logging.info(orderTP2)
        return
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send("เกิดเตุการณืไม่คาดฝัน Order TP  ทำรายการไม่สำเร็จ")
        logging.info(e)
    return


async def fetching_balance():
    exchange = await connect()
    try:
        balance = await exchange.fetch_balance()
        await disconnect(exchange)
        return balance
    except Exception as e:
        lastUpdate.status = f"{e}"
        await disconnect(exchange)
        logging.info(e)
        exchange = await connect()
        balance = await exchange.fetch_balance()
        await disconnect(exchange)
        return balance


# Position Sizing
def buysize(df, balance, symbol, exchange, RISK):
    last = len(df.index) - 1
    freeusd = float(balance["free"]["USDT"])
    low = float(df["lowest"][last])
    if RISK[0] == "$":
        risk = float(RISK[1 : len(RISK)])
    elif RISK[0] == "%":
        percent = float(RISK)
        risk = (percent / 100) * freeusd
    else:
        risk = float(RISK)
    amount = abs(risk / (df["close"][last] - low))
    lot = exchange.amount_to_precision(symbol, amount)
    return float(lot)


def sellsize(df, balance, symbol, exchange, RISK):
    last = len(df.index) - 1
    freeusd = float(balance["free"]["USDT"])
    high = float(df["highest"][last])
    if RISK[0] == "$":
        risk = float(RISK[1 : len(RISK)])
    elif RISK[0] == "%":
        percent = float(RISK)
        risk = (percent / 100) * freeusd
    else:
        risk = float(RISK)
    amount = abs(risk / (high - df["close"][last]))
    lot = exchange.amount_to_precision(symbol, amount)
    return float(lot)


# OpenLong=Buy
async def OpenLong(df, balance, risk_manage, Lside, min_balance):
    try:
        exchange = await connect_loads()
        await exchange.cancel_all_orders(risk_manage["symbol"])
        amount = buysize(
            df,
            balance,
            risk_manage["symbol"],
            exchange,
            risk_manage["risk_size"],
        )
        markets = await exchange.fetchMarkets()
        min_amount = float(
            (
                data["limits"]["amount"]["min"]
                for data in markets
                if data["id"] == risk_manage["symbol"].replace("/", "")
            ).__next__()
        )
        if amount < min_amount:
            amount = min_amount
        ask = await get_bidask(risk_manage["symbol"], "askPrice")
        logging.info(
            f"Entry Long {risk_manage['symbol']} Long @{ask} qmt:{amount}"
        )
        leve = await setleverage(
            risk_manage["symbol"], risk_manage["leverage"]
        )
        if amount * ask > risk_manage["max_size"] * int(leve):
            new_lots = risk_manage["max_size"] * int(leve) / ask
            amount = float(
                exchange.amount_to_precision(risk_manage["symbol"], new_lots)
            )
        free = float(balance["free"]["USDT"])
        amttp1 = amount * (risk_manage["tp_percent"] / 100)
        amttp2 = amount * (risk_manage["tp_percent_2"] / 100)
        low = df["lowest"][len(df.index) - 1]
        if free > min_balance:
            try:
                order = await exchange.create_market_order(
                    risk_manage["symbol"],
                    "buy",
                    amount,
                    params={"positionSide": Lside},
                )
                logging.info(order)
            except ccxt.InsufficientFunds as e:
                logging.info(e)
                notify_send(e)
                return
            if risk_manage["use_tp_1"]:
                await USETPLONG(
                    risk_manage["symbol"],
                    df,
                    exchange,
                    ask,
                    risk_manage["risk_reward_1"],
                    risk_manage["risk_reward_2"],
                    Lside,
                    amttp1,
                    amttp2,
                    risk_manage["use_tp_2"],
                )
            if risk_manage["use_sl"]:
                await USESLLONG(
                    df,
                    risk_manage["symbol"],
                    exchange,
                    ask,
                    amount,
                    low,
                    Lside,
                    risk_manage["use_tailing"],
                )
            margin = ask * amount / int(leve)
            total = float(balance["total"]["USDT"])
            msg = (
                "BINANCE:"
                + f"\nCoin        : {risk_manage['symbol']}"
                + "\nStatus      : OpenLong[BUY]"
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
        notify_send(msg)
        candle(df, risk_manage["symbol"], risk_manage["timeframe"])
        return await disconnect(exchange)
    except Exception as e:
        lastUpdate.status = f"{e}"
        logging.info(e)
        notify_send(f"เกิดความผิดพลาดในการเข้า Order : OpenLong\n {e}")
        return await disconnect(exchange)


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
        msg = (
            "BINANCE:"
            + f"\nCoin        : {symbol}"
            + "\nStatus      : Order-TP1"
            + f"\nAmount      : {amttp1}"
            + f"\nPrice       : {triggerPrice}USDT"
        )
        notify_send(msg)
        logging.info(orderTP)
        if USETP2:
            triggerPrice2 = RRTP(df, False, 2, bid, TPRR1, TPRR2)
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
            msg2 = (
                "BINANCE:"
                + f"\nCoin        : {symbol}"
                + "\nStatus      : Order-TP2"
                + f"\nAmount      : {amttp2}"
                + f"\nPrice       : {triggerPrice2}"
            )
            notify_send(msg2)
            logging.info(orderTP2)
        return
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send("เกิดเตุการณืไม่คาดฝัน Order TP  ทำรายการไม่สำเร็จ")
        logging.info(e)
    return


# OpenShort=Sell
async def OpenShort(df, balance, risk_manage, Sside, min_balance):
    try:
        exchange = await connect_loads()
        await exchange.cancel_all_orders(risk_manage["symbol"])
        amount = sellsize(
            df,
            balance,
            risk_manage["symbol"],
            exchange,
            risk_manage["risk_size"],
        )
        markets = await exchange.fetchMarkets()
        min_amount = float(
            (
                data["limits"]["amount"]["min"]
                for data in markets
                if data["id"] == risk_manage["symbol"].replace("/", "")
            ).__next__()
        )
        if amount < min_amount:
            amount = min_amount
        bid = await get_bidask(risk_manage["symbol"], "bidPrice")
        logging.info(
            f"Entry Short {risk_manage['symbol']} Short @{bid} qmt:{amount}"
        )
        leve = await setleverage(
            risk_manage["symbol"], risk_manage["leverage"]
        )
        if amount * bid > risk_manage["max_size"] * int(leve):
            new_lots = risk_manage["max_size"] * int(leve) / bid
            amount = float(
                exchange.amount_to_precision(risk_manage["symbol"], new_lots)
            )
        free = float(balance["free"]["USDT"])
        amttp1 = amount * (risk_manage["tp_percent"] / 100)
        amttp2 = amount * (risk_manage["tp_percent_2"] / 100)
        high = df["highest"][len(df.index) - 1]
        if free > min_balance:
            try:
                order = await exchange.create_market_order(
                    risk_manage["symbol"],
                    "sell",
                    amount,
                    params={"positionSide": Sside},
                )
                logging.info(order)
            except ccxt.InsufficientFunds as e:
                logging.info(e)
                notify_send(e)
                return
            if risk_manage["use_sl"]:
                await USESLSHORT(
                    df,
                    risk_manage["symbol"],
                    exchange,
                    bid,
                    amount,
                    high,
                    Sside,
                    risk_manage["use_tailing"],
                )
            if risk_manage["use_tp_1"]:
                await USETPSHORT(
                    risk_manage["symbol"],
                    df,
                    exchange,
                    bid,
                    risk_manage["risk_reward_1"],
                    risk_manage["risk_reward_2"],
                    Sside,
                    amttp1,
                    amttp2,
                    risk_manage["use_tp_2"],
                )
            margin = bid * amount / int(leve)
            total = float(balance["total"]["USDT"])
            msg = (
                "BINANCE:"
                + f"\nCoin        : {risk_manage['symbol']}"
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
        notify_send(msg)
        candle(df, risk_manage["symbol"], risk_manage["timeframe"])
        return await disconnect(exchange)
    except Exception as e:
        lastUpdate.status = f"{e}"
        logging.info(e)
        notify_send(f"เกิดความผิดพลาดในการเข้า Order : OpenShort\n{e}")
        return await disconnect(exchange)


# CloseLong=Sell
async def CloseLong(df, balance, symbol, amt, pnl, Lside, tf):
    try:
        exchange = await connect_loads()
        amount = abs(amt)
        upnl = pnl
        bid = await get_bidask(symbol, "bidPrice")
        logging.info(f"Close Long {symbol} @{bid} qmt:{amount}")
        try:
            order = await exchange.create_market_order(
                symbol, "sell", amount, params={"positionSide": Lside}
            )
        except Exception as e:
            lastUpdate.status = f"{e}"
            await disconnect(exchange)
            logging.info(e)
            exchange = await connect_loads()
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
        notify_send(msg)
        candle(df, symbol, tf)
        return await disconnect(exchange)
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send(f"เกิดความผิดพลาดในการออก Order : CloseLong{e}")
        return await disconnect(exchange)


# CloseShort=Buy
async def CloseShort(df, balance, symbol, amt, pnl, Sside, tf):
    try:
        exchange = await connect_loads()
        amount = abs(amt)
        upnl = pnl
        ask = await get_bidask(symbol, "askPrice")
        logging.info(f"Close Short {symbol}  @{ask} qmt:{amount}")
        try:
            order = await exchange.create_market_order(
                symbol, "buy", amount, params={"positionSide": Sside}
            )
        except Exception as e:
            lastUpdate.status = f"{e}"
            await disconnect(exchange)
            logging.info(e)
            exchange = await connect_loads()
            order = await exchange.create_market_order(
                symbol, "buy", amount, params={"positionSide": Sside}
            )
        logging.info(order)
        total = float(balance["total"]["USDT"])
        msg = (
            "BINANCE:\n"
            f"Coin        : {symbol}\n"
            "Status      : CloseShort[BUY]\n"
            f"Amount      : {str(amount)}({round((amount * ask), 2)}USDT)\n"
            f"Price       : {ask} USDT\n"
            f"Realized P/L:  {round(upnl, 2)}USDT\n"
            f"Balance     : {round(total, 2)}USDT"
        )
        notify_send(msg)
        candle(df, symbol, tf)
        return await disconnect(exchange)
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send(f"เกิดความผิดพลาดในการออก Order : CloseShort {e}")
        return await disconnect(exchange)


async def get_currentmode():
    exchange = await connect()
    try:
        currentMODE = await exchange.fapiPrivate_get_positionside_dual()
    except Exception as e:
        lastUpdate.status = f"{e}"
        await disconnect(exchange)
        logging.info(e)
        exchange = await connect()
        currentMODE = await exchange.fapiPrivate_get_positionside_dual()
    await disconnect(exchange)
    currentMode.dualSidePosition = currentMODE["dualSidePosition"]
    if currentMode.dualSidePosition:
        currentMode.Sside = "SHORT"
        currentMode.Lside = "LONG"


async def feed(
    df,
    risk_manage,
    balance,
    min_balance,
    status,
):
    is_in_Long = False
    is_in_Short = False
    is_in_position = False
    amt = 0.0
    upnl = 0.0
    posim = risk_manage["symbol"].replace("/", "")
    if status is None:
        return
    for i in status.index:
        if status["symbol"][i] == posim:
            amt = float(status["positionAmt"][i])
            upnl = float(status["unrealizedProfit"][i])
            break
    # NO Position
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
        lastUpdate.status = "changed to Bullish, buy"
        if is_in_Short:
            lastUpdate.status = "closeshort"
            await CloseShort(
                df,
                balance,
                risk_manage["symbol"],
                amt,
                upnl,
                currentMode.Sside,
                risk_manage["timeframe"],
            )
            if risk_manage["use_long"]:
                await OpenLong(
                    df,
                    balance,
                    risk_manage,
                    currentMode.Lside,
                    min_balance,
                )
            else:
                lastUpdate.status = (
                    "No permission for excute order : Do nothing"
                )

        elif not is_in_Long and risk_manage["use_long"]:
            await OpenLong(
                df,
                balance,
                risk_manage,
                currentMode.Lside,
                min_balance,
            )
        else:
            lastUpdate.status = "already in position, nothing to do"
    if df["SELL"][last] == 1:
        lastUpdate.status = "changed to Bearish, Sell"
        if is_in_Long:
            lastUpdate.status = "closelong"
            await CloseLong(
                df,
                balance,
                risk_manage["symbol"],
                amt,
                upnl,
                currentMode.Lside,
                risk_manage["timeframe"],
            )
            if risk_manage["use_short"]:
                await OpenShort(
                    df,
                    balance,
                    risk_manage,
                    currentMode.Sside,
                    min_balance,
                )
            else:
                lastUpdate.status = (
                    "No permission for excute order : Do nothing"
                )
        elif not is_in_Short and risk_manage["use_short"]:
            await OpenShort(
                df,
                balance,
                risk_manage,
                currentMode.Sside,
                min_balance,
            )
        else:
            lastUpdate.status = "already in position, nothing to do"
