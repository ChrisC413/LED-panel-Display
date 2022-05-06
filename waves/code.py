#
# SPDX-License-Identifier: MIT

import time
import os
import displayio
import usb_cdc
from adafruit_matrixportal.matrix import Matrix
# usb_cdc.enable(console=True, data=True)
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


def load_images():
    """
    Load an image as a sprite
    """
    # pylint: disable=global-statement
    global current_frame, current_loop, frame_count, frame_duration
    while sprite_group:
        sprite_group.pop()

    # # CircuitPython 7+ compatible
    bitmap = displayio.OnDiskBitmap("/bmps/waves_dark.bmp")
    sprite = displayio.TileGrid(
        bitmap,
        pixel_shader=bitmap.pixel_shader,
        tile_width=bitmap.width,
        tile_height=8,
        y=32
    )
    sprite_group.append(sprite)
    
    for i in range(40, 64, 8):
        bitmap = displayio.OnDiskBitmap("/bmps/waves_dim.bmp")
        sprite = displayio.TileGrid(
            bitmap,
            pixel_shader=bitmap.pixel_shader,
            tile_width=bitmap.width,
            tile_height=8,
            y=i
        )
        sprite_group.append(sprite)
    

    current_frame = 0
    current_loop = 0
    frame_count = 4
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
    load_images()


def advance_frame():
    """
    Advance to the next frame and loop back at the end
    """
    # pylint: disable=global-statement
    global current_frame, current_loop
    current_frame = current_frame + 1
    if current_frame >= frame_count:
        current_frame = 0
        current_loop = current_loop + 1
    for i, sprite in enumerate(sprite_group):
        sprite[0]= (current_frame + i) % 4
        time.sleep(.2)

advance_image()

while True:
    if auto_advance and current_loop >= AUTO_ADVANCE_LOOPS:
        advance_image()
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


