"""Build gate: read canonical texts and compile every live HTML/SVG/grade configuration."""
import argparse, collections, re, sys
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rediscover import content, mathcheck

def check(ids=(), reading_standard=False):
    groups, expected = content.catalog()
    inventory = {p.stem for p in (content.ROOT/'courses').glob('*.md')}
    assert inventory==set(expected) and len(inventory)==140
    assert {g:count for g,(title,count) in groups.items()}==dict(collections.Counter(i[0] for i in inventory))
    _, courses = content.load(ids=ids)
    counts = collections.defaultdict(collections.Counter)
    prose,figures = set(),set()
    selected = ids or courses
    for cid in selected:
        c=courses[cid]; s=c['steps']
        assert c['version']>=1 and len(s)>=3 and not s[-1].get('question')
        assert content.reading_gate(s[0]) is None, (cid,'opening cannot be gated')
        if reading_standard:
            assert sum(len(step.get('figure_panels',[])) or 1 for step in s if 'figure' in step)>=2, (cid,'need two figures or independently useful panels')
        ids = set(); predictions=set(); cc=counts[cid[0]]; cc['courses']+=1
        assert any(step.get('figure') for step in s) and any(step.get('question') for step in s)
        for a in s:
            cc['steps']+=1
            assert re.fullmatch(r'[a-z0-9-]+',a['id']) and a['id'] not in ids and a['title']
            ids.add(a['id']); assert a['body'] not in prose and len(a['body'])>=24
            prose.add(a['body']); h=content.html(a['body']); assert h
            for link in re.findall(r'href="/rediscover/([A-N]\d\d)/[^\"]*"',h): assert link in inventory
            if 'compare' in a: assert a['compare'] in predictions
            if 'reading_gate' in a:
                assert isinstance(a['reading_gate'],str) and 1<=len(a['reading_gate'].strip())<=40
            if a.get('solution_on_pass'):
                assert a.get('solution') and a['question']['kind'] in ('expression','explanation')
            if 'figure_panels' in a:
                panels=a['figure_panels']
                assert 'figure' in a and isinstance(panels,list) and len(panels)>=2
                assert all(isinstance(p,str) and p.strip() for p in panels) and len(set(panels))==len(panels)
            if f:=a.get('figure'):
                assert len(f) in (3,4) and (len(f)==4 or f[0]!='diagram')
                decoded=content.svg(f,cid); assert len(f[2])>=16 and decoded not in figures
                if len(f)==4: assert len(f[3].strip())>=12
                if f[0]=='grid': assert len({len(row) for row in f[1]})==1, (cid,a['id'])
                assert ElementTree.fromstring(decoded).tag.endswith('}svg')
                figures.add(decoded); cc['figures']+=1
            if q:=a.get('question'):
                kind=q['kind']; cc[kind]+=1; assert q['prompt']
                if 'hints' in q:
                    assert kind!='prediction' and isinstance(q['hints'],list) and 1<=len(q['hints'])<=8
                    assert all(isinstance(h,str) and h.strip() for h in q['hints'])
                if kind=='prediction': predictions.add(a['id']); assert 'solution' not in a; continue
                assert a['solution'] and content.html(a['solution']) and q['hint'] and q['pass']
                if kind=='explanation':
                    assert q['criteria'] and len(q['criteria'])==len(q['cues']) and all(q['criteria']) and all(q['cues'])
                elif kind=='expression':
                    assert (not q.get('units')) == ('unit' not in q)
                    x=q['example']; u=q.get('unit','')
                    assert mathcheck.grade(q,x,u)[0],(cid,a['id'],x,u)
                    assert not mathcheck.grade(q,'0/0',u)[0]
                    if u: assert not mathcheck.grade(q,x,'bad unit')[0]
                else: raise ValueError(kind)
        assert predictions=={a['compare'] for a in s if 'compare' in a}
    for g,c in counts.items(): print(g, ', '.join(f'{k}={v}' for k,v in c.items()))
    print(f'{len(selected)} courses, {len(prose)} distinct compiled steps, {len(figures)} distinct XML SVG resources')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--course',action='append',choices=content.catalog()[1],help='repeat to limit compilation (default: all)')
    p.add_argument('--reading-standard',action='store_true',help='opt into the migrated-manuscript figure floor')
    a=p.parse_args(); check(dict.fromkeys(a.course or ()),a.reading_standard)
