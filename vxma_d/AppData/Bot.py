import asyncio
import logging
import time
import warnings
from uuid import uuid4

import pandas as pd
from tabulate import tabulate

from vxma_d.AppData import colorCS, lastUpdate
from vxma_d.AppData.Appdata import (
    AppConfig,
    RiskManageTable,
    TATable,
    bot_setting,
    candle,
    clearconsol,
    notify_send,
)
from vxma_d.MarketEX.CCXT_Binance import (
    feed,
    fetchbars,
    fetching_balance,
    get_currentmode,
    get_symbol,
    getAllsymbol,
)

have_talib = False
try:
    from vxma_d.Strategy.vxma_talib import vxma as ta

    have_talib = True
except Exception as e:  # noqa:
    from vxma_d.Strategy.vxma_pandas_ta import vxma as ta

    have_talib = False

if have_talib:
    from vxma_d.Strategy.Benchmarking import benchmarking as ta_score


bot_name = "VXMA Trading Bot by Vaz.(Version 0.1.1) github.com/vazw/vxma_web"

launch_uid = uuid4()
pd.set_option("display.max_rows", None)
warnings.filterwarnings("ignore")


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

common_names = {
    "symbol": "Symbols",
    "entryPrice": "ราคาเข้า",
    "positionSide": "Side",
    "unrealizedProfit": "u.P/L $",
    "positionAmt": "Amount",
    "initialMargin": "Margin $",
    "leverage": "Leverage",
}


async def bot_1(symbol, ta_data, tf):
    try:
        data1 = await fetchbars(symbol, tf)
        bot1 = ta(data1, ta_data)
        data1 = bot1.indicator()
        return data1
    except Exception as e:
        lastUpdate.status = f"{e}"
        logging.info(e)
        pass


async def bot_2(symbol, ta_data, tf):
    try:
        data2 = await fetchbars(symbol, tf)
        bot2 = ta(data2, ta_data)
        data2 = bot2.indicator()
        return data2
    except Exception as e:
        lastUpdate.status = f"{e}"
        logging.info(e)
        pass


async def bot_3(symbol, ta_data, tf):
    try:
        data3 = await fetchbars(symbol, tf)
        bot3 = ta(data3, ta_data)
        data3 = bot3.indicator()
        return data3
    except Exception as e:
        lastUpdate.status = f"{e}"
        logging.info(e)
        pass


async def scanSideway():
    symbolist = await getAllsymbol()
    lastUpdate.status = f"Scanning {len(symbolist)} Symbols"
    ta_data = TATable()
    symbols = []
    for symbol in symbolist:
        try:
            df1, df2, df3 = await asyncio.gather(
                bot_1(symbol, ta_data.__dict__, "1d"),
                bot_2(symbol, ta_data.__dict__, "6h"),
                bot_3(symbol, ta_data.__dict__, "1h"),
            )

            if df1 is not None:
                long_term = ta_score(df1)
                mid_term = ta_score(df2)
                short_term = ta_score(df3)
                long_term_score = long_term.benchmarking()
                mid_term_score = mid_term.benchmarking()
                short_term_score = short_term.benchmarking()
                if (
                    (
                        long_term_score == "Side-Way"
                        and mid_term_score == "Side-Way"
                    )
                    or (
                        long_term_score == "Side-Way"
                        and short_term_score == "Side-Way"
                    )
                    or (
                        mid_term_score == "Side-Way"
                        and short_term_score == "Side-Way"
                    )
                ):
                    pass
                else:
                    symbols.append(symbol)
                    lastUpdate.status = f"Added {symbol} to list"
        except Exception as e:
            lastUpdate.status = f"{e}"
            logging.info(e)
            pass
    return symbols


async def get_dailytasks():
    daycollum = ["Symbol", "LastPirce", "Long-Term", "Mid-Term", "Short-Term"]
    symbolist = await get_symbol()
    ta_data = TATable()
    for symbol in symbolist:
        try:
            df1, df2, df3 = await asyncio.gather(
                bot_1(symbol, ta_data.__dict__, "1d"),
                bot_2(symbol, ta_data.__dict__, "6h"),
                bot_3(symbol, ta_data.__dict__, "1h"),
            )

            # candle(df2, symbol, "6h")
            # candle(df3, symbol, "1h")
            if df1 is not None:
                candle(df1, symbol, "1d")
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
            lastUpdate.status = f"{e}"
            logging.info(e)
            pass


def remove_last_line_from_string(text):
    return text[: text.rfind("\n")]


def hourly_report(balance):
    lastUpdate.status = "Hourly report"
    total = round(float(balance["total"]["USDT"]), 2)
    msg = f"Total Balance : {total} USDT"
    notify_send(msg, sticker=10863, package=789)
    insession["hour"] = True


async def dailyreport():
    lastUpdate.status = "Daily Report"
    try:
        notify_send(
            "คู่เทรดที่น่าสนใจในวันนี้\n",
            sticker=1990,
            package=446,
        )
        async for line in get_dailytasks():
            msg1 = remove_last_line_from_string(str(line))
            notify_send(msg=msg1)
        balance = await fetching_balance()
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
        margin = float((status["initialMargin"]).astype("float64").sum())
        netunpl = float((status["unrealizedProfit"]).astype("float64").sum())
        print(f"Margin Used : {margin}")
        print(f"NET unrealizedProfit : {netunpl}")
        status = status.sort_values(by=["unrealizedProfit"], ascending=False)
        status = status.head(1)
        print(status)
        sim1 = status["symbol"][0]
        upnl = round(float(status["unrealizedProfit"][0]), 2)
        entryP = status["entryPrice"][0]
        metthod = status["positionSide"][0]
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
        return
    except Exception as e:
        notify_send(f"เกิดความผิดพลาดในส่วนของแจ้งเตือนรายวัน {e}")
        lastUpdate.status = f"{e}"
        logging.info(e)
        return


async def running_module():
    lastUpdate.status = "Loading..."
    symbolist = bot_setting()
    seconds = time.time()
    local_time = time.ctime(seconds)
    if str(local_time[14:-9]) == "1":
        insession["day"] = False
        insession["hour"] = False
    if str(local_time[11:-9]) == "07:0" and not insession["day"]:
        insession["day"] = True
        insession["hour"] = True
        if have_talib:
            await asyncio.gather(dailyreport())
    if not symbolist.empty:
        balance = await fetching_balance()
        if str(local_time[14:-9]) == "0" and not insession["hour"]:
            hourly_report(balance)
        free_balance = float(balance["free"]["USDT"])
        lastUpdate.balance = round(float(balance["total"]["USDT"]), 2)
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
                lastUpdate.status = f"Scaning {risk_manage_data.symbol}"
                data = await bot_1(
                    risk_manage_data.symbol,
                    ta_table_data.__dict__,
                    risk_manage_data.timeframe,
                )
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
                margin = 0.0
                netunpl = 0.0
                config = AppConfig()
                max_margin = config.max_margin
                min_balance = config.min_balance
                margin = float(
                    (status["initialMargin"]).astype("float64").sum()
                )
                netunpl = float(
                    (status["unrealizedProfit"]).astype("float64").sum()
                )
                if margin > max_margin:
                    notify_send(
                        "Margin ที่ใช้สูงเกินไปแล้ว\nMargin : {margin}\n",
                        f"ที่กำหนดไว้ : {max_margin}",
                        sticker=17857,
                        package=1070,
                    )
                    return
                await asyncio.sleep(50 / 1000)
                await asyncio.gather(
                    feed(
                        data,
                        risk_manage_data.__dict__,
                        balance,
                        min_balance,
                        status,
                    )
                )

            except Exception as e:
                lastUpdate.status = f"{e}"
                logging.info(e)
                pass

        clearconsol()
        status["unrealizedProfit"] = (
            (status["unrealizedProfit"]).astype("float64").round(2)
        )
        status["initialMargin"] = (
            (status["initialMargin"]).astype("float64").round(2)
        )
        status.rename(columns=common_names, errors="ignore", inplace=True)
        print(f"{colorCS.CBOLD}{colorCS.CGREEN}{bot_name}{colorCS.CEND}")
        print(tabulate(status, showindex=False, headers="keys"))
        print(
            f"Margin Used : {colorCS.CBOLD + colorCS.CRED}{round(margin, 3)} ${colorCS.CEND}"  # noqa:
            + f"  NET P/L : {colorCS.CBOLD + colorCS.CGREEN}{round(netunpl, 3)} ${colorCS.CEND}"  # noqa:
            + f" Balance : {colorCS.CBOLD + colorCS.CGREEN}{lastUpdate.balance} ${colorCS.CEND}"  # noqa:
        )
        lastUpdate.status = "idle"
        await asyncio.sleep(30)
    else:
        lastUpdate.status = "idle"
        await asyncio.sleep(60)


async def waiting():
    count = 0
    status = [
        "[        ]Latest",
        "[=       ]lAtest",
        "[===     ]laTest",
        "[====    ]latEst",
        "[=====   ]lateSt",
        "[======  ]latesT",
        "[======= ]latest",
        "[========]Latest",
        "[ =======]lAtest",
        "[  ======]laTest",
        "[   =====]latEst",
        "[    ====]lateSt",
        "[     ===]latesT",
        "[      ==]latest",
        "[       =]latest",
    ]
    while True:
        await asyncio.sleep(0.2)
        text_time = f"{colorCS.CYELLOW} เวลา {colorCS.CGREEN}"
        time_now = f"{(lastUpdate.candle)[:-10].replace('T',text_time)}"
        status_text = f"{lastUpdate.status}"
        print(
            "\r"
            + colorCS.CRED
            + colorCS.CBOLD
            + status[count % len(status)]
            + f" update : {colorCS.CGREEN}"
            + time_now
            + colorCS.CRED
            + f"{colorCS.CRED} Status : "
            + colorCS.CEND
            + status_text[0:27],
            end="",
        )
        count += 1
        count = count % len(status)


async def warper_fn():
    while True:
        try:
            await running_module()
        except Exception as e:
            lastUpdate.status = f"{e}"
            logging.info(e)
            notify_send(f"เกิดข้อผิดพลาดภายนอก\n{e}\nบอทเข้าสู่ Sleep Mode")
            lastUpdate.status = "Sleep Mode"
            await asyncio.sleep(60)
            tasks = asyncio.current_task()
            clearconsol()
            tasks.cancel()
            raise ConnectionError


async def run_bot():
    try:
        await get_currentmode()
        await asyncio.gather(warper_fn(), waiting())
    except Exception as e:
        logging.info(e)
        notify_send("บอทเข้าสู่สถานะ Fallback Mode")
        lastUpdate.status = "Fallback Mode : Restarting..."
        return
