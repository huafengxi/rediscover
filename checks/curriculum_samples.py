"""One focused teaching check per series, with independently selected expected values/constraints."""
from pathlib import Path
import sys
from fractions import Fraction as F
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rediscover.content import load, svg
from rediscover.mathcheck import grade

# Values are review fixtures, not copied from generated answer fields or the fixture's example expression.
CASES = [
    ('A18','evidence','2*15','°',F(30),'东 30.5°','参考港'),
    ('B06','evidence','100/(10000/5)','%',F(1,20),'孤立强散射','5 个事件'),
    ('C07','evidence','(5^2)-24','',F(1),'不再有乘法逆元','余 1'),
    ('D08','evidence','4*3^3/3','cm^3',F(36),'赤道洞半径','R²−z²'),
    ('E05','evidence','(1+2+3)/2','格',F(3),'解析结果','差分法'),
    ('F09','evidence','2*(4-1)','kWh',F(6),'2.88 kWh','功率'),
    ('G04','evidence','1+1+1','',F(3),'八种输入','进位'),
    ('H03','evidence','(50+2*50)/100','位/字',F(3,2),'码表本身','Huffman'),
    ('I05','evidence','(100*0.9)/(100*0.9+900*0.1)','',F(1,2),'8.3%','先验'),
    ('J05','evidence','1/4','',F(1,4),'1:3','密度带'),
    ('K04','evidence','7-2','份/拍',F(5),'容量模型','割'),
    ('L05','evidence','(40+14)/5','cm',F(54,5),'90 cm','方差'),
    ('M05','evidence','16-6-8','Hz',F(2),'采样前滤掉','8 Hz'),
    ('N12','window','84+(120-80)','拍',F(124),'船载 117','启动'),
]

if __name__=='__main__':
    _,courses=load()
    for cid,sid,alternative,unit,expected,boundary,caption in CASES:
        c=courses[cid]; s=next(s for s in c['steps'] if s['id']==sid);q=s['question']
        assert F(q['answer'])==expected and grade(q,alternative,unit)[0],cid
        assert boundary in c['steps'][-1]['body'] and caption in s['figure'][2] and len(svg(s['figure']))>400,cid
        print(cid,s['figure'][0],expected,unit,'; transfer/limitation present')
    for cid,terms in [('B03',['不是从一个反应','数密度']),('D07',['平方和公式','趋零']),('I04',['误报','漏报']),('N12',['两份档案','月面记录为 114.0','备用校验'])]:
        text=' '.join(s['body'] for s in courses[cid]['steps'])
        assert all(t in text for t in terms),cid
    print('14 series teaching/figure fixtures plus B03, D07, I04, N12 evidence checks')
