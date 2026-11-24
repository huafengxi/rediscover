"""Build gate: read canonical texts and compile every live HTML/SVG/grade configuration."""
import collections, re, sys
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rediscover import content, mathcheck

def check():
    groups, expected = content.catalog()
    _, courses = content.load()
    assert set(courses)==set(expected) and len(courses)==140
    assert {g:count for g,(title,count) in groups.items()}==dict(collections.Counter(i[0] for i in courses))
    counts = collections.defaultdict(collections.Counter)
    prose,figures = set(),set()
    for cid,c in courses.items():
        s=c['steps']; assert c['version']>=1 and len(s)>=3 and not s[-1].get('question')
        ids = set(); predictions=set(); cc=counts[cid[0]]; cc['courses']+=1
        assert any(step.get('figure') for step in s) and any(step.get('question') for step in s)
        for a in s:
            cc['steps']+=1
            assert re.fullmatch(r'[a-z0-9-]+',a['id']) and a['id'] not in ids and a['title']
            ids.add(a['id']); assert a['body'] not in prose and len(a['body'])>=24
            prose.add(a['body']); h=content.html(a['body']); assert h
            for link in re.findall(r'href="/rediscover/([A-N]\d\d)/"',h): assert link in courses
            if 'compare' in a: assert a['compare'] in predictions
            if f:=a.get('figure'):
                decoded=content.svg(f); assert f[2] and decoded not in figures
                assert ElementTree.fromstring(decoded).tag.endswith('}svg')
                figures.add(decoded); cc['figures']+=1
            if q:=a.get('question'):
                kind=q['kind']; cc[kind]+=1; assert q['prompt']
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
    print(f'{len(courses)} courses, {len(prose)} distinct compiled steps, {len(figures)} distinct XML SVG resources')

if __name__=='__main__': check()
