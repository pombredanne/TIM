from flask import Blueprint, abort, request
from flask import current_app
from sqlalchemy import func, distinct, true
from sqlalchemy.exc import IntegrityError

from timApp.auth.accesshelper import verify_read_marking_right, get_doc_or_abort, verify_teacher_access
from timApp.auth.sessioninfo import get_session_usergroup_ids, get_current_user_group
from timApp.document.docentry import DocEntry
from timApp.document.post_process import hide_names_in_teacher
from timApp.readmark.readings import mark_read, get_readings, mark_all_read
from timApp.readmark.readparagraph import ReadParagraph
from timApp.readmark.readparagraphtype import ReadParagraphType
from timApp.timdb.exceptions import TimDbException
from timApp.timdb.sqa import db
from timApp.user.user import User
from timApp.user.usergroup import UserGroup
from timApp.util.flask.requesthelper import verify_json_params, get_referenced_pars_from_req, get_option, \
    get_consent_opt
from timApp.util.flask.responsehelper import json_response, ok_response, csv_response
from timApp.util.utils import seq_to_str, split_by_semicolon

readings = Blueprint('readings',
                     __name__,
                     url_prefix='')


@readings.route("/read/<int:doc_id>", methods=['GET'])
def get_read_paragraphs(doc_id):
    d = get_doc_or_abort(doc_id)
    verify_read_marking_right(d)
    doc = d.document
    # TODO: Get the intersection of read markings of all session users
    result = get_readings(get_current_user_group(), doc)
    return json_response(result)


@readings.route("/unread/<int:doc_id>/<par_id>", methods=['PUT'])
def unread_paragraph(doc_id, par_id):
    return set_read_paragraph(doc_id, par_id, unread=True)


@readings.route("/read/<int:doc_id>/<par_id>/<int:read_type>", methods=['PUT'])
def set_read_paragraph(doc_id, par_id, read_type=None, unread=False):
    paragraph_type = ReadParagraphType(read_type) if read_type is not None else ReadParagraphType.click_red
    if current_app.config['DISABLE_AUTOMATIC_READINGS'] and paragraph_type in (ReadParagraphType.on_screen,
                                                                               ReadParagraphType.hover_par):
        return ok_response()
    d = get_doc_or_abort(doc_id)
    verify_read_marking_right(d)
    doc = d.document
    par_ids, = verify_json_params('pars', require=False)
    if not par_ids:
        par_ids = [par_id]
    try:
        pars = [doc.get_paragraph(par_id) for par_id in par_ids]
    except TimDbException:
        return abort(404, 'Non-existent paragraph')

    for group_id in get_session_usergroup_ids():
        for par in pars:
            for p in get_referenced_pars_from_req(par):
                if unread:
                    rp = ReadParagraph.query.filter_by(usergroup_id=group_id,
                                                       doc_id=p.get_doc_id(),
                                                       par_id=p.get_id(),
                                                       type=paragraph_type)
                    rp.delete()
                else:
                    mark_read(group_id, p.doc, p, paragraph_type)
    try:
        db.session.commit()
    except IntegrityError:
        abort(400, 'Paragraph was already marked read')
    return ok_response()


@readings.route("/read/<int:doc_id>", methods=['PUT'])
def mark_document_read(doc_id):
    d = get_doc_or_abort(doc_id)
    verify_read_marking_right(d)
    doc = d.document
    for group_id in get_session_usergroup_ids():
        mark_all_read(group_id, doc)
    db.session.commit()
    return ok_response()


@readings.route("/read/stats/<path:doc_path>")
def get_statistics(doc_path):
    d = DocEntry.find_by_path(doc_path, fallback_to_id=True)
    if not d:
        abort(404)
    verify_teacher_access(d)
    sort_opt = get_option(request, 'sort', 'username')
    group_opt = get_option(request, 'groups', None)
    block_opt = get_option(request, 'blocks', None)
    result_format = get_option(request, 'format', 'json')
    csv_dialect = get_option(request, 'csv', 'excel-tab')
    consent = get_consent_opt()
    extra_condition = true()
    if group_opt:
        group_names = split_by_semicolon(group_opt)
        extra_condition = extra_condition & UserGroup.name.in_(
            User.query.join(UserGroup, User.groups).filter(UserGroup.name.in_(group_names)).with_entities(User.name)
        )
    if consent:
        extra_condition = extra_condition & UserGroup.id.in_(
            User.query.join(UserGroup, User.groups).filter(User.consent == consent).with_entities(UserGroup.id))
    if block_opt:
        block_ids = split_by_semicolon(block_opt)
        extra_condition = extra_condition & ReadParagraph.par_id.in_(block_ids)
    automatic_types = [
        ReadParagraphType.click_par,
        ReadParagraphType.hover_par,
        ReadParagraphType.on_screen,
    ]
    cols = [func.count(distinct(ReadParagraph.par_id)).filter(ReadParagraph.type == t) for t in
            (ReadParagraphType.click_red,
             *automatic_types
             )]
    cols.append(func.count(distinct(ReadParagraph.par_id)).filter(ReadParagraph.type.in_(automatic_types)))
    column_names = ('username', 'click_red', 'click_par', 'hover_par', 'on_screen', 'any_of_phs')
    sort_col_map = dict(zip(column_names, [UserGroup.name] + cols))
    col_to_sort = sort_col_map.get(sort_opt)
    if col_to_sort is None:
        abort(400, f'Invalid sort option. Possible values are {seq_to_str(column_names)}.')
    q = (UserGroup.query.join(ReadParagraph)
         .filter_by(doc_id=d.id)
         .filter(extra_condition)
         .add_columns(*cols)
         .group_by(UserGroup)
         .order_by(col_to_sort)
         .with_entities(UserGroup.name, *cols))

    def row_to_dict(row):
        di = dict(zip(column_names, row))
        if hide_names_in_teacher():
            di['username'] = 'user'
        return di

    if result_format == 'csv':
        def gen_rows():
            yield column_names
            yield from q

        return csv_response(gen_rows(), dialect=csv_dialect)
    else:
        return json_response(
            list(
                map(
                    row_to_dict,
                    q.all()
                )
            )
        )
