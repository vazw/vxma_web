import pandas as pd
import talib as ta
import numpy as np
import warnings
import math
import multiprocessing as mp
# VXMA VAZ
# standard TA weighing
ADX_W = 30
VXMA_W = 50
MACD_W = 10
SMA200_W = 10

pd.set_option('display.max_rows', None)
warnings.filterwarnings('ignore')

# Pivot High-Low only calculate last fixed bars


def callbackRate(data):
    m = len(data.index)
    try:
        highest = data['highest'][m - 1]
        lowest = data['Lowest'][m - 1]
        rate = round((highest - lowest) / highest * 100, 1)
        if rate > 5:
            rate = 5
        elif rate < 0.1:
            rate = 0.1
        return rate
    except Exception as e:
        print(f'callbackRate is error : {e}')
        return 2.5


def swingL(data, Pivot):
    try:
        data['Lowest'] = ta.MIN(data['Low'], int(Pivot))
        return data
    except Exception as e:
        print(f'swing Low is error : {e}')
        return data


def swingH(data, Pivot):
    try:
        data['Highest'] = ta.MAX(data['High'], int(Pivot))
        return data
    except Exception as e:
        print(f'swing High is error : {e}')
        return data


def andean(close, open, aol_ip, m):
    alpha = 2 / (int(aol_ip) + 1)
    Close = pd.Series(close, dtype=np.float64)
    Open = pd.Series(open, dtype=np.float64)
    up2 = np.full(m, np.nan)
    up1 = np.full(m, np.nan)
    dn1 = np.full(m, np.nan)
    dn2 = np.full(m, np.nan)
    cBull = np.full(m, np.nan)
    cBear = np.full(m, np.nan)
    try:
        for i in range(2, m):
            up11 = (max(Close[i], Open[i],
                        up1[i - 1] - (up1[i - 1] - Close[i]) * alpha))
            up22 = (max(
                Close[i] * Close[i], Open[i] * Open[i],
                up2[i - 1] - (up2[i - 1] - Close[i] * Close[i]) * alpha))
            dn11 = (min(Close[i], Open[i],
                        dn1[i - 1] + (Close[i] - dn1[i - 1]) * alpha))
            dn22 = (min(
                Close[i] * Close[i], Open[i] * Open[i],
                dn2[i - 1] + (Close[i] * Close[i] - dn2[i - 1]) * alpha))
            # up1[i-1] := nz(math.max(C, O, up1[1] - (up1[1] - C) * alpha), C)
            up11 = up1[i] = up11 if up22 is not np.nan else Close[i]
            # up2[i-1] := nz(math.max(C * C, O * O, up2[1] - (up2[1] - C * C) * alpha), C * C)
            up22 = up2[i] = up22 if up22 is not np.nan else Close[i] * Close[i]
            # dn1[i-1] := nz(math.min(C, O, dn1[1] + (C - dn1[1]) * alpha), C)
            dn11 = dn1[i] = dn11 if dn11 is not np.nan else Close[i]
            # dn2[i-1] := nz(math.min(C * C, O * O, dn2[1] + (C * C - dn2[1]) * alpha), C * C)
            dn22 = dn2[i] = dn22 if dn22 is not np.nan else Close[i] * Close[i]
            cBull[i] = math.sqrt(dn22 - (dn11 * dn11))
            cBear[i] = math.sqrt(up22 - (up11 * up11))
        return cBull, cBear
    except Exception as e:
        print(f'Andean Oscillator is error : {e}')
        return cBull, cBear


# AlphaTrend
def alPhaT(data, atr_input, atrM_input, rsi_ip, m):
    alpha = np.full(m, np.nan)
    Close = pd.Series(data['Close'], dtype=np.float64)
    High = pd.Series(data['High'], dtype=np.float64)
    Low = pd.Series(data['Low'], dtype=np.float64)
    atr = ta.ATR(High, Low, Close, int(atr_input))
    rsi = ta.RSI(Close, int(rsi_ip))
    dnT = pd.Series(High + atr * float(atrM_input))
    upT = pd.Series(Low - atr * float(atrM_input))
    try:
        for i in range(1, m):
            if rsi[i] >= 50:
                if upT[i] < (alpha[i - 1]) if alpha[i -
                                                    1] is not np.nan else 0:
                    alpha[i] = (alpha[i - 1]) if alpha[i -
                                                       1] is not np.nan else 0
                else:
                    alpha[i] = upT[i]
            else:
                if dnT[i] > (alpha[i - 1]) if alpha[i -
                                                    1] is not np.nan else 0:
                    alpha[i] = (alpha[i - 1]) if alpha[i -
                                                       1] is not np.nan else 0
                else:
                    alpha[i] = dnT[i]
        return alpha
    except Exception as e:
        print(f'AlphaTrend is error : {e}')
        return alpha


# VXMA
def VXMA(data, ema_ip, subhag, smooth, atr_input, atrM_input, rsi_ip, aol_ip,
         m):
    vxma = np.full(m, np.nan)
    Close = pd.Series(data['Close'], dtype=np.float64)
    Open = pd.Series(data['Open'], dtype=np.float64)
    EMAFAST = ta.EMA(Close, int(ema_ip))
    LINREG = ta.EMA(ta.LINEARREG(Close, int(subhag)), int(smooth))
    alPha = alPhaT(data, atr_input, atrM_input, rsi_ip, m)
    cBull, cBear = andean(Close, Open, aol_ip, m)
    # alPha rsibb >= 50 ? upT < nz(alPha[1]) ? nz(alPha[1]) : upT :
    # downT > nz(alPha[1]) ? nz(alPha[1]) : downT
    try:
        for i in range(2, m):
            clohi = max(EMAFAST[i], LINREG[i], alPha[i - 2])
            clolo = min(EMAFAST[i], LINREG[i], alPha[i - 2])
            #CloudMA := (bull > bear) ? clolo < nz(CloudMA[1]) ? nz(CloudMA[1]) : clolo :
            if cBull[i] > cBear[i]:
                if clolo < (vxma[i - 1] if vxma[i - 1] is not np.nan else 0):
                    vxma[i] = (vxma[i - 1] if vxma[i - 1] is not np.nan else 0)
                else:
                    vxma[i] = clolo
                #  (bear > bull) ? clohi > nz(CloudMA[1]) ? nz(CloudMA[1]) : clohi : nz(CloudMA[1])
            elif cBull[i] < cBear[i]:
                if clohi > (vxma[i - 1] if vxma[i - 1] is not np.nan else 0):
                    vxma[i] = (vxma[i - 1] if vxma[i - 1] is not np.nan else 0)
                else:
                    vxma[i] = clohi
            else:
                vxma[i] = (vxma[i - 1] if vxma[i - 1] is not np.nan else 0)
        return vxma
    except Exception as e:
        print(f'VXMA is error : {e}')
        return vxma


bCollum = ['BUY', 'buyPrice', 'SELL', 'sellPrice']


def checkForSignal(data, m):
    preBuy = np.full(m, np.nan)
    preSell = np.full(m, np.nan)
    buyPrice = np.full(m, np.nan)
    sellPrice = np.full(m, np.nan)
    BUY = np.full(m, 0)
    SELL = np.full(m, 0)
    trend = np.full(m, 0)
    vxma_ = pd.Series(data['vxma'], dtype=np.float64)
    Close = pd.Series(data['Close'], dtype=np.float64)
    try:
        for i in range(2, m):
            #Get trend True = Bull False = Bear
            if vxma_[i] > vxma_[i - 1] and vxma_[i - 1] > vxma_[i - 2]:
                trend[i] = 1
            elif vxma_[i] < vxma_[i - 1] and vxma_[i - 1] < vxma_[i - 2]:
                trend[i] = 0
            else:
                trend[i] = trend[i - 1]
            #if trend change get pre-signal
            if trend[i] != 1 and trend[i - 1] == 1:
                preBuy[i] = 0
                preSell[i] = 1
            elif trend[i] == 1 and trend[i - 1] != 1:
                preBuy[i] = 1
                preSell[i] = 0
            else:
                preBuy[i] = 0
                preSell[i] = 0
            #if close is above cloud is buy signal
            if Close[i] > vxma_[i] and (preBuy[i] == 1 or preBuy[i - 1]
                                        == 1) and (BUY[i - 1] != 1):
                BUY[i] = 1
                buyPrice[i] = Close[i]
            elif Close[i] < vxma_[i] and (preSell[i] == 1 or preSell[i - 1]
                                          == 1) and (SELL[i - 1] != 1):
                SELL[i] = 1
                sellPrice[i] = Close[i]
            else:
                BUY[i] = 0
                SELL[i] = 0
        data['BUY'] = BUY
        data['buyPrice'] = buyPrice
        data['SELL'] = SELL
        data['sellPrice'] = sellPrice
        return data
    except Exception as e:
        print(f'Signal is error : {e}')
        return data


# Call everthing here if not benchmark
def indicator(data, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip,
              aol_ip, pivot):
    m = len(data.index)
    try:
        data = swingL(data, pivot)
        data = swingH(data, pivot)
        data['vxma'] = VXMA(data, ema_ip, subhag, smooth, atr_input,
                            atrM_input, rsi_ip, aol_ip, m)
        data = checkForSignal(data, m)
        return data
    except Exception as e:
        print(f'Indicator error : {e}')
        return data


# Trending a symbol.
def benchmarking(data, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip,
                 aol_ip, pivot):
    tacollum = ['sma_200', 'macd', 'adx', 'adx+', 'adx-']
    datascoe = pd.DataFrame(columns=tacollum)
    # verify series
    Close = pd.Series(data['Close'], dtype=np.float64)
    Open = pd.Series(data['Open'], dtype=np.float64)
    High = pd.Series(data['High'], dtype=np.float64)
    Low = pd.Series(data['Low'], dtype=np.float64)
    try:
        datascoe['sma_200'] = ta.SMA(Close, 200)
        datascoe['macd'], macdsignal, macdhist = ta.MACD(Open, 12, 26, 9)
        datascoe['adx'] = ta.ADX(High, Low, Close, 14)
        datascoe['adx+'] = ta.PLUS_DI(High, Low, Close, 14)
        datascoe['adx-'] = ta.MINUS_DI(High, Low, Close, 14)
        data = indicator(data, atr_input, atrM_input, ema_ip, subhag, smooth,
                         rsi_ip, aol_ip, pivot)
        m = len(datascoe.index) - 1
        adxx = 0
        if float(datascoe['adx'][m]) > 25 and float(
                datascoe['adx+'][m]) > float(datascoe['adx-'][m]):
            adxx = 10
        elif float(datascoe['adx'][m]) > 25 and float(
                datascoe['adx+'][m]) < float(datascoe['adx-'][m]):
            adxx = 0
        else:
            adxx = 5
        macd = (10 if float(datascoe['macd'][m]) > 0 else 0)
        sma = (10 if float(datascoe['sma_200'][m]) < float(Close[m]) else 0)
        if data['vxma'][m] > data['vxma'][m - 1]:
            vxda = 10
        elif data['vxma'][m] < data['vxma'][m - 1]:
            vxda = 0
        else:
            vxda = 5
        score = ((macd * MACD_W) / 100 + (adxx * ADX_W) / 100 +
                 (sma * SMA200_W) / 100 + (vxda * VXMA_W) / 100)
        if score > 8:
            scr = 'Extreme-Bullish'
        elif score > 6:
            scr = 'Bullish'
        elif score < 4:
            scr = 'Bearish'
        elif score < 2:
            scr = 'Extreme-Bearish'
        else:
            scr = 'Side-Way'
        return scr, data
    except Exception as e:
        print(f'Bencmarking is error : {e}')
        return 'error', data


def ema(df, emafast, emaslow):
    df['emafast'] = ta.EMA(df['Close'], int(emafast))
    df['emaslow'] = ta.EMA(df['Close'], int(emaslow))
    m = len(df.index)
    df['buy'] = [0] * m
    df['sell'] = [0] * m
    df['buyPrice'] = [np.nan] * m
    df['sellPrice'] = [np.nan] * m
    try:
        for i in range(3, m):
            if df['emafast'][i - 1] > df['emaslow'][i - 1] and df['emafast'][
                    i - 2] < df['emaslow'][i - 2]:
                df['buy'][i] = 0
                df['buyPrice'][i] = df['Close'][i]
            if df['emafast'][i - 1] < df['emaslow'][i - 1] and df['emafast'][
                    i - 2] > df['emaslow'][i - 2]:
                df['sell'][i] = 0
                df['sellPrice'][i] = df['Close'][i]
        return df
    except Exception as e:
        print(f'2EMA is error : {e}')
        return df


def sTreamswingL(data, Pivot):
    try:
        data['Lowest'] = ta.MIN(data['Low'], int(Pivot))
        return data
    except Exception as e:
        print(f'Streaming swing Low is error : {e}')
        return data


def sTreamswingH(data, Pivot):
    try:
        data['Highest'] = ta.MAX(data['High'], int(Pivot))
        return data
    except Exception as e:
        print(f'Streaming swing High is error : {e}')
        return data


def sTreamandean(close, open, aol_ip, m):
    alpha = 2 / (int(aol_ip) + 1)
    Close = pd.Series(close, dtype=np.float64)
    Open = pd.Series(open, dtype=np.float64)
    up2 = np.full(m, np.nan)
    up1 = np.full(m, np.nan)
    dn1 = np.full(m, np.nan)
    dn2 = np.full(m, np.nan)
    cBull = np.full(m, np.nan)
    cBear = np.full(m, np.nan)
    try:
        for i in range(2, m):
            up11 = (max(Close[i], Open[i],
                        up1[i - 1] - (up1[i - 1] - Close[i]) * alpha))
            up22 = (max(
                Close[i] * Close[i], Open[i] * Open[i],
                up2[i - 1] - (up2[i - 1] - Close[i] * Close[i]) * alpha))
            dn11 = (min(Close[i], Open[i],
                        dn1[i - 1] + (Close[i] - dn1[i - 1]) * alpha))
            dn22 = (min(
                Close[i] * Close[i], Open[i] * Open[i],
                dn2[i - 1] + (Close[i] * Close[i] - dn2[i - 1]) * alpha))
            # up1[i-1] := nz(math.max(C, O, up1[1] - (up1[1] - C) * alpha), C)
            up11 = up1[i] = up11 if up22 is not np.nan else Close[i]
            # up2[i-1] := nz(math.max(C * C, O * O, up2[1] - (up2[1] - C * C) * alpha), C * C)
            up22 = up2[i] = up22 if up22 is not np.nan else Close[i] * Close[i]
            # dn1[i-1] := nz(math.min(C, O, dn1[1] + (C - dn1[1]) * alpha), C)
            dn11 = dn1[i] = dn11 if dn11 is not np.nan else Close[i]
            # dn2[i-1] := nz(math.min(C * C, O * O, dn2[1] + (C * C - dn2[1]) * alpha), C * C)
            dn22 = dn2[i] = dn22 if dn22 is not np.nan else Close[i] * Close[i]
            cBull[i] = math.sqrt(dn22 - (dn11 * dn11))
            cBear[i] = math.sqrt(up22 - (up11 * up11))
        return cBull, cBear
    except Exception as e:
        print(f'Streaming Andean Oscillator is error : {e}')
        return cBull, cBear


# AlphaTrend
def sTreamalPhaT(data, atr_input, atrM_input, rsi_ip, m):
    alpha = np.full(m, np.nan)
    Close = pd.Series(data['Close'], dtype=np.float64)
    High = pd.Series(data['High'], dtype=np.float64)
    Low = pd.Series(data['Low'], dtype=np.float64)
    atr = ta.ATR(High, Low, Close, int(atr_input))
    rsi = ta.RSI(Close, int(rsi_ip))
    dnT = pd.Series(High + atr * float(atrM_input))
    upT = pd.Series(Low - atr * float(atrM_input))
    #alPha rsibb >= 50 ? upT < nz(alPha[1]) ? nz(alPha[1]) : upT : downT > nz(alPha[1]) ? nz(alPha[1]) : downT
    try:
        for i in range(1, m):
            if rsi[i] >= 50:
                if upT[i] < (alpha[i - 1]) if alpha[i -
                                                    1] is not np.nan else 0:
                    alpha[i] = (alpha[i - 1]) if alpha[i -
                                                       1] is not np.nan else 0
                else:
                    alpha[i] = upT[i]
            else:
                if dnT[i] > (alpha[i - 1]) if alpha[i -
                                                    1] is not np.nan else 0:
                    alpha[i] = (alpha[i - 1]) if alpha[i -
                                                       1] is not np.nan else 0
                else:
                    alpha[i] = dnT[i]
        return alpha
    except Exception as e:
        print(f'Streaming AlphaTrend is error : {e}')
        return alpha


# VXMA
def sTreamVXMA(data, ema_ip, subhag, smooth, atr_input, atrM_input, rsi_ip,
               aol_ip, m):
    vxma = np.full(m, np.nan)
    Close = pd.Series(data['Close'], dtype=np.float64)
    Open = pd.Series(data['Open'], dtype=np.float64)
    EMAFAST = ta.EMA(Close, int(ema_ip))
    LINREG = ta.EMA(ta.LINEARREG(Close, int(subhag)), int(smooth))
    alPha = sTreamalPhaT(data, atr_input, atrM_input, rsi_ip, m)
    cBull, cBear = sTreamandean(Close, Open, aol_ip, m)
    #alPha rsibb >= 50 ? upT < nz(alPha[1]) ? nz(alPha[1]) : upT : downT > nz(alPha[1]) ? nz(alPha[1]) : downT
    try:
        for i in range(2, m):
            clohi = max(EMAFAST[i], LINREG[i], alPha[i - 2])
            clolo = min(EMAFAST[i], LINREG[i], alPha[i - 2])
            #CloudMA := (bull > bear) ? clolo < nz(CloudMA[1]) ? nz(CloudMA[1]) : clolo :
            if cBull[i] > cBear[i]:
                if clolo < (vxma[i - 1] if vxma[i - 1] is not np.nan else 0):
                    vxma[i] = (vxma[i - 1] if vxma[i - 1] is not np.nan else 0)
                else:
                    vxma[i] = clolo
                #  (bear > bull) ? clohi > nz(CloudMA[1]) ? nz(CloudMA[1]) : clohi : nz(CloudMA[1])
            elif cBull[i] < cBear[i]:
                if clohi > (vxma[i - 1] if vxma[i - 1] is not np.nan else 0):
                    vxma[i] = (vxma[i - 1] if vxma[i - 1] is not np.nan else 0)
                else:
                    vxma[i] = clohi
            else:
                vxma[i] = (vxma[i - 1] if vxma[i - 1] is not np.nan else 0)
        return vxma
    except Exception as e:
        print(f'Streaming VXMA is error : {e}')
        return vxma


bCollum = ['BUY', 'buyPrice', 'SELL', 'sellPrice']


def sTreamcheckForSignal(data, m):
    preBuy = np.full(m, np.nan)
    preSell = np.full(m, np.nan)
    buyPrice = np.full(m, np.nan)
    sellPrice = np.full(m, np.nan)
    BUY = np.full(m, 0)
    SELL = np.full(m, 0)
    trend = np.full(m, 0)
    vxma_ = pd.Series(data['vxma'], dtype=np.float64)
    Close = pd.Series(data['Close'], dtype=np.float64)
    try:
        for i in range(3, m):
            # Get trend True = Bull False = Bear
            if vxma_[i - 1] > vxma_[i - 2] and vxma_[i - 2] > vxma_[i - 3]:
                trend[i - 1] = 1
            elif vxma_[i - 1] < vxma_[i - 2] and vxma_[i - 2] < vxma_[i - 3]:
                trend[i - 1] = 0
            else:
                trend[i - 1] = trend[i - 2]
            # if trend change get pre-signal
            if trend[i - 1] != 1 and trend[i - 2] == 1:
                preBuy[i - 1] = 0
                preSell[i - 1] = 1
            elif trend[i - 1] == 1 and trend[i - 2] != 1:
                preBuy[i - 1] = 1
                preSell[i - 1] = 0
            else:
                preBuy[i - 1] = 0
                preSell[i - 1] = 0
            # if close is above cloud is buy signal
            if Close[i - 1] > vxma_[i - 1] and (preBuy[i] == 1 or preBuy[i - 2]
                                                == 1) and (BUY[i - 2] != 1):
                BUY[i - 1] = 1
                buyPrice[i - 1] = Close[i - 1]
            elif Close[i - 1] < vxma_[i - 1] and (preSell[i] == 1
                                                  or preSell[i - 2]
                                                  == 1) and (SELL[i - 2] != 1):
                SELL[i - 1] = 1
                sellPrice[i - 1] = Close[i - 1]
            else:
                BUY[i - 1] = 0
                SELL[i - 1] = 0
        data['BUY'] = BUY
        data['buyPrice'] = buyPrice
        data['SELL'] = SELL
        data['sellPrice'] = sellPrice
        return data
    except Exception as e:
        print(f'Streaming Signal is error : {e}')
        return data


# Call everything here if not benchmark
def sTreamindicator(data, atr_input, atrM_input, ema_ip, subhag, smooth,
                    rsi_ip, aol_ip, pivot):
    m = len(data.index)
    try:
        data = sTreamswingL(data, pivot)
        data = sTreamswingH(data, pivot)
        data['vxma'] = sTreamVXMA(data, ema_ip, subhag, smooth, atr_input,
                                  atrM_input, rsi_ip, aol_ip, m)
        data = sTreamcheckForSignal(data, m)
        return data
    except Exception as e:
        print(f'Streaming Indicator error : {e}')
        return data
