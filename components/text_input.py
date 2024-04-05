from PyQt5.QtGui import QFont
from qfluentwidgets import PlainTextEdit


class PromptInput(PlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText(self.tr("Enter the description of the picture"))
        font = QFont()
        font.setFamily("Consolas")
        font.setPointSize(13)
        self.setFont(font)


class OCRInput(PlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText(self.tr("Enter the text contained in the image"))
        font = QFont()
        font.setFamily("Consolas")
        font.setPointSize(13)
        self.setFont(font)