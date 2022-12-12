# The BEERWARE License (BEERWARE)
#
# Copyright (c) 2022 Author. All rights reserved.
#
# Licensed under the "THE BEER-WARE LICENSE" (Revision 42):
# vazw wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer or coffee in return

import asyncio
import os
import sqlite3
from dataclasses import dataclass

import bcrypt
import mplfinance as mplf
import pandas as pd
from line_notify import LineNotify

barsC = 1502

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


def bot_setting():
    symbolist = pd.read_csv("vxma_d/AppData/bot_config.csv")
    return symbolist


def config_setting():
    with sqlite3.connect(
        "vxma_d/AppData/vxma.db", check_same_thread=False
    ) as con:
        config = pd.read_sql("SELECT * FROM key", con=con)
    return config


def cooking(id, pwd):
    pepper = f"{id}{pwd}!{barsC}vz{id}"
    bytePwd = pepper.encode("utf-8")
    Salt = bcrypt.gensalt(rounds=12)
    cook = bcrypt.hashpw(bytePwd, Salt)
    return cook


def perf(id, pwd):
    hash1 = "X"
    with sqlite3.connect(
        "vxma_d/AppData/vxma.db", check_same_thread=False
    ) as con:
        bata = pd.read_sql("SELECT * FROM user", con=con)
    iid = bata["id"][0]
    if iid == id:
        hash1 = bata["pass"][0]
    egg = f"{id}{pwd}!{barsC}vz{id}"
    bytePwd = egg.encode("utf-8")
    proof = bcrypt.checkpw(bytePwd, hash1)
    return proof


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
    async def __init__(self, symbolist, free_balance):
        self.symbol = symbolist["symbol"][0]
        if self.symbol[0:4] == "1000":
            self.symbol = self.symbol[4 : len(self.symbol)]
        self.timeframe = symbolist["timeframe"][0]
        self.use_long = await self.check_bool(symbolist["Uselong"][0])
        self.use_short = await self.check_bool(symbolist["Useshort"][0])
        self.use_tp_1 = await self.check_bool(symbolist["UseTP1"][0])
        self.use_tp_2 = await self.check_bool(symbolist["UseTP2"][0])
        self.use_sl = await self.check_bool(symbolist["UseSL"][0])
        self.use_tailing = await self.check_bool(symbolist["Tail_SL"])
        self.max_size = max_margin_size(
            str(symbolist["Max_Size"][0]), free_balance
        )
        self.risk_size = str(symbolist["Risk"][0])
        self.tp_percent = symbolist["TP1"][0]
        self.tp_percent_2 = symbolist["TP2"][0]
        self.risk_reward_1 = symbolist["RR1"][0]
        self.risk_reward_2 = symbolist["RR2"][0]
        self.leverage = symbolist["leverage"][0]

    async def check_bool(self, arg):
        return True if str(arg).lower() == "true" else False


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
    if image_path is not None:
        notify.send(message=msg, image_path=image_path)
    elif sticker is not None:
        notify.send(
            msg,
            sticker_id=sticker,
            package_id=package,
        )
    else:
        notify.send(msg)


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
    notify_send(f"info : {titles}", image_path=("./candle.png"))
    asyncio.sleep(0.5)
    return
