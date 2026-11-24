"""Local only: force a SQLite write failure on disposable Rediscover state and retry unchanged."""
import argparse, sqlite3, uuid
from pathlib import Path
from urllib.parse import urlsplit
from flow import Browser

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('database',type=Path);p.add_argument('scratch',type=Path);a=p.parse_args()
    # Do not lock a deployed database. The caller must provide an independent test scratch root.
    scratch=a.scratch.resolve(strict=True); database=a.database.resolve(strict=True)
    assert scratch.parent==Path('/tmp') and scratch.name.startswith('rediscover-local.')
    assert database.parent==scratch and urlsplit(a.url).hostname=='127.0.0.1' and urlsplit(a.url).port!=8871
    a.auth_file=None
    b=Browser(a); assert len(b.view('A03')['steps'])==1
    key=uuid.uuid4().hex
    c=sqlite3.connect(database)
    try:
        c.execute('BEGIN IMMEDIATE')
        b.action('A03','sticks',answer='影子会变化',key=key,expect=503)
        assert len(b.view('A03')['steps'])==1
        assert c.execute('SELECT count(*) FROM progress').fetchone()[0]==0
    finally: c.rollback(); c.close()
    v=b.action('A03','sticks',answer='影子会变化',key=key)
    assert len(v['steps'])==2 and len(v['steps'][0]['attempts'])==1
    assert b.action('A03','sticks',answer='影子会变化',key=key)==v
    print('SQLite write failure: 503, evidence stayed locked, identical retry recorded and advanced exactly once')
