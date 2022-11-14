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
import time

import ccxt.async_support as ccxt
import pandas as pd


class Download_Candle:
    """Download Candle Stick for backtesting
    which we'll Download more than 1500 Candle on a loop
    with ccxt limited it 1500 candle at a times"""

    def __init__(self, symbol, timeframe):
        self.symbol = symbol
        self.timeframe = timeframe

    async def fetching_candle(self):
        exchange = ccxt.binance()
        bars = await exchange.fetch_ohlcv(self.symbol, self.timeframe)
        df = pd.DataFrame(
            bars,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        await exchange.close()

        return df
