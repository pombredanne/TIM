"""
TIM plugin: a checkbox field
"""
from dataclasses import dataclass, asdict
from typing import Union, Dict, List, Tuple

from flask import render_template_string
from marshmallow.utils import missing

from common_schemas import TextfieldStateModel
from pluginserver_flask import GenericHtmlModel, \
    create_blueprint, GenericAnswerModel, PluginAnswerWeb, PluginAnswerResp, PluginReqs
from timApp.document.docentry import DocEntry
from timApp.plugin.taskid import TaskId
from timApp.tim_app import csrf
from timApp.user.user import User
from timApp.util.get_fields import get_fields_and_users, RequestedGroups, GetFieldsAccess, FieldValue
from utils import Missing


# Use caseja:

# Luennot + pääteohjaukset:

"""
timezone: Europe/Helsinki  # oletus
weeks: [35-38, 40]
weekdays:  # oletus 5 arkipäivää näkyvillä per viikko
 - mon
 - tue
 - wed
 - thu
 - fri
weekevents:
 luento:
  - [Luento 1, 'mon 10:15-12:00']
  - [Luento 2, 'tue 12:15-14:00', {weeks: [36, 41]}]  # oletusviikoista poikkeavat
 paate:
  - [Pääte 1, 'wed 10:15-12:00', {max: 15}]
  - [Pääte 2, 'thu 12:15-14:00']
events:  # tähän voi lisätä epäsäännöllisiä tapahtumia
 - [Muu tapahtuma, '6.11.2020 14:00-15:00']
eventgroups:
 luento:
  suggestAllInEventGroup: true  # jos yhdenkin luennon ruksii, niin ehdotetaanko, että ruksitaan kaikki
 paate:
  suggestForEachWeek: true  # ehdotetaanko jokaisen viikon osalta saman tapahtuman ruksimista
  max: 20  # oletusmaksimiosallistujamäärä jokaiseen tämän ryhmän tapahtumaan
  maxPerPerson: 1  # yksi henkilö voi osallistua korkeintaan näin moneen tämän ryhmän tapahtumaan per viikko
"""

# Harjoitustöiden ohjausajat:

"""
weeks: [35-38, 40]
weekevents:
 ohjaus:
  - [Ohjaus, 'mon 8:00-18:00', {splitToMulti: 20mins}]
filterEvents:
 right: view
 deadline: 6h  # ajat varattava viimeistään 6h etukäteen
 allowIfHasParticipant: ohj1  # näytetään view-oikeudellisille vain ne ajat, joissa on ainakin 1 ohj1-ryhmään kuuluva
eventgroups:
 ohjaus:
  suggestForEachWeek: true  # ehdotetaanko jokaisen viikon osalta saman tapahtuman ruksimista
  max: 2  # ohjaaja + opiskelija
"""

# Real-world-esimerkki: Ohj1 syksy 2018 luennot ja pääteohjaukset, ks.
# https://korppi.jyu.fi/kotka/course/student/generalCourseInfo.jsp?course=226410

"""
year: 2018
weeks: [37-48]
weekevents:
 luento:
  - [Luento 1, 'ma 12:15-14:00']
  - [Luento 2, 'ti 14:15-16:00']
 demo:
  - [Demo 1, 'ma 14:15-16:00']
  - [Demo 2, 'ma 16:05-18:00']
 paate:
  - [Pääte 1, 'wed 10:15-12:00', {max: 15}]
  - [Pääte 2, 'thu 12:15-14:00']
events:
 - [PP-luento, '23.10.2018 16:15-18:00']
eventgroups:
 demo:
  weeks: [38-48]
 luento:
  suggestAllInEventGroup: true  # jos yhdenkin luennon ruksii, niin ehdotetaanko, että ruksitaan kaikki
 paate:
  suggestForEachWeek: true  # ehdotetaanko jokaisen viikon osalta saman tapahtuman ruksimista
  max: 20  # oletusmaksimiosallistujamäärä jokaiseen tämän ryhmän tapahtumaan
  maxPerPerson: 1  # yksi henkilö voi osallistua korkeintaan näin moneen tämän ryhmän tapahtumaan per viikko
"""


@dataclass
class CalendarMarkupModel:
    events: Union[List[str], Missing] = missing


@dataclass
class CalendarInputModel:
    c: str
    nosave: Union[bool, Missing] = missing


@dataclass
class CalendarHtmlModel(GenericHtmlModel[CalendarInputModel, CalendarMarkupModel, TextfieldStateModel]):
    def get_component_html_name(self) -> str:
        return 'calendar-runner'

    def get_static_html(self) -> str:
        return render_static_calendar(self)

    def get_browser_json(self) -> Dict:
        r = super().get_browser_json()
        count, _ = get_calendar_state(self.markup, self.taskID, self.current_user_id)
        r['count'] = count
        return r


@dataclass
class CalendarAnswerModel(GenericAnswerModel[CalendarInputModel, CalendarMarkupModel, TextfieldStateModel]):
    pass


def render_static_calendar(m: CalendarHtmlModel) -> str:
    return render_template_string("""""".strip(),
        **asdict(m.markup),
    )


class CalendarAnswerWeb(PluginAnswerWeb, total=False):
    count: int


class CalendarAnswerResp(PluginAnswerResp, total=False):
    pass


def answer(args: CalendarAnswerModel) -> CalendarAnswerResp:
    web: CalendarAnswerWeb = {}
    result = CalendarAnswerResp(web=web)
    c = args.input.c

    count, previous = get_calendar_state(args.markup, args.taskID, args.info.user_id)

    # Take the current answer into account.
    if previous is None:
        previous = '0'
    if previous != c:
        if c == '1':
            count += 1
        else:
            count -= 1
    nosave = args.input.nosave

    if not nosave:
        save = {"c": c}
        result["save"] = save
        web['result'] = "saved"
        web['count'] = count

    return result


def get_calendar_state(markup: CalendarMarkupModel, task_id: str, user_id: str) -> Tuple[int, FieldValue]:
    doc_id = TaskId.parse_doc_id(task_id)
    curr_user = User.get_by_name(user_id)
    assert curr_user is not None
    d = DocEntry.find_by_id(doc_id)
    if not d:
        return 0, None  # TODO handle error properly
    user_fields, _, _, _ = get_fields_and_users(
        [task_id],
        RequestedGroups.from_name_list(['*']),
        d,
        curr_user,
        access_option=GetFieldsAccess.AllowAlwaysNonTeacher,
    )

    count = 0
    previous = None
    for u in user_fields:
        fs = u['fields']
        val = fs[task_id]
        if val == '1':
            count += 1
        if curr_user == u['user']:
            previous = val
    return count, previous


def reqs() -> PluginReqs:
    return {
        "js": ["calendar"],
        "css": ["/field/css/field.css"],
        "multihtml": True,
    }


calendar_route = create_blueprint(
    __name__,
    'calendar',
    CalendarHtmlModel,
    CalendarAnswerModel,
    answer,
    reqs,
    csrf,
)
