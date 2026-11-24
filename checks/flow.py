"""Exercise both modes over HTTP, locally or through authenticated ingress (stdlib only)."""
import argparse, base64, collections, http.cookiejar, json, re, uuid
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
    def read(self,i): return json.loads(self.raw('api/read/'+i))
    def read_on(self,i,s,version,expect=200):
        return json.loads(self.raw(f'api/read/{i}/action',dict(step=s,version=version),expect))
    def action(self,i,s,action='submit',answer='',unit='',key=None,expect=200,version=1):
        return json.loads(self.raw('api/course/'+i+'/action',dict(key=key or uuid.uuid4().hex,action=action,step=s,version=version,answer=answer,unit=unit),expect))


def svg(b,f):
    assert f['caption'] and f['alt']
    data=b.raw(f['url']); doc=ElementTree.fromstring(data)
    assert doc.tag.endswith('}svg') and len(doc)>2
    return data


def a03_clock(b, step):
    f=step['figure']; data=svg(b,f).decode()
    assert '练习点' in data and '练习点' in f['alt']
    # This exercise varies only the time at an unrelated site; it must not give
    # the actual B noon observation away in the graphic or its text equivalents.
    assert all(x not in data+f['caption']+f['alt'] for x in ('北站','南站','12:00','7.2°','800 km'))


def private_question(q):
    assert not {'answer','example','criteria','cues','pass','partial','hint','tol','inputs','units'} & q.keys()


def a03(args):
    cid='A03'
    for prediction in ('北站会有偏差','两站没有差别',None):
        b=Browser(args); start=b.view(cid); version=start['version']
        def action(*a,**kw):return b.action(cid,*a,**kw,version=version)
        assert [s['id'] for s in start['steps']]==['setup']
        r=b.read(cid); assert [s['id'] for s in r['steps']]==['setup','sticks'] and r['gate']['id']=='observations'
        assert all(x not in json.dumps(r,ensure_ascii=False) for x in ('7.2°','800 km','40,000','10.9°'))
        a03_clock(b,r['steps'][1])
        b.raw('read-media/A03/observations.svg',expect=404)
        b.read_on(cid,'closure',version,expect=409)
        b.read_on(cid,'observations',version-1,expect=409)
        # Open reading evidence, complete the reading, then prove quiz still at the untouched start.
        r=b.read_on(cid,'observations',version); assert r==b.read_on(cid,'observations',version)==b.read(cid)
        assert len(r['steps'])==7 and r['gate']['id']=='closure' and '10.9°' not in json.dumps(r,ensure_ascii=False)
        r=b.read_on(cid,'closure',version); assert not r['gate'] and '10.9°' in r['steps'][-1]['html']
        assert r==b.read(cid) and all('attempts' not in s and 'prediction' not in s for s in r['steps'])
        assert b.view(cid)==start
        for s in r['steps']:
            if f:=s.get('figure'):
                svg(b,f); b.raw(f['url'].replace('/read-media/','/media/'),expect=404)
                Browser(args).raw(f['url'],expect=404)
        action('arc','reveal',expect=409); action('arc','hint',expect=409)
        v=action('setup','continue'); assert [s['id'] for s in v['steps']]==['setup','sticks']
        assert '7.2°' not in json.dumps(v,ensure_ascii=False)
        a03_clock(b,v['steps'][1])
        b.raw('media/A03/observations.svg',expect=404)
        k=uuid.uuid4().hex
        for _ in range(2):
            v=action('sticks',answer=prediction or '',action='submit' if prediction else 'skip',key=k)
            assert len(v['steps'])==3 and len(v['steps'][1]['attempts'])==1
        assert v==b.view(cid) and v['steps'][2]['prediction']['answer']==(prediction or '')
        assert v['steps'][2]['prediction']['skipped']==(prediction is None)
        assert b.read(cid)==r  # quiz data is not added to the article
        svg(b,v['steps'][2]['figure']); b.raw('media/A03/geometry.svg',expect=404)
        action('observations','continue'); v=action('geometry','continue'); assert len(v['steps'])==5
        q=v['steps'][-1]['question']; private_question(q)
        assert q['canHint'] and q['hints']==[] and 'solution' not in v['steps'][-1]
        k=uuid.uuid4().hex
        hint1=action('arc','hint',key=k); assert hint1==action('arc','hint',key=k)
        hint2=action('arc','hint'); step=hint2['steps'][-1]
        assert len(step['question']['hints'])==2 and not step['attempts'] and 'solution' not in step
        for ans,unit,hint in [('800/7.2','km','每度'),('7.2/360','km','比例'),('800*(7.2/360)','km','用反'),('360/7.2','km','份数'),('40000','km','数值吻合'),('800*360/7.2','m','单位'),('800*360/7.2','','单位'),('40*1000','km','原始数据'),('1/0','km','为零')]:
            v=action('arc',answer=ans,unit=unit)
            assert len(v['steps'])==5 and hint in v['steps'][-1]['attempts'][-1]['feedback'] and 'solution' not in v['steps'][-1]
        v=action('arc',answer='800 ÷ (7.2 ÷ 360)' if prediction else '800 × 360 ÷ 7.2',unit='千米')
        assert len(v['steps'])==6 and '1/50' in v['steps'][4]['solution'] and 'solution' not in v['steps'][5]
        v=action('arc',answer='1+2',unit='km'); assert len(v['steps'])==6
        assert len(action('transfer',answer='40*1000',unit='km')['steps'])==6
        v=action('transfer',answer='660*360/6',unit='km'); assert len(v['steps'])==7 and '39,600' in v['steps'][5]['solution']
        assert '10.9°' not in json.dumps(v,ensure_ascii=False) and 'solution' not in v['steps'][6]
        v=action('recheck','reveal') if prediction is None else action('recheck',answer='1200/40000*360',unit='度')
        assert len(v['steps'])==8 and '10.8' in v['steps'][6]['solution'] and '10.9°' in v['steps'][7]['html']
        v=action('closure','continue'); assert v['completed'] and v==b.view(cid)
    b=Browser(args); version=b.view(cid)['version']
    b.action(cid,'setup','continue',version=version); b.action(cid,'sticks','skip',version=version)
    assert b.read(cid)['gate']['id']=='observations'
    b.raw('read-media/A03/observations.svg',expect=404)
    print('A03: two reading gates and private media; original/skip/idempotency; progressive hints; partial/ratio/result/unit/error; equivalent expressions; independent transfer and third-station evidence; completion')


def b01(args):
    b=Browser(args); v=b.view('B01'); r=b.read('B01'); assert r['gate']['id']=='metal' and '10.30' not in json.dumps(v)
    r=b.read_on('B01','metal',r['version']); assert r['gate']['id']=='sealed' and len(r['steps'])==3
    r=b.read_on('B01','sealed',r['version']); assert r['gate'] is None and '内部转移' in r['steps'][3]['solution']
    assert b.view('B01')==v; b.raw('media/B01/sealed.svg',expect=404)
    v=b.action('B01','residue',answer='会变轻：有东西离开'); assert len(v['steps'])==2
    assert '会变轻' in v['steps'][1]['prediction']['answer']
    b.action('B01','metal','continue'); v=b.view('B01'); assert '150.00' not in json.dumps(v)
    v=b.action('B01','weigh',answer='一样'); assert len(v['steps'])==4 and '150.00' in v['steps'][-1]['html']
    v=b.action('B01','sealed',answer='我只说天平'); assert len(v['steps'])==4 and v['steps'][-1]['attempts'][-1]['feedback']
    v=b.action('B01','sealed','reveal'); assert len(v['steps'])==5 and '内部转移' in v['steps'][3]['solution']
    b.action('B01','ledger',answer='70+0.5+0.6-1.5-0.7-0.6',unit='kg')
    assert b.action('B01','audit','continue')['completed']
    print('B01 v1: legacy compare gates, sealed record, original prediction, explanation feedback/reveal, transfer, completion')


def routes(args,selected=()):
    b=Browser(args)
    data=json.loads(b.raw('api/catalog')); health=json.loads(b.raw('health')); assert health['release']==data['release']
    expected=dict(re.findall(r'^\| ([A-N]\d\d) \| (.*?) \| .*? \|$',MAP.read_text(),re.M))
    got={x['id']:x['title'] for x in data['courses']}
    assert len(expected)==len(got)==len(data['courses'])==health['courses']==140 and expected==got
    groups=collections.Counter(i[0] for i in got)
    assert dict(groups)=={g:group['count'] for g,group in data['groups'].items()}
    seen=set(); images=steps=0
    for i in selected or expected:
        for suffix in ('/','?mode=read','?mode=quiz'):
            assert b'<html lang="zh-Hans">' in b.raw(i+suffix)
        v=b.view(i); assert v['title']==expected[i] and len(v['steps'])==1 and v['total']>=3
        initial=v; r=b.read(i); assert r['title']==expected[i] and r['version']==v['version'] and r['steps']
        while r['gate']:
            before=len(r['steps']); gate=r['gate']['id']
            r=b.read_on(i,gate,r['version']); assert len(r['steps'])>before and r['steps'][before]['id']==gate
        assert len(r['steps'])==v['total'] and b.read(i)==r and b.view(i)==initial
        while not v['completed']:
            s=v['steps'][-1]; q=s.get('question'); read=r['steps'][len(v['steps'])-1]
            assert s['html'] and s['html'] not in seen,(i,s['id']); seen.add(s['html']); steps+=1
            assert {k:s[k] for k in ('id','html','title')}=={k:read[k] for k in ('id','html','title')}
            assert not any(k in read for k in ('attempts','prediction')) and 'solution' not in s
            if q:
                private_question(q)
                private_question(read['question'])
            for link in re.findall(r'href="/rediscover/([A-N]\d\d)/[^\"]*"',s['html']): assert link in got
            if s.get('figure'):
                f,rf=s['figure'],read['figure']; assert f['caption']==rf['caption'] and f['alt']==rf['alt']
                assert svg(b,f)==svg(b,rf); images+=1
            # Finishing the article must not open figures or answers in quiz mode.
            if len(v['steps']) < len(r['steps']):
                following=r['steps'][len(v['steps'])]
                if f:=following.get('figure'):
                    b.raw(f['url'].replace('/read-media/','/media/'),expect=404)
                if 'solution' in following:
                    b.action(i,following['id'],'reveal',version=v['version'],expect=409)
            action='continue' if not q else 'skip' if q['kind']=='prediction' else 'reveal'
            new=b.action(i,s['id'],action,version=v['version'])
            assert new['completed'] or len(new['steps'])==len(v['steps'])+1
            if q:
                assert all(q[k]==val for k,val in read['question'].items())
                if action=='reveal': assert new['steps'][len(v['steps'])-1]['solution']==read['solution']
            v=new
        assert any(s.get('question') for s in v['steps']) and any(s.get('figure') for s in v['steps'])
    for asset in ('app.js','style.css'): assert b.raw(asset)
    print('Two-mode routes:',len(selected or expected),'courses;',steps,'steps;',images,'identical SVG pairs;',health)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('url'); p.add_argument('--auth-file',type=Path)
    mode=p.add_mutually_exclusive_group(); mode.add_argument('--pilot',action='store_true'); mode.add_argument('--all',action='store_true'); mode.add_argument('--course',action='append',choices=re.findall(r'^\| ([A-N]\d\d) \|', MAP.read_text(),re.M))
    a=p.parse_args()
    if a.all or a.course:
        routes(a,a.course or ())
    else:
        a03(a); b01(a); routes(a,('A03','B01'))
