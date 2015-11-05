# -*- coding:utf-8 -*-

import functools
from mock import patch
from flask.ext.restful import Api
from collections import namedtuple

SWITCH_ON = True
SWITCH_OFF = False


Api.new = Api.add_resource


def _mock_add_resource(resources_box):
    def _mock(self, resource, *urls, **kwargs):
        resources_box.append(resource)
        resource.belong_to = self.app.name
        return Api.new(self, resource, *urls, **kwargs)
    return _mock


def auto_doc(
        app,
        status,
        file_path='api_doc.md',
        file_format='markdown'):

    resources = []

    def _decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if status is SWITCH_ON:
                with patch('flask.ext.restful.Api.add_resource',
                           _mock_add_resource(resources)):
                    ret = func(*args, **kwargs)
                    _doc_handler(app, resources, file_path, file_format)
                    return ret
            else:
                return func(*args, **kwargs)
        return wrapper
    return _decorator


def _doc_handler(app, resources, file_path, file_format):
    rh = RuleHandler(app)
    doc_file = open(file_path, 'w')
    doc_file.write('#<a id="#top">WebAPI文档</a>\n\n')

    start_module = ''
    for resource in resources:
        resource.url = rh.match(resource.endpoint)
        if resource.belong_to != start_module:
            start_module = resource.belong_to
            doc_file.write('####{}模块  \n'.format(start_module))
        doc_file.write('####[...{}](#{}) \n'.format(
            resource.url.replace('<', '\<'), resource.endpoint
        ))
    try:
        for resource in resources:
            argparse = ArguemtnHandler(resource)
            doc_file.write(
                '##<a id={}>{}</a><a href="#top" style="float:right">#</a>  \n'
                .format(
                    resource.endpoint,
                    resource.url.replace(
                        '<', '\<')
                )
            )
            methods = map(lambda x: x.lower(), resource.methods)
            for m in methods:
                doc_file.write('####方法  \n**{}** \n'.format(m.upper()))
                doc_file.write('####输入参数\n\n')
                doc_file.write('|名字|类型|必填|位置|默认值|说明|  \n')
                doc_file.write('|---|---|---|----|---|-----|  \n')
                for arg in argparse.get_args(m):
                    doc_file.write('|{name}|{type}|{required}|{location}|{default}|{help}|  \n'.format(  # noqa
                        **arg))
                doc_file.write('####详细介绍\n\n{}  \n'.format(
                    getattr(resource, m).__doc__))
    except Exception as e:
        print e.message
    finally:
        doc_file.close()


class RuleHandler(object):

    def __init__(self, app):
        self.map = {r.endpoint: r.rule for r in app.url_map.iter_rules()}

    def match(self, endpoint):
        assert isinstance(endpoint, str)
        _lower = endpoint.lower()
        return self._search(_lower)

    def _search(self, keyword):
        for endpoint, url in self.map.iteritems():
            if keyword in endpoint:
                return url

    def get_map(self):
        return self.map


class ArguemtnHandler(object):

    def __init__(self, resource,
                 parser_suffix='_parser', default_parser='parser'):
        self.resource = resource()
        self.target = resource.__name__
        self.parser_suffix = parser_suffix
        self.default_parser = default_parser
        self.arguments = {}
        self.argclass = namedtuple(
            'argument',
            ['name', 'type', 'required', 'location', 'help']
        )

    def get_args(self, method):
        method = method.lower()
        if method in self.arguments:
            return self.arguments[method]

        self.arguments[method] = []
        try:
            parser = ''.join((method, self.parser_suffix))
            self.Argument = getattr(self.resource, parser, None) \
                or getattr(self.resource, self.default_parser)
        except:
            self.Argument = None
        if self.Argument:
            for arg in self.Argument.args:
                self.arguments[method].append(
                    dict(name=arg.name,
                         type=arg.type.__name__,
                         required=arg.required,
                         location=arg.location,
                         help=arg.help,
                         default=arg.default,
                         ignore=arg.ignore,
                         trim=arg.trim,
                         choices=arg.choices)
                )
        return self.arguments[method]

    @property
    def args(self):
        return self.arguments
