from enum import Enum

from PyQt5.QtCore import QLocale
from qfluentwidgets import (QConfig, ConfigSerializer, OptionsConfigItem, OptionsValidator, qconfig,
                            ConfigItem, FolderListValidator)


class Language(Enum):
    ENGLISH = QLocale(QLocale.English)
    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    AUTO = QLocale()

class LanguageSerializer(ConfigSerializer):
    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO


class Config(QConfig):

    language = OptionsConfigItem(
        "MainWindow", "Language", Language.ENGLISH, OptionsValidator(Language), LanguageSerializer(), restart=True)

    folder = ConfigItem("ImageSource", "Folders", [], FolderListValidator(), restart=True)

    uid = ConfigItem(
        "Pixiv", "UID", "")

    cookie = ConfigItem(
        "Pixiv", "Cookie", "")


URL = "https://github.com/BeaCox/CoolSo"
EMAIL = "wyt_0416@sjtu.edu.cn"
YEAR = 2024
AUTHOR = "CoolSo Team"
VERSION = "1.0"

cfg = Config()
qconfig.load('resource/config.json', cfg)
