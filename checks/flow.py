"""Re-run the same HTTP assertions locally or at authenticated dev ingress (stdlib only)."""
import argparse, base64, collections, http.cookiejar, json, os, re, sys, uuid
import urllib.error, urllib.parse, urllib.request
from pathlib import Path
from xml.etree import ElementTree

MAP = Path(__file__).resolve().parents[1]/'docs/curriculum-map.md'

class Browser:
    def __init__(self,args):
        self.base=args.url.rstrip('/')+'/'
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),urllib.request.ProxyHandler({}))
        self.headers = {}
        if args.auth_file:
            self.headers['Authorization']='Basic '+base64.b64encode(args.auth_file.read_bytes().strip()).decode()
    def raw(self,path,payload=None,expect=200):
        url=urllib.parse.urljoin(self.base,path)
        assert urllib.parse.urlsplit(url).netloc==urllib.parse.urlsplit(self.base).netloc
        headers = dict(self.headers)
        if payload is not None: headers.update({'Content-Type':'application/json','X-Rediscover':'1'})
        req=urllib.request.Request(url, None if payload is None else json.dumps(payload).encode(),headers)
        try: r=self.opener.open(req,timeout=20)
        except urllib.error.HTTPError as e: r=e
        with r:
            assert r.status==expect,(path,r.status,expect)
            return r.read()
    def view(self,i): return json.loads(self.raw('api/course/'+i))
    def action(self,i,s,action='submit',answer='',unit='',key=None,expect=200,version=1):
        return json.loads(self.raw('api/course/'+i+'/action',dict(key=key or uuid.uuid4().hex,action=action,step=s,version=version,answer=answer,unit=unit),expect))


def pilot(args):
    for prediction in ('影子角度增大','影子不变',None):
        b=Browser(args); assert len(b.view('A03')['steps'])==1
        assert b.view('A03')['steps'][0]['title']=='两个中午'
        assert b.raw('media/A03/arc.svg',expect=404)
        b.action('A03','arc',action='reveal',expect=409)
        k=uuid.uuid4().hex
        for _ in range(2):
            v=b.action('A03','sticks',answer=prediction or '',action='submit' if prediction else 'skip',key=k)
            assert len(v['steps'])==2 and len(v['steps'][0]['attempts'])==1
        assert v==b.view('A03') and v['steps'][1]['prediction']['answer']==(prediction or '')
        assert v['steps'][1]['prediction']['skipped']==(prediction is None)
        assert 'solution' not in v['steps'][1]
        ElementTree.fromstring(b.raw('media/A03/arc.svg'))
        for ans,unit,hint in [('800/7.2','km','每度'),('40000','km','数值吻合'),('800*360/7.2','m','单位'),('800+7.2','km','比例'),('1/0','km','为零')]:
            v=b.action('A03','arc',answer=ans,unit=unit)
            assert len(v['steps'])==2 and hint in v['steps'][1]['attempts'][-1]['feedback']
        v=b.action('A03','arc',answer='800 ÷ (7.2 ÷ 360)' if prediction else '800 × 360 ÷ 7.2',unit='km')
        assert len(v['steps'])==3
        v=b.action('A03','arc',answer='1+2',unit='km');assert len(v['steps'])==3
        v=b.action('A03','recheck','reveal');assert len(v['steps'])==4 and '10.8' in v['steps'][2]['solution']
        v=b.action('A03','closure','continue');assert v['completed'] and v==b.view('A03')
    b=Browser(args); v=b.view('B01'); assert '10.30' not in json.dumps(v)
    v=b.action('B01','residue',answer='会变轻：有东西离开');assert len(v['steps'])==2
    assert '会变轻' in v['steps'][1]['prediction']['answer']
    b.action('B01','metal','continue'); v=b.view('B01'); assert '150.00' not in json.dumps(v)
    v=b.action('B01','weigh',answer='一样');assert len(v['steps'])==4 and '150.00' in v['steps'][-1]['html']
    v=b.action('B01','sealed',answer='我只说天平'); assert len(v['steps'])==4 and v['steps'][-1]['attempts'][-1]['feedback']
    v=b.action('B01','sealed','reveal');assert len(v['steps'])==5 and '内部转移' in v['steps'][3]['solution']
    b.action('B01','ledger',answer='70+0.5+0.6-1.5-0.7-0.6',unit='kg')
    assert b.action('B01','audit','continue')['completed']
    print('A03/B01: 3 prediction paths, original, hidden evidence/media, idempotency, refresh, equivalent math, partial/result/unit/error, old-step repeat, reveal, explanation fallback/feedback, transfer, completion')


def all_courses(args):
    b=Browser(args)
    data=json.loads(b.raw('api/catalog')); health=json.loads(b.raw('health')); assert health['release']==data['release']
    expected=dict(re.findall(r'^\| ([A-N]\d\d) \| (.*?) \| .*? \|$',MAP.read_text(),re.M))
    got={x['id']:x['title'] for x in data['courses']}
    assert len(expected)==len(got)==len(data['courses'])==health['courses']==140 and expected==got
    groups=collections.Counter(id[0] for id in got)
    assert dict(groups)=={g:group['count'] for g,group in data['groups'].items()}
    seen=set(); images=0; steps=0
    for i in expected:
        assert b'<html lang="zh-Hans">' in b.raw(i+'/')
        v=b.view(i); assert v['title']==expected[i] and len(v['steps'])==1 and v['total']>=3
        while not v['completed']:
            s=v['steps'][-1]; q=s.get('question'); key=uuid.uuid4().hex
            assert s['html'] and s['html'] not in seen,(i,s['id']); seen.add(s['html']); steps+=1
            for link in re.findall(r'href="/rediscover/([A-N]\d\d)/"',s['html']): assert link in got
            if s.get('figure'):
                f=s['figure']; assert f['caption']
                svg=ElementTree.fromstring(b.raw(f['url'])); assert svg.tag.endswith('}svg') and len(svg)>2; images+=1
            action='continue' if not q else 'skip' if q['kind']=='prediction' else 'reveal'
            new=b.action(i,s['id'],action,version=v['version'],key=key)
            assert new['completed'] or len(new['steps'])==len(v['steps'])+1
            v=new
        assert any(s.get('question') for s in v['steps']) and any(s.get('figure') for s in v['steps'])
    for asset in ('app.js','style.css'): assert b.raw(asset)
    print('Counts:',dict(groups),'steps:',steps,'SVG:',images,'release:',health['release'],'AI configured:',health['ai'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('--auth-file',type=Path);p.add_argument('--pilot',action='store_true');p.add_argument('--all',action='store_true');a=p.parse_args()
    pilot(a)
    if a.all: all_courses(a)
