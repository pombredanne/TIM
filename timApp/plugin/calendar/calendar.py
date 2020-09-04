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

"""
timezone: Europe/Helsinki  # oletus
weeks:
 - 31.8.2020
 - 7.9.2020
 - 14.9.2020
 - 21.9.2020
 - 28.9.2020
# tai kelpaa myös:
weeks:
 from: 31.8.2020
 to: 28.9.2020
weekdays:  # oletus 5 arkipäivää näkyvillä per viikko
 - mon
 - tue
 - wed
 - thu
 - fri
weekevents:
 - title: Luento 1
   time: mon 10:15-12:00
   eventgroup: luento
 - title: Luento 2
   time: mon 10:15-12:00
   eventgroup: luento
 - title: Pääte 1
   time: wed 10:15-12:00
   eventgroup: paate
   max: 15
 - title: Pääte 2
   time: thu 12:15-14:00
   eventgroup: paate
# tai ehkä:
 - [Luento 1, 'mon 10:15-12:00', {eventgroup: luento}]  # flow context vaatii hipsut '...' koska sisältää ":"
 - [Luento 2, 'tue 12:15-14:00', {eventgroup: luento}]
 - [Pääte 1, 'wed 10:15-12:00', {eventgroup: paate, max: 15}]  # vähän kömpelön näköinen
 - [Pääte 2, 'thu 12:15-14:00', {eventgroup: paate}]
events:  # tähän voi lisätä epäsäännöllisiä tapahtumia
 - title: Muu tapahtuma
   time: 6.11.2020 14:00-15:00
# tai ehkä:
 - [Muu tapahtuma, '6.11.2020 14:00-15:00']
eventgroups:
 luento:
  suggestAll: true  # jos yhdenkin luennon ruksii, niin ehdotetaanko, että ruksitaan kaikki
 paate:
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
