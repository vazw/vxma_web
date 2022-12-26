# VXMA Trading
web app bot-trading version beta

### default 
User = 'vxma'
password = 'vxmaBot'


![image](https://user-images.githubusercontent.com/8637706/189531967-c03dec80-60aa-4b5a-9c95-7b26581710aa.png)

## Directions 
**init** -concept <br/>
├─ it must easy to use(user friendly) <br/>
├─ it must customizable <br/>
├─ it must safe an secure <br/>
├─ it must profitable <br/>
├─ it must Free <br/>

**init** -what we have now? <br/>
├─ a trend following custom strategy vxma <br/>
├─ web-ui setting(it work but noob) :D <br/>
├─ notification to Line  <br/>
├─ position sizing <br/>
├─ tailing-stop <br/>
├─ daily trend analysis <br/>
├─ any-timeframe trading <br/>
├─ callbackRate calculation for tailing-stop <br/>
├─ global limit position size <br/>
├─ minimum balance to execute open position <br/>

## Changelog
> let's begin our journey to financial freedom!

├─ 0.1.0 start! <br />
├─ 0.1.1  <br />
│   ├── Update terminal UI
│   ├── Woring on Docker
│   ├── Better error handler
│   ├── Blazing fast 

[![Tradingview_VXMA](https://user-images.githubusercontent.com/8637706/196947394-d71c8ef6-9ab7-451a-b6bc-55a642c9e845.png)](https://www.tradingview.com/script/m54nptt2-VXMA-Bot)

### Need to help?
1. read TODO files for our current workflow 
2. any improvement or pointing some issues are welcome! 😁
3. I need your help 🙏

### Structure
```
vxma_web/
├── vxma_d
│   ├── AppData
│   │   ├── Appdata.py
│   │   ├── Bot.py
│   │   ├── __init__.py
│   │   ├── oldutil
│   │   └── ResetDatabase.py
│   ├── Backtesting
│   │   ├── Candle_ohlc.py
│   │   └── __init__.py
│   ├── MarketEX
│   │   ├── CCXT_Binance.py
│   │   └── __init__.py
│   ├── Strategy
│   │   ├── Benchmarking.py
│   │   ├── ematalib.py
│   │   ├── __init__.py
│   │   ├── vxma_pandas_ta.py
│   │   ├── vxma_talib.py
│   │   └── vxmatalib.py
│   ├── web
│   │   ├── __init__.py
│   │   └── web.py
│   └── __init__.py
├── app.py
├── bot_config.csv
├── candle.png
├── Dockerfile
├── LICENSE
├── log.log
├── README.md
├── requirements_docker.txt
├── requirements_pandas.txt
├── requirements_talib.txt
├── requirements.txt
├── run.sh
├── tester.py
├── TODO
├── vxma.db
└── web_app.py
```
