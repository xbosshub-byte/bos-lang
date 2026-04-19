import sys
import re

# หากต้องการต่อ MQTT ของจริง ให้ติดตั้งไลบรารีก่อน: pip install paho-mqtt
# และเอาคอมเมนต์ด้านล่างนี้ออกครับ
# import paho.mqtt.client as mqtt 

class BOSLexer:
    def __init__(self, code):
        self.code = code
        self.tokens = []
        self.tokenize()

    def tokenize(self):
        # เพิ่มคีย์เวิร์ด mqtt_pub เข้ามาในระบบ
        keywords = {'if', 'print', 'api_send', 'mqtt_pub'}
        rules = [
            ('STRING',   r'"[^"]*"'),
            ('NUMBER',   r'\d+'),
            ('EQ',       r'=='),
            ('ASSIGN',   r'='),
            ('GT',       r'>'),
            ('LT',       r'<'),
            ('LBRACE',   r'\{'),
            ('RBRACE',   r'\}'),
            ('ID',       r'[A-Za-z_]\w*'),
            ('NEWLINE',  r'\n'),
            ('SKIP',     r'[ \t]+'),
            ('MISMATCH', r'.'),
        ]
        
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in rules)
        for mo in re.finditer(tok_regex, self.code):
            kind = mo.lastgroup
            value = mo.group()
            
            if kind in ('SKIP', 'NEWLINE'):
                continue
            elif kind == 'MISMATCH':
                raise RuntimeError(f'[Syntax Error] สัญลักษณ์ที่ไม่ได้รับอนุญาต: "{value}"')
            elif kind == 'ID' and value in keywords:
                kind = value.upper()
                
            self.tokens.append((kind, value))

class BOSInterpreter:
    def __init__(self):
        self.env = {}
        # โค้ดสำหรับเชื่อมต่อ MQTT ของจริง (ใส่ Broker ของคุณแทนได้เลย)
        # self.mqtt = mqtt.Client()
        # self.mqtt.connect("broker.hivemq.com", 1883, 60)

    def execute(self, tokens):
        i = 0
        while i < len(tokens):
            kind, value = tokens[i]

            if kind == 'ID' and i + 1 < len(tokens) and tokens[i+1][0] == 'ASSIGN':
                var_name = value
                val_token = tokens[i+2]
                if val_token[0] == 'NUMBER':
                    self.env[var_name] = int(val_token[1])
                elif val_token[0] == 'STRING':
                    self.env[var_name] = val_token[1].strip('"')
                i += 3

            elif kind == 'PRINT':
                target = tokens[i+1]
                if target[0] == 'STRING':
                    print(target[1].strip('"'))
                elif target[0] == 'ID':
                    print(self.env.get(target[1], 'NULL'))
                i += 2

            # เพิ่มการทำงานของคำสั่ง mqtt_pub (ตัวอย่าง: mqtt_pub "topic/status" "ONLINE")
            elif kind ==
