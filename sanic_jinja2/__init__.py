#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import functools

try:
    from collections import Mapping
except ImportError:
    from collections.abc import Mapping

from functools import partial

from jinja2 import Environment, PackageLoader, TemplateNotFound
from jinja2.ext import _make_new_gettext, _make_new_ngettext
from sanic.exceptions import ServerError
from sanic.response import HTTPResponse, html
from sanic.views import HTTPMethodView

__version__ = "2021.12.25"

CONTEXT_PROCESSORS = "context_processor"


def fake_trans(text, *args, **kwargs):
    return text


def get_request_container(request):
    return request.ctx.__dict__ if hasattr(request, "ctx") else request


def get_session_name(request):
    jinja_obj = request.app.ctx.extensions.get("jinja2")
    if jinja_obj:
        return getattr(jinja_obj, "session_name", None) or "session"

    return "session"


def update_request_context(request, context):
    if not request:
        return

    if "babel" in request.app.ctx.extensions:
        babel = request.app.ctx.babel_instance
        g = _make_new_gettext(babel._get_translations(request).ugettext)
        ng = _make_new_ngettext(babel._get_translations(request).ungettext)
        context.setdefault("gettext", g)
        context.setdefault("ngettext", ng)
        context.setdefault("_", context["gettext"])

    session_name = get_session_name(request)
    req = get_request_container(request)
    if session_name in req:
        context.setdefault("session", req[session_name])

    context.setdefault("_", fake_trans)
    context.setdefault("request", request)
    context.setdefault(
        "get_flashed_messages", partial(_get_flashed_messages, request)
    )


def _get_flashed_messages(request, with_categories=False, category_filter=[]):
    session_name = get_session_name(request)
    req = get_request_container(request)
    if session_name not in req:
        return []

    flashes = req[session_name].pop("_flashes", [])
    if category_filter:
        flashes = list(filter(lambda f: f[0] in category_filter, flashes))

    if not with_categories:
        return [x[1] for x in flashes]

    return flashes


class SanicJinja2:
    def __init__(
        self,
        app=None,
        loader=None,
        pkg_name=None,
        pkg_path=None,
        context_processors=None,
        session=None,
        **kwargs
    ):
        self.enable_async = kwargs.get("enable_async", False)
        self.env = Environment(loader=loader, **kwargs)
        self._loader = loader
        self.app = app
        self.context_processors = context_processors
        self.__sess = session

        if app:
            self.init_app(app, loader, pkg_name or app.name, pkg_path)

    def add_env(self, name, obj, scope="globals"):
        if scope == "globals":
            self.env.globals[name] = obj
        elif scope == "filters":
            self.env.filters[name] = obj

    def init_app(self, app, loader=None, pkg_name=None, pkg_path=None):
        self.app = app
        if not hasattr(app.ctx, "extensions"):
            app.ctx.extensions = {}

        if self.context_processors:
            if not hasattr(app, CONTEXT_PROCESSORS):
                setattr(app, CONTEXT_PROCESSORS, self.context_processors)
                app.request_middleware.append(self.context_processors)

        app.ctx.extensions["jinja2"] = self
        app.ctx.jinja_env = self.env
        app.ctx.enable_async = self.enable_async
        if loader:
            self.env.loader = loader
        elif not self._loader:
            loader = PackageLoader(
                pkg_name or app.name, pkg_path or "templates"
            )
            self.env.loader = loader

        self.add_env("app", app)
        self.add_env("url_for", app.url_for)
        self.url_for = app.url_for

        @app.middleware("request")
        async def add_flash_to_request(request):
            req = get_request_container(request)
            if "flash" not in req:
                req["flash"] = partial(self._flash, req)

    def init_session(self, session):
        if session:
            self.__sess = session

    @property
    def session_name(self):
        return self.__sess.interface.session_name if self.__sess else "session"

    async def render_string_async(self, template, request, **context):
        self.update_request_context(request, context)
        return await self.env.get_template(template).render_async(**context)

    async def render_async(
        self, template, request, status=200, headers=None, **context
    ):
        return html(
            await self.render_string_async(template, request, **context),
            status=status,
            headers=headers,
        )

    def render_source(self, source, request, **context):
        self.update_request_context(request, context)
        return self.env.from_string(source).render(**context)

    def render_string(self, template, request, **context):
        self.update_request_context(request, context)
        return self.env.get_template(template).render(**context)

    def render(self, template, request, status=200, headers=None, **context):
        return html(
            self.render_string(template, request, **context),
            status=status,
            headers=headers,
        )

    def update_request_context(self, request, context):
        update_request_context(request, context)

    def _flash(self, request, message, category="message"):
        """need sanic_session extension"""
        sess = self.session(request)
        if sess is not None:
            flashes = sess.get("_flashes", [])
            flashes.append((category, message))
            sess["_flashes"] = flashes

    def flash(self, request, message, category="message"):
        self._flash(request, message, category)

    def session(self, request):
        req = get_request_container(request)
        return req.get(self.session_name)

    @staticmethod
    def template(template_name, encoding="utf-8", headers=None, status=200):
        """Decorate web-handler to convert returned dict context into
        sanic.response.Response
        filled with template_name template.
        :param template_name: template name.
        :param request: a parameter from web-handler,
                        sanic.request.Request instance.
        :param context: context for rendering.
        """

        def wrapper(func):
            @asyncio.coroutine
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                if asyncio.iscoroutinefunction(func):
                    coro = func
                else:
                    coro = asyncio.coroutine(func)

                context = yield from coro(*args, **kwargs)

                # wrapped function return HTTPResponse
                # instead of dict-like object
                if isinstance(context, HTTPResponse):
                    return context

                # wrapped function is class method
                # and got `self` as first argument
                if isinstance(args[0], HTTPMethodView):
                    request = args[1]
                else:
                    request = args[0]

                if context is None:
                    context = {}

                env = getattr(request.app.ctx, "jinja_env", None)
                if not env:
                    raise ServerError(
                        "Template engine has not been initialized yet.",
                        status_code=500,
                    )
                try:
                    template = env.get_template(template_name)
                except TemplateNotFound:
                    raise ServerError(
                        "Template '{}' not found".format(template_name),
                        status_code=500,
                    )
                if not isinstance(context, Mapping):
                    raise ServerError(
                        "context should be mapping, not {}".format(
                            type(context)
                        ),
                        status_code=500,
                    )
                # if request.get(REQUEST_CONTEXT_KEY):
                #     context = dict(request[REQUEST_CONTEXT_KEY], **context)
                update_request_context(request, context)

                if request.app.ctx.enable_async:
                    text = yield from template.render_async(context)
                else:
                    text = template.render(context)

                content_type = "text/html; charset={}".format(encoding)

                return HTTPResponse(
                    text,
                    status=status,
                    headers=headers,
                    content_type=content_type,
                )

            return wrapped

        return wrapper
