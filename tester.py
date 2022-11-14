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

from vxma_d.AppData.Candle_ohlc import Download_Candle


async def main():
    bot = Download_Candle("BTC/USDT", "1d")
    df = await bot.fetching_candle()
    print(df.tail())
    # print(await bot.fetching_candle())


if __name__ == "__main__":
    asyncio.run(main())
