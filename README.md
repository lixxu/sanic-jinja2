# sanic-jinja2
Jinja2 support for sanic

![Example](https://github.com/lixxu/sanic-jinja2/blob/master/example/example.png)

## Installation

`pip install sanic-jinja2`


## Usage

```
NOTICE:
If you want to use flash and get_flashed_messages, you need setup session first

Currently, app and request are hooked into jinja templates, thus you can use them in template directly.
```


```python

    #!/usr/bin/env python
    # -*- coding: utf-8 -*-

    from sanic import Sanic
    from sanic_session import InMemorySessionInterface
    from sanic_jinja2 import SanicJinja2

    app = Sanic()

    jinja = SanicJinja2(app)
    # or setup later
    # jinja = SanicJinja2()
    # jinja.init_app(app)

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
        return jinja.render('index.html', greetings='Hello, sanic!')


    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=8000, debug=True)
```
