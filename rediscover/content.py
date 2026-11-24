"""Load private Markdown manuscripts and render their private, accessible SVGs."""
import re, json
from pathlib import Path
from html import escape

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


def load(directory=None):
    groups, rows = catalog()
    courses = {}
    for f in sorted((directory or ROOT/'courses').glob('*.md')):
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


def svg(f):
    kind, data, caption = f
    def e(s): return escape(str(s),quote=True)
    def label(x,y,text,anchor='middle',size=17):
        return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" fill="#182b34">{e(text)}</text>'
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
        x0,x1 = min(0,*[x for x,y in pts]), max(1,*[x for x,y in pts])
        y0,y1 = min(0,*[y for x,y in pts]), max(1,*[y for x,y in pts])
        X = lambda x: 65+420*(x-x0)/(x1-x0)
        Y = lambda y: 189-135*(y-y0)/(y1-y0)
        elements = line(48,Y(0),510,Y(0),'#9eaeac',1)+line(X(0),24,X(0),199,'#9eaeac',1)+label(507,222,xname,'end')+label(15,25,yname,'start')
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
    elif kind == 'grid':
        h = 28+len(data)*35
        elements = ''
        for i,row in enumerate(data):
            width = 500/len(row)
            for j,name in enumerate(row):
                x,y = 20+j*width,10+i*35
                elements += f'<rect x="{x}" y="{y}" width="{width-2}" height="33" rx="3" fill="{"#c3dbd6" if i%2==0 else "#e2ece8"}"/>'+label(x+width/2,y+23,name,size=16)
    else:
        raise ValueError(f'Invalid figure kind {kind}')
    return f'<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 540 {h}" font-family="system-ui,sans-serif"><title>{e(caption)}</title><rect width="540" height="{h}" rx="8" fill="#edf4f0"/>{elements}</svg>'.encode()


def html(body):
    """Deliberately small Markdown subset; no raw HTML, links only to courses and HTTPS citations."""
    def inline(s):
        def replace(m):
            title, url = m.groups()
            if re.fullmatch(r'/rediscover/[A-N]\d\d/|https://[A-Za-z0-9./#?%_~=&:+-]+',url):
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
