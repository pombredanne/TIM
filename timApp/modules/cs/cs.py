# -*- coding: utf-8 -*-
import datetime
import http.server
import io
import logging
import signal
import socketserver
import threading
from languages import *
import pwd, os
import glob
from base64 import b64encode

#  uid = pwd.getpwnam('agent')[2]
#  os.setuid(uid)

# cs.py: WWW-palvelin portista 5000 (ulospäin 56000) joka palvelee csPlugin pyyntöjä
#
# Uuden kielen lisäämiseksi
# 1. Mene tiedostoon languges.py ja kopioi sieltä luokka
#        class Lang(Language):
#      ja vaihda sille nimi, toteuta metodit  ja lisää myös languages-sanastoon.
# 2. Tee tarvittava lisäys myös js/dir.js tiedoston kieliluetteloon.
# 3. Lisää kielen kääntäjä/tulkki vastaavaan konttiin, ks. Dockerfile
#
# Ensin käynistettävä
# ./startPlugins.sh             - käynnistää dockerin cs.py varten
# ./startAll.sh                 - ajetaan dockerin sisällä cs.py (ajetaan edellisestä)
# Muut tarvittavat skriptit:
# rcmd.sh          - käynistetään ajettavan ohjelman kontin sisälle ajamaan
# cs.py tuottama skripti
#
# Hakemistot:
#  tim-koneessa
#     /opt/cs               - varsinainen csPluginin hakemisto, skirptit yms
#     /opt/cs/templates     - pluginin templatet editoria varten
#     /opt/cs/java          - javan tarvitsemat tavarat
#     /opt/cs/images/cs     - kuvat jotka syntyvät csPlugin ajamista ohjelmista
#     /opt/cs/jypeli        - jypelin tarvitsemat tiedostot
#     /tmp/uhome            - käyttäjän hakemistoja ohjelmien ajamisen ajan
#     /tmp/uhome/user       - käyttäjän hakemistoja ohjelmien ajamisen ajan
#     /tmp/uhome/user/HASH  - yhden käyttäjän hakemisto joka säilyy ajojen välillä
#
# tim-koneesta käynnistetään cs docker-kontti nimelle csPlugin (./startPlugins.sh), jossa
# mountataan em. hakemistoja seuraavasti:
#
#   /opt/cs  ->          /cs/          read only
#   /opt/cs/images/cs -> /csimages/    kuvat
#   /tmp/uhome:       -> /tmp/         käyttäjän jutut tänne
#
# Käyttäjistä (csPlugin-kontissa) tehdään /tmp/user/HASHCODE
# tai /tmp/HASHCODE nimiset hakemistot (USERPATH=user/HASHCODE tai HASHCODE),
# joihin tehdään ohjelmien käännökset ja joista ohjelmat ajetaan.
# HASHCODE = käyttäjätunnuksesta muodostettu hakemiston nimi.
# Mikäli käyttäjätunnusta ei ole, on tiedoston nimi satunnainen.
#
# Kääntämisen jälkeen luodaan /tmp/USERPATH hakemistoon
# täydellinen ajokomento run/URNDFILE.sh
# Tämä jälkeen tehdään /tmp/run -hakemistoon tiedosto
# RNDNAME johon on kirjoitettu "USERPATH run/URNDFILE.sh"
# Tähän ajokonttiin mountataan tim-koneesta
#  (udir = userhash + "/"  + docid  jos on path: user)
#
#   /opt/cs          -> /cs/          read only
#   /tmp/uhome/udir  -> /home/agent   käyttäjän "kotihakemisto"
#
# Docker-kontin käynnistyessä suoritetaan komento /cs/rcmd.sh
# (TIMissä /opt/cs/rcmd.sh)
# joka alustaa "näytön" ja luo sopivat ympäristömuuttajat mm.
# javan polkuja varten ja sitten vaihtaa hakemistoon /home/agent
# ja ajaa sieltä komennon ./run/URNDFILE.sh
# stdout ja stderr tulevat tiedostoihin ./run/URNDFILE.in ja ./run/URNDFILE.err
# Kun komento on ajettu, docker-kontti häviää.  Ajon lopuksi tuohotaan
# ./run/URNDFILE.sh
# ja kun tämä on hävinnyt, luetaan stdin ja stderr ja tiedot lähetetään
# selaimelle (Timin kautta)
#

PORT = 5000


def generate_filename():
    return str(uuid.uuid4())


def get_process_children(pid):
    p = Popen('ps --no-headers -o pid --ppid %d' % pid, shell=True,
              stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    return [int(p) for p in stdout.split()]


def print_lines(file, lines, n1, n2):
    linefmt = "{0:03d} "
    n = len(lines)
    if n1 < 0:
        n1 = 0
    if n2 >= n:
        n2 = n - 1

    for i in range(n1, n2 + 1):
        line = lines[i]
        ln = linefmt.format(i + 1)
        file.write((ln + line + "\n"))


def write_json_error(file, err, result, points_rule=None):
    return_points(points_rule, result)

    result["web"] = {"error": err}
    result_str = json.dumps(result)
    file.write(result_str.encode())
    print("ERROR:======== ", err.encode("UTF8"))
    print(result_str)


def removedir(dirname):
    # noinspection PyBroadException
    try:
        # os.chdir('/tmp')
        shutil.rmtree(dirname)
    except:
        return


def save_extra_files(query, extra_files, prgpath):
    if not extra_files:
        return
    ie = 0
    for extra_file in extra_files:
        ie += 1
        efilename = prgpath + "/extrafile" + str(ie)
        if "name" in extra_file:
            efilename = prgpath + "/" + extra_file["name"]

        mkdirs(os.path.dirname(efilename))
        if "text" in extra_file:
            # noinspection PyBroadException
            try:
                s = replace_random(query, extra_file["text"])
                codecs.open(efilename, "w", "utf-8").write(s)
            except:
                print("Can not write", efilename)
        if "file" in extra_file:
            try:
                if extra_file.get("type", "") != "bin":
                    lines = get_url_lines_as_string(replace_random(query, extra_file["file"]))
                    codecs.open(efilename, "w", "utf-8").write(lines)
                else:
                    open(efilename, "wb").write(urlopen(extra_file["file"]).read())
            except Exception as e:
                print(str(e))
                print("XXXXXXXXXXXXXXXXXXXXXXXX Could no file cache: \n", efilename)


def delete_extra_files(extra_files, prgpath):
    if not extra_files:
        return
    ie = 0
    for extra_file in extra_files:
        ie += 1
        if extra_file.get("delete", False):
            efilename = prgpath + "/extrafile" + str(ie)
            if "name" in extra_file:
                efilename = prgpath + "/" + extra_file["name"]
            # noinspection PyBroadException
            try:
                os.remove(efilename)
            except:
                print("Can not delete: ", efilename)


def get_md(ttype, query):
    tiny = False

    if query.hide_program:
        get_param_del(query, 'program', '')

    js = query_params_to_map_check_parts(query)
    if "byFile" in js and not ("byCode" in js):
        js["byCode"] = get_url_lines_as_string(
            js["byFile"])  # TODO: Tähän niin että jos tiedosto puuttuu, niin parempi tieto
    bycode = ""
    if "by" in js:
        bycode = js["by"]
    if "byCode" in js:
        bycode = js["byCode"]
    if get_param(query, "noeditor", False):
        bycode = ""

    qso = json.dumps(query.jso)
    # print(qso)
    uf = get_param(query, "uploadedFile", None)
    ut = get_param(query, "uploadedType", None)
    uf = get_json_eparam(query.jso, "state", "uploadedFile", uf)
    ut = get_json_eparam(query.jso, "state", "uploadedType", ut)
    if uf and ut:
        js["uploadedFile"] = uf
        js["uploadedType"] = ut

    jso = json.dumps(js)
    # print(jso)
    runner = 'cs-runner'
    # print(ttype)
    is_input = ''
    if "input" in ttype or "args" in ttype:
        is_input = '-input'
    if "comtest" in ttype or "junit" in ttype:
        runner = 'cs-comtest-runner'
    if "tauno" in ttype:
        runner = 'cs-tauno-runner'
    if "simcir" in ttype:
        runner = 'cs-simcir-runner'
        bycode = ''
    if "tiny" in ttype:
        runner = 'cs-text-runner'
        tiny = True
    if "parsons" in ttype:
        runner = 'cs-parsons-runner'
    if "jypeli" in ttype or "graphics" in ttype or "alloy" in ttype:
        runner = 'cs-jypeli-runner'
    if "sage" in ttype:
        runner = 'cs-sage-runner'
    if "wescheme" in ttype:
        runner = 'cs-wescheme-runner'

    usercode = None
    user_print = get_json_param(query.jso, "userPrint", None, False)
    if user_print:
        usercode = get_json_eparam(query.jso, "state", "usercode", None, False)
    if usercode is None:
        usercode = bycode

    r = runner + is_input

    if "csconsole" in ttype:  # erillinen konsoli
        r = "cs-console"

    # s = '\\begin{verbatim}\n' + usercode + '\n\\end{verbatim}'
    header = str(get_param(query, "header", ""))
    stem = str(get_param(query, "stem", ""))
    footer = str(get_param(query, "footer", ""))

    rows = get_param(query, "rows", None)

    target_format = get_param(query, "targetFormat", 'latex')

    if target_format == 'html':
        s = '''
<h4>{}</h4>
<p>{}</p>
<pre>
{}
</pre>
<p>{}</p>
'''.format(header, stem, usercode, footer)
        return s

    if target_format == 'md':
        s = '''
#### {}
{}
```
{}
```
{}
'''.format(header, stem, usercode, footer)
        return s

    if target_format == "latex":
        code = '\\begin{lstlisting}\n' + \
               str(usercode) + '\n' + \
               '\\end{lstlisting}\n'

        if 'text' in ttype and rows is not None and str(usercode) == '':
            r = ''  # for text make a verbatim with number of rows empty lines
            rows = str_to_int(rows, 1)
            for i in range(0, rows):
                r += "\n"
            code = '\\begin{verbatim}\n' + \
                   r + \
                   '\\end{verbatim}\n'

        s = '\\begin{taskenv}{' + header + '}{' + stem + '}{' + footer + '}' + \
            '\\lstset{language=[Sharp]C, numbers=left}\n' + \
            code + \
            '\\end{taskenv}'

        return s

    # plain
    s = '''
{0}

{1}

{2}

{3}
'''.format(header, stem, usercode, footer)
    return s


def min_sanitaize(s):
    if s.find('<svg') >= 0: return s;
    s = s.replace('<', '&lt;').replace('>', '&gt;')
    return s


def get_html(self, ttype, query):
    if get_param(query, "cache", False): # check if we should take the html from cache
        cache_root = "/tmp"
        cache_clear = get_param(query, "cacheClear", True)
        if not cache_clear:
            cache_root = "/tmp/ucache" # maybe user dependent cacha that may grow bigger, so to different place
        h = hashlib.new('ripemd160')
        h.update(str(query.jso['markup']).encode())
        task_id = get_param(query, "taskID", False)
        filepath = cache_root + '/imgcache/' + task_id.replace('.', '/')
        if filepath.endswith('/'):
            task_id = get_param(query, "taskIDExt", False)
            filepath = '/tmp/imgcache/' + task_id.replace('..', '/')

        contenthash = h.hexdigest()
        filename = filepath + '/' + contenthash + '.html'
        if os.path.isfile(filename):  # if we have cache, use that
            with open(filename, "r") as fh:
                htmldata = fh.read()
            return htmldata

        query.jso['markup']['imgname'] = "/csgenerated/" + task_id # + "/" + hash
        query.jso['state']= None
        ret = self.do_all(query) # otherwise generate new image

        htmldata = NOLAZY

        error = ret['web'].get('error', None)
        if error:
            htmldata += '<div class="error">' + min_sanitaize(error) + '</div>'

        is_html = get_param(query, "isHtml", False)
        default_class = 'console'
        if is_html:
            default_class = 'htmlresult'
        cache_class = get_param(query, "cacheClass", default_class)

        cache_elem = 'div'
        if cache_class == 'console':
            cache_elem = 'pre'

        if cache_class:
            cache_class = 'class="' + min_sanitaize(cache_class) + '"'

        console = ret['web'].get('console', None)
        if console:
            if not is_html:
                console = min_sanitaize(console)
            htmldata += '<' + cache_elem + ' ' + cache_class + '>' + console + '</'+ cache_elem+'>'

        img = ret['web'].get('image', None)
        if img:
            with open(img,"rb") as fh:
                pngdata = fh.read()
            pngenc = b64encode(pngdata)
            htmldata += '<img src="data:image/png;base64, ' + pngenc.decode() + '" />'
            os.remove(img)

        cache_footer = get_param(query, "cacheFooter", "")
        if not cache_footer:
            cache_footer = get_param(query, "footer", "")

        if cache_footer:
            htmldata += '<figcaption>' + cache_footer + '</figcaption>'


        if cache_clear:
            files = glob.glob(filepath+'/*')
            for f in files:
                os.remove(f)

        os.makedirs(filepath, exist_ok = True)

        with open(filename,"w") as fh:
            fh.write(htmldata)

        # return '<img src="' + img + '">'
        return htmldata

    user_id = get_param(query, "user_id", "--")
    tiny = False
    # print("UserId:", user_id)
    if user_id == "Anonymous":
        allow_anonymous = str(get_param(query, "anonymous", "false")).lower()
        jump = get_param(query, "taskID", "")
        # print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX jump: ", jump)
        if allow_anonymous != "true":
            return (NOLAZY + '<p class="pluginError"><a href="/login?anchor=' + jump +
                    '">Please login to interact with this component</a></p><pre class="csRunDiv">' +
                    get_param(query, "byCode", "") + '</pre>')
    do_lazy = is_lazy(query)
    # do_lazy = False
    # print("do_lazy",do_lazy,type(do_lazy))

    if query.hide_program:
        get_param_del(query, 'program', '')

    js = query_params_to_map_check_parts(query)
    # print(js)
    if "byFile" in js and not ("byCode" in js):
        js["byCode"] = get_url_lines_as_string(js["byFile"])
        # TODO: Tähän niin että jos tiedosto puuttuu, niin parempi tieto
    bycode = ""
    if "byCode" in js:
        bycode = js["byCode"]
    if get_param(query, "noeditor", False):
        bycode = ""

    qso = json.dumps(query.jso)
    # print(qso)
    uf = get_param(query, "uploadedFile", None)
    ut = get_param(query, "uploadedType", None)
    uf = get_json_eparam(query.jso, "state", "uploadedFile", uf)
    ut = get_json_eparam(query.jso, "state", "uploadedType", ut)
    if uf and ut:
        js["uploadedFile"] = uf
        js["uploadedType"] = ut

    jso = json.dumps(js)
    # jso)
    runner = 'cs-runner'
    # print(ttype)
    is_input = ''
    if "input" in ttype or "args" in ttype:
        is_input = '-input'
    if "comtest" in ttype or "junit" in ttype:
        runner = 'cs-comtest-runner'
    if "tauno" in ttype:
        runner = 'cs-tauno-runner'
    if "simcir" in ttype:
        runner = 'cs-simcir-runner'
        bycode = ''
    if "tiny" in ttype:
        runner = 'cs-text-runner'
        tiny = True
    if "parsons" in ttype:
        runner = 'cs-parsons-runner'
    if "jypeli" in ttype or "graphics" in ttype or "alloy" in ttype:
        runner = 'cs-jypeli-runner'
    if "sage" in ttype:
        runner = 'cs-sage-runner'
    if "wescheme" in ttype:
        runner = 'cs-wescheme-runner'

    usercode = get_json_eparam(query.jso, "state", "usercode", "")
    if is_review(query):
        userinput = get_json_eparam(query.jso, "state", "userinput", None)
        userargs = get_json_eparam(query.jso, "state", "userargs", None)
        uploaded_file = get_json_eparam(query.jso, "state", "uploadedFile", None)
        s = ""
        if userinput is not None:
            s = s + '<p>Input:</p><pre>' + userinput + '</pre>'
        if userargs is not None:
            s = s + '<p>Args:</p><pre>' + userargs + '</pre>'
        if uploaded_file is not None:
            s = s + '<p>File:</p><pre>' + os.path.basename(uploaded_file) + '</pre>'
        if usercode:
            s = '<pre>' + usercode + '</ pre>' + s
        if not s:
            s = "No answer"
        result = NOLAZY + '<div class="review" ng-non-bindable>' + s + '</div>'
        return result

    r = runner + is_input
    s = '<' + r + ' ng-cloak>xxxJSONxxx' + jso + '</' + r + '>'
    # print(s)
    lazy_visible = ""
    lazy_class = ""
    lazy_start = ""
    lazy_end = ""

    if "csconsole" in ttype:  # erillinen konsoli
        r = "cs-console"

    if do_lazy:
        # r = LAZYWORD + r;
        code = bycode
        if usercode:
            code = usercode
        if not isinstance(code, str):
            print("Ei ollut string: ", code, jso)
            code = '' + str(code)
            # ebycode = html.escape(code)
        # ebycode = code.replace("</pre>", "</pre>")  # prevent pre ending too early
        ebycode = code.replace("<", "&lt;").replace(">", "&gt;")
        if tiny:
            lazy_visible = '<div class="lazyVisible csRunDiv csTinyDiv no-popup-menu" >' + get_tiny_surrounding_headers(
                query,
                '' + ebycode + '') + '</div>'
        else:
            lazy_visible = ('<div class="lazyVisible csRunDiv no-popup-menu" >' +
                            get_surrounding_headers(query,
                                                    ('<div class="csRunCode csEditorAreaDiv '
                                                     'csrunEditorDiv csRunArea csInputArea '
                                                     'csLazyPre" ng-non-bindable><pre>') +
                                                    ebycode + '</pre></div>') + '</div>')
        # lazyClass = ' class="lazyHidden"'
        lazy_start = LAZYSTART
        lazy_end = LAZYEND

    if ttype == "c1" or True:  # c1 oli testejä varten ettei sinä aikana rikota muita.
        hx = binascii.hexlify(jso.encode("UTF8"))
        s = lazy_start + '<' + r + lazy_class + ' ng-cloak>xxxHEXJSONxxx' + hx.decode() + '</' + r + '>' + lazy_end
        s += lazy_visible
    return s


def wait_file(f1):
    """Wait until the file is ready or 10 tries has been done.

    :param f1: filename to wait
    :return: sthe file status if it became ready, otherwise False

    """
    count = 0
    while count < 10:
        count += 1
        if os.path.isfile(f1):
            s1 = os.stat(f1)
            if s1.st_size > 50:
                return s1
            print(s1.st_size, " ??????????????????????? ")
        time.sleep(0.05)
    return False


def debug_str(s):
    t = datetime.datetime.now()
    print(t.isoformat(' ') + ": " + s)


def log(self):
    t = datetime.datetime.now()
    agent = " :AG: " + self.headers["User-Agent"]
    if agent.find("ython") >= 0:
        agent = ""
    logfile = "/cs/log.txt"
    try:
        with open(logfile, 'a') as f:
            f.write(t.isoformat(' ') + ": " + self.path + agent + " u:" + self.user_id + "\n")
    except Exception as e:
        print(e)
        return

    return


def replace_code(rules, s):
    result = s
    if not rules:
        return result

    for rule in rules:
        cut_replace, cut_by = get_2_items(rule, "replace", "by", None, "")
        if cut_replace:
            try:
                while True:
                    m = re.search(cut_replace, result, flags=re.S)
                    if not m:
                        break
                    result = result.replace(m.group(1), cut_by)
            except Exception as e:
                msg = str(e)
                if isinstance(e, IndexError):
                    msg = "group () missing"
                result = "replace pattern error: " + msg + "\n" + "Pattern: " + cut_replace + "\n\n" + result
    return result


def check_code(out, err, compiler_output, ttype):
    err = err + compiler_output
    if ttype == "fs":
        err = err.replace(
            "F# Compiler for F# 4.0 (Open Source Edition)\n"
            "Freely distributed under the Apache 2.0 Open Source License\n",
            "")

    if type('') != type(err):
        err = err.decode()
    # if type(out) != type(''): out = out.decode()
    # noinspection PyBroadException
    try:
        if out and out[0] in [254, 255]:
            out = out.decode('UTF16')
        elif type('') != type(out):
            out = out.decode('utf-8-sig')
    except:
        # out = out.decode('iso-8859-1')
        pass

    return out, err


def check_fullprogram(query, cut_errors=False):
    # Try to find fullprogram or fullfile attribute and if found,
    # do program, bycode and replace attributes from that
    query.cut_errors = get_param_table(query, "cutErrors")
    # -cutErrors:
    # - "(\n[^\n]*REMOVEBEGIN.* REMOVEEND[^\n]*)"
    # - "(\n[^\n]*REMOVELINE[^\n]*)"
    if not query.cut_errors:
        query.cut_errors = [{'replace': "(\n[^\n]*REMOVEBEGIN.*? REMOVEEND[^\n]*)", 'by': ""},
                            {'replace': "(\n[^\n]*REMOVELINE[^\n]*)", 'by': ""}]

    query.hide_program = False
    fullprogram = get_param(query, "-fullprogram", None)
    if not fullprogram:
        fullprogram = get_param(query, "fullprogram", None)
    else:
        query.hide_program = True
    if not fullprogram:
        fullfile = get_param(query, "-fullfile", None)
        if not fullfile:
            fullfile = get_param(query, "fullfile", None)
        else:
            query.hide_program = True
        if not fullfile:
            return False
        fullprogram = get_url_lines_as_string(fullfile)
    if not fullprogram:
        return False

    get_param_del(query, 'fullprogram', '')
    get_param_del(query, 'fullfile', '')

    program = fullprogram

    program = replace_random(query, program)
    by_code_replace = [{'replace': "(\\n[^\\n]*DELETEBEGIN.*? DELETEEND[^\\n]*)", 'by': ""}]
    program = replace_code(by_code_replace, program)
    delete_line = [{'replace': "(\n[^\n]*DELETELINE[^\n]*)", 'by': ""}]
    program = replace_code(delete_line, program)
    delete_line = get_param_table(query, "deleteLine")
    if delete_line:
        program = replace_code(delete_line, program)
    m = re.search("BYCODEBEGIN[^\\n]*\n(.*)\n.*?BYCODEEND", program, flags=re.S)
    # m = re.search("BYCODEBEGIN[^\\n]\n(.*)\n.*?BYCODEEND", program, flags=re.S)
    by_code = ""
    if m:
        by_code = m.group(1)
        by_code_replace = [{'replace': "((\n|)[^\\n]*BYCODEBEGIN.*?BYCODEEND[^\\n]*)", 'by': "\nREPLACEBYCODE"}]
    else:  # no BYCODEBEGIN
        m = re.search("BYCODEBEGIN[^\\n]*\n(.*)", program, flags=re.S)
        if m:
            by_code = m.group(1)
            by_code_replace = [{'replace': "((\n|)[^\\n]*BYCODEBEGIN.*)", 'by': "\nREPLACEBYCODE"}]
        else:
            m = re.search("[^\\n]*\n(.*)\n.*?BYCODEEND", program, flags=re.S)
            if m:
                by_code = m.group(1)
                by_code_replace = [{'replace': "((\n|)[^\\n]*.*?BYCODEEND[^\\n]*)", 'by': "\nREPLACEBYCODE"}]
            else:
                by_code = fullprogram
                program = "REPLACEBYCODE"
    program = replace_code(by_code_replace, program)
    if program.startswith("\nREPLACEBYCODE") and not fullprogram.startswith("\n"):
        program = program[1:]  # remove extra \n from begin
    if cut_errors:
        program = replace_code(query.cut_errors, program)
    query.query["replace"] = ["REPLACEBYCODE"]
    query.query["program"] = [program]
    query.query["by"] = [by_code]
    # query.jso.markup["byCode"] = by_code
    # query.jso.markup["program"] = program
    return True


def check_parsons(expect_code, usercode, maxn, notordermatters):
    p = 0
    exlines = expect_code.splitlines()
    exlines = exlines[:maxn]
    usrlines = usercode.splitlines()
    usrlines = usrlines[:maxn]

    if notordermatters:
        for usrline in usrlines:
            for i, exline in enumerate(exlines):
                if usrline == exline:
                    exlines[i] = "XXXXXXXXXXXX"
                    p += 1
                    break
    else:
        for i, exline in enumerate(exlines):
            if i >= len(usrlines):
                break
            if exline == usrlines[i]:
                p += 1

    return p


# see: http://stackoverflow.com/questions/366682/how-to-limit-execution-time-of-a-function-call-in-python
# noinspection PyUnusedLocal
def signal_handler(signum, frame):
    print("Timed out1!")
    raise Exception("Timed out1!")

type_splitter = re.compile("[^a-z0-9]")

class TIMServer(http.server.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, _server):
        # print(request,client_address)
        super().__init__(request, client_address, _server)
        self.user_id = "--"

    def do_OPTIONS(self):
        print("do_OPTIONS ==============================================")
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, PUT, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "version, X-Requested-With, Content-Type")
        print(self.path)
        print(self.headers)

    def do_GET(self):
        # print("do_GET ==================================================")
        self.do_all(get_params(self))

    def do_POST(self):
        # print("do_POST =================================================")
        multimd = self.path.find('/multimd') >= 0

        if self.path.find('/multihtml') < 0 and not multimd:
            self.do_all(post_params(self))
            return

        # print("do_POST MULTIHML ==========================================")
        t1 = time.clock()
        t1t = time.time()
        querys = multi_post_params(self)
        do_headers(self, "application/json")
        is_tauno = self.path.find('/tauno') >= 0
        is_simcir = self.path.find('/simcir') >= 0
        is_parsons = self.path.find('/parsons') >= 0
        htmls = []
        self.user_id = get_param(querys[0], "user_id", "--")
        if self.user_id != "--":
            print("UserId:", self.user_id)
        log(self)
        # print(querys)

        global_anonymous = False
        for query in querys:
            ga = get_param(query, "GlobalAnonymous", None)
            if ga:
                global_anonymous = True
            if global_anonymous:
                query.query["anonymous"] = [True]
            # print(query.jso)
            # print(str(query))
            usercode = get_json_param(query.jso, "state", "usercode", None)
            if usercode:
                query.query["usercode"] = [usercode]
            userinput = get_json_param(query.jso, "state", "userinput", None)
            if userinput is None:
                userinput = get_json_param(query.jso, "markup", "userinput", None)

            if userinput is not None:
                query.query["userinput"] = [str(userinput)]
            userargs = get_json_param(query.jso, "state", "userargs", None)
            if userargs is None:
                userargs = get_json_param(query.jso, "markup", "userargs", None)

            if userargs is not None:
                query.query["userargs"] = [str(userargs)]
            selected_language = get_json_param(query.jso, "state", "selectedLanguage", None)
            if selected_language:
                query.query["selectedLanguage"] = [selected_language]
            ttype = get_param(query, "type", "cs").lower()
            if is_tauno:
                ttype = 'tauno'
            if is_simcir:
                ttype = 'simcir'
            if is_parsons:
                ttype = 'parsons'
            check_fullprogram(query, True)
            if multimd:
                # noinspection PyBroadException
                try:
                    s = get_md(ttype, query)
                except Exception as ex:
                    print("ERROR: " + str(ex) + " " + json.dumps(query))
                    continue
            else:
                s = get_html(self, ttype, query)
            # print(s)
            htmls.append(s)

        # print(htmls)
        sresult = json.dumps(htmls)
        self.wout(sresult)
        log(self)
        t2 = time.clock()
        t2t = time.time()
        ts = "multihtml: %7.4f %7.4f" % (t2 - t1, t2t - t1t)
        print(ts)

    def do_PUT(self):
        # print("do_PUT =================================================")
        t1put = time.time()
        self.do_all(post_params(self))
        t2 = time.time()
        ts = "do_PUT: %7.4f" % (t2 - t1put)
        print(ts)

    def wout(self, s):
        self.wfile.write(s.encode("UTF-8"))

    def do_all(self, query):
        try:
            signal.signal(signal.SIGALRM, signal_handler)
            signal.alarm(20)  # Ten seconds
        except Exception as e:
            # print("No signal", e)  #  TODO; why is this signal at all when it always comes here?
            pass
        try:
            return self.do_all_t(query)
        except Exception as e:
            print("Timed out2!", e)
            logging.exception("Timed out 2 trace")
            self.wout(str(e))

    def do_all_t(self, query):
        t1start = time.time()
        t_run_time = 0
        times_string = ""
        # print("t:", time.time() - t1start)

        query.randomcheck = binascii.hexlify(os.urandom(16)).decode()
        pwddir = ""
        # print(threading.currentThread().getName())
        result = {}  # query.jso
        if not result:
            result = {}
        save = {}
        web = {}
        result["web"] = web

        # print("doAll ===================================================")
        # print(self.path)
        # print(self.headers)

        if self.path.find('/favicon.ico') >= 0:
            self.send_response(404)
            return

        # print(query)
        self.user_id = get_param(query, "user_id", "--")
        if self.user_id != "--":
            print("UserId:", self.user_id)
        log(self)
        '''
        if self.path.find('/login') >= 0:
            username = check_korppi_user(self,"tim")
            if not username: return

            self.send_response(200)
            content_type = 'text/plain'
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wout("Username = " + username)
            return
        '''

        is_test = ""

        is_cache = get_param(query, "cache", False)
        is_template = self.path.find('/template') >= 0
        is_fullhtml = self.path.find('/fullhtml') >= 0
        is_gethtml = self.path.find('/gethtml') >= 0
        is_html = (self.path.find('/html') >= 0 or self.path.find('.html') >= 0) and not is_gethtml
        is_css = self.path.find('.css') >= 0
        is_js = self.path.find('.js') >= 0
        is_reqs = self.path.find('/reqs') >= 0
        is_iframe_param = get_param_del(query, "iframe", "")
        is_iframe = (self.path.find('/iframe') >= 0) or is_iframe_param
        is_answer = self.path.find('/answer') >= 0
        is_tauno = self.path.find('/tauno') >= 0
        is_simcir = self.path.find('/simcir') >= 0
        is_parsons = self.path.find('/parsons') >= 0
        is_ptauno = self.path.find('/ptauno') >= 0
        is_rikki = self.path.find('rikki') >= 0
        print_file = get_param(query, "print", "")

        content_type = 'text/plain'
        if is_js:
            content_type = 'application/javascript'
        if is_fullhtml or is_gethtml or is_html or is_ptauno or is_tauno:
            content_type = 'text/html; charset=utf-8'
        if is_reqs or is_answer:
            content_type = "application/json"
        if is_css:
            content_type = 'text/css'
        if not is_cache:
            do_headers(self, content_type)

        if is_template:
            tempfile = get_param(query, "file", "")
            tidx = get_param(query, "idx", "0")
            # print("tempfile: ", tempfile, tidx)
            # return self.wout(file_to_string('templates/' + tempfile))
            return self.wout(get_template('templates', tidx, tempfile))

        if self.path.find("refresh") >= 0:
            self.wout(get_chache_keys())
            clear_cache()
            return

        if is_gethtml:
            scripts = get_param(query, "scripts", "")
            inchtml = get_param(query, "html", "")
            p = self.path.split("?")
            # print(p, scripts)
            htmlstring = file_to_string(p[0])
            htmlstring = replace_scripts(htmlstring, scripts, "%INCLUDESCRIPTS%")
            htmlstring = htmlstring.replace("%INCLUDEHTML%", inchtml)
            self.wout(htmlstring)
            return

        if is_ptauno:
            # print("PTAUNO: " + content_type)
            p = self.path.split("?")
            self.wout(file_to_string(p[0]))
            return

            # Get the template type
        ttype = get_param(query, "type", "cs").lower()
        ttype = type_splitter.split(ttype)
        ttype = ttype[0]


        if is_tauno and not is_answer:
            ttype = 'tauno'  # answer is newer tauno
        if is_simcir:
            ttype = 'simcir'

        if is_reqs:
            templs = {}
            if not (is_tauno or is_rikki or is_parsons or is_simcir):
                templs = get_all_templates('templates')
            result_json = {"js": ["/cs/js/build/csPlugin.js",
                                  ],
                           "angularModule": ["csApp", "csConsoleApp"],
                           "css": ["/cs/css/cs.css",
                                   "/cs/css/mathcheck.css"
                                   ], "multihtml": True, "multimd": True}
            if is_parsons:
                result_json = {"js": ["/cs/js/build/csPlugin.js",
                                      "jqueryui-touch-punch",
                                      "/cs/js-parsons/lib/underscore-min.js",
                                      "/cs/js-parsons/lib/lis.js",
                                      "/cs/js-parsons/parsons.js",
                                      "/cs/js-parsons/lib/skulpt.js",
                                      "/cs/js-parsons/lib/skulpt-stdlib.js",
                                      "/cs/js-parsons/lib/prettify.js"
                                      ],
                               "angularModule": ["csApp", "csConsoleApp"],
                               "css": ["/cs/css/cs.css", "/cs/js-parsons/parsons.css",
                                       "/cs/js-parsons/lib/prettify.css"], "multihtml": True, "multimd": True}
            if is_simcir:
                result_json = {"js": ["/cs/js/build/csPlugin.js"],
                               "angularModule": ["csApp"],
                               "css": ["/cs/css/cs.css", "/cs/simcir/simcir.css", "/cs/simcir/simcir-basicset.css"],
                               "multihtml": True, "multimd": True}
            result_json.update(templs)
            result_str = json.dumps(result_json)
            return self.wout(result_str)

        if is_tauno and not is_answer:
            # print("PTAUNO: " + content_type)
            p = self.path.split("?")
            self.wout(file_to_string(p[0]))
            return

        # answer-route

        task_id = get_param(query, "taskID", None)
        if task_id:
            print("taskID:", task_id)

        points_rule = None

        is_doc = False
        extra_files = None
        warnmessage = ""
        language = dummy_language
        # print("t:", time.time() - t1start)

        try:
            # if ( query.jso != None and query.jso.has_key("state") and query.jso["state"].has_key("usercode") ):
            uploaded_file = get_json_param(query.jso, "input", "uploadedFile", None)
            uploaded_type = get_json_param(query.jso, "input", "uploadedType", None)
            if uploaded_file and uploaded_type:
                save["uploadedFile"] = uploaded_file
                save["uploadedType"] = uploaded_type
            usercode = get_json_param(query.jso, "state", "usercode", None)
            if usercode:
                query.query["usercode"] = [usercode]

            userinput = get_json_param(query.jso, "state", "userinput", None)
            if userinput is None:
                userinput = get_json_param(query.jso, "markup", "userinput", None)
            if userinput is not None:
                userinput = str(userinput)
                save["userinput"] = userinput
                if len(userinput) > 0 and userinput[-1:] != "\n":
                    userinput += "\n"
                query.query["userinput"] = [userinput]
            else:
                userinput = ''

            selected_language = get_json_param(query.jso, "input", "selectedLanguage", None)
            if selected_language:
                save["selectedLanguage"] = selected_language

            userargs = get_json_param(query.jso, "input", "userargs", None)
            if userargs is None:
                userargs = get_json_param(query.jso, "markup", "userargs", None)
            if userargs is not None:
                userargs = str(userargs)
                save["userargs"] = userargs
            else:
                userargs = ''


            is_doc = get_json_param3(query.jso, "input", "markup", "document", False)

            extra_files = get_json_param(query.jso, "markup", "extrafiles", None)
            if not extra_files:
                extra_files = get_json_param(query.jso, "markup", "-extrafiles", None)

            # print("t:", time.time() - t1start)

            # print("USERCODE: XXXXX = ", usercode)

            # print("Muutos ========")
            # pprint(query.__dict__, indent=2)

            if is_css:
                # return self.wout(file_to_string('cs.css'))
                return self.wout(file_to_string(self.path))

            if is_js:
                if is_rikki:
                    return self.wout(file_to_string('js/dirRikki.js'))
                # return self.wout(file_to_string('js/dir.js'))
                return self.wout(file_to_string(self.path))

            if is_html and not is_iframe:
                # print("HTML:==============")
                s = get_html(self, ttype, query)
                # print(s)
                return self.wout(s)

            if is_fullhtml:
                self.wout(file_to_string('begin.html'))
                self.wout(get_html(self, ttype, query))
                self.wout(file_to_string('end.html'))
                return

            if is_iframe and not print_file and ttype not in ["js", "glowscript", "vpython", "processing"]:
                s = string_to_string_replace_url(
                    '<iframe frameborder="0"  src="https://tim.it.jyu.fi/cs/fullhtml?##QUERYPARAMS##" ' +
                    'style="overflow:hidden;" height="##HEIGHT##" width="100%"  seamless></iframe>',
                    "##QUERYPARAMS##", query)
                return self.wout(s)

            check_fullprogram(query, print_file)

            # Check query parameters
            p0 = FileParams(query, "", "")
            # print("p0=")
            # print(p0.replace)
            if p0.url == "" and p0.replace == "":
                p0.replace = "XXXX"

            # print("type=" + ttype)

            # s = ""
            # if p0.url != "":
            #
            if p0.breakCount > 0:
                parts = get_file_parts_to_output(query, False)
                # print(parts)
                if print_file == "2":
                    return self.wout(json.dumps(parts))
                s = join_file_parts(parts)
            else:
                s = get_file_to_output(query, False and print_file)
            slines = ""

            # Open the file and write it
            # print(print_file,"Haetaan")
            if print_file:
                s = replace_code(query.cut_errors, s)
                return self.wout(s)

            language_class = languages.get(ttype.lower(), Language)
            language = language_class(query, s)

            mkdirs(language.prgpath)
            # os.chdir(language.prgpath)

            # /answer-path comes here
            usercode = get_json_param(query.jso, "input", "usercode", None)
            if usercode:
                save["usercode"] = usercode

            nosave = get_param(query, "nosave", None)
            nosave = get_json_param(query.jso, "input", "nosave", nosave)

            if not nosave:
                result["save"] = save

            if is_doc:
                s = replace_code(query.cut_errors, s)

            if not s.startswith("File not found"):
                errorcondition = get_json_param(query.jso, "markup", "errorcondition", False)
                if errorcondition:
                    m = re.search(errorcondition, s, flags=re.S)
                    if m:
                        errormessage = get_json_param(query.jso, "markup", "errormessage",
                                                      "Not allowed to use: " + errorcondition)
                        return write_json_error(self.wfile, errormessage, result)

                warncondition = get_json_param(query.jso, "markup", "warncondition", False)
                if warncondition:
                    m = re.search(warncondition, s, flags=re.S)
                    if m:
                        warnmessage = "\n" + get_json_param(query.jso, "markup", "warnmessage",
                                                            "Not recomended to use: " + warncondition)

                # print(os.path.dirname(language.sourcefilename))
                mkdirs(os.path.dirname(language.sourcefilename))
                # print("Write file: " + language.sourcefilename)
                if s == "":
                    s = "\n"

                # Write the program to the file =======================================================
                s = language.before_save(language.before_code + s)
                codecs.open(language.sourcefilename, "w", "utf-8").write(s)
                slines = s

            save_extra_files(query, extra_files, language.prgpath)

            if not os.path.isfile(language.sourcefilename) or os.path.getsize(language.sourcefilename) == 0:
                return write_json_error(self.wfile, "Could not get the source file", result)
                # self.wfile.write("Could not get the source file\n")
                # print "=== Could not get the source file"

            nocode = get_param(query, "nocode", False)

            is_test = ""
            if "test" in ttype:
                is_test = "test"
            points_rule = get_param(query, "pointsRule", None)
            # if points_rule is None and language.readpoints_default:
            #    points_rule = {}
            if points_rule is not None:
                points_rule["points"] = get_json_param(query.jso, "state", "points", None)
                points_rule["result"] = 0
                if points_rule["points"]:
                    if is_test:
                        points_rule["points"]["test"] = 0
                    elif is_doc:
                        points_rule["points"]["doc"] = 0
                        # ("doc points: ", points_rule["points"]["doc"])
                    else:
                        points_rule["points"]["run"] = 0
                if not is_doc:
                    is_plain = False
                    expect_code = get_points_rule(points_rule, is_test + "expectCode", None)
                    if not expect_code:
                        expect_code = get_points_rule(points_rule, is_test + "expectCodePlain", None)
                        is_plain = True

                    if expect_code:
                        if expect_code == "byCode":
                            expect_code = get_param(query, "byCode", "")
                        maxn = get_param(query, "parsonsmaxcheck", 0)
                        if maxn > 0:
                            p = check_parsons(expect_code, usercode, maxn, get_param(
                                query, "parsonsnotordermatters", False))
                            give_points(points_rule, "code", p)
                        else:
                            excode = expect_code.rstrip('\n')
                            match = False
                            if is_plain:
                                match = usercode == excode
                            else:
                                excode = re.compile(excode, re.M)
                                match = excode.match(usercode)
                            if match:
                                give_points(points_rule, "code", 1)
                    number_rule = get_points_rule(points_rule, is_test + "numberRule", None)
                    if number_rule:
                        give_points(points_rule, "code", check_number_rule(usercode, number_rule))
            # print(points_rule)

            # uid = pwd.getpwnam("agent").pw_uid
            # gid = grp.getgrnam("agent").gr_gid
            # os.chown(prgpath, uid, gid)
            shutil.chown(language.prgpath, user="agent", group="agent")
            # print("t:", time.time() - t1start)

            # print(ttype)
            # ########################## Compiling programs ###################################################
            log(self)
            cmdline = ""

            if is_doc:
                # doxygen
                # ./doxygen/csdoc.sh /tmp/user/4d85...17114/3 /csgenerated/docs/vesal/abcd /csgenerated/docs/vesal
                # http://tim3/csgenerated/docs/vesal/abcd/html/index.html
                #
                userdoc = "/csgenerated/docs/%s" % self.user_id
                docrnd = generate_filename()
                doccmd = "/cs/doxygen/csdoc.sh %s %s/%s %s" % (language.prgpath, userdoc, docrnd, userdoc)
                doccmd = sanitize_cmdline(doccmd)
                p = re.compile('\.java')
                docfilename = p.sub("", language.filename)
                p = re.compile('[^.]*\.')
                docfilename = p.sub("", docfilename)
                docfilename = docfilename.replace("_", "__")  # jostakin syystä tekee näin
                dochtml = "/csgenerated/docs/%s/%s/html/%s_8%s.html" % (
                    self.user_id, docrnd, docfilename, language.fileext)
                docfile = "%s/%s/html/%s_8%s.html" % (userdoc, docrnd, docfilename, language.fileext)
                # print("XXXXXXXXXXXXXXXXXXXXXX", language.filename)
                # print("XXXXXXXXXXXXXXXXXXXXXX", docfilename)
                # print("XXXXXXXXXXXXXXXXXXXXXX", dochtml)
                # print("XXXXXXXXXXXXXXXXXXXXXX", docfile)
                check_output([doccmd], stderr=subprocess.STDOUT, shell=True).decode("utf-8")
                if not os.path.isfile(
                        docfile):  # There is maybe more files with same name and it is difficult to guess the name
                    dochtml = "/csgenerated/docs/%s/%s/html/%s" % (self.user_id, docrnd, "files.html")
                    # print("XXXXXXXXXXXXXXXXXXXXXX", dochtml)

                web["docurl"] = dochtml
                give_points(points_rule, "doc")

            else:
                cmdline = language.get_cmdline(s)

            if get_param(query, "justSave", False) or get_param(query, "justCmd", False):
                cmdline = ""

            '''
            # old unsafe compile
            compiler_output = ""
            t1startrun = time.time()
            if cmdline:
                compiler_output = check_output(["cd " + language.prgpath + " && " + cmdline],
                                               stderr=subprocess.STDOUT,
                                               shell=True).decode("utf-8")
                compiler_output = compiler_output.replace(language.prgpath, "")
                if language.hide_compile_out:
                    compiler_output = ""
                give_points(points_rule, is_test + "compile")

            # self.wfile.write("*** Success!\n")
            print("*** Compile Success")
            t_run_time = time.time() - t1startrun
            times_string = "\n" + str(t_run_time)
            '''

            # change old long file names to relatice paths
            language.compile_commandline = cmdline.replace(language.prgpath, "/home/agent")

            language.prgpath = sanitize_cmdline(language.prgpath)

            if nocode and ttype != "jcomtest":
                print("Poistetaan ", ttype, language.sourcefilename)
                # remove(language.sourcefilename)
                # print(compiler_output)
                language.compile_commandline += " && rm " + \
                                                language.sourcefilename.replace(language.prgpath, "/home/agent")

            # ########################## Running programs ###################################################
            # delete_tmp = False

            lang = ""
            plang = get_param(query, "lang", "")
            env = dict(os.environ)
            if plang:
                if plang.find("fi") == 0:
                    lang = "fi_FI.UTF-8"
                if plang.find("en") == 0:
                    lang = "en_US.UTF-8"

            if lang:
                env["LANG"] = lang
                env["LC_ALL"] = lang
            # print("Lang= ", lang)

            err = ""
            out = ""

            pwddir = ""

            t1startrun = time.time()

            if is_doc:
                pass  # jos doc ei ajeta
            elif get_param(query, "justSave", False):
                showname = language.sourcefilename.replace(language.basename, "").replace("/tmp//", "")
                if showname == "prg":
                    showname = ""
                code, out, err, pwddir = (0, "", ("Saved " + showname), "")
            #elif get_param(query, "justCompile", False) and ttype.find("comtest") < 0:
            #    language.just_compile = True
                # code, out, err, pwddir = (0, "".encode("utf-8"), ("Compiled " + filename).encode("utf-8"), "")
            #    code, out, err, pwddir = (0, "", ("Compiled " + language.filename), "")

            else:  # run cmd wins all other run types
                if get_param(query, "justCompile", False) and ttype.find("comtest") < 0:
                    language.just_compile = True
                language.set_stdin(userinput)
                runcommand = get_param(query, "cmd", "")
                if ttype != "run" and (runcommand or get_param(query, "cmds", "")) and not is_test:
                    # print("runcommand: ", runcommand)
                    # code, out, err, pwddir = run2([runcommand], cwd=prgpath, timeout=10, env=env, stdin=stdin,
                    #                               uargs=get_param(query, "runargs", "") + " " + userargs)
                    cmd = shlex.split(runcommand)
                    uargs = userargs
                    extra = get_param(query, "cmds", "").format(language.pure_exename, uargs)
                    if extra != "":
                        cmd = []
                        uargs = ""
                    # print("run: ", cmd, extra, language.pure_exename, language.sourcefilename)
                    try:
                        code, out, err, pwddir = run2(cmd, cwd=language.prgpath, timeout=language.timeout, env=env,
                                                      stdin=language.stdin,
                                                      uargs=get_param(query, "runargs", "") + " " + uargs,
                                                      extra=extra, no_x11=language.no_x11,
                                                      ulimit=language.ulimit,
                                                      compile_commandline = language.compile_commandline
                                                      )
                    except Exception as e:
                        print(e)
                        code, out, err = (-1, "", str(e))
                    # print("Run2: ", language.imgsource, language.pngname)
                    out, err = language.copy_image(web, code, out, err, points_rule)
                else:  # Most languages are run from here
                    code, out, err, pwddir = language.run(web, slines, points_rule)

                t_run_time = time.time() - t1startrun
                try:
                    times_string += codecs.open(language.fullpath + "/run/time.txt", 'r', "iso-8859-15").read() or ""
                except:
                    pass

                if err.find("Compile error") >= 0:
                    # print("directory = " + os.curdir)
                    # error_str = "!!! Error code " + str(e.returncode) + "\n"
                    # error_str += e.output.decode("utf-8") + "\n"
                    # error_str += e.output.decode("utf-8") + "\n"
                    # errorStr = re.sub("^/tmp/.*cs\(\n", "tmp.cs(", errorStr, flags=re.M)
                    error_str = err.replace(language.prgpath, "")
                    error_str += out
                    output = io.StringIO()
                    file = codecs.open(language.sourcefilename, 'r', "utf-8")
                    lines = file.read().splitlines()
                    file.close()
                    if not nocode:
                        print_lines(output, lines, 0, 10000)
                    error_str += output.getvalue()
                    output.close()
                    error_str = replace_code(query.cut_errors, error_str)

                    if language.delete_tmp:
                        removedir(language.prgpath)
                    give_points(points_rule, is_test + "notcompile")
                    return write_json_error(self.wfile, error_str, result, points_rule)

                give_points(points_rule, is_test + "compile")

                if not err and not language.run_points_given:  # because test points are already given
                    give_points(points_rule, "run")
                # print(code, out, err, pwddir)

                if code == -9:
                    out = "Runtime exceeded, maybe loop forever\n" + out

                else:
                    print(err)
                    # err = err + compiler_output
                    err = language.clean_error(err)

                    # if type(out) != type(''): out = out.decode()
                    # noinspection PyBroadException
                    try:
                        if out and out[0] in [254, 255]:
                            out = out.decode('UTF16')
                            # elif type('') != type(out):
                            #    out = out.decode('utf-8-sig')
                    except:
                        # out = out.decode('iso-8859-1')
                        pass
        except Exception as e:
            print("run: ", e)
            code, out, err = (-1, "", str(e))  # .encode())

        if is_doc:
            pass  # jos doc, ei ajeta
        else:
            expect_output = get_points_rule(points_rule, is_test + "expectOutput", None)
            if expect_output:
                exout = re.compile(expect_output.rstrip('\n'), re.M)
                if exout.match(out):
                    give_points(points_rule, "output", 1)
            expect_output = get_points_rule(points_rule, is_test + "expectOutputPlain", None)
            if expect_output:
                exout = expect_output.rstrip('\n')
                if exout == out.rstrip('\n'):
                    give_points(points_rule, "output", 1)

            readpoints = get_points_rule(points_rule, "readpoints", language.readpoints_default)
            readpointskeep = get_points_rule(points_rule, "readpointskeep", False)
            if readpoints:
                try:
                    readpoints = replace_random(query, readpoints)
                    m = re.search(readpoints, out)
                    m2 = re.findall(readpoints, out)
                    if m and m.group(1):
                        p = 0
                        if not readpointskeep:
                            out = re.sub(m.group(0), "", out)
                        # noinspection PyBroadException
                        try:
                            if len(m2) == 1:  # Only one line found
                                p = float(m.group(1))
                            else:
                                err += "Pattern is more than once: " + readpoints + "\n"
                        except:
                            p = 0
                        give_points(points_rule, "output", p)
                except Exception as e:
                    msg = str(e)
                    if isinstance(e, IndexError):
                        msg = "no group ()"
                    err += "readpoints pattern error: " + msg + "\n"
                    err += "Pattern: " + readpoints + "\n"

        return_points(points_rule, result)

        delete_extra_files(extra_files, language.prgpath)
        if language.delete_tmp:
            removedir(language.prgpath)

        out = out[0:get_param(query, "maxConsole", 20000)]

        out_replace = get_param(query, "outReplace", None)
        out_by = get_param(query, "outBy", "")
        if out_replace:
            if type(out_replace) is list:
                for rep in out_replace:
                    replace = rep.get("replace", "")
                    if replace:
                        out = re.sub(replace, rep.get("by", out_by), out, flags=re.M)
            else:
                out = re.sub(out_replace, out_by, out, flags=re.M)

        web["console"] = out
        web["error"] = err + warnmessage
        web["pwd"] = pwddir.strip()

        t2 = time.time()
        ts = "%7.3f %7.3f" % ((t2 - t1start), t_run_time)
        ts += times_string
        # print(ts)
        web["runtime"] = ts

        result["web"] = web
        # print(result)

        # Clean up
        # print("FILE NAME:", sourcefilename)
        # remove(sourcefilename)

        # self.wfile.write(out)
        # self.wfile.write(err)
        sresult = json.dumps(result)
        if is_cache:
            return result
        self.wout(sresult)
        # print("Result ========")
        # print(sresult)
        # print(out)
        # print(err)


# Kun debuggaa Windowsissa, pitää vaihtaa ThreadingMixIn
# Jos ajaa Linuxissa ThreadingMixIn, niin chdir vaihtaa kaikkien hakemistoa?
# Ongelmaa korjattu siten, että kaikki run-kommennot saavat prgpathin käyttöönsä

if __debug__:
    # if True:
    class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        """Handle requests in a separate thread."""


    print("Debug mode/ThreadingMixIn")
else:
    class ThreadedHTTPServer(socketserver.ForkingMixIn, http.server.HTTPServer):
        """Handle requests in a separate thread."""


    print("Normal mode/ForkingMixIn")

if __name__ == '__main__':
    server = ThreadedHTTPServer(('', PORT), TIMServer)
    print('Starting server, use <Ctrl-C> to stop')
    server.serve_forever()
