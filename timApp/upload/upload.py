import imghdr
import io
import json
import os
import posixpath
from pathlib import Path, PurePosixPath
from typing import List, Optional, Tuple
from urllib.parse import unquote, urlparse

import magic
from dataclasses import dataclass

import subprocess
from flask import Blueprint, request, send_file, Response
from flask import abort
from werkzeug.utils import secure_filename

from timApp.auth.accesshelper import verify_view_access, verify_seeanswers_access, verify_task_access, \
    grant_access_to_session_users, get_doc_or_abort, verify_edit_access, AccessDenied
from timApp.auth.accesstype import AccessType
from timApp.auth.sessioninfo import get_current_user_object
from timApp.auth.sessioninfo import logged_in, get_current_user_group_object
from timApp.document.docentry import DocEntry
from timApp.document.docinfo import DocInfo
from timApp.document.documents import import_document
from timApp.item.block import Block
from timApp.item.block import BlockType
from timApp.item.validation import validate_item_and_create_intermediate_folders, validate_uploaded_document_content
from timApp.plugin.pluginexception import PluginException
from timApp.plugin.taskid import TaskId, TaskIdAccess
from timApp.timdb.dbaccess import get_files_path
from timApp.timdb.sqa import db
from timApp.upload.uploadedfile import PluginUpload, PluginUploadInfo, UploadedFile
from timApp.util.flask.requesthelper import use_model, RouteException
from timApp.util.flask.responsehelper import json_response, ok_response
from timApp.util.pdftools import StampDataInvalidError, default_stamp_format, AttachmentStampData, \
    PdfError, stamp_pdfs, create_tex_file, stamp_model_default_path

upload = Blueprint('upload',
                   __name__,
                   url_prefix='')


@upload.after_request
def set_csp(resp: Response):
    # Chrome refuses to render PDFs with "CSP: sandbox" header
    if resp.mimetype != 'application/pdf':
        resp.headers['Content-Security-Policy'] = "sandbox"
        resp.headers['X-Content-Security-Policy'] = "sandbox"  # For IE
    return resp


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


DOC_EXTENSIONS = ['txt', 'md', 'markdown']
PIC_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif']
ALLOWED_EXTENSIONS = set(PIC_EXTENSIONS + DOC_EXTENSIONS)

# The folder for stamped and original pdf files.
default_attachment_folder = get_files_path() / "blocks/files"

WHITELIST_MIMETYPES = {
    'application/pdf',
    'image/gif',
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/svg+xml',
    'text/plain',
    'text/xml',
    'application/octet-stream',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
    'application/vnd.ms-word.document.macroEnabled.12',
    'application/vnd.ms-word.template.macroEnabled.12',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
    'application/vnd.ms-excel.sheet.macroEnabled.12',
    'application/vnd.ms-excel.template.macroEnabled.12',
    'application/vnd.ms-excel.addin.macroEnabled.12',
    'application/vnd.ms-excel.sheet.binary.macroEnabled.12',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.openxmlformats-officedocument.presentationml.template',
    'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
    'application/vnd.ms-powerpoint.addin.macroEnabled.12',
    'application/vnd.ms-powerpoint.presentation.macroEnabled.12',
    'application/vnd.ms-powerpoint.template.macroEnabled.12',
    'application/vnd.ms-powerpoint.slideshow.macroEnabled.12',
    'application/vnd.ms-access',
}


def get_mimetype(p):
    mime = magic.Magic(mime=True)
    mt = mime.from_file(p)
    if mt == 'image/svg':
        mt += '+xml'
    if isinstance(mt, bytes):
        mt = mt.decode('utf-8')
    if mt not in WHITELIST_MIMETYPES:
        if mt.startswith('text/'):
            mt = 'text/plain'
        else:
            mt = 'application/octet-stream'
    return mt


@upload.route('/uploads/<path:relfilename>')
def get_upload(relfilename: str):
    mt, up = get_pluginupload(relfilename)
    return send_file(up.filesystem_path.as_posix(), mimetype=mt, add_etags=False)


def get_pluginupload(relfilename: str) -> Tuple[str, PluginUpload]:
    slashes = relfilename.count('/')
    if slashes < 2:
        raise RouteException()
    if slashes == 2:
        relfilename += '/'
    if slashes == 3 and not relfilename.endswith('/'):
        raise RouteException('Incorrect filename specification.')
    block = Block.query.filter((Block.description.startswith(relfilename)) & (
            Block.type_id == BlockType.Upload.value)).order_by(Block.description.desc()).first()
    if not block or (block.description != relfilename and not relfilename.endswith('/')):
        raise RouteException('The requested upload was not found.')
    if not verify_view_access(block, require=False):
        answerupload = block.answerupload.first()

        # Answerupload may only be None for early test uploads (before the AnswerUpload model was implemented)
        # or if the upload process was interrupted at a specific point
        if answerupload is None:
            raise AccessDenied()
        answer = answerupload.answer
        if not answer:
            raise RouteException('Upload has not been associated with any answer; it should be re-uploaded')
        tid = TaskId.parse(answer.task_id)
        d = get_doc_or_abort(tid.doc_id)
        if not verify_seeanswers_access(d, require=False) and get_current_user_object() not in answer.users_all:
            raise AccessDenied("Sorry, you don't have permission to access this upload.")

    up = PluginUpload(block)
    p = up.filesystem_path.as_posix()
    mt = get_mimetype(p)
    return mt, up


# noinspection PyUnusedLocal
@upload.route('/pluginUpload/<int:doc_id>/<task_id>/<user_id>/', methods=['POST'])
def pluginupload_file2(doc_id: int, task_id: str, user_id):
    return pluginupload_file(doc_id, task_id)


def is_pdf_producer_ghostscript(f: UploadedFile):
    r = subprocess.run(
        [
            'pdftk',
            f.filesystem_path,
            'dump_data_utf8',
        ],
        capture_output=True,
    )
    stdout = r.stdout.decode()

    # If the producer is Ghostscript, InfoValue contains also Ghostscript version, but let's not hardcode it here.
    result = '\nInfoBegin\nInfoKey: Producer\nInfoValue: GPL Ghostscript ' in stdout
    return result


def compress_pdf(f: UploadedFile):

    # If the PDF producer is Ghostscript, let's assume this PDF has already been compressed.
    # It's unlikely that any end user uses it.
    if is_pdf_producer_ghostscript(f):
        return

    p = f.filesystem_path
    orig = p.rename(p.with_name(p.stem + '_original.pdf'))
    subprocess.run([
        'gs',
        '-q',
        '-dNOPAUSE',
        '-dBATCH',
        '-dSAFER',
        '-dSimulateOverprint=true',
        '-sDEVICE=pdfwrite',
        '-dPDFSETTINGS=/ebook',
        '-dEmbedAllFonts=true',
        '-dSubsetFonts=true',
        '-dAutoRotatePages=/None',
        '-dColorImageDownsampleType=/Bicubic',
        '-dColorImageResolution=150',
        '-dGrayImageDownsampleType=/Bicubic',
        '-dGrayImageResolution=150',
        '-dMonoImageDownsampleType=/Bicubic',
        '-dMonoImageResolution=150',
        f'-sOutputFile={p}',
        orig,
    ])
    orig.unlink()


@upload.route('/pluginUpload/<int:doc_id>/<task_id>/', methods=['POST'])
def pluginupload_file(doc_id: int, task_id: str):
    d = get_doc_or_abort(doc_id)
    try:
        tid = TaskId.parse(task_id, require_doc_id=False, allow_block_hint=False)
    except PluginException:
        return abort(400)
    tid.doc_id = d.id
    verify_task_access(d, tid, AccessType.view, TaskIdAccess.ReadWrite)
    file = request.files.get('file')
    if file is None:
        abort(400, 'Missing file')
    content = file.read()
    u = get_current_user_object()
    f = UploadedFile.save_new(
        content,
        file.filename,
        BlockType.Upload,
        upload_info=PluginUploadInfo(
            task_id_name=task_id,
            user=u,
            doc=d))
    f.block.set_owner(u.get_personal_group())
    grant_access_to_session_users(f)
    mt = get_mimetype(f.filesystem_path.as_posix())
    if mt == 'application/pdf':
        compress_pdf(f)
    db.session.commit()
    return json_response(
        {
            "file": (Path('/uploads') / f.relative_filesystem_path).as_posix(),
            "type": mt,
            "block": f.id,
        })


@upload.route('/upload/', methods=['POST'])
def upload_file():
    if not logged_in():
        abort(403, 'You have to be logged in to upload a file.')
    file = request.files.get('file')
    if file is None:
        abort(400, 'Missing file')
    folder = request.form.get('folder')
    if folder is not None:
        return upload_document(folder, file)
    doc_id = request.form.get('doc_id')
    if not doc_id:
        abort(400, 'Missing doc_id')
    d = DocEntry.find_by_id(int(doc_id))
    verify_edit_access(d)
    try:
        attachment_params = json.loads(request.form.get('attachmentParams'))
        autostamp = attachment_params[len(attachment_params) - 1]
    except:
        # Just go on with normal upload if necessary conditions are not met.
        return upload_image_or_file(d, file)
    else:
        if autostamp:
            # Only go here if attachment params are valid enough and autostamping is valid and true
            # because otherwise normal uploading may be interrupted.
            if len(attachment_params) < 6:
                raise StampDataInvalidError("Request missing parameters", attachment_params)
            try:
                stamp_format = attachment_params[1]
                # If stampformat is empty (as it's set to be if undefined in pareditor.ts), use default.
                if not stamp_format:
                    stamp_format = default_stamp_format
                stamp_data = AttachmentStampData(date=attachment_params[0],
                                                 attachment=attachment_params[3],
                                                 issue=attachment_params[4])
                custom_stamp_model = attachment_params[len(attachment_params) - 2]
                return upload_and_stamp_attachment(d, file, stamp_data, stamp_format, custom_stamp_model)
            # If attachment isn't a pdf, gives an error too (since it's in 'showPdf' plugin)
            except PdfError as e:
                abort(400, str(e))


@dataclass
class AttachmentModel:
    issueNumber: int
    attachmentLetter: str
    uploadUrl: str
    upToDate: Optional[bool] = None


@dataclass
class RestampModel:
    attachments: List[AttachmentModel]
    meetingDate: str
    stampFormat: Optional[str] = None
    customStampModel: Optional[str] = None


@upload.route('/upload/restamp', methods=['POST'])
@use_model(RestampModel)
def restamp_attachments(args: RestampModel):
    """
    Route for updating stamps for one or more uploaded attachments.
    :return: Ok response or an error in stamping process.
    """
    attachments, meeting_date, stamp_format, custom_stamp_model_content = args.attachments, args.meetingDate, args.stampFormat, args.customStampModel

    if not stamp_format:
        stamp_format = default_stamp_format
    stamp_data_list = []
    attachment_folder = default_attachment_folder
    for a in attachments:
        stamp_data = AttachmentStampData(date=meeting_date,
                                         attachment=a.attachmentLetter,
                                         issue=a.issueNumber)
        # Parse link path and find unstamped attachment.
        # In case of errors abort the whole process.
        attachment_path = PurePosixPath(unquote(urlparse(a.uploadUrl).path))
        try:
            stamp_data.file = attachment_folder / attachment_path.parts[-2] / attachment_path.parts[-1].replace("_stamped","")
        except IndexError:
            abort(400, f'Invalid attachment url: "{attachment_path}"')
        file = UploadedFile.find_by_id(attachment_path.parts[-2])
        if not file:
            abort(400, f'Attachment not found: "{attachment_path}"')

        verify_edit_access(file, check_parents=True)
        stamp_data_list.append(stamp_data)

    stamp_model_path = create_tex_file(custom_stamp_model_content) if custom_stamp_model_content else stamp_model_default_path
    stamp_pdfs(
        stamp_data_list,
        stamp_text_format=stamp_format,
        stamp_model_path=stamp_model_path,
    )

    return ok_response()


def upload_document(folder, file):
    path = posixpath.join(folder, os.path.splitext(secure_filename(file.filename))[0])

    content = validate_uploaded_document_content(file)
    validate_item_and_create_intermediate_folders(path, BlockType.Document, get_current_user_group_object())

    doc = import_document(content, path, get_current_user_group_object())
    db.session.commit()
    return json_response({'id': doc.doc_id})


def upload_and_stamp_attachment(d: DocInfo, file, stamp_data: AttachmentStampData, stampformat: str,
                                custom_stamp_model_content: Optional[str] = None):
    """
    Uploads the file and makes a stamped version of it into the same folder.
    :param d: Document info.
    :param file: The file to upload and stamp.
    :param stamp_data: Stamp data object (attachment and list ids) without the path.
    :param stampformat: Formatting of stamp text.
    :param custom_stamp_model_content: LaTeX-string for a custom stamp.
    :return: Json response containing the stamped file path.
    """

    attachment_folder = default_attachment_folder
    content = file.read()

    f = save_file_and_grant_access(d, content, file, BlockType.File)

    # Add the uploaded file path (the one to stamp) to stamp data.

    stamp_data.file = attachment_folder / f"{f.id}/{f.filename}"

    stamp_model_path = create_tex_file(
        custom_stamp_model_content) if custom_stamp_model_content else stamp_model_default_path
    output = stamp_pdfs(
        [stamp_data],
        stamp_text_format=stampformat,
        stamp_model_path=stamp_model_path)[0]

    stamped_filename = output.name
    db.session.commit()

    # TODO: In case of raised errors give proper no-upload response?
    return json_response({"file": f"{str(f.id)}/{stamped_filename}"})


def upload_image_or_file(d: DocInfo, file):
    content = file.read()
    imgtype = imghdr.what(None, h=content)
    type_str = 'image' if imgtype else 'file'
    f = save_file_and_grant_access(d, content, file, BlockType.from_str(type_str))
    db.session.commit()
    return json_response({type_str: f'{f.id}/{f.filename}'})


def save_file_and_grant_access(d: DocInfo, content, file, block_type: BlockType) -> UploadedFile:
    f = UploadedFile.save_new(content, file.filename, block_type)
    f.block.set_owner(get_current_user_object().get_personal_group())
    d.block.children.append(f.block)
    return f


@upload.route('/files/<int:file_id>/<file_filename>')
def get_file(file_id, file_filename):
    f = UploadedFile.get_by_id_and_filename(file_id, file_filename)
    if not f:
        abort(404, 'File not found')
    verify_view_access(f, check_parents=True)
    file_path = f.filesystem_path.as_posix()
    return send_file(file_path, mimetype=get_mimetype(file_path))


@upload.route('/images/<int:image_id>/<image_filename>')
def get_image(image_id, image_filename):
    f = UploadedFile.find_by_id(image_id)
    if not f:
        abort(404, 'Image not found')
    verify_view_access(f, check_parents=True)
    if image_filename != f.filename:
        abort(404, 'Image not found')
    img_data = f.data
    imgtype = imghdr.what(None, h=img_data)
    f = io.BytesIO(img_data)
    return send_file(f, mimetype='image/' + imgtype)
