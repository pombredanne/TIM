from subprocess import Popen, PIPE, run as subprocess_run
from os import remove, path as os_path
from typing import Union, List
# from uuid import uuid4
from urllib import request as url_request
from urllib.error import HTTPError

"""
Stamping and merging pdf-files with pdftk and pdflatex

Visa Naukkarinen
"""

# Default parameter values:
# temp_folder_default_path = "/tmp"
temp_folder_default_path = "static/testpdf"
stamp_model_default_path = "static/tex/stamp_model.tex"
# default format for stamp text
default_stamp_format = "Kokous {1}\n\nLiite {2} lista {3}"
# how long (seconds) subprocess can take until TimeoutExpired
default_subprocess_timeout = 10
pdfmerge_timeout = 300

##############################################################################
# Custom error classes:


class PdfError(Exception):
    """
    Inherited by all the other custom errors pdftools-module uses.
    """
    pass


class ModelStampMissingError(PdfError):
    """
    Raised if model tex-file for creating stamps can't be found.
    """

    def __init__(self, file_path: str = ""):
        """
        :param file_path:
        """
        self.file_path = file_path


class ModelStampInvalidError(PdfError):
    """
    Raised if model tex-file for creating stamps is broken,
    """

    def __init__(self, file_path: str = ""):
        """
        :param file_path:
        """
        self.file_path = file_path


class TempFolderNotFoundError(PdfError):
    """
    Raised if the folder for temporary files is missing
    """

    def __init__(self, folder_path: str = ""):
        """
        :param folder_path:
        """
        self.folder_path = folder_path


class AttachmentNotFoundError(PdfError):
    """
    Raised when at least one pdf file in input data is missing.
    """

    def __init__(self, file_path: str = ""):
        """
        :param file_path: path of the attachment pdf that caused the error
        """
        self.file_path = file_path


class StampFileNotFoundError(PdfError):
    """
    Raised when stamp to use is missing.
    """

    def __init__(self, file_path: str = ""):
        """
        :param file_path: path of the stamp file that caused the error
        """
        self.file_path = file_path


class StampDataInvalidError(PdfError):
    """
    Raised if stamp data type is wrong
    """

    def __init__(self, reason: str = "", item: Union[str, dict, List[dict]] = ""):
        """
        :param reason: error cause
        :param item: item or data that caused the error
        """
        self.reason = reason
        self.item = item

    def __str__(self):
        return self.reason + ": " + repr(self.item)


class StampDataMissingKeyError(PdfError):
    """
    Raised when stamp data is missing one or more required keys.
    """

    def __init__(self, key: str = "", item: Union[str, dict] = ""):
        """
        :param key: the missing key
        :param item: the dict item which caused the error
        """
        self.key = key
        self.item = item

    def __str__(self):
        return repr(self.key) + " not found: " + repr(self.item)


class StampDataEmptyError(PdfError):
    """
    Raised if input data is an empty list.
    """
    pass


class SubprocessError(PdfError):
    """
    Raised when subprocesses (pdftk, pdflatex, possibly others) return
    error code or otherwise raise exception.
    """

    def __init__(self, cmd: str = ""):
        self.cmd = cmd


##############################################################################
# Functions:


def merge_pdf(pdf_path_list: List[str], output_path: str) -> str:
    """
    Merges a list of pdfs using pdftk
    :param pdf_path_list: list of pdfs to merge OR
           a string with paths separated with spaces
    :param output_path: merged output file path
    :return: output_path
    """
    args = ["pdftk"] + pdf_path_list + ["cat", "output", output_path]
    print(args)
    # raise SubprocessError is done twice because Popen raises
    # FileNotFoundError in some cases and skips the return code check
    call_popen(args, pdfmerge_timeout)
    return output_path


def get_stamp_text(
        item: dict,
        text_format: str = default_stamp_format) -> str:
    """
    Gives formatted stamp text; note: may not work properly with non-ascii
    :param item: dictionary with 'date','attachment' and 'issue' keys
           or alternatively just 'text'
    :param text_format: formatting for file=0, date=1, attachment=2 and
           issue=3 keys
    :return: either contents of 'text' key or a formatted string
    """
    # normal formatted stamp data takes precedence
    try:
        return text_format.format(
            item['file'],
            item['date'],
            item['attachment'],
            item['issue'])
    # if stamp data has only a free-form text, use that
    except KeyError:
        try:
            return item['text']
        # if dictionary doesn't have 'text'-key either;
        # normally this part is obsolete, since checks have been done before
        except KeyError:
            raise StampDataMissingKeyError('text', item)
    # if input data wasn't a dictionary
    except TypeError:
        raise StampDataInvalidError("wrong type", item)


def create_stamp(
        model_path: str,
        work_dir: str,
        stamp_name: str,
        text: str,
        remove_pdflatex_files: bool=False) -> str:
    """
    Creates a stamp pdf-file with given text into temp folder
    :param model_path: model stamp tex-file's complete path; contains
           '%TEXT_HERE' to locate the text area
    :param work_dir: the folder where stamp output and temp files will be
    :param stamp_name: name of the stamp and temp files (no file extension)
    :param text: text displayed in the stamp
    :param remove_pdflatex_files: if true, newly created .aux, .log, .out and
           .tex files will be deleted
    :return: complete path of the created stamp pdf-file
    """
    try:
        stamp_model = open(model_path, "r")

    # raises custom error if stamp_model is missing
    except FileNotFoundError:
        raise ModelStampMissingError()

    with stamp_model, open(os_path.join(work_dir, stamp_name + ".tex"),
                           "w+", encoding='utf-8') as stamp_temp:
        try:
            for line in stamp_model:
                if "%TEXT_HERE" in line:
                    stamp_temp.write(text)
                else:
                    stamp_temp.write(line)
        # if stamp_model file is broken
        # TODO: check if failure to write a new stamp file raises proper error
        except UnicodeDecodeError:
            raise ModelStampInvalidError(model_path)
    args = ["pdflatex", stamp_name]
    print(args)

    # directs pdflatex text flood to the log-file pdflatex will create anyway
    with open(os_path.join(work_dir, stamp_name + ".log"), "a") as pdflatex_log:
        try:
            # pdflatex can't write files outside of work dir so use cwd
            rc = subprocess_run(
                args,
                stdout=pdflatex_log,
                cwd=work_dir,
                timeout=default_subprocess_timeout
            ).returncode
            if rc != 0:
                raise SubprocessError(" ".join(args))
        except FileNotFoundError:
            raise SubprocessError(" ".join(args))

    # optional; delete the files pdflatex created, except the stamp-pdf file,
    # which is obviously needed for stamping
    if remove_pdflatex_files:
        remove_temp_files(
            work_dir,
            stamp_name,
            [".aux", ".log", ".out", ".tex"])
    return work_dir + stamp_name + ".pdf"


def stamp_pdf(
        pdf_path: str, stamp_path: str, output_path: str,
        remove_stamp: bool = False) -> str:
    """
    Creates a new stamped pdf file (with stamp overlay on each page)
    :param pdf_path:
    :param stamp_path:
    :param output_path:
    :param remove_stamp: delete stamp file after use
    :return: output_path
    """
    if not os_path.exists(pdf_path):
        raise AttachmentNotFoundError(pdf_path)
    if not os_path.exists(stamp_path):
        raise StampFileNotFoundError(stamp_path)
    args = ["pdftk", pdf_path, "stamp", stamp_path, "output", output_path]
    print(args)
    call_popen(args)

    # optionally clean up the stamp-pdf after use
    if remove_stamp:
        remove(stamp_path)
    return output_path


def call_popen(args: List[str], timeout_seconds=default_subprocess_timeout) -> None:
    """
    Calls Popen with args list, checks return code and
    raises error if timeouted.
    :param args: List of arguments
    :param timeout_seconds: timeout after which error is raised
    :return: None
    """
    try:
        p = Popen(args, stdout=PIPE)
        stream_data = p.communicate(timeout=timeout_seconds)[0]
        print(str(stream_data))
        rc = p.returncode
        if rc != 0:
            raise SubprocessError(" ".join(args))
    except FileNotFoundError:
        raise SubprocessError(" ".join(args))


def remove_temp_files(
        dir_path: str, temp_file_name: str, ext_list: List[str]) -> None:
    """
    Deletes temp files created for the stamping process
    :param dir_path: temp-file folder path
    :param temp_file_name: common part of the names
    :param ext_list: list of extensions after common part for files to remove
    :return: None
    """
    # fail_list = []
    for ext in ext_list:
        try:
            remove(os_path.join(dir_path, temp_file_name + ext))
        # removes the rest of files even if some are missing
        except FileNotFoundError:
            # fail_list.append(path.join(dir_path, temp_file_name + ext))
            continue
    # return fail_list


def check_stamp_data_validity(stamp_data: List[dict]) -> None:
    """
    Raises a specific error if stamp_data is invalid
    :param stamp_data:
    :return:
    """
    # not a list
    if type(stamp_data) is not list:
        raise StampDataInvalidError("is not a list", stamp_data)
    # if empty
    if not stamp_data:
        raise StampDataEmptyError()
    for item in stamp_data:
        # if there are no dictionaries inside the list
        if type(item) is not dict:
            raise StampDataInvalidError("is not a dictionary", item)
        # path is always required
        if "file" not in item:
            raise StampDataMissingKeyError("file", item)
        # if missing a pdf-file
        if not os_path.exists(item["file"]):
            raise AttachmentNotFoundError(item["file"])
        # text or date, attachment & issue are alternatives
        if "text" not in item:
            if "date" not in item:
                raise StampDataMissingKeyError("date", item)
            if "attachment" not in item:
                raise StampDataMissingKeyError("attachment", item)
            if "issue" not in item:
                raise StampDataMissingKeyError("issue", item)


def is_url(string: str) -> bool:
    """
    Simple test to see if str is url
    :param string:
    :return:
    """
    # TODO: check special cases
    if string.startswith("http"):
        return True
    else:
        return False


def download_file_from_url(
        url: str,
        output_dir: str = temp_folder_default_path) -> str:
    """
    Downloads a file from url, keeps the filename same.
    :param url: file url
    :param output_dir: download folder
    :return: path of the saved file
    """
    try:
        output_path = os_path.join(output_dir, get_base_filename(url))
        url_request.urlretrieve(url, output_path)
        return output_path
    except HTTPError:
        raise AttachmentNotFoundError(url)


def get_base_filename(path: str, no_extension: bool = False) -> str:
    """
    Returns filename with or without file extension from url or path.
    :param path: url or path to parse
    :param no_extension: keep the extension included
    :return: the file's basename, extension is optional
    """
    if no_extension:
        return os_path.splitext(os_path.basename(path))[0]
    else:
        return os_path.basename(path)


def stamp_merge_pdfs(
        stamp_data: List[dict],
        merged_file_path: str,
        dir_path: str = temp_folder_default_path,
        stamp_model_path: str = stamp_model_default_path,
        merge: bool = True) -> Union[str, List[str]]:
    """
    Creates stamps, stamps pdf-files and merges them into a single file.
    :param stamp_data: dict-list containing pdf-names and stamp-contents
    :param merged_file_path: path the merged pdf-file shall have
    :param dir_path: folder for temp files
    :param stamp_model_path: tex-file to be used as model for stamps
    :param merge
    :return: merged_file_path or list of stamped
    """
    # uses 128-bit random string as temp name!
    # temp_file_name = str(uuid4()) + "_"
    # a number counter to separate subsequent temp files
    # counter = 0

    # string that will have all stamped pdf paths (for pdftk)
    pdfs_to_merge = []

    # creates a new stamp and stamps the corresponding pdfs based on
    # the data-item in dictionary
    # check if temp-folder exists
    if not (os_path.isdir(dir_path) and os_path.exists(dir_path)):
        raise TempFolderNotFoundError(dir_path)

    # check if model stamp exists
    if not os_path.exists(stamp_model_path):
        raise ModelStampMissingError(stamp_model_path)

    # checks multiple potential problems and raises error if invalid
    check_stamp_data_validity(stamp_data)

    for item in stamp_data:
        # TODO: check for duplicate file names and add numbers to avoid conflicts
        # TODO: option to use random names for stamp or stamped files

        # names and paths of new files to use as params
        item_basename = get_base_filename(item['file'], True)
        item_stamp_name_no_ext = item_basename + "_stamp"
        item_stamp_path = os_path.join(dir_path, item_stamp_name_no_ext + ".pdf")
        item_stamped_name = item_basename + "_stamped.pdf"
        item_stamped_path = os_path.join(dir_path, item_stamped_name)

        # set
        create_stamp(stamp_model_path,
                     dir_path,
                     item_stamp_name_no_ext,
                     get_stamp_text(item),
                     remove_pdflatex_files=True)

        # set to remove stamp-pdf after use
        stamp_pdf(item['file'],
                  item_stamp_path,
                  item_stamped_path,
                  remove_stamp=True)

        # adds the created stamp's path to be used by the merge command
        pdfs_to_merge.append(item_stamped_path)

    # TODO: returns both the merged file and stamped individual files (tuple?)
    if merge:
        merge_pdf(pdfs_to_merge, merged_file_path)
        return merged_file_path
    else:
        return pdfs_to_merge

##############################################################
# Testing/examples (may be outdated):


"""
data = [
    # normal case
    {"file": "C:/Testi/testi1.pdf", "date": "20.12.2009", "attachment": "A", "issue": "2"},
    # allowed case
    {"file": "C:/Testi/testi2.pdf", "text": "Sample text \\newline with some LaTeX \\newline formatting"},
    # text will go out of bounds a little, but will compile
]

output = "C:/Testi/merged.pdf"

# Error test cases:

stamp_merge_pdfs("banana", output)
stamp_merge_pdfs([], output)
stamp_merge_pdfs(["banana"], output)
stamp_merge_pdfs([{"path": "C:/Testi/testi2.pdf", "banana": "If this ends up\nin stamp, it's a mistake!"}], output)
stamp_merge_pdfs([{"path": "C:/Testi/broken.pdf", "text": "If this ends up\nin stamp, it's a mistake!"}], output)
stamp_merge_pdfs([{"path": "C:/Testi/i_don't_exist.pdf", "text": "If this ends up\nin stamp, it's a mistake!"}], output)

# Real cases:
print(stamp_merge_pdfs(data, output, merge=True))


create_stamp(
    "C:/Testi/stamp_model.tex",
    "C:/Testi",
    "stamp",
    get_stamp_text(data[0], "Kokous {1}\n\nLIITE {2} lista {3}"))
stamp_pdf("C:/Testi/testi1.pdf","C:/Testi/stamp.pdf","C:/Testi/stamped.pdf")

"""
