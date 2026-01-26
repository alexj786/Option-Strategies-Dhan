import time
import datetime
import talib
from Dhan_Tradehull import Tradehull

# ==================== LOGIN ====================
client_code = "1102773623"
token_id    = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY4NDUzMDg5LCJpYXQiOjE3NjgzNjY2ODksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAyNzczNjIzIn0.O4S-V4zMJOaBk6wO3WKGD6tyOnBROWAKRnXBYAxyEvKpFI0bM0XFpZxGsTbzqv0vbowOCiVqPnydjL8FPRgS7A"
tsl = Tradehull(client_code, token_id)

# ==================== CAPITAL ====================
opening_balance = tsl.get_balance()
base_capital = 100000
market_money = opening_balance - base_capital

if market_money < 0:
	market_money = 0
	base_capital = opening_balance

max_risk_for_today = 1500
max_order_for_today = 5
risk_per_trade = max_risk_for_today / max_order_for_today
atr_multipler = 3

# ==================== STATE ====================
watchlist = ['NIFTY JAN FUT']
last_candle_time = {}

single_order = {
	'options_name': None,
	'hedge_symbol': None,
	'hedge_qty': None,
	'entry_price': None,
	'qty': None,
	'sl': None,
	'tsl': None,
	'exit_price': None,
	'pnl': None,
	'traded': None,
	'remark': None
}

orderbook = {}
completed_orders = []

for name in watchlist:
	orderbook[name] = single_order.copy()

user_input_price = int(input("Enter NIFTY breakdown price: "))

# ==================== MAIN LOOP ====================
while True:

	current_time = datetime.datetime.now().time()
	if current_time < datetime.time(9, 15):
		time.sleep(1)
		continue

	# -------- Daily Loss Protection --------
	live_pnl = tsl.get_live_pnl()
	if live_pnl < -max_risk_for_today:
		print("Max loss hit. Closing all positions.")
		#tsl.cancel_all_orders()
		break

	for name in watchlist:

		# -------- Candle Scan (15m) --------
		try:
			chart = tsl.get_intraday_data("NIFTY JAN FUT", "NFO", 15)
			cc = chart.iloc[-2]                       # last CLOSED candle
			candle_time = cc.name

			if last_candle_time.get(name) == candle_time:
				continue

			last_candle_time[name] = candle_time
			candle_close = cc['close']
			print(f"Current Completed Candle Close: {candle_close}, Time: {current_time}", "& you entered level", {user_input_price})

		except:
			continue

		# -------- ENTRY --------
		if candle_close <= user_input_price and orderbook[name]['traded'] is None:

			print("Bearish signal confirmed. Entering Bear Put Spread.")

			_, pe_name, _, _ = tsl.OTM_Strike_Selection('NIFTY', 0, 2)
			_, ITM_PE, _, _ = tsl.ITM_Strike_Selection('NIFTY', 0, 1)

			lot_size = tsl.get_lot_size(ITM_PE)

			opt_chart = tsl.get_intraday_data(ITM_PE, "NFO", 15)
			opt_chart['atr'] = talib.ATR(
				opt_chart['high'], opt_chart['low'], opt_chart['close'], 14
			)

			rc = opt_chart.iloc[-2]
			sl_points = rc['atr'] * atr_multipler

			# ----- Place Orders -----
			entry_oid = tsl.order_placement(
				tradingsymbol=ITM_PE,
				exchange='NFO',
				quantity=lot_size,
				price=0,
				trigger_price=0,
				order_type='MARKET',
				transaction_type='BUY',
				trade_type='MIS'
			)
			time.sleep(2)

			tsl.order_placement(
				tradingsymbol=pe_name,
				exchange='NFO',
				quantity=lot_size,
				price=0,
				trigger_price=0,
				order_type='MARKET',
				transaction_type='SELL',
				trade_type='MIS'
			)

			entry_price = tsl.get_executed_price(orderid=entry_oid)
			sl_price = round(entry_price - sl_points, 1)

			orderbook[name] = {
				'options_name': ITM_PE,
				'hedge_symbol': pe_name,
				'hedge_qty': lot_size,
				'entry_price': entry_price,
				'qty': lot_size,
				'sl': sl_price,
				'tsl': sl_price,
				'traded': "yes",
				'remark': "Entry"
			}

			continue

		# ==================== ACTIVE TRADE ====================
		if orderbook[name]['traded'] == "yes":

			options_ltp = tsl.get_ltp_data(names = ITM_PE)
			print(f"Current LTP of {ITM_PE}: {options_ltp} and current TSL is {orderbook[name]['tsl']} --— checking if the current TSL is hit")
			

			# -------- EXIT (TSL HIT) --------
			if options_ltp <= orderbook[name]['tsl']:

				print("TSL hit. Exiting hedge first, then primary.")

				# Exit hedge
				tsl.order_placement(
					tradingsymbol=orderbook[name]['hedge_symbol'],
					exchange='NFO',
					quantity=orderbook[name]['hedge_qty'],
					price=0,
					trigger_price=0,
					order_type='MARKET',
					transaction_type='BUY',
					trade_type='MIS'
				)

				time.sleep(0.3)

				# Exit primary
				exit_oid = tsl.order_placement(
					tradingsymbol=orderbook[name]['options_name'],
					exchange='NFO',
					quantity=orderbook[name]['qty'],
					price=0,
					trigger_price=0,
					order_type='MARKET',
					transaction_type='SELL',
					trade_type='MIS'
				)

				exit_price = tsl.get_executed_price(orderid=exit_oid)
				pnl = (exit_price - orderbook[name]['entry_price']) * orderbook[name]['qty']

				orderbook[name]['exit_price'] = exit_price
				orderbook[name]['pnl'] = pnl
				orderbook[name]['remark'] = "TSL Exit"

				completed_orders.append(orderbook[name])
				orderbook[name] = single_order.copy()

				continue

			# -------- TRAILING UPDATE --------
			opt_chart = tsl.get_intraday_data(ITM_PE, "NFO", 5)
			opt_chart['atr'] = talib.ATR(
				opt_chart['high'], opt_chart['low'], opt_chart['close'], 14
			)

			rc = opt_chart.iloc[-2]
			new_tsl = options_ltp - (rc['atr'] * atr_multipler)

			if new_tsl > orderbook[name]['tsl']:
				orderbook[name]['tsl'] = round(new_tsl, 1)

	time.sleep(1)
