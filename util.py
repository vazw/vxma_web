import pandas as pd
pd.set_option('display.max_rows', None)
import talib as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')
import math 
import multiprocessing as mp
#VXMA VAZ
#standard TA weighing
ADX_W       = 30
VXMA_W      = 50
MACD_W      = 10
SMA200_W    = 10

#Pivot High-Low only calculate last fixed bars
def callbackRate(data):
    m = len(data.index)
    try:
        highest = data['highest'][m-1]
        lowest = data['Lowest'][m-1]
        rate = round((highest-lowest)/highest*100,1)
        if rate > 5 :
            rate = 5
        elif rate < 0.1 :
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
    alpha = 2/(int(aol_ip) + 1)
    up2 = np.full(m, np.nan)
    up1 = np.full(m, np.nan)
    dn1 = np.full(m, np.nan)
    dn2 = np.full(m, np.nan)
    cBull = np.full(m, np.nan)
    cBear = np.full(m, np.nan)
    try:
        for i in range(2,m):
            up11 = (max(close[i],open[i],up1[i-1] - (up1[i-1] - close[i])*alpha))
            up22 = (max(close[i]*close[i],open[i]*open[i],up2[i-1] - (up2[i-1] - close[i]*close[i])*alpha))
            dn11 = (min(close[i],open[i],dn1[i-1] + (close[i] - dn1[i-1])*alpha))
            dn22 = (min(close[i]*close[i],open[i]*open[i],dn2[i-1] + (close[i]*close[i] - dn2[i-1])*alpha))
            # up1[i-1] := nz(math.max(C, O, up1[1] - (up1[1] - C) * alpha), C)
            up11 = up1[i] = up11 if up22 is not np.nan else close[i]
            # up2[i-1] := nz(math.max(C * C, O * O, up2[1] - (up2[1] - C * C) * alpha), C * C)
            up22 = up2[i] = up22 if up22 is not np.nan else close[i]*close[i]
            # dn1[i-1] := nz(math.min(C, O, dn1[1] + (C - dn1[1]) * alpha), C)
            dn11 = dn1[i] = dn11 if dn11 is not np.nan else close[i]
            # dn2[i-1] := nz(math.min(C * C, O * O, dn2[1] + (C * C - dn2[1]) * alpha), C * C)
            dn22 = dn2[i] = dn22 if dn22 is not np.nan else close[i]*close[i]
            cBull[i] = math.sqrt(dn22 - (dn11 * dn11))
            cBear[i] = math.sqrt(up22 - (up11 * up11))
        return cBull, cBear
    except Exception as e:
        print(f'Andean Oscillator is error : {e}')
        return cBull, cBear

#AlphaTrend
def alPha(data, atr_input, atrM_input, rsi_ip, m):
    alpha = np.full(m, np.nan)
    atr = ta.ATR(data['High'],data['Low'],data['Close'], int(atr_input))
    rsi = ta.RSI(data['Close'], int(rsi_ip))
    dnT = pd.Series(data['High']+ atr * float(atrM_input), dtype=np.float64) 
    upT = pd.Series(data['Low'] - atr * float(atrM_input), dtype=np.float64) 
    #alPha rsibb >= 50 ? upT < nz(alPha[1]) ? nz(alPha[1]) : upT : downT > nz(alPha[1]) ? nz(alPha[1]) : downT
    try:
        for i in range(1,m):
            if rsi[i] >= 50 :
                if upT[i] < (alpha[i-1]) if alpha[i-1] is not np.nan else 0:
                    alpha[i] = (alpha[i-1]) if alpha[i-1] is not np.nan else 0
                else : alpha[i] = upT[i]
            else:
                if dnT[i] > (alpha[i-1]) if alpha[i-1] is not np.nan else 0:
                    alpha[i] = (alpha[i-1]) if alpha[i-1] is not np.nan else 0
                else : alpha[i] = dnT[i]
        return alpha
    except Exception as e:
        print(f'AlphaTrend is error : {e}')
        return alpha
    
#VXMA
def VXMA(data, ema_ip, subhag, smooth, m):
    vxma = np.full(m, np.nan)
    EMAFAST = ta.EMA(data['Close'], int(ema_ip))
    LINREG = ta.EMA(ta.LINEARREG(data['Close'], int(subhag)), int(smooth))  
    alPha = pd.Series(data['alPha'], dtype=np.float64)
    cBull = pd.Series(data['cBull'], dtype=np.float64)
    cBear = pd.Series(data['cBear'], dtype=np.float64)
    #alPha rsibb >= 50 ? upT < nz(alPha[1]) ? nz(alPha[1]) : upT : downT > nz(alPha[1]) ? nz(alPha[1]) : downT
    try:
        for i in range(2,m): 
            clohi = max(EMAFAST[i],LINREG[i],alPha[i-2])
            clolo = min(EMAFAST[i],LINREG[i],alPha[i-2])
                #CloudMA := (bull > bear) ? clolo < nz(CloudMA[1]) ? nz(CloudMA[1]) : clolo :
            if cBull[i] > cBear[i] :
                if clolo < (vxma[i-1] if vxma[i-1] is not np.nan else 0):
                    vxma[i] = (vxma[i-1] if vxma[i-1] is not np.nan else 0)
                else : vxma[i] = clolo
                #  (bear > bull) ? clohi > nz(CloudMA[1]) ? nz(CloudMA[1]) : clohi : nz(CloudMA[1])
            elif  cBull[i] < cBear[i]:
                if clohi > (vxma[i-1] if vxma[i-1] is not np.nan else 0):
                    vxma[i] = (vxma[i-1] if vxma[i-1] is not np.nan else 0)
                else : vxma[i] = clohi
            else:
                vxma[i] = (vxma[i-1] if vxma[i-1] is not np.nan else 0)
        return vxma
    except Exception as e:
        print(f'VXMA is error : {e}')
        return vxma

bCollum = ['BUY','buyPrice','SELL','sellPrice']
def checkForSignal(data, m):
    bData = pd.DataFrame(columns=bCollum)
    preBuy =  np.full(m, np.nan)
    preSell = np.full(m, np.nan)
    buyPrice = np.full(m, np.nan)
    sellPrice = np.full(m, np.nan)
    BUY = np.full(m, 0) 
    SELL = np.full(m, 0)
    trend = np.full(m, 0)
    vxma_ = pd.Series(data['vxma'], dtype=np.float64)
    Close = pd.Series(data['Close'], dtype=np.float64)
    try:
        for i in range(2,m):
                #Get trend True = Bull False = Bear
            if vxma_[i] > vxma_[i-1] and vxma_[i-1] > vxma_[i-2] :
                trend[i] = 1
            elif vxma_[i] < vxma_[i-1] and vxma_[i-1] < vxma_[i-2] :
                trend[i] = 0
            else:
                trend[i] = trend[i-1] 
            #if trend change get pre-signal
            if trend[i] != 1 and trend[i-1] ==1 :
                preBuy[i] = 0
                preSell[i] = 1
            elif trend[i] == 1 and trend[i-1] !=1 :
                preBuy[i] = 1
                preSell[i] = 0
            else :
                preBuy[i] = 0
                preSell[i] = 0
            #if close is above cloud is buy signal
            if Close[i] > vxma_[i] and (preBuy[i] == 1 or preBuy[i-1] == 1) and (BUY[i-1] !=1):
                BUY[i] = 1 
                buyPrice[i] = Close[i]
            elif Close[i] < vxma_[i] and (preSell[i] == 1 or preSell[i-1] == 1) and (SELL[i-1] != 1):
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

#Call everthing here if not benchmark
def indicator(data, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip, aol_ip, pivot):
    m = len(data.index) 
    try:
        data = swingL(data, pivot)
        data = swingH(data, pivot)
        data['cBull'], data['cBear'] = andean(data['Close'], data['Open'], aol_ip, m)
        data['alPha'] = alPha(data, atr_input, atrM_input, rsi_ip, m)
        data['vxma'] = VXMA(data, ema_ip, subhag, smooth, m)
        data = checkForSignal(data, m)
        # Drop unwanted part
        data.drop(['cBear','alPha','cBull'],axis=1,inplace=True)
        return data
    except Exception as e:
        print(f'Indicator error : {e}')
        return data
    

#Trending a symbol.
def benchmarking(data, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip, aol_ip, pivot):
    tacollum = ['sma_200', 'macd', 'adx', 'adx+', 'adx-']
    datascoe = pd.DataFrame(columns=tacollum)
    try:
        datascoe['sma_200'] = ta.SMA(data['Close'],200)
        datascoe['macd'], macdsignal, macdhist = ta.MACD(data['Close'],12,26,9)
        datascoe['adx']  = ta.ADX(data['High'],data['Low'],data['Close'],14)
        datascoe['adx+'] = ta.PLUS_DI(data['High'],data['Low'],data['Close'],14)
        datascoe['adx-'] = ta.MINUS_DI(data['High'],data['Low'],data['Close'],14)
        data = indicator(data, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip, aol_ip, pivot)
        m = len(datascoe.index)-1
        adxx = 0
        if float(datascoe['adx'][m]) > 25 and float(datascoe['adx+'][m]) > float(datascoe['adx-'][m]):
            adxx = 10
        elif float(datascoe['adx'][m]) > 25 and float(datascoe['adx+'][m]) < float(datascoe['adx-'][m]):
            adxx = 0
        else : adxx = 5
        macd = (10 if float(datascoe['macd'][m]) > 0 else 0)
        sma = (10 if float(datascoe['sma_200'][m]) < float(data['Close'][m]) else 0)
        if data['vxma'][m] > data['vxma'][m-1]:
            vxda = 10
        elif data['vxma'][m] < data['vxma'][m-1]:
            vxda = 0
        else: vxda = 5
        score = ((macd*MACD_W)/100 + (adxx*ADX_W)/100 + (sma*SMA200_W)/100  + (vxda*VXMA_W)/100)
        if score > 8 :
            scr = 'Extreme-Bullish'
        elif score > 6 :
            scr = 'Bullish'
        elif score < 4 :
            scr = 'Bearish'
        elif score < 2 :
            scr = 'Extreme-Bearish'
        else:
            scr = 'Side-Way'
        return scr , data
    except Exception as e:
        print(f'Bencmarking is error : {e}')
        return 'error' , data


def ema(df, emafast, emaslow):
    df['emafast'] = ta.EMA(df['Close'],int(emafast))
    df['emaslow'] = ta.EMA(df['Close'],int(emaslow))
    m = len(df.index)
    df['buy'] = [0] * m
    df['sell'] = [0] * m
    df['buyPrice'] = [np.nan] * m
    df['sellPrice'] = [np.nan] * m
    try:
        for i in range(3,m):
            if df['emafast'][i-1] > df['emaslow'][i-1] and df['emafast'][i-2] < df['emaslow'][i-2]:
                df['buy'][i] = 0
                df['buyPrice'][i] = df['Close'][i]
            if df['emafast'][i-1] < df['emaslow'][i-1] and df['emafast'][i-2] > df['emaslow'][i-2]:
                df['sell'][i] = 0
                df['sellPrice'][i] = df['Close'][i]
        return df
    except Exception as e:
        print(f'2EMA is error : {e}')
        return df



