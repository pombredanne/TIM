# -*- coding: utf-8 -*-
import json
import os
from functools import lru_cache

import requests
from requests.exceptions import Timeout

from documentmodel.docparagraphencoder import DocParagraphEncoder
from plugin import PluginException
from tim_app import app

TIM_URL = ""

CSPLUGIN_NAME = 'csPlugin'
SVNPLUGIN_NAME = 'showFile'
HASKELLPLUGIN_NAME = 'haskellplugins2'
PALIPLUGIN_NAME = 'pali'


TIM_HOST = os.environ.get('TIM_HOST', default='localhost')

if TIM_HOST != 'localhost' and app.config.get('PLUGIN_CONNECTIONS') == 'nginx':
    # To use this, put your IP in TIM_HOST environment variable
    # so tim can get out of the container and to the plugins,
    # and set PLUGIN_CONNECTIONS = "nginx" in the flask config file
    print("Using nginx for plugins")
    PLUGINS = {
        "csPlugin":      {"host": "http://" + TIM_HOST + ":56000/cs/"},
        "taunoPlugin":   {"host": "http://" + TIM_HOST + ":56000/cs/tauno/"},
        "simcirPlugin":  {"host": "http://" + TIM_HOST + ":56000/cs/simcir/"},
        "csPluginRikki": {"host": "http://" + TIM_HOST + ":56000/cs/rikki/"},  # demonstrates a broken plugin
        "showCode":      {"host": "http://" + TIM_HOST + ":55000/svn/", "browser": False},
        "showImage":     {"host": "http://" + TIM_HOST + ":55000/svn/image/", "browser": False},
        "showVideo":     {"host": "http://" + TIM_HOST + ":55000/svn/video/", "browser": False},
        "mcq":           {"host": "http://" + TIM_HOST + ":57000/"},
        "mmcq":          {"host": "http://" + TIM_HOST + ":58000/"},
        "shortNote":     {"host": "http://" + TIM_HOST + ":59000/"},
        "graphviz":      {"host": "http://" + TIM_HOST + ":60000/", "browser": False},
    }
else:
    print("Using container network for plugins")
    PLUGINS = {
        "csPlugin":      {"host": "http://" + CSPLUGIN_NAME + ":5000/cs/"},
        "taunoPlugin":   {"host": "http://" + CSPLUGIN_NAME + ":5000/cs/tauno/"},
        "simcirPlugin":  {"host": "http://" + CSPLUGIN_NAME + ":5000/cs/simcir/"},
        "csPluginRikki": {"host": "http://" + CSPLUGIN_NAME + ":5000/cs/rikki/"},  # demonstrates a broken plugin
        "showCode":      {"host": "http://" + SVNPLUGIN_NAME + ":5000/svn/", "browser": False},
        "showImage":     {"host": "http://" + SVNPLUGIN_NAME + ":5000/svn/image/", "browser": False},
        "showVideo":     {"host": "http://" + SVNPLUGIN_NAME + ":5000/svn/video/", "browser": False},
        "mcq":           {"host": "http://" + HASKELLPLUGIN_NAME + ":5001/"},
        "mmcq":          {"host": "http://" + HASKELLPLUGIN_NAME + ":5002/"},
        "shortNote":     {"host": "http://" + HASKELLPLUGIN_NAME + ":5003/"},
        "graphviz":      {"host": "http://" + HASKELLPLUGIN_NAME + ":5004/", "browser": False},
        # "pali":          {"host": "http://" + PALIPLUGIN_NAME + ":5000/"}
    }


def call_plugin_generic(plugin, method, route, data=None, headers=None, params=None):
    plug = get_plugin(plugin)
    try:
        request = requests.request(method, plug['host'] + route + "/", data=data, timeout=15, headers=headers, params=params)
        request.encoding = 'utf-8'
        return request.text
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        raise PluginException("Could not connect to plugin.")


def call_plugin_html(plugin, info, state, task_id=None, params=None):
    data_dict = {"markup": info, "state": state, "taskID": task_id}
    data_dict.update(params or {})
    plugin_data = json.dumps(data_dict,
                             cls=DocParagraphEncoder)
    return call_plugin_generic(plugin,
                               'post',
                               'html',
                               data=plugin_data,
                               headers={'Content-type': 'application/json'},
                               params=params)


def call_plugin_multihtml(plugin, plugin_data, params=None):
    if params is not None:
        for p in plugin_data:
            p.update(params)
    return call_plugin_generic(plugin,
                               'post',
                               'multihtml',
                               data=json.dumps(plugin_data, cls=DocParagraphEncoder),
                               headers={'Content-type': 'application/json'},
                               params=params)


def call_plugin_resource(plugin, filename):
    try:
        plug = get_plugin(plugin)
        request = requests.get(plug['host'] + filename, timeout=5, stream=True)
        request.encoding = 'utf-8'
        return request
    except requests.exceptions.Timeout:
        raise PluginException("Could not connect to plugin: " + plugin)


def call_plugin_answer(plugin, answer_data):
    return call_plugin_generic(plugin,
                               'put',
                               'answer',
                               json.dumps(answer_data, cls=DocParagraphEncoder),
                               headers={'Content-type': 'application/json'})


# Get lists of js and css files required by plugin, as well as list of Angular modules they define.
@lru_cache(maxsize=100)
def plugin_reqs(plugin):
    return call_plugin_generic(plugin, 'get', 'reqs')


# Gets plugin info (host)
def get_plugin(plugin):
    if plugin in PLUGINS:
        return PLUGINS[plugin]
    raise PluginException("Plugin does not exist.")


# Get address towards which the plugin must send its further requests, such as answers
def get_plugin_tim_url(plugin):
    if plugin in PLUGINS:
        return TIM_URL + "/" + plugin
    raise PluginException("Plugin does not exist.")


def get_plugin_needs_browser(plugin):
    # if not plugin: return False
    plg = get_plugin(plugin)
    if "browser" not in plg: return True
    return plg["browser"] != False
