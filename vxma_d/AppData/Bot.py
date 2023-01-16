import asyncio
import time
from uuid import uuid4
import warnings
from tabulate import tabulate
from datetime import datetime

import pandas as pd

from vxma_d.AppData import alrnotify, colorCS, lastUpdate, timer
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
    fetching_fiat_balance,
    getAllsymbol,
    get_currentmode,
    get_symbol,
)
from vxma_d.Strategy.Benchmarking import benchmarking as ta_score
from vxma_d.Strategy.vxma_talib import vxma as ta


bot_name = "VXMA Trading Bot by Vaz.(Version 0.1.3) github.com/vazw/vxma_web"

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
statcln = [
    "symbol",
    "entryPrice",
    "positionSide",
    "unrealizedProfit",
    "positionAmt",
    "initialMargin",
    "leverage",
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

TIMEFRAME_SECONDS = {
    "1m": 1,
    "3m": 60 * 3,
    "5m": 60 * 5,
    "15m": 60 * 15,
    "30m": 60 * 30,
    "1h": 60 * 60,
    "2h": 60 * 60 * 2,
    "4h": 60 * 60 * 4,
    "6h": 60 * 60 * 6,
    "8h": 60 * 60 * 8,
    "12h": 60 * 60 * 12,
    "1d": 60 * 60 * 24,
    "1w": 60 * 60 * 24 * 7,
    "1M": 60 * 60 * 24 * 7,
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
        pass


async def bot_2(symbol, ta_data, tf):
    try:
        data2 = await fetchbars(symbol, tf)
        bot2 = ta(data2, ta_data)
        data2 = bot2.indicator()
        return data2
    except Exception as e:
        lastUpdate.status = f"{e}"
        pass


async def bot_3(symbol, ta_data, tf):
    try:
        data3 = await fetchbars(symbol, tf)
        bot3 = ta(data3, ta_data)
        data3 = bot3.indicator()
        return data3
    except Exception as e:
        lastUpdate.status = f"{e}"
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
                    print(f"{symbol} is Side-Way: Pass")
                    pass
                else:
                    symbols.append(symbol)
                    lastUpdate.status = f"Added {symbol} to list"
        except Exception as e:
            lastUpdate.status = f"{e}"
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
                time_now = f"{(lastUpdate.candle)[:-10].replace('T',' at ')}"
                candle(df1, symbol, f"1d {time_now}")
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
            pass


def remove_last_line_from_string(text):
    return text[: text.rfind("\n")]


async def hourly_report():
    balance = await fetching_balance()
    lastUpdate.status = "Hourly report"
    positions = balance["info"]["positions"]
    status = pd.DataFrame(
        [
            position
            for position in positions
            if float(position["positionAmt"]) != 0
        ],
        columns=statcln,
    )
    netunpl = float(
        status["unrealizedProfit"].astype("float64").sum()
        if not status.empty
        else 0.0
    )
    fiat_balance = {
        x: y for x, y in balance.items() if x == "USDT" or x == "BUSD"
    }
    lastUpdate.balance = fiat_balance
    msg = (
        "Balance Report\n BUSD"
        + f"\nFree   : {round(fiat_balance['BUSD']['free'],2)}$"
        + f"\nMargin : {round(fiat_balance['BUSD']['used'],2)}$"
        + f"\nTotal  : {round(fiat_balance['BUSD']['total'],2)}$\nUSDT"
        + f"\nFree   : {round(fiat_balance['USDT']['free'],2)}$"
        + f"\nMargin : {round(fiat_balance['USDT']['used'],2)}$"
        + f"\nTotal  : {round(fiat_balance['USDT']['total'],2)}$"
        + f"\nNet Profit/Loss  : {round(netunpl,2)}$"
    )
    notify_send(msg)
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
        status = pd.DataFrame(
            [
                position
                for position in positions
                if float(position["positionAmt"]) != 0
            ],
            columns=statcln,
        )
        margin = float((status["initialMargin"]).astype("float64").sum())
        netunpl = float((status["unrealizedProfit"]).astype("float64").sum())
        print(f"Margin Used : {margin}")
        print(f"NET unrealizedProfit : {netunpl}")
        status = status.sort_values(by=["unrealizedProfit"], ascending=False)
        status = status.head(1)
        firstline = (status.index)[0]
        upnl = round(
            float((status["unrealizedProfit"]).astype("float64").sum()), 2
        )
        entryP = status["entryPrice"][firstline]
        metthod = status["positionSide"][firstline]
        msg2 = (
            f"{firstline} {metthod} at {entryP} \nunrealizedProfit : {upnl}$"
        )
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
        return


async def running_module():
    lastUpdate.status = "Loading..."
    symbolist = bot_setting()

    balance = await fetching_balance()

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

            risk_manage_data = RiskManageTable(symbolist, i, balance)
            lastUpdate.status = f"Scaning {risk_manage_data.symbol}"

            data = await bot_1(
                risk_manage_data.symbol,
                ta_table_data.__dict__,
                risk_manage_data.timeframe,
            )

            positions = balance["info"]["positions"]
            status = pd.DataFrame(
                [
                    position
                    for position in positions
                    if float(position["positionAmt"]) != 0
                ],
                columns=statcln,
            )

            margin = 0.0
            config = AppConfig()
            max_margin = config.max_margin
            min_balance = config.min_balance
            margin = float((status["initialMargin"]).astype("float64").sum())

            if margin > max_margin:
                notify_send(
                    f"Margin ที่ใช้สูงเกินไปแล้ว\nMargin : {margin}\n",
                    f"ที่กำหนดไว้ : {max_margin}",
                    sticker=17857,
                    package=1070,
                )
                pass

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
            pass


async def waiting():
    text_time = f"{colorCS.CYELLOW} เวลา {colorCS.CGREEN}"
    time_now = f"{(lastUpdate.candle)[:-10].replace('T',text_time)}"
    balance = await fetching_balance()
    positions = balance["info"]["positions"]
    status = pd.DataFrame(
        [
            position
            for position in positions
            if float(position["positionAmt"]) != 0
        ],
        columns=statcln,
    )
    status["unrealizedProfit"] = (
        (status["unrealizedProfit"]).astype("float64").round(2)
    )

    status["initialMargin"] = (status["initialMargin"]).astype("float64")
    margin = float((status["initialMargin"]).astype("float64").sum())
    netunpl = float((status["unrealizedProfit"]).astype("float64").sum())
    status.rename(columns=common_names, errors="ignore", inplace=True)
    print(tabulate(status, showindex=False, headers="keys"))
    try:
        print(
            f"Margin Used : {colorCS.CBOLD + colorCS.CRED}{round(margin, 3)} ${colorCS.CEND}"  # noqa:
            + f"  NET P/L : {colorCS.CBOLD + colorCS.CGREEN}{round(netunpl, 3)} ${colorCS.CEND}"  # noqa:
            + f" Balance : BUSD {colorCS.CBOLD + colorCS.CGREEN}{lastUpdate.balance['BUSD']} ${colorCS.CEND}"  # noqa:
            + f" USDT {colorCS.CBOLD + colorCS.CGREEN}{lastUpdate.balance['USDT']} ${colorCS.CEND}"  # noqa:
        )
    except Exception:  # noqa:
        print(
            f"Margin Used : {colorCS.CBOLD + colorCS.CRED}{round(margin, 3)} ${colorCS.CEND}"  # noqa:
            + f"  NET P/L : {colorCS.CBOLD + colorCS.CGREEN}{round(netunpl, 3)} ${colorCS.CEND}"  # noqa:
            + f" Balance : {colorCS.CBOLD + colorCS.CGREEN}{lastUpdate.balance} ${colorCS.CEND}"  # noqa:
        )
    print(
        "\r"
        + colorCS.CRED
        + colorCS.CBOLD
        + f"Update : {colorCS.CGREEN}"
        + time_now
        + colorCS.CRED
        + f"{colorCS.CRED} Status : "
        + colorCS.CEND
        + f"{lastUpdate.status}",
        end="\n",
    )


async def get_waiting_time():
    symbolist = bot_setting()
    try:
        timer.min_timewait = min(
            TIMEFRAME_SECONDS[x] for x in symbolist["timeframe"]
        )
        if timer.min_timewait >= 3600:
            timer.min_timewait = 1800
        timer.min_timeframe = next(
            i
            for i in symbolist["timeframe"]
            if TIMEFRAME_SECONDS[i] == timer.min_timewait
        )
        lastUpdate.candle = f"{datetime.now().isoformat()}"
        await running_module()
        timer.next_candle = timer.last_closed + timer.min_timewait
    except Exception:
        tasks = asyncio.current_task()
        clearconsol()
        tasks.cancel()
        raise ConnectionError


async def warper_fn():
    while True:
        try:
            local_time = time.ctime(time.time())

            symbolist = bot_setting()
            if symbolist is None or symbolist.empty:
                lastUpdate.status = "Idle"
                await asyncio.sleep(60)
                return

            if timer.min_timewait != min(
                TIMEFRAME_SECONDS[x] for x in symbolist["timeframe"]
            ):
                print("detected new settings")
                await get_waiting_time()

            if str(local_time[14:-9]) == "1" or str(local_time[14:-9]) == "3":
                insession["day"] = False
                insession["hour"] = False
            if str(local_time[11:-9]) == "07:0" and not insession["day"]:
                insession["day"] = True
                insession["hour"] = True
                alrnotify.symbols = []
                await asyncio.gather(dailyreport())
                await hourly_report()

            if str(local_time[14:-9]) == "0" and not insession["hour"]:
                await hourly_report()
                await waiting()

            t1 = time.time()
            if t1 >= timer.next_candle:
                lastUpdate.candle = f"{datetime.now().isoformat()}"
                await running_module()
                timer.next_candle += timer.min_timewait
            else:
                await asyncio.sleep(round(timer.next_candle - t1))

        except Exception as e:
            lastUpdate.status = f"{e}"
            print(e)
            notify_send(f"เกิดข้อผิดพลาดภายนอก\n{e}\nบอทเข้าสู่ Sleep Mode")
            lastUpdate.status = "Sleep Mode"
            await asyncio.sleep(60)
            tasks = asyncio.current_task()
            clearconsol()
            tasks.cancel()
            raise ConnectionError


async def run_bot():
    config = AppConfig()
    if config.notify_token == "":
        await asyncio.sleep(60)
        return
    print(f"{colorCS.CBOLD}{colorCS.CGREEN}{bot_name}{colorCS.CEND}")
    try:
        await get_currentmode()
        await get_waiting_time()
        await waiting()
        await asyncio.gather(warper_fn())
    except Exception as e:
        notify_send(f"บอทเข้าสู่สถานะ Fallback Mode\n{e}")
        lastUpdate.status = "Fallback Mode : Restarting..."
        return
