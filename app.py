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
from dash import Dash, html, dcc, dash_table, register_page, CeleryManager, DiskcacheManager
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash.dependencies import Input, Output, State, ClientsideFunction
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from threading import Thread
import os
from uuid import uuid4
launch_uid = uuid4()

if 'REDIS_URL' in os.environ:
    # Use Redis & Celery if REDIS_URL set as an env variable
    from celery import Celery
    celery_app = Celery(__name__, broker=os.environ['REDIS_URL'], backend=os.environ['REDIS_URL'])
    background_callback_manager = CeleryManager(
        celery_app, cache_by=[lambda: launch_uid], expire=60
    )

else:
    # Diskcache for non-production apps when developing locally
    import diskcache
    cache = diskcache.Cache("./cache")
    background_callback_manager = DiskcacheManager(
        cache, cache_by=[lambda: launch_uid], expire=60
    )

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
# API_KEY = str(os.environ['API_KEY'])
# API_SECRET = str(os.environ['API_SECRET'])
# LINE_TOKEN=str(os.environ['Line_Notify_Token'])

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
    notify = LineNotify(LINE_TOKEN)
    if MIN_BALANCE[0]=='$':
        min_balance=float(MIN_BALANCE[1:len(MIN_BALANCE)])
    else: min_balance=float(MIN_BALANCE)
    if max_margin[0]=='$' :
        max_margin = float(max_margin[1:len(max_margin)])
    else: max_margin = float(max_margin)
    BNBCZ = {
    "apiKey": API_KEY,
    "secret": API_SECRET,
    'options': {'defaultType': 'future'},
    'enableRateLimit': True,
    'adjustForTimeDifference': True}
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
        if df['BUY'][last] == 1:
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
        if df['SELL'][last]  == 1:
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
    await asyncio.sleep(60)
    symbolist = pd.read_sql(f'SELECT * FROM Bot',con=con)
    get_config()
    t2 = time.time()
    seconds = time.time()
    local_time = time.ctime(seconds)
    if insession['name'] and t1 == 0:
        t1 = time.time()
    if float(t2-t1) > 900 :
        insession['name'] = False
        t1 = 0
    if str(local_time[14:-9]) == '1':
        insession['day'] = False
        insession['hour'] = False
    if str(local_time[12:-9]) == '0:0' and not insession['day']:
        insession['day'] = True
        insession['hour'] = True   
        await asyncio.gather(dailyreport())     
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
            if str(local_time[14:-9]) == '0' and not insession['hour']:
                total = round(float(balance['total']['USDT']),2)
                notify.send(f'Total Balance : {total} USDT',sticker_id=10863, package_id=789)
                insession['hour'] = True
            exchange.precisionMode = accxt.DECIMAL_PLACES
            free = float(balance['free']['USDT'])
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


option_input = dmc.Group(
    direction="column",
    children=[
        dmc.Checkbox(label="Long", size="xs", checked=True,id="Long-input"),
        dmc.Checkbox(label="Short", size="xs", checked=True,id="Short-input"),
        dmc.Checkbox(label="TP1", size="xs", checked=True,id="TP1-input"),
        dmc.Checkbox(label="TP2", size="xs", checked=True,id="TP2-input"),
        dmc.Checkbox(label="Stop-Loss", size="xs", checked=True,id="Stop-input"),
        dmc.Checkbox(label="Tailing-Stop", size="xs", checked=True,id="Tailing-input"),
    ],
)
#HTML COMPONENT 
symbol_dropdown = dmc.Select(
    data=[{'label': symbol, 'value': symbol} for symbol in newsym],
    label='Symbol/Pair',
    id='symbol-dropdown',
    searchable=True,
    value="BTC/USDT",
    clearable=False,
    style={"width": 120},
)
timeframe_dropdown = dmc.Select(
    data=[{'label': timeframe, 'value': timeframe} for timeframe in TIMEFRAMES],
    label='Timeframe',
    id='timeframe-dropdown',
    searchable=True,
    value="6h",
    clearable=False,
    style={"width": 75},
)
num_bars_input = dmc.Select(
    data=['X1','X2','X3','X4','X5'],
    label='Zoom',
    id='num-bar-input',
    searchable=True,
    value="X4",
    clearable=False,
    style={"width": 75},
)

atr_input = dmc.NumberInput(
    label="ATR Period",
    id='atr-input',
    value=12,
    min=1,
    step=1,
    style={"width": 75},
)
atrm_input = dmc.NumberInput(
    label="ATR.M",
    id='atrm-input',
    precision=1,
    value=1.6,
    min=0.1,
    step=0.1,
    style={"width": 75},
)
EMA_input = dmc.NumberInput(
    label="EMA",
    id='EMA-input',
    value=30,
    min=1,
    step=1,
    style={"width": 75},
)
SUBHAG_input = dmc.NumberInput(
    label="SUBHAG",
    id='SUBHAG-input',
    value=30,
    min=1,
    step=1,
    style={"width": 75},
)
SMOOTH_input = dmc.NumberInput(
    label="SMOOTH",
    id='SMOOTH-input',
    value=30,
    min=1,
    step=1,
    style={"width": 75},
)
RSI_input = dmc.NumberInput(
    label="RSI",
    id='RSI-input',
    value=25,
    min=1,
    step=1,
    style={"width": 75},
)
AOL_input = dmc.NumberInput(
    label="Oscillator",
    id='Andean-Oscillator-input',
    value=30,
    min=1,
    max=500,
    step=1,
    style={"width": 75},
)
Pivot_input = dmc.NumberInput(
    label="Pivot",
    id='Pivot-lookback-input',
    value=60,
    min=1,
    max=500,
    step=1,
    style={"width": 75},
)
RRTP1_input = dmc.NumberInput(
    label="R:R TP1",
    id='RR-TP1-input',
    precision=1,
    value=3,
    min=1,
    step=0.1,
    style={"width": 75},
)
RRTP2_input = dmc.NumberInput(
    label="R:R TP2",
    id='RR-TP2-input',
    precision=1,
    value=4.5,
    min=1,
    step=0.1,
    style={"width": 75},
)
perTP1_input = dmc.NumberInput(
    label="% TP1",
    id='per-TP1-input',
    value=50,
    min=1,
    max=100,
    step=1,
    style={"width": 75},
)
perTP2_input = dmc.NumberInput(
    label="% TP2",
    id='per-TP2-input',
    value=50,
    min=0,
    max=100,
    step=1,
    style={"width": 75},
)
RISK_input = dmc.TextInput(label="RISK($,%)", style={"width": 75},id='Risk-input', value='$3', type='text')
Margin_input = dmc.TextInput(label="MaxMargin", style={"width": 75},id='maxmargin-input', value='%5', type='text')

Apply_input = dmc.Button("Apply Setting", variant="filled",id='Apply-strategy', color='yellow', n_clicks=0, size="sm")
Runbot_input = dmc.Button("Start   Bot", variant="filled",id='run-input', color='red', n_clicks=0, size="sm")

Leverage_input = dmc.NumberInput(
    label="Leverage",
    id='leverage-input',
    value=50,
    min=1,
    max=125,
    step=1,
    style={"width": 75},
)
API_KEY_input = dmc.TextInput(label="API KEY", style={"width": 300},id='api-key-input', value='Binance API Key', type='text')
API_SECRET_input = dmc.TextInput(label="API SECRET", style={"width": 300},id='api-secret-input', value='Binance API Secret Key', type='password')
NOTIFY_input = dmc.TextInput(label="LINE : Notify", style={"width": 200},id='api-notify-input', value='Line Notify Key', type='text')

Sumkey_input = dmc.Button("Apply Setting", variant="light",id='set-api-key', color='yellow', n_clicks=0)

Freebalance_input = dmc.TextInput(label="Free Balance $", style={"width": 200},id='freebalance-input', value=f'Free Balance : วงเงินสำหรับบอท(Margin รวมทั้งหมด) ', type='text')
minBalance_input = dmc.TextInput(label="Min Balance $", style={"width": 200},id='minBalance-input', value=f'Min Balance : ถ้าเงินเหลือต่ำกว่านี้บอทจะหยุดเข้า Position ', type='text')

passwd_input = dmc.PasswordInput(placeholder="Password",style={"width": 300 },id='passwd-input',error=False,required= True)
passwd2_input = dmc.PasswordInput(placeholder="Confirm Password",style={"width": 300 },id='repasswd2-input',error=False,required= True)
passwdKey_input = dmc.PasswordInput(placeholder="Password",style={"width": 300 },id='repasswdKey-input',error=False,required= True)

newUsername = dmc.TextInput(label="New Username", style={"width": 300},id='newUsername-input', value='Change new Username', type='text')

EMAFAST_input = dmc.NumberInput(
    label="EMA Fast",
    id='emafast-input',
    value=12,
    min=1,
    max=500,
    step=1,
    style={"width": 75},
)
EMASLOW_input = dmc.NumberInput(
    label="EMA Slow",
    id='emaslow-input',
    value=26,
    min=1,
    max=500,
    step=1,
    style={"width": 75},
)
resetpass_input = html.Div([dbc.Button('Reset Password',id='resetpass-input', color='danger', name='RunBot', size="md", n_clicks=0)])
logoutBut = dcc.Link([dmc.Button("Log Out", variant="light",id='logoutBut', color='red', n_clicks=0)],refresh=True , href='/',id='logoutLink')

edit_table = dcc.ConfirmDialogProvider([dmc.Button("Edit Data", variant="light", color='red', n_clicks=0, size="md")],id='edit-table',message='ชัวร์แล้วนาาา?',submit_n_clicks=0)

refresh_table = dmc.Button("Refresh", variant="light",id='update-table', color='green', n_clicks=0, size="md")

ready_input = dmc.Switch(
    size="sm",
    radius="sm",
    label="พร้อมแล้ว!",
    checked=False,
    id="ready-input")
edit_input = dmc.Switch(
    size="sm",
    radius="sm",
    label="ฉันได้ตรวจทานการตั้งค่าใหม่เรียบร้อยแล้ว",
    checked=False,
    id="edit-input")
readyAPI_input = dmc.Switch(
    size="sm",
    radius="sm",
    label="ฉันได้ตรวจทานความถูกต้องเรียบร้อยแล้ว และยอมรับว่า Vaz จะไม่รับผิดชอบเงินของคุณ",
    checked=False,
    id="readyAPI-input")

refresher_i = dcc.Interval(id='update', interval=10000)


login_page = dmc.Center([
    dmc.Stack(
    [
        dmc.TextInput(id="user", placeholder="Enter Username", style={"width": 250}),
        dmc.PasswordInput(placeholder="Your password",style={"width": 250 },id='passw',error=False,required= True),
        dmc.Center([ dcc.Link([ dbc.Button('Log in',id='verify', color='danger', name='RunBot', size="lg", n_clicks=0, style={"width": 250})],href='/index',refresh=True)]),
    ],style={"height": 500 , 'color':'white'}, align="stretch", justify="center")
    ])


index_page = dmc.MantineProvider([dmc.Header(
    height=70,
    fixed=False,
    children=[
        dmc.Container(
            fluid= True,
            children=dmc.Group(
                position="apart",
                align="flex-start",
                children=[
                    dmc.Center(
                        dcc.Link(
                            [
                                html.H2('VXMA BOT')
                            ],
                            href="/index", refresh=True,
                            style={"paddingTop": 5, "textDecoration": "none"},
                        ),
                    ),
                    dmc.Group(
                        position="right",
                        align="flex-end",
                        children=[
                            dmc.Center(
                                [dcc.Interval(id='session', interval=900000),html.Div(id='loading'),logoutBut]
                            ),
                        ],
                    ),
                ],
            ),
        )
    ],
),dmc.Tabs(active= 0, color='green',id='tabs-one',grow=False,position="right",orientation="horizontal", children=[
        dmc.Tab(label='Summary'),
        dmc.Tab(label='VXMA bot'),
        dmc.Tab(label='EMA bot'),
        dmc.Tab(label='Running Bot'),
        dmc.Tab(label='Setting'),
    ]),dmc.Center(id='page-content-tabs')],theme={"colorScheme": "dark"},id='theme',styles={"height": "100%", "width": "98%"}
    )

Summary_page = dmc.Container([refresher_i,
                dmc.Grid([
                    dmc.Col([
                        dmc.Text('Comming.. soon...', size="xl"),
                        dmc.Text(' by Vaz.', size="sm")
                    ])
                ],  justify="space-between",
                    align="flex-start",
                    gutter='md',
                    grow=True)
                ,html.Hr(),
                dbc.Row([
                    dmc.Grid([
                    dmc.Col([
                        
                        ])
                ],  justify="space-between",
                    align="flex-start",
                    gutter='md',
                    grow=True)       
                ])
                ,html.Hr(),
                dbc.Row([
                    dmc.Paper(
                        children=[dmc.Text('by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm', size="xs")],
                        shadow="xs",
                    )
                ])
                
            ])


vxma_page = dmc.Container([refresher_i,
                dmc.Grid([
                    dmc.Col([
                        option_input,
                    ],span=1),
                    dmc.Col([
                        Margin_input,
                        RRTP1_input,
                        RRTP2_input,
                    ],span=1),
                    dmc.Col([
                        RISK_input,
                        perTP1_input,
                        perTP2_input
                    ],span=1),
                    dmc.Col([
                        Leverage_input,
                        atr_input,
                        atrm_input,
                    ],span=1),
                    dmc.Col([
                        Pivot_input,
                        RSI_input,
                        EMA_input,
                    ],span=1),
                    dmc.Col([
                        AOL_input,
                        SUBHAG_input,
                        SMOOTH_input
                    ],span=1),
                    dmc.Col([
                        dmc.Stack(
                            [
                                symbol_dropdown,
                                Apply_input,
                                ready_input,
                                Runbot_input,
                            ],
                            align="flex-start",
                            spacing="xs",
                        ),
                    ],span=1),
                ],  justify="space-between",
                    align="flex-start",
                    gutter='md',
                    grow=True)
                ,html.Hr(),
                dbc.Row([
                    dcc.Graph(id='clientside-graph'),
                    dcc.Store(id='clientside-store-figure'),             
                ])
                ,html.Hr(),
                dbc.Row([
                dmc.Grid([
                    dmc.Col([
                        html.H5('ตรวจดูตั้งค่าทุกครั้ง!!', style={'color': 'red'})
                    ],span=1), 
                    dmc.Col([
                        html.Div(id='alert-suc'),
                    ],span=1),     
                    dmc.Col([
                        dmc.Group([timeframe_dropdown, num_bars_input]),
                    ],span=1, offset=1),     
                ],  justify="space-between",
                    align="flex-end",
                    gutter='md',
                    grow=True)])
                ,html.Hr(),
                dbc.Row([
                    dmc.Paper(
                        children=[dmc.Text('by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm', size="xs")],
                        shadow="xs",
                    )
                ])
                
            ])


EMA_page = dmc.Container([refresher_i,
                dmc.Grid([
                    dmc.Col([
                        option_input,
                    ],span=1),
                    dmc.Col([
                        Margin_input,
                        RRTP1_input,
                        RRTP2_input,
                    ],span=1),
                    dmc.Col([
                        RISK_input,
                        perTP1_input,
                        perTP2_input
                    ],span=1),
                    dmc.Col([
                        Leverage_input,
                        EMAFAST_input,
                        EMASLOW_input,
                    ],span=1),
                    dmc.Col([
                        dmc.Stack(
                            [
                                symbol_dropdown,
                                Apply_input,
                                ready_input,
                                Runbot_input,
                            ],
                            align="flex-start",
                            spacing="xs",
                        ),
                    ],span=1),
                ],  justify="space-between",
                    align="flex-start",
                    gutter='md',
                    grow=True)
                ,html.Hr(),
                dbc.Row([
                    dcc.Graph(id='clientside-graph-ema'),
                    dcc.Store(id='clientside-store-figure-ema'),           
                ])
                ,html.Hr(),
                dbc.Row([
                dmc.Grid([
                    dmc.Col([
                        html.H5('ตรวจดูตั้งค่าทุกครั้ง!!', style={'color': 'red'})
                    ],span=1), 
                    dmc.Col([
                        html.Div(id='alert-ema'),
                    ],span=1),     
                    dmc.Col([
                        dmc.Group([timeframe_dropdown, num_bars_input]),
                    ],span=1, offset=1),     
                ],  justify="space-between",
                    align="flex-end",
                    gutter='md',
                    grow=True)])
                ,html.Hr(),
                dbc.Row([
                    dmc.Paper(
                        children=[dmc.Text('by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm', size="xs")],
                        shadow="xs",
                    )
                ])
                
            ])

RunningBot_page = dmc.Container([refresher_i,
                dmc.Grid([
                    dmc.Col([
                        refresh_table,
                    ], span=1),
                    dmc.Col([
                        dmc.Center(id='alert-fai'),
                    ], span=1),
                    dmc.Col([
                        edit_input,
                    ], span=1),
                    dmc.Col([
                        edit_table,
                    ], span=1)
                ],  justify="space-between",
                    align="flex-start",
                    gutter='md',
                    grow=True)
                ,html.Hr(),
                dbc.Row([
                    dmc.Center(id='datatable')        
                ])
                ,html.Hr(),
                dbc.Row([
                    dmc.Paper(
                        children=[dmc.Text('by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm', size="xs")],
                        shadow="xs",
                    )
                ])
                
            ])


Setting_page = dmc.Container([refresher_i,
                dmc.Grid([
                    dmc.Col([
                        dmc.Group([Freebalance_input, minBalance_input,NOTIFY_input]),
                        dmc.Group([API_KEY_input, API_SECRET_input]),
                        dmc.Group([passwdKey_input, readyAPI_input]),
                        dmc.Center(id='alert-su'),
                        Sumkey_input
                    ])
                ],  justify="space-between",
                    align="flex-start",
                    gutter='md',
                    grow=True)
                ,html.Hr(),
                dbc.Row([
                    dmc.Grid([
                    dmc.Col([
                        dmc.Group([newUsername, html.H6('เข้าใช้งานครั้งแรกให้เปลี่ยนรหัสผ่านทันที!!!', style={'color': 'red'})]),
                        dmc.Group([passwd_input, html.Td([html.H6('โปรดใช้งานบอทอย่างระมัดระวัง : Use as your own RISK')])]),
                        dmc.Group([passwd2_input]),
                        dmc.Center(id='alert-fai'),
                        resetpass_input
                    ])
                ],  justify="space-between",
                    align="flex-start",
                    gutter='md',
                    grow=True)       
                ])
                ,html.Hr(),
                dbc.Row([
                    dmc.Paper(
                        children=[dmc.Text('by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm', size="xs")],
                        shadow="xs",
                    )
                ])
                
            ])




# creates the Dash App
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], title='VXMA Bot', update_title=None, background_callback_manager=background_callback_manager) #,suppress_callback_exceptions=True
register_page("VXMA", path='/index', layout=index_page)
register_page("Login", path='/login', layout=login_page)
app.layout = dmc.MantineProvider(
    children=[
            dcc.Location(id='url', refresh=True),
            dmc.Container(id='page-content-login'),
            ],theme={"colorScheme": "dark"},id='theme',styles={"height": "100%", "width": "98%"}
    )

# #logout button
@app.callback(
    Output('loading', 'children'),
    Input('logoutBut', 'n_clicks'))
def logout(click):
    if click is not None and insession['name']:
        insession['name']=False
        return 'loged In'
    elif click is not None:
        insession['name']=False
        return 'loged Out'
    else:
        return ''

#login page, dmc.Space(h=70)
@app.callback(
    Output('passw', 'error'),
    Output('passw', 'value'),
    Input('verify', 'n_clicks'),
    State('user', 'value'),
    State('passw', 'value'))
def update_output(n_clicks, uname, passw):
    config = pd.read_sql('SELECT * FROM user',con=con)
    li = config['id'][0]
    if uname =='' or uname == None or passw =='' or passw == None:
        return 'Invalid Username' , ''
    elif uname != li:
        return 'Incorrect Username' , ''
    elif perf(uname, passw):
        insession['name'] = True
        return 'Loged-In' , ''
    elif insession['name']:
        return 'Already Loged in' , ''
    else:
        return 'Incorrect Password' , ''

# #url condition
@app.callback(
    Output('page-content-login', 'children'),
    Input('url', 'pathname'))
def pathname_page(pathname):
    if pathname == '/index' and insession['name']:
        return index_page
    elif pathname == '/' and insession['name']:
        return index_page
    elif pathname == '/' and not insession['name']:
        return login_page
    elif not insession['name']:
        return login_page
    else:
        return 'Code : 404'

@app.callback(
    Output('page-content-tabs','children'),
    Input('tabs-one','active'))
def tabs(tabs):
    if tabs == 1:
        return vxma_page
    elif tabs == 2:
        return EMA_page
    elif tabs == 3:
        return RunningBot_page
    elif tabs == 4:
        return Setting_page
    else: return Summary_page

#VXMA strategy
@app.callback(
    Output('clientside-store-figure', 'data'),
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
    prevent_initial_call=True)
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
    df = indi.indicator(df, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip, aol_ip, pivot)
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
    return fig

# Clientside callback
app.clientside_callback(
    """
    function(figure_data, title_text) {
        if(figure_data === undefined) {
            return {'data': [], 'layout': {}};
        }
        const fig = Object.assign({}, figure_data, {
                'layout': {
                    ...figure_data.layout,
                    'title': {
                        ...figure_data.layout.title, text: title_text
                    }
                }
        });
        return fig;
    }
    """,
    Output('clientside-graph', 'figure'),
    Input('clientside-store-figure', 'data'),
)

#EMA strategy
@app.callback(
    Output('clientside-store-figure-ema', 'data'),
    Input('update', 'n_intervals'),
    Input('Apply-strategy', 'n_clicks'),
    State('symbol-dropdown', 'value'),
    State('timeframe-dropdown', 'value'),
    State('num-bar-input', 'value'),
    State('emafast-input', 'value'),
    State('emaslow-input', 'value'),
    prevent_initial_call=True)
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
    return fig
# Clientside callback
app.clientside_callback(
    """
    function(figure_data, title_text) {
        if(figure_data === undefined) {
            return {'data': [], 'layout': {}};
        }
        const fig = Object.assign({}, figure_data, {
                'layout': {
                    ...figure_data.layout,
                    'title': {
                        ...figure_data.layout.title, text: title_text
                    }
                }
        });
        return fig;
    }
    """,
    Output('clientside-graph-ema', 'figure'),
    Input('clientside-store-figure-ema', 'data'),
)


# #VXMA excute bot
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
    State('leverage-input', 'value'),
    State('Pivot-lookback-input', 'value'),
    State('RR-TP1-input', 'value'),
    State('RR-TP2-input', 'value'),
    State('per-TP1-input', 'value'),
    State('per-TP2-input', 'value'),
    State('Risk-input', 'value'),
    State('maxmargin-input', 'value'),
    State('ready-input', 'checked'),
    State('Long-input' , 'checked'),
    State('Short-input' , 'checked'),
    State('TP1-input' , 'checked'),
    State('TP2-input' , 'checked'),
    State('Stop-input' , 'checked'),
    State('Tailing-input' , 'checked'),
    background=True)
def excuteBot(click, symbol, timeframe, atr_input, atrM_input, ema_ip, subhag, smooth, rsi_ip, aol_ip, leverage, Pivot, RR1, RR2, TP1, TP2, Risk,maxMargin, ready, ul, us, tp, tp2, sl, tsl):
    if click is not None:
        data = pd.DataFrame(columns=BOTCOL)
        if ready:
            try:
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
        return  [dbc.Alert("Wellcome.", dismissable=True, duration=5000, is_open=True, color='info')]
#api setting
@app.callback(
    Output('alert-su', 'children'),
    Input('set-api-key', 'n_clicks'),
    State('freebalance-input', 'value'),
    State('minBalance-input', 'value'),
    State('api-key-input', 'value'),
    State('api-secret-input', 'value'),
    State('api-notify-input', 'value'),
    State('repasswdKey-input', 'value'),
    State('readyAPI-input', 'checked'),
    prevent_initial_call=True,
    background=True)
def setting(click, freeB, minB, api_key, apiZ, notifykey, pwd, ready):
    if click is not None:
        data = pd.DataFrame(columns=['freeB','minB','apikey','apisec','notify'])
        config = pd.read_sql('SELECT * FROM user',con=con)
        id = config['id'][0]
        valit = True if perf(id, pwd) else False
        if ready and valit:
            try:
                compo = [freeB, minB, api_key, apiZ, notifykey]
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
# #reset user pass
@app.callback(
    Output('alert-fai', 'children'),
    Input('resetpass-input', 'n_clicks'),
    State('passwd-input', 'value'),
    State('repasswd-input', 'value'),
    State('newUsername-input', 'value'),
    prevent_initial_call=True,
    background=True)
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
# #read data running bot
@app.callback(
Output('datatable', 'children'),
Input('update-table', 'n_clicks'),
background=True,
prevent_initial_call=True)
def runningBot(click):
    if click is not None:
        get_config()
        return dash_table.DataTable(data=symbolist.to_dict('records'),columns=[{"name": i, "id": i} for i in symbolist],page_current=0,page_size=99,page_action='custom',editable=True, id='datatable', style_table={'color':'black'})
    else:
        return PreventUpdate
# #write data edit running bot
@app.callback(
Output('alert-ta', 'children'),
Input('edit-table', 'submit_n_clicks'),
State('datatable', 'data'),
State('edit-input', 'checked'),
background=True,
prevent_initial_call=True)
def edit_menu(click, rows, ready):
    if click is not None and ready is not None:
        if ready:
            try:
                df = pd.DataFrame(rows, columns=BOTCOL)
                df = df.set_index('id')
                df.to_sql('Bot', con=con, if_exists='replace', index_label='id')
                return [dbc.Alert("Success.", dismissable=True, duration=5000, is_open=True)]
            except Exception as e:
                print(e)
                return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]
        else:
            return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]
    else:
        return [dbc.Alert("Ops! Something went wrong, Please retry.", dismissable=True, duration=5000, is_open=True, color='danger')]


if __name__ == "__main__":
    # th = Thread(target=run)
    # th.start()
    app.run(debug=True)
    # th.join()
    
        
