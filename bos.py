import sys
import re

class BOSLexer:
    def __init__(self, code):
        self.code = code
        self.tokens = []
        self.tokenize()

    def tokenize(self):
        keywords = {'if', 'print', 'api_send'}
        rules = [
            ('STRING',   r'"[^"]*"'),             # ข้อความ
            ('NUMBER',   r'\d+'),                 # ตัวเลข
            ('EQ',       r'=='),                  # ตรวจสอบความเท่ากับ
            ('ASSIGN',   r'='),                   # กำหนดค่า
            ('GT',       r'>'),                   # มากกว่า
            ('LT',       r'<'),                   # น้อยกว่า
            ('LBRACE',   r'\{'),                  # ปีกกาเปิด
            ('RBRACE',   r'\}'),                  # ปีกกาปิด
            ('ID',       r'[A-Za-z_]\w*'),        # ชื่อตัวแปรหรือคำสั่ง
            ('NEWLINE',  r'\n'),                  # บรรทัดใหม่
            ('SKIP',     r'[ \t]+'),              # เว้นวรรค
            ('MISMATCH', r'.'),                   # สัญลักษณ์ที่ไม่รู้จัก
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
                kind = value.upper() # เปลี่ยนเป็น Keyword Token
                
            self.tokens.append((kind, value))

class BOSInterpreter:
    def __init__(self):
        self.env = {} # หน่วยความจำของระบบ

    def execute(self, tokens):
        i = 0
        while i < len(tokens):
            kind, value = tokens[i]

            # 1. การกำหนดค่าตัวแปร (เช่น coin = 15)
            if kind == 'ID' and i + 1 < len(tokens) and tokens[i+1][0] == 'ASSIGN':
                var_name = value
                val_token = tokens[i+2]
                
                if val_token[0] == 'NUMBER':
                    self.env[var_name] = int(val_token[1])
                elif val_token[0] == 'STRING':
                    self.env[var_name] = val_token[1].strip('"')
                i += 3

            # 2. คำสั่งแสดงผล (print)
            elif kind == 'PRINT':
                target = tokens[i+1]
                if target[0] == 'STRING':
                    print(target[1].strip('"'))
                elif target[0] == 'ID':
                    print(self.env.get(target[1], 'NULL'))
                i += 2

            # 3. คำสั่งจำลองการส่ง API (api_send)
            elif kind == 'API_SEND':
                target = tokens[i+1]
                data = target[1].strip('"') if target[0] == 'STRING' else self.env.get(target[1], 'NULL')
                print(f"[Hardware/API Mock] >> Sending Data: {data}")
                i += 2

            # 4. เงื่อนไข If แบบง่าย (if var > num { ... })
            elif kind == 'IF':
                var_name = tokens[i+1][1]
                op = tokens[i+2][0]
                compare_val = int(tokens[i+3][1])
                
                # ข้ามไปหาจุดเริ่มบล็อก {
                i += 4 
                if tokens[i][0] == 'LBRACE':
                    i += 1 # เข้าสู่บล็อก
                    
                # ดึงค่าปัจจุบันมาตรวจสอบ
                current_val = self.env.get(var_name, 0)
                condition_met = False
                
                if op == 'GT' and current_val > compare_val: condition_met = True
                elif op == 'LT' and current_val < compare_val: condition_met = True
                elif op == 'EQ' and current_val == compare_val: condition_met = True

                # ถ้าเงื่อนไขเป็นจริง ให้ประมวลผลต่อตามปกติ ถ้าเป็นเท็จ ให้หาปีกกาปิด }
                if not condition_met:
                    while i < len(tokens) and tokens[i][0] != 'RBRACE':
                        i += 1
                else:
                    pass # ทำงานบรรทัดต่อไปในบล็อก
            
            # ปีกกาปิด (ข้ามการประมวลผล)
            elif kind == 'RBRACE':
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
        print(e)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python bos.py <file.bos>")
    else:
        run_file(sys.argv[1])
