#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sanic import Sanic
from sanic_session import Session, InMemorySessionInterface
from sanic_jinja2 import SanicJinja2

app = Sanic()

session = Session(app, interface=InMemorySessionInterface())
jinja = SanicJinja2(app, session=session)


@app.route("/")
async def index(request):
    jinja.flash(request, "success message", "success")
    jinja.flash(request, "info message", "info")
    jinja.flash(request, "warning message", "warning")
    jinja.flash(request, "error message", "error")
    jinja.session(request)["user"] = "session user"
    return jinja.render("index.html", request, greetings="Hello, sanic!")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
