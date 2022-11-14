import asyncio
import logging
from datetime import datetime as dt

import ccxt.async_support as ccxt
import pandas as pd

from vxma_d.AppData.Appdata import (
    AppConfig,
    bot_setting,
    callbackRate,
    notify_send,
)

barsC = 1502


async def connect():
    config = AppConfig()
    exchange = ccxt.binance(config.BNBCZ)
    return exchange


async def disconnect(exchange):
    return await exchange.close()


async def get_symbol():
    symbols = pd.DataFrame()
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
        notify_send(
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
        notify_send("เกิดเตุการณืไม่คาดฝัน Order Stop Loss ทำรายการไม่สำเร็จ")
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
        notify_send("เกิดเตุการณืไม่คาดฝัน Order TP  ทำรายการไม่สำเร็จ")
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
                notify_send(e)
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
        notify_send(msg)
        candle(df, risk_manage.symbol, risk_manage.tf)
        return
    except Exception as e:
        print(e)
        logging.info(e)
        notify_send(f"เกิดความผิดพลาดในการเข้า Order {e}")
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
        notify_send("เกิดเตุการณืไม่คาดฝัน Order TP  ทำรายการไม่สำเร็จ")
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
                notify_send(e)
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
        notify_send(msg)
        candle(df, risk_manage.symbol, risk_manage.tf)
    except Exception as e:
        print(e)
        logging.info(e)
        notify_send("เกิดความผิดพลาดในการเข้า Order")
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
        notify_send(msg)
        candle(df, symbol, tf)
    except Exception as e:
        print(e)
        notify_send(f"เกิดความผิดพลาดในการออก Order {e}")
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
        notify_send(msg)
        candle(df, symbol, tf)
    except Exception as e:
        print(e)
        notify_send(f"เกิดความผิดพลาดในการออก Order {e}")
    return


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
        notify_send(
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
