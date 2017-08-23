import os
import ssl
import aiohttp
from aiohttp import web
import asyncio
from subprocess import call

CHUNK_SIZE = 16


# HTTP forwarding
async def handler(request):
    print('req', request)
    print('url', request.url)
    print('method', request.method)
    print('v', request.version)
    print('path', request.path)
    print('scheme', request.scheme)
    print('host', request.host)

    print('headers', request.headers)

    # NOT ENOUGH IS PASSED AROUND
    # SESSION SHOULD BE SAVED FOR LONGER
    async with aiohttp.request(
        request.method,
        request.scheme + '://' + request.host + request.path,
        # params=request.params,
        # DATA
        headers=request.headers,
        allow_redirects=False,
        skip_auto_headers=['Accept', 'Accept-Encoding', 'Host', 'User-Agent']
        # Hardcode this list because aiohttp doesn't give an easy way for this
        # https://github.com/aio-libs/aiohttp/blob/bb646d143cc7bd3b1a614d7c101957b56b11a67f/aiohttp/client_reqrep.py#L163
    ) as resp:
        print(resp)
        # MORE LOGGING

        my_resp = web.StreamResponse(
            status=resp.status,
            headers=resp.headers
        )
        await my_resp.prepare(request)

        d = await resp.content.read(CHUNK_SIZE)
        while d:
            my_resp.write(d)
            await my_resp.drain()
            d = await resp.content.read(CHUNK_SIZE)
        my_resp.write_eof()
        return my_resp

# HTTPS
async def h2(client_reader, client_writer):
    print('hi!')
    line = await client_reader.readline()
    if b'CONNECT' in line:
        await https(line, client_reader, client_writer)
    else:
        print("BAD USAGE, this is for CONNECT only")


async def https(line, client_reader, client_writer):
    print(line)
    while line.strip():
        line = await client_reader.readline()
        print(line)
    client_writer.write(b'HTTP/1.1 200 OK\r\n\r\n')
    await client_writer.drain()

    s_r, s_w = await asyncio.open_connection(host='127.0.0.1', port=3129)
    print ("connection made")

    loop = asyncio.get_event_loop()
    t1 = loop.create_task(weld(client_reader, s_w))
    t2 = loop.create_task(weld(s_r, client_writer))

# HACK because asyncio doesn't support this yet
async def weld(i, o):
    while True:
        d = await i.read(1)
        o.write(d)
# END HTTPS

async def web_ui(request):
    return web.Response(text='hi im the webui')

def create_cert():
    call([
        'openssl',
        'req',
        '-x509', '-nodes', '-batch',
        '-newkey', 'rsa:4096',
        '-keyout', 'key.pem',
        '-out' ,'cert.pem',
        '-days', '365'
    ])


if __name__ == '__main__':
    cert_here = os.path.exists('cert.pem') and os.path.exists('key.pem')
    if not cert_here:
        create_cert()
    sc = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    sc.load_cert_chain('cert.pem', 'key.pem')

    # TODO auto add root CA to OS

    loop = asyncio.get_event_loop()
    
    # for http
    f = loop.create_server(web.Server(handler), "0.0.0.0", 3128)

    # for https 
    f4 = asyncio.start_server(h2, "0.0.0.0", 3126, loop=loop)

    # used as a hack
    f2 = loop.create_server(web.Server(handler), "127.0.0.1", 3129, ssl=sc)

    # used for UI
    f3 = loop.create_server(web.Server(web_ui), "0.0.0.0", 4100)

    try:
        loop.run_until_complete(f)
        loop.run_until_complete(f2)
        loop.run_until_complete(f3)
        loop.run_until_complete(f4)
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    loop.close()
