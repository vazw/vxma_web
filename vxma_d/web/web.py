# The BEERWARE License (BEERWARE)
#
# Copyright (c) 2022 Author. All rights reserved.
#
# Licensed under the "THE BEER-WARE LICENSE" (Revision 42):
# vazw wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer or coffee in return
import logging
import os
import sqlite3
import time
import warnings
import math
from uuid import uuid4
from datetime import datetime, date

import ccxt
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import (
    CeleryManager,
    Dash,
    DiskcacheManager,
    dash_table,
    dcc,
    html,
    register_page,
)
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from vxma_d.AppData.Appdata import (
    BOTCOL,
    bot_setting,
    cooking,
    notify_send,
    perf,
)

try:
    from vxma_d.Strategy.vxma_talib import vxma as indi
except Exception as e:
    print(e)
    from vxma_d.Strategy.vxma_pandas_ta import vxma as indi


launch_uid = uuid4()
pd.set_option("display.max_rows", None)
warnings.filterwarnings("ignore")

if "REDIS_URL" in os.environ:
    # Use Redis & Celery if REDIS_URL set as an env variable
    from celery import Celery

    celery_app = Celery(
        __name__,
        broker=os.environ["REDIS_URL"],
        backend=os.environ["REDIS_URL"],
    )
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

# LINE_TOKEN = str(os.environ["Line_Notify_Token"])
# notify = LineNotify(LINE_TOKEN)


logging.basicConfig(
    filename="log.log", format="%(asctime)s - %(message)s", level=logging.INFO
)


websession = dict(name=False, day=False, hour=False)
# STAT setting
barsC = 1502
msg = ""
# timframe dicts and collum
ZOOM_DICT = {"X1": 500, "X2": 250, "X3": 180, "X4": 125, "X5": 50}
TIMEFRAMES = [
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1M",
]
TIMEFRAMES_DICT = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
    "3d": "3d",
    "1w": "1w",
    "1M": "1M",
}


nomEX = ccxt.binance(
    {
        "options": {"defaultType": "future"},
        "enableRateLimit": True,
        "adjustForTimeDifference": True,
    }
)


def makepairlist():
    symbols = pd.DataFrame()
    try:
        market = nomEX.fetch_tickers(params={"type": "future"})
    except Exception as e:
        print(e)
        time.sleep(2)
        market = nomEX.fetch_tickers(params={"type": "future"})
    for x, y in market.items():
        if y["symbol"][len(y["symbol"]) - 4 : len(y["symbol"])] == "USDT":
            symbols = symbols.append(y, ignore_index=True)
    symbols = symbols.set_index("symbol")
    symbols["datetime"] = pd.to_datetime(
        symbols["timestamp"], unit="ms", utc=True
    ).map(lambda x: x.tz_convert("Asia/Bangkok"))
    symbols = symbols.sort_values(by=["quoteVolume"], ascending=False)
    symbols.drop(["timestamp", "high", "low", "average"], axis=1, inplace=True)
    symbols.drop(
        ["bid", "bidVolume", "ask", "askVolume"], axis=1, inplace=True
    )
    symbols.drop(["vwap", "open", "baseVolume", "info"], axis=1, inplace=True)
    symbols.drop(["close", "previousClose", "datetime"], axis=1, inplace=True)
    newsym = []
    for symbol in symbols.index:
        newsym.append(symbol)
    return newsym


# HTML COMPONENT
option_input = dmc.Group(
    children=[
        dmc.Checkbox(label="Long", size="xs", checked=True, id="Long-input"),
        dmc.Checkbox(label="Short", size="xs", checked=True, id="Short-input"),
        dmc.Checkbox(label="TP1", size="xs", checked=True, id="TP1-input"),
        dmc.Checkbox(label="TP2", size="xs", checked=True, id="TP2-input"),
        dmc.Checkbox(
            label="Stop-Loss", size="xs", checked=True, id="Stop-input"
        ),
        dmc.Checkbox(
            label="Tailing-Stop", size="xs", checked=True, id="Tailing-input"
        ),
    ],
)
pairlist = makepairlist()
symbol_dropdown = dmc.Select(
    data=[{"label": symbol, "value": symbol} for symbol in pairlist],
    label="Symbol/Pair",
    id="symbol-dropdown",
    searchable=True,
    value="BTC/USDT",
    clearable=False,
    style={"width": 120},
)
timeframe_dropdown = dmc.Select(
    data=[
        {"label": timeframe, "value": timeframe} for timeframe in TIMEFRAMES
    ],
    label="Timeframe",
    id="timeframe-dropdown",
    searchable=True,
    value="6h",
    clearable=False,
    style={"width": 75},
)
num_bars_input = dmc.Select(
    data=["X1", "X2", "X3", "X4", "X5"],
    label="Zoom",
    id="num-bar-input",
    searchable=True,
    value="X4",
    clearable=False,
    style={"width": 75},
)

atr_input = dmc.NumberInput(
    label="ATR Period",
    id="atr-input",
    value=12,
    min=1,
    step=1,
    style={"width": 75},
)
atrm_input = dmc.NumberInput(
    label="ATR.M",
    id="atrm-input",
    precision=1,
    value=1.6,
    min=0.1,
    step=0.1,
    style={"width": 75},
)
EMA_input = dmc.NumberInput(
    label="EMA",
    id="EMA-input",
    value=30,
    min=1,
    step=1,
    style={"width": 75},
)
SUBHAG_input = dmc.NumberInput(
    label="SUBHAG",
    id="SUBHAG-input",
    value=30,
    min=1,
    step=1,
    style={"width": 75},
)
SMOOTH_input = dmc.NumberInput(
    label="SMOOTH",
    id="SMOOTH-input",
    value=30,
    min=1,
    step=1,
    style={"width": 75},
)
RSI_input = dmc.NumberInput(
    label="RSI",
    id="RSI-input",
    value=25,
    min=1,
    step=1,
    style={"width": 75},
)
AOL_input = dmc.NumberInput(
    label="Oscillator",
    id="Andean-Oscillator-input",
    value=30,
    min=1,
    max=500,
    step=1,
    style={"width": 75},
)
Pivot_input = dmc.NumberInput(
    label="Pivot",
    id="Pivot-lookback-input",
    value=60,
    min=1,
    max=500,
    step=1,
    style={"width": 75},
)
RRTP1_input = dmc.NumberInput(
    label="R:R TP1",
    id="RR-TP1-input",
    precision=1,
    value=3,
    min=1,
    step=0.1,
    style={"width": 75},
)
RRTP2_input = dmc.NumberInput(
    label="R:R TP2",
    id="RR-TP2-input",
    precision=1,
    value=4.5,
    min=1,
    step=0.1,
    style={"width": 75},
)
perTP1_input = dmc.NumberInput(
    label="% TP1",
    id="per-TP1-input",
    value=50,
    min=1,
    max=100,
    step=1,
    style={"width": 75},
)
perTP2_input = dmc.NumberInput(
    label="% TP2",
    id="per-TP2-input",
    value=50,
    min=0,
    max=100,
    step=1,
    style={"width": 75},
)
RISK_input = dmc.TextInput(
    label="RISK($,%)",
    style={"width": 75},
    id="Risk-input",
    value="$1",
    type="text",
)
Margin_input = dmc.TextInput(
    label="MaxMargin",
    style={"width": 75},
    id="maxmargin-input",
    value="%5",
    type="text",
)

Apply_input = dmc.Button(
    "Apply Setting",
    variant="filled",
    id="Apply-strategy",
    color="yellow",
    n_clicks=0,
    size="sm",
)
Runbot_input = dmc.Button(
    "Start   Bot",
    variant="filled",
    id="run-input",
    color="red",
    n_clicks=0,
    size="sm",
)

Leverage_input = dmc.NumberInput(
    label="Leverage",
    id="leverage-input",
    value=50,
    min=1,
    max=125,
    step=1,
    style={"width": 75},
)
API_KEY_input = dmc.TextInput(
    label="API KEY",
    style={"width": 300},
    id="api-key-input",
    value="Binance API Key",
    type="text",
)
API_SECRET_input = dmc.TextInput(
    label="API SECRET",
    style={"width": 300},
    id="api-secret-input",
    value="Binance API Secret Key",
    type="password",
)
NOTIFY_input = dmc.TextInput(
    label="LINE : Notify",
    style={"width": 200},
    id="api-notify-input",
    value="Line Notify Key",
    type="text",
)

Sumkey_input = dmc.Button(
    "Apply Setting",
    variant="light",
    id="set-api-key",
    color="yellow",
    n_clicks=0,
)

Freebalance_input = dmc.TextInput(
    label="Free Balance $",
    style={"width": 200},
    id="freebalance-input",
    value="Free Balance : วงเงินสำหรับบอท(Margin รวมทั้งหมด) ",
    type="text",
)
minBalance_input = dmc.TextInput(
    label="Min Balance $",
    style={"width": 200},
    id="minBalance-input",
    value="Min Balance : ถ้าเงินเหลือต่ำกว่านี้บอทจะหยุดเข้า Position ",
    type="text",
)

passwd_input = dmc.PasswordInput(
    placeholder="Password",
    style={"width": 300},
    id="passwd-input",
    error=False,
    required=True,
)
passwd2_input = dmc.PasswordInput(
    placeholder="Confirm Password",
    style={"width": 300},
    id="repasswd2-input",
    error=False,
    required=True,
)
passwdKey_input = dmc.PasswordInput(
    placeholder="Password",
    style={"width": 300},
    id="repasswdKey-input",
    error=False,
    required=True,
)

newUsername = dmc.TextInput(
    label="New Username",
    style={"width": 300},
    id="newUsername-input",
    value="Change new Username",
    type="text",
)

EMAFAST_input = dmc.NumberInput(
    label="EMA Fast",
    id="emafast-input",
    value=12,
    min=1,
    max=500,
    step=1,
    style={"width": 75},
)
EMASLOW_input = dmc.NumberInput(
    label="EMA Slow",
    id="emaslow-input",
    value=26,
    min=1,
    max=500,
    step=1,
    style={"width": 75},
)
resetpass_input = html.Div(
    [
        dbc.Button(
            "Reset Password",
            id="resetpass-input",
            color="danger",
            name="RunBot",
            size="md",
            n_clicks=0,
        )
    ]
)
logoutBut = dcc.Link(
    [
        dmc.Button(
            "Log Out", variant="light", id="logoutBut", color="red", n_clicks=0
        )
    ],
    refresh=True,
    href="/",
    id="logoutLink",
)

edit_table = dcc.ConfirmDialogProvider(
    [
        dmc.Button(
            "Edit Data",
            variant="light",
            color="red",
            n_clicks=0,
            size="md",
        )
    ],
    id="edit-table",
    message="ชัวร์แล้วนาาา?",
    submit_n_clicks=0,
)

refresh_table = dmc.Button(
    "Refresh",
    variant="light",
    id="update-table",
    color="green",
    n_clicks=0,
    size="md",
)

ready_input = dmc.Switch(
    size="sm", radius="sm", label="พร้อมแล้ว!", checked=False, id="ready-input"
)
edit_input = dmc.Switch(
    size="sm",
    radius="sm",
    label="ฉันได้ตรวจทานการตั้งค่าใหม่เรียบร้อยแล้ว",
    checked=False,
    id="edit-input",
)
readyAPI_input = dmc.Switch(
    size="sm",
    radius="sm",
    label="ฉันได้ตรวจทานความถูกต้องเรียบร้อยแล้ว"
    + "และยอมรับว่า Vaz จะไม่รับผิดชอบเงินของคุณ",
    checked=False,
    id="readyAPI-input",
)

refresher_i = dcc.Interval(id="update", interval=5000)


login_page = dmc.Center(
    [
        dmc.Stack(
            [
                dmc.TextInput(
                    id="user",
                    placeholder="Enter Username",
                    style={"width": 250},
                ),
                dmc.PasswordInput(
                    placeholder="Your password",
                    style={"width": 250},
                    id="passw",
                    error=False,
                    required=True,
                ),
                dmc.Center(
                    [
                        dcc.Link(
                            [
                                dbc.Button(
                                    "Log in",
                                    id="verify",
                                    color="danger",
                                    name="RunBot",
                                    size="lg",
                                    n_clicks=0,
                                    style={"width": 250},
                                )
                            ],
                            href="/index",
                            refresh=True,
                        )
                    ]
                ),
            ],
            style={"height": 500, "color": "white"},
            align="stretch",
            justify="center",
        )
    ]
)


Summary_page = dmc.Container(
    [
        dmc.Grid(
            [
                dmc.Col(
                    [
                        html.H3("Realized Profit Loss JupyterDash"),
                        #     html.P("date_range:"),
                        #     dcc.DatePickerRange(
                        #         id='my-date-picker-range',
                        #         min_date_allowed=date(1990, 1, 1),
                        #         max_date_allowed=date(2100, 12, 31),
                        #         initial_visible_month=date(2021, 1, 1),
                        #         start_date=date(2021, 1, 1),
                        #         end_date=date(2021, 12, 31)
                        # ),
                        # dcc.Graph(id="graph")
                    ]
                )
            ],
            justify="space-between",
            align="flex-start",
            gutter="md",
            grow=True,
        ),
        html.Hr(),
        dbc.Row(
            [
                dmc.Grid(
                    [dmc.Col([])],
                    justify="space-between",
                    align="flex-start",
                    gutter="md",
                    grow=True,
                )
            ]
        ),
        html.Hr(),
        dbc.Row(
            [
                dmc.Paper(
                    children=[
                        dmc.Text(
                            "by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm",  # noqa:
                            size="xs",
                        )
                    ],
                    shadow="xs",
                )
            ]
        ),
    ]
)

vxma_page = dmc.Container(
    [
        dmc.Grid(
            [
                dmc.Col(
                    [
                        option_input,
                    ],
                    span=1,
                ),
                dmc.Col(
                    [
                        Margin_input,
                        RRTP1_input,
                        RRTP2_input,
                    ],
                    span=1,
                ),
                dmc.Col([RISK_input, perTP1_input, perTP2_input], span=1),
                dmc.Col(
                    [
                        Leverage_input,
                        atr_input,
                        atrm_input,
                    ],
                    span=1,
                ),
                dmc.Col(
                    [
                        Pivot_input,
                        RSI_input,
                        EMA_input,
                    ],
                    span=1,
                ),
                dmc.Col([AOL_input, SUBHAG_input, SMOOTH_input], span=1),
                dmc.Col(
                    [
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
                    ],
                    span=1,
                ),
            ],
            justify="space-between",
            align="flex-start",
            gutter="md",
            grow=True,
        ),
        html.Hr(),
        dbc.Row(
            [
                dcc.Graph(id="clientside-graph"),
                dcc.Store(id="clientside-store-figure"),
            ]
        ),
        html.Hr(),
        dbc.Row(
            [
                dmc.Grid(
                    [
                        dmc.Col(
                            [
                                html.H5(
                                    "ตรวจดูตั้งค่าทุกครั้ง!!",
                                    style={"color": "red"},
                                )
                            ],
                            span=1,
                        ),
                        dmc.Col(
                            [
                                html.Div(id="alert-suc"),
                            ],
                            span=1,
                        ),
                        dmc.Col(
                            [
                                dmc.Group(
                                    [timeframe_dropdown, num_bars_input]
                                ),
                            ],
                            span=1,
                            offset=1,
                        ),
                    ],
                    justify="space-between",
                    align="flex-end",
                    gutter="md",
                    grow=True,
                )
            ]
        ),
        html.Hr(),
        dbc.Row(
            [
                dmc.Paper(
                    children=[
                        dmc.Text(
                            "by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm",  # noqa:
                            size="xs",
                        )
                    ],
                    shadow="xs",
                )
            ]
        ),
    ]
)


# EMA_page = dmc.Container(
#     [
#         dmc.Grid(
#             [
#                 dmc.Col(
#                     [
#                         option_input,
#                     ],
#                     span=1,
#                 ),
#                 dmc.Col(
#                     [
#                         Margin_input,
#                         RRTP1_input,
#                         RRTP2_input,
#                     ],
#                     span=1,
#                 ),
#                 dmc.Col([RISK_input, perTP1_input, perTP2_input], span=1),
#                 dmc.Col(
#                     [
#                         Leverage_input,
#                         EMAFAST_input,
#                         EMASLOW_input,
#                     ],
#                     span=1,
#                 ),
#                 dmc.Col(
#                     [
#                         dmc.Stack(
#                             [
#                                 symbol_dropdown,
#                                 Apply_input,
#                                 ready_input,
#                                 Runbot_input,
#                             ],
#                             align="flex-start",
#                             spacing="xs",
#                         ),
#                     ],
#                     span=1,
#                 ),
#             ],
#             justify="space-between",
#             align="flex-start",
#             gutter="md",
#             grow=True,
#         ),
#         html.Hr(),
#         dbc.Row(
#             [
#                 dcc.Graph(id="clientside-graph-ema"),
#                 dcc.Store(id="clientside-store-figure-ema"),
#             ]
#         ),
#         html.Hr(),
#         dbc.Row(
#             [
#                 dmc.Grid(
#                     [
#                         dmc.Col(
#                             [
#                                 html.H5(
#                                     "ตรวจดูตั้งค่าทุกครั้ง!!",
#                                     style={"color": "red"},
#                                 )
#                             ],
#                             span=1,
#                         ),
#                         dmc.Col(
#                             [
#                                 html.Div(id="alert-ema"),
#                             ],
#                             span=1,
#                         ),
#                         dmc.Col(
#                             [
#                                 dmc.Group(
#                                     [timeframe_dropdown, num_bars_input]
#                                 ),
#                             ],
#                             span=1,
#                             offset=1,
#                         ),
#                     ],
#                     justify="space-between",
#                     align="flex-end",
#                     gutter="md",
#                     grow=True,
#                 )
#             ]
#         ),
#         html.Hr(),
#         dbc.Row(
#             [
#                 dmc.Paper(
#                     children=[
#                         dmc.Text(
#                             "by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm",  # noqa:
#                             size="xs",
#                         )
#                     ],
#                     shadow="xs",
#                 )
#             ]
#         ),
#     ]
# )


RunningBot_page = dmc.Container(
    [
        dmc.Grid(
            [
                dmc.Col(
                    [
                        refresh_table,
                    ],
                    span=1,
                ),
                dmc.Col(
                    [
                        dmc.Center(id="alert-bot"),
                    ],
                    span=1,
                ),
                dmc.Col(
                    [
                        edit_input,
                    ],
                    span=1,
                ),
                dmc.Col(
                    [
                        edit_table,
                    ],
                    span=1,
                ),
            ],
            justify="space-between",
            align="flex-start",
            gutter="md",
            grow=True,
        ),
        html.Hr(),
        dbc.Row([dmc.Center([dmc.Table(id="datatable")])]),
        html.Hr(),
        dbc.Row(
            [
                dmc.Paper(
                    children=[
                        dmc.Text(
                            "by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm",  # noqa:
                            size="xs",
                        )
                    ],
                    shadow="xs",
                )
            ]
        ),
    ]
)


Setting_page = dmc.Container(
    [
        dmc.Grid(
            [
                dmc.Col(
                    [
                        dmc.Group(
                            [Freebalance_input, minBalance_input, NOTIFY_input]
                        ),
                        dmc.Group([API_KEY_input, API_SECRET_input]),
                        dmc.Group([passwdKey_input, readyAPI_input]),
                        dmc.Center(id="alert-su"),
                        Sumkey_input,
                    ]
                )
            ],
            justify="space-between",
            align="flex-start",
            gutter="md",
            grow=True,
        ),
        html.Hr(),
        dbc.Row(
            [
                dmc.Grid(
                    [
                        dmc.Col(
                            [
                                dmc.Group(
                                    [
                                        newUsername,
                                        html.H6(
                                            "เข้าใช้งานครั้งแรกให้เปลี่ยนรหัสผ่านทันที!!!",  # noqa:
                                            style={"color": "red"},
                                        ),
                                    ]
                                ),
                                dmc.Group(
                                    [
                                        passwd_input,
                                        html.Td(
                                            [
                                                html.H6(
                                                    "โปรดใช้งานบอทอย่างระมัดระวัง : Use as your own RISK"  # noqa:
                                                )
                                            ]
                                        ),
                                    ]
                                ),
                                dmc.Group([passwd2_input]),
                                dmc.Center(id="alert-fai"),
                                resetpass_input,
                            ]
                        )
                    ],
                    justify="space-between",
                    align="flex-start",
                    gutter="md",
                    grow=True,
                )
            ]
        ),
        html.Hr(),
        dbc.Row(
            [
                dmc.Paper(
                    children=[
                        dmc.Text(
                            "by Vaz. Donate : XMR : 87tT3DZqi4mhGuJjEp3Yebi1Wa13Ne6J7RGi9QxU21FkcGGNtFHkfdyLjaPLRv8T2CMrz264iPYQ2dCsJs2MGJ27GnoJFbm",  # noqa:
                            size="xs",
                        )
                    ],
                    shadow="xs",
                )
            ]
        ),
    ]
)

index_page = dmc.MantineProvider(
    [
        dmc.Header(
            height=70,
            fixed=False,
            children=[
                dmc.Container(
                    fluid=True,
                    children=dmc.Group(
                        position="apart",
                        align="flex-start",
                        children=[
                            dmc.Center(
                                dcc.Link(
                                    [html.H2("VXMA BOT")],
                                    href="/index",
                                    refresh=True,
                                    style={
                                        "paddingTop": 5,
                                        "textDecoration": "none",
                                    },
                                ),
                            ),
                            dmc.Group(
                                position="right",
                                align="flex-end",
                                children=[
                                    dmc.Center(
                                        [
                                            refresher_i,
                                            dcc.Interval(
                                                id="session", interval=900000
                                            ),
                                            html.Div(id="loading"),
                                            logoutBut,
                                        ]
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            ],
        ),
        dmc.Tabs(
            value="sumarry",
            color="green",
            id="tabs-one",
            orientation="horizontal",
            children=[
                dmc.TabsList(
                    [
                        dmc.Tab("Summary", value="sumarry"),
                        dmc.Tab("VXMA bot", value="vxma"),
                        # dmc.Tab("EMA bot", value="ema"),
                        dmc.Tab("Running Bot", value="running"),
                        dmc.Tab("Setting", value="setting"),
                    ],
                    grow=False,
                    position="right",
                ),
                dmc.TabsPanel(Summary_page, value="sumarry"),
                dmc.TabsPanel(vxma_page, value="vxma"),
                # dmc.TabsPanel(EMA_page, value="ema"),
                dmc.TabsPanel(RunningBot_page, value="running"),
                dmc.TabsPanel(Setting_page, value="setting"),
            ],
        ),
    ],
    theme={"colorScheme": "dark"},
    id="theme",
    withGlobalStyles={"height": "100%", "width": "98%"},
)

# creates the Dash App
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="VXMA Bot",
    update_title=None,
    background_callback_manager=background_callback_manager,
)
# suppress_callback_exceptions=True
register_page("VXMA", path="/index", layout=index_page)
register_page("Login", path="/login", layout=login_page)
app.layout = dmc.MantineProvider(
    children=[
        dcc.Location(id="url", refresh=True),
        dmc.Container(id="page-content-login"),
    ],
    theme={"colorScheme": "dark"},
    id="theme",
    withGlobalStyles={"height": "100%", "width": "98%"},
)


# #logout button
@app.callback(Output("loading", "children"), Input("logoutBut", "n_clicks"))
def logout(click):
    if click is not None and websession["name"]:
        websession["name"] = False
        return "loged In"
    elif click is not None:
        websession["name"] = False
        return "loged Out"
    else:
        return ""


# login page, dmc.Space(h=70)
@app.callback(
    Output("passw", "error"),
    Input("verify", "n_clicks"),
    State("user", "value"),
    State("passw", "value"),
)
def update_output(n_clicks, uname, passw):
    with sqlite3.connect("vxma.db", check_same_thread=False) as con:
        config = pd.read_sql("SELECT * FROM user", con=con)
    li = config["id"][0]
    if uname == "" or uname is None or passw == "" or passw is None:
        return "Invalid Username"
    elif uname != li:
        return "Incorrect Username"
    elif perf(uname, passw):
        websession["name"] = True
        return "Loged-In"
    elif websession["name"]:
        return "Already Loged in"
    else:
        return "Incorrect Password"


# #url condition
@app.callback(
    Output("page-content-login", "children"), Input("url", "pathname")
)
def pathname_page(pathname):
    if pathname == "/index" and websession["name"]:
        return index_page
    elif pathname == "/" and websession["name"]:
        return index_page
    elif pathname == "/" and not websession["name"]:
        return login_page
    elif not websession["name"]:
        return login_page
    else:
        return "Code : 404"


# VXMA strategy
@app.callback(
    Output("clientside-store-figure", "data"),
    Input("update", "n_intervals"),
    Input("Apply-strategy", "n_clicks"),
    State("symbol-dropdown", "value"),
    State("timeframe-dropdown", "value"),
    State("num-bar-input", "value"),
    State("atr-input", "value"),
    State("atrm-input", "value"),
    State("EMA-input", "value"),
    State("SUBHAG-input", "value"),
    State("SMOOTH-input", "value"),
    State("RSI-input", "value"),
    State("Andean-Oscillator-input", "value"),
    State("Pivot-lookback-input", "value"),
    prevent_initial_call=True,
)
def update_VXMA_chart(
    interval,
    click,
    symbol,
    timeframe,
    zoom,
    atr_input,
    atrM_input,
    ema_ip,
    subhag,
    smooth,
    rsi_ip,
    aol_ip,
    pivot,
):
    timeframe = TIMEFRAMES_DICT[timeframe]
    num_bars = ZOOM_DICT[zoom]
    try:
        bars = nomEX.fetch_ohlcv(
            symbol, timeframe=timeframe, since=None, limit=barsC
        )
    except Exception as e:
        print(e)
        logging.info(e)
        time.sleep(2)
        bars = nomEX.fetch_ohlcv(
            symbol, timeframe=timeframe, since=None, limit=barsC
        )
    df = pd.DataFrame(
        bars[:-1],
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).map(
        lambda x: x.tz_convert("Asia/Bangkok")
    )
    df = df.set_index("timestamp")
    ta_table = {
        "atr_p": atr_input,
        "atr_m": atrM_input,
        "ema": ema_ip,
        "linear": subhag,
        "smooth": smooth,
        "rsi": rsi_ip,
        "aol": aol_ip,
        "pivot": pivot,
    }
    streaming = indi(df, ta_table)
    df = streaming.indicator()
    data = df.tail(num_bars)
    fig = go.Figure(
        data=go.Candlestick(
            x=data.index,
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            showlegend=False,
            name=f"{symbol}",
        ),
        layout=dict(autosize=True, template="plotly_dark"),
    )
    vxma = go.Scatter(
        x=data.index,
        y=data["vxma"],
        mode="lines",
        line=go.scatter.Line(color="yellow"),
        showlegend=True,
        name="VXMA",
    )
    buy = go.Scatter(
        x=data.index,
        y=data["buyPrice"],
        mode="markers",
        marker=dict(size=20, color="lime"),
        showlegend=True,
        name="Buy",
    )
    sell = go.Scatter(
        x=data.index,
        y=data["sellPrice"],
        mode="markers",
        marker=dict(size=20, color="orange"),
        showlegend=True,
        name="Sell",
    )
    pvtop = go.Scatter(
        x=data.index,
        y=data["highest"],
        mode="lines",
        line=go.scatter.Line(color="red"),
        showlegend=True,
        name="Pivot Top",
    )
    pvbot = go.Scatter(
        x=data.index,
        y=data["lowest"],
        mode="lines",
        line=go.scatter.Line(color="green"),
        showlegend=True,
        name="Pivot Bottom",
    )
    slprice = go.Scatter(
        x=data.index,
        y=data["SLPRICE"],
        mode="lines",
        line=go.scatter.Line(color="white"),
        showlegend=True,
        name="SL Price",
    )
    trendl = go.Scatter(
        x=data.index,
        y=data["TRENDL"],
        mode="markers",
        marker=dict(size=15, color="#00BFFF"),
        showlegend=True,
        name="Trend Change",
    )
    fig.add_trace(vxma)
    fig.add_trace(buy)
    fig.add_trace(sell)
    fig.add_trace(pvtop)
    fig.add_trace(pvbot)
    fig.add_trace(slprice)
    fig.add_trace(trendl)
    fig.update(layout_xaxis_rangeslider_visible=False)
    fig.update_layout(yaxis={"side": "right"})
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
    Output("clientside-graph", "figure"),
    Input("clientside-store-figure", "data"),
)


# # EMA strategy
# @app.callback(
#     Output("clientside-store-figure-ema", "data"),
#     Input("update", "n_intervals"),
#     Input("Apply-strategy", "n_clicks"),
#     State("symbol-dropdown", "value"),
#     State("timeframe-dropdown", "value"),
#     State("num-bar-input", "value"),
#     State("emafast-input", "value"),
#     State("emaslow-input", "value"),
#     prevent_initial_call=True,
# )
# def update_EMA_chart(
#     interval, click, symbol, timeframe, zoom, emafast, emaslow
# ):
#     timeframe = TIMEFRAMES_DICT[timeframe]
#     num_bars = ZOOM_DICT[zoom]
#     try:
#         bars = nomEX.fetch_ohlcv(
#             symbol, timeframe=timeframe, since=None, limit=barsC
#         )
#     except Exception as e:
#         print(e)
#         logging.info(e)
#         time.sleep(2)
#         bars = nomEX.fetch_ohlcv(
#             symbol, timeframe=timeframe, since=None, limit=barsC
#         )
#     df = pd.DataFrame(
#         bars, columns=["timestamp", "open", "high", "low", "close", "volume"]
#     )
#   df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).map(
#         lambda x: x.tz_convert("Asia/Bangkok")
#     )
#     df = df.set_index("timestamp")
#     df = EMA(df, emafast, emaslow)
#     data = df.tail(num_bars)
#     fig = go.Figure(
#         data=go.Candlestick(
#             x=data.index,
#             open=data["open"],
#             high=data["high"],
#             low=data["low"],
#             close=data["close"],
#             showlegend=False,
#             name=f"{symbol}",
#         ),
#         layout=dict(autosize=True, template="plotly_dark"),
#     )
#     ema1 = go.Scatter(
#         x=data.index,
#         y=data["EMA_FAST"],
#         mode="lines",
#         line=go.scatter.Line(color="blue"),
#         showlegend=True,
#         name="FAST",
#     )
#     ema2 = go.Scatter(
#         x=data.index,
#         y=data["EMA_SLOW"],
#         mode="lines",
#         line=go.scatter.Line(color="yellow"),
#         showlegend=True,
#         name="SLOW",
#     )
#     buy = go.Scatter(
#         x=data.index,
#         y=data["buyPrice"],
#         mode="markers",
#         marker=dict(size=15, color="lime"),
#         showlegend=True,
#         name="Buy",
#     )
#     sell = go.Scatter(
#         x=data.index,
#         y=data["sellPrice"],
#         mode="markers",
#         marker=dict(size=15, color="orange"),
#         showlegend=True,
#         name="Sell",
#     )
#     fig.add_trace(ema1)
#     fig.add_trace(ema2)
#     fig.add_trace(buy)
#     fig.add_trace(sell)
#     fig.update(layout_xaxis_rangeslider_visible=False)
#     fig.update_layout(yaxis={"side": "right"})
#     fig.layout.xaxis.fixedrange = True
#     fig.layout.yaxis.fixedrange = True
#     return fig


# Clientside callback
# app.clientside_callback(
#     """
#     function(figure_data, title_text) {
#         if(figure_data === undefined) {
#             return {'data': [], 'layout': {}};
#         }
#         const fig = Object.assign({}, figure_data, {
#                 'layout': {
#                     ...figure_data.layout,
#                     'title': {
#                         ...figure_data.layout.title, text: title_text
#                     }
#                 }
#         });
#         return fig;
#     }
#     """,
#     Output("clientside-graph-ema", "figure"),
#     Input("clientside-store-figure-ema", "data"),
# )


# #VXMA Execute bot
@app.callback(
    Output("alert-suc", "children"),
    Input("run-input", "n_clicks"),
    State("symbol-dropdown", "value"),
    State("timeframe-dropdown", "value"),
    State("atr-input", "value"),
    State("atrm-input", "value"),
    State("EMA-input", "value"),
    State("SUBHAG-input", "value"),
    State("SMOOTH-input", "value"),
    State("RSI-input", "value"),
    State("Andean-Oscillator-input", "value"),
    State("leverage-input", "value"),
    State("Pivot-lookback-input", "value"),
    State("RR-TP1-input", "value"),
    State("RR-TP2-input", "value"),
    State("per-TP1-input", "value"),
    State("per-TP2-input", "value"),
    State("Risk-input", "value"),
    State("maxmargin-input", "value"),
    State("ready-input", "checked"),
    State("Long-input", "checked"),
    State("Short-input", "checked"),
    State("TP1-input", "checked"),
    State("TP2-input", "checked"),
    State("Stop-input", "checked"),
    State("Tailing-input", "checked"),
)
def excuteBot(
    click,
    symbol,
    timeframe,
    atr_input,
    atrM_input,
    ema_ip,
    subhag,
    smooth,
    rsi_ip,
    aol_ip,
    leverage,
    Pivot,
    RR1,
    RR2,
    TP1,
    TP2,
    Risk,
    maxMargin,
    ready,
    ul,
    us,
    tp,
    tp2,
    sl,
    tsl,
):
    if click is not None:
        data = pd.DataFrame(columns=BOTCOL)
        if ready:
            id = f"{symbol}_{timeframe}"
            compo = [
                id,
                symbol,
                timeframe,
                atr_input,
                atrM_input,
                ema_ip,
                subhag,
                smooth,
                rsi_ip,
                aol_ip,
                ul,
                us,
                tp,
                tp2,
                sl,
                tsl,
                leverage,
                Pivot,
                RR1,
                RR2,
                TP1,
                TP2,
                Risk,
                maxMargin,
            ]
            try:
                data = pd.read_csv("bot_config.csv")
                data = data.append(
                    pd.Series(compo, index=BOTCOL), ignore_index=True
                )
                data.to_csv("bot_config.csv", index=False)
                notify_send("Setting บอทเรียบร้อย บอทกำลังทำงาน!")
                return [
                    dbc.Alert(
                        "Success.",
                        dismissable=True,
                        duration=5000,
                        is_open=True,
                    )
                ]
            except sqlite3.Error as e:
                print(e)
                return [
                    dbc.Alert(
                        "Ops! Something went wrong, Please retry.",
                        dismissable=True,
                        duration=5000,
                        is_open=True,
                        color="danger",
                    )
                ]
        else:
            return [
                dbc.Alert(
                    "Ops! Something went wrong, Please retry.",
                    dismissable=True,
                    duration=5000,
                    is_open=True,
                    color="danger",
                )
            ]
    else:
        return [
            dbc.Alert(
                "Wellcome.",
                dismissable=True,
                duration=5000,
                is_open=True,
                color="info",
            )
        ]


# api setting


@app.callback(
    Output("alert-su", "children"),
    Input("set-api-key", "n_clicks"),
    State("freebalance-input", "value"),
    State("minBalance-input", "value"),
    State("api-key-input", "value"),
    State("api-secret-input", "value"),
    State("api-notify-input", "value"),
    State("repasswdKey-input", "value"),
    State("readyAPI-input", "checked"),
    prevent_initial_call=True,
    background=True,
)
def setting(click, freeB, minB, api_key, apiZ, notifykey, pwd, ready):
    if click is not None:
        data = pd.DataFrame(
            columns=["freeB", "minB", "apikey", "apisec", "notify"]
        )
        with sqlite3.connect("vxma.db", check_same_thread=False) as con:
            config = pd.read_sql("SELECT * FROM user", con=con)
        id = config["id"][0]
        valit = True if perf(id, pwd) else False
        if ready and valit:
            try:
                compo = [freeB, minB, api_key, apiZ, notifykey]
                data.loc[1] = compo
                data = data.set_index("apikey")
                with sqlite3.connect(
                    "vxma.db", check_same_thread=False
                ) as con:
                    data.to_sql(
                        "key",
                        con=con,
                        if_exists="replace",
                        index=True,
                        index_label="apikey",
                    )
                    con.commit()
                notify_send("Setting API update")
                return [
                    dbc.Alert(
                        "Success.",
                        dismissable=True,
                        duration=5000,
                        is_open=True,
                    )
                ]
            except sqlite3.Error as e:
                print(e)
                return [
                    dbc.Alert(
                        "Ops! Something went wrong, Please retry.",
                        dismissable=True,
                        duration=5000,
                        is_open=True,
                        color="danger",
                    )
                ]
        else:
            return [
                dbc.Alert(
                    "Ops! Something went wrong, Please retry.",
                    dismissable=True,
                    duration=5000,
                    is_open=True,
                    color="danger",
                )
            ]
    else:
        return PreventUpdate


# #reset user pass
@app.callback(
    Output("alert-fai", "children"),
    Input("resetpass-input", "n_clicks"),
    State("passwd-input", "value"),
    State("passwd-input", "value"),
    State("newUsername-input", "value"),
    prevent_initial_call=True,
    background=True,
)
def resetpwd(click, pwd1, pwd2, id):
    if click is not None:
        data = pd.DataFrame(columns=["id", "pass"])
        valit = True if pwd1 == pwd2 else False
        if valit:
            cook = cooking(id, pwd2)
            compo = [id, cook]
            data.loc[1] = compo
            data = data.set_index("id")
            try:
                with sqlite3.connect(
                    "vxma.db", check_same_thread=False
                ) as con:
                    data.to_sql(
                        "user",
                        con=con,
                        if_exists="replace",
                        index=True,
                        index_label="id",
                    )
                    con.commit()
                notify_send("Setting รหัสผ่านสำเร็จ")
                return [
                    dbc.Alert(
                        "Success.",
                        dismissable=True,
                        duration=5000,
                        is_open=True,
                    )
                ]
            except Exception as e:
                print(e)
                logging.info(e)
                return [
                    dbc.Alert(
                        "Ops! Something went wrong, Please retry.",
                        dismissable=True,
                        duration=5000,
                        is_open=True,
                        color="danger",
                    )
                ]
        else:
            return [
                dbc.Alert(
                    "Ops! Something went wrong, Please retry.",
                    dismissable=True,
                    duration=5000,
                    is_open=True,
                    color="danger",
                )
            ]
    else:
        return [
            dbc.Alert(
                "Ops! Something went wrong, Please retry.",
                dismissable=True,
                duration=5000,
                is_open=True,
                color="danger",
            )
        ]


# #read data running bot
@app.callback(
    Output("datatable", "children"),
    Input("update-table", "n_clicks"),
)
def runningBot(click):
    if click is not None:
        symbolist = bot_setting()
        return dash_table.DataTable(
            data=symbolist.to_dict("records"),
            columns=[{"name": i, "id": i} for i in symbolist],
            page_current=0,
            page_size=99,
            page_action="custom",
            editable=True,
            id="datatable",
            style_table={"color": "black"},
        )
    else:
        return PreventUpdate


# #write data edit running bot
@app.callback(
    Output("alert-bot", "children"),
    Input("edit-table", "submit_n_clicks"),
    State("datatable", "data"),
    State("edit-input", "checked"),
    prevent_initial_call=True,
)
def edit_menu(click, rows, ready):
    if click is not None and ready is not None:
        if ready:
            try:
                df = pd.DataFrame(rows, columns=BOTCOL)
                df = df.dropna(axis=0, how="any")
                df.to_csv("bot_config.csv", index=False)
                notify_send("มีการแก้ไขบอท")
                return [
                    dbc.Alert(
                        "Success.",
                        dismissable=True,
                        duration=5000,
                        is_open=True,
                    )
                ]
            except Exception as e:
                print(e)
                return [
                    dbc.Alert(
                        "Ops! Something went wrong, Please retry.",
                        dismissable=True,
                        duration=5000,
                        is_open=True,
                        color="danger",
                    )
                ]
        else:
            return [
                dbc.Alert(
                    "Ops! Something went wrong, Please retry.",
                    dismissable=True,
                    duration=5000,
                    is_open=True,
                    color="danger",
                )
            ]
    else:
        return [
            dbc.Alert(
                "Ops! Something went wrong, Please retry.",
                dismissable=True,
                duration=5000,
                is_open=True,
                color="danger",
            )
        ]
