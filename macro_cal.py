import re
import math

class AdvancedMacroEngine:
    def __init__(self):
        self.vars = {i: 0.0 for i in range(1, 1000)}
        self.pc = 0  # Program Counter (當前執行的行索引)
        self.lines = []
        # 邏輯運算符映射
        self.ops = {"EQ": "==", "NE": "!=", "GT": ">", "LT": "<", "GE": ">=", "LE": "<="}

    def _clean_math(self, expr):
        """處理 CNC 數學表達式"""
        expr = expr.upper().replace('[', '(').replace(']', ')')
        expr = re.sub(r'#(\d+)', r'self.vars[\1]', expr)
        # 映射函數
        expr = expr.replace('SIN(', 'math.sin(math.radians(')
        expr = expr.replace('COS(', 'math.cos(math.radians(')
        expr = expr.replace('SQRT(', 'math.sqrt(')
        return expr

    def _eval_condition(self, condition_str):
        """解析 IF 中的邏輯條件，例如 [#1 GT #2]"""
        # 移除外層括號
        cond = condition_str.strip()[1:-1]
        for cnc_op, py_op in self.ops.items():
            if cnc_op in cond:
                parts = cond.split(cnc_op)
                left = eval(self._clean_math(parts[0]))
                right = eval(self._clean_math(parts[1]))
                return eval(f"{left} {py_op} {right}")
        return False

    def run(self, gcode_text):
        self.lines = [line.split('(')[0].strip() for line in gcode_text.splitlines()]
        
        # 預掃描標記 N 標籤的位置，優化 GOTO 速度
        labels = {re.search(r'N(\d+)', l).group(1): i 
                  for i, l in enumerate(self.lines) if re.match(r'N\d+', l)}

        while self.pc < len(self.lines):
            line = self.lines[self.pc]
            if not line:
                self.pc += 1
                continue

            # 1. 分歧指令：IF [#1 GT 10] GOTO 100
            if line.startswith('IF'):
                match = re.search(r'IF\s*(.+?)\s*GOTO\s*(\d+)', line)
                if match:
                    condition, target = match.groups()
                    if self._eval_condition(condition):
                        self.pc = labels[target]
                        print(f">>> Condition Met: Jumping to N{target}")
                        continue

            # 2. 演算賦值：#100 = [#101 + 1.0]
            elif line.startswith('#'):
                var_part, expr_part = line.split('=')
                var_num = int(re.search(r'\d+', var_part).group())
                self.vars[var_num] = eval(self._clean_math(expr_part))
                print(f"[VAR] #{var_num} = {self.vars[var_num]}")

            # 3. 普通指令：G01 X#100
            elif line.startswith('G') or line.startswith('X') or line.startswith('Y'):
                output = line
                for m in re.findall(r'#(\d+)', line):
                    output = output.replace(f"#{m}", f"{self.vars[int(m)]:.3f}")
                print(f"[EXEC] {output}")

            self.pc += 1

# --- 測試多重邏輯的 Macro 文本 ---
macro_script = """
#1 = 1.0       (起始半徑)
#2 = 5.0       (目標半徑)
#3 = 1.5       (每次遞增)
N100
#1 = [#1 + #3] (運算：增加半徑)
G01 X#1 F500   (輸出移動)
IF [#1 LT #2] GOTO 100 (分歧：如果半徑小於5則跳回N100)
G00 X0         (結束後回原點)
"""

engine = AdvancedMacroEngine()
engine.run(macro_script)