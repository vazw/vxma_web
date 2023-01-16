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
import pandas as pd
from datetime import datetime as dt
import time

from vxma_d.AppData.Appdata import candle, notify_send
from vxma_d.AppData.Appdata import bot_setting, RiskManageTable, AppConfig
from vxma_d.AppData.Bot import (
    scanSideway,
    running_module,
    waiting,
    hourly_report,
)
from vxma_d.MarketEX.CCXT_Binance import (
    connect,
    connect_loads,
    fetchbars,
    fetching_balance,
    disconnect,
    get_symbol,
    getAllsymbol,
    OpenLong,
    get_bidask,
)
from vxma_d.Strategy.vxma_talib import vxma

symbols = [
    "BTC/USDT",
    "ETH/USDT",
    "APT/USDT",
    "GALA/USDT",
    "XRP/USDT",
    "SOL/USDT",
    "FTT/USDT",
    "DOGE/USDT",
    "LTC/USDT",
    "ETC/USDT",
    "OCEAN/USDT",
    "WOO/USDT",
    "BNB/USDT",
    "APE/USDT",
    "ADA/USDT",
    "SRM/USDT",
    "1000SHIB/USDT",
    "MATIC/USDT",
    "LINK/USDT",
    "AVAX/USDT",
    "LDO/USDT",
    "CHZ/USDT",
    "CRV/USDT",
    "NEAR/USDT",
    "GMT/USDT",
    "SAND/USDT",
    "OP/USDT",
    "DYDX/USDT",
    "ZIL/USDT",
    "EOS/USDT",
    "RLC/USDT",
    "MASK/USDT",
    "AXS/USDT",
    "DOT/USDT",
    "FTM/USDT",
    "FIL/USDT",
    "LUNA2/USDT",
    "ATOM/USDT",
    "SUSHI/USDT",
    "PEOPLE/USDT",
    "RAY/USDT",
    "TRX/USDT",
    "BNX/USDT",
    "MANA/USDT",
    "BCH/USDT",
    "1000LUNC/USDT",
    "GRT/USDT",
    "DENT/USDT",
    "XMR/USDT",
    "LIT/USDT",
    "KAVA/USDT",
    "HOT/USDT",
    "CELO/USDT",
    "JASMY/USDT",
    "WAVES/USDT",
    "REEF/USDT",
    "AAVE/USDT",
    "ANKR/USDT",
    "THETA/USDT",
    "XLM/USDT",
    "TLM/USDT",
    "DASH/USDT",
    "SC/USDT",
    "ZEC/USDT",
    "REN/USDT",
    "UNI/USDT",
    "BAND/USDT",
    "ALGO/USDT",
    "TRB/USDT",
    "ICP/USDT",
    "EGLD/USDT",
    "KNC/USDT",
    "YFI/USDT",
    "CVC/USDT",
    "FOOTBALL/USDT",
    "RUNE/USDT",
    "MKR/USDT",
    "LPT/USDT",
    "SXP/USDT",
    "IMX/USDT",
    "MTL/USDT",
    "STORJ/USDT",
    "1INCH/USDT",
    "ENS/USDT",
    "ALPHA/USDT",
    "COMP/USDT",
    "FLOW/USDT",
    "BAL/USDT",
    "VET/USDT",
    "AR/USDT",
    "OMG/USDT",
    "LINA/USDT",
    "XTZ/USDT",
    "KSM/USDT",
    "XEM/USDT",
    "UNFI/USDT",
    "GAL/USDT",
    "STMX/USDT",
    "ANT/USDT",
    "ENJ/USDT",
    "RSR/USDT",
    "C98/USDT",
    "QTUM/USDT",
    "HBAR/USDT",
    "SNX/USDT",
    "NEO/USDT",
    "IOTX/USDT",
    "ZEN/USDT",
    "BTS/USDT",
    "ONE/USDT",
    "HNT/USDT",
    "KLAY/USDT",
    "ROSE/USDT",
    "AUDIO/USDT",
    "LRC/USDT",
    "ALICE/USDT",
    "GTC/USDT",
    "STG/USDT",
    "QNT/USDT",
    "COTI/USDT",
    "OGN/USDT",
    "IOTA/USDT",
    "ZRX/USDT",
    "BAT/USDT",
    "CHR/USDT",
    "FLM/USDT",
    "SFP/USDT",
    "RVN/USDT",
    "NKN/USDT",
    "CELR/USDT",
    "ATA/USDT",
    "IOST/USDT",
    "DGB/USDT",
    "SKL/USDT",
    "BEL/USDT",
    "1000XEC/USDT",
    "API3/USDT",
    "BLZ/USDT",
    "CVX/USDT",
    "INJ/USDT",
    "ONT/USDT",
    "CTSI/USDT",
    "ICX/USDT",
    "DAR/USDT",
    "CTK/USDT",
    "BTCDOM/USDT",
    "BAKE/USDT",
    "SPELL/USDT",
    "DUSK/USDT",
    "ARPA/USDT",
    "TOMO/USDT",
    "DEFI/USDT",
    "BLUEBIRD/USDT",
]

tflist = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"]

symbol = "BTC/USDT"
tf = "6h"


async def main():
    df = await fetchbars(symbol, tf)
    # bot = vxma(df)
    # df = bot.indicator()
    print(df.tail(2000))
    # df.to_csv(f"data/{symbol.replace('/','')}_{tf}.csv")
    # candle(df, symbol, tf)


async def test_scan():
    symbols = await scanSideway()
    print(symbols)
    print(len(symbols))


async def load_info():
    profit_loss = pd.DataFrame(columns=["symbol", "$P/L"])
    exchange = await connect()
    for symbol in symbols:
        trade_history = await exchange.fetch_my_trades(symbol, limit=1)
        pnl = sum(
            [
                float(history["info"]["realizedPnl"])
                for history in trade_history
                if history["info"]["realizedPnl"] != 0
            ]
        )

        profit_loss = profit_loss.append(
            {"symbol": symbol, "$P/L": pnl}, ignore_index=True
        )
    await disconnect(exchange)
    profit_loss = profit_loss.sort_values(by=["$P/L"], ascending=False)
    profit_loss = profit_loss[profit_loss["$P/L"] != 0.0]
    print(profit_loss.head(10).to_string(index=False))
    print(profit_loss["$P/L"].sum())


async def makepairlist():
    exchange = await connect()
    try:
        market = await exchange.fetch_tickers(params={"type": "future"})
    except Exception as e:
        print(e)
        market = await exchange.fetch_tickers(params={"type": "future"})
    await disconnect(exchange)
    symbols = pd.DataFrame(
        [
            y
            for x, y in market.items()
            if x.endswith("USDT")
            # or x.endswith("BUSD")
        ]
    )
    symbols = symbols.sort_values(by=["quoteVolume"], ascending=False)
    symbols = symbols.head(100)
    newsym = [symbol[:-5] for symbol in symbols["symbol"]]
    return newsym


async def min_amount():
    exchange = await connect()
    markets = await exchange.fetchMarkets()
    this_symbol = "DEFI/USDT"
    min_amount = (
        data for data in markets if data["symbol"] == this_symbol
    ).__next__()

    print(min_amount)
    # ["limits"]["amount"]["min"]
    # order = await exchange.create_market_order(
    #     this_symbol,
    #     "sell",
    #     min_amount,
    #     params={"positionSide": "SHORT"},
    # )
    # print(order)
    await disconnect(exchange)


async def fetching_fiat_balance():
    exchange = await connect()
    bbalance = await exchange.fetch_balance()
    await disconnect(exchange)
    balance = {x: y for x, y in bbalance.items() if x == "USDT" or x == "BUSD"}
    balance_data = pd.DataFrame(balance, dtype="float").round(2)
    # msg = (
    #     f"Free Balance\nBUSD : {balance['BUSD']['free']}$"
    #     + f"\nMargin \nBUSD : {balance['BUSD']['used']}$"
    #     + f"\nTotal Balance\nBUSD : {balance['BUSD']['total']}$"
    #     + f"\nUSDT : {balance['USDT']['free']}$"
    #     + f"\nUSDT : {balance['USDT']['used']}$"
    #     + f"\nUSDT : {balance['USDT']['total']}$"
    # )
    notify_send(balance_data.to_string())


async def balance():

    exchange = await connect()
    balance = await exchange.fetch_balance()
    await disconnect(exchange)
    positions = balance["info"]["positions"]
    status = pd.DataFrame(
        [
            position
            for position in positions
            if float(position["positionAmt"]) != 0
        ],
        columns=[
            "symbol",
            "entryPrice",
            "positionSide",
            "unrealizedProfit",
            "positionAmt",
            "initialMargin",
            "leverage",
        ],
        dtype="float",
    )
    posim = "DEFIUSDT"
    status = status[status["symbol"] == posim]
    print(status)
    if status.empty:
        amt_short = 0.0
        amt_long = 0.0
        upnl_short = 0.0
        upnl_long = 0.0
    elif len(status.index) > 1:
        amt_long = (
            status["positionAmt"][i]
            for i in status.index
            if status["symbol"][i] == posim
            and status["positionSide"][i] == "LONG"
        ).__next__()
        amt_short = (
            status["positionAmt"][i]
            for i in status.index
            if status["symbol"][i] == posim
            and status["positionSide"][i] == "SHORT"
        ).__next__()
        upnl_long = (
            status["unrealizedProfit"][i]
            for i in status.index
            if status["symbol"][i] == posim
            and status["positionSide"][i] == "LONG"
        ).__next__()
        upnl_short = (
            status["unrealizedProfit"][i]
            for i in status.index
            if status["symbol"][i] == posim
            and status["positionSide"][i] == "SHORT"
        ).__next__()
    else:
        amt = (
            status["positionAmt"][i]
            for i in status.index
            if status["symbol"][i] == posim
        ).__next__()
        amt_long = amt if amt > 0.0 else 0.0
        amt_short = amt if amt < 0.0 else 0.0
        upnl = (
            status["unrealizedProfit"][i]
            for i in status.index
            if status["symbol"][i] == posim
        ).__next__()
        upnl_long = upnl if amt != 0.0 else 0.0
        upnl_short = upnl if amt != 0.0 else 0.0

    print(amt_long, amt_short)
    print(upnl_long, upnl_short)


TIMEFRAME_SECONDS = {
    "1m": 1,
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

config_timeframe = ["15m", "30m", "1h", "6h"]


async def tester():
    # top10 = await get_symbol()
    # allsym = await getAllsymbol()
    # print(allsym)
    min_timewait = min(TIMEFRAME_SECONDS[x] for x in config_timeframe)
    min_timeframe = next(
        i for i in config_timeframe if TIMEFRAME_SECONDS[i] == min_timewait
    )
    # print(top10)
    # await hourly_report()
    print(min_timeframe)
    print(min_timewait)
    t1 = time.time()
    print(t1)


async def tester02():
    symbols = await makepairlist()
    print(symbols)
    print(len(symbols))


async def tester_order():
    balance = await fetching_balance()
    config = AppConfig()
    min_balance = config.min_balance
    symbolist = bot_setting()
    df = await fetchbars("DEFI/USDT:USDT", "30m")
    bot = vxma(df)
    df = bot.indicator()
    risk_manage_data = RiskManageTable(symbolist, 9, balance)
    print(risk_manage_data.symbol)

    await OpenLong(df, balance, risk_manage_data.__dict__, "LONG", min_balance)


async def tester_balance():
    symbol = "BTC/USDT:USDT"
    exchange = await connect_loads()

    # symbols = []
    ask = await get_bidask(symbol, exchange, "ask")
    # info = await exchange.fetch_bids_asks()
    print(ask)
    await disconnect(exchange)
    # print(info)
    # for x, y in info.items():
    #     symbols.append(x)
    # print(symbols)
    # print(len(symbols))


if __name__ == "__main__":
    # asyncio.run(tester_order())
    asyncio.run(tester_balance())
    # print(dt.now().timestamp())
