import time
import warnings
from datetime import datetime as dt

import ccxt
import pandas as pd
import plotly.graph_objects as go

from appdata import risk_manage, ta_table
from vxmatalib import benchmarking as ta_score
from vxmatalib import vxma as ta

warnings.filterwarnings("ignore")
pd.set_option("display.max_rows", None)
# config = configparser.ConfigParser()
# config.read("config.ini")
# API_KEY = config["KEY"]["API_KEY"]
# API_SECRET = config["KEY"]["API_SECRET"]
# LINE_TOKEN = config['KEY']['LINE_TOKEN']
# notify = LineNotify(LINE_TOKEN)
# TF = "1m"
# API CONNECT


# idex = {
#     "apiKey": API_KEY,
#     "secret": API_SECRET,
#     "options": {"defaultType": "future"},
#     "enableRateLimit": True,
#     "adjustForTimeDifference": True,
# }
exchange = ccxt.binance()

# get OHLC info

# ta_table = {
#     "atr_p": 12,
#     "atr_m": 1.6,
#     "ema": 30,
#     "linear": 30,
#     "smooth": 30,
#     "rsi": 14,
#     "aol": 30,
#     "pivot": 60,
# }


def fetchbars(symbol, timeframe, exchange):
    bars = 2000
    print(
        f"Benchmarking new bars for {symbol , timeframe , dt.now().isoformat()}"
    )
    try:
        bars = exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, since=None, limit=bars
        )
    except Exception as e:
        print(e)
        time.sleep(2)
        bars = exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, since=None, limit=bars
        )
    df = pd.DataFrame(
        bars[:-1],
        columns=["timestamp", "Open", "High", "Low", "Close", "Volume"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).map(
        lambda x: x.tz_convert("Asia/Bangkok")
    )
    df = df.set_index("timestamp")
    return df


"""""
# Draw candle
def candle(data, symbol, tf):
    # data = df.tail(500)
    fig = go.Figure(
        data=go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            showlegend=False,
        ),
        layout=dict(autosize=True, title=f"{symbol}_{tf}"),
    )
    buy2 = go.Scatter(
        x=data.index,
        y=data["buyPrice"],
        mode="markers",
        marker=dict(size=20, color="purple"),
        hovertext="Buy",
        name="BUY",
    )
    sell2 = go.Scatter(
        x=data.index,
        y=data["sellPrice"],
        mode="markers",
        marker=dict(size=20, color="orange"),
        hovertext="Sell",
        name="SELL",
    )
    sar_d = go.Scatter(
        x=data.index,
        y=data["PSARs_0.02_0.2"],
        mode="markers",
        marker=dict(size=8, color="red"),
        showlegend=True,
        name="PSARs",
    )
    sar_u = go.Scatter(
        x=data.index,
        y=data["PSARl_0.02_0.2"],
        mode="markers",
        marker=dict(size=8, color="green"),
        showlegend=True,
        name="PSARl",
    )
    fig.add_trace(buy2)
    fig.add_trace(sell2)
    fig.add_trace(sar_d)
    fig.add_trace(sar_u)
    fig.update(layout_xaxis_rangeslider_visible=False)
    fig.show()
    return


data["adx"] = ta.ADX(data.High, data.Low, data.Close, 14)
data["adx+"] = ta.PLUS_DI(data.High, data.Low, data.Close, 14)
data["adx-"] = ta.MINUS_DI(data.High, data.Low, data.Close, 14)
psar = pta.psar(data.High, data.Low, data.Close)
data = pd.concat([data, psar], axis=1)
print(data.tail(5))
data = checkForSignal(data)
def checkForSignal(data):
    m = len(data.index)
    buyPrice = np.full(m, np.nan)
    sellPrice = np.full(m, np.nan)
    BUY = np.full(m, 0)
    SELL = np.full(m, 0)
    trend = np.full(m, 0)
    Close = pd.Series(data["Close"], dtype=np.float64)
    for i in range(3, m):
        bear = data["PSARs_0.02_0.2"][i] > data["Close"][i]
        bull = data["PSARl_0.02_0.2"][i] < data["Close"][i]
        if (
            data["adx"][i] > 25
            and data["adx+"][i] > data["adx-"][i]
            and bull
            and trend[i - 1] != 1
        ):  # noqa:
            BUY[i] = 1
            buyPrice[i] = Close[i]
            trend[i] = 1
        elif (
            data["adx"][i] > 25
            and data["adx+"][i] < data["adx-"][i]
            and bear
            and trend[i - 1] != 0
        ):  # noqa:
            SELL[i] = 1
            sellPrice[i] = Close[i]
            trend[i] = 0
        else:
            BUY[i] = 0
            SELL[i] = 0
            trend[i] = trend[i - 1]
    data["BUY"] = BUY
    data["buyPrice"] = buyPrice
    data["SELL"] = SELL
    data["sellPrice"] = sellPrice
    return data
data = pd.read_csv('Bitcoin_1D_2009-2022.csv')
data = data.rename(columns={'Price':'Close'})
data = data.convert_dtypes()
data.sort_index(ascending=False, inplace=True)
data.reset_index()
for i in data.iterrows():
    Close = pd.Series(data['Close'].apply(lambda x: str(x).replace(',','')), dtype=np.float64)
    Open = pd.Series(data['Open'].apply(lambda x: str(x).replace(',','')), dtype=np.float64)
    High = pd.Series(data['High'].apply(lambda x: str(x).replace(',','')), dtype=np.float64)
    Low = pd.Series(data['Low'].apply(lambda x: str(x).replace(',','')), dtype=np.float64)
data['Close'] = Close
data['Open'] = Open
data['High'] = High
data['Low'] = Low
data.to_csv('Bitcoin_1D_2009-2022.csv')
score ,data = indi.benchmarking(data, 12, 1.6, 30, 30, 30, 25, 30, 60)
print(score)
print(data.tail())
data = data.set_index('Date')
candle(data, 'BTC', '1D')
""" ""

# ฟังชั่นตัด 1000 ออกจากชื่อ symbol
"""""
symbol = '1000XEC/USDT'

if symbol[0:4] == "1000":
    symbol = symbol[4:len(symbol)]
print(symbol)

data = fetchbars(symbol,'1d',exchange)
print(data.tail(5))

""" ""
"""""
symbols = pd.DataFrame()
market = exchange.fetchTickers(params={'type':'future'})
for x,y in market.items():
    if y['symbol'][len(y['symbol'])-4:len(y['symbol'])] == "USDT":
        symbols = symbols.append(y , ignore_index=True)
symbols = symbols.set_index('symbol')
print(symbols)

""" ""


# def andean(self):
#     """""
#     calculate Andean Oscillator.
#     tradingview.
#     :https://www.tradingview.com/script/x9qYvBYN-Andean-Oscillator/
#     """ ""
#     alpha = 2 / (self.aol + 1)
#     Close = self.close
#     Open = self.open
#     up1 = np.full(self.length, np.nan)
#     up2 = np.full(self.length, np.nan)
#     dn1 = np.full(self.length, np.nan)
#     dn2 = np.full(self.length, np.nan)
#     cBull = np.full(self.length, np.nan)
#     cBear = np.full(self.length, np.nan)
#     def find_up1():
#     up1.apply()
#     try:
#         for i in range(2, self.length):
#             up11 = max(
#                 Close[i],
#                 Open[i],
#                 up1[i - 1] - (up1[i - 1] - Close[i]) * alpha,
#             )  # noqa:
#             up22 = max(
#                 Close[i] * Close[i],
#                 Open[i] * Open[i],
#                 up2[i - 1] - (up2[i - 1] - Close[i] * Close[i]) * alpha,
#             )
#             dn11 = min(
#                 Close[i],
#                 Open[i],
#                 dn1[i - 1] + (Close[i] - dn1[i - 1]) * alpha,
#             )  # noqa:
#             dn22 = min(
#                 Close[i] * Close[i],
#                 Open[i] * Open[i],
#                 dn2[i - 1] + (Close[i] * Close[i] - dn2[i - 1]) * alpha,
#             )
#             # up1[-1] := nz(math.max(
#             # C, O, up1[1] - (up1[1] - C) * alpha), C)
#             up11 = up1[i] = up11 if up22 is not np.nan else Close[i]
#             # up2[-1] := nz(math.max(
#             # C * C, O * O, up2[1] - (up2[1] - C * C)
#             # * alpha), C * C)
#             up22 = up2[i] = up22 if up22 is not np.nan else Close[i] * Close[i]
#             # dn1[-1] := nz(math.min(
#             # C, O, dn1[1] + (C - dn1[1]) * alpha), C)
#             dn11 = dn1[i] = dn11 if dn11 is not np.nan else Close[i]
#             # dn2[-1] := nz(math.min(
#             # C * C, O * O, dn2[1] + (C * C - dn2[1])
#             # * alpha), C * C)
#             dn22 = dn2[i] = dn22 if dn22 is not np.nan else Close[i] * Close[i]
#             cBull[i] = math.sqrt(dn22 - (dn11 * dn11))
#             cBear[i] = math.sqrt(up22 - (up11 * up11))
#         return cBull, cBear
#     except Exception as e:
#         print(f"Andean Oscillator is error : {e}")
#         return cBull, cBear
#
def plot(bot):
    fig = go.Figure(
        data=go.Candlestick(
            x=bot.data.index,
            open=bot.open,
            high=bot.high,
            low=bot.low,
            close=bot.close,
            showlegend=False,
        ),
        layout=dict(autosize=True, template="plotly_dark"),
    )
    vxma = go.Scatter(
        x=bot.data.index,
        y=bot.data["vxma"],
        mode="lines",
        line=go.scatter.Line(color="yellow"),
        showlegend=True,
        name="VXMA",
    )
    buy = go.Scatter(
        x=bot.data.index,
        y=bot.data["buyPrice"],
        mode="markers",
        marker=dict(size=15, color="lime"),
        showlegend=True,
        name="Buy",
    )
    sell = go.Scatter(
        x=bot.data.index,
        y=bot.data["sellPrice"],
        mode="markers",
        marker=dict(size=15, color="orange"),
        showlegend=True,
        name="Sell",
    )
    pvtop = go.Scatter(
        x=bot.data.index,
        y=bot.swing_h,
        mode="lines",
        line=go.scatter.Line(color="red"),
        showlegend=True,
        name="Pivot Top",
    )
    pvbot = go.Scatter(
        x=bot.data.index,
        y=bot.swing_l,
        mode="lines",
        line=go.scatter.Line(color="green"),
        showlegend=True,
        name="Pivot Bottom",
    )
    fig.add_trace(vxma)
    fig.add_trace(buy)
    fig.add_trace(sell)
    fig.add_trace(pvtop)
    fig.add_trace(pvbot)
    # fig.update(layout_xaxis_rangeslider_visible=False)
    # fig.update_layout(yaxis={"side": "right"})
    # fig.layout.xaxis.fixedrange = True
    # fig.layout.yaxis.fixedrange = True
    return fig.show()


# data = fetchbars("BTC/USDT", "1d", exchange)
# data = pd.read_csv("Bitcoin_1D_2009-2022.csv")
# data = data.set_index("Date")
# t1 = time.time()
# bot = ta(data, ta_table)
# data = bot.indicator()
# t2 = time.time()
# print(f"TA-LIB Time used : {round(t2-t1,2)} Seconds")
# t1 = time.time()
# bot2 = pa(data, ta_table)
# data2 = bot2.indicator()
# score = ta_score(data2)
# print(score.benchmarking())
# plot(bot)
# t2 = time.time()
# print(f"PANDAS TA Time used : {round(t2-t1,2)} Seconds")
# print(data.tail(2))
# print(data2.tail(2))
print(ta_table)
