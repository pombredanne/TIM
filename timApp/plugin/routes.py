from flask import request, Response, stream_with_context, abort, Blueprint

from timApp.plugin.containerLink import call_plugin_resource
from timApp.plugin.pluginexception import PluginException

plugin_bp = Blueprint('plugin',
                      __name__,
                      url_prefix='')


@plugin_bp.route("/<plugin>/<path:filename>")
def plugin_call(plugin, filename):
    try:
        req = call_plugin_resource(plugin, filename, request.args)
        return Response(stream_with_context(req.iter_content()), content_type=req.headers['content-type'])
    except PluginException as e:
        abort(404, str(e))


@plugin_bp.route("/echoRequest/<path:filename>")
def echo_request(filename):
    def generate():
        yield 'Request URL: ' + request.url + "\n\n"
        yield 'Headers:\n\n'
        yield from (k + ": " + v + "\n" for k, v in request.headers.items())

    return Response(stream_with_context(generate()), mimetype='text/plain')


@plugin_bp.route("/<plugin>/template/<template>/<index>")
def view_template(plugin, template, index):
    try:
        req = call_plugin_resource(plugin, "template?file=" + template + "&idx=" + index)
        return Response(stream_with_context(req.iter_content()), content_type=req.headers['content-type'])
    except PluginException:
        abort(404)
