#     DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#
# Copyright (c) 2022 vazw. All rights reserved.
#
# Licensed under the "THE BEER-WARE LICENSE" (Revision 42):
# Everyone is permitted to copy and distribute verbatim or modified
# copies of this license document, and changing it is allowed as long
# as the name is changed.
#
#     DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
# TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#     0. You just DO WHAT THE FUCK YOU WANT TO.

import asyncio
import datetime

import ccxt.async_support as ccxt
import moment
import pandas as pd

TIMEFRAME_SECONDS = {
    "1m": 60,
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
}


async def fetching_candle(symbol: str, timeframe: str) -> pd.DataFrame:
    df = pd.DataFrame(
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    needed_candle = TIMEFRAME_SECONDS[f"{timeframe}"] * -200000
    milisec_step = TIMEFRAME_SECONDS[f"{timeframe}"] * 1000
    for seconds in range(needed_candle, 0, milisec_step):
        try:
            await asyncio.sleep(50 / 100)
            exchange = ccxt.binance()
            currentDay = moment.utcnow()
            timeInepoch = currentDay.add(seconds=seconds).epoch(
                milliseconds=True
            )
            timeInepoch = None if seconds >= 0 else timeInepoch
            bars = await exchange.fetch_ohlcv(
                symbol, timeframe, timeInepoch, 1000
            )
            data = pd.DataFrame(
                bars,
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ],
            )
            data["timestamp"] = pd.to_datetime(
                data["timestamp"], unit="ms", utc=True
            ).map(lambda x: x.tz_convert("Asia/Bangkok"))
            df = pd.concat([df, data], axis=0, ignore_index=True)
            print(df)
            await exchange.close()
        except Exception as e:
            print(e)
            await exchange.close()
            exchange = ccxt.binance()
            timeInepoch = currentDay.add(seconds=seconds).epoch(
                milliseconds=True
            )
            timeInepoch = None if seconds >= 0 else timeInepoch
            bars = await exchange.fetch_ohlcv(
                symbol, timeframe, timeInepoch, 1000
            )
            data = pd.DataFrame(
                bars,
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ],
            )
            data["timestamp"] = pd.to_datetime(
                data["timestamp"], unit="ms", utc=True
            ).map(lambda x: x.tz_convert("Asia/Bangkok"))
            df = pd.concat([df, data], axis=0, ignore_index=True)
            print(df)
    await exchange.close()
    df = df.set_index("timestamp")
    df = df.sort_index()
    return df.drop_duplicates()


async def downloadMultiCandle(symbols: list, tflist: list) -> None:
    for symbol in symbols:
        for tf in tflist:
            df = await fetching_candle(symbol, tf)
            print(df)
            df.to_csv(f"data/{symbol.replace('/','')}_{tf}.csv")


async def downloadCandle(symbol: str, timeframe: str):
    return await fetching_candle(symbol, timeframe)
