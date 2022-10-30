# The BEERWARE License (BEERWARE)
#
# Copyright (c) 2022 Author. All rights reserved.
#
# Licensed under the "THE BEER-WARE LICENSE" (Revision 42):
# vazw wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer or coffee in return


import sqlite3
from dataclasses import dataclass

import bcrypt
import pandas as pd

barsC = 1502


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


class risk_manage:
    def __init__(self, symbolist, free_balance):
        self.symbol = symbolist["symbol"][0]
        if self.symbol[0:4] == "1000":
            self.symbol = self.symbol[4 : len(self.symbol)]
        self.timeframe = symbolist["timeframe"][0]
        self.use_long = self.check_bool(symbolist["Uselong"][0])
        self.use_short = self.check_bool(symbolist["Useshort"][0])
        self.use_tp_1 = self.check_bool(symbolist["UseTP1"][0])
        self.use_tp_2 = self.check_bool(symbolist["UseTP2"][0])
        self.use_sl = self.check_bool(symbolist["UseSL"][0])
        self.use_tailing = self.check_bool(symbolist["Tail_SL"])
        self.max_size = max_margin_size(
            str(symbolist["Max_Size"][0]), free_balance
        )
        self.risk_size = str(symbolist["Risk"][0])
        self.tp_percent = symbolist["TP1"][0]
        self.tp_percent_2 = symbolist["TP2"][0]
        self.risk_reward_1 = symbolist["RR1"][0]
        self.risk_reward_2 = symbolist["RR2"][0]
        self.leverage = symbolist["leverage"][0]

    def check_bool(self, arg):
        return True if str(arg).lower() == "true" else False


@dataclass
class ta_table:
    atr_p: int = 12
    atr_m: float = 1.6
    ema: int = 30
    linear: int = 30
    smooth: int = 30
    rsi: int = 25
    aol: int = 30
    pivot: int = 60
