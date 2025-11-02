import time
import datetime
import traceback
import pandas as pd
import talib
from Dhan_Tradehull import Tradehull

# ==============================
# USER CONFIGURATION
# ==============================
client_code = "Enter Client Code From Broker"
token_id = "Enter TOken  from your profile"
# Initialize Tradehull session
tsl = Tradehull(client_code, token_id)

# ==============================
# STRATEGY CONFIGURATION
# ==============================
ATM_CE_symbol_name, ATM_PE_symbol_name, ATM_strike_price = tsl.ATM_Strike_Selection(Underlying='NIFTY', Expiry=0)
print("============Dada Take a note of ATM strikes, ATM option var ch sagla khel chalnar aahe====================")
print("✅ ATM CE Symbol:", ATM_CE_symbol_name)
print("✅ ATM PE Symbol:", ATM_PE_symbol_name)
print("✅ ATM Strike Price:", ATM_strike_price)
print("========================================================================================================")
available_balance = tsl.get_balance()
leveraged_margin = available_balance * 5
max_trades = 2
per_trade_margin = leveraged_margin / max_trades
max_loss = available_balance * 0.01

# Watchlist setup
watchlist = [ATM_PE_symbol_name]
entry_done = False
iteration = 1

# Cutoff for entry (HH:MM)
CUTOFF_HOUR = 11
CUTOFF_MINUTE = 15


print("===================================================================")
print(f"🚀 Starting strategy at {datetime.datetime.now().strftime('%H:%M:%S')}")
print(f"Available balance: ₹{available_balance:.2f}")
print(f"Leverage: x5 | Max trades: {max_trades} | Max loss: ₹{max_loss:.2f}")
print("===================================================================")

# ==============================
# STRATEGY LOOP
# ==============================
while not entry_done:
    now = datetime.datetime.now()
    if now.hour > CUTOFF_HOUR or (now.hour == CUTOFF_HOUR and now.minute >= CUTOFF_MINUTE):
        print(f"🛑 Time cutoff reached ({now.strftime('%H:%M')}). Stopping strategy safely.")
        break

    for stock in watchlist:
        time.sleep(0.2)

        # Step 1: Select OTM and Hedge CALL strikes
       #otm_ce_name, otm_pe_name, ce_otm_strike, pe_otm_strike = tsl.OTM_Strike_Selection('NIFTY', 0, 1)
        otm_H_ce_name, otm_H_pe_name, ce_H_otm_strike, pe_H_otm_strike = tsl.OTM_Strike_Selection('NIFTY', 0, 4)

        # Step 1.1: Modification , do calculate ATM as primary is going to be ATM
        ATM_CE_symbol_name, ATM_PE_symbol_name, ATM_strike_price = tsl.ATM_Strike_Selection(Underlying='NIFTY', Expiry=0)

        print("===================================================================")
        print(f"Primary ATM PUT Option (Sell Leg): {ATM_PE_symbol_name}")
        print(f"Hedge PUT Option (Buy Leg): {otm_H_pe_name}")
        print("===================================================================")

        # Step 2: Fetch 15-min data for CALL symbol
        chart_15 = tsl.get_intraday_data(stock, "NFO", 15)
        print(f"Iteration: {iteration} | Checking: {stock}")

        if chart_15 is None or chart_15.empty:
            print("No intraday data available: Market Band aahe, tumhi abhyaas kara")
            continue

        # Step 3: Identify first candle (9:15–9:30)
        first_candle = chart_15.iloc[0]
        first_candle_low = first_candle['low']
        first_candle_time = first_candle.name
        print(f"First Candle Low: {first_candle_low}, Time: {first_candle_time}")

        # Step 4: Use last completed candle for entry check
        current_completed_candle = chart_15.iloc[-2]
        current_close = current_completed_candle['close']
        current_time = current_completed_candle.name

        print(f"Checking last completed 15-min candle at {current_time} | "
              f"Close = {current_close:.2f} | First Candle Low = {first_candle_low:.2f}")

        # Entry condition: Last completed candle close < first candle low
        if current_close < first_candle_low:
            print(f"✅ Entry condition met at {current_time} (Close: {current_close} < Low: {first_candle_low})")

            lot_size = tsl.get_lot_size(ATM_PE_symbol_name)

            # Hedge BUY (deeper OTM PUT)
            ltp_hedge = tsl.get_ltp_data(names=otm_H_pe_name)
            #tsl.order_placement(otm_H_pe_name, 'NFO', lot_size, 0, 0, 'MARKET', 'BUY', 'MIS')
            print(f"Paper trade Hedge BUY executed: {otm_H_pe_name} at price: {ltp_hedge}")
            

            # Primary SELL (near OTM PUT)
            ltp_primary = tsl.get_ltp_data(names=ATM_PE_symbol_name)
            #tsl.order_placement(ATM_PE_symbol_name, 'NFO', lot_size, 0, 0, 'MARKET', 'SELL', 'MIS')
            print(f"Paper Trade Primary position SELL executed: {ATM_PE_symbol_name} at price: {ltp_primary}")

            entry_done = True
            print("🎯 Entry executed successfully. No further entries will be made today.")

            # Step 5: Ask for Stop-Loss Monitoring
            enable_sl = input("🛑🛑 Do you want to enable stop-loss monitoring? (y/n): ").strip().lower()

            if enable_sl == 'y':
                print("📊 Stop-loss monitoring activated. Checking every 5 minutes...")

                while True:
                    time.sleep(300)  # every 5 min
                    try:
                        chart_15_sl = tsl.get_intraday_data(ATM_PE_symbol_name, "NFO", 15)
                        if chart_15_sl is None or chart_15_sl.empty:
                            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ⚠️ No new data. Retrying...")
                            continue

                        last_candle = chart_15_sl.iloc[-2]
                        last_close = last_candle['close']
                        last_time = last_candle.name

                        print(f"[SL Check {datetime.datetime.now().strftime('%H:%M:%S')}] {otm_H_pe_name} | "
                              f"Last Close = {last_close:.2f}, First Low = {first_candle_low:.2f}")

                        # Stop-loss trigger
                        if last_close > first_candle_low:
                            print(f"🚨 Stop-loss triggered at {last_time}! (Close {last_close} > Low {first_candle_low})")

                            # Exit primary SELL first
                            #tsl.order_placement(ATM_PE_symbol_name, 'NFO', lot_size, 0, 0, 'MARKET', 'BUY', 'MIS')
                            print(f"Exited primary position: {ATM_PE_symbol_name}")

                            # Exit hedge BUY next
                            #tsl.order_placement(otm_H_pe_name, 'NFO', lot_size, 0, 0, 'MARKET', 'SELL', 'MIS')
                            print(f"Exited hedge position: {otm_H_pe_name}")

                            print("✅ Both positions exited. Stopping SL monitor.")
                            break

                        # Optional: Stop SL monitoring after 3 PM
                        now = datetime.datetime.now()
                        if now.hour >= 15:
                            print("⏰ Market nearing close. Exiting SL monitor.")
                            break

                    except Exception as e:
                        print(f"⚠️ Error during SL check: {e}")
                        traceback.print_exc()
                        continue

            else:
                print("🟢 Stop-loss monitoring skipped by user.")

            break  # Exit after one successful trade

        iteration += 1

    if not entry_done:
        print(f"No valid entry yet at {datetime.datetime.now().strftime('%H:%M')}. Retrying...\n")
        time.sleep(300)
