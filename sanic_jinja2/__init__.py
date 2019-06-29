#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from collections import Mapping
import functools
from functools import partial
from sanic.response import html, HTTPResponse
from sanic.exceptions import ServerError
from sanic.views import HTTPMethodView
from jinja2 import Environment, PackageLoader, TemplateNotFound
from jinja2.ext import _make_new_gettext, _make_new_ngettext

__version__ = "0.7.5"

CONTEXT_PROCESSORS = "context_processor"


def fake_trans(text, *args, **kwargs):
    return text


def update_request_context(request, context):
    if not request:
        return

    if "babel" in request.app.extensions:
        babel = request.app.babel_instance
        g = _make_new_gettext(babel._get_translations(request).ugettext)
        ng = _make_new_ngettext(babel._get_translations(request).ungettext)
        context.setdefault("gettext", g)
        context.setdefault("ngettext", ng)
        context.setdefault("_", context["gettext"])

    if "session" in request:
        context.setdefault("session", request["session"])

    context.setdefault("_", fake_trans)
    context.setdefault("request", request)
    context.setdefault(
        "get_flashed_messages", partial(_get_flashed_messages, request)
    )


def _get_flashed_messages(request, with_categories=False, category_filter=[]):
    if "session" not in request:
        return []

    flashes = request["session"].pop("_flashes", [])
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
        **kwargs
    ):
        self.enable_async = kwargs.get("enable_async", False)
        self.env = Environment(loader=loader, **kwargs)
        self._loader = loader
        self.app = app
        self.context_processors = context_processors

        if app:
            self.init_app(app, loader, pkg_name or app.name, pkg_path)

    def add_env(self, name, obj, scope="globals"):
        if scope == "globals":
            self.env.globals[name] = obj
        elif scope == "filters":
            self.env.filters[name] = obj

    def init_app(self, app, loader=None, pkg_name=None, pkg_path=None):
        self.app = app
        if not hasattr(app, "extensions"):
            app.extensions = {}

        if self.context_processors:
            if not hasattr(app, CONTEXT_PROCESSORS):
                setattr(app, CONTEXT_PROCESSORS, self.context_processors)
                app.request_middleware.append(self.context_processors)

        app.extensions["jinja2"] = self
        app.jinja_env = self.env
        app.enable_async = self.enable_async
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
            if "flash" not in request:
                request["flash"] = partial(self._flash, request)

    async def render_string_async(self, template, request, **context):
        update_request_context(request, context)
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
        update_request_context(request, context)
        return self.env.from_string(source).render(**context)

    def render_string(self, template, request, **context):
        update_request_context(request, context)
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
        if "session" in request:
            flashes = request["session"].get("_flashes", [])
            flashes.append((category, message))
            request["session"]["_flashes"] = flashes

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

                env = getattr(request.app, "jinja_env", None)
                if not env:
                    raise ServerError(
                        "Template engine has not been initialized yet.",
                        status_code=500
                    )
                try:
                    template = env.get_template(template_name)
                except TemplateNotFound as e:
                    raise ServerError(
                        "Template '{}' not found".format(template_name),
                        status_code=500
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

                if request.app.enable_async:
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
