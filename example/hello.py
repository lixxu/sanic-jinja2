#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sanic import Sanic
from sanic_session import InMemorySessionInterface
from sanic_jinja2 import SanicJinja2

app = Sanic()

jinja = SanicJinja2(app)
session = InMemorySessionInterface(cookie_name=app.name, prefix=app.name)


@app.middleware('request')
async def add_session_to_request(request):
    # before each request initialize a session
    # using the client's request
    await session.open(request)


@app.middleware('response')
async def save_session(request, response):
    # after each request save the session,
    # pass the response to set client cookies
    await session.save(request, response)


@app.route('/')
async def index(request):
    jinja.flash('success message', 'success')
    jinja.flash('info message', 'info')
    jinja.flash('warning message', 'warning')
    jinja.flash('error message', 'error')
    return await jinja.render('index.html', greetings='Hello, sanic!')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
