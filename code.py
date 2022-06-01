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
AUTO_ADVANCE_LOOPS = 3

DISPLAY_ON = True
LAST_INPUT_RECEIVED = 0

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
    print(SPRITESHEET_FOLDER)
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
    if r.datetime.tm_hour not in range(7,20) and DISPLAY_ON:
        DISPLAY_ON = False
        while sprite_group:
            sprite_group.pop()
    elif DISPLAY_ON == False and  r.datetime.tm_hour in range(7,20):
        DISPLAY_ON = True
        load_image()

while True:
    if auto_advance and current_loop >= AUTO_ADVANCE_LOOPS:
        advance_image()
    while serial.in_waiting > 0:
        byte = serial.read(1)
        if byte == b'\r':
            out_data = in_data
            out_data += b'  '
            print(f'processing: {out_data.decode()}')
            change = process_serial_input(out_data.decode())
            if change:
                print("change in state")
                SPRITESHEET_FOLDER = change
                populate_file_list()
                load_image()

            in_data = bytearray()
            print(r.datetime)
        else:
            in_data += byte
            if len(in_data) == 129:
                in_data = in_data[128] + in_data[1:127]
    advance_frame()
    time.sleep(frame_duration)
    check_time_of_day()
