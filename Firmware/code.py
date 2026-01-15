import board
import busio
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC
from kmk.scanners import DiodeOrientation
from kmk.modules.layers import Layers
from kmk.modules.encoder import EncoderHandler
from kmk.extensions.media_keys import MediaKeys

# --- HARDWARE CONFIGURATION ---
keyboard = KMKKeyboard()

# 3x4 Matrix (matches your KiCad schematic)
keyboard.col_pins = (board.D6, board.D7, board.D10)
keyboard.row_pins = (board.D0, board.D1, board.D2, board.D3)
keyboard.diode_orientation = DiodeOrientation.COL2ROW 

# Encoder Setup
encoder_handler = EncoderHandler()
encoder_handler.pins = ((board.D8, board.D9, None, False),)
keyboard.modules.append(encoder_handler)
keyboard.modules.append(Layers())
keyboard.extensions.append(MediaKeys())

# --- OLED SETUP (D4=SDA, D5=SCL) ---
displayio.release_displays()
i2c = busio.I2C(board.D5, board.D4) # SCL, SDA
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=32)

# Helper to write text to screen
def update_screen(text):
    splash = displayio.Group()
    bg = displayio.TileGrid(displayio.Bitmap(128, 32, 1), pixel_shader=displayio.Palette(1))
    text_area = label.Label(terminalio.FONT, text=text, color=0, x=5, y=15)
    splash.append(bg)
    splash.append(text_area)
    display.root_group = splash

# --- KEYMAP ---
# LOGICAL LAYOUT: Your electrical matrix is 4 rows x 3 cols.
# But physically you have 5 cols x 3 rows.
#
# Electrical Map vs Physical Map:
# [SW1, SW2, SW3]   -> Top Row Left
# [SW4, SW5, SW6]   -> Top Right + Mid Left
# [SW7, SW8, SW9]   -> Mid Right + Bottom Left
# [SW10, SW11, SW12]-> Bottom Mid + Knob Keys

# LAYER 0: MEDIA & NAV
# Knob: Volume Up/Down
keyboard.keymap = [
    [
        # ROW 1 (SW1, SW2, SW3)
        KC.MEDIA_PREV_TRACK, KC.MEDIA_PLAY_PAUSE, KC.MEDIA_NEXT_TRACK,
        # ROW 2 (SW4, SW5, SW6)
        KC.MUTE,             KC.LCTRL(KC.C),      KC.LCTRL(KC.V),
        # ROW 3 (SW7, SW8, SW9)
        KC.LGUI(KC.D),       KC.LALT(KC.TAB),     KC.LGUI,
        # ROW 4 (SW10, SW11<, SW12>)
        KC.DELETE,           KC.TO(1),            KC.TO(2),
    ],
    # LAYER 1: CODING / OBS (Red)
    [
        KC.F5,               KC.F10,              KC.F11,
        KC.MACRO("git status"), KC.MACRO("git add ."), KC.MACRO("git commit -m"),
        KC.LCTRL(KC.Z),      KC.LCTRL(KC.Y),      KC.LCTRL(KC.S),
        KC.ENTER,            KC.TO(2),            KC.TO(0),
    ],
    # LAYER 2: SYSTEM / ZOOM (Blue)
    [
        KC.LCTRL(KC.W),      KC.LCTRL(KC.T),      KC.LCTRL(KC.SHIFT(KC.T)),
        KC.VIDEO,            KC.AUDIO_MUTE,       KC.NO,
        KC.NO,               KC.NO,               KC.NO,
        KC.NO,               KC.TO(0),            KC.TO(1),
    ]
]

# Encoder Map (Volume on L0, Scroll on L1, Zoom on L2)
encoder_handler.map = [
    ((KC.VOLD, KC.VOLU, KC.MUTE),),  # Layer 0
    ((KC.MW_UP, KC.MW_DN, KC.NO),),  # Layer 1
    ((KC.LCTRL(KC.MINUS), KC.LCTRL(KC.PLUS), KC.NO),), # Layer 2
]

# --- MAIN LOOP ---
current_layer = -1
if __name__ == '__main__':
    update_screen("MAXPAD v1\nReady...")
    
    while True:
        # Check Layer Change for OLED
        new_layer = keyboard.active_layers[0]
        if new_layer != current_layer:
            current_layer = new_layer
            mode_names = {0: "MEDIA MODE", 1: "CODE MODE", 2: "ZOOM MODE"}
            update_screen(mode_names.get(current_layer, "UNKNOWN"))
            
        keyboard.go()