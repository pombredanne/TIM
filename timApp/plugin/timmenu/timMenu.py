"""
TimMenu-plugin.
"""
import uuid
from dataclasses import dataclass, asdict

from flask import render_template_string
from marshmallow.utils import missing

from tim_common.timjsonencoder import TimJsonEncoder
from timApp.item.partitioning import INCLUDE_IN_PARTS_CLASS_NAME
from timApp.markdown.dumboclient import call_dumbo
from timApp.tim_app import csrf
from tim_common.markupmodels import GenericMarkupModel
from tim_common.pluginserver_flask import (
    GenericHtmlModel,
    create_nontask_blueprint,
    PluginReqs,
    EditorTab,
)
from tim_common.utils import Missing


@dataclass
class TimMenuStateModel:
    """Model for the information that is stored in TIM database for each answer."""


class TimMenuIndentation:
    """
    A class for saving and comparing indentation levels user has used previously.
    """

    def __init__(self, level: int, spaces_min: int, spaces_max: int):
        self.spaces_min = spaces_min
        self.spaces_max = spaces_max
        self.level = level

    def is_this_level(self, index: int) -> bool:
        """
        Check whether the given number of spaces is within the closed range of the indentation level.

        :param index: First index of the hyphen marking i.e. number of spaces preceding it.
        :return: True if index is part of the level.
        """
        return self.spaces_min <= index <= self.spaces_max

    def __str__(self) -> str:
        return f"{{level: {self.level}, spaces_min: {self.spaces_min}, spaces_max: {self.spaces_max}}}"

    def __repr__(self) -> str:
        return str(self)


class TimMenuItem:
    """
    Menu item with mandatory attributes (content, level, id, list of contained menu items and opening state)
    and optional styles.
    """

    def __init__(
        self, text: str, level: int, items: list["TimMenuItem"], is_open: bool = False
    ) -> None:
        self.text = text
        self.level = level
        self.id = ""
        self.items = items
        self.open = is_open
        self.width: str | None = None
        self.height: str | None = None
        self.rights: str | None = None

    def __str__(self) -> str:
        s = f"{{level: {self.level}, id: '{self.id}', text: '{self.text}', items: {self.items}"
        if self.width:
            s += f", width: '{self.width}'"
        if self.height:
            s += f", height: '{self.height}'"
        if self.rights:
            s += f", rights: '{self.rights}'"
        return f"{s}}}"

    def generate_id(self) -> None:
        """
        Generate an id string for the menu item.
        :return: None.
        """
        self.id = str(uuid.uuid4())

    def __repr__(self) -> str:
        return str(self)

    def to_json(self) -> dict:
        s = {
            "level": self.level,
            "id": self.id,
            "text": self.text,
            "open": self.open,
            "items": self.items,
        }
        if self.width:
            s.update({"width": self.width})
        if self.height:
            s.update({"height": self.height})
        if self.rights:
            s.update({"rights": self.rights})
        return s


@dataclass
class TimMenuItemModel:
    text: str
    level: int


@dataclass
class TimMenuMarkupModel(GenericMarkupModel):
    backgroundColor: str | Missing | None = "#F7F7F7"
    basicColors: bool | Missing | None = False
    fontSize: str | Missing | None = "0.84em"
    hoverOpen: bool | Missing | None = True
    keepLinkColors: bool | Missing | None = True
    menu: str | Missing = missing
    openAbove: bool | Missing | None = False
    openingSymbol: str | Missing | None = "▼"
    separator: str | Missing | None = "|"
    textColor: str | Missing | None = "black"
    topMenu: bool | Missing | None = False
    topMenuTriggerHeight: int | Missing | None = 200


class TimMenuError(Exception):
    """
    Generic timmenu-plugin error.
    """


@dataclass
class TimMenuInputModel:
    """Model for the information that is sent from browser (plugin AngularJS component)."""


def decide_menu_level(
    index: int,
    previous_level: int,
    level_indentations: list[TimMenuIndentation],
    max_level: int = 3,
) -> int:
    """
    Parse menu level from indentations by comparing to previously used, i.e. if user
    used (for first instances) 1 space for level 0, 3 spaces for level 1 and 5 spaces for level 2, then:

    - 0 spaces > 'YAML is malformed'; going below first indentation of an attribute is not allowed in YAML
    - 1 space > level 0
    - 2-3 spaces > level 1
    - 4-5 spaces > level 2
    - 6+ spaces > level 3

    Following level is always at most one greater than the previous, since skipping a level
    would make that menu unreachable by the user.

    :param index: Number of spaces before beginning of the list.
    :param previous_level: Previous menu's level.
    :param level_indentations: List of previously used level indentations.
    :param max_level: Level ceiling; further indentations go into the same menu level.
    :return: Menu level decided by indentation.
    """
    # TODO: Allow no max_level when recursive menu is implemented.
    for ind in level_indentations:
        if ind.is_this_level(index):
            return ind.level
    level = previous_level + 1
    level = max_level if level > max_level else level
    # If current item level isn't in the indentation list, add it.
    missing_level = True
    for ind in level_indentations:
        if ind.level is level:
            missing_level = False
            break
    if missing_level:
        level_indentations.append(
            TimMenuIndentation(
                level=level,
                spaces_min=level_indentations[-1].spaces_max + 1,
                spaces_max=index,
            )
        )
    return level


def set_attributes(line: str, item: TimMenuItem) -> None:
    """
    Adds attributes recognized from non-list line to the above menu item.
    Note: supports only one attribute per line.

    :param line: Attribute line in menu attribute.
    :param item: Previous menu item.
    """
    if not item.width:
        width = get_attribute(line, "width")
        if width:
            item.width = width
    if not item.height:
        height = get_attribute(line, "height")
        if height:
            item.height = height
    if not item.rights:
        rights = get_attribute(line, "rights")
        if rights:
            item.rights = rights


def get_attribute(line: str, attr_name: str) -> str | None:
    """
    Tries parsing given attributes value, if the string contains it.

    :param line: String in format "attribute_name: value".
    :param attr_name: Name of the attribute to get.
    :return: Attribute value, or None, if the line doesn't contain it.
    """
    try:
        return line[line.index(f"{attr_name}:") + len(attr_name) + 1 :].strip()
    except ValueError:
        return None


def parse_menu_string(menu_str: str, replace_tabs: bool = False) -> list[TimMenuItem]:
    """
    Converts menu-attribute string into a menu structure with html content.
    Note: string uses a custom syntax similar to markdown lists, with hyphen (-) marking
    a menu item and indentation its level. For example:
    ::
         - Menu title 1
           width: 100px
           - [Menu item 1](item_1_address)
           - [Menu item 2](item_2_address)
           - *Non-link item*
         - Menu title 2
           - Submenu title 1
             height: 60px
             - [Submenu item 1](submenu_item_1_address)
             - [Submenu item 2](submenu_item_2_address)
         - [Menu title as link](menu_title_address)

    :param menu_str: Menu as a single string.
    :param replace_tabs: Replace tabs with four spaces each.
    :return: Converted menu as list of menu item objects.
    """
    menu_split = menu_str.split("\n")
    if not menu_split:
        # TODO: Users can't see this!
        raise TimMenuError("'menu' is empty or invalid!")

    # Separate parts with text content for Dumbo conversion, because Dumbo breaks syntax.
    text_list = []
    for item in menu_split:
        try:
            list_symbol_index = item.index("-")
        except ValueError:
            # Attribute lines get a placeholder in list.
            text_list.append("")
            continue
        text_list.append(item[list_symbol_index + 1 :])
    html_text_list = call_dumbo(text_list)

    level_indentations = [TimMenuIndentation(level=0, spaces_min=0, spaces_max=0)]
    parents = [TimMenuItem(text="", level=-1, items=[])]
    previous_level = -1
    current = None
    for i, item in enumerate(menu_split, start=0):
        try:
            if replace_tabs:
                item = item.replace("\t", "    ")
            list_symbol_index = item.index("-")
        except ValueError:
            if current:
                set_attributes(item, current)
            continue
        level = decide_menu_level(list_symbol_index, previous_level, level_indentations)
        previous_level = level
        # Remove p-tags as unnecessary.
        text_html = html_text_list[i].replace("<p>", "").replace("</p>", "").strip()
        current = TimMenuItem(text=text_html, level=level, items=[])
        current.generate_id()
        for parent in parents:
            if parent.level < level:
                parent.items.append(current)
                parents.insert(0, current)
                break
    # List has all menus that are parents to any others, but first one contains the whole menu tree.
    return parents[-1].items


@dataclass
class TimMenuHtmlModel(
    GenericHtmlModel[TimMenuInputModel, TimMenuMarkupModel, TimMenuStateModel]
):
    def get_static_html(self) -> str:
        return render_static_timmenu(self)

    def get_component_html_name(self) -> str:
        return "timmenu-runner"

    def show_in_view_default(self) -> bool:
        return True

    def get_maybe_empty_static_html(self) -> str:
        """Renders a static version of the plugin."""
        return render_static_timmenu(self)

    def get_json_encoder(self) -> type[TimJsonEncoder]:
        return TimJsonEncoder

    def get_browser_json(self) -> dict:
        r = super().get_browser_json()
        r["menu"] = parse_menu_string(r["markup"]["menu"], replace_tabs=True)
        return r

    def requires_login(self) -> bool:
        return False

    def get_md(self) -> str:
        return ""


def render_static_timmenu(m: TimMenuHtmlModel) -> str:
    return render_template_string(
        f"""
<div class="TimMenu">TimMenu static placeholder</div>
<br>
        """,
        **asdict(m.markup),
    )


def reqs() -> PluginReqs:
    # Note: selecting the whole line doesn't work with underscore in some devices, so
    # camel case is used for parts meant to be replaced by the user.
    templates = [
        """
``` {plugin="timMenu" .hidden-print}
openingSymbol: "▼"
separator: "|"      
backgroundColor: "#F7F7F7"  # Menu bar background color (overrides basicColors)
textColor: black            # Menu bar text color (overrides basicColors)
fontSize: 0.84em
topMenu: false              # Show menu at the top when scrolling from below
basicColors: false          # Use TIM default color scheme in menu bar
keepLinkColors: true
hoverOpen: true             # Allow opening menus without clicking
menu: |!!
 - Menu title 1
   - [Menu item 1](item1Address)
   - [Menu item 2](item2Address)
   - [Menu item 3](item3Address)
   - *Non-link item with italics*
 - Menu title 2
   - Submenu title 1
     - [Submenu item 1](submenuItem1Address)
     - [Submenu item 2](submenuItem2Address)
     - Subsubmenu title 1
       - [Subsubmenu item 1](subsubmenuItem1Address)
   - [Menu item 4](item4Address)
   - [Menu item 5](item5Address)
 - [Title as direct link 1](title3Address)
 - [Title as direct link 2](title4Address)
!!
```
""",
        """
``` {plugin="timMenu" .hidden-print}
menu: |!!
 - Menu title 1
   - [Menu item](item1Address)
!!
```
""",
        f"""
``` {{plugin="timMenu" .hidden-print .{INCLUDE_IN_PARTS_CLASS_NAME}}}
topMenu: true
topMenuTriggerHeight: 200
openingSymbol: "▼"
separator: "|"      
backgroundColor: "#F7F7F7"  # Menu bar background color (overrides basicColors)
textColor: black            # Menu bar text color (overrides basicColors)
fontSize: 0.84em
topMenu: false              # Show menu at the top when scrolling from below
basicColors: false          # Use TIM default color scheme in menu bar
keepLinkColors: true
menu: |!!
 - Menu title 1
   - [Menu item 1](item1Address)
   - [Menu item 2](item2Address)
   - [Menu item 3](item3Address)
 - Menu title 2
   - [Menu item 4](item4Address)
   - [Menu item 5](item5Address)
   - Submenu title
     - [Submenu item 1](submenuItem1Address)
     - [Submenu item 2](submenuItem2Address)
 - [Title 3](title3Address)
!!
```
""",
        """
``` {plugin="timMenu" .hidden-print}
openingSymbol: "▼"
separator: "|"      
backgroundColor: "#F7F7F7"  # Menu bar background color (overrides basicColors)
textColor: black            # Menu bar text color (overrides basicColors)
fontSize: 0.84em
topMenu: false              # Show menu at the top when scrolling from below
basicColors: false          # Use TIM default color scheme in menu bar
keepLinkColors: true
topMenu: true
menu: |!!
 - Menu title 1
   width: 7.5em
   - [Menu item 1](item1Address)
   - [Menu item 2](item2Address)
   - [Menu item 3](item3Address)
 - Menu title 2
   width: 7.5em
   - [Menu item 4](item4Address)
   - [Menu item 5](item5Address)
   - Submenu title
     - [Submenu item 1](submenuItem1Address)
     - [Submenu item 2](submenuItem2Address)
 - Menu title 3
   width: 7.5em
   - [Menu item 6](item6Address)
   - [Menu item 7](item7Address)
   - [Menu item 8](item8Address)
 - [Menu title 4](title4Address)
    width: 7.5em
 - [Menu title 5](title5Address)
    width: 7.5em
!!
```
""",
    ]
    editor_tabs: list[EditorTab] = [
        {
            "text": "Insert",
            "items": [
                {
                    "text": "Menus",
                    "items": [
                        {
                            "data": templates[0].strip(),
                            "text": "timMenu",
                            "expl": "Add a dropdown menu bar with submenus",
                        },
                        {
                            "data": templates[1].strip(),
                            "text": "timMenu (simple)",
                            "expl": "Add a minimal dropdown menu bar",
                        },
                        {
                            "data": templates[2].strip(),
                            "text": "timMenu (sticky)",
                            "expl": "Add a dropdown menu bar that shows at the top when scrolling",
                        },
                        {
                            "data": templates[3].strip(),
                            "text": "timMenu (set width)",
                            "expl": "Add a dropdown menu bar with custom menu widths",
                        },
                    ],
                },
            ],
        },
    ]
    return {
        "js": ["timMenu"],
        "multihtml": True,
        "multimd": True,
        "editor_tabs": editor_tabs,
    }


timMenu_plugin = create_nontask_blueprint(
    __name__,
    "timMenu",
    TimMenuHtmlModel,
    reqs,
    csrf,
)
