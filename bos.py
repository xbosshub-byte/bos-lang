import sys
import re
import time
import random
import os

# ==========================================
# 1. ระบบตรวจจับแพลตฟอร์ม & โหลด Library
# ==========================================
SYS_PLATFORM = sys.platform
HW_MODE = "MOCK"   
NET_MODE = "MOCK"  

if SYS_PLATFORM in ['esp32', 'rp2']:
    HW_MODE = "MICROPYTHON"
    try:
        from machine import ADC, Pin
        import network
        from umqtt.simple import MQTTClient
        NET_MODE = "MICROPYTHON"
    except ImportError: pass 
else:
    try:
        import paho.mqtt.client as mqtt_client
        NET_MODE = "PAHO"
    except ImportError: pass
    try:
        import RPi.GPIO as GPIO
        HW_MODE = "RPI"
        
        # ระบบ Auto-Download สำหรับ Pi 5 ดึงไลบรารีจาก BOSSHUB 
        if not os.path.exists("tm1637_display.py"):
            print("[SYSTEM]: ไม่พบ tm1637_display.py กำลังดาวน์โหลดจาก BOSSHUB...")
            import urllib.request
            urllib.request.urlretrieve("https://ide.bosshub.io/libs/admin/tm1637_display.py", "tm1637_display.py")
            print("[SYSTEM]: ดาวน์โหลดไลบรารีสำเร็จ!")
            
        import tm1637_display as rpi_tm1637 
    except ImportError: pass

# ==========================================
# 2. ระบบประมวลผล (Interpreter)
# ==========================================
class BOSInterpreter:
    def __init__(self):
        self.env = {}
        self.loop_stack = []
        self.mqtt = None
        self.display = None

    def _get_val(self, token):
        if token[0] == 'NUMBER': return int(token[1])
        elif token[0] == 'STRING': return token[1].strip('"')
        elif token[0] == 'ID': return self.env.get(token[1], 0)
        return ""

    def execute(self, tokens):
        i = 0
        while i < len(tokens):
            if i >= len(tokens): break
            kind, value = tokens[i]

            # --- [Basic Logic] ---
            if kind == 'ID' and i + 1 < len(tokens) and tokens[i+1][0] == 'ASSIGN':
                if i + 3 < len(tokens) and tokens[i+3][0] == 'PLUS':
                    self.env[value] = self._get_val(tokens[i+2]) + self._get_val(tokens[i+4])
                    i += 5
                else:
                    self.env[value] = self._get_val(tokens[i+2])
                    i += 3
            elif kind == 'PRINT':
                print(f"[BOS]: {self._get_val(tokens[i+1])}")
                i += 2
            elif kind == 'DELAY':
                time.sleep(self._get_val(tokens[i+1]) / 1000)
                i += 2

            # --- [User Input (POS & Vending)] ---
            elif kind == 'INPUT':
                var_name = tokens[i+1][1]
                prompt = self._get_val(tokens[i+2])
                if HW_MODE in ("MOCK", "RPI"):
                    val = input(f"{prompt} ") # รอรับค่าจาก Keyboard/Barcode Scanner
                    try: val = int(val) # แปลงเป็นตัวเลขถ้าทำได้
                    except ValueError: pass
                    self.env[var_name] = val
                else:
                    self.env[var_name] = 1 # โหมดจำลองสำหรับบอร์ดที่ไม่มีคีย์บอร์ด
                i += 3
                
            elif kind == 'WAIT_BTN':
                pin = self._get_val(tokens[i+1])
                var_name = tokens[i+2][1]
                print(f"[HARDWARE]: กรุณากดปุ่มที่ Pin {pin}...")
                
                if HW_MODE == "MICROPYTHON":
                    btn = Pin(pin, Pin.IN, Pin.PULL_UP)
                    while btn.value() == 1: time.sleep(0.1) # รอจนกว่าจะมีการกด (Active Low)
                elif HW_MODE == "RPI":
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    while GPIO.input(pin) == GPIO.HIGH: time.sleep(0.1)
                else:
                    input("[MOCK]: กด Enter เพื่อจำลองการกดปุ่มฮาร์ดแวร์...")
                
                self.env[var_name] = 1 # กำหนดค่าให้ตัวแปรว่าถูกกดแล้ว
                print(f"[HARDWARE]: ปุ่ม Pin {pin} ถูกกดแล้ว!")
                i += 3

            # --- [Network & MQTT] ---
            elif kind == 'WIFI_CONNECT':
                ssid, pwd = self._get_val(tokens[i+1]), self._get_val(tokens[i+2])
                if NET_MODE == "MICROPYTHON":
                    w = network.WLAN(network.STA_IF); w.active(True); w.connect(ssid, pwd)
                    while not w.isconnected(): pass
                print(f"[WIFI]: Connected to {ssid}")
                i += 3
            elif kind == 'MQTT_CONNECT':
                broker = self._get_val(tokens[i+1])
                cid = self.env.get('machine_id', 'BOS_DEV')
                if NET_MODE == "PAHO":
                    self.mqtt = mqtt_client.Client(cid); self.mqtt.connect(broker, 1883); self.mqtt.loop_start()
                elif NET_MODE == "MICROPYTHON":
                    self.mqtt = MQTTClient(cid, broker); self.mqtt.connect()
                print(f"[MQTT]: Connected to {broker}")
                i += 2
            elif kind == 'MQTT_PUB':
                t, m = self._get_val(tokens[i+1]), str(self._get_val(tokens[i+2]))
                if self.mqtt:
                    if NET_MODE == "PAHO": self.mqtt.publish(t, m)
                    elif NET_MODE == "MICROPYTHON": self.mqtt.publish(t.encode(), m.encode())
                i += 3

            # --- [TM1637 Display Control] ---
            elif kind == 'DISPLAY_INIT':
                clk, dio = self._get_val(tokens[i+1]), self._get_val(tokens[i+2])
                if HW_MODE == "MICROPYTHON":
                    import tm1637 
                    self.display = tm1637.TM1637(clk=Pin(clk), dio=Pin(dio))
                elif HW_MODE == "RPI":
                    self.display = rpi_tm1637.TM1637(clk=clk, dio=dio)
                print(f"[DISPLAY]: Initialized on CLK:{clk} DIO:{dio}")
                i += 3
            elif kind == 'DISPLAY_NUM':
                val = self._get_val(tokens[i+1])
                if self.display:
                    if HW_MODE == "MICROPYTHON": self.display.number(int(val))
                    elif HW_MODE == "RPI": self.display.number(int(val))
                i += 2

            # --- [Hardware IO] ---
            elif kind == 'READ_SENSOR':
                v, p = tokens[i+1][1], self._get_val(tokens[i+2])
                self.env[v] = ADC(Pin(p)).read_u16() if HW_MODE == "MICROPYTHON" else random.randint(10, 50)
                i += 3
            elif kind in ('PIN_ON', 'PIN_OFF'):
                p, s = self._get_val(tokens[i+1]), (1 if kind == 'PIN_ON' else 0)
                if HW_MODE == "MICROPYTHON": Pin(p, Pin.OUT).value(s)
                elif HW_MODE == "RPI": 
                    GPIO.setup(p, GPIO.OUT); GPIO.output(p, s)
                i += 2

            # --- [Control Flow] ---
            elif kind in ('IF', 'WHILE'):
                start = i
                var, op, target = tokens[i+1][1], tokens[i+2][0], int(tokens[i+3][1])
                i += 4; if tokens[i][0] == 'LBRACE': i += 1
                curr = self.env.get(var, 0)
                cond = (curr > target if op == 'GT' else curr < target if op == 'LT' else curr == target)
                if cond:
                    if kind == 'WHILE': self.loop_stack.append(start)
                else:
                    b = 1
                    while i < len(tokens) and b > 0:
                        if tokens[i][0] == 'LBRACE': b += 1
                        elif tokens[i][0] == 'RBRACE': b -= 1
                        i += 1
            elif kind == 'RBRACE':
                if self.loop_stack: i = self.loop_stack.pop()
                else: i += 1
            else: i += 1

# ==========================================
# 3. Lexer & Main
# ==========================================
class BOSLexer:
    def __init__(self, code):
        self.tokens = []
        kw = {'if', 'while', 'print', 'wifi_connect', 'mqtt_connect', 'mqtt_pub', 'read_sensor', 'delay', 'pin_on', 'pin_off', 'display_init', 'display_num', 'input', 'wait_btn'}
        rules = [
            ('STRING', r'"[^"]*"'), ('NUMBER', r'\d+'), ('EQ', r'=='), ('ASSIGN', r'='),
            ('PLUS', r'\+'), ('GT', r'>'), ('LT', r'<'), ('LBRACE', r'\{'), ('RBRACE', r'\}'),
            ('ID', r'[A-Za-z_]\w*'), ('NEWLINE', r'\n'), ('SKIP', r'[ \t]+'), ('MISMATCH', r'.'),
        ]
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in rules)
        for mo in re.finditer(tok_regex, code):
            k, v = mo.lastgroup, mo.group()
            if k in ('SKIP', 'NEWLINE'): continue
            if k == 'ID' and v in kw: k = v.upper()
            self.tokens.append((k, v))

def main():
    if len(sys.argv) < 2: 
        print("BOS Pro v2.5 (POS & Vending Input Edition)")
        print("วิธีใช้: bos <file.bos>")
        return
    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            BOSInterpreter().execute(BOSLexer(f.read()).tokens)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__': main()
