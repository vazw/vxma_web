# The BEERWARE License (BEERWARE)
#
# Copyright (c) 2022 Author. All rights reserved.
#
# Licensed under the "THE BEER-WARE LICENSE" (Revision 42):
# vazw wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer or coffee in return
import asyncio
import logging
import time
import warnings
from uuid import uuid4

import mplfinance as mplf
import pandas as pd

from vxma_d.AppData.Appdata import (
    RiskManageTable,
    TATable,
    bot_setting,
    candle,
    notify_send,
)
from vxma_d.MarketEX.CCXT_Binance import (
    connect,
    disconnect,
    feed,
    fetchbars,
    get_symbol,
)
from vxma_d.Strategy.Benchmarking import benchmarking as ta_score

try:
    from vxma_d.Strategy.vxma_talib import vxma as ta
except Exception as e:
    from vxma_d.Strategy.vxma_pandas_ta import vxma as ta

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


async def get_dailytasks():
    daycollum = ["Symbol", "LastPirce", "Long-Term", "Mid-Term", "Short-Term"]
    symbolist = await get_symbol()
    print(len(symbolist))
    ta_data = TATable()
    for symbol in symbolist:
        try:
            df1, df2, df3 = await asyncio.gather(
                bot_1(symbol, ta_data.__dict__, "1d"),
                bot_2(symbol, ta_data.__dict__, "6h"),
                bot_3(symbol, ta_data.__dict__, "1h"),
            )

            # candle(df1, symbol, "1d")
            # candle(df2, symbol, "6h")
            # candle(df3, symbol, "1h")
            if df1 is not None:
                long_term = ta_score(df1)
                mid_term = ta_score(df2)
                short_term = ta_score(df3)
                yield pd.Series(
                    [
                        symbol,
                        df3["close"][len(df1.index) - 1],
                        long_term.benchmarking(),
                        mid_term.benchmarking(),
                        short_term.benchmarking(),
                    ],
                    index=daycollum,
                )
        except Exception as e:
            print(e)
            logging.info(e)
            pass


def remove_last_line_from_string(s):
    return s[: s.rfind("\n")]


async def dailyreport():
    try:
        notify_send(
            "คู่เทรดที่น่าสนใจในวันนี้\n",
            sticker=1990,
            package=446,
        )
        async for line in get_dailytasks():
            msg1 = remove_last_line_from_string(str(line))
            notify_send(msg=msg1)
        exchange = await connect()
        try:
            balance = await exchange.fetch_balance()
        except Exception as e:
            print(e)
            await disconnect(exchange)
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
        print(f"NET unrealizedProfit : {netunpl}")
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
        notify_send(
            message,
            sticker=1995,
            package=446,
        )
        await disconnect(exchange)
        return
    except Exception as e:
        notify_send(f"เกิดความผิดพลาดในส่วนของแจ้งเตือนรายวัน {e}")
        print(e)
        return


async def running_module():
    symbolist = bot_setting()
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
            logging.info(e)
            exchange = await connect()
            balance = await exchange.fetch_balance()
        if str(local_time[14:-9]) == "0" and not insession["hour"]:
            total = round(float(balance["total"]["USDT"]), 2)
            msg = f"Total Balance : {total} USDT"
            notify_send(msg, sticker=10863, package=789)
            insession["hour"] = True
        free_balance = float(balance["free"]["USDT"])
        await disconnect(exchange)
        for i in symbolist.index:
            try:

                ta_table_data = TATable(
                    atr_p=symbolist["ATR"][i],
                    atr_m=symbolist["ATR_m"][i],
                    ema=symbolist["EMA"][i],
                    linear=symbolist["subhag"][i],
                    smooth=symbolist["smooth"][i],
                    rsi=symbolist["RSI"][i],
                    aol=symbolist["Andean"][i],
                    pivot=symbolist["Pivot"][i],
                )
                risk_manage_data = RiskManageTable(symbolist, i, free_balance)
                data = await bot_1(
                    risk_manage_data.symbol,
                    ta_table_data.__dict__,
                    risk_manage_data.timeframe,
                )
                await asyncio.gather(feed(data, risk_manage_data.__dict__))

            except Exception as e:
                print(e)
                pass
        await asyncio.sleep(1)
        print("Bot is running...")
    else:
        await asyncio.sleep(60)
        print("Nothing to do now.....")


async def run_bot():
    await asyncio.gather(running_module())
    await asyncio.sleep(30)
    # await asyncio.gather(dailyreport())
