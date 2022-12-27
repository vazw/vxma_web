# The BEERWARE License (BEERWARE)
#
# Copyright (c) 2022 Author. All rights reserved.
#
# Licensed under the "THE BEER-WARE LICENSE" (Revision 42):
# vazw wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer or coffee in return

# def menuInpput():
#     menuList = ["input1", "input2", "input3", "input4"]:
#     input_result = []
#     for i in menuList:
#         input = dmc.NumberInput(
#             label=f"{i}",
#             id=f"{i}-input",
#             style={"width": 75},
#         )
#         input_result.append(input)
#     return input_result
import asyncio
import os

from vxma_d.AppData.Appdata import candle
from vxma_d.AppData.Bot import scanSideway
from vxma_d.Backtesting.Candle_ohlc import downloadCandle, downloadMultiCandle
from vxma_d.MarketEX.CCXT_Binance import connect, fetchbars
from vxma_d.Strategy.vxma_talib import vxma

symbols = ["BTC/USDT", "ETH/USDT"]
tflist = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"]

symbol = "BTC/USDT"
tf = "1d"


async def main():
    df = await fetchbars(symbol, tf)
    bot = vxma(df)
    df = bot.indicator()
    print(df)
    # df.to_csv(f"data/{symbol.replace('/','')}_{tf}.csv")
    candle(df, symbol, tf)


async def test_scan():
    symbols = await scanSideway()
    print(symbols)
    print(len(symbols))


async def load_info():
    exchange = await connect()
    balance = await exchange.fetch_balance()
    positions = balance["info"]["positions"]
    current_positions = [
        position
        for position in positions
        if float(position["positionAmt"]) != 0
    ]
    print(current_positions)


if __name__ == "__main__":
    asyncio.run(load_info())
    # asyncio.run(test_scan())
