import attr
from flask import Response, abort, request, Blueprint
from marshmallow import Schema, fields, post_load
from webargs.flaskparser import use_args

from timApp.auth.accesshelper import get_doc_or_abort, verify_edit_access
from timApp.document.document import Document
from timApp.document.documentversion import DocumentVersion
from timApp.timdb.exceptions import TimDbException
from timApp.util.flask.requesthelper import get_option
from timApp.util.flask.responsehelper import json_response

doc_bp = Blueprint('document',
                   __name__,
                   url_prefix='')


@doc_bp.route('/download/<int:doc_id>')
def download_document(doc_id):
    d = get_doc_or_abort(doc_id)
    verify_edit_access(d)
    return return_doc_content(d.document)


def return_doc_content(d: Document):
    use_raw = get_option(request, 'format', 'md') == 'json'
    if use_raw:
        return json_response(d.export_raw_data())
    else:
        return Response(d.export_markdown(), mimetype="text/plain")


@doc_bp.route('/download/<int:doc_id>/<int:major>/<int:minor>')
def download_document_version(doc_id, major, minor):
    d = get_doc_or_abort(doc_id)
    verify_edit_access(d)
    doc = DocumentVersion(doc_id, (major, minor))
    if not doc.exists():
        abort(404, "This document version does not exist.")
    return return_doc_content(doc)


@doc_bp.route('/diff/<int:doc_id>/<int:major1>/<int:minor1>/<int:major2>/<int:minor2>')
def diff_document(doc_id, major1, minor1, major2, minor2):
    d = get_doc_or_abort(doc_id)
    verify_edit_access(d)
    doc1 = DocumentVersion(doc_id, (major1, minor1))
    doc2 = DocumentVersion(doc_id, (major2, minor2))
    if not doc1.exists():
        abort(404, f"The document version {(major1, minor1)} does not exist.")
    if not doc2.exists():
        abort(404, f"The document version {(major2, minor2)} does not exist.")
    return Response(DocumentVersion.get_diff(doc1, doc2), mimetype="text/html")


@attr.s(auto_attribs=True)
class GetBlockModel:
    doc_id: int = None
    par_id: str = None
    area_start: str = None
    area_end: str = None
    use_exported: bool = True


class GetBlockSchema(Schema):
    doc_id = fields.Int()
    par_id = fields.Str()
    area_start = fields.Str()
    area_end = fields.Str()
    use_exported = fields.Bool(missing=True)

    @post_load
    def make_obj(self, data):
        # noinspection PyArgumentList
        return GetBlockModel(**data)


@doc_bp.route("/getBlock/<int:doc_id>/<par_id>")
def get_block(doc_id, par_id):
    return get_block_2(GetBlockModel(
        area_end=request.args.get('area_end'),
        area_start=request.args.get('area_start'),
        doc_id=doc_id,
        par_id=par_id,
    ))


@doc_bp.route("/getBlock")
@use_args(GetBlockSchema(strict=True))
def get_block_schema(args: GetBlockModel):
    return get_block_2(args)


def get_block_2(args: GetBlockModel):
    d = get_doc_or_abort(args.doc_id)
    verify_edit_access(d)
    area_start = args.area_start
    area_end = args.area_end
    if area_start and area_end:
        try:
            section = d.document.export_section(area_start, area_end)
        except TimDbException as e:
            return abort(404, 'Area not found. It may have been deleted.')
        return json_response({"text": section})
    else:
        try:
            par = d.document.get_paragraph(args.par_id)
        except TimDbException as e:
            return abort(404, 'Paragraph not found. It may have been deleted.')
        if args.use_exported:
            return json_response({"text": par.get_exported_markdown()})
        else:
            return json_response({"text": par.get_markdown()})
