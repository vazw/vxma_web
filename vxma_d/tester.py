# The BEERWARE License (BEERWARE)
#
# Copyright (c) 2022 Author. All rights reserved.
#
# Licensed under the "THE BEER-WARE LICENSE" (Revision 42):
# vazw wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer or coffee in return

# def menuInpput():
#     menuList = ["input1", "input2", "input3", "input4"]
#     input_result = []
#     for i in menuList:
#         input = dmc.NumberInput(
#             label=f"{i}",
#             id=f"{i}-input",
#             style={"width": 75},
#         )
#         input_result.append(input)
#     return input_result

import sqlite3

import pandas as pd


def bot_setting():
    symbolist = pd.read_csv("appData/bot_config.csv")
    return symbolist


def config_setting():
    with sqlite3.connect("appData/vxma.db", check_same_thread=False) as con:
        config = pd.read_sql("SELECT * FROM key", con=con)
    return config


if __name__ == "__main__":
    print(config_setting())
    print(bot_setting())
