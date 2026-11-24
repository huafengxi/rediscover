"""Check the Rediscover upstream socket contract on an isolated loopback service."""
import argparse
from http.client import HTTPConnection
from http.cookies import SimpleCookie
import json
from urllib.parse import urlsplit

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', help='http://127.0.0.1:<test port>/rediscover/')
    addr = urlsplit(parser.parse_args().url)
    assert addr.scheme == 'http' and addr.hostname == '127.0.0.1' and addr.port not in (None, 8871)
    assert addr.path == '/rediscover/' and not (addr.username or addr.password or addr.query or addr.fragment)
    conn = HTTPConnection(addr.hostname, addr.port, timeout=5)
    start = '/rediscover/api/read/A03'
    try:
        conn.request('GET', start)
        response = conn.getresponse()
        assert response.status == 200 and not response.will_close
        jar = SimpleCookie(response.getheader('Set-Cookie'))
        cookie = '; '.join(m.OutputString(attrs=[]) for m in jar.values())
        course = json.loads(response.read())
        headers = {'Cookie': cookie, 'Content-Type': 'application/json', 'X-Rediscover': '1'}
        action = {'version': course['version'], 'step': course['gate']['id']}
        for expected, payload in ((200, action), (200, action), (409, {**action, 'version': 0})):
            conn.request('POST', start+'/action', json.dumps(payload), headers)
            response = conn.getresponse()
            assert response.status == expected
            assert response.getheader('Connection') == 'close', 'POST closes its upstream socket but does not notify the HTTP/1.1 pool'
            assert response.will_close
            response.read()
    finally:
        conn.close()
    print('Keep-alive GET; successful, replayed and rejected POST all signal Connection: close')
