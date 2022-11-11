#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sanic import Sanic
from sanic_jinja2 import SanicJinja2
from sanic_session import InMemorySessionInterface, Session

app = Sanic(__name__)

session = Session(app, interface=InMemorySessionInterface())
jinja = SanicJinja2(app, session=session)


@app.route("/")
@jinja.template("index.html")
async def index(request):
    jinja.flash(request, "success message", "success")
    jinja.flash(request, "info message", "info")
    jinja.flash(request, "warning message", "warning")
    jinja.flash(request, "error message", "error")
    jinja.session(request)["user"] = "session user"
    return dict(greetings="Hello, template decorator!")


@app.route("/normal")
async def normal_index(request):
    jinja.flash(request, "success message", "success")
    jinja.flash(request, "info message", "info")
    jinja.flash(request, "warning message", "warning")
    jinja.flash(request, "error message", "error")
    jinja.session(request)["user"] = "session user"
    return jinja.render(
        "normal_index.html", request, greetings="Hello, tempalte render!"
    )


@app.route("/sync-handler")
@jinja.template("index.html")
def sync_hander(request):
    jinja.flash(request, "success message", "success")
    jinja.flash(request, "info message", "info")
    jinja.flash(request, "warning message", "warning")
    jinja.flash(request, "error message", "error")
    jinja.session(request)["user"] = "session user"
    return dict(greetings="Hello, sync handler!")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True, auto_reload=True)
