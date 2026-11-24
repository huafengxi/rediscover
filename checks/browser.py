"""Drive Chromium over CDP at real desktop/mobile viewport sizes without WebDriver downloads."""
import argparse, base64, json, os, re, subprocess, time, urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape
from websocket import create_connection

class CDP:
    def __init__(self,port):
        targets=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=4))
        self.ws=create_connection(next(t['webSocketDebuggerUrl'] for t in targets if t['type']=='page'),timeout=30,suppress_origin=True)
        self.serial=0; self.credentials=None; self.auth_attempted=set()
    def call(self,method,**params):
        self.serial+=1
        self.ws.send(json.dumps(dict(id=self.serial,method=method,params=params)))
        return self.serial
    def send(self,method,**params):
        i=self.call(method,**params)
        while True:
            result=json.loads(self.ws.recv())
            if result.get('id')==i:
                if 'error' in result: raise RuntimeError(result['error'])
                return result['result']
            e=result.get('params',{}); event=result.get('method')
            if event=='Fetch.requestPaused':
                self.call('Fetch.continueRequest',requestId=e['requestId'])
            if event=='Fetch.authRequired':
                user,password,origin=self.credentials
                rid=e['requestId']; challenge=e.get('authChallenge',{})
                ok=(rid not in self.auth_attempted and challenge.get('source')=='Server' and challenge.get('origin')==origin and challenge.get('scheme','').lower()=='basic')
                self.auth_attempted.add(rid)
                self.call('Fetch.continueWithAuth',requestId=rid,authChallengeResponse={'response':'ProvideCredentials','username':user,'password':password} if ok else {'response':'CancelAuth'})
    def js(self,expression):
        r=self.send('Runtime.evaluate',expression=expression,returnByValue=True,awaitPromise=True)
        if 'exceptionDetails' in r: raise RuntimeError('Browser evaluation failed: '+expression)
        return r['result'].get('value')
    def wait(self,expression,seconds=23):
        start=time.monotonic()
        while time.monotonic()-start<seconds:
            if self.js(expression): return
            time.sleep(.1)
        raise AssertionError(f'Browser timed out on {expression}')
    def click(self,caption):
        self.wait(f'[...document.querySelectorAll("button")].some(x=>x.textContent==={json.dumps(caption)}&&!x.disabled)')
        self.js(f'[...document.querySelectorAll("button")].find(x=>x.textContent==={json.dumps(caption)}&&!x.disabled).click()')
    def fill(self,text,unit=None):
        self.wait('!!document.querySelector("#response")')
        self.js(f'document.querySelector("#response").value={json.dumps(text)}')
        if unit is not None: self.js(f'document.querySelector("#unit").value={json.dumps(unit)}')
    def steps(self,n): self.wait(f'document.querySelectorAll("article.step").length==={n}')
    def text(self,s): self.wait('document.body.innerText.includes('+json.dumps(s)+')')
    def images(self): self.wait('[...document.images].length > 0 && [...document.images].every(i=>i.complete && i.naturalWidth>0 && i.alt.length>0)')
    def screenshot(self,path): path.write_bytes(base64.b64decode(self.send('Page.captureScreenshot',format='png')['data']))
    def no_overflow(self): assert self.js('document.documentElement.scrollWidth <= innerWidth')
    def completed(self): self.text('本关已完成')
    def offline(self,flag): self.send('Network.emulateNetworkConditions',offline=flag,latency=0,downloadThroughput=-1,uploadThroughput=-1)

def reading(c,args,device):
    c.wait('document.querySelector(".mode-nav [aria-current]")?.textContent==="阅读模式"')
    c.wait('document.querySelectorAll(".reading .read-step").length===2'); c.images(); c.no_overflow()
    assert c.js('!document.querySelector("form,#observations,#closure") && document.images.length===1')
    c.text('如果不能绕行星走一圈'); c.text('先排除一个会骗人的差别')
    c.screenshot(args.output/f'{device}-a03-opening.png')
    c.js('document.querySelector("#sticks figure").scrollIntoView({block:"center"})')
    c.screenshot(args.output/f'{device}-a03-clock.png')
    c.click('看两站记录'); c.text('短弧怎样换成整圈'); c.text('1/50'); c.text('39,600'); c.images()
    assert c.js('document.images.length===4 && !document.body.innerText.includes("10.9°") && !document.querySelector("form")')
    for sid in ('observations','geometry','arc'):
        c.js(f'document.querySelector("#{sid} figure").scrollIntoView({{block:"center"}})')
        c.screenshot(args.output/f'{device}-a03-{sid}.png')
    c.click('看第三站的读数'); c.text('10.9° ± 0.2°'); c.text('用第三张记录检验估计'); c.no_overflow()
    c.js('document.getElementById("closure").scrollIntoView()')
    c.screenshot(args.output/f'{device}-a03-conclusion.png')
    assert c.js('!document.querySelector("form, .reading-gate, .answer")')


def exercise(c,args):
    base=args.url.rstrip('/')+'/'
    c.send('Network.enable'); c.send('Network.setCacheDisabled',cacheDisabled=True); c.send('Page.enable'); c.send('DOM.enable')
    if args.auth_file:
        user,password=args.auth_file.read_text().strip().split(':',1)
        u=urlsplit(base)
        c.credentials=(user,password,u.scheme+'://'+u.netloc)
        c.send('Fetch.enable',patterns=[{'urlPattern':base+'*'}],handleAuthRequests=True)
    c.send('Emulation.setDeviceMetricsOverride',width=1366,height=900,deviceScaleFactor=1,mobile=False)
    def page(s):
        c.send('Page.navigate',url=base+s); c.wait('location.href==='+json.dumps(base+s))
    def mode(label):
        c.js('[...document.querySelectorAll(".mode-nav a")].find(x=>x.textContent==='+json.dumps(label)+').click()')
        c.wait('document.querySelector(".mode-nav [aria-current]")?.textContent==='+json.dumps(label))
    def reload():
        c.js('window.__beforeReload=true'); c.send('Page.reload'); c.wait('!window.__beforeReload')
    page('')
    # Chromium has accepted/cached the BasicAuth challenge for this origin; resume normal network I/O.
    if args.auth_file: c.send('Fetch.disable')
    c.wait('document.querySelectorAll(".list a").length===140'); c.no_overflow()
    c.screenshot(args.output/'desktop-catalog.png')
    c.js('document.querySelector(\'.list a[href="/rediscover/A03/"]\').click()'); reading(c,args,'desktop')
    read_y=c.js('scrollY'); assert read_y>300
    mode('答题模式'); c.steps(1)
    assert c.js('!document.querySelector("#observations,#arc,#closure,form textarea") && !document.images.length')
    c.click('继续'); c.steps(2); c.images()
    c.fill('北边影子增加'); c.offline(True); c.click('提交'); c.text('连接中断'); c.steps(2)
    assert c.js('document.querySelector("#response").value')=='北边影子增加'
    c.offline(False); c.click('提交'); c.steps(3); c.text('我当时写下：北边影子增加'); c.images()
    mode('阅读模式'); c.wait(f'Math.abs(scrollY-{read_y})<8'); c.text('用第三张记录检验估计')
    assert c.js('!document.querySelector(".answer,form")')
    reload(); c.wait(f'Math.abs(scrollY-{read_y})<8'); c.text('10.9° ± 0.2°')
    mode('答题模式'); c.steps(3); c.text('我当时写下：北边影子增加')
    assert c.js('!document.querySelector("#arc,#closure")')
    c.click('继续'); c.steps(4); c.click('继续'); c.steps(5)
    c.fill('800/7.2','km'); c.click('查看提示'); c.text('C 所对应的是哪一个角'); c.steps(5)
    assert c.js('document.querySelector("#response").value')=='800/7.2'
    c.click('下一条提示'); c.text('整圈未知'); c.click('提交'); c.text('每度对应的距离'); c.steps(5)
    reload(); c.steps(5); c.text('每度对应的距离'); c.text('整圈未知')
    assert c.js('!document.querySelector(".solution,#transfer")')
    if args.audio:
        audio=str(args.audio.resolve())
        current='fetch("/rediscover/api/course/A03").then(r=>r.json())'
        before=c.js(current)
        c.wait('!!document.querySelector("#voice-file")')
        node=c.send('DOM.querySelector',nodeId=c.send('DOM.getDocument')['root']['nodeId'],selector='#voice-file')['nodeId']
        c.send('DOM.setFileInputFiles',files=[audio],nodeId=node)
        c.text('请核对并修改转写'); assert re.search('[\u3400-\u9fff]{2,}',c.js('document.querySelector("#response").value'))
        assert c.js(current)==before
        c.screenshot(args.output/'desktop-editable-voice.png')
    c.fill('800 × 360 ÷ 7.2','km'); c.click('提交'); c.steps(6); c.text('1/50')
    c.screenshot(args.output/'desktop-quiz-derivation.png')
    c.fill('660/(6/360)','km'); c.click('提交'); c.steps(7); c.text('39,600 km')
    assert c.js('!document.body.innerText.includes("10.9°")')
    c.click('查看推导'); c.steps(8); c.text('10.8°'); c.text('10.9° ± 0.2°'); c.click('完成本关'); c.completed(); c.no_overflow()
    print('Desktop 1366×900: A03 catalog/default reading, both gates/four figures/full derivation, exact scroll resume/switch, fresh quiz, original prediction, offline retry, two hints/partial, voice draft + edit (%s), equivalent math/transfer, gated recheck and completion'%bool(args.audio),flush=True)
    page('B01/?mode=quiz'); c.steps(1); c.fill('只要释放东西就一定变轻'); c.click('提交'); c.steps(2); c.images()
    c.click('继续'); c.steps(3); c.click('暂时想不出'); c.steps(4); c.text('已略过'); c.images()
    c.fill('我只说天平'); c.click('提交'); c.text('先说清楚 150.00 g'); c.steps(4)
    if args.ai:
        c.fill('同一封闭装置（容器、空气、金属）整体前后均为 150.00 g，在 ±0.02 g 测量精度内不变；金属增加 0.30 g，说明其他部分共少约 0.30 g 的内部转移是合理推论，不是直接测量。'); c.click('提交'); c.steps(5)
        c.text('你把测量范围固定了'); c.js('document.getElementById("sealed").scrollIntoView()'); c.screenshot(args.output/'desktop-b01-rubric.png')
    else: c.click('查看作者解释'); c.steps(5)
    c.fill('70+0.5+0.6-1.5-0.7-0.6','kg'); c.click('提交'); c.steps(6); c.click('完成本关'); c.completed(); c.no_overflow()
    print('Desktop: B01 original/skip, sealed mass, rubric feedback, transfer and completion',flush=True)
    c.send('Emulation.setDeviceMetricsOverride',width=390,height=844,deviceScaleFactor=2,mobile=True)
    c.send('Emulation.setTouchEmulationEnabled',enabled=True,maxTouchPoints=1)
    c.js('sessionStorage.clear()'); c.send('Network.clearBrowserCookies')
    page('A03/'); reading(c,args,'mobile'); mode('答题模式'); c.steps(1); c.click('继续'); c.steps(2)
    c.click('暂时想不出'); c.steps(3); c.text('已略过'); c.images(); c.no_overflow()
    print('Mobile 390×844 touch: A03 uninterrupted reading between evidence gates, four diagrams, formulas, conclusion, and fresh quiz skip',flush=True)
    page('A18/?mode=quiz'); c.steps(1); c.fill('偏东'); c.click('提交'); c.steps(2); c.images(); c.no_overflow()
    c.js('document.querySelector("#evidence figure").scrollIntoView({block:"center"})'); c.screenshot(args.output/'mobile-a18-evidence.png')
    c.fill('(12-10)*360/24','°'); c.click('提交'); c.steps(3); c.text('东 30.5°'); c.click('完成本关'); c.completed()
    c.js('window.scrollTo(0,0)'); c.screenshot(args.output/'mobile-a18.png')
    page('N12/?mode=quiz'); c.steps(1); c.click('暂时想不出'); c.steps(2); c.images(); c.no_overflow()
    c.fill('110+(84-80)','拍'); c.click('提交'); c.steps(3)
    if args.ai:
        c.fill('选甲档。114−4＝110，对得上；112不符合。'); c.click('提交'); c.steps(4)
        c.text('你用留出的脉冲区分了残档')
    else: c.click('查看作者解释'); c.steps(4)
    c.fill('120+(84-80)','拍'); c.click('提交'); c.steps(5); c.click('完成本关'); c.completed(); c.images(); c.no_overflow()
    c.js('document.getElementById("home").scrollIntoView()'); c.screenshot(args.output/'mobile-n12.png')
    print('Mobile: 390×844 with touch, A18 clock correction, N12 independent signal and return window, SVG loaded and no horizontal overflow',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('url'); p.add_argument('--chrome',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--auth-file',type=Path);p.add_argument('--audio',type=Path);p.add_argument('--fonts',type=Path);p.add_argument('--ai',action='store_true');p.add_argument('--no-sandbox',action='store_true');a=p.parse_args()
    a.profile.mkdir(mode=0o700); a.output.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'TMPDIR':str(a.profile)}
    if a.fonts:
        fonts=a.profile/'fontconfig.xml'
        fonts.write_text(f'<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig><include>/etc/fonts/fonts.conf</include><dir>{escape(str(a.fonts.resolve()))}</dir><cachedir>{escape(str(a.profile/"fonts-cache"))}</cachedir></fontconfig>')
        env['FONTCONFIG_FILE']=str(fonts)
    with (a.output/'chromium.log').open('wb') as log:
        proc = subprocess.Popen([str(a.chrome),'--headless','--disable-gpu','--no-first-run','--disable-background-networking','--disable-sync','--no-proxy-server','--remote-debugging-port=0',f'--user-data-dir={a.profile}',*(['--no-sandbox'] if a.no_sandbox else []),'about:blank'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        try:
            ready=a.profile/'DevToolsActivePort'; deadline=time.monotonic()+12
            while not ready.exists():
                assert proc.poll() is None and time.monotonic()<deadline,'Chromium did not start'
                time.sleep(.1)
            exercise(CDP(int(ready.read_text().splitlines()[0])),a)
        finally:
            proc.terminate(); proc.wait(timeout=12)
