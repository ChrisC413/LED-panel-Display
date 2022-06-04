import time
import json
import rtc

r = rtc.RTC()

def set_animations(key, value):
    if key == 'cpu':
        if value == 'h':
            return '/bmps/fast'
        if value == 'l':
            print('cpu low')
            return '/bmps/slow'

def set_time(time_str: str):
    r.datetime = time.localtime(int(time_str) - 60* 60 *4)
    current_time = r.datetime
    print(current_time)

def process_serial_input(input):
    try:
        input_obj = json.loads(input)
    except:
        print("bad input")
        print(input)
        return

    if 'time' in input_obj:
        set_time(input_obj['time'])

    if 'cpu' in input_obj:
        return set_animations('cpu', input_obj['cpu'])

