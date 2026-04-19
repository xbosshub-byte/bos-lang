import sys
import re

class BOSLexer:
    def __init__(self, code):
        self.code = code
        self.tokens = []
        self.tokenize()

    def tokenize(self):
        # เพิ่มคีย์เวิร์ด while เข้ามา
        keywords = {'if', 'while', 'print', 'api_send', 'mqtt_pub'}
        rules = [
            ('STRING',   r'"[^"]*"'),
            ('NUMBER',   r'\d+'),
            ('EQ',       r'=='),
            ('ASSIGN',   r'='),
            ('PLUS',     r'\+'),              # เพิ่มเครื่องหมายบวก
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
        self.loop_stack = [] # Stack สำหรับจำตำแหน่งเริ่มต้นของ Loop

    def _get_val(self, token):
        """ตัวช่วยดึงข้อมูล ไม่ว่าจะเป็น ตัวเลข ข้อความ หรือ ค่าในตัวแปร"""
        if token[0] == 'NUMBER': return int(token[1])
        elif token[0] == 'STRING': return token[1].strip('"')
        elif token[0] == 'ID': return self.env.get(token[1], 0)
        return ""

    def execute(self, tokens):
        i = 0
        while i < len(tokens):
            if i >= len(tokens): break
            kind, value = tokens[i]

            # 1. การกำหนดค่า (เช่น coin = 10 หรือ coin = coin + 5)
            if kind == 'ID' and i + 1 < len(tokens) and tokens[i+1][0] == 'ASSIGN':
                var_name = value
                
                # เช็คว่าเป็นการบวกเลขหรือไม่ (เช่น coin = coin + 5)
                if i + 3 < len(tokens) and tokens[i+3][0] == 'PLUS':
                    val1 = self._get_val(tokens[i+2])
                    val2 = self._get_val(tokens[i+4])
                    self.env[var_name] = val1 + val2
                    i += 5
                else:
                    self.env[var_name] = self._get_val(tokens[i+2])
                    i += 3

            # 2. คำสั่งแสดงผล
            elif kind == 'PRINT':
                print(self._get_val(tokens[i+1]))
                i += 2

            # 3. คำสั่ง MQTT
            elif kind == 'MQTT_PUB':
                topic = self._get_val(tokens[i+1])
                msg = self._get_val(tokens[i+2])
                print(f"[MQTT Action] >> Topic: '{topic}' | Data: '{msg}'")
                i += 3

            # 4. เงื่อนไข IF และ WHILE
            elif kind in ('IF', 'WHILE'):
                start_idx = i # จำตำแหน่งเริ่มต้นไว้เผื่อต้องวนลูปกลับมา
                var_name = tokens[i+1][1]
                op = tokens[i+2][0]
                compare_val = int(tokens[i+3][1])
                
                i += 4 
                if i < len(tokens) and tokens[i][0] == 'LBRACE': 
                    i += 1 
                    
                current_val = self.env.get(var_name, 0)
                condition_met = False
                
                if op == 'GT': condition_met = current_val > compare_val
                elif op == 'LT': condition_met = current_val < compare_val
                elif op == 'EQ': condition_met = current_val == compare_val

                if condition_met:
                    if kind == 'WHILE':
                        self.loop_stack.append(start_idx) # เก็บตำแหน่งเพื่อวนกลับ
                    # ทำงานบรรทัดถัดไปในบล็อกตามปกติ
                else:
                    # ถ้าเงื่อนไขเป็นเท็จ ให้ข้ามไปหาปีกกาปิด }
                    brace_count = 1
                    while i < len(tokens) and brace_count > 0:
                        if tokens[i][0] == 'LBRACE': brace_count += 1
                        elif tokens[i][0] == 'RBRACE': brace_count -= 1
                        i += 1
            
            # 5. ปีกกาปิด }
            elif kind == 'RBRACE':
                if self.loop_stack:
                    i = self.loop_stack.pop() # วนลูปกลับไปเช็คเงื่อนไข WHILE ใหม่
                else:
                    i += 1
            else:
                i += 1

def run_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        lexer = BOSLexer(code)
        interpreter = BOSInterpreter()
        interpreter.execute(lexer.tokens)
        
    except FileNotFoundError:
        print(f"Error: ไม่พบไฟล์ '{filepath}'")
    except Exception as e:
        print(f"Runtime Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python bos.py <file.bos>")
    else:
        run_file(sys.argv[1])
