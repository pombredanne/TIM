"""
Module for serving drag item-plugin.
"""
import re
from typing import Union, List

import attr
from flask import jsonify, render_template_string
from marshmallow import Schema, fields, post_load, validates, ValidationError
from marshmallow.utils import missing
from webargs.flaskparser import use_args

from pluginserver_flask import GenericMarkupModel, GenericMarkupSchema, GenericHtmlSchema, GenericHtmlModel, \
    GenericAnswerSchema, GenericAnswerModel, Missing, \
    make_base64, InfoSchema, create_app


@attr.s(auto_attribs=True)
class DragStateModel:
    word: str


class DragStateSchema(Schema):
    word = fields.Str(required=True)

    @post_load
    def make_obj(self, data):
        return DragStateModel(**data)

    class Meta:
        strict = True


@attr.s(auto_attribs=True)
class DragMarkupModel(GenericMarkupModel):
    points_array: Union[str, Missing] = missing
    inputstem: Union[str, Missing] = missing
    needed_len: Union[int, Missing] = missing
    word: Union[str, Missing] = missing
    followid: Union[str, Missing] = missing


class DragMarkupSchema(GenericMarkupSchema):
    points_array = fields.List(fields.List(fields.Number()))
    inputstem = fields.Str()
    needed_len = fields.Int()
    cols = fields.Int()
    word = fields.Str()
    followid = fields.String()

    @validates('points_array')
    def validate_points_array(self, value):
        if len(value) != 2 or not all(len(v) == 2 for v in value):
            raise ValidationError('Must be of size 2 x 2.')

    @post_load
    def make_obj(self, data):
        return DragMarkupModel(**data)

    class Meta:
        strict = True


@attr.s(auto_attribs=True)
class DragInputModel:
    word: str
    nosave: bool = missing


class DragInputSchema(Schema):
    nosave = fields.Bool()
    word = fields.Str(required=True)

    @validates('word')
    def validate_word(self, word):
        if not word:
            raise ValidationError('Must not be empty.')

    @post_load
    def make_obj(self, data):
        return DragInputModel(**data)


class DragAttrs(Schema):
    markup = fields.Nested(DragMarkupSchema)
    state = fields.Nested(DragStateSchema, allow_none=True, required=True)


@attr.s(auto_attribs=True)
class DragHtmlModel(GenericHtmlModel[DragInputModel, DragMarkupModel, DragStateModel]):
    def get_static_html(self) -> str:
        return render_static_drag(self)

    def get_browser_json(self):
        r = super().get_browser_json()
        if self.state:
            r['word'] = self.state.word
        return r

    def get_real_html(self):
        return render_template_string(
            """<drag-runner json="{{data}}"></drag-runner>""",
            data=make_base64(self.get_browser_json()),
        )

    class Meta:
        strict = True


class DragHtmlSchema(DragAttrs, GenericHtmlSchema):
    info = fields.Nested(InfoSchema, allow_none=True, required=True)

    @post_load
    def make_obj(self, data):
        # noinspection PyArgumentList
        return DragHtmlModel(**data)

    class Meta:
        strict = True


@attr.s(auto_attribs=True)
class DragAnswerModel(GenericAnswerModel[DragInputModel, DragMarkupModel, DragStateModel]):
    pass


class DragAnswerSchema(DragAttrs, GenericAnswerSchema):
    input = fields.Nested(DragInputSchema, required=True)

    @post_load
    def make_obj(self, data):
        # noinspection PyArgumentList
        return DragAnswerModel(**data)

    class Meta:
        strict = True


def render_static_drag(m: DragHtmlModel):
    return render_template_string(
        """
<div class="csRunDiv no-popup-menu">
    <h4>{{ header }}</h4>
    <p class="stem">{{ stem }}</p>
    <div><label>{{ inputstem or '' }} <span>
        <input type="text"
               class="form-control"
               placeholder="{{inputplaceholder}}"
               size="{{cols}}"></span></label>
    </div>
    <button class="timButton">
        {{ buttonText or button or "Save" }}
    </button>
    <a>{{ resetText }}</a>
    <p class="plgfooter">{{ footer }}</p>
</div>
        """,
        **attr.asdict(m.markup),
    )


app = create_app(__name__, DragHtmlSchema())


@app.route('/answer/', methods=['put'])
@use_args(DragAnswerSchema(strict=True), locations=("json",))
def answer(args: DragAnswerModel):
    web = {}
    result = {'web': web}
    word = args.input.word

    # plugin can ask not to save the word
    nosave = args.input.nosave
    if not nosave:
        save = {"word: word"}
        result["save"] = save
        web['result'] = "saved"

    return jsonify(result)

@app.route('/reqs/')
@app.route('/reqs')
def reqs():
    templates = [
"""
#- {defaultplugin="drag"}
The weather {#item1 word: is} nice today.
""",
"""
#- {defaultplugin="drag"}
Näin tänään {#item2 word: kissan}
joka jahtasi {#item3 word: hiirtä}
"""
]
    return jsonify({
        "js": ["js/build/drag.js"],
        "multihtml": True,
        "css": ["css/drag.css"],
        'editor_tabs': [
            {
                'text': 'Plugins',
                'items': [
                    {
                        'text': 'Drag',
                        'items': [
                            {
                                'data': templates[0].strip(),
                                'text': 'One question',
                                'expl': 'Add a draggable word'
                            },
                            {
                                'data': templates[1].strip(),
                                'text': 'Two questions',
                                'expl': 'Add two draggable words'
                            },
                        ],
                    },
                ],
            },
        ],
    })


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
    )
