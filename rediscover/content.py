"""Load private Markdown manuscripts and render their private, accessible SVGs."""
import re, json
from math import cos, sin, radians
from pathlib import Path
from html import escape
from unicodedata import east_asian_width

ROOT = Path(__file__).resolve().parents[1]
ROW = re.compile(r'^\| ([A-N]\d\d) \| (.*?) \| (.*?) \|$', re.M)
GROUP = re.compile(r'^\| ([A-N]) \| (.*?) \| .*? \| (\d+) \|$', re.M)


def catalog():
    source = (ROOT/'docs/curriculum-map.md').read_text()
    rows = ROW.findall(source)
    if len(rows) != len({r[0] for r in rows}):
        raise ValueError('Duplicate IDs in curriculum map')
    groups = {g: (name,int(count)) for g,name,count in GROUP.findall(source)}
    return groups, {i: {'id':i,'title':title,'goal':goal} for i,title,goal in rows}


def load(directory=None, ids=()):
    groups, rows = catalog()
    courses = {}
    directory = directory or ROOT/'courses'
    files = [directory/(cid+'.md') for cid in ids] if ids else sorted(directory.glob('*.md'))
    for f in files:
        name = f.stem
        meta, *chunks = re.split(r'^@@ ',f.read_text(),flags=re.M)
        version = int(meta.strip().removeprefix('version: '))
        steps = []
        for chunk in chunks:
            header, body = chunk.split('\n',1)
            step = json.loads(header)
            step['body'] = body.strip()
            if not step['body']:
                raise ValueError(f'{f}: empty step')
            steps.append(step)
        courses[name] = {**rows[name], 'version':version,'steps':steps}
    return groups, courses


def reading_gate(step):
    """Stop before evidence, not after it. Legacy prediction comparisons are gates too."""
    return step.get('reading_gate') or ('看观测结果' if 'compare' in step else None)


def svg(f, cid=None):
    kind, data, caption = f[:3]
    if kind == 'diagram':
        if not re.fullmatch(r'[A-N]\d\d', cid or '') or not re.fullmatch(r'[a-z0-9-]+', data):
            raise ValueError('Invalid diagram resource name')
        directory = (ROOT/'courses'/cid).resolve()
        path = (directory/(data+'.json')).resolve()
        if directory.parent != ROOT/'courses' or path.parent != directory or path.stat().st_size > 32000:
            raise ValueError('Invalid diagram resource path or size')
        return diagram(json.loads(path.read_text()), caption)
    def e(s): return escape(str(s),quote=True)
    def label(x,y,text,anchor='middle',size=17,limit=None):
        if not str(text): return ''
        em = sum(1 if east_asian_width(c) in ('W','F') else .59 for c in str(text))
        if limit is not None: size = min(size,limit/em)
        width = em*size
        left = width if anchor=='end' else width/2 if anchor=='middle' else 0
        x = max(6+left,min(x,534-(width-left)))
        return f'<text x="{x:.2f}" y="{y}" text-anchor="{anchor}" font-size="{size:.2f}" fill="#182b34">{e(text)}</text>'
    def line(a,b,c,d,color='#397274',width=3):
        return f'<path d="M{a},{b} L{c},{d}" stroke="{color}" stroke-width="{width}" fill="none"/>'
    def point(x,y,color='#a04934'):
        return f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>'
    if kind == 'bars':
        h = 37+len(data)*49
        mx = max(abs(value) for _,value in data) or 1
        elements = line(285,14,285,h-13,'#90a7aa',1)
        for n,(name,value) in enumerate(data):
            y = 30+49*n
            x = 285 + (180 if min(v for _,v in data) >= 0 else 125)*value/mx
            elements += label(148,y+5,name,'end',16)+line(285,y,x,y,'#397274',14)+label(x+10,y+5,value,'start',15)
    elif kind == 'plot':
        # Author supplies axes labels and numbered study points; categorical diagrams use nodes.
        xname,yname,pts = data
        h = 245
        lo,hi = min(x for x,y in pts),max(x for x,y in pts)
        x0,x1 = (lo,hi) if hi-lo>0 and lo>hi-lo else (min(0,lo),max(1,hi))
        y0,y1 = min(0,*[y for x,y in pts]), max(1,*[y for x,y in pts])
        X = lambda x: 65+420*(x-x0)/(x1-x0)
        Y = lambda y: 189-135*(y-y0)/(y1-y0)
        elements = line(48,Y(0),510,Y(0),'#9eaeac',1)+line(X(max(x0,0)),24,X(max(x0,0)),199,'#9eaeac',1)+label(507,222,xname,'end')+label(15,25,yname,'start')
        for (x,y),(a,b) in zip(pts,pts[1:]): elements += line(X(x),Y(y),X(a),Y(b))
        for i,(x,y) in enumerate(pts):
            elements += point(X(x),Y(y))+label(X(x),Y(y)+(-12 if i%2==0 else 23),f'{x}, {y}',size=14)
    elif kind == 'nodes':
        nodes,edges = data
        h = 210
        elements = ''
        for a,b,name in edges:
            x,y,_ = nodes[a]; u,v,_ = nodes[b]
            elements += line(x,y,u,v)+label((x+u)/2,(y+v)/2-9,name,size=15)
        for x,y,name in nodes:
            elements += point(x,y)+label(x,y+25,name,size=17)
    elif kind == 'strips':
        h = 13+len(data)*47
        elements = ''
        for i,(name,count,filled) in enumerate(data):
            width = 343/count
            y = 10+i*47
            elements += label(139,y+23,name,'end')
            for j in range(count):
                fill = '#397274' if j<filled else '#dae8e2'
                elements += f'<rect x="{156+j*width}" y="{y}" width="{width-1}" height="32" fill="{fill}" stroke="#446966"/>'
    elif kind == 'grid':
        h = 28+len(data)*35
        elements = ''
        for i,row in enumerate(data):
            width = 500/len(row)
            for j,name in enumerate(row):
                x,y = 20+j*width,10+i*35
                elements += f'<rect x="{x}" y="{y}" width="{width-2}" height="33" rx="3" fill="{"#c3dbd6" if i%2==0 else "#e2ece8"}"/>'+label(x+width/2,y+23,name,size=16,limit=width-12)
    else:
        raise ValueError(f'Invalid figure kind {kind}')
    return f'<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 540 {h}" font-family="system-ui,sans-serif"><title>{e(caption)}</title><rect width="540" height="{h}" rx="8" fill="#edf4f0"/>{elements}</svg>'.encode()


def diagram(spec, caption):
    """Numeric drawing primitives only: never serve author-provided SVG markup."""
    width = 400
    height, commands = spec['height'], spec['draw']
    if set(spec) != {'height','draw'} or type(height) is not int or not 100 <= height <= 480:
        raise ValueError('Invalid diagram dimensions')
    if not isinstance(commands,list) or not 1 <= len(commands) <= 200:
        raise ValueError('Invalid diagram command count')
    palette = {
        'ink': ('#263b44', 2, ''), 'light': ('#885719', 2, ''),
        'guide': ('#506563', 2, '5 4'), 'measure': ('#9c402c', 4, ''),
        'surface': ('#176664', 3, ''), 'circle': ('#506563', 2, ''),
    }
    def number(v, lo=0, hi=480):
        if type(v) not in (int,float) or not lo <= v <= hi:
            raise ValueError(f'Diagram number outside [{lo}, {hi}]')
        return round(v, 3)
    def coord(x,y): return number(x,0,width), number(y,0,height)
    def style(name):
        color,weight,dash = palette[name]
        return f'stroke="{color}" stroke-width="{weight}" stroke-dasharray="{dash or "none"}" stroke-linecap="round" fill="none"'
    elements = []
    for cmd in commands:
        match cmd:
            case ['line',x,y,u,v,ink]:
                x,y = coord(x,y); u,v = coord(u,v)
                elements.append(f'<path d="M{x},{y} L{u},{v}" {style(ink)}/>')
            case ['circle',x,y,r,ink]:
                x,y = coord(x,y); r = number(r,1,min(x,y,width-x,height-y))
                elements.append(f'<circle cx="{x}" cy="{y}" r="{r}" {style(ink)}/>')
            case ['arc',x,y,r,a,b,ink]:
                x,y = coord(x,y); r = number(r,1,width)
                a,b = number(a,-360,360),number(b,-360,360)
                if not 0 < b-a < 360: raise ValueError('Invalid arc span')
                def endpoint(angle):
                    u,v = coord(x+r*cos(radians(angle)),y+r*sin(radians(angle)))
                    return f'{u},{v}'
                elements.append(f'<path d="M{endpoint(a)} A{r},{r} 0 {int(b-a>180)} 1 {endpoint(b)}" {style(ink)}/>')
            case ['dot',x,y]:
                x,y = coord(x,y)
                elements.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="#263b44"/>')
            case ['label',x,y,str(label),('start' | 'middle' | 'end') as anchor] if 0 < len(label) <= 52:
                x,y = coord(x,y)
                elements.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="#182b34">{escape(label)}</text>')
            case _: raise ValueError('Invalid diagram command')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 {width} {height}" '
            f'font-family="system-ui,sans-serif" font-size="17"><title>{escape(caption)}</title>'
            f'<rect width="{width}" height="{height}" rx="8" fill="#edf4f0"/>{"".join(elements)}</svg>').encode()


def html(body):
    """Deliberately small Markdown subset; no raw HTML, links only to courses and HTTPS citations."""
    def inline(s):
        def replace(m):
            title, url = m.groups()
            if re.fullmatch(r'/rediscover/[A-N]\d\d/(?:\?mode=(?:read|quiz))?|https://[A-Za-z0-9./#?%_~=&:+-]+',url):
                return f'<a href="{escape(url,quote=True)}">{escape(title)}</a>'
            raise ValueError(f'Unsupported Markdown link: {url}')
        result = []; start = 0
        for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)',s):
            result += [escape(s[start:m.start()]),replace(m)]; start = m.end()
        result.append(escape(s[start:]))
        return re.sub(r'`([^`]+)`',r'<code>\1</code>',re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',''.join(result)))
    blocks = []
    for p in body.split('\n\n'):
        if p.startswith('### '): blocks.append('<h3>'+inline(p[4:])+'</h3>')
        elif p.startswith('> '): blocks.append('<blockquote>'+inline(p[2:])+'</blockquote>')
        else: blocks.append('<p>'+inline(p.replace('\n',' '))+'</p>')
    return ''.join(blocks)
