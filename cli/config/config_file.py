from configparser import ConfigParser
from pathlib import Path
from typing import Dict, Tuple, List, Any, TYPE_CHECKING, Optional

from cli.docker.service_variables import (
    tim_image_tag,
    csplugin_target,
    csplugin_image_tag,
)

if TYPE_CHECKING:
    from _typeshed import SupportsWrite


class ProxyDict:
    def set(self, key: str, value: Any) -> None:
        self.__dict__[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.__dict__.get(key, default)


class TIMConfig(ConfigParser):
    """
    TIM configuration file handler.
    """

    def __init__(self, save_path: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._comment_lines: Dict[Tuple[str, str], str] = {}
        self._save_path = save_path

    def add_comment(self, section: str, option: str, comment: str) -> None:
        self._comment_lines[(section, option)] = comment.strip()

    def load_ext_dict(self, ext_dict: Dict[str, Dict[str, Tuple[str, str]]]) -> None:
        for section, options in ext_dict.items():
            self.add_section(section)
            for key, (value, comment) in options.items():
                self.set(section, key, value)
                self.add_comment(section, key, comment)

    def save(self) -> None:
        with open(self._save_path, "w") as fp:
            self.write(fp)

    def env_dict(self, profile: Optional[str] = None) -> Dict[str, str]:
        env_dict: dict[str, Any] = {}
        for section in self._sections:  # type: ignore
            if section == "__meta__":
                continue
            for key in self._sections[section].keys():  # type: ignore
                env_dict[f"{section.upper()}_{key.upper()}"] = self.get(section, key)

        profile = profile or self.get("compose", "profiles")
        env_dict["COMPOSE_PROFILES"] = profile
        env_dict["TIM_IMAGE_TAG"] = tim_image_tag()
        env_dict["TIM_ROOT"] = Path.cwd().as_posix()
        env_dict["CSPLUGIN_TARGET"] = csplugin_target(profile)
        return env_dict

    def var_ctx(self, profile: Optional[str] = None) -> Dict[str, Any]:
        var_dict = {}
        for section in self._sections:
            var_dict[section] = ProxyDict()
            for key in self._sections[section].keys():
                if key == "dev":
                    var_dict[section].set(key, self.getboolean(section, key))
                else:
                    var_dict[section].set(key, self.get(section, key))
        var_dict["default"] = ProxyDict()
        for key in self._defaults.keys():
            var_dict["default"].set(key, self._defaults[key])

        profile = profile or self.get("compose", "profiles")
        var_dict["compose"].set("profiles", profile)
        var_dict["tim"].set("image_tag", tim_image_tag())
        var_dict["csplugin"].set("image_tag", csplugin_image_tag())
        var_dict["tim"].set("dev", profile == "dev")
        var_dict["csplugin"].set("target", csplugin_target(profile))
        return var_dict

    def write(
        self, fp: "SupportsWrite[str]", space_around_delimiters: bool = True
    ) -> None:
        if space_around_delimiters:
            d = " {} ".format(self._delimiters[0])  # type: ignore
        else:
            d = self._delimiters[0]  # type: ignore
        # Ensure meta is always written first
        meta_section = self._sections.get("__meta__")  # type: ignore
        if meta_section:
            self._write_section(fp, "__meta__", meta_section.items(), d)
        for section in self._sections:  # type: ignore
            if section == "__meta__":
                continue
            self._write_section(fp, section, self._sections[section].items(), d)  # type: ignore

    def _write_section(
        self,
        fp: "SupportsWrite[str]",
        section_name: str,
        section_items: List[Tuple[str, str]],
        delimiter: str,
    ) -> None:
        fp.write("[{}]\n".format(section_name))
        for key, value in section_items:
            comment = self._comment_lines.get((section_name, key))
            if comment:
                for comment_line in comment.splitlines():
                    fp.write("{} {}\n".format(self._comment_prefixes[0], comment_line))  # type: ignore
            value = self._interpolation.before_write(self, section_name, key, value)  # type: ignore
            if value is not None or not self._allow_no_value:
                value = delimiter + str(value).replace("\n", "\n\t")
            else:
                value = ""
            fp.write("{}{}\n\n".format(key, value))
        fp.write("\n")
