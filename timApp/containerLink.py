# -*- coding: utf-8 -*-
import json

import requests
from requests.exceptions import Timeout

from documentmodel.docparagraphencoder import DocParagraphEncoder
from plugin import PluginException
from tim_app import app

BRIDGE = app.config['DOCKER_BRIDGE']

TIM_URL = ""

# Most plugins are currently running on tim-beta.it.jyu.fi
# Plugins with numeric IP-address are running there as well, they just don't have routes
# defined in nginx, and as such must be accessed through tim-beta localhost. However,
# as TIM is run from a docker container, pointing to tim-beta's localhost
# must be made through a special bridge.
PLUGINS = {
    "csPlugin":      {"host": BRIDGE + ":56000/cs/"},
    "taunoPlugin":   {"host": BRIDGE + ":56000/cs/tauno/"},
    "simcirPlugin":  {"host": BRIDGE + ":56000/cs/simcir/"},
    "csPluginRikki": {"host": BRIDGE + ":56000/cs/rikki/"},  # demonstrates a broken plugin
    "showCode":      {"host": BRIDGE + ":55000/svn/", "browser": False},
    "showImage":     {"host": BRIDGE + ":55000/svn/image/", "browser": False},
    "showVideo":     {"host": BRIDGE + ":55000/svn/video/", "browser": False},
    "mcq":           {"host": BRIDGE + ":57000/"},
    "mmcq":          {"host": BRIDGE + ":58000/"},
    "shortNote":     {"host": BRIDGE + ":59000/"},
    "graphviz":      {"host": BRIDGE + ":60000/", "browser": False},
    "pali":          {"host": BRIDGE + ":61000/"}
}


def call_plugin_generic(plugin, method, route, data=None, headers=None):
    plug = get_plugin(plugin)
    try:
        request = requests.request(method, plug['host'] + route + "/", data=data, timeout=5, headers=headers)
        request.encoding = 'utf-8'
        return request.text
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        raise PluginException("Could not connect to plugin.")


def call_plugin_html(plugin, info, state, task_id=None):
    plugin_data = json.dumps({"markup": info, "state": state, "taskID": task_id}, cls=DocParagraphEncoder)
    return call_plugin_generic(plugin,
                               'post',
                               'html',
                               data=plugin_data,
                               headers={'Content-type': 'application/json'})


def call_plugin_multihtml(plugin, plugin_data):
    return call_plugin_generic(plugin,
                               'post',
                               'multihtml',
                               data=json.dumps(plugin_data, cls=DocParagraphEncoder),
                               headers={'Content-type': 'application/json'})


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
