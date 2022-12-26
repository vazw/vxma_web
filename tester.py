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

import mplfinance as mplf

from vxma_d.AppData.Bot import scanSideway
from vxma_d.Backtesting.Candle_ohlc import downloadCandle, downloadMultiCandle

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


def candle(df, symbol, tf):
    data = df
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
            tight_layout=True,
            figratio=(9, 9),
            datetime_format="%y/%b/%d %H:%M",
            xrotation=20,
        )
    return


symbols = ["BTC/USDT", "ETH/USDT"]
tflist = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"]

symbol = "BTC/USDT"
tf = "1m"


async def main():
    df = await downloadCandle(symbol, tf)
    print(df)
    df.to_csv(f"data/{symbol.replace('/','')}_{tf}.csv")
    candle(df, symbol, tf)


async def test_scan():
    symbols = await scanSideway()
    print(symbols)
    print(len(symbols))


if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.run(test_scan())
