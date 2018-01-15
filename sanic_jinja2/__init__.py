#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from functools import partial
import asyncio
import functools
from sanic.response import html, HTTPResponse
from sanic.views import HTTPMethodView
from jinja2 import Environment, PackageLoader
from jinja2.ext import _make_new_gettext, _make_new_ngettext

__version__ = '0.5.5'

CONTEXT_PROCESSORS = 'context_processor'
APP_KEY = 'jinja2_env'


class SanicJinja2:
    def __init__(self, app=None, loader=None, pkg_name=None, pkg_path=None,
                 context_processors=None, **kwargs):
        self.env = Environment(**kwargs)
        self.app = app
        self.context_processors = context_processors

        if app:
            self.init_app(app, loader, pkg_name or app.name, pkg_path)

    def add_env(self, name, obj, scope='globals'):
        if scope == 'globals':
            self.env.globals[name] = obj
        elif scope == 'filters':
            self.env.filters[name] = obj

    def init_app(self, app, loader=None, pkg_name=None, pkg_path=None):
        self.app = app
        if not hasattr(app, 'extensions'):
            app.extensions = {}

        if self.context_processors:
            if not hasattr(app, CONTEXT_PROCESSORS):
                setattr(app, CONTEXT_PROCESSORS, self.context_processors)
                app.request_middleware.append(self.context_processors)

        app.extensions['jinja2'] = self
        setattr(app, APP_KEY, self.env)
        if not loader:
            loader = PackageLoader(pkg_name or app.name,
                                   pkg_path or 'templates')

        self.env.loader = loader
        self.add_env('app', app)
        self.add_env('url_for', app.url_for)
        self.url_for = app.url_for

        @app.middleware('request')
        async def add_flash_to_request(request):
            if 'flash' not in request:
                request['flash'] = partial(self._flash, request)

    def fake_trans(self, text, *args, **kwargs):
        return text

    def update_request_context(self, request, context):
        if 'babel' in request.app.extensions:
            babel = request.app.babel_instance
            g = _make_new_gettext(babel._get_translations(request).ugettext)
            ng = _make_new_ngettext(babel._get_translations(request).ungettext)
            context.setdefault('gettext', g)
            context.setdefault('ngettext', ng)
            context.setdefault('_', context['gettext'])

        if 'session' in request:
            context.setdefault('session', request['session'])

        context.setdefault('_', self.fake_trans)
        context.setdefault('request', request)
        context.setdefault('get_flashed_messages',
                           partial(self._get_flashed_messages, request))


    async def render_string_async(self, template, request, **context):
        self.update_request_context(request, context)
        return await self.env.get_template(template).render_async(**context)


    async def render_async(self, template, request, **context):
        return html(await self.render_string_async(template, request,
                                                   **context))

    arender = render_async


    def render_source(self, source, request, **context):
        self.update_request_context(request, context)
        return self.env.from_string(source).render(**context)


    def render_string(self, template, request, **context):
        self.update_request_context(request, context)
        return self.env.get_template(template).render(**context)


    def render(self, template, request, **context):
        return html(self.render_string(template, request, **context))


    def _flash(self, request, message, category='message'):
        '''need sanic_session extension'''
        if 'session' in request:
            flashes = request['session'].get('_flashes', [])
            flashes.append((category, message))
            request['session']['_flashes'] = flashes


    def _get_flashed_messages(self, request, with_categories=False,
                              category_filter=[]):
        if 'session' not in request:
            return []

        flashes = request['session'].pop('_flashes') \
            if '_flashes' in request['session'] else []

        if category_filter:
            flashes = list(filter(lambda f: f[0] in category_filter, flashes))

        if not with_categories:
            return [x[1] for x in flashes]

        return flashes

    @staticmethod
    def template(template_name, *, app_key=APP_KEY, encoding='utf-8',
                 headers=None, status=200):
        """
        Decorate web-handler to convert returned dict context into sanic.response.Response
        filled with template_name template.
        :param template_name: template name.
        :param request: a parameter from web-handler, sanic.request.Request instance.
        :param context: context for rendering.
        :param encoding: response encoding, 'utf-8' by default.
        :param status: HTTP status code for returned response, 200 (OK) by default.
        :param app_key: a optional key for application instance. If not provided,
                        default value will be used.
        """

        def wrapper(func):
            @functools.wraps(func)
            async def wrapped(*args, **kwargs):

                if asyncio.iscoroutinefunction(func):
                    coro = func
                else:
                    coro = asyncio.coroutine(func)

                context = await coro(*args, **kwargs)

                if isinstance(context, HTTPResponse):
                    return context

                if isinstance(args[0], HTTPMethodView):
                    request = args[1]
                else:
                    request = args[0]

                return request.app[APP_KEY].render(template_name, request, context,
                                       app_key=app_key, encoding=encoding)

            return wrapped

        return wrapper