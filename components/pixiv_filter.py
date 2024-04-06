from typing import Union

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QButtonGroup, QHBoxLayout, QWidget, QVBoxLayout
from qfluentwidgets import ExpandGroupSettingCard, RadioButton, LineEdit, ComboBox


class SearchOptionCard(ExpandGroupSettingCard):
    def __init__(self,  icon: Union[str, QIcon], title: str, content=None, parent=None):
        super().__init__(icon, title, content, parent=parent)

        # Radio buttons
        self.bookmarkOption = RadioButton(self.tr('By bookmark'))
        self.artistOption = RadioButton(self.tr('By artist'))
        self.keywordOption = RadioButton(self.tr('By keyword'))
        self.buttonGroup = QButtonGroup(self)
        self.buttonGroup.addButton(self.bookmarkOption)
        self.buttonGroup.addButton(self.artistOption)
        self.buttonGroup.addButton(self.keywordOption)

        # Bookmark option widgets
        self.bookmarkWidget = QWidget(self.view)
        self.bookmarkOptionLayout = QHBoxLayout(self.bookmarkWidget)
        self.bookmarkOptionLayout.addWidget(self.bookmarkOption)
        self.uidInput = LineEdit()
        self.uidInput.setFixedWidth(500)
        self.uidInput.setPlaceholderText("Enter bookmark owner uid")
        self.bookmarkOptionLayout.addWidget(self.uidInput)

        # Artist option widgets
        self.artistOptionWidget = QWidget(self.view)
        self.artistOptionLayout = QHBoxLayout(self.artistOptionWidget)
        self.artistOptionLayout.addWidget(self.artistOption)
        self.artistIdInput = LineEdit()
        self.artistIdInput.setFixedWidth(500)
        self.artistIdInput.setPlaceholderText("Enter artist uid")
        self.artistOptionLayout.addWidget(self.artistIdInput)

        # Keyword option widgets
        self.keywordOptionWidget = QWidget(self.view)
        self.keywordOptionLayout = QHBoxLayout(self.keywordOptionWidget)
        self.keywordOptionLayout.addWidget(self.keywordOption)
        self.orderBox = ComboBox()
        self.orderBox.setPlaceholderText("Search from")
        self.orderBox.addItem("Hottest")
        self.orderBox.addItem("Latest")
        self.orderBox.setCurrentIndex(-1)
        self.keywordOptionLayout.addWidget(self.orderBox)
        self.restrictBox = ComboBox()
        self.restrictBox.setPlaceholderText("Limit to")
        self.restrictBox.addItem("safe")
        self.restrictBox.addItem("r18")
        self.restrictBox.addItem("all")
        self.restrictBox.setCurrentIndex(-1)
        self.keywordOptionLayout.addWidget(self.restrictBox)
        self.keywordInput = LineEdit()
        self.keywordInput.setFixedWidth(500)
        self.keywordInput.setPlaceholderText("Enter keyword")
        self.keywordOptionLayout.addWidget(self.keywordInput)

        self.bookmarkOption.setChecked(True)
        self.__initLayout()

    def __initLayout(self):
        # Create a main layout to hold all options
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.bookmarkWidget)
        mainLayout.addWidget(self.artistOptionWidget)
        mainLayout.addWidget(self.keywordOptionWidget)

        self.viewLayout.addLayout(mainLayout)

        # ensure correct initial size
        self._adjustViewSize()
