import board
import busio
import displayio
import terminalio
import i2cdisplaybus
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import json
import time
import usb_cdc

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC
from kmk.scanners import DiodeOrientation
from kmk.modules.layers import Layers
from kmk.modules.encoder import EncoderHandler
from kmk.extensions.media_keys import MediaKeys
from kmk.modules.macros import Macros
from kmk.modules.mouse_keys import MouseKeys
from kmk.modules import Module

# --- HARDWARE CONFIGURATION ---
keyboard = KMKKeyboard()
keyboard.debug_enabled = True

keyboard.col_pins = (board.D6, board.D7, board.D10)
keyboard.row_pins = (board.D0, board.D1, board.D2, board.D3)
keyboard.diode_orientation = DiodeOrientation.COL2ROW 

encoder_handler = EncoderHandler()
encoder_handler.pins = ((board.D8, board.D9, None, False),)

keyboard.modules.append(encoder_handler)
keyboard.modules.append(Layers())
keyboard.modules.append(Macros())
keyboard.modules.append(MouseKeys())
keyboard.extensions.append(MediaKeys())

# --- OLED SETUP ---
displayio.release_displays()
i2c = busio.I2C(board.D5, board.D4)
display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=32)

serial_data = None
try:
  serial_data = usb_cdc.data
except Exception:
  try:
    serial_data = usb_cdc.console
  except Exception:
    serial_data = None

pressed_state = [False] * 12
current_screen_text = "MAXPAD v1\nReady..."
current_layer = 0
last_telemetry = 0.0

def send_telemetry(force=False):
  global last_telemetry
  if serial_data is None:
    return

  now = time.monotonic()
  if not force and (now - last_telemetry) < 0.05:
    return

  payload = {
    "type": "telemetry",
    "active_profile": current_layer,
    "pressed": pressed_state,
    "screen": current_screen_text,
    "ts": now,
  }

  try:
    serial_data.write((json.dumps(payload) + "\n").encode("utf-8"))
    last_telemetry = now
  except Exception:
    try:
      usb_cdc.console.write((json.dumps(payload) + "\n").encode("utf-8"))
      last_telemetry = now
    except Exception:
      # Keep firmware stable even if host disconnects.
      pass

def expand_keys(keys, size=12):
    result = list(keys[:size])
    while len(result) < size:
        result.append(KC.NO)
    return result

def expand_encoder(enc):
    result = list(enc[:3])
    while len(result) < 3:
        result.append(KC.NO)
    return tuple(result)

def update_screen(text):
  global current_screen_text
  current_screen_text = text
  splash = displayio.Group()
  text_area = label.Label(terminalio.FONT, text=text, color=0xFFFFFF, x=5, y=15)
  splash.append(text_area)
  display.root_group = splash
  send_telemetry(True)

def parse_key(k_str):
    try:
        if k_str.startswith("KC."):
            return eval(k_str, {"KC": KC})
        return KC.TRNS
    except:
        return KC.TRNS

# --- THE COORDINATE MAP ---
keyboard.coord_mapping = [
    0,  1,  2,  11, 7,  
    8,  3,  4,   5, 9,  
    10, 6               
]

class TelemetryModule(Module):
  def during_bootup(self, keyboard):
    return None

  def before_matrix_scan(self, keyboard):
    return None

  def after_matrix_scan(self, keyboard):
    return None

  def process_key(self, keyboard, key, is_pressed, int_coord):
    if int_coord is not None:
      try:
        idx = keyboard.coord_mapping.index(int_coord)
        if 0 <= idx < len(pressed_state):
          pressed_state[idx] = bool(is_pressed)
          send_telemetry(True)
      except Exception:
        pass
    return key

  def before_hid_send(self, keyboard):
    return None

  def after_hid_send(self, keyboard):
    return None

  def on_powersave_enable(self, keyboard):
    return None

  def on_powersave_disable(self, keyboard):
    return None

  def deinit(self, keyboard):
    return None

keyboard.modules.append(TelemetryModule())

# --- LOAD CONFIG ---
mode_names = {}
try:
    with open("maxpad_config.json", "r") as f:
        config = json.load(f)
    
    keymap = []
    encoder_map = []
    
    profiles = config.get("profiles", config.get("layers", []))
    for i, layer in enumerate(profiles):
        mode_names[i] = (layer.get("name", f"PROFILE {i}") + " profile")
        layer_keys = [parse_key(k) for k in layer.get("keys", [])]
        keymap.append(expand_keys(layer_keys))
        
        enc = [parse_key(k) for k in layer.get("encoder", ["KC.NO", "KC.NO", "KC.NO"])]
        encoder_map.append((expand_encoder(enc),))
        
    if not keymap:
        raise ValueError("Empty config")
        
    keyboard.keymap = keymap
    encoder_handler.map = encoder_map

except Exception as e:
    # Fallback default
    mode_names = {0: "ERROR / DEFAULT profile"}
    keyboard.keymap = [
        expand_keys([KC.A, KC.B, KC.C, KC.D, KC.E, KC.F, KC.G, KC.H, KC.I, KC.J, KC.K, KC.L])
    ]
    encoder_handler.map = [((KC.VOLD, KC.VOLU, KC.NO),)]
    print("Error loading config:", e)

# --- MAIN LOOP ---
current_layer = -1
if __name__ == '__main__':
    update_screen("MAXPAD v1\nReady...")
    keyboard._init()
    while True:
        new_layer = keyboard.active_layers[0] if keyboard.active_layers else 0
        if new_layer != current_layer:
            current_layer = new_layer
            update_screen(mode_names.get(current_layer, f"PROFILE {current_layer} profile"))

        keyboard._main_loop()
        send_telemetry(False)
