"""Answer-related routes."""
import json
import re
import time
from collections import defaultdict
from datetime import timezone, timedelta, datetime
from typing import Union, List, Tuple, Dict

import attr
import dateutil.parser
import dateutil.relativedelta
from flask import Blueprint
from flask import Response
from flask import abort
from flask import request
from marshmallow import Schema, fields, post_load, validates_schema, ValidationError
from marshmallow.utils import _Missing, missing
from sqlalchemy import func, tuple_
from sqlalchemy.orm import defaultload
from webargs.flaskparser import use_args

from pluginserver_flask import GenericMarkupSchema
from timApp.answer.answer import Answer
from timApp.answer.answer_models import AnswerUpload
from timApp.answer.answers import get_latest_answers_query, get_common_answers, save_answer, get_all_answers
from timApp.auth.accesshelper import verify_logged_in, get_doc_or_abort, verify_manage_access
from timApp.auth.accesshelper import verify_task_access, verify_teacher_access, verify_seeanswers_access, \
    has_teacher_access, \
    verify_view_access, get_plugin_from_request
from timApp.auth.accesstype import AccessType
from timApp.auth.sessioninfo import get_current_user_id, logged_in
from timApp.auth.sessioninfo import get_current_user_object, get_session_users, get_current_user_group
from timApp.document.docentry import DocEntry
from timApp.document.docinfo import DocInfo
from timApp.document.document import Document
from timApp.document.post_process import hide_names_in_teacher
from timApp.item.block import Block, BlockType
from timApp.markdown.dumboclient import call_dumbo
from timApp.plugin.containerLink import call_plugin_answer
from timApp.plugin.plugin import Plugin, PluginWrap, NEVERLAZY, TaskNotFoundException
from timApp.plugin.plugin import PluginType
from timApp.plugin.plugin import find_plugin_from_document
from timApp.plugin.pluginControl import find_task_ids, pluginify
from timApp.plugin.pluginControl import task_ids_to_strlist
from timApp.plugin.pluginexception import PluginException
from timApp.plugin.taskid import TaskId, TaskIdAccess
from timApp.timdb.dbaccess import get_timdb
from timApp.timdb.exceptions import TimDbException
from timApp.timdb.sqa import db
from timApp.user.groups import verify_group_view_access
from timApp.user.user import User
from timApp.user.usergroup import UserGroup
from timApp.util.flask.requesthelper import verify_json_params, get_option, get_consent_opt
from timApp.util.flask.responsehelper import json_response, ok_response
from timApp.util.utils import try_load_json, get_current_time

answers = Blueprint('answers',
                    __name__,
                    url_prefix='')


@answers.route("/savePoints/<int:user_id>/<int:answer_id>", methods=['PUT'])
def save_points(answer_id, user_id):
    answer, _ = verify_answer_access(
        answer_id,
        user_id,
        require_teacher_if_not_own=True,
    )
    tid = TaskId.parse(answer.task_id)
    d = get_doc_or_abort(tid.doc_id)
    points, = verify_json_params('points')
    try:
        plugin = Plugin.from_task_id(answer.task_id, user=get_current_user_object())
    except PluginException as e:
        return abort(400, str(e))
    a = Answer.query.get(answer_id)
    try:
        points = points_to_float(points)
    except ValueError:
        abort(400, 'Invalid points format.')
    try:
        a.points = plugin.validate_points(points) if not has_teacher_access(d) else points
    except PluginException as e:
        abort(400, str(e))
    a.last_points_modifier = get_current_user_group()
    db.session.commit()
    return ok_response()


def points_to_float(points: Union[str, float]):
    if points:
        points = float(points)
    else:
        points = None
    return points


@answers.route("/iframehtml/<plugintype>/<task_id_ext>/<int:user_id>/<int:anr>")
def get_iframehtml(plugintype: str, task_id_ext: str, user_id: int, anr: int):
    """
    Gets the HTML to be used in iframe.

    :param plugintype: plugin type
    :param task_id_ext: task id
    :param user_id: the user whose information to get
    :param anr: answer number from answer browser, 0 = newest
    :return: HTML to be used in iframe
    """
    timdb = get_timdb()
    try:
        tid = TaskId.parse(task_id_ext)
    except PluginException as e:
        return abort(400, f'Task id error: {e}')
    d = get_doc_or_abort(tid.doc_id)
    d.document.insert_preamble_pars()

    try:
        tid.block_id_hint = None  # TODO: this should only be done in preview?
        plugin = verify_task_access(d, tid, AccessType.view, TaskIdAccess.ReadWrite)
    except (PluginException, TimDbException) as e:
        return abort(400, str(e))

    if plugin.type != plugintype:
        abort(400, f'Plugin type mismatch: {plugin.type} != {plugintype}')

    users = [User.query.get(user_id)]

    old_answers = get_common_answers(users, tid)

    info = plugin.get_info(users, len(old_answers), look_answer=False and not False, valid=True)

    if anr < 0:
        anr = 0
    # Get the newest answer (state). Only for logged in users.
    state = try_load_json(old_answers[anr].content) if logged_in() and len(old_answers) > 0 else None

    answer_call_data = {'markup': plugin.values,
                        'state': state,
                        'taskID': tid.doc_task,
                        'info': info,
                        'iframehtml': True}

    plugin_response = call_plugin_answer(plugintype, answer_call_data)
    try:
        jsonresp = json.loads(plugin_response)
    except ValueError:
        return json_response({'error': 'The plugin response was not a valid JSON string. The response was: ' +
                                       plugin_response}, 400)
    except PluginException:
        return json_response({'error': 'The plugin response took too long'}, 400)

    if 'iframehtml' not in jsonresp:
        return json_response({'error': 'The key "iframehtml" is missing in plugin response.'}, 400)
    result = jsonresp['iframehtml']
    db.session.commit()
    return result


def get_fields_and_users(u_fields: List[str], groups: List[UserGroup], d: DocInfo, current_user: User):
    needs_group_access_check = UserGroup.get_teachers_group() not in current_user.groups
    for group in groups:
        if needs_group_access_check and group.name != current_user.name:
            if not verify_group_view_access(group, current_user, require=False):
                return abort(403, f'Missing view access for group {group.name}')

    task_ids = []
    task_id_map = defaultdict(list)
    alias_map = {}
    content_map = {}
    jsrunner_alias_map = {}
    doc_map = {}
    for field in u_fields:
        field_content = field.split("|")
        try:
            t, a, *rest = field_content[0].split("=")
        except ValueError:
            t, a, rest = field_content[0], None, None
        if rest:
            return abort(400, f'Invalid alias: {field}')
        if a == '':
            return abort(400, f'Alias cannot be empty: {field}')
        try:
            task_id = TaskId.parse(t, False, False)
        except PluginException as e:
            return abort(400, str(e))
        task_ids.append(task_id)
        if not task_id.doc_id:
            task_id.doc_id = d.id
        task_id_map[task_id.doc_task].append(task_id)
        if len(field_content) == 2:
            content_map[task_id.extended_or_doc_task] = field_content[1].strip()
        if a:
            alias = a
            if alias in jsrunner_alias_map:
                abort(400, f'Duplicate alias {alias} in fields attribute')
            alias_map[task_id.extended_or_doc_task] = alias
            jsrunner_alias_map[alias] = task_id.extended_or_doc_task
        if task_id.doc_id in doc_map:
            continue
        dib = get_doc_or_abort(task_id.doc_id, f'Document {task_id.doc_id} not found')
        if not current_user.has_teacher_access(dib):
            abort(403, f'Missing teacher access for document {dib.id}')
        doc_map[task_id.doc_id] = dib.document

    res = []
    group_filter = UserGroup.id.in_([ug.id for ug in groups])
    answer_sub = Answer.query.filter(Answer.task_id.in_(task_ids_to_strlist(task_ids)))
    aid_max = func.max(Answer.id)
    sub = (
        answer_sub
            .join(User, Answer.users)
            .join(UserGroup, User.groups)
            .filter(group_filter)
            .group_by(Answer.task_id, User.id)
            .with_entities(aid_max.label('aid'), User.id.label('uid'))
            .all()
    )
    aid_uid_map = {}
    for aid, uid in sub:
        aid_uid_map[aid] = uid
    users = (
        UserGroup.query.filter(group_filter)
            .join(User, UserGroup.users)
            .options(defaultload(UserGroup.users).lazyload(User.groups))
            .with_entities(User)
            .order_by(User.id)
            .all()
    )
    user_map = {}
    for u in users:
        user_map[u.id] = u
    answs = Answer.query.filter(Answer.id.in_(aid for aid, _ in sub)).all()
    answers_with_users = []
    for a in answs:
        answers_with_users.append((aid_uid_map[a.id], a))
    missing_users = set(u.id for u in users) - set(uid for uid, _ in answers_with_users)
    for mu in missing_users:
        answers_with_users.append((mu, None))
    answers_with_users.sort(key=lambda x: x[0])
    last_user = None
    user_tasks = None
    user_index = -1
    user = None
    for uid, a in answers_with_users:
        if last_user != uid:
            user_index += 1
            user_tasks = {}
            user = users[user_index]
            res.append({'user': user, 'fields': user_tasks})
            last_user = uid
            if not a:
                continue
        for task in task_id_map[a.task_id]:
            if not a:
                value = None
            elif task.field == "points":
                value = a.points
            elif task.field == "datetime":
                value = time.mktime(a.answered_on.timetuple())
            else:
                json_str = a.content
                p = json.loads(json_str)
                if task.extended_or_doc_task in content_map:
                    # value = p[content_map[task.extended_or_doc_task]]
                    value = p.get(content_map[task.extended_or_doc_task])
                else:
                    if len(p) > 1:
                        plug = find_plugin_from_document(doc_map[task.doc_id], task, user)
                        content_field = plug.get_content_field_name()
                        value = p.get(content_field)
                    else:
                        values_p = list(p.values())
                        value = values_p[0]
            if task.extended_or_doc_task in alias_map:
                user_tasks[alias_map.get(task.extended_or_doc_task)] = value
            else:
                user_tasks[task.extended_or_doc_task] = value
    return res, jsrunner_alias_map, content_map


class JsRunnerSchema(GenericMarkupSchema):
    creditField = fields.Str()
    gradeField = fields.Str()
    gradingScale = fields.Dict()
    defaultPoints = fields.Float()
    failGrade = fields.Str()
    fieldhelper = fields.Bool()
    group = fields.Str()
    groups = fields.List(fields.Str())
    program = fields.Str()
    timeout = fields.Int()
    fields = fields.List(fields.Str(), required=True)

    @validates_schema(skip_on_field_errors=True)
    def validate_schema(self, data):
        if data.get('group') is None and data.get('groups') is None:
            raise ValidationError("Either group or groups must be given.")


@answers.route("/<plugintype>/<task_id_ext>/answer/", methods=['PUT'])
def post_answer(plugintype: str, task_id_ext: str):
    """Saves the answer submitted by user for a plugin in the database.

    :param plugintype: The type of the plugin, e.g. csPlugin.
    :param task_id_ext: The extended task id of the form "22.palidrome.par_id".
    :return: JSON

    """

    try:
        tid = TaskId.parse(task_id_ext)
    except PluginException as e:
        return abort(400, f'Task id error: {e}')
    d = get_doc_or_abort(tid.doc_id)
    d.document.insert_preamble_pars()

    curr_user = get_current_user_object()
    ptype = PluginType(plugintype)
    answerdata, = verify_json_params('input')
    answer_browser_data, answer_options = verify_json_params('abData', 'options', require=False, default={})
    force_answer = answer_options.get('forceSave', False)
    is_teacher = answer_browser_data.get('teacher', False)
    save_teacher = answer_browser_data.get('saveTeacher', False)
    should_save_answer = answer_browser_data.get('saveAnswer', True) and tid.task_name

    if tid.is_points_ref:
        verify_teacher_access(d)
        given_points = answerdata.get(ptype.get_content_field_name())
        if given_points is not None:
            try:
                given_points = float(given_points)
            except ValueError:
                return abort(400, 'Points must be a number.')
        a = curr_user.answers.filter_by(task_id=tid.doc_task).order_by(Answer.id.desc()).first()
        if a:
            a.points = given_points
            s = None
        else:
            a = Answer(
                content=json.dumps({ptype.get_content_field_name(): ''}),
                points=given_points,
                task_id=tid.doc_task,
                users_all=[curr_user],
                valid=True,
            )
            db.session.add(a)
            db.session.flush()
            s = a.id
        db.session.commit()
        return json_response({'savedNew': s, 'web': {'result': 'points saved'}})

    if save_teacher:
        verify_teacher_access(d)
    users = None

    try:
        get_task = answerdata and answerdata.get("getTask", None) and ptype.can_give_task()
    except:
        get_task = False

    if not (should_save_answer or get_task) or is_teacher:
        verify_seeanswers_access(d)
    ctx_user = None
    if is_teacher:
        answer_id = answer_browser_data.get('answer_id', None)
        user_id = answer_browser_data.get('userId', None)
        if answer_id is not None:
            answer = Answer.query.get(answer_id)
            if not answer:
                return abort(404, f'Answer not found: {answer_id}')
            expected_task_id = answer.task_id
            if expected_task_id != tid.doc_task:
                return abort(400, 'Task ids did not match')

            # Later on, we may call users.append, but we don't want to modify the users of the existing
            # answer. Therefore, we make a copy of the user list so that SQLAlchemy no longer associates
            # the user list with the answer.
            users = list(answer.users_all)
            if not users:
                return abort(400, 'No users found for the specified answer')
            if user_id not in (u.id for u in users):
                return abort(400, 'userId is not associated with answer_id')
        elif user_id and user_id != curr_user.id:
            teacher_group = UserGroup.get_teachers_group()
            if curr_user not in teacher_group.users:
                abort(403, 'Permission denied: you are not in teachers group.')
        if user_id:
            ctx_user = User.query.get(user_id)
            if not ctx_user:
                abort(404, f'User {user_id} not found')
    try:
        plugin = verify_task_access(d, tid, AccessType.view, TaskIdAccess.ReadWrite, context_user=ctx_user)
    except (PluginException, TimDbException) as e:
        return abort(400, str(e))

    if plugin.type != plugintype:
        abort(400, f'Plugin type mismatch: {plugin.type} != {plugintype}')

    upload = None
    if isinstance(answerdata, dict):
        file = answerdata.get('uploadedFile', '')
        trimmed_file = file.replace('/uploads/', '')
        type = answerdata.get('type', '')
        if trimmed_file and type == 'upload':
            # The initial upload entry was created in /pluginUpload route, so we need to check that the owner matches
            # what the browser is saying. Additionally, we'll associate the answer with the uploaded file later
            # in this route.
            block = Block.query.filter((Block.description == trimmed_file) &
                                       (Block.type_id == BlockType.Upload.value)).first()
            if block is None:
                abort(400, f'Non-existent upload: {trimmed_file}')
            verify_view_access(block, message="You don't have permission to touch this file.")
            upload = AnswerUpload.query.filter(AnswerUpload.upload_block_id == block.id).first()
            # if upload.answer_id is not None:
            #    abort(400, f'File was already uploaded: {file}')

    # Load old answers

    if users is None:
        users = [User.query.get(u['id']) for u in get_session_users()]

    old_answers = get_common_answers(users, tid)
    try:
        valid, _ = plugin.is_answer_valid(len(old_answers), {})
    except PluginException as e:
        return abort(400, str(e))
    info = plugin.get_info(users, len(old_answers), look_answer=is_teacher and not save_teacher, valid=valid)

    # Get the newest answer (state). Only for logged in users.
    state = try_load_json(old_answers[0].content) if logged_in() and len(old_answers) > 0 else None

    if plugin.type == 'jsrunner':
        s = JsRunnerSchema()
        try:
            s.load(plugin.values)
        except ValidationError as e:
            return abort(400, str(e))
        groupnames = plugin.values.get('groups', [plugin.values.get('group')])
        g = UserGroup.query.filter(UserGroup.name.in_(groupnames))
        found_groups = g.all()
        not_found_groups = sorted(list(set(groupnames) - set(g.name for g in found_groups)))
        if not_found_groups:
            abort(404, f'The following groups were not found: {", ".join(not_found_groups)}')

        answerdata['data'], answerdata['aliases'], _ = get_fields_and_users(plugin.values['fields'],
                                                                            found_groups,
                                                                            d,
                                                                            get_current_user_object())
        if plugin.values.get('program') is None:
            abort(400, "Attribute 'program' is required.")

    answer_call_data = {'markup': plugin.values,
                        'state': state,
                        'input': answerdata,
                        'taskID': tid.doc_task,
                        'info': info}

    plugin_response = call_plugin_answer(plugintype, answer_call_data)
    try:
        jsonresp = json.loads(plugin_response)
    except ValueError:
        return json_response({'error': 'The plugin response was not a valid JSON string. The response was: ' +
                                       plugin_response}, 400)
    except PluginException:
        return json_response({'error': 'The plugin response took too long'}, 400)

    if 'web' not in jsonresp:
        return json_response({'error': 'The key "web" is missing in plugin response.'}, 400)
    result = {'web': jsonresp['web']}

    if plugin.type == 'jsrunner' or plugin.type == 'tableForm':
        handle_jsrunner_response(jsonresp, result, d)
        db.session.commit()
        return json_response(result)

    def add_reply(obj, key, run_markdown=False):
        if key not in plugin.values:
            return
        text_to_add = plugin.values[key]
        if run_markdown:
            dumbo_result = call_dumbo([text_to_add])
            text_to_add = dumbo_result[0]
        obj[key] = text_to_add

    if not get_task:
        add_reply(result['web'], '-replyImage')
        add_reply(result['web'], '-replyMD', True)
        add_reply(result['web'], '-replyHTML')
    if 'save' in jsonresp and not get_task:
        # TODO: RND_SEED: save used rnd_seed for this answer if answer is saved, found from par.get_rnd_seed()
        save_object = jsonresp['save']
        tags = []
        tim_info = jsonresp.get('tim_info', {})
        points = tim_info.get('points', None)
        multiplier = plugin.points_multiplier()
        if multiplier and points is not None:
            points *= plugin.points_multiplier()
        elif not multiplier:
            points = None
        # Save the new state
        try:
            tags = save_object['tags']
        except (TypeError, KeyError):
            pass
        if not is_teacher and should_save_answer:
            is_valid, explanation = plugin.is_answer_valid(len(old_answers), tim_info)
            points_given_by = None
            if answer_browser_data.get('giveCustomPoints'):
                try:
                    points = plugin.validate_points(answer_browser_data.get('points'))
                except PluginException as e:
                    result['error'] = str(e)
                else:
                    points_given_by = get_current_user_group()
            if points or save_object is not None or tags:
                result['savedNew'] = save_answer(users,
                                                 tid,
                                                 json.dumps(save_object),
                                                 points,
                                                 tags,
                                                 is_valid,
                                                 points_given_by,
                                                 force_answer)
            else:
                result['savedNew'] = None
            if not is_valid:
                result['error'] = explanation
        elif save_teacher:
            points = answer_browser_data.get('points', points)
            points = points_to_float(points)
            result['savedNew'] = save_answer(users,
                                             tid,
                                             json.dumps(save_object),
                                             points,
                                             tags,
                                             valid=True,
                                             points_given_by=get_current_user_group(),
                                             saver=curr_user)
        else:
            result['savedNew'] = None
        if result['savedNew'] is not None and upload is not None:
            # Associate this answer with the upload entry
            upload.answer_id = result['savedNew']

    db.session.commit()
    return json_response(result)


def handle_jsrunner_response(jsonresp, result, current_doc: DocInfo):
    save_obj = jsonresp.get('save')
    if not save_obj:
        return
    tasks = set()
    # content_map = {}
    doc_map: Dict[int, DocInfo] = {}
    for item in save_obj:
        task_u = item['fields']
        for key in task_u.keys():
            key_content = key.split("|")
            tid = key_content[0]
            # #TODO: Parse content tässä
            # if len(key_content) == 2:
            #     content_map[key_content[0]] = key_content[1].strip()
            tasks.add(tid)
            try:
                id_num = TaskId.parse(tid, False, False)
            except PluginException:
                return abort(400, f'Invalid task name: {tid.split(".")[1]}')
            if id_num.doc_id not in doc_map:
                doc_map[id_num.doc_id] = get_doc_or_abort(id_num.doc_id)
    task_content_name_map = {}
    curr_user = get_current_user_object()
    for task in tasks:
        t_id = TaskId.parse(task, False, False)
        dib = doc_map[t_id.doc_id]
        if not curr_user.has_teacher_access(dib):
            return abort(403, f'Missing teacher access for document {dib.id}')
        if t_id.task_name == "grade" or t_id.task_name == "credit":
            task_content_name_map[task] = 'c'
            continue
        try:
            plug = find_plugin_from_document(dib.document, t_id, curr_user)
            content_field = plug.get_content_field_name()
            # key_content = key.split("|")
            # #TODO: Parse content tässä
            # if len(key_content) == 2:
            #     content_map[key_content[0]] = key_content[1].strip()
            # TODO: check plug content type ^
            task_content_name_map[task] = content_field
        except TaskNotFoundException as e:
            task_display = t_id.doc_task if t_id.doc_id != current_doc.id else t_id.task_name
            result['web']['error'] = f"Task not found: {task_display}"
            return

    for user in save_obj:
        u_id = user['user']
        u = User.get_by_id(u_id)
        user_fields = user['fields']
        for key, value in user_fields.items():
            content_list = key.split("|")
            if len(content_list) == 2:
                content_field = content_list[1].strip()
            else:
                content_field = task_content_name_map[content_list[0]]
            task_id = TaskId.parse(content_list[0], False, False)
            an: Answer = get_latest_answers_query(task_id, [u]).first()
            content = json.dumps({content_field: value})
            if an and an.content == content:
                continue
            elif an:
                an_content = json.loads(an.content)
                if an_content.get(content_field) == value:
                    continue
                an_content[content_field] = value
                content = json.dumps(an_content)
            ans = Answer(
                content=content,
                task_id=task_id.doc_task,
                users=[u],
                valid=True,
                saver=curr_user,
            )
            db.session.add(ans)


def get_hidden_name(user_id):
    return 'Student %d' % user_id


def should_hide_name(d: DocInfo, user: User):
    return True
    # return not user.has_teacher_access(d) and user.id != get_current_user_id()


def maybe_hide_name(d: DocInfo, u: User):
    if should_hide_name(d, u):
        u.hide_name = True


@answers.route("/taskinfo/<task_id>")
def get_task_info(task_id):
    try:
        plugin = Plugin.from_task_id(task_id, user=get_current_user_object())
        tim_vars = {'maxPoints': plugin.max_points(),
                    'userMin': plugin.user_min_points(),
                    'userMax': plugin.user_max_points(),
                    'deadline': plugin.deadline(),
                    'starttime': plugin.starttime(),
                    'answerLimit': plugin.answer_limit(),
                    'triesText': plugin.values.get('triesText', 'Tries left:'),
                    'pointsText': plugin.values.get('pointsText', 'Points:')
                    }
    except PluginException as e:
        return abort(400, str(e))
    return json_response(tim_vars)


@answers.route("/answers/<task_id>/<user_id>")
def get_answers(task_id, user_id):
    try:
        user_id = int(user_id)
    except ValueError:
        abort(404, 'Not a valid user id')
    verify_logged_in()
    try:
        tid = TaskId.parse(task_id)
    except PluginException as e:
        return abort(400, str(e))
    d = get_doc_or_abort(tid.doc_id)
    user = User.get_by_id(user_id)
    if user_id != get_current_user_id():
        verify_seeanswers_access(d)
    if user is None:
        abort(400, 'Non-existent user')
    try:
        user_answers: List[Answer] = user.get_answers_for_task(tid.doc_task).all()
        if hide_names_in_teacher():
            for answer in user_answers:
                for u in answer.users_all:
                    maybe_hide_name(d, u)
        return json_response(user_answers)
    except Exception as e:
        return abort(400, str(e))


@answers.route("/allDocumentAnswersPlain/<path:doc_path>")
def get_document_answers(doc_path):
    d = DocEntry.find_by_path(doc_path, fallback_to_id=True)
    pars = d.document.get_dereferenced_paragraphs()
    task_ids, _, _ = find_task_ids(pars)
    return get_all_answers_list_plain(task_ids)


@answers.route("/allAnswersPlain/<task_id>")
def get_all_answers_plain(task_id):
    return get_all_answers_list_plain([TaskId.parse(task_id)])


def get_all_answers_list_plain(task_ids: List[TaskId]):
    all_answers = get_all_answers_as_list(task_ids)
    jointext = "\n"
    print_opt = get_option(request, 'print', 'all')
    print_answers = print_opt == "all" or print_opt == "answers"
    if print_answers:
        jointext = "\n\n----------------------------------------------------------------------------------\n"
    text = jointext.join(all_answers)
    return Response(text, mimetype='text/plain')


def get_all_answers_as_list(task_ids: List[TaskId]):
    verify_logged_in()
    if not task_ids:
        return []
    doc_ids = set()
    for tid in task_ids:
        doc_ids.add(tid.doc_id)
        d = get_doc_or_abort(tid.doc_id)
        # Require full teacher rights for getting all answers
        verify_teacher_access(d)

    usergroup = get_option(request, 'group', None)
    age = get_option(request, 'age', 'max')
    valid = get_option(request, 'valid', '1')
    name_opt = get_option(request, 'name', 'both')
    sort_opt = get_option(request, 'sort', 'task')
    print_opt = get_option(request, 'print', 'all')
    period_opt = get_option(request, 'period', 'whenever')
    consent = get_consent_opt()
    printname = name_opt == 'both'

    period_from, period_to = period_handling(task_ids, doc_ids, period_opt)

    if not usergroup:
        usergroup = None

    hide_names = name_opt == 'anonymous'
    hide_names = hide_names or hide_names_in_teacher()
    all_answers = get_all_answers(task_ids,
                                  usergroup,
                                  hide_names,
                                  age,
                                  valid,
                                  printname,
                                  sort_opt,
                                  print_opt,
                                  period_from,
                                  period_to,
                                  consent=consent)
    return all_answers


@answers.route("/allAnswers/<task_id>")
def get_all_answers_route(task_id):
    all_answers = get_all_answers_as_list(task_id)
    return json_response(all_answers)


class GetStateSchema(Schema):
    answer_id = fields.Int(required=True)
    par_id = fields.Str()
    user_id = fields.Int(required=True)
    review = fields.Bool(missing=False)

    @post_load
    def make_obj(self, data):
        return GetStateModel(**data)


@attr.s(auto_attribs=True)
class GetStateModel:
    answer_id: int
    user_id: int
    review: bool
    par_id: Union[str, _Missing] = missing


@answers.route("/getState")
@use_args(GetStateSchema())
def get_state(args: GetStateModel):
    par_id, user_id, answer_id, review = args.par_id, args.user_id, args.answer_id, args.review

    try:
        answer, doc_id = verify_answer_access(answer_id, user_id)
    except PluginException as e:
        return abort(400, str(e))
    doc = Document(doc_id)
    # if doc_id != d_id and doc_id not in doc.get_referenced_document_ids():
    #     abort(400, 'Bad document id')

    tid = TaskId.parse(answer.task_id)
    if par_id:
        tid.maybe_set_hint(par_id)
    user = User.query.get(user_id)
    if user is None:
        abort(400, 'Non-existent user')
    doc.insert_preamble_pars()
    try:
        doc, plug = get_plugin_from_request(doc, task_id=tid, u=user)
    except PluginException as e:
        return abort(400, str(e))
    block = plug.par

    _, _, _, plug = pluginify(
        doc,
        [block],
        user,
        custom_answer=answer,
        pluginwrap=PluginWrap.Nothing,
        do_lazy=NEVERLAZY,
    )
    html = plug.get_final_output()
    if review:
        block.final_dict = None
        _, _, _, rplug = pluginify(
            doc,
            [block],
            user,
            custom_answer=answer,
            review=review,
            pluginwrap=PluginWrap.Nothing,
            do_lazy=NEVERLAZY,
        )
        return json_response({'html': html, 'reviewHtml': rplug.get_final_output()})
    else:
        return json_response({'html': html, 'reviewHtml': None})


def verify_answer_access(
        answer_id: int,
        user_id: int,
        require_teacher_if_not_own=False,
        required_task_access_level: TaskIdAccess = TaskIdAccess.ReadOnly,
) -> Tuple[Answer, int]:
    answer: Answer = Answer.query.get(answer_id)
    if answer is None:
        abort(400, 'Non-existent answer')
    tid = TaskId.parse(answer.task_id)
    d = get_doc_or_abort(tid.doc_id)
    d.document.insert_preamble_pars()
    if user_id != get_current_user_id() or not logged_in():
        if require_teacher_if_not_own:
            verify_task_access(d, tid, AccessType.teacher, required_task_access_level)
        else:
            verify_task_access(d, tid, AccessType.see_answers, required_task_access_level)
    else:
        verify_task_access(d, tid, AccessType.view, required_task_access_level)
        if not any(a.id == user_id for a in answer.users_all):
            abort(403, "You don't have access to this answer.")
    return answer, tid.doc_id


@answers.route("/getTaskUsers/<task_id>")
def get_task_users(task_id):
    tid = TaskId.parse(task_id)
    d = get_doc_or_abort(tid.doc_id)
    verify_seeanswers_access(d)
    usergroup = request.args.get('group')
    q = User.query.join(Answer, User.answers).filter_by(task_id=task_id).join(UserGroup, User.groups).order_by(
        User.real_name.asc())
    if usergroup is not None:
        q = q.filter(UserGroup.name.in_([usergroup]))
    users = q.all()
    if hide_names_in_teacher():
        for user in users:
            maybe_hide_name(d, user)
    return json_response(users)


@answers.route('/renameAnswers/<old_name>/<new_name>/<path:doc_path>')
def rename_answers(old_name: str, new_name: str, doc_path: str):
    d = DocEntry.find_by_path(doc_path, fallback_to_id=True)
    if not d:
        abort(404)
    verify_manage_access(d)
    force = get_option(request, 'force', False)
    for n in (old_name, new_name):
        if not re.fullmatch('[a-zA-Z0-9_-]+', n):
            abort(400, f'Invalid task name: {n}')
    conflicts = Answer.query.filter_by(task_id=f'{d.id}.{new_name}').count()
    if conflicts > 0 and not force:
        abort(400, f'The new name conflicts with {conflicts} other answers with the same task name.')
    answers_to_rename = Answer.query.filter_by(task_id=f'{d.id}.{old_name}').all()
    for a in answers_to_rename:
        a.task_id = f'{d.id}.{new_name}'
    db.session.commit()
    return json_response({'modified': len(answers_to_rename), 'conflicts': conflicts})


def period_handling(task_ids, doc_ids, period):
    """
    Returns start and end of an period for answer results.
    :param task_ids: Task ids containing the answers.
    :param doc_ids: Documents containing the answers.
    :param period: Period options: whenever, sincelast, day, week, month, other.
    :return: Return "from"-period and "to"-period.
    """
    period_from = datetime.min.replace(tzinfo=timezone.utc)
    period_to = get_current_time()

    since_last_key = task_ids[0].doc_task if task_ids else None
    if len(task_ids) > 1:
        since_last_key = str(next(d for d in doc_ids))
        if len(doc_ids) > 1:
            since_last_key = None

        # Period from which to take results.
    if period == 'whenever':
        pass
    elif period == 'sincelast':
        u = get_current_user_object()
        prefs = u.get_prefs()
        last_answer_fetch = prefs.last_answer_fetch
        period_from = last_answer_fetch.get(since_last_key, datetime.min.replace(tzinfo=timezone.utc))
        last_answer_fetch[since_last_key] = get_current_time()
        prefs.last_answer_fetch = last_answer_fetch
        u.set_prefs(prefs)
        db.session.commit()
    elif period == 'day':
        period_from = period_to - timedelta(days=1)
    elif period == 'week':
        period_from = period_to - timedelta(weeks=1)
    elif period == 'month':
        period_from = period_to - dateutil.relativedelta.relativedelta(months=1)
    elif period == 'other':
        period_from_str = get_option(request, 'periodFrom', period_from.isoformat())
        period_to_str = get_option(request, 'periodTo', period_to.isoformat())
        try:
            period_from = dateutil.parser.parse(period_from_str)
        except (ValueError, OverflowError):
            pass
        try:
            period_to = dateutil.parser.parse(period_to_str)
        except (ValueError, OverflowError):
            pass

    return period_from, period_to
