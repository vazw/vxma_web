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
    if size[0] == "$":
        Max_Size = float(size[1 : len(size)])
        return Max_Size
    elif size[0] == "%":
        size = float(size[1 : len(size)])
        Max_Size = free_balance * (size / 100)
        return Max_Size
    else:
        Max_Size = float(size)
        return Max_Size


class RiskManageTable:
    def __init__(self, symbolist, balance):
        self.symbol = symbolist["symbol"]
        self.quote = "BUSD" if self.symbol.endswith("BUSD") else "USDT"
        # if self.symbol[0:4] == "1000":
        #     self.symbol = self.symbol[4 : len(self.symbol)]
        self.timeframe = symbolist["timeframe"]
        self.use_long = self.check_bool(symbolist["Uselong"])
        self.use_short = self.check_bool(symbolist["Useshort"])
        self.use_tp_1 = self.check_bool(symbolist["UseTP"])
        self.use_tp_2 = self.check_bool(symbolist["UseTP2"])
        self.use_sl = self.check_bool(symbolist["UseSL"])
        self.use_tailing = self.check_bool(symbolist["Tail_SL"])
        self.free_balance = float(balance["free"][self.quote])
        self.max_size = max_margin_size(
            str(symbolist["maxMargin"]), self.free_balance
        )
        self.risk_size = str(symbolist["Risk"])
        self.tp_percent = symbolist["TP1"]
        self.tp_percent_2 = symbolist["TP2"]
        self.risk_reward_1 = symbolist["RR1"]
        self.risk_reward_2 = symbolist["RR2"]
        self.leverage = symbolist["leverage"]
        self.usehedge = self.check_bool(symbolist["hedge"])
        self.hedge_timeframe = symbolist["hedgeTF"]

    def check_bool(self, arg) -> bool:
        return True if str(arg).lower() == "true" else False


class DefaultRiskTable:
    def __init__(self, symbol: str, balance):
        self.symbol = symbol
        self.quote = "BUSD" if self.symbol.endswith("BUSD") else "USDT"
        # if self.symbol[0:4] == "1000":
        #     self.symbol = self.symbol[4 : len(self.symbol)]
        self.timeframe = "6h"
        self.use_long = True
        self.use_short = True
        self.use_tp_1 = True
        self.use_tp_2 = False
        self.use_sl = True
        self.use_tailing = True
        self.free_balance = float(balance["free"][self.quote])
        self.max_size = 20
        self.risk_size = "%5"
        self.tp_percent = 50
        self.tp_percent_2 = 50
        self.risk_reward_1 = 2
        self.risk_reward_2 = 3
        self.leverage = 10
        self.usehedge = False
        self.hedge_timeframe = "15m"


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
    get_time: bool = False


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


def read_all_open_position_record():
    order_history = pd.read_csv("trades.csv")
    order_history = order_history[pd.isnull(order_history["ClosePrice"])]
    return order_history


def read_one_open_trade_record(
    symbol: str,
    timeframe: str,
    direction: str = "",
) -> pd.Series:
    order_history = pd.read_csv("trades.csv")
    position = None
    for id in order_history.index:
        if (
            order_history["Symbol"][id] == symbol
            and pd.isnull(order_history["ClosePrice"][id])
            and order_history["Position"][id] == direction
            and order_history["TF"][id] == timeframe
        ):
            position = order_history.loc[
                id,
            ]
            break
    return position


def write_trade_record(
    timestamp: datetime,
    symbol: str,
    timeframe: str,
    amount: float,
    price: float,
    direction: str,
    tp: any = None,
    sl: float = None,
) -> None:
    # Create a dataframe from the input data
    df = pd.DataFrame(
        {
            "EntryTime": [timestamp],
            "ExitTime": [None],
            "Symbol": [symbol],
            "TF": [timeframe],
            "Position": [direction],
            "Amount": [amount],
            "EntryPrice": [price],
            "ClosePrice": [None],
            "TP": [tp],
            "SL": [sl],
            "PNL$": [None],
        }
    )

    # Append the dataframe to the CSV file
    # df.to_csv("trades.csv", index=False, header=True)
    df.to_csv("trades.csv", mode="a", index=False, header=False)


def write_tp_record(
    timestamp: datetime,
    symbol: str,
    timeframe: str,
    direction: str,
    price: float,
    amount: float,
    saved_position: pd.Series,
) -> None:
    # Create a dataframe from the input data
    order_history = pd.read_csv("trades.csv")
    for id in order_history.index:
        if (
            order_history["Symbol"][id] == symbol
            and pd.isnull(order_history["ClosePrice"][id])
            and order_history["Position"][id] == direction
            and order_history["TF"][id] == timeframe
        ):

            order_history["ExitTime"][id] = timestamp
            order_history["ClosePrice"][id] = price
            order_history["Amount"][id] = amount

            if order_history["Position"][id] == "Long":
                order_history["PNL$"][id] = round(
                    (
                        order_history["ClosePrice"][id]
                        - order_history["EntryPrice"][id]
                    )
                    * order_history["Amount"][id],
                    3,
                )
            else:
                order_history["PNL$"][id] = round(
                    (
                        order_history["EntryPrice"][id]
                        - order_history["ClosePrice"][id]
                    )
                    * order_history["Amount"][id],
                    3,
                )
    # rewrite the whole dataframe to the CSV file
    order_history.to_csv("trades.csv", index=False, header=True)

    df = pd.DataFrame(
        {
            "EntryTime": [saved_position["EntryTime"]],
            "ExitTime": [None],
            "Symbol": [symbol],
            "TF": [timeframe],
            "Position": [direction],
            "Amount": [float(saved_position["Amount"]) - amount],
            "EntryPrice": [price],
            "ClosePrice": [None],
            "TP": [saved_position["TP"]],
            "SL": [saved_position["SL"]],
            "PNL$": [None],
        }
    )

    # Append the dataframe to the CSV file
    # df.to_csv("trades.csv", index=False, header=True)
    df.to_csv("trades.csv", mode="a", index=False, header=False)


def edit_trade_record(
    timestamp: datetime,
    symbol: str,
    timeframe: str,
    direction: str,
    price: float,
    isSl: bool = False,
) -> None:
    # Create a dataframe from the input data
    order_history = pd.read_csv("trades.csv")
    for id in order_history.index:
        if (
            order_history["Symbol"][id] == symbol
            and pd.isnull(order_history["ClosePrice"][id])
            and order_history["Position"][id] == direction
            and order_history["TF"][id] == timeframe
        ):
            order_history["ExitTime"][id] = timestamp
            if isSl:
                order_history["ClosePrice"][id] = order_history["SL"][id]
            else:
                order_history["ClosePrice"][id] = price

            if order_history["Position"][id] == "Long":
                order_history["PNL$"][id] = round(
                    (
                        order_history["ClosePrice"][id]
                        - order_history["EntryPrice"][id]
                    )
                    * order_history["Amount"][id],
                    3,
                )
            else:
                order_history["PNL$"][id] = round(
                    (
                        order_history["EntryPrice"][id]
                        - order_history["ClosePrice"][id]
                    )
                    * order_history["Amount"][id],
                    3,
                )
    # rewrite the whole dataframe to the CSV file
    order_history.to_csv("trades.csv", index=False, header=True)


def edit_all_trade_record(
    timestamp: datetime,
    symbol: str,
    direction: str,
    price: float,
    isSl: bool = False,
) -> None:
    # Create a dataframe from the input data
    order_history = pd.read_csv("trades.csv")
    for id in order_history.index:
        if (
            order_history["Symbol"][id] == symbol
            and pd.isnull(order_history["ClosePrice"][id])
            and order_history["Position"][id] == direction
        ):
            order_history["ExitTime"][id] = timestamp
            if isSl:
                order_history["ClosePrice"][id] = order_history["SL"][id]
            else:
                order_history["ClosePrice"][id] = price

            if order_history["Position"][id] == "Long":
                order_history["PNL$"][id] = round(
                    (
                        order_history["ClosePrice"][id]
                        - order_history["EntryPrice"][id]
                    )
                    * order_history["Amount"][id],
                    3,
                )
            else:
                order_history["PNL$"][id] = round(
                    (
                        order_history["EntryPrice"][id]
                        - order_history["ClosePrice"][id]
                    )
                    * order_history["Amount"][id],
                    3,
                )
    # rewrite the whole dataframe to the CSV file
    order_history.to_csv("trades.csv", index=False, header=True)
