import datetime, time
from iqoptionapi.stable_api import IQ_Option as iq

DELAY_SEC = 2

def login(user, password):
	api = iq(user, password)
	connected, why = api.connect()
	print(connected, why)
	return api, connected

def is_mhi_time():
	now = datetime.datetime.now().time()
	while not (now.minute % 10 == 4 and now.second > (60 - DELAY_SEC)) and not (now.minute % 10 == 9 and now.second > (60 - DELAY_SEC)):
	#while not (now.second >= (60 - DELAY_SEC)):
		now = datetime.datetime.now().time()
		time.sleep(0.5)
		#print(now, not (now.minute % 10 == 4 and now.second > (60 - DELAY_SEC)), not (now.minute % 10 == 9 and now.second > (60 - DELAY_SEC)))
	return True

def verify_gale_need(api, action_close_hour, init_value, direction, pair, seconds_until=1):
	action_close_hour = (action_close_hour - datetime.timedelta(seconds=seconds_until)).time()
	#print("Close hour:", action_close_hour)

	while True:
		time_now = datetime.datetime.strptime(datetime.datetime.now().strftime("%H:%M:%S"),
											  '%H:%M:%S').time()
		if time_now > action_close_hour:
			return False
		if time_now == action_close_hour:
			candle = api.get_realtime_candles(pair, 60)
			value_now = [candle[i]['close'] for i in candle][0]
			if direction == 'put' and value_now > init_value:
				return True
			elif direction == 'call' and value_now < init_value:
				return True
			else:
				return False
		time.sleep(1)

def verify_trend(api, active): # based in https://gist.github.com/dsinmsdj/8c2f1685556f0c28f217f28edced3b94
	candles = api.get_candles(active, 60, 20,  time.time())

	first = candles[0]['close']
	last = candles[-1]['close']

	diff = abs(((last - first) / first) * 100)
	return "call" if last < first and diff > 0.01 else "put" if last > first and diff > 0.01 else "not"
	 

def mhi(api, active, value):
	api.start_candles_stream(active, 60, 1)
	cont_win = 0
	cont_loss = 0
	while is_mhi_time():
		candles = api.get_candles(active, 60, 3, time.time())

		if candles[0]['open'] == candles[0]['close'] or candles[1]['open'] == candles[1]['close'] or candles[2]['open'] == candles[2]['close']:
			continue

		direction_count = 0

		direction_count += 1 if candles[0]['open'] < candles[0]['close'] else -1
		direction_count += 1 if candles[1]['open'] < candles[1]['close'] else -1
		direction_count += 1 if candles[2]['open'] < candles[2]['close'] else -1

		direction = 'call' if direction_count < 0 else 'put'
		trend = verify_trend(api, active) == direction
		#if trend != direction:
		#	print("no trend")
		#	continue
		def buy(do_gale, is_gale):
			status, id_buy = api.buy_digital_spot(active, value * (2**is_gale), direction, 1)
			#print(status, id_buy)
			if not status:
				return False

			time.sleep(DELAY_SEC + 1)

			candle = api.get_realtime_candles(active, 60)
			for i in candle:
				initial_value = candle[i]['close']
				close_hour = datetime.datetime.fromtimestamp(candle[i]['to'])
			if do_gale and not is_gale == 2:
				gale = verify_gale_need(api, close_hour, initial_value, direction, active)
				if gale:
					return buy(True, is_gale + 1)
				else:
					status, result = api.check_win_digital_v2(id_buy)
					while result == None:
						status, result = api.check_win_digital_v2(id_buy)
					return result
			else:
				status, result = api.check_win_digital_v2(id_buy)
				while result == None:
					status, result = api.check_win_digital_v2(id_buy)
				return result


		x = (buy(True, 0))
		if x > 0:
			cont_win += 1
			print("Win - Trend:", trend)
		else:
			cont_loss += 1
			print("Loss - Trend:", trend)
		print(cont_win, cont_loss)

api, connected = login('user', 'password')
api.change_balance('PRACTICE')
mhi(api, 'EURJPY', 1)
