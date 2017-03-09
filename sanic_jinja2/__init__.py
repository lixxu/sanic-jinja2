#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from functools import partial
from sanic.response import html
from jinja2 import Environment, PackageLoader
from jinja2.ext import _make_new_gettext, _make_new_ngettext


class SanicJinja2:
    def __init__(self, app=None, loader=None, **kwargs):
        self.env = Environment(**kwargs)
        self.app = app
        if app:
            self.init_app(app, loader)

    def add_env(self, name, obj, scope='globals'):
        if scope == 'globals':
            self.env.globals[name] = obj
        elif scope == 'filters':
            self.env.filters[name] = obj

    def init_app(self, app, loader=None):
        self.app = app
        if not hasattr(app, 'extensions'):
            app.extensions = {}

        app.extensions['jinja2'] = self
        app.jinja_env = self.env
        if not loader:
            loader = PackageLoader(app.name, 'templates')

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
