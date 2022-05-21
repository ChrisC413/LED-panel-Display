#
# SPDX-License-Identifier: MIT

import time
import os
import displayio
import usb_cdc
import adafruit_requests as requests
from adafruit_ntp import NTP
from adafruit_matrixportal.matrix import Matrix
import board
import busio
from digitalio import DigitalInOut
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi


# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)


while not esp.is_connected:
    try:
        esp.connect_AP(secrets["ssid"], secrets["password"])
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        continue

# Initialize the NTP object
ntp = NTP(esp, debug=True)
while not ntp.valid_time:
    ntp.set_time(tz_offset=-4 * 60 * 60)
    print("Failed to obtain time, retrying in 5 seconds...")
    time.sleep(5)
# Fetch and set the microcontroller's current UTC time
requests.set_socket(socket, esp)

# --| NOAA CONFIG |--------------------------
STATION_ID = (
    "8419317"  # tide location, find yours here: https://tidesandcurrents.noaa.gov/
)
VSCALE = 2  # pixels per ft or m
DAILY_UPDATE_HOUR = 3  # 24 hour format
# -------------------------------------------
def split_date(prediction):
    prediction['h'] , prediction['m'] = prediction['t'].split(" ", 2)[1].split(":")
    return prediction

def generate_noaa_url(station=STATION_ID):
    """Build and return the URL for the tides API."""
    URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?format=json"
    URL += "&product=predictions"
    URL += "&interval=hilo"
    URL += "&datum=mllw"  # MLLW = "tides"
    URL += "&units=metric"
    URL += "&time_zone=lst_ldt"
    URL += "&date=today"
    URL += "&station=" + station
    return URL

def get_tide_data():
    """Fetch JSON tide data and return parsed results in a list."""
    # Get raw JSON data
    response = requests.get(generate_noaa_url())
    response = response.json()
    print(response['predictions'])
    response = map(split_date, response['predictions'])
    return list(response)


def calculate_nearest_tides(predictions):
    curr_hour = getattr(time.localtime(), 'tm_hour')
    curr_min = getattr(time.localtime(), 'tm_min')
    nearest = {}
    for i, prediction in enumerate(predictions):
        if int(prediction['h']) <= curr_hour:
            nearest['previous'] = prediction
            print(f'parse index: {i}')
            if len(predictions) > i+1:
                nearest['next'] = predictions[i+1]
            else:
                nearest['next'] = { 'h': str((int(prediction['h']) + 6) % 24),
                                   'm': prediction['m'],
                                   'type': 'L' if prediction['type'] == 'H' else 'H' }
    if 'previous' not in nearest:
        nearest['next'] = predictions[0]
        nearest['previous'] = { 'h': str(24 - int(nearest['next']['h'])) ,
                                   'm': nearest['next']['m'],
                                   'type': 'L' if nearest['next']['type'] == 'H' else 'H' }
    nearest['direction'] = 'in' if nearest['previous']['type'] == 'L' else 'out'

    # how close to the next tide are we?
    next_tide = int(nearest['next']['h'])
    if next_tide < curr_hour:
        next_tide = next_tide + 24

    mins_till_next_tide = (next_tide - curr_hour) * 60 + int(nearest['next']['m']) - curr_min
    nearest['interval'] = mins_till_next_tide
    return nearest

tide_data = get_tide_data()
nearest_tides = calculate_nearest_tides(tide_data)
print(nearest_tides)

serial = usb_cdc.data
in_data = bytearray()





















SPRITESHEET_FOLDER = "/bmps"
DEFAULT_FRAME_DURATION = .2  # 100ms
AUTO_ADVANCE_LOOPS = 30

# --- Display setup ---
matrix = Matrix(bit_depth=4, height=64, width=64)
sprite_group = displayio.Group()
matrix.display.show(sprite_group)

auto_advance = True

file_list = sorted(
    [
        f
        for f in os.listdir(SPRITESHEET_FOLDER)
        if (f.endswith(".bmp") and not f.startswith("."))
    ]
)

if len(file_list) == 0:
    raise RuntimeError("No images found")

current_image = None
current_frame = 0
current_loop = 0
frame_count = 0
frame_duration = DEFAULT_FRAME_DURATION


def load_tide_images(nearest_tides):
    """
    Load an image as a sprite
    """
    waves = int(nearest_tides['interval']/90 + 1)
    print(waves)
    waves = 5 if waves > 5 else waves
    print(waves)
    # Determine how many intervals
    if nearest_tides['direction'] == 'in':
        waves = 6 - waves
        print("inverting")
    waves = 3 if waves < 3 else waves
    print(waves)
    waves_top_pixel = 64 - 8 * waves
    # pylint: disable=global-statement
    global current_frame, current_loop, frame_count, frame_duration
    while sprite_group:
        sprite_group.pop()

    # # CircuitPython 7+ compatible
    bitmap = displayio.OnDiskBitmap("/bmps/waves_combined.bmp")
    print("top wave")
    print(waves_top_pixel)

    for i in range(waves_top_pixel, 64, 8):

        sprite = displayio.TileGrid(
            bitmap,
            pixel_shader=bitmap.pixel_shader,
            tile_width=bitmap.width,
            tile_height=8,
            y=i
        )
        sprite_group.append(sprite)
    print(f'placed {len(sprite_group)} in sprite group')
    for i, sprite in enumerate(sprite_group):
        if nearest_tides['direction'] == 'in':
            if i < 2:
                sprite[0] = 8
            elif i == 3:
                sprite[0] = 4
            else:
                sprite[0] = 0
        else:
            if i == 0:
                sprite[0] = 4
            else:
                sprite[0] = 0

    current_frame = 0
    current_loop = 0
    frame_count = 4
    frame_duration = DEFAULT_FRAME_DURATION
#     if file_list[current_image] in FRAME_DURATION_OVERRIDES:
#         frame_duration = FRAME_DURATION_OVERRIDES[file_list[current_image]]


def advance_image(nearest_tides):
    """
    Advance to the next image in the list and loop back at the end
    """
    # pylint: disable=global-statement
    global current_image
    if current_image is not None:
        current_image += 1
    if current_image is None or current_image >= len(file_list):
        current_image = 0
    load_tide_images(nearest_tides)


def advance_frame():
    """
    Advance to the next frame and loop back at the end
    """

    global current_frame, current_loop
    current_frame = current_frame + 1
#     if current_frame <= 0:
#         current_frame = frame_count
#         current_loop = current_loop + 1

    for i, sprite in enumerate(sprite_group):
#         print(f'index{i}')
#         print(f'current frame{current_frame}')
        if nearest_tides['direction'] == 'in':
            # first frame show all sprites minus first 3
            if (i == 3 - current_frame) or ( i==0 and 3 - current_frame < 0) : # top most visible sprite
                print(f'top sprite {i} frame ={current_frame + 1}')
                sprite[0] = (current_frame % 3)+1 
            elif i < 3 - current_frame : # invisible sprite
                print(f' hiding  sprite {i}')
                sprite[0] = 0
            else: # regular sprite
                print(f'regular sprite at {i}, frame {5 + (current_frame % 3)}')
                sprite[0] = 5 + (current_frame % 3)
                time.sleep(DEFAULT_FRAME_DURATION)
        else:
            if (i < current_frame) and (i < 2) and (i < len(sprite_group)) : # invisible sprites
                sprite[0] = 0 #top most sprite
                sprite_group[i+1][0] = 1 + current_frame % 4
                time.sleep(DEFAULT_FRAME_DURATION)
            else:
                sprite[0] = 5 + current_frame % 4
                time.sleep(DEFAULT_FRAME_DURATION)
    if current_frame == 9:
        current_frame = -1

advance_image(nearest_tides)

while True:
    while serial.in_waiting > 0:
        byte = serial.read(1)
        if byte == b'\r':
            print(in_data.decode("utf-8"))
            out_data = in_data
            out_data += b'  '
            in_data = bytearray()
            out_index = 0
            print(f'received: {out_data}')
        else:
            in_data += byte
            if len(in_data) == 129:
                in_data = in_data[128] + in_data[1:127]

    advance_frame()
    time.sleep(frame_duration)



