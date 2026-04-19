import sys
import re
import time
import random

# ==========================================
# 1. ระบบตรวจจับแพลตฟอร์ม (Auto-Detect)
# ==========================================
SYS_PLATFORM = sys.platform
HW_MODE = "MOCK"   
NET_MODE = "MOCK"  

if SYS_PLATFORM in ['esp32', 'rp2']:
    HW_MODE = "MICROPYTHON"
    try:
        from machine import ADC, Pin
    except ImportError:
        pass
    try:
        import network
        from umqtt.simple import MQTTClient
        NET_MODE = "MICROPYTHON"
    except ImportError:
        pass 
else:
    try:
        import paho.mqtt.client as mqtt_client
        NET_MODE = "PAHO"
    except ImportError:
        pass
    try:
        import RPi.GPIO as GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        HW_MODE = "RPI"
    except ImportError:
        pass

# ==========================================
# 2. ระบบประมวลผล (Interpreter)
# ==========================================
class BOSInterpreter:
    def __init__(self):
        self.env = {}
        self.loop_stack = []
        self.mqtt = None
        self.wifi = None
        self.env['SYS_PLATFORM'] = SYS_PLATFORM 

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

            if kind == 'ID' and i + 1 < len(tokens) and tokens[i+1][0] == 'ASSIGN':
                var_name = value
                if i + 3 < len(tokens) and tokens[i+3][0] == 'PLUS':
                    self.env[var_name] = self._get_val(tokens[i+2]) + self._get_val(tokens[i+4])
                    i += 5
                else:
                    self.env[var_name] = self._get_val(tokens[i+2])
                    i += 3

            elif kind == 'PRINT':
                print(f"[BOS]: {self._get_val(tokens[i+1])}")
                i += 2

            elif kind == 'DELAY':
                time.sleep(self._get_val(tokens[i+1]) / 1000)
                i += 2

            # --- จัดการ Wi-Fi และ MQTT ---
            elif kind == 'WIFI_CONNECT':
                ssid = self._get_val(tokens[i+1])
                pwd = self._get_val(tokens[i+2])
                print(f"[WIFI]: กำลังเชื่อมต่อ {ssid}...")
                if NET_MODE == "MICROPYTHON":
                    self.wifi = network.WLAN(network.STA_IF)
                    self.wifi.active(True)
                    self.wifi.connect(ssid, pwd)
                    while not self.wifi.isconnected(): pass
                    print("[WIFI]: เชื่อมต่อสำเร็จ")
                else:
                    print(f"[WIFI]: แจำลองการเชื่อมต่อบน {SYS_PLATFORM}")
                i += 3

            elif kind == 'MQTT_CONNECT':
                broker = self._get_val(tokens[i+1])
                client_id = self.env.get('machine_id', f'BOS_{random.randint(1000,9999)}')
                if NET_MODE == "PAHO":
                    self.mqtt = mqtt_client.Client(client_id)
                    self.mqtt.connect(broker, 1883)
                    self.mqtt.loop_start()
                elif NET_MODE == "MICROPYTHON":
                    self.mqtt = MQTTClient(client_id, broker)
                    self.mqtt.connect()
                print(f"[MQTT]: เชื่อมต่อ {broker} สำเร็จ")
                i += 2

            elif kind == 'MQTT_PUB':
                topic = self._get_val(tokens[i+1])
                msg = str(self._get_val(tokens[i+2]))
                if self.mqtt:
                    if NET_MODE == "PAHO": self.mqtt.publish(topic, msg)
                    elif NET_MODE == "MICROPYTHON": self.mqtt.publish(topic.encode(), msg.encode())
                print(f"[MQTT PUB]: {topic} -> {msg}")
                i += 3

            # --- จัดการ Sensor / GPIO (Input/Output) ---
            elif kind == 'READ_SENSOR':
                var_name = tokens[i+1][1]
                pin = self._get_val(tokens[i+2])
                if HW_MODE == "MICROPYTHON":
                    adc = ADC(Pin(pin))
                    if SYS_PLATFORM == 'esp32': adc.atten(ADC.ATTN_11V)
                    val = adc.read_u16() 
                elif HW_MODE == "RPI":
                    GPIO.setup(pin, GPIO.IN)
                    val = GPIO.input(pin)
                else:
                    val = random.randint(100, 999) # โหมดจำลอง
                self.env[var_name] = val
                print(f"[SENSOR]: อ่านค่า Pin {pin} ได้ {val}")
                i += 3

            elif kind in ('PIN_ON', 'PIN_OFF'):
                pin_num = self._get_val(tokens[i+1])
                state = 1 if kind == 'PIN_ON' else 0
                
                if HW_MODE == "MICROPYTHON":
                    p = Pin(pin_num, Pin.OUT)
                    p.value(state)
                elif HW_MODE == "RPI":
                    GPIO.setup(pin_num, GPIO.OUT)
                    GPIO.output(pin_num, state)
                
                status_text = "เปิด (ON)" if state == 1 else "ปิด (OFF)"
                print(f"[OUTPUT]: สั่งการ Pin {pin_num} -> {status_text}")
                i += 2

            # --- จัดการ Control Flow ---
            elif kind in ('IF', 'WHILE'):
                start_idx = i
                var_name = tokens[i+1][1]
                op = tokens[i+2][0]
                compare_val = int(tokens[i+3][1])
                i += 4 
                if i < len(tokens) and tokens[i][0] == 'LBRACE': i += 1 
                
                curr = self.env.get(var_name, 0)
                cond = False
                if op == 'GT': cond = curr > compare_val
                elif op == 'LT': cond = curr < compare_val
                elif op == 'EQ': cond = curr == compare_val

                if cond:
                    if kind == 'WHILE': self.loop_stack.append(start_idx)
                else:
                    braces = 1
                    while i < len(tokens) and braces > 0:
                        if tokens[i][0] == 'LBRACE': braces += 1
                        elif tokens[i][0] == 'RBRACE': braces -= 1
                        i += 1
            
            elif kind == 'RBRACE':
                if self.loop_stack: i = self.loop_stack.pop()
                else: i += 1
            else: i += 1

# ==========================================
# 3. ตัวแยกคำสั่ง (Lexer)
# ==========================================
class BOSLexer:
    def __init__(self, code):
        self.tokens = []
        keywords = {'if', 'while', 'print', 'wifi_connect', 'mqtt_connect', 'mqtt_pub', 'read_sensor', 'delay', 'pin_on', 'pin_off'}
        rules = [
            ('STRING', r'"[^"]*"'), ('NUMBER', r'\d+'), ('EQ', r'=='), ('ASSIGN', r'='),
            ('PLUS', r'\+'), ('GT', r'>'), ('LT', r'<'), ('LBRACE', r'\{'), ('RBRACE', r'\}'),
            ('ID', r'[A-Za-z_]\w*'), ('NEWLINE', r'\n'), ('SKIP', r'[ \t]+'), ('MISMATCH', r'.'),
        ]
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in rules)
        for mo in re.finditer(tok_regex, code):
            kind = mo.lastgroup
            val = mo.group()
            if kind in ('SKIP', 'NEWLINE'): continue
            if kind == 'ID' and val in keywords: kind = val.upper()
            self.tokens.append((kind, val))

def main():
    if len(sys.argv) < 2:
        print("BOS Pro v2.2 (Hardware Control Edition)")
        print("วิธีใช้: bos <file.bos>")
        return
    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            lexer = BOSLexer(f.read())
        BOSInterpreter().execute(lexer.tokens)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
