"""

"""
import os
from typing import Union, List

import attr

from flask import jsonify, render_template_string
from marshmallow import Schema, fields, post_load
from marshmallow.utils import missing

from pluginserver_flask import GenericMarkupModel, GenericMarkupSchema, GenericHtmlSchema, GenericHtmlModel, \
     Missing, InfoSchema, create_blueprint
from timApp.tim_app import csrf


@attr.s(auto_attribs=True)
class TimMenuStateModel:
    """Model for the information that is stored in TIM database for each answer."""
    url: Union[str, Missing] = None
    separator: Union[str, Missing] = None

class TimMenuStateSchema(Schema):
    url = fields.Str(allow_none=True)
    separator = fields.Str(allow_none=True)

    @post_load
    def make_obj(self, data):
        res = TimMenuStateModel(**data)
        return res

class TimMenuItem():
    def __init__(self, text: str):
        self.text = text

@attr.s(auto_attribs=True)
class TimMenuMarkupModel(GenericMarkupModel):
    hoverOpen: Union[bool, Missing] = missing
    separator: Union[str, Missing] = missing
    menu: Union[List[str], Missing] = missing

@attr.s(auto_attribs=True)
class TimMenuItemModel:
    text: str

class TimMenuItemSchema(Schema):
    text = fields.Str(required=False)

    @post_load
    def make_obj(self, data):
        return TimMenuItemModel(**data)


class TimMenuMarkupSchema(GenericMarkupSchema):
    hoverOpen = fields.Bool(allow_none=True, default=True)
    separator = fields.Str(allow_none=True)
    menu = fields.List(fields.Str())
    # menu = fields.List(fields.Nested(TimMenuItemSchema))
    @post_load
    def make_obj(self, data):
        return TimMenuMarkupModel(**data)

class TimMenuAttrs(Schema):
    """Common fields for HTML and answer routes."""
    markup = fields.Nested(TimMenuMarkupSchema)
    state = fields.Nested(TimMenuStateSchema, allow_none=True, required=True)


@attr.s(auto_attribs=True)
class TimMenuInputModel:
    """Model for the information that is sent from browser (plugin AngularJS component)."""
    data: str
    separator: str
    url: str

class TimMenuInputSchema(Schema):
    data = fields.Str(required=True)
    separator = fields.Str(required=False)
    url = fields.Str(required=False)

    @post_load
    def make_obj(self, data):
        return TimMenuInputModel(**data)

@attr.s(auto_attribs=True)
class TimMenuHtmlModel(GenericHtmlModel[TimMenuInputModel, TimMenuMarkupModel, TimMenuStateModel]):
    def get_component_html_name(self) -> str:
        return 'timmenu-runner'

    def show_in_view_default(self) -> bool:
        return True

    def get_static_html(self) -> str:
        s = "TimMenu"
        return render_static_TimMenu(self, s)

    def get_browser_json(self):
        r = super().get_browser_json()
        # r['state']['separator'] = ";"
        return r


class TimMenuHtmlSchema(TimMenuAttrs, GenericHtmlSchema):
    info = fields.Nested(InfoSchema, allow_none=True, required=True)

    @post_load
    def make_obj(self, data):
        # noinspection PyArgumentList
        return TimMenuHtmlModel(**data)


def render_static_TimMenu(m: TimMenuHtmlModel, s: str):
    return render_template_string(
        f"""
<div class="TimMenu">
 {s}
</div>
<br>
        """,
        **attr.asdict(m.markup),
    )


timMenu_plugin = create_blueprint(__name__, 'timMenu', TimMenuHtmlSchema(), csrf)

@timMenu_plugin.route('/reqs/')
@timMenu_plugin.route('/reqs')
def reqs():
    """Introducing templates for TimMenu plugin"""
    templates = ["""
``` {plugin="timMenu"}
width: 10em;
separator: "|"
openDirection: top
- text: [link1_text](link1)
- text: Title 1
    - text: [link2_text](link2)
    - text: [link3_text](link3)
-  text: Title 2
    - text: [link4_text](link4)
    - text: [link5_text](link5)
```
""","""
``` {plugin="timMenu"}
- [link1_text](link1)
- Title 1
    - [link2_text](link2)
    - [link3_text](link3)
-  Title 2
    - [link4_text](link4)
    - [link5_text](link5)
```
    """]
    editor_tabs = [
            {
                'text': 'Insert',
                'items': [
                    {
                        'text': 'Others',
                        'items': [
                            {
                                'data': templates[0].strip(),
                                'text': 'TimMenu',
                                'expl': 'Add a dropdown menu bar',
                            },
                            {
                                'data': templates[1].strip(),
                                'text': 'TimMenu (simple)',
                                'expl': 'Add a minimal dropdown menu bar',
                            },
                        ],
                    },
                ],
            },
        ]
    if os.environ.get('SHOW_TEMPLATES', "True") == "False":
        editor_tabs = None
    return jsonify({
        "js": [],
        "multihtml": True,
        'editor_tabs': editor_tabs,
    },
    )
