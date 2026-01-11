#Bearish Entry with ATR, this code is not tested as of 11th jan 2026

import pdb
import time
import datetime
import traceback
#from Dhan_Tradehull_V2 import Tradehull
from Dhan_Tradehull import Tradehull
import pandas as pd
#from pprint import pprint
import talib

client_code = "1102773623"
token_id    = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY4MDMzODM2LCJpYXQiOjE3Njc5NDc0MzYsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAyNzczNjIzIn0.4qgimaEbkYGJBXIknnIgQWp8GyZl_2aYX96BbuHT8zFvzp9py6OSp1cdFe1NGY1IChzHGa_825AaC_0U10EQgw"
tsl         = Tradehull(client_code,token_id)

print("========================ENTRY===========================================")
user_input_price = int(input("At which price should the 15-minute Nifty candle close for a BEARISH ENTRY? NIFTY FUTURES would need to close below (breakdown) this price for entry: "))
print("========================================================================")
print("========================================================================")
print(f"🚀 🚀🚀🚀🚀 Starting strategy at {datetime.datetime.now().strftime('%H:%M:%S')}🚀🚀🚀🚀🚀")

entry_done = False
last_checked_time = None

while not entry_done:
    
        # Step 1: Fetch historical data for the specified trading symbol
        # "NIFTY JAN FUT" is the trading symbol, "NFO" is the exchange, and "15" is the timeframe (15-minute candles)
        Futchart_15 = tsl.get_intraday_data("NIFTY JAN FUT", "NFO", 15)
        
        # Step 2: Apply ATR on the chart data
        #print(chart_15)
        Futchart_15['atr'] = talib.ATR(Futchart_15['high'], Futchart_15['low'], Futchart_15['close'], timeperiod=14)
        otm_H_ce_name, otm_H_pe_name, ce_H_otm_strike, pe_H_otm_strike = tsl.OTM_Strike_Selection('NIFTY', 0, 2)

        # Step 1.1: Modification , do calculate ATM as primary is going to be ATM
        ITM_CE_symbol_name, ITM_PE_symbol_name, ITM_strike_price = tsl.ITM_Strike_Selection(Underlying='NIFTY', Expiry=0, ITM_count=1)

        print("===================================================================")
        print("=================Strategy Name: Bear PUT Spread===================")
        print(f"Primary ATM PUT Option (Buy Leg): {ITM_PE_symbol_name}")
        print(f"Hedge PUT Option (Sell Leg): {otm_H_pe_name}")
        print("===================================================================")


        
        current_completed_candle = Futchart_15.iloc[-2]
        current_close = current_completed_candle['close']
        current_time = current_completed_candle.name
        candle_time = current_completed_candle.name
        print(candle_time)
        if candle_time == last_checked_time:
            time.sleep(30)
            continue

        last_checked_time = candle_time

        print(f"Current Completed Candle Close: {current_close}, Time: {current_time}")
        if  current_close <= user_input_price:
            print(f"✅ Entry condition met at {current_time} (User Input Price: {user_input_price} >= Close: {current_close})")
            print("Placing Bear Put Spread Order Now...")
            # Place Bull Put Spread Order
            
            lot_size = tsl.get_lot_size(ITM_PE_symbol_name)
            ltp_primary = tsl.get_ltp_data(names=ITM_PE_symbol_name)
            ltp_hedge = tsl.get_ltp_data(names=otm_H_pe_name)

            # Pri BUY (ITM Put)
            
            tsl.order_placement(ITM_PE_symbol_name, 'NFO', lot_size, 0, 0, 'MARKET', 'BUY', 'MIS')
            print(f"Primay Position Executed: {ITM_PE_symbol_name} at price: {ltp_primary}")
            #Adding Timesleep sothat orders dont clash
            time.sleep(10)
                

            # Hedge SELL (near OTM PUT)
            
            tsl.order_placement(otm_H_pe_name, 'NFO', lot_size, 0, 0, 'MARKET', 'SELL', 'MIS')
            print(f"Hedge Position Executed: {otm_H_pe_name} at price: {ltp_hedge}")

            entry_done = True
            print("🎯 Entry executed successfully. No further entries will be made today.")
            
        else:
            print(f"❌ Entry condition not met at {current_time} (User Input Price: {user_input_price} > Close: {current_close})")


# ============================================================
# ================= SL & TSL MANAGEMENT ======================
# ============================================================

atr_multiplier = 3
trade_active   = True

# --- Fetch option historical data to calculate ATR ---
options_chart = tsl.get_historical_data(
    tradingsymbol=ITM_PE_symbol_name,
    exchange='NFO',
    timeframe="5"
)

options_chart['atr'] = talib.ATR(
    options_chart['high'],
    options_chart['low'],
    options_chart['close'],
    timeperiod=14
)

rc_options = options_chart.iloc[-1]

# --- Initial SL calculation ---
entry_price = tsl.get_ltp_data(names=ITM_PE_symbol_name)
sl_points   = rc_options['atr'] * atr_multiplier
sl_price    = round(entry_price - sl_points, 1)

# --- Place SL order ---
sl_order_id = tsl.order_placement(
    tradingsymbol=ITM_PE_symbol_name,
    exchange='NFO',
    quantity=lot_size,
    price=sl_price - 0.05,
    trigger_price=sl_price,
    order_type='STOPLIMIT',
    transaction_type='SELL',
    trade_type='MIS'
)

print(f"🛑 Initial SL placed at {sl_price}")

# --- TSL starts from SL ---
current_tsl = sl_price


# ================= TSL MONITORING LOOP ======================
while trade_active:

    time.sleep(10)

    # Get latest option price
    option_ltp = tsl.get_ltp_data(names=ITM_PE_symbol_name)

    # Recalculate ATR-based SL distance
    options_chart = tsl.get_historical_data(
        tradingsymbol=ITM_PE_symbol_name,
        exchange='NFO',
        timeframe="5"
    )

    options_chart['atr'] = talib.ATR(
        options_chart['high'],
        options_chart['low'],
        options_chart['close'],
        timeperiod=14
    )

    rc_options = options_chart.iloc[-1]
    sl_points  = rc_options['atr'] * atr_multiplier

    # --- New TSL calculation ---
    new_tsl = round(option_ltp - sl_points, 1)

    # --- Trail SL only upwards ---
    if new_tsl > current_tsl:
        tsl.modify_order(
            order_id=sl_order_id,
            order_type='STOPLIMIT',
            quantity=lot_size,
            price=new_tsl - 0.05,
            trigger_price=new_tsl
        )

        current_tsl = new_tsl
        print(f"🔵 TSL moved up to {current_tsl}")

    # --- Check if SL is hit ---
    sl_status = tsl.get_order_status(orderid=sl_order_id)

    if sl_status == "TRADED":
        print("❌ SL HIT — Trade closed")
        trade_active = False
        break
