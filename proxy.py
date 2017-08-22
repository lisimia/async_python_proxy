import os
import ssl
import aiohttp
from aiohttp import web
import asyncio
from subprocess import call

CHUNK_SIZE = 16


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


async def handler_https(request):
    return web.Response(text='hi from https')


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

    f = loop.create_server(web.Server(handler), "0.0.0.0", 3128)
    f2 = loop.create_server(web.Server(handler), "0.0.0.0", 3129, ssl=sc)
    f3 = loop.create_server(web.Server(web_ui), "0.0.0.0", 4100)

    try:
        loop.run_until_complete(f)
        loop.run_until_complete(f2)
        loop.run_until_complete(f3)
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    loop.close()
