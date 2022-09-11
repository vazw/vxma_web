import asyncio
import ccxt.async_support as accxt
import ccxt
import time
import pandas as pd
pd.set_option('display.max_rows', None)
from line_notify import LineNotify 
import bcrypt
from datetime import datetime as dt
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')
from tabulate import tabulate
import logging
import util as indi
import mplfinance as mplf
from dash import Dash, html, dcc, dash_table, register_page
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from threading import Thread
import os

def clearconsol():
    try:
        if os.name == 'posix':
            os.system('clear')
        else:
            os.system('cls') 
        return
    except Exception as e:
        print(e)
        return
logging.basicConfig(filename='log.log', format='%(asctime)s - %(message)s', level=logging.INFO)
import sqlite3
con = sqlite3.connect('vxma.db', check_same_thread=False)
cur = con.cursor()
rcs = {"axes.labelcolor":"none",
        "axes.spines.left": False,
        "axes.spines.right": False,
        "axes.axisbelow": False,
        "axes.grid": True,
        "grid.linestyle": ":",
        "axes.titlesize": "xx-large",
        "axes.titleweight": "bold"}

def get_config():
    global BNBCZ, notify, min_balance, max_margin, API_KEY, LINE_TOKEN, MIN_BALANCE, symbolist
    config = pd.read_sql('SELECT * FROM key',con=con)
    symbolist = pd.read_sql(f'SELECT * FROM Bot',con=con)
    if config.empty:
        API_KEY = ''
        API_SECRET = ''
        LINE_TOKEN = ''
        max_margin = '$10'
        MIN_BALANCE = '$50'
    else:
        max_margin = str(config['freeB'][0])
        MIN_BALANCE = str(config['minB'][0])
        API_KEY = str(config['apikey'][0])
        API_SECRET = str(config['apisec'][0])
        LINE_TOKEN = str(config['notify'][0])
    BNBCZ = {
        "apiKey": API_KEY,
        "secret": API_SECRET,
        'options': {
        'defaultType': 'future'
        },
        'enableRateLimit': True,
        'adjustForTimeDifference': True
        }
    notify = LineNotify(LINE_TOKEN)
    if MIN_BALANCE[0]=='$':
        min_balance=float(MIN_BALANCE[1:len(MIN_BALANCE)])
    else: min_balance=float(MIN_BALANCE)
    if max_margin[0]=='$' :
        max_margin = float(max_margin[1:len(max_margin)])
    else: max_margin = float(max_margin)
    return  
get_config()

#Bot setting
insession = dict(name=False,day=False,hour=False)
#STAT setting
barsC = 1502
#timframe dicts and collum
ZOOM_DICT = { 'X1': 500 ,'X2': 250 ,'X3': 180 ,'X4': 125 ,'X5': 50 }
TIMEFRAMES = [  '1m','3m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d','3d','1w','1M']
TIMEFRAMES_DICT = { '1m': '1m','3m': '3m','5m': '5m','15m': '15m','30m': '30m',
                       '1h': '1h','2h': '2h','4h': '4h','6h': '6h','8h': '8h',
                       '12h': '12h','1d': '1d','3d': '3d','1w': '1w','1M': '1M'}
BOTCOL = ['id','symbol', 'timeframe', 'ATR', 'ATR_m', 'EMA', 'subhag', 'smooth', 'RSI', 'Andean',
          'Uselong', 'Useshort', 'UseTP', 'UseSL', 'Tail_SL', 'leverage', 'Pivot', 'RR1', 'RR2', 'TP1', 'TP2', 'Risk', 'maxMargin']

def perf(id, pwd):
    hash1 = None
    bata = pd.read_sql('SELECT * FROM user',con=con)
    iid = bata['id'][0]
    if iid == id:
        hash1 = bata['pass'][0]
    egg = f'{id}{pwd}!{barsC}vz{id}'
    bytePwd = egg.encode('utf-8')
    proof = bcrypt.checkpw(bytePwd, hash1)
    return proof


async def connect():
    exchange = accxt.binance(BNBCZ)
    return exchange

async def disconnect(exchange):
    return await exchange.close()

def candle(df,symbol,tf):
    data = df.tail(60)
    titles = f'{symbol}_{tf}'
    color = mplf.make_marketcolors(up='white',down='black',wick='black',edge='black')   
    s = mplf.make_mpf_style(rc=rcs,y_on_right=True,marketcolors=color,figcolor='lime',gridaxis='horizontal')
    try:
        vxma = mplf.make_addplot(data.vxma,secondary_y=False,color='blue',linewidths=0.2) 
        mplf.plot(data,type='candle',title=titles,addplot=vxma, style=s,volume=True,savefig='candle.png',tight_layout=True,figratio=(9,9),datetime_format='%y/%b/%d %H:%M', xrotation=20)
    except AttributeError as e:
        print(f'{e}')
        mplf.plot(data,type='candle',title=titles,addplot=vxma, style=s,volume=True,savefig='candle.png',tight_layout=True,figratio=(9,9),datetime_format='%y/%b/%d %H:%M', xrotation=20)
    notify.send(f'info : {titles}',image_path=('./candle.png'))
    return 

async def get_symbol(exchange):
    symbols = pd.DataFrame()
    symbolist = pd.read_sql(f'SELECT * FROM Bot',con=con)
    print('fecthing Symbol of Top 10 Volume...')
    exchange = await connect()
    try:
        market = await exchange.fetchTickers(params={'type':'future'})
    except accxt.RequestTimeout as e:
        print('[' + type(e).__name__ + ']')
        print(str(e)[0:200])
        market = await exchange.fetchTickers(params={'type':'future'})
        # will retry
    except accxt.DDoSProtection as e:
        print('[' + type(e).__name__ + ']')
        print(str(e.args)[0:200])
        market = await exchange.fetchTickers(params={'type':'future'})
        # will retry
    except accxt.ExchangeNotAvailable as e:
        print('[' + type(e).__name__ + ']')
        print(str(e.args)[0:200])
        market = await exchange.fetchTickers(params={'type':'future'})
        # will retry
    except accxt.ExchangeError as e:
        print('[' + type(e).__name__ + ']')
        print(str(e)[0:200])
        market = await exchange.fetchTickers(params={'type':'future'})
    await disconnect(exchange)
    for x,y in market.items()    :
        if y['symbol'][len(y['symbol'])-4:len(y['symbol'])] == "USDT":
            symbols = symbols.append(y , ignore_index=True)
    symbols = symbols.set_index('symbol')
    symbols['datetime'] = pd.to_datetime(symbols['timestamp'], unit='ms', utc=True).map(lambda x: x.tz_convert('Asia/Bangkok'))
    symbols = symbols.sort_values(by=['quoteVolume'],ascending=False)
    symbols.drop(['timestamp','high','low','average'],axis=1,inplace=True)
    symbols.drop(['bid','bidVolume','ask','askVolume'],axis=1,inplace=True)
    symbols.drop(['vwap','open','baseVolume','info'],axis=1,inplace=True)
    symbols.drop(['close','previousClose','datetime'],axis=1,inplace=True)
    symbols = symbols.head(10)
    newsym = []
    if len(symbolist.index) > 0:
        for i in len(symbolist.index):
            newsym.append(symbolist['symbol'][i])
    for symbol in symbols.index:
        newsym.append(symbol)
    print(tabulate(symbols, headers = 'keys', tablefmt = 'grid'))
    newsym = list(dict.fromkeys(newsym))
    print(f'Interested : {newsym}')
    return newsym 
#pass
async def fetchbars(symbol,timeframe):
    print(f"Benchmarking new bars for {symbol , timeframe , dt.now().isoformat()}")
    exchange = await connect()
    try:
        bars = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, since = None, limit =barsC)
    except accxt.RequestTimeout as e:
        print('[' + type(e).__name__ + ']')
        print(str(e)[0:200])
        await asyncio.sleep(1)
        bars = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, since = None, limit =barsC)
    except accxt.DDoSProtection as e:
        print('[' + type(e).__name__ + ']')
        print(str(e.args)[0:200])
        await asyncio.sleep(1)
        bars = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, since = None, limit =barsC)
    except accxt.ExchangeNotAvailable as e:
        print('[' + type(e).__name__ + ']')
        print(str(e.args)[0:200])
        await asyncio.sleep(1)
        bars = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, since = None, limit =barsC)
    except accxt.ExchangeError as e:
        print('[' + type(e).__name__ + ']')
        print(str(e)[0:200])
        await asyncio.sleep(1)
        bars = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, since = None, limit =barsC)
    await disconnect(exchange)
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).map(lambda x: x.tz_convert('Asia/Bangkok'))
    df = df.set_index('timestamp')
    return df
#set leverage pass
async def setleverage(symbol,exchange):
    try:
        await exchange.set_leverage(lev,symbol)
    except accxt.RequestTimeout as e:
        print('[' + type(e).__name__ + ']')
        print(str(e)[0:200])
        await asyncio.sleep(1)
        exchange.load_markets()
        lever = await exchange.fetch_positions_risk([symbol])
        for x in range(len(lever)):
            if (lever[x]['symbol']) == symbol:
                lev = round(lever[x]['leverage'],0)
                print(lev)
                await exchange.set_leverage(int(lev),symbol)
                break
    except accxt.DDoSProtection as e:
        print('[' + type(e).__name__ + ']')
        print(str(e.args)[0:200])
        await asyncio.sleep(1)
        lever = await exchange.fetch_positions_risk([symbol])
        for x in range(len(lever)):
            if (lever[x]['symbol']) == symbol:
                lev = round(lever[x]['leverage'],0)
                print(lev)
                await exchange.set_leverage(int(lev),symbol)
                break
    except accxt.ExchangeNotAvailable as e:
        print('[' + type(e).__name__ + ']')
        print(str(e.args)[0:200])
        await asyncio.sleep(1)
        lever = await exchange.fetch_positions_risk([symbol])
        for x in range(len(lever)):
            if (lever[x]['symbol']) == symbol:
                lev = round(lever[x]['leverage'],0)
                print(lev)
                await exchange.set_leverage(int(lev),symbol)
                break
    except accxt.ExchangeError as e:
        print('[' + type(e).__name__ + ']')
        print(str(e)[0:200])
        await asyncio.sleep(1)
        lever = await exchange.fetch_positions_risk([symbol])
        for x in range(len(lever)):
            if (lever[x]['symbol']) == symbol:
                lev = round(lever[x]['leverage'],0)
                print(lev)
                await exchange.set_leverage(int(lev),symbol)
                break
    except:
        await asyncio.sleep(1)
        lever = await exchange.fetch_positions_risk([symbol])
        for x in range(len(lever)):
            if (lever[x]['symbol']) == symbol:
                lev = round(lever[x]['leverage'],0)
                print(lev)
                await exchange.set_leverage(int(lev),symbol)
                break
    return round(int(lev),0)

#Position Sizing
def buysize(df,balance,symbol,exchange,RISK):
    last = len(df.index) -1
    freeusd = float(balance['free']['USDT'])
    low = float(df['Lowest'][last])
    if RISK[0]=='$' :
        risk = float(RISK[1:len(RISK)])
    elif RISK[0]=='%' :
        percent = float(RISK)
        risk = (percent/100)*freeusd
    else: risk = float(RISK)
    amount = abs(risk  / (df['Close'][last] - low))
    qty_precision = exchange.amount_to_precision(symbol, amount)
    lot = qty_precision
    return float(lot)

def sellsize(df,balance,symbol,exchange,RISK):
    last = len(df.index) -1
    freeusd = float(balance['free']['USDT'])
    high = float(df['Highest'][last])
    if RISK[0]=='$' :
        risk = float(RISK[1:len(RISK)])
    elif RISK[0]=='%' :
        percent = float(RISK)
        risk = (percent/100)*freeusd
    else: risk = float(RISK)
    amount = abs(risk  / (high - df['Close'][last]))
    qty_precision = exchange.amount_to_precision(symbol, amount)
    lot = qty_precision
    return float(lot)
#TP with Risk:Reward    
def RRTP(df,direction,step,price,TPRR1 ,TPRR2):
    m = len(df.index)
    if direction :
        low = float(df['Lowest'][m-1])
        if step == 1 :
            target = price *(1+((price-low)/price)*float(TPRR1))
        if step == 2 :
            target = price *(1+((price-low)/price)*float(TPRR2))
    else :
        high = float(df['Highest'][m-1])
        if step == 1 :
            target = price *(1-((high-price)/price)*float(TPRR1))
        if step == 2 :
            target = price *(1-((high-price)/price)*float(TPRR2))    
    return float(target)
#pass
def RR1(df,direction,price):
    m = len(df.index)
    if direction :
        low = df['Lowest'][m-1]
        target = price *(1+((price-float(low))/price)*1)
    else :
        high = df['Highest'][m-1]
        target = price *(1-((float(high)-price)/price)*1)
    return target
#OpenLong=Buy
async def OpenLong(df, balance, symbol, lev, exchange, currentMODE, Lside, tf, RISK, Max_Size, TPPer, TPPer2, USETP, USESL, Tailing_SL,TPRR1,TPRR2):
    try:    
        amount = buysize(df,balance,symbol,exchange,RISK)
        try:
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.RequestTimeout as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.DDoSProtection as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.ExchangeNotAvailable as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.ExchangeError as e:
            print('[' + type(e).__name__ + ']')
            logging.info(e)
            print(str(e)[0:200])
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except Exception as e:
            print(e)
            logging.info(e)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        ask = float(info['askPrice'])
        print(f'price : {ask}')
        logging.info(f'Entry {symbol} Long @{ask} qmt:{amount}')
        leve = await setleverage(symbol,exchange)
        if amount*ask > Max_Size*int(leve):
            amount = Max_Size*int(leve)/ask    
        free = float(balance['free']['USDT'])
        amttp1 = amount*(TPPer/100)
        amttp2 = amount*(TPPer2/100)
        low = df['Lowest'][len(df.index)-1]
        if free > min_balance :
            try:
                order = await exchange.createMarketOrder(symbol,'buy',amount,params={'positionSide':Lside})
                logging.info(order)
            except accxt.InsufficientFunds as e:
                logging.debug(e)
                notify.send(e)
                return    
            if USESL :
                if currentMODE['dualSidePosition']:
                    orderSL         = await exchange.create_order(symbol,'stop','sell',amount,float(low),params={'stopPrice':float(low),'triggerPrice':float(low),'positionSide':Lside})
                    if Tailing_SL :
                        ordertailingSL  = await exchange.create_order(symbol, 'TRAILING_STOP_MARKET','sell',amount,params ={'activationPrice':float(RR1(df,True,ask)) ,'callbackRate': float(indi.callbackRate(df)),'positionSide':Lside})
                else:
                    orderSL         = await exchange.create_order(symbol,'stop','sell',amount,float(low),params={'stopPrice':float(low),'triggerPrice':float(low),'reduceOnly': True ,'positionSide':Lside})
                    if Tailing_SL :
                        ordertailingSL  = await exchange.create_order(symbol, 'TRAILING_STOP_MARKET','sell',amount,params ={'activationPrice':float(RR1(df,True,ask)) ,'callbackRate': float(indi.callbackRate(df)),'reduceOnly': True ,'positionSide':Lside})
                if Tailing_SL :
                    logging.info(ordertailingSL)
                logging.info(orderSL)
            if USETP :
                orderTP  = await exchange.create_order(symbol,'TAKE_PROFIT_MARKET','sell',amttp1,float(RRTP(df,True,1,ask,TPRR1,TPRR2)),params={'stopPrice':float(RRTP(df,True,1,ask,TPRR1,TPRR2)),'triggerPrice':float(RRTP(df,True,1,ask,TPRR1,TPRR2)),'positionSide':Lside})
                orderTP2 = await exchange.create_order(symbol,'TAKE_PROFIT_MARKET','sell',amttp2,float(RRTP(df,True,2,ask,TPRR1,TPRR2)),params={'stopPrice':float(RRTP(df,True,2,ask,TPRR1,TPRR2)),'triggerPrice':float(RRTP(df,True,2,ask,TPRR1,TPRR2)),'positionSide':Lside})
                logging.info(orderTP)
                logging.info(orderTP2)
            time.sleep(1)
            margin=ask*amount/int(lev)
            total = float(balance['total']['USDT'])
            msg ="BINANCE:\n" + "BOT         : \nCoin        : " + symbol + "\nStatus      : " + "OpenLong[BUY]" + "\nAmount    : " + str(amount) +"("+str(round((amount*ask),2))+" USDT)" + "\nPrice        :" + str(ask) + " USDT" + str(round(margin,2))+  " USDT"+ "\nBalance   :" + str(round(total,2)) + " USDT"
        else :
            msg = "MARGIN-CALL!!!\nยอดเงินต่ำกว่าที่กำหนดไว้  : " + str(min_balance) + '\nยอดปัจจุบัน ' + str(round(free,2)) + ' USD\nบอทจะทำการยกเลิกการเข้า Position ทั้งหมด' 
        notify.send(msg)
        candle(df,symbol,tf)
    except:
        notify.send('เกิดความผิดพลาดในการเข้า Order')
    return
#OpenShort=Sell
async def OpenShort(df, balance, symbol, lev, exchange, currentMODE, Sside, tf, RISK, Max_Size, TPPer, TPPer2, USETP, USESL, Tailing_SL,TPRR1,TPRR2):
    try:
        amount = sellsize(df,balance,symbol,exchange,RISK)
        try:
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.RequestTimeout as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.DDoSProtection as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.ExchangeNotAvailable as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.ExchangeError as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except Exception as e:
            print(e)
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        bid = float(info['bidPrice'])
        logging.info(f'Entry {symbol} Short @{bid} qmt:{amount}')
        leve = await setleverage(symbol,exchange)
        if amount*bid > Max_Size*int(leve):
            amount = Max_Size*int(leve)/bid  
        free = float(balance['free']['USDT'])
        amttp1 = amount*(TPPer/100)
        amttp2 = amount*(TPPer2/100)
        high = df['Highest'][len(df.index)-1]
        if free > min_balance :
            try:
                order = await exchange.createMarketOrder(symbol,'sell',amount,params={'positionSide':Sside})
                logging.info(order)
            except accxt.InsufficientFunds as e:
                logging.debug(e)
                notify.send(e)
                return        
            if USESL :
                if currentMODE['dualSidePosition']:
                    orderSL         = await exchange.create_order(symbol,'stop','buy',amount,float(high),params={'stopPrice':float(high),'triggerPrice':float(high),'positionSide':Sside})
                    if Tailing_SL :
                        ordertailingSL  = await exchange.create_order(symbol,'TRAILING_STOP_MARKET','buy',amount,params ={'activationPrice':float(RR1(df,False,bid)) ,'callbackRate': float(indi.callbackRate(df)),'positionSide':Sside})
                else :
                    orderSL         = await exchange.create_order(symbol,'stop','buy',amount,float(high),params={'stopPrice':float(high),'triggerPrice':float(high),'reduceOnly': True ,'positionSide':Sside})
                    if Tailing_SL :
                        ordertailingSL  = await exchange.create_order(symbol,'TRAILING_STOP_MARKET','buy',amount,params ={'activationPrice':float(RR1(df,False,bid)) ,'callbackRate': float(indi.callbackRate(df)),'reduceOnly': True ,'positionSide':Sside})
                if Tailing_SL :    
                    logging.info(ordertailingSL)
                logging.info(orderSL)
            if USETP :
                orderTP = await exchange.create_order(symbol,'TAKE_PROFIT_MARKET','buy',amttp1,float(RRTP(df,False,1,bid,TPRR1,TPRR2)),params={'stopPrice':float(RRTP(df,False,1,bid,TPRR1,TPRR2)),'triggerPrice':float(RRTP(df,False,1,bid,TPRR1,TPRR2)),'positionSide':Sside})
                logging.info(orderTP)
                orderTP2 = await exchange.create_order(symbol,'TAKE_PROFIT_MARKET','buy',amttp2,float(RRTP(df,False,2,bid,TPRR1,TPRR2)),params={'stopPrice':float(RRTP(df,False,2,bid,TPRR1,TPRR2)),'triggerPrice':float(RRTP(df,False,2,bid,TPRR1,TPRR2)),'positionSide':Sside})
                logging.info(orderTP2)
            time.sleep(1)
            margin=bid*amount/int(lev)
            total = float(balance['total']['USDT'])
            msg ="BINANCE:\nBOT         : \nCoin        : " + symbol + "\nStatus      : " + "OpenShort[SELL]" + "\nAmount    : " + str(amount) +"("+str(round((amount*bid),2))+" USDT)" + "\nPrice        :" + str(bid) + " USDT" + str(round(margin,2))+  " USDT"+ "\nBalance   :" + str(round(total,2)) + " USDT"
        else :
            msg = "MARGIN-CALL!!!\nยอดเงินต่ำกว่าที่กำหนดไว้  : " + str(min_balance) + '\nยอดปัจจุบัน ' + str(round(free,2)) + ' USD\nบอทจะทำการยกเลิกการเข้า Position ทั้งหมด' 
        notify.send(msg)
        candle(df,symbol,tf)
    except:
        notify.send('เกิดความผิดพลาดในการเข้า Order')
    return

def cooking(id, pwd):
    pepper = f'{id}{pwd}!{barsC}vz{id}'
    bytePwd = pepper.encode('utf-8')
    Salt = bcrypt.gensalt(rounds=12)
    cook = bcrypt.hashpw(bytePwd, Salt)
    return cook
#CloseLong=Sell
async def CloseLong(df,balance,symbol,amt,pnl,exchange,Lside, tf):
    try:
        amount = abs(amt)
        upnl = pnl
        try:
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.RequestTimeout as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.DDoSProtection as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.ExchangeNotAvailable as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.ExchangeError as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except Exception as e:
            print(e)
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        bid = float(info['bidPrice'])
        logging.info(f'Close {symbol} Long @{bid} qmt:{amount}')
        try:
            order = await exchange.createMarketOrder(symbol,'sell',amount,params={'positionSide':Lside})
        except:
            await asyncio.sleep(1)
            order = await exchange.createMarketOrder(symbol,'sell',amount,params={'positionSide':Lside})
        time.sleep(1)
        logging.info(order)
        total = float(balance['total']['USDT'])
        msg ="BINANCE:\n" + "BOT         : \nCoin        : " + symbol + "\nStatus      : " + "CloseLong[SELL]" + "\nAmount    : " + str(amount) +"("+str(round((amount*bid),2))+" USDT)" + "\nPrice        :" + str(bid) + " USDT" + "\nRealized P/L: " + str(round(upnl,2)) + " USDT"  +"\nBalance   :" + str(round(total,2)) + " USDT"
        notify.send(msg)
        candle(df,symbol,tf)
    except:
        notify.send('เกิดความผิดพลาดในการออก Order')
    return
#CloseShort=Buy
async def CloseShort(df,balance,symbol,amt,pnl,exchange,Sside, tf):
    try:
        amount = abs(amt)
        upnl = pnl
        try:
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.RequestTimeout as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.DDoSProtection as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.ExchangeNotAvailable as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except accxt.ExchangeError as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        except Exception as e:
            print(e)
            logging.info(e)
            await asyncio.sleep(1)
            info = (await exchange.fetchBidsAsks([symbol]))[symbol]['info']
        ask = float(info['askPrice'])
        logging.info(f'Close {symbol} Short @{ask} qmt:{amount}')
        try:
            order = await exchange.createMarketOrder(symbol,'buy',amount,params={'positionSide':Sside})
        except:
            time.sleep(1)
            order = await exchange.createMarketOrder(symbol,'buy',amount,params={'positionSide':Sside})
        time.sleep(1)
        logging.info(order)
        total = float(balance['total']['USDT'])
        msg ="BINANCE:\n" + "BOT         : \nCoin        : " + symbol + "\nStatus      : " + "CloseShort[BUY]" + "\nAmount    : " + str(amount) +"("+ str(round((amount*ask),2))+" USDT)" + "\nPrice        :" + str(ask) + " USDT" + "\nRealized P/L: " + str(round(upnl,2)) + " USDT"  +"\nBalance   :" + str(round(total,2)) + " USDT"
        notify.send(msg)
        candle(df,symbol,tf)
    except:
        notify.send('เกิดความผิดพลาดในการออก Order')
    return

async def feed(df,symbol, tf, RISK, Max_Size, TPPer, TPPer2, USETP, USESL, Tailing_SL,TPRR1,TPRR2 ,USELONG,USESHORT,leverage):
    is_in_Long = False
    is_in_Short = False
    is_in_position = False
    try:        
        posim = symbol.replace('/','')  
        exchange = await connect()  
        try:    
            balance = await exchange.fetch_balance()
        except accxt.RequestTimeout as e:
            print('[' + type(e).__name__ + ']')
            logging.info(e)
            print(str(e)[0:200])
            await asyncio.sleep(1)
            balance = await exchange.fetch_balance()
        except accxt.DDoSProtection as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            balance = await exchange.fetch_balance()
        except accxt.ExchangeNotAvailable as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            balance = await exchange.fetch_balance()
        except accxt.ExchangeError as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            balance = await exchange.fetch_balance()
        except Exception as e:
            print(e)
            logging.info(e)
            await asyncio.sleep(1)
            balance = await exchange.fetch_balance()
        positions = balance['info']['positions']
        current_positions = [position for position in positions if float(position['positionAmt']) != 0]
        status = pd.DataFrame(current_positions, columns=["symbol", "entryPrice","positionSide", "unrealizedProfit", "positionAmt", "initialMargin"])  
        amt = 0.0
        upnl = 0.0
        margin = 0.0
        netunpl = 0.0
        for i in status.index:
            margin += float(status['initialMargin'][i])
            netunpl += float(status['unrealizedProfit'][i])
        print(f'Margin Used : {margin}')
        print(f'NET unrealizedProfit : {netunpl}')
        try:    
            currentMODE = await exchange.fapiPrivate_get_positionside_dual()
        except accxt.RequestTimeout as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            currentMODE = await exchange.fapiPrivate_get_positionside_dual()
        except accxt.DDoSProtection as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            currentMODE = await exchange.fapiPrivate_get_positionside_dual()
        except accxt.ExchangeNotAvailable as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            currentMODE = await exchange.fapiPrivate_get_positionside_dual()
        except accxt.ExchangeError as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            currentMODE = await exchange.fapiPrivate_get_positionside_dual()
        if margin > max_margin:
            await notify.send(f'Margin ที่ใช้สูงเกินไปแล้ว\nMargin : {margin}\nที่กำหนดไว้ : {max_margin}',sticker_id=17857, package_id=1070)
        for i in status.index:
            if status['symbol'][i] == posim:
                amt = float(status['positionAmt'][i])
                upnl = float(status['unrealizedProfit'][i])
                break
        # NO Position
        if currentMODE['dualSidePosition']:
            Sside = 'SHORT'
            Lside = 'LONG'
        else:
            Sside = 'BOTH'
            Lside = 'BOTH'
        if not status.empty and amt != 0 :
            is_in_position = True
        # Long position
        if is_in_position and amt > 0  :
            is_in_Long = True
            is_in_Short = False
        # Short position
        elif is_in_position and amt < 0  :
            is_in_Short = True
            is_in_Long = False 
        else: 
            is_in_position = False
            is_in_Short = False
            is_in_Long = False 
        last = len(df.index)-1
        if df['BUY'][last] :
            print("changed to Bullish, buy")
            if is_in_Short :
                print('closeshort')
                await CloseShort(df,balance,symbol,amt,upnl,exchange,Sside, tf, RISK, Max_Size, TPPer, TPPer2, USETP, USESL, Tailing_SL,TPRR1,TPRR2)
            if not is_in_Long and USELONG:
                await exchange.cancel_all_orders(symbol)
                await OpenLong(df,balance,symbol,leverage,exchange,currentMODE,Lside, tf, RISK, Max_Size, TPPer, TPPer2, USETP, USESL, Tailing_SL,TPRR1,TPRR2)
                is_in_Long = True
            else:
                print("already in position, nothing to do")
        if df['SELL'][last]:
            print("changed to Bearish, Sell")
            if is_in_Long :
                print('closelong')
                await CloseLong(df,balance,symbol,amt,upnl,exchange,Lside, tf, RISK, Max_Size, TPPer, TPPer2, USETP, USESL, Tailing_SL,TPRR1,TPRR2)
            if not is_in_Short and USESHORT :
                await exchange.cancel_all_orders(symbol)
                await OpenShort(df,balance,symbol,leverage,exchange,currentMODE,Sside, tf, RISK, Max_Size, TPPer, TPPer2, USETP, USESL, Tailing_SL,TPRR1,TPRR2)
                is_in_Short = True
            else:
                print("already in position, nothing to do")
        await disconnect(exchange)
    except Exception as e:
        notify.send(f'เกิดความผิดพลาดในการ หาสัญญาณซื้อขาย {e}')
        logging.info(e)
        await disconnect(exchange)
    return 

async def get_dailytasks():
    daycollum = ['Symbol', 'LastPirce', 'Long-Term', 'Mid-Term', 'Short-Term']
    dfday = pd.DataFrame(columns=daycollum)
    try:
        symbolist = await get_symbol()
        for symbol in symbolist:
            # score , df = benchmarking(df)
            data1 = await fetchbars(symbol,'1d')
            score1, df1 = indi.benchmarking(data1, 12, 1.6, 30, 30, 30, 25, 30, 60)
            candle(df1,symbol,'1d')
            await asyncio.sleep(0.1)
            data2 = await fetchbars(symbol,'6h')
            score2, df2 = indi.benchmarking(data2, 12, 1.6, 30, 30, 30, 25, 30, 60)
            await asyncio.sleep(0.1)
            data3 = await fetchbars(symbol,'1h')
            score3, df3 = indi.benchmarking(data3, 12, 1.6, 30, 30, 30, 25, 30, 60)
            candle(df3,symbol,'1h')
            await asyncio.sleep(0.1)
            ask = data3['Close'][len(data3.index)-1]
            print(symbol,f"Long_Term : {score1} , Mid_Term : {score2} , Short_Term : {score3}")
            dfday = dfday.append(pd.Series([symbol, ask, score1, score2, score3],index=daycollum),ignore_index=True) 
        return  dfday
    except Exception as e:
        notify.send(f'เกิดความผิดพลาดในส่วนของแจ้งเตือนรายวัน {e}')
        logging.info(e)
    return  dfday

async def dailyreport():
    try:
        exchange = await connect()
        data = await get_dailytasks()
        todays = str(data)
        logging.info(f'{todays}')
        data = data.set_index('Symbol')
        data.drop(['Mid-Term','LastPirce'],axis=1,inplace=True)
        msg = str(data)
        notify.send(f'คู่เทรดที่น่าสนใจในวันนี้\n{msg}',sticker_id=1990, package_id=446) 
        try:    
            balance = await exchange.fetch_balance()
        except accxt.RequestTimeout as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            balance = await exchange.fetch_balance()
        except accxt.DDoSProtection as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            balance = await exchange.fetch_balance()
        except accxt.ExchangeNotAvailable as e:
            print('[' + type(e).__name__ + ']')
            print(str(e.args)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            balance = await exchange.fetch_balance()
        except accxt.ExchangeError as e:
            print('[' + type(e).__name__ + ']')
            print(str(e)[0:200])
            logging.info(e)
            await asyncio.sleep(1)
            balance = await exchange.fetch_balance()
        except Exception as e:
            print(e)
            logging.info(e)
            await asyncio.sleep(1)
            balance = await exchange.fetch_balance()
        await disconnect(exchange)
        positions = balance['info']['positions']
        current_positions = [position for position in positions if float(position['positionAmt']) != 0]
        status = pd.DataFrame(current_positions, columns=["symbol", "entryPrice","positionSide", "unrealizedProfit", "positionAmt", "initialMargin"])   
        m = status.index
        margin = 0.0
        netunpl = 0.0
        for i in m:
            margin += float(status['initialMargin'][i])
            netunpl += float(status['unrealizedProfit'][i])
        print(f'Margin Used : {margin}')
        print(f'NET unrealizedProfit : {margin}')
        status = status.sort_values(by=['unrealizedProfit'],ascending=False)
        status = status.head(1)
        sim1 = status['symbol'][0]
        upnl = round(float(status['unrealizedProfit'][0]),2)
        entryP = status['entryPrice'][0]
        metthod = status['positionSide'][0]
        msg2 = f'{sim1} {metthod} at {entryP} \nunrealizedProfit : {upnl}$'
        notify.send(f'Top Performance\n{msg2}\n-----\nNet Margin Used : {round(float(margin),2)}$\nNet unrealizedProfit : {round(float(netunpl),2)}$',sticker_id=1995, package_id=446) 
        return 
    except:
        notify.send('เกิดความผิดพลาดในส่วนของแจ้งเตือนรายวัน')
        await disconnect(exchange)
    return

t1 = 0
async def main():
    global symbolist, botStatus, insession, t1, t2
    symbolist = pd.read_sql(f'SELECT * FROM Bot',con=con)
    get_config()
    t2 = time.time()
    if insession['name'] and t1 == 0:
        t1 = time.time()
    if float(t2-t1) > 900 :
        insession['name'] = False
        t1 = 0
    if str(local_time[14:-9]) == '1':
        insession['day'] = False
        insession['hour'] = False
    if str(local_time[12:-9]) == '8:0' and not insession['day']:
        insession['day'] = True
        insession['hour'] = True   
        await asyncio.gather(dailyreport())     
    if str(local_time[14:-9]) == '0' and not insession['hour']:
        total = round(float(balance['total']['USDT']),2)
        notify.send(f'Total Balance : {total} USDT',sticker_id=10863, package_id=789)
        insession['hour'] = True
    if len(symbolist.index) > 0:
        try:
            exchange = await connect()
            try:
                balance = await exchange.fetch_balance()  
            except accxt.RequestTimeout as e:
                print('[' + type(e).__name__ + ']')
                print(str(e)[0:200])
                logging.info(e)
                await asyncio.sleep(1)
                balance = await exchange.fetch_balance()
            except accxt.DDoSProtection as e:
                print('[' + type(e).__name__ + ']')
                print(str(e.args)[0:200])
                logging.info(e)
                await asyncio.sleep(1)
                balance = await exchange.fetch_balance() 
            except accxt.ExchangeNotAvailable as e:
                print('[' + type(e).__name__ + ']')
                print(str(e.args)[0:200])
                logging.info(e)
                await asyncio.sleep(1)
                balance = await exchange.fetch_balance()  
            except accxt.ExchangeError as e:
                print('[' + type(e).__name__ + ']')
                print(str(e)[0:200])
                logging.info(e)
                await asyncio.sleep(1)
                balance = await exchange.fetch_balance() 
            except ConnectionError as e:
                print('[' + type(e).__name__ + ']')
                print(str(e)[0:200])
                logging.info(e)
                balance = await exchange.fetch_balance()
            exchange.precisionMode = accxt.DECIMAL_PLACES
            free = float(balance['free']['USDT'])
            seconds = time.time()
            local_time = time.ctime(seconds)
            await disconnect(exchange)
            for i in range(len(symbolist.index)):
                try:
                    USELONG     = True if symbolist['Uselong'][i] == 1 else False
                    USESHORT    = True if symbolist['Useshort'][i]== 1 else False
                    USETP       = True if symbolist['UseTP'][i] == 1 else False
                    USESL       = True if symbolist['UseSL'][i] == 1 else False
                    Tailing_SL  = True if symbolist['Tail_SL'][i] == 1 else False
                    RISK        = str(symbolist['Risk'][i])
                    Max_Size    = str(symbolist['maxMargin'][i])
                    if Max_Size[0]=='$':
                        Max_Size=float(Max_Size[1:len(Max_Size)])
                    elif Max_Size[0]=='%':
                        size=float(Max_Size[1:len(Max_Size)])
                        Max_Size = free*(size/100)
                    else: Max_Size=float(Max_Size)
                    TPRR1       = symbolist['RR1'][i]
                    TPRR2       = symbolist['RR2'][i]
                    TPPer       = symbolist['TP1'][i]
                    TPPer2      = symbolist['TP2'][i]
                    symbol      = symbolist['symbol'][i]
                    leverage    = symbolist['leverage'][i]
                    tf          = symbolist['timeframe'][i]
                    atr_p       = symbolist['ATR'][i]
                    atr_m       = symbolist['ATR_m'][i]
                    rsi         = symbolist['RSI'][i]
                    ema         = symbolist['EMA'][i]
                    linear      = symbolist['subhag'][i]
                    smooth      = symbolist['smooth'][i]
                    AOL         = symbolist['Andean'][i]
                    Pivot       = symbolist['Pivot'][i]
                except Exception as e :
                    pass
                data        = await fetchbars(symbol,tf)
                try:
                    score1, df = indi.benchmarking(data, atr_p, atr_m, ema, linear, smooth, rsi, AOL, Pivot)
                except Exception as e:
                    notify.send('เกิดความผิดพลาดที่การคำนวน')
                    continue
                print(f"{symbol} is {score1}")
                await asyncio.gather(feed(df,symbol, tf, RISK, Max_Size, TPPer, TPPer2, USETP, USESL, Tailing_SL,TPRR1,TPRR2 ,USELONG,USESHORT,leverage))
                await asyncio.sleep(1)
                botStatus = 'Bot is running...'
        except Exception as e:
            notify.send(f'เกิดความผิดพลาดที่ Main : {e}')
            logging.info(e)
            await disconnect(exchange)
    else:
        botStatus = 'Nothing to do now.....'
    

async def async_main():
    await asyncio.gather(main())
        
def run():
    while True:
        asyncio.run(async_main())

#end VXMA Start Dash app
nomEX = ccxt.binance()
symbols = pd.DataFrame()
syms = []
try:
    market = nomEX.fetchTickers(params={'type':'future'})
except:
    time.sleep(2)
    market = nomEX.fetchTickers(params={'type':'future'})
for x,y in market.items()    :
    if y['symbol'][len(y['symbol'])-4:len(y['symbol'])] == "USDT":
        symbols = symbols.append(y , ignore_index=True)
symbols = symbols.set_index('symbol')
symbols['datetime'] = pd.to_datetime(symbols['timestamp'], unit='ms', utc=True).map(lambda x: x.tz_convert('Asia/Bangkok'))
symbols = symbols.sort_values(by=['quoteVolume'],ascending=False)
symbols.drop(['timestamp','high','low','average'],axis=1,inplace=True)
symbols.drop(['bid','bidVolume','ask','askVolume'],axis=1,inplace=True)
symbols.drop(['vwap','open','baseVolume','info'],axis=1,inplace=True)
symbols.drop(['close','previousClose','datetime'],axis=1,inplace=True)
newsym = []
for symbol in symbols.index:
    newsym.append(symbol)

#HTML COMPONENT 
symbol_dropdown = html.Div([html.P('Symbol:'),dcc.Dropdown(id='symbol-dropdown',options=[{'label': symbol, 'value': symbol} for symbol in newsym],value='BTC/USDT')])
timeframe_dropdown = html.Div([html.P('Timeframe:'),dcc.Dropdown(id='timeframe-dropdown',options=[{'label': timeframe, 'value': timeframe} for timeframe in TIMEFRAMES],value='1d')])
num_bars_input = html.Div([html.P('Zoom'),dcc.Dropdown(id='num-bar-input', value='X4', options=['X1','X2','X3','X4','X5'])])
atr_input = html.Div([html.P('ATR Period'),dbc.Input(id='atr-input', type='number', value='12', min='1', max='100')])
atrm_input = html.Div([html.P('ATR Mutiply'),dbc.Input(id='atrm-input', type='number', value='1.6', min='0.1', max='100', step='0.1')])
EMA_input = html.Div([html.P('EMA'),dbc.Input(id='EMA-input', type='number', value='30', min='1', max='500')])
SUBHAG_input = html.Div([html.P('SUBHAG'),dbc.Input(id='SUBHAG-input', type='number', value='30', min='1', max='500')])
SMOOTH_input = html.Div([html.P('SMOOTH'),dbc.Input(id='SMOOTH-input', type='number', value='30', min='1', max='500')])
RSI_input = html.Div([html.P('RSI'),dbc.Input(id='RSI-input', type='number', value='14', min='1', max='100')])
AOL_input = html.Div([html.P('Andean Oscillator'),dbc.Input(id='Andean-Oscillator-input', type='number', value='30', min='1', max='500')])
Pivot_input = html.Div([html.P('Pivot lookback'),dbc.Input(id='Pivot-lookback-input', type='number', value='60', min='1', max='500')])
RRTP1_input = html.Div([html.P('Risk:Reward TP1'),dbc.Input(id='RR-TP1-input', type='number', value='3', min='1', max='100', step='0.1')])
RRTP2_input = html.Div([html.P('Risk:Reward TP2'),dbc.Input(id='RR-TP2-input', type='number', value='4.5', min='1', max='100', step='0.1')])
perTP1_input = html.Div([html.P('Percent TP1'),dbc.Input(id='per-TP1-input', type='number', value='50', min='0', max='100')])
perTP2_input = html.Div([html.P('Percent TP2'),dbc.Input(id='per-TP2-input', type='number', value='50', min='0', max='100')])
RISK_input = html.Div([html.P('RISK ($,%)lost/trade'),dbc.Input(id='Risk-input', type='text', value='$3')])
Margin_input = html.Div([html.P('MaxMargin/trade'),dbc.Input(id='maxmargin-input', type='text', value='%5')])
Apply_input = html.Div([dbc.Button('Apply to Chart',id='Apply-strategy',title = 'Apply_Strategy', name='refresh', color='warning', n_clicks=0)])
Runbot_input = html.Div([dcc.ConfirmDialogProvider([dbc.Button('Start Bot',title = 'Start_Bot', name='RunBot', size="lg", color='danger' , n_clicks=0)],message='ชัวร์แล้วนาาา?',submit_n_clicks=0, id='run-input')])
Leverage_input = html.Div([html.P('Leverage'),dbc.Input(id='leverage-input', type='number', value='20', min='1', max='125')])
API_KEY_input = html.Div([html.P('API KEY'),dbc.Input(id='api-key-input', type='text', value=f'Binance API Key {API_KEY[:-50]}**************************************************')])
API_SECRET_input = html.Div([html.P('API SECRET'),dbc.Input(id='api-secret-input', type='password', value='Binance API Secret Key')])
NOTIFY_input = html.Div([html.P('LINE : Notify'),dbc.Input(id='api-notify-input', type='text', value=f'Line Notify key {LINE_TOKEN[:-35]}**************************************************')])
Sumkey_input = html.Div([dbc.Button('Apply',id='set-api-key',title = 'Setting', name='refresh', size="lg", color='warning', n_clicks=0)])
Freebalance_input = html.Div([html.P('Free Balance $'),dbc.Input(id='freebalance-input', type='text', value=f'Free Balance : วงเงินสำหรับบอท {max_margin}')])
minBalance_input = html.Div([html.P('Min Balance $'),dbc.Input(id='minBalance-input', type='text', value=f'Min Balance : ถ้าเงินเหลือต่ำกว่านี้บอทจะหยุดเข้า Position {min_balance}')])
passwd_input = html.Div([html.P('Reset password'),dbc.Input(id='passwd-input', type='password', value='reset password')])
passwd2_input = html.Div([html.P('Confirm password'),dbc.Input(id='repasswd2-input', type='password', value='Confirm password')])
newUsername = html.Div([html.P('New Username'),dbc.Input(id='newUsername-input', type='text', value='Change new Username')])
EMAFAST_input = html.Div([html.P('EMA Fast'),dbc.Input(id='emafast-input', type='number', value='12', min='1', max='500')])
EMASLOW_input = html.Div([html.P('EMA Slow'),dbc.Input(id='emaslow-input', type='number', value='26', min='1', max='500')])
resetpass_input = html.Div([dbc.Button('Reset Password',id='resetpass-input', color='danger', name='RunBot', size="lg", n_clicks=0)])
logoutBut = html.Div([dbc.Button('Log Out',id='logoutBut', color='danger', size="lg", n_clicks=0)])
edit_table = html.Div([dcc.ConfirmDialogProvider([dbc.Button('Edit', color='warning', size="lg", n_clicks=0)],id='edit-table',message='ชัวร์แล้วนาาา?',submit_n_clicks=0)])
refresh_table = html.Div([dbc.Button('Refresh',id='update-table', color='info', size="lg", n_clicks=0)])

option_input = html.Div([dcc.Checklist(
   options=[
       {'label': 'Long Position', 'value': 'ul'},
       {'label': 'Short Position', 'value': 'us'},
       {'label': 'Take-Profit', 'value': 'tp'},
       {'label': 'Stop-Loss', 'value': 'sl'},
       {'label': 'Tailing-Stop ', 'value': 'tsl'},],value=['ul','us','tp','sl','tsl'],id="switches-input")])
tabs_styles = {'height': '40px'}
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '6px',
    'backgroundColor': 'black',
    'color': 'white'}
tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': 'Gray',
    'color': 'white',
    'fontWeight': 'bold',
    'padding': '6px'}
ready_input = html.Div([dcc.Checklist(options=[{'label': 'ฉันเข้าใจในความเสี่ยง และยอมรับความเจ็บปวดหลังพ่ายแพ้', 'value': 'pass'},],value=[],id="ready-input")])
edit_input = html.Div([dcc.Checklist(options=[{'label': 'ฉันได้ตรวจทานการตั้งค่าใหม่เรียบร้อยแล้ว', 'value': 'pass'},],value=[],id="edit-input")])
readyAPI_input = html.Div([dcc.Checklist(options=[{'label': 'ฉันได้ตรวจทานความถูกต้องเรียบร้อยแล้ว และยอมรับว่า Vaz จะไม่รับผิดชอบเงินของคุณ', 'value': 'pass'},],value=[],id="readyAPI-input")],style={'align':'center'})
session = dcc.Interval(id='session', interval=900000)
refresher_i = dcc.Interval(id='update', interval=9999)
index_page = html.Div([
    html.Div(dcc.Input(id="user", type="text", placeholder="Enter Username",className="inputbox1",style={'margin-left':'35%','width':'450px','height':'45px','padding':'10px','margin-top':'60px','font-size':'16px','border-width':'3px','border-color':'#a0a3a2'}),),
    html.Div(dcc.Input(id="passw", type="password", placeholder="Enter Password",className="inputbox2",style={'margin-left':'35%','width':'450px','height':'45px','padding':'10px','margin-top':'10px','font-size':'16px','border-width':'3px','border-color':'#a0a3a2',}),),
    html.Div([dcc.Link([dbc.Button('Log in',id='verify', color='danger', name='RunBot', size="lg", n_clicks=0, style={'margin-left':'35%','width':'450px','height':'45px','padding':'10px','margin-top':'10px','font-size':'16px','border-width':'3px','border-color':'#a0a3a2',})],href='/index',refresh=True)]),html.Div(id='output1')])
main_page = html.Div([session,
    dcc.Tabs(id='tabs-one', value='tab-4', children=[
        dcc.Tab(label='Summary', value='tab-4', style=tab_style, selected_style=tab_selected_style),
        dcc.Tab(label='VXMA bot', value='tab-1', style=tab_style, selected_style=tab_selected_style),
        dcc.Tab(label='EMA bot', value='tab-5', style=tab_style, selected_style=tab_selected_style),
        dcc.Tab(label='Running Bot', value='tab-2', style=tab_style, selected_style=tab_selected_style),
        dcc.Tab(label='Setting', value='tab-3', style=tab_style, selected_style=tab_selected_style),
    ], style=tabs_styles),html.Div(id='tabs-content-1')],style={'margin-left': '1%','margin-right':'1%'})

summary_page = html.Div([
                dbc.Row([
                    html.H3('ยินดีต้อนรับเข้าสู่บอท VXMA x Binance API'),
                    html.H5('Donate : XMR'),
                    html.P('87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm')
                ]),
                dbc.Row([
                    html.H4('โปรดใช้งานบอทอย่างระมัดระวัง : Use as your own RISK', style={'color': 'red'})
                ])
                
            ])

setting_page = html.Div([html.Div(id='loading'),
                dbc.Row([
                    html.Table([
                            html.Td([
                                html.H3('API Setting'),
                                html.H5('Donate : XMR'),
                                html.P('87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm')
                            ]),
                            html.Td([
                                dcc.Link([
                                    logoutBut
                                ],href='/',refresh=True)
                            ])
                    ]),
                ]),
                dbc.Row([html.Hr(),html.Div(id='alert-su'),html.Hr(),
                    html.Table([
                            html.Td([Freebalance_input],style={'align-content': 'center'}),
                            html.Td([minBalance_input],style={'align-content': 'center'})
                            ]),
                    html.Table([
                            html.Td([API_KEY_input],style={'align-content': 'center'}),
                            html.Td([API_SECRET_input],style={'align-content': 'center'})
                            ]),
                    html.Table([
                            html.Td([NOTIFY_input],style={'align-content': 'center'}),
                            # html.Td([],style={'align-content': 'center'})
                            ]),
                    passwd2_input,
                    readyAPI_input,
                    Sumkey_input,
                    html.Hr(),
                    html.H6('เข้าใช้งานครั้งแรกให้เปลี่ยนรหัสผ่านทันที!!!', style={'color': 'red'}),
                    html.Div(id='alert-fai'),
                    newUsername,
                    passwd_input,
                    passwd2_input,
                    html.Table([
                            html.Td([resetpass_input],style={'align-content': 'center'}),
                            html.Td([html.H4('โปรดใช้งานบอทอย่างระมัดระวัง : Use as your own RISK')],style={'align-content': 'center'})
                            ]),
                ])
                
            ])
botdata_page = html.Div([refresher_i,html.Div(id='alert-ta'),
                dbc.Row([
                    html.Table([
                            html.Td([
                                html.H3('API Setting'),
                                html.H5('Donate : XMR'),
                                html.P('87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm')
                            ]),
                            html.Table([
                            html.Tr([refresh_table],style={'align-content': 'center'}),
                            edit_input,
                            html.Tr([edit_table],style={'align-content': 'center'})
                            ])
                    ])
                ]),html.Hr(),
                dbc.Row([
                    html.Div(id='datatable')
                ])
                
            ])

main_index = html.Div([refresher_i,
                dbc.Row([
                    dbc.Col([
                        num_bars_input,
                        symbol_dropdown,
                        timeframe_dropdown,
                    ]),
                    dbc.Col([
                        Margin_input,
                        RRTP1_input,
                        RRTP2_input,
                    ]),
                    dbc.Col([
                        RISK_input,
                        perTP1_input,
                        perTP2_input
                    ]),
                    dbc.Col([
                        Leverage_input,
                        option_input,
                    ]),
                    dbc.Col([
                        Pivot_input,
                        RSI_input,
                        EMA_input,
                    ]),
                    dbc.Col([
                        AOL_input,
                        SUBHAG_input,
                        SMOOTH_input
                    ]),
                    dbc.Col([
                        atr_input,
                        atrm_input,
                        html.H5('ตรวจดูตั้งค่าอีกครั้ง!', style={'color': 'red'}),
                    ]),
                    dbc.Col([
                        html.P('กด Apply ลองดูก่อน'),
                        Apply_input,
                        ready_input,
                        Runbot_input,
                        html.Div(id='alert-suc'),
                    ]),
                ])
                ,html.Hr(),
                dbc.Row([
                        html.Div(id='page-content')                
                ])
                ,html.Hr(),
                dbc.Row([
                    html.P('by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm')
                ])
                
            ])

ema_index = html.Div([refresher_i,
                dbc.Row([
                    dbc.Col([
                        num_bars_input,
                        symbol_dropdown,
                        timeframe_dropdown,
                    ]),
                    dbc.Col([
                        Margin_input,
                        RRTP1_input,
                        RRTP2_input,
                    ]),
                    dbc.Col([
                        RISK_input,
                        perTP1_input,
                        perTP2_input
                    ]),
                    dbc.Col([
                        Leverage_input,
                        option_input,
                    ]),
                    dbc.Col([
                        EMAFAST_input,
                        EMASLOW_input,
                    ]),
                    dbc.Col([
                        html.H1('DEMO!', style={'color': 'red'}),
                        # html.H5('ตรวจดูตั้งค่าอีกครั้ง!', style={'color': 'red'}),
                    ]),
                    dbc.Col([
                        html.P('กด Apply ลองดูก่อน'),
                        Apply_input,
                        ready_input,
                        html.Div(id='alert-ema'),
                    ]),
                ])
                ,html.Hr(),
                dbc.Row([
                        html.Div(id='page-content2')                
                ])
                ,html.Hr(),
                dbc.Row([
                    html.P('by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm')
                ])
                
            ])
# creates the Dash App
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG],suppress_callback_exceptions=True, title='VXMA Bot', update_title=None)
register_page("VXMA", path='/index', layout=main_page)
app.layout = html.Div([dcc.Location(id='url', refresh=True),html.Div(id='page-content-login')])
#logout button
@app.callback(
    Output('loading', 'children'),
    Input('session', 'n_intervals'),
    Input('logoutBut', 'n_clicks'))
def logout(n,click):
    if click is not None or n is not None:
        insession['name'] = False
        return 'loged out'
    else:
        return PreventUpdate
    
#login page
@app.callback(
    Output('output1', 'children'),
    Input('verify', 'n_clicks'),
    State('user', 'value'),
    State('passw', 'value'))
def update_output(n_clicks, uname, passw):
    config = pd.read_sql('SELECT * FROM user',con=con)
    li = config['id'][0]
    if uname =='' or uname == None or passw =='' or passw == None:
        return html.Div(children='',style={'padding-left':'550px','padding-top':'10px'})
    elif uname != li:
        return html.Div(children='Incorrect Username',style={'padding-left':'550px','padding-top':'40px','font-size':'16px'})
    elif perf(uname, passw):
        insession['name'] = True
        return html.Div(children='Loged-In ',style={'padding-left':'550px','padding-top':'40px','font-size':'16px'})
    elif insession['name']:
        return main_page
    else:
        return html.Div(children='Incorrect Password',style={'padding-left':'550px','padding-top':'40px','font-size':'16px'})
#tab component
@app.callback(
    Output('tabs-content-1', 'children'),
    Input('tabs-one', 'value'))
def display_page(tab):
    if tab == 'tab-4':
        return summary_page
    elif tab == 'tab-1':
        return main_index
    elif tab == 'tab-2':
        return botdata_page
    elif tab == 'tab-3': 
        return setting_page
    elif tab == 'tab-5':
        return ema_index
    else:
        return '404'
#url condition
@app.callback(
    Output('page-content-login', 'children'),
    Input('url', 'pathname'))
def pathname_page(pathname):
    if pathname == '/index' and insession['name']:
        return main_page
    elif insession['name']:
        return main_page
    elif not insession['name']:
        return index_page
    else:
        return 'Code : 404'
#VXMA strategy
@app.callback(
    Output('page-content', 'children'),
    Input('update', 'n_intervals'),
    Input('Apply-strategy', 'n_clicks'),
    State('symbol-dropdown', 'value'),
    State('timeframe-dropdown', 'value'),
    State('num-bar-input', 'value'),
    State('atr-input', 'value'),
    State('atrm-input', 'value'),
    State('EMA-input', 'value'),
    State('SUBHAG-input', 'value'),
    State('SMOOTH-input', 'value'),
    State('RSI-input', 'value'),
    State('Andean-Oscillator-input', 'value'),
    State('Pivot-lookback-input', 'value'),
    suppress_callback_exceptions=True)
def update_VXMA_chart(interval, click, symbol, timeframe, zoom, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip, aol_ip, pivot):
    timeframe = TIMEFRAMES_DICT[timeframe]
    num_bars = ZOOM_DICT[zoom]
    try:
        bars = nomEX.fetch_ohlcv(symbol, timeframe=timeframe, since = None, limit =barsC)
    except:
        time.sleep(2)
        bars = nomEX.fetch_ohlcv(symbol, timeframe=timeframe, since = None, limit =barsC)
    df = pd.DataFrame(bars, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).map(lambda x: x.tz_convert('Asia/Bangkok'))
    df = df.set_index('timestamp')
    df = indi.vxma(df, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip, aol_ip, pivot)
    data = df.tail(num_bars)
    fig = go.Figure(data=go.Candlestick(x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                    showlegend=False,
                    name=f'{symbol}'),
                    layout=dict(autosize=True, template='plotly_dark'))
    vxma = go.Scatter(x=data.index,y=data['vxma'],mode="lines", line=go.scatter.Line(color='yellow'), showlegend=True, name='VXMA')
    buy = go.Scatter(x=data.index,y=data['buyPrice'],  mode="markers", marker=dict(size=15, color="lime"), showlegend=True, name='Buy')
    sell = go.Scatter(x=data.index,y=data['sellPrice'],  mode="markers", marker=dict(size=15, color="orange"), showlegend=True, name='Sell')
    pvtop = go.Scatter(x=data.index,y=data['Highest'],mode="lines", line=go.scatter.Line(color='red'), showlegend=True, name='Pivot Top')
    pvbot = go.Scatter(x=data.index,y=data['Lowest'],mode="lines", line=go.scatter.Line(color='green'), showlegend=True, name='Pivot Bottom')
    fig.add_trace(vxma)
    fig.add_trace(buy)
    fig.add_trace(sell)
    fig.add_trace(pvtop)
    fig.add_trace(pvbot)
    fig.update(layout_xaxis_rangeslider_visible=False)
    fig.update_layout(yaxis={'side': 'right'})
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True
    return [dcc.Graph(figure=fig, config={'displayModeBar': False})]
#EMA strategy
@app.callback(
    Output('page-content2', 'children'),
    Input('update', 'n_intervals'),
    Input('Apply-strategy', 'n_clicks'),
    State('symbol-dropdown', 'value'),
    State('timeframe-dropdown', 'value'),
    State('num-bar-input', 'value'),
    State('emafast-input', 'value'),
    State('emaslow-input', 'value'),
    suppress_callback_exceptions=True)
def update_EMA_chart(interval, click, symbol, timeframe, zoom, emafast, emaslow):
    timeframe = TIMEFRAMES_DICT[timeframe]
    num_bars = ZOOM_DICT[zoom]
    try:
        bars = nomEX.fetch_ohlcv(symbol, timeframe=timeframe, since = None, limit =barsC)
    except:
        time.sleep(2)
        bars = nomEX.fetch_ohlcv(symbol, timeframe=timeframe, since = None, limit =barsC)
    df = pd.DataFrame(bars, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).map(lambda x: x.tz_convert('Asia/Bangkok'))
    df = df.set_index('timestamp')
    df = indi.ema(df, emafast, emaslow)
    data = df.tail(num_bars)
    fig = go.Figure(data=go.Candlestick(x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                    showlegend=False,
                    name=f'{symbol}'),
                    layout=dict(autosize=True, template='plotly_dark'))
    ema1 = go.Scatter(x=data.index,y=data['emafast'],mode="lines", line=go.scatter.Line(color='blue'), showlegend=True, name='FAST')
    ema2 = go.Scatter(x=data.index,y=data['emaslow'],mode="lines", line=go.scatter.Line(color='yellow'), showlegend=True, name='SLOW')
    buy = go.Scatter(x=data.index,y=data['buyPrice'],  mode="markers", marker=dict(size=15, color="lime"), showlegend=True, name='Buy')
    sell = go.Scatter(x=data.index,y=data['sellPrice'],  mode="markers", marker=dict(size=15, color="orange"), showlegend=True, name='Sell')
    fig.add_trace(ema1)
    fig.add_trace(ema2)
    fig.add_trace(buy)
    fig.add_trace(sell)
    fig.update(layout_xaxis_rangeslider_visible=False)
    fig.update_layout(yaxis={'side': 'right'})
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True
    return [dcc.Graph(figure=fig, config={'displayModeBar': False})]  
#VXMA excute bot
@app.callback(
    Output('alert-suc', 'children'),
    Input('run-input', 'submit_n_clicks'),
    State('symbol-dropdown', 'value'),
    State('timeframe-dropdown', 'value'),
    State('atr-input', 'value'),
    State('atrm-input', 'value'),
    State('EMA-input', 'value'),
    State('SUBHAG-input', 'value'),
    State('SMOOTH-input', 'value'),
    State('RSI-input', 'value'),
    State('Andean-Oscillator-input', 'value'),
    State('switches-input' , 'value'),
    State('leverage-input', 'value'),
    State('Pivot-lookback-input', 'value'),
    State('RR-TP1-input', 'value'),
    State('RR-TP2-input', 'value'),
    State('per-TP1-input', 'value'),
    State('per-TP2-input', 'value'),
    State('Risk-input', 'value'),
    State('maxmargin-input', 'value'),
    State('ready-input', 'value'))
def excuteBot(click, symbol, timeframe, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip, aol_ip, switches, leverage, Pivot, RR1, RR2, TP1, TP2, Risk,maxMargin, ready):
    if click is not None:
        data = pd.DataFrame(columns=BOTCOL)
        ok = True if 'pass' in ready else False
        if ok:
            try:
                ul = True if 'ul' in switches else False
                us = True if 'us' in switches else False
                tp = True if 'tp' in switches else False
                sl = True if 'sl' in switches else False
                tsl= True if 'tsl' in switches else False
                id = f'{symbol}_{timeframe}'
                compo = [id, symbol, timeframe, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip, aol_ip, ul, us, tp , sl, tsl, leverage, Pivot, RR1, RR2, TP1, TP2, Risk, maxMargin]
                data.loc[1] = compo
                data = data.set_index('id')
                data.to_sql('Bot', con=con, if_exists='append', index_label='id')
                notify.send('Setting บอทเรียบร้อย บอทกำลังทำงาน!')
                return [dbc.Alert("Success.", dismissable=True, duration=5000, is_open=True)]
            except sqlite3.Error as e:
                print(e)
                return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]
        else:
            return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]
    else:
        return  PreventUpdate
#api setting
@app.callback(
    Output('alert-su', 'children'),
    Input('set-api-key', 'n_clicks'),
    State('freebalance-input', 'value'),
    State('minBalance-input', 'value'),
    State('api-key-input', 'value'),
    State('api-secret-input', 'value'),
    State('api-notify-input', 'value'),
    State('repasswd2-input', 'value'),
    State('readyAPI-input', 'value'),
    suppress_callback_exceptions=True)
def setting(click, freeB, minB, api_key, apiZ, notify, pwd, ready):
    if click is not None:
        data = pd.DataFrame(columns=['freeB','minB','apikey','apisec','notify'])
        ok = True if 'pass' in ready else False
        config = pd.read_sql('SELECT * FROM user',con=con)
        id = config['id'][0]
        valit = True if perf(id, pwd) else False
        if ok and valit:
            try:
                compo = [freeB, minB, api_key, apiZ, notify]
                data.loc[1] = compo
                data = data.set_index('apikey')
                data.to_sql('key', con=con, if_exists='replace', index=True, index_label='apikey')
                notify.send('Setting API update')
                return [dbc.Alert("Success.", dismissable=True, duration=5000, is_open=True)]
            except sqlite3.Error as e:
                print(e)
                return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]
        else:
            return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]
    else:
        return PreventUpdate
#reset user pass
@app.callback(
    Output('alert-fai', 'children'),
    Input('resetpass-input', 'n_clicks'),
    State('passwd-input', 'value'),
    State('repasswd2-input', 'value'),
    State('newUsername-input', 'value'),
    suppress_callback_exceptions=True)
def resetpwd(click, pwd1, pwd2, id):
    if click is not None:
        data = pd.DataFrame(columns=['id','pass'])
        valit = True if pwd1 == pwd2 else False
        if valit:
            try:
                cook = cooking(id, pwd2)
                compo = [id, cook]
                data.loc[1] = compo
                data = data.set_index('id')
                data.to_sql('user', con=con, if_exists='replace', index=True, index_label='id')
                notify.send('Setting รหัสผ่านสำเร็จ')
                return [dbc.Alert("Success.", dismissable=True, duration=5000, is_open=True)]
            except sqlite3.Error as e:
                print(e)
                return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]
        else:
            return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]
    else:
        return PreventUpdate
#read data running bot
@app.callback(
Output('datatable', 'children'),
Input('update-table', 'n_clicks'),)
def runningBot(click):
    if click is not None:
        get_config()
        return dash_table.DataTable(data=symbolist.to_dict('records'),columns=[{"name": i, "id": i} for i in symbolist],page_current=0,page_size=99,page_action='custom',editable=True, id='datatable', style_table={'color':'black'})
    else:
        return PreventUpdate
#write data edit running bot
@app.callback(
Output('alert-ta', 'children'),
Input('edit-table', 'submit_n_clicks'),
State('datatable', 'data'),
State('edit-input', 'value'))
def edit_menu(click, rows, ready):
    if click is not None and ready is not None:
        ok = True if 'pass' in ready else False
        if ok:
            try:
                df = pd.DataFrame(rows, columns=BOTCOL)
                df = df.set_index('id')
                df.to_sql('Bot', con=con, if_exists='replace', index_label='id')
                data = pd.read_sql(f'SELECT * FROM Bot',con=con)
                return [dbc.Alert("Success.", dismissable=True, duration=5000, is_open=True)]
            except Exception as e:
                print(e)
                return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]
        else:
            return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]
    else:
        return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]

if __name__ == "__main__":
    while True:
        th = Thread(target=run)
        th.start()
        app.run(debug=False,port=80)
        th.join()
