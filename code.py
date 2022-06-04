# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os
import displayio
import usb_cdc
from process_serial import process_serial_input, r
from adafruit_matrixportal.matrix import Matrix
# usb_cdc.enable(console=True, data=True)
serial = usb_cdc.data
in_data = bytearray()

SPRITESHEET_FOLDER = "/bmps/fast"
DEFAULT_FRAME_DURATION = .2  # 100ms
AUTO_ADVANCE_LOOPS = 8
IS_IDLE = False
DISPLAY_ON = True
INPUT_DEADLINE = 0
STATE = ""
LOOP_DELAY = 30
NEXT_IDLE = 0

# --- Display setup ---
matrix = Matrix(bit_depth=4, height=64, width=64)
sprite_group = displayio.Group()
matrix.display.show(sprite_group)

auto_advance = True
def populate_file_list():
    global file_list
    file_list = sorted(
        [
            f
            for f in os.listdir(SPRITESHEET_FOLDER)
            if (f.endswith(".bmp") and not f.startswith("."))
        ]
    )
    if len(file_list) == 0:
        raise RuntimeError("No images found")
    return file_list

def populate_folder_properties(folder: str):
    if "properties.json" in os.listdir(folder):
        prop_file = open(folder+"/properties.json", 'r')
        props = json.loads(prop_file)
        global DEFAULT_FRAME_DURATION, LOOP_DELAY
        if "speed" in props:
            DEFAULT_FRAME_DURATION = float(props['speed'])
        else:
            DEFAULT_FRAME_DURATION = .2
        if "delay" in props:
            LOOP_DELAY = float(props['delay'])
        else:
            LOOP_DELAY = 0
populate_file_list()

current_image = None
current_frame = 0
current_loop = 0
frame_count = 0
frame_duration = DEFAULT_FRAME_DURATION


def load_image():
    """
    Load an image as a sprite
    """
    # pylint: disable=global-statement
    global current_frame, current_loop, frame_count, frame_duration
    while sprite_group:
        sprite_group.pop()

    filename = SPRITESHEET_FOLDER + "/" + file_list[current_image]
    # # CircuitPython 7+ compatible
    bitmap = displayio.OnDiskBitmap(filename)
    sprite = displayio.TileGrid(
        bitmap,
        pixel_shader=bitmap.pixel_shader,
        tile_width=bitmap.width,
        tile_height=matrix.display.height,
    )

    sprite_group.append(sprite)

    current_frame = 0
    current_loop = 0
    frame_count = int(bitmap.height / matrix.display.height)
    frame_duration = DEFAULT_FRAME_DURATION
#     if file_list[current_image] in FRAME_DURATION_OVERRIDES:
#         frame_duration = FRAME_DURATION_OVERRIDES[file_list[current_image]]


def advance_image():
    """
    Advance to the next image in the list and loop back at the end
    """
    # pylint: disable=global-statement
    global current_image
    if current_image is not None:
        current_image += 1
    if current_image is None or current_image >= len(file_list):
        current_image = 0
    load_image()


def advance_frame():
    """
    Advance to the next frame and loop back at the end
    """
    if len(sprite_group) > 0:
        # pylint: disable=global-statement
        global current_frame, current_loop
        current_frame = current_frame + 1
        if current_frame >= frame_count:
            current_frame = 0
            current_loop = current_loop + 1
        sprite_group[0][0] = current_frame

advance_image()

def check_time_of_day():
    global DISPLAY_ON
    if r.datetime.tm_hour not in range(7, 23) and DISPLAY_ON:
        DISPLAY_ON = False
        while sprite_group:
            sprite_group.pop()
    elif DISPLAY_ON is False and r.datetime.tm_hour in range(7, 23) and NEXT_IDLE <= time.mktime(r.datetime):
        DISPLAY_ON = True
        load_image()


def switch_to_idle():
    print("switching to idle mode")
    global SPRITESHEET_FOLDER, IS_IDLE
    IS_IDLE = True
    current_loop = 0
    SPRITESHEET_FOLDER = "/bmps/sleep"
    populate_file_list()
    load_image()

def led_switch_state(input_state: str, path="/bmps/sleep"):
    global STATE, SPRITESHEET_FOLDER
    # no change in state
    if input_state == STATE:
        return

    if STATE != "idle" and input_state == "idle" and STATE != "OFF":
        STATE = "idle"
        SPRITESHEET_FOLDER = "/bmps/sleep"
    elif STATE != "off" and input_state == "off":
        while sprite_group:
            sprite_group.pop()
    elif STATE != "off":  # handle most state changes
        STATE = input_state
        SPRITESHEET_FOLDER = path
    else:
        # break if no change in state
        return

    populate_file_list()
    load_image()



while True:
    if auto_advance and current_loop >= AUTO_ADVANCE_LOOPS:
        if IS_IDLE:
            while sprite_group:
                sprite_group.pop()
#             DISPLAY_ON = False
            NEXT_IDLE = time.mktime(r.datetime) + LOOP_DELAY
            current_loop = -1
#             IS_IDLE = False
#         advance_image()
    while serial.in_waiting > 0:
        byte = serial.read(1)
        if byte == b'\r':
            out_data = in_data
            out_data += b'  '
            print(f'processing: {out_data.decode()}')
            change = process_serial_input(out_data.decode())
            if change:
                print("change in state")
                IS_IDLE = False
                DISPLAY_ON = True
                SPRITESHEET_FOLDER = change
                current_loop = 0
                populate_file_list()
                load_image()

            in_data = bytearray()
            print(r.datetime)
        else:
            in_data += byte
            print(in_data)
            if len(in_data) > 256:
                print("flush")
                in_data = bytearray()
#             if len(in_data) == 129:
#                 in_data = in_data[128] + in_data[1:127]
        # record when display switches to idle mode
        INPUT_DEADLINE = time.mktime(r.datetime) + 30
    advance_frame()
    time.sleep(frame_duration)
    print(f'input deadline{INPUT_DEADLINE}')
    print(time.mktime(r.datetime))
    print(time.mktime(r.datetime) > INPUT_DEADLINE)
    print(f'display on {DISPLAY_ON}')
    print(f'is_idle {IS_IDLE}')
    print((time.mktime(r.datetime) > INPUT_DEADLINE) and DISPLAY_ON and IS_IDLE is False)
    if (time.mktime(r.datetime) > INPUT_DEADLINE) and DISPLAY_ON and IS_IDLE is False:
        switch_to_idle()
    if (time.mktime(r.datetime) > NEXT_IDLE) and IS_IDLE is True and current_loop == -1:
        switch_to_idle()

    check_time_of_day()

