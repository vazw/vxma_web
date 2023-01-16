import asyncio  # pyright: ignore # noqa:

import ccxt.async_support as ccxt
import pandas as pd

from vxma_d.AppData import (
    currentMode,
    lastUpdate,
    alrnotify,
    candle_ohlc,
    timer,
)
from vxma_d.AppData.Appdata import (
    AppConfig,
    bot_setting,
    candle,
    notify_send,
    write_trade_record,
)

barsC = 1502


def callbackRate(data, direction):
    m = len(data.index)
    close = data["close"][m - 1]
    highest = data["highest"][m - 1]
    lowest = data["lowest"][m - 1]
    try:
        if direction:
            rate = round((100 - (lowest / close * 100)), 1)
        else:
            rate = round((100 - (close / highest * 100)), 1)
        if rate > 5.0:
            return 5.0
        elif rate < 1.0:
            return 1.0
        else:
            return rate
    except Exception as e:
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
    try:
        exchange = ccxt.binance(config.BNBCZ)
        return exchange
    except Exception as e:
        print(e)
        return await disconnect(exchange)


async def connect_loads():
    config = AppConfig()
    exchange = ccxt.binance(config.BNBCZ)
    await exchange.load_markets(reload=True)
    return exchange


async def disconnect(exchange):
    return await exchange.close()


async def get_bidask(symbol, exchange, bidask="ask"):
    try:
        info = (await exchange.fetch_bids_asks())[symbol][bidask]
    except Exception:
        info = (await exchange.fetch_bids_asks())[symbol[:-5]][bidask]
    return float(info)


async def get_symbol():
    """
    get top 10 volume symbol of the day
    """
    symbolist = bot_setting()
    lastUpdate.status = "fecthing Symbol of Top 10 Volume..."
    exchange = await connect()
    try:
        market = await exchange.fetch_tickers(params={"type": "future"})
    except Exception as e:
        print(e)
        market = await exchange.fetch_tickers(params={"type": "future"})
    await disconnect(exchange)
    symbols = pd.DataFrame(
        [
            y
            for x, y in market.items()
            if x.endswith("USDT") or x.endswith("BUSD")
        ]
    )
    symbols = symbols.sort_values(by=["quoteVolume"], ascending=False)
    symbols = symbols.head(10)
    newsym = [symbol for symbol in symbols["symbol"]]
    if symbolist is not None and len(symbolist.index) > 0:
        for i in range(len(symbolist.index)):
            newsym.append(symbolist["symbol"][i])
    newsym = list(dict.fromkeys(newsym))
    print(f"Interested : {newsym}")
    return newsym


async def getAllsymbol():
    """
    Get all symbols
    """
    exchange = await connect()
    try:
        market = await exchange.fetch_tickers(params={"type": "future"})
    except Exception as e:
        print(e)
        market = await exchange.fetch_tickers(params={"type": "future"})
    await disconnect(exchange)
    symbols = pd.DataFrame(
        [
            y
            for x, y in market.items()
            if x.endswith("USDT") or x.endswith("BUSD")
        ]
    )
    symbols = symbols.sort_values(by=["quoteVolume"], ascending=False)
    return [symbol for symbol in symbols["symbol"]]


async def fetching_candle_ohlc(symbol, timeframe, limits):
    exchange = await connect()
    try:
        bars = await exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, since=None, limit=limits
        )
        await disconnect(exchange)
        return bars
    except Exception as e:
        lastUpdate.status = f"{e}"
        await disconnect(exchange)

        exchange = await connect()
        bars = await exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, since=None, limit=limits
        )
        await disconnect(exchange)
        return bars


async def fetchbars(symbol, timeframe):
    """
    get candle from exchange
    """
    if f"{symbol}{timeframe}" not in candle_ohlc.keys():
        bars = await fetching_candle_ohlc(symbol, timeframe, barsC)
        df = pd.DataFrame(
            bars[:-1],
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        if timeframe == timer.min_timeframe:
            timer.last_closed = int(df["timestamp"][len(df.index) - 1] / 1000)
        df["timestamp"] = pd.to_datetime(
            df["timestamp"], unit="ms", utc=True
        ).map(lambda x: x.tz_convert("Asia/Bangkok"))
        df = df.set_index("timestamp")
        candle_ohlc.update({f"{symbol}{timeframe}": df})
        return candle_ohlc[f"{symbol}{timeframe}"].copy()
    else:
        bars = await fetching_candle_ohlc(symbol, timeframe, 5)
        df = pd.DataFrame(
            bars[:-1],
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(
            df["timestamp"], unit="ms", utc=True
        ).map(lambda x: x.tz_convert("Asia/Bangkok"))
        df = df.set_index("timestamp")
        df = pd.concat(
            [candle_ohlc[f"{symbol}{timeframe}"], df], ignore_index=False
        )
        candle_ohlc[f"{symbol}{timeframe}"] = df[
            ~df.index.duplicated(keep="last")
        ].tail(barsC)
        return candle_ohlc[f"{symbol}{timeframe}"].copy()


# set leverage pass
async def setleverage(symbol, lev, exchange):
    try:
        await exchange.set_leverage(lev, symbol)
        return lev
    except Exception as e:
        print(e)
        lever = await exchange.fetch_positions_risk([symbol])
        for x in range(len(lever)):
            if (lever[x]["symbol"]) == symbol:
                lev = round(lever[x]["leverage"], 0)
                await exchange.set_leverage(int(lev), symbol)
                break
        return round(int(lev), 0)


def RR1(stop, side, price, symbol, exchange):
    if side:
        target = price * (1 + ((price - float(stop)) / price) * 1)
        return exchange.price_to_precision(symbol, target)
    elif not side:
        target = price * (1 - ((float(stop) - price) / price) * 1)
        return exchange.price_to_precision(symbol, target)
    else:
        return None


async def TailingLongOrder(df, symbol, exchange, ask, amount, low, side):
    try:
        triggerPrice = RR1(low, True, ask, symbol, exchange)
        if triggerPrice is None:
            return
        callbackrate = callbackRate(df, True)
        if currentMode.dualSidePosition:
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
        else:
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
        print(ordertailingSL)
        msg2 = (
            "BINANCE:"
            + f"\nCoin        : {symbol}"
            + "\nStatus      : Tailing-StopLoss"
            + f"\nAmount      : {amount}"
            + f"\nCallbackRate: {callbackrate}%"
            + f"\ntriggerPrice: {triggerPrice}"
        )
        notify_send(msg2)
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send(f"เกิดความผิดพลาดในการเข้า Order : Tailing Stop\n{e}")


async def TailingShortOrder(df, symbol, exchange, bid, amount, high, Sside):
    try:
        triggerPrice = RR1(high, False, bid, symbol, exchange)
        if triggerPrice is None:
            return
        callbackrate = callbackRate(df, False)
        if currentMode.dualSidePosition:
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
        else:
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
        print(ordertailingSL)
        msg2 = (
            "BINANCE:"
            + f"\nCoin        : {symbol}"
            + "\nStatus      : Tailing-StopLoss"
            + f"\nAmount      : {amount}"
            + f"\nCallbackRate: {callbackrate}%"
            + f"\ntriggerPrice: {triggerPrice}"
        )
        notify_send(msg2)
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send(f"เกิดความผิดพลาดในการเข้า Order : Tailing Stop\n{e}")


async def USESLSHORT(symbol, exchange, amount, high, Sside):
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
            print(orderSL)
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
        return high
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send(
            "เกิดเตุการณืไม่คาดฝัน Order Stop Loss" + f"ทำรายการไม่สำเร็จ {e}"
        )
        return 0.0


async def USESLLONG(symbol, exchange, amount, low, side):
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
        print(orderSL)
        return low
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send(f"เกิดเตุการณืไม่คาดฝัน Order TP  ทำรายการไม่สำเร็จ{e}")
        return 0.0


async def USETPLONG(
    symbol, df, exchange, ask, TPRR1, TPRR2, Lside, amttp1, amttp2, USETP2
):
    try:
        stop_price = exchange.price_to_precision(
            symbol, RRTP(df, True, 1, ask, TPRR1, TPRR2)
        )
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
        print(orderTP)
        if USETP2:
            triggerPrice = exchange.price_to_precision(
                symbol, RRTP(df, True, 2, ask, TPRR1, TPRR2)
            )
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
            print(orderTP2)
            return [stop_price, triggerPrice]
        return [stop_price]
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send(f"เกิดเตุการณืไม่คาดฝัน Order TP  ทำรายการไม่สำเร็จ{e}")
        return None


async def fetching_balance():
    exchange = await connect()
    try:
        balance = await exchange.fetch_balance()
        await disconnect(exchange)
        return balance
    except Exception as e:
        lastUpdate.status = f"{e}"
        await disconnect(exchange)
        exchange = await connect()
        balance = await exchange.fetch_balance()
        await disconnect(exchange)
        return balance


async def fetching_fiat_balance():
    balance = await fetching_balance()
    return {x: y for x, y in balance.items() if x == "USDT" or x == "BUSD"}


# Position Sizing
def buysize(df, balance, symbol, exchange, RISK):
    last = len(df.index) - 1
    quote = symbol[-4:]
    freeusd = float(balance["free"][quote])
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
    quote = symbol[-4:]
    freeusd = float(balance["free"][quote])
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
    exchange = await connect_loads()
    # try:
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
            if data["symbol"] == risk_manage["symbol"]
        ).__next__()
    )
    if amount < min_amount:
        amount = min_amount
    ask = await get_bidask(risk_manage["symbol"], exchange, "ask")
    leve = await setleverage(
        risk_manage["symbol"], risk_manage["leverage"], exchange
    )
    if amount * ask > risk_manage["max_size"] * int(leve):
        new_lots = risk_manage["max_size"] * int(leve) / ask
        amount = float(
            exchange.amount_to_precision(risk_manage["symbol"], new_lots)
        )
    free = float(risk_manage["free_balance"])
    amttp1 = amount * (risk_manage["tp_percent"] / 100)
    amttp2 = amount * (risk_manage["tp_percent_2"] / 100)
    low = df["lowest"][len(df.index) - 1]
    quote = risk_manage["quote"]
    if free > min_balance:
        try:
            order = await exchange.create_market_order(
                risk_manage["symbol"],
                "buy",
                amount,
                params={"positionSide": Lside},
            )
            print(order)
            margin = ask * amount / int(leve)
            total = float(balance["total"][quote])
        except ccxt.InsufficientFunds as e:
            notify_send(e)
            return await disconnect(exchange)
        if risk_manage["use_tp_1"]:
            tp12 = await USETPLONG(
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
            slprice = await USESLLONG(
                risk_manage["symbol"],
                exchange,
                amount,
                low,
                Lside,
            )
        msg = (
            "BINANCE:"
            + f"\nCoin        : {risk_manage['symbol']}"
            + "\nStatus      : OpenLong[BUY]"
            + f"\nAmount      : {amount}({round((amount * ask), 2)}{quote})"
            + f"\nPrice       : {ask}{quote}"
            + f"\nmargin      : {round(margin, 2)}{quote}"
            + f"\nBalance     : {round(total, 2)}{quote}"
            + f"\nTP Price    : {tp12}{quote}"
            + f"\nSL Price    : {slprice}{quote}"
        )
        notify_send(msg)
        if risk_manage["use_tailing"]:
            await TailingLongOrder(
                df,
                risk_manage["symbol"],
                exchange,
                ask,
                amount,
                low,
                Lside,
            )
    else:
        msg = (
            f"MARGIN-CALL!!!\nยอดเงินต่ำกว่าที่กำหนดไว้ :{min_balance}USD"
            + f"\nยอดปัจจุบัน  {round(free, 2)}"
            + " USD\nบอทจะทำการยกเลิกการเข้า Position ทั้งหมด"
        )
        notify_send(msg)
    time_now = f"{(lastUpdate.candle)[:-10].replace('T',' at ')}"
    write_trade_record(
        time_now,
        risk_manage["symbol"],
        amount,
        ask,
        "OpenLong[BUY]",
        tp12,
        slprice,
    )
    candle(df, risk_manage["symbol"], f"{risk_manage['timeframe']} {time_now}")
    return await disconnect(exchange)
    # except Exception as e:
    #     print(e)
    #     lastUpdate.status = f"{e}"
    #     notify_send(f"เกิดความผิดพลาดในการเข้า Order : OpenLong\n {e}")
    #     return await disconnect(exchange)


async def USETPSHORT(
    symbol, df, exchange, bid, TPRR1, TPRR2, Sside, amttp1, amttp2, USETP2
):
    try:
        triggerPrice = exchange.price_to_precision(
            symbol, RRTP(df, False, 1, bid, TPRR1, TPRR2)
        )
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
        print(orderTP)
        if USETP2:
            triggerPrice2 = exchange.price_to_precision(
                symbol, RRTP(df, False, 2, bid, TPRR1, TPRR2)
            )
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
            print(orderTP2)
            return [triggerPrice, triggerPrice2]
        return [triggerPrice]
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send("เกิดเตุการณืไม่คาดฝัน Order TP  ทำรายการไม่สำเร็จ")
        return None


# OpenShort=Sell
async def OpenShort(df, balance, risk_manage, Sside, min_balance):
    exchange = await connect_loads()
    try:
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
                if data["symbol"] == risk_manage["symbol"]
            ).__next__()
        )
        if amount < min_amount:
            amount = min_amount
        bid = await get_bidask(risk_manage["symbol"], exchange, "bid")
        leve = await setleverage(
            risk_manage["symbol"], risk_manage["leverage"], exchange
        )
        if amount * bid > risk_manage["max_size"] * int(leve):
            new_lots = risk_manage["max_size"] * int(leve) / bid
            amount = float(
                exchange.amount_to_precision(risk_manage["symbol"], new_lots)
            )
        free = float(risk_manage["free_balance"])
        amttp1 = amount * (risk_manage["tp_percent"] / 100)
        amttp2 = amount * (risk_manage["tp_percent_2"] / 100)
        high = df["highest"][len(df.index) - 1]
        quote = risk_manage["quote"]
        if free > min_balance:
            try:
                order = await exchange.create_market_order(
                    risk_manage["symbol"],
                    "sell",
                    amount,
                    params={"positionSide": Sside},
                )
                print(order)
                margin = bid * amount / int(leve)
                total = float(balance["total"][quote])
            except ccxt.InsufficientFunds as e:
                notify_send(e)
                return await disconnect(exchange)
            if risk_manage["use_sl"]:
                slprice = await USESLSHORT(
                    risk_manage["symbol"],
                    exchange,
                    amount,
                    high,
                    Sside,
                )
            if risk_manage["use_tp_1"]:
                tp12 = await USETPSHORT(
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
            msg = (
                "BINANCE:"
                + f"\nCoin        : {risk_manage['symbol']}"
                + "\nStatus      : OpenShort[SELL]"
                + f"\nAmount      : {amount}({round((amount * bid), 2)}{quote})"
                + f"\nPrice       : {bid}{quote}"
                + f"\nmargin      : {round(margin, 2)}{quote}"
                + f"\nBalance     : {round(total, 2)}{quote}"
                + f"\nTP Price    : {tp12}{quote}"
                + f"\nSL Price    : {slprice}{quote}"
            )
            notify_send(msg)
            if risk_manage["use_tailing"]:
                await TailingShortOrder(
                    df,
                    risk_manage["symbol"],
                    exchange,
                    bid,
                    amount,
                    high,
                    Sside,
                )
        else:
            msg = (
                f"MARGIN-CALL!!!\nยอดเงินต่ำกว่าที่กำหนดไว้ :{min_balance}USD"
                + f"\nยอดปัจจุบัน  {round(free, 2)}"
                + " USD\nบอทจะทำการยกเลิกการเข้า Position ทั้งหมด"
            )
            notify_send(msg)
        time_now = f"{(lastUpdate.candle)[:-10].replace('T',' at ')}"
        write_trade_record(
            time_now,
            risk_manage["symbol"],
            amount,
            bid,
            "OpenShort[SELL]",
            tp12,
            slprice,
        )
        candle(
            df, risk_manage["symbol"], f"{risk_manage['timeframe']} {time_now}"
        )
        return await disconnect(exchange)
    except Exception as e:
        lastUpdate.status = f"{e}"
        notify_send(f"เกิดความผิดพลาดในการเข้า Order : OpenShort\n{e}")
        return await disconnect(exchange)


# CloseLong=Sell
async def CloseLong(df, balance, symbol, amt, pnl, Lside, tf):
    exchange = await connect_loads()
    try:
        amount = abs(amt)
        upnl = pnl
        quote = symbol[-4:]
        bid = await get_bidask(symbol, exchange, "bid")
        try:
            order = await exchange.create_market_order(
                symbol, "sell", amount, params={"positionSide": Lside}
            )
        except Exception as e:
            lastUpdate.status = f"{e}"
            await disconnect(exchange)
            exchange = await connect_loads()
            order = await exchange.create_market_order(
                symbol, "sell", amount, params={"positionSide": Lside}
            )
            print(order)
        total = float(balance["total"][quote])
        msg = (
            "BINANCE:\n"
            + f"Coin        : {symbol}\n"
            + "Status      : CloseLong[SELL]\n"
            + f"Amount      : {str(amount)}({round((amount * bid), 2)} {quote})\n"
            + f"Price       : {bid} {quote}\n"
            + f"Realized P/L:  {round(upnl, 2)} {quote}\n"
            + f"Balance     : {round(total, 2)} {quote}"
        )
        notify_send(msg)
        time_now = f"{(lastUpdate.candle)[:-10].replace('T',' at ')}"
        write_trade_record(
            time_now, symbol, amount, bid, "CloseLong[SELL]", pnl=upnl
        )
        candle(df, symbol, f"{tf} {time_now}")
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
        quote = symbol[-4:]
        upnl = pnl
        ask = await get_bidask(symbol, exchange, "ask")
        try:
            order = await exchange.create_market_order(
                symbol, "buy", amount, params={"positionSide": Sside}
            )
        except Exception as e:
            lastUpdate.status = f"{e}"
            await disconnect(exchange)
            exchange = await connect_loads()
            order = await exchange.create_market_order(
                symbol, "buy", amount, params={"positionSide": Sside}
            )
            print(order)
        total = float(balance["total"][quote])
        msg = (
            "BINANCE:\n"
            f"Coin        : {symbol}\n"
            "Status      : CloseShort[BUY]\n"
            f"Amount      : {str(amount)}({round((amount * ask), 2)}{quote})\n"
            f"Price       : {ask} {quote}\n"
            f"Realized P/L:  {round(upnl, 2)}{quote}\n"
            f"Balance     : {round(total, 2)}{quote}"
        )
        notify_send(msg)
        time_now = f"{(lastUpdate.candle)[:-10].replace('T',' at ')}"
        write_trade_record(
            time_now, symbol, amount, ask, "CloseShort[BUY]", pnl=upnl
        )
        candle(df, symbol, f"{tf} {time_now}")
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
    posim = risk_manage["symbol"][:-5].replace("/", "")
    if status is None:
        return
    status = status[status["symbol"] == posim]

    if status.empty:
        amt_short = 0.0
        amt_long = 0.0
        upnl_short = 0.0
        upnl_long = 0.0
    elif len(status.index) > 1:
        amt_long = (
            status["positionAmt"][i]
            for i in status.index
            if status["symbol"][i] == posim
            and status["positionSide"][i] == "LONG"
        ).__next__()
        amt_short = (
            status["positionAmt"][i]
            for i in status.index
            if status["symbol"][i] == posim
            and status["positionSide"][i] == "SHORT"
        ).__next__()
        upnl_long = (
            status["unrealizedProfit"][i]
            for i in status.index
            if status["symbol"][i] == posim
            and status["positionSide"][i] == "LONG"
        ).__next__()
        upnl_short = (
            status["unrealizedProfit"][i]
            for i in status.index
            if status["symbol"][i] == posim
            and status["positionSide"][i] == "SHORT"
        ).__next__()
    else:
        amt = float(
            (
                status["positionAmt"][i]
                for i in status.index
                if status["symbol"][i] == posim
            ).__next__()
        )
        amt_long = amt if amt > 0 else 0.0
        amt_short = amt if amt < 0 else 0.0
        upnl = float(
            (
                status["unrealizedProfit"][i]
                for i in status.index
                if status["symbol"][i] == posim
            ).__next__()
        )
        upnl_long = upnl if amt != 0 else 0.0
        upnl_short = upnl if amt != 0 else 0.0

    is_in_Long = True if amt_long != 0 else False
    is_in_Short = True if amt_short != 0 else False

    last = len(df.index) - 1
    if (
        df["isSL"][last] == 1
        and f"{risk_manage['symbol']}{df.index.last()}"
        not in alrnotify.symbols
    ):
        notify_send(f"{risk_manage['symbol']} got Stop-Loss!")
        alrnotify.symbols.append(f"{risk_manage['symbol']}{df.index.last()}")

    if df["BUY"][last] == 1:
        lastUpdate.status = "changed to Bullish, buy"
        if is_in_Short:
            lastUpdate.status = "closeshort"
            await CloseShort(
                df,
                balance,
                risk_manage["symbol"],
                amt_short,
                upnl_short,
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
                amt_long,
                upnl_long,
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
