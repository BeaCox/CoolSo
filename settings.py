from typing import Union

from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QStandardPaths
from PyQt5.QtGui import QIcon, QColor, QDesktopServices
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QButtonGroup, QPushButton
from qfluentwidgets import (ScrollArea, SettingCardGroup, OptionsSettingCard, HyperlinkCard, PrimaryPushSettingCard,
                            RadioButton, setTheme, setThemeColor, isDarkTheme, LineEdit, ExpandGroupSettingCard, Theme,
                            ExpandLayout, ColorDialog, qconfig, ColorConfigItem, FluentIconBase, ComboBoxSettingCard,
                            InfoBar, SettingCard, FolderListSettingCard)
from qfluentwidgets import FluentIcon as FIF

import utils
from config import cfg, EMAIL, URL, AUTHOR, VERSION, YEAR


class SettingInterface(ScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.mongo_collection = utils.get_mongo_collection()
        self.expandLayout = ExpandLayout(self.scrollWidget)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        # Personalization group
        self.personalizationGroup = SettingCardGroup(self.tr("Personalization"), self.scrollWidget)

        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            self.tr("Application theme"),
            self.tr("Change the appearance of your application"),
            texts=[self.tr("Light"), self.tr("Dark"), self.tr("Use system setting")],
            parent=self.personalizationGroup
        )

        self.themeColorCard = ColorSettingCard(
            cfg.themeColor,
            FIF.PALETTE,
            self.tr('Theme color'),
            self.tr('Change the theme color of you application'),
            parent=self.personalizationGroup
        )

        self.languageCard = ComboBoxSettingCard(
            cfg.language,
            FIF.LANGUAGE,
            self.tr("Language"),
            self.tr("Set your preferred language for UI"),
            texts=['English', '简体中文', self.tr('Use system setting')],
            parent=self.personalizationGroup
        )

        # Configuration group
        self.configurationGroup = SettingCardGroup(self.tr("Configuration"), self.scrollWidget)
        self.folderCard = FolderListSettingCard(
            cfg.folder,
            self.tr("Local Picture Library"),
            directory=QStandardPaths.writableLocation(QStandardPaths.MusicLocation),
            parent=self.configurationGroup
        )
        self.URLCard = URLSettingCard(
            FIF.GLOBE,
            self.tr("URL"),
            self.tr("Configure the URL for online search"),
            parent=self.configurationGroup
        )

        # About group
        self.aboutGroup = SettingCardGroup(self.tr("About"), self.scrollWidget)
        self.helpCard = HyperlinkCard(
            URL,
            self.tr("Open help page"),
            FIF.HELP,
            self.tr("Help"),
            self.tr("Discover new features and learn useful tips about CoolSo"),
            self.aboutGroup
        )
        self.feedbackCard = PrimaryPushSettingCard(
            self.tr("Provide feedback"),
            FIF.FEEDBACK,
            self.tr("Provide feedback"),
            self.tr("Help us improve CoolSo by providing feedback"),
            self.aboutGroup
        )
        self.aboutCard = PrimaryPushSettingCard(
            self.tr("About us"),
            FIF.INFO,
            self.tr("About"),
            '© ' + self.tr('Copyright') + f" {YEAR}, {AUTHOR}. " +
            self.tr('Version') + f" {VERSION}",
            self.aboutGroup
        )

        self.__initWidget()

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 0, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        # initialize style sheet
        self.__setQss()

        # initialize layout
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        # add cards to group
        self.personalizationGroup.addSettingCard(self.themeCard)
        self.personalizationGroup.addSettingCard(self.themeColorCard)
        self.personalizationGroup.addSettingCard(self.languageCard)
        self.configurationGroup.addSettingCard(self.folderCard)
        self.configurationGroup.addSettingCard(self.URLCard)
        self.aboutGroup.addSettingCard(self.helpCard)
        self.aboutGroup.addSettingCard(self.feedbackCard)
        self.aboutGroup.addSettingCard(self.aboutCard)

        # add setting card group to layout
        self.expandLayout.setSpacing(20)
        self.expandLayout.setContentsMargins(60, 0, 60, 0)
        self.expandLayout.addWidget(self.personalizationGroup)
        self.expandLayout.addWidget(self.configurationGroup)
        self.expandLayout.addWidget(self.aboutGroup)

    def __showRestartTooltip(self):
        """ show restart tooltip """
        InfoBar.warning(
            self.tr('Setting changed'),
            self.tr('Configuration takes effect after restart'),
            parent=self.parent()
        )

    def __onThemeChanged(self, theme: Theme):
        setTheme(theme)
        self.__setQss()

    def __setQss(self):
        self.scrollWidget.setObjectName('scrollWidget')
        theme = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/{theme}.qss', 'r') as f:
            self.setStyleSheet(f.read())

    def __connectSignalToSlot(self):
        cfg.appRestartSig.connect(self.__showRestartTooltip)
        cfg.themeChanged.connect(self.__onThemeChanged)
        self.themeColorCard.colorChanged.connect(setThemeColor)
        self.folderCard.folderChanged.connect(self.clearDB)
        self.feedbackCard.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl(f"mailto:{EMAIL}?subject=CoolSo%20Feedback&body=Here%20is%20my%20feedback%20about"
                 "%CoolSo: ")))
        self.aboutCard.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(URL)))

    def clearDB(self):
        self.mongo_collection.drop()

class URLSettingCard(SettingCard):
    def __init__(self, icon: Union[str, QIcon, FluentIconBase], title, content=None, parent=None):
        super().__init__(icon, title, content, parent)
        self.urlLabel = LineEdit()
        self.urlLabel.setFixedWidth(200)
        self.urlLabel.setPlaceholderText(self.tr('Enter URL'))
        self.urlLabel.setText(cfg.URL.value)
        self.hBoxLayout.addWidget(self.urlLabel, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)
        self.urlLabel.textChanged.connect(self.__onURLChanged)

    def __onURLChanged(self, text: str):
        cfg.set(cfg.URL, text)

class ColorSettingCard(ExpandGroupSettingCard):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, configItem: ColorConfigItem, icon: Union[str, QIcon, FluentIconBase], title: str,
                 content=None, parent=None, enableAlpha=False):

        super().__init__(icon, title, content, parent=parent)
        self.enableAlpha = enableAlpha
        self.configItem = configItem
        self.defaultColor = QColor("#fab005")
        self.customColor = QColor(qconfig.get(configItem))

        self.choiceLabel = QLabel(self)

        self.radioWidget = QWidget(self.view)
        self.radioLayout = QVBoxLayout(self.radioWidget)
        self.defaultRadioButton = RadioButton(
            self.tr('Default color'), self.radioWidget)
        self.customRadioButton = RadioButton(
            self.tr('Custom color'), self.radioWidget)
        self.buttonGroup = QButtonGroup(self)

        self.customColorWidget = QWidget(self.view)
        self.customColorLayout = QHBoxLayout(self.customColorWidget)
        self.customLabel = QLabel(
            self.tr('Custom color'), self.customColorWidget)
        self.chooseColorButton = QPushButton(
            self.tr('Choose color'), self.customColorWidget)

        self.__initWidget()

    def __initWidget(self):
        self.__initLayout()

        if self.defaultColor != self.customColor:
            self.customRadioButton.setChecked(True)
            self.chooseColorButton.setEnabled(True)
        else:
            self.defaultRadioButton.setChecked(True)
            self.chooseColorButton.setEnabled(False)

        self.choiceLabel.setText(self.buttonGroup.checkedButton().text())
        self.choiceLabel.adjustSize()

        self.chooseColorButton.setObjectName('chooseColorButton')

        self.buttonGroup.buttonClicked.connect(self.__onRadioButtonClicked)
        self.chooseColorButton.clicked.connect(self.__showColorDialog)

    def __initLayout(self):
        self.addWidget(self.choiceLabel)

        self.radioLayout.setSpacing(19)
        self.radioLayout.setAlignment(Qt.AlignTop)
        self.radioLayout.setContentsMargins(48, 18, 0, 18)
        self.buttonGroup.addButton(self.customRadioButton)
        self.buttonGroup.addButton(self.defaultRadioButton)
        self.radioLayout.addWidget(self.customRadioButton)
        self.radioLayout.addWidget(self.defaultRadioButton)
        self.radioLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        self.customColorLayout.setContentsMargins(48, 18, 44, 18)
        self.customColorLayout.addWidget(self.customLabel, 0, Qt.AlignLeft)
        self.customColorLayout.addWidget(self.chooseColorButton, 0, Qt.AlignRight)
        self.customColorLayout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.viewLayout.setSpacing(0)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.addGroupWidget(self.radioWidget)
        self.addGroupWidget(self.customColorWidget)

    def __onRadioButtonClicked(self, button: RadioButton):
        """ radio button clicked slot """
        if button.text() == self.choiceLabel.text():
            return

        self.choiceLabel.setText(button.text())
        self.choiceLabel.adjustSize()

        if button is self.defaultRadioButton:
            self.chooseColorButton.setDisabled(True)
            qconfig.set(self.configItem, self.defaultColor)
            if self.defaultColor != self.customColor:
                self.colorChanged.emit(self.defaultColor)
        else:
            self.chooseColorButton.setDisabled(False)
            qconfig.set(self.configItem, self.customColor)
            if self.defaultColor != self.customColor:
                self.colorChanged.emit(self.customColor)

    def __showColorDialog(self):
        """ show color dialog """
        w = ColorDialog(
            qconfig.get(self.configItem), self.tr('Choose color'), self.window(), self.enableAlpha)
        w.colorChanged.connect(self.__onCustomColorChanged)
        w.exec()

    def __onCustomColorChanged(self, color):
        """ custom color changed slot """
        qconfig.set(self.configItem, color)
        self.customColor = QColor(color)
        self.colorChanged.emit(color)




