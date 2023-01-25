# The BEERWARE License (BEERWARE)
#
# Copyright (c) 2022 Author. All rights reserved.
#
# Licensed under the "THE BEER-WARE LICENSE" (Revision 42):
# vazw wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer or coffee in return

from datetime import datetime
import os
import sqlite3
from dataclasses import dataclass

import bcrypt
import mplfinance as mplf
import pandas as pd
from line_notify import LineNotify

barsC = 1502


rcs = {
    "axes.labelcolor": "white",
    "axes.spines.left": False,
    "axes.spines.right": False,
    "axes.axisbelow": False,
    "axes.grid": True,
    "grid.linestyle": ":",
    "axes.titlesize": "xx-large",
    "axes.titleweight": "bold",
}


colors_candle = mplf.make_marketcolors(
    up="black",
    down="white",
    wick="white",
    edge="white",
    volume={"up": "green", "down": "red"},
)
style_candle = mplf.make_mpf_style(
    base_mpf_style="nightclouds",
    rc=rcs,
    y_on_right=False,
    marketcolors=colors_candle,
    figcolor="black",
    gridaxis="horizontal",
    facecolor="black",
)

BOTCOL = [
    "id",
    "symbol",
    "timeframe",
    "ATR",
    "ATR_m",
    "EMA",
    "subhag",
    "smooth",
    "RSI",
    "Andean",
    "Uselong",
    "Useshort",
    "UseTP",
    "UseTP2",
    "UseSL",
    "Tail_SL",
    "leverage",
    "Pivot",
    "RR1",
    "RR2",
    "TP1",
    "TP2",
    "Risk",
    "maxMargin",
    "hedge",
    "hedgeTF",
]


def bot_setting() -> pd.DataFrame:
    try:
        symbolist = pd.read_csv("bot_config.csv")
        return symbolist
    except Exception as e:
        print(e)
        return pd.DataFrame()


def config_setting():
    try:
        with sqlite3.connect("vxma.db", check_same_thread=False) as con:
            config = pd.read_sql("SELECT * FROM key", con=con)
        return config
    except Exception as e:
        print(e)
        return None


def cooking(id, pwd):
    try:
        pepper = f"{id}{pwd}!{barsC}vz{id}"
        bytePwd = pepper.encode("utf-8")
        Salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(bytePwd, Salt)
    except Exception as e:
        print(e)
        return None


def perf(id, pwd):
    hash1 = "X"
    try:
        with sqlite3.connect("vxma.db", check_same_thread=False) as con:
            bata = pd.read_sql("SELECT * FROM user", con=con)
        iid = bata["id"][0]
        if iid == id:
            hash1 = bata["pass"][0]
        egg = f"{id}{pwd}!{barsC}vz{id}"
        bytePwd = egg.encode("utf-8")
        return bcrypt.checkpw(bytePwd, hash1)
    except Exception as e:
        print(e)
        return None


def max_margin_size(size, free_balance) -> float:
    Max_Size = size
    if Max_Size[0] == "$":
        Max_Size = float(Max_Size[1 : len(Max_Size)])
        return Max_Size
    elif Max_Size[0] == "%":
        size = float(Max_Size[1 : len(Max_Size)])
        Max_Size = free_balance * (size / 100)
        return Max_Size
    else:
        Max_Size = float(Max_Size)
        return Max_Size


class RiskManageTable:
    def __init__(self, symbolist, col_index, balance):
        self.symbol = symbolist["symbol"][col_index]
        self.quote = "BUSD" if self.symbol.endswith("BUSD") else "USDT"
        # if self.symbol[0:4] == "1000":
        #     self.symbol = self.symbol[4 : len(self.symbol)]
        self.timeframe = symbolist["timeframe"][col_index]
        self.use_long = self.check_bool(symbolist["Uselong"][col_index])
        self.use_short = self.check_bool(symbolist["Useshort"][col_index])
        self.use_tp_1 = self.check_bool(symbolist["UseTP"][col_index])
        self.use_tp_2 = self.check_bool(symbolist["UseTP2"][col_index])
        self.use_sl = self.check_bool(symbolist["UseSL"][col_index])
        self.use_tailing = self.check_bool(symbolist["Tail_SL"][col_index])
        self.free_balance = float(balance["free"][self.quote])
        self.max_size = max_margin_size(
            str(symbolist["maxMargin"][col_index]), self.free_balance
        )
        self.risk_size = str(symbolist["Risk"][col_index])
        self.tp_percent = symbolist["TP1"][col_index]
        self.tp_percent_2 = symbolist["TP2"][col_index]
        self.risk_reward_1 = symbolist["RR1"][col_index]
        self.risk_reward_2 = symbolist["RR2"][col_index]
        self.leverage = symbolist["leverage"][col_index]
        self.usehedge = self.check_bool(symbolist["hedge"][col_index])
        self.hedge_timeframe = symbolist["hedgeTF"][col_index]

    def check_bool(self, arg) -> bool:
        return True if str(arg).lower() == "true" else False


class Notified:
    """List of notified SL."""

    def __init__(self):
        self.symbols = []
        self.orders = []


@dataclass
class Last_update:
    candle: str = "T -- ----------"
    balance: any = "--"
    status: str = "Starting"


@dataclass
class Timer:
    min_timewait: int = 1
    min_timeframe: str = "1m"
    last_closed: any = 0.0
    next_candle: any = 0.0


@dataclass
class PositionMode:
    dualSidePosition: bool = False
    Sside: str = "BOTH"
    Lside: str = "BOTH"


# ansi escape code
@dataclass
class ColorCS:
    CLS_SCREEN: str = "\033[2J\033[1;1H"  # cls + set top left
    CLS_LINE: str = "\033[0J"
    SHOW_CURSOR: str = "\033[?25h"
    HIDE_CURSOR: str = "\033[?25l"
    CRED: str = "\33[31m"
    CGREEN: str = "\33[32m"
    CYELLOW: str = "\33[33m"
    CEND: str = "\033[0m"
    CBOLD: str = "\33[1m"


@dataclass
class TATable:
    atr_p: int = 12
    atr_m: float = 1.6
    ema: int = 30
    linear: int = 30
    smooth: int = 30
    rsi: int = 25
    aol: int = 30
    pivot: int = 60


class AppConfig:
    """Get config for global App."""

    def __init__(self):
        config = config_setting()
        max_margin = "$10"
        MIN_BALANCE = "$50"
        if not config.empty:
            max_margin = str(config["freeB"][0])
            MIN_BALANCE = str(config["minB"][0])
            API_KEY = str(config["apikey"][0])
            API_SECRET = str(config["apisec"][0])
            LINE_TOKEN = str(config["notify"][0])
        else:
            API_KEY = ""
            API_SECRET = ""
            LINE_TOKEN = ""
        if "API_KEY" in os.environ:
            API_KEY = str(os.environ["API_KEY"])
            API_SECRET = str(os.environ["API_SECRET"])
            LINE_TOKEN = str(os.environ["Line_Notify_Token"])
        if MIN_BALANCE[0] == "$":
            self.min_balance = float(MIN_BALANCE[1 : len(MIN_BALANCE)])
        else:
            self.min_balance = float(MIN_BALANCE)
        if max_margin[0] == "$":
            self.max_margin = float(max_margin[1 : len(max_margin)])
        else:
            self.max_margin = float(max_margin)
        self.notify_token = LINE_TOKEN
        self.BNBCZ = {
            "apiKey": API_KEY,
            "secret": API_SECRET,
            "options": {"defaultType": "future"},
            "enableRateLimit": True,
            "adjustForTimeDifference": True,
        }


def notify_send(msg, sticker=None, package=None, image_path=None):
    config = AppConfig()
    notify = LineNotify(config.notify_token)
    try:
        if image_path is not None:
            notify.send(msg, image_path=image_path)
        elif sticker is not None:
            notify.send(
                msg,
                sticker_id=sticker,
                package_id=package,
            )
        else:
            notify.send(msg)
    except Exception as e:
        print(e)


def candle(df, symbol, tf):
    data = df.tail(60)
    titles = f"{symbol}_{tf}"
    try:
        vxma = mplf.make_addplot(
            data.vxma, secondary_y=False, color="yellow", linewidths=0.2
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
            style=style_candle,
            volume=True,
            savefig="candle.png",
            tight_layout=True,
            figratio=(9, 9),
            datetime_format="%y/%b/%d %H:%M",
            xrotation=20,
        )
    except Exception as e:
        print(e)
        mplf.plot(
            data,
            type="candle",
            title=titles,
            style=style_candle,
            volume=True,
            savefig="candle.png",
            tight_layout=True,
            figratio=(9, 9),
            datetime_format="%y/%b/%d %H:%M",
            xrotation=20,
        )
    return notify_send(f"{titles}", image_path=("/candle.png"))


def clearconsol():
    try:
        if os.name == "posix":
            os.system("clear")
        else:
            os.system("cls")
    except Exception as e:
        print(e)


def write_trade_record(
    timestamp: datetime,
    symbol: str,
    amount: float,
    price: float,
    direction: str,
    tp: any = None,
    sl: float = None,
    pnl: float = None,
):
    # Create a dataframe from the input data
    df = pd.DataFrame(
        {
            "DateTime": [timestamp],
            "Symbol": [symbol],
            "Amount": [amount],
            "Price": [price],
            "Position": [direction],
            "TP/SL": [f"{tp}/{sl}"],
            "PNL$": [f"{round(pnl,2) if pnl is not None else None}"],
        }
    )

    # Append the dataframe to the CSV file
    df.to_csv("trades.csv", mode="a", index=False, header=False)
