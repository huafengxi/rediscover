"""Small, bounded expression language. Never evaluate Python or inferred AI output."""
import re
from fractions import Fraction

TOKEN = re.compile(r'(?:\d{1,9}(?:\.\d{1,9})?|\.[0-9]{1,9}|[+*/()^%-])')
TRANS = str.maketrans({'×':'*','÷':'/','−':'-','–':'-','（':'(','）':')','％':'%','π':'p','，':',','．':'.', **{chr(65296+i):str(i) for i in range(10)}, '＋':'+','－':'-','＊':'*','／':'/','＝':'='})

def parse(expr):
    t = re.sub(r'\s+', '', expr.translate(TRANS)).replace('**','^').replace('p','3.141592654')
    tokens = TOKEN.findall(t)
    if not tokens or ''.join(tokens) != t or len(tokens) > 70:
        raise ValueError('写成数字、括号和 + − × ÷ ^，不要省略乘号。')
    i = 0
    count = 0
    def take():
        nonlocal i
        if i >= len(tokens):
            raise ValueError('算式还没有写完。')
        i += 1
        return tokens[i-1]
    def level(minimum=0):
        nonlocal i,count
        a = take()
        if a in ('+','-'):
            x = level(3) * (-1 if a == '-' else 1)
        elif a == '(':
            x = level()
            if take() != ')':
                raise ValueError('请配对左右括号。')
        else:
            x = Fraction(a)
        while i < len(tokens):
            op = tokens[i]
            priority = {'+':1,'-':1,'*':2,'/':2,'^':3,'%':4}.get(op,0)
            if not priority or priority < minimum:
                break
            i += 1
            if op == '%':
                x /= 100
                continue
            count += 1
            y = level(priority + (op != '^'))
            if op == '^':
                if y.denominator != 1 or abs(y) > 8:
                    raise ValueError('此处只支持 −8 至 8 的整数指数。')
                x **= y.numerator
            else:
                x = {'+':lambda:x+y,'-':lambda:x-y,'*':lambda:x*y,'/':lambda:x/y}[op]()
            if max(x.numerator.bit_length(), x.denominator.bit_length()) > 256:
                raise ValueError('中间数值过大。')
        return x
    x = level()
    if i != len(tokens):
        raise ValueError('运算符或括号的位置不对。')
    return x,count

def grade(q, raw, unit):
    if len(raw) > 200:
        return False, '请只保留这一问的算式。'
    try:
        parts = raw.translate(TRANS).split('=')
        if len(parts) > 2:
            return False, '请把单个算式写在等号左侧。'
        x,n = parse(parts[0])
        if len(parts) == 2 and abs(x-parse(parts[1])[0]) > Fraction(q.get('tol','0')):
            return False,'等号两边的数值不一致；请检查计算或保留位数。'
    except (ValueError, ZeroDivisionError) as e:
        if isinstance(e, ZeroDivisionError):
            return False, '分母不能为零。'
        return False, str(e) if not str(e).startswith('Invalid literal') else '请写出可计算的数字算式；单位另填。'
    if abs(x-Fraction(q['answer'])) > Fraction(q.get('tol','0')):
        for partial, feedback in q.get('partial',{}).items():
            if abs(x-Fraction(partial)) <= Fraction(q.get('tol','0')):
                return False,feedback
        return False,q['hint']
    if q.get('require_expression',True) and not n:
        return False,'数值吻合。请补上从题中数据得到它的计算关系。'
    if q.get('units') and unit.strip().casefold().replace('²','^2').replace('³','^3') not in q['units']:
        return False,'算式给出了目标数值，但单位不对或还未填写；请按题面单位填写。'
    return True,q['pass']
