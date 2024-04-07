from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout
from qfluentwidgets import SimpleCardWidget, BodyLabel, Slider, SpinBox

from components.image_input import ImageInput
from components.text_input import PromptInput


class FusionInput(SimpleCardWidget):
    def __init__(self):
        super().__init__()
        self.inputBoxLayout = QHBoxLayout()
        self.sliderBoxLayout = QHBoxLayout()
        self.vBoxLayout = QVBoxLayout()
        self.propmtInput = PromptInput()
        self.imageInput = ImageInput(430, 180)
        self.imageInput.setFixedWidth(460)
        self.weightLabel = BodyLabel(self.tr("Percentage weight of prompt:"))
        self.weightSlider = Slider(Qt.Horizontal)
        self.weightBox = SpinBox()

        self.inputBoxLayout.addWidget(self.propmtInput)
        self.inputBoxLayout.addWidget(self.imageInput)
        self.sliderBoxLayout.addWidget(self.weightLabel)
        self.sliderBoxLayout.addWidget(self.weightBox)
        self.sliderBoxLayout.addWidget(self.weightSlider)
        self.vBoxLayout.addLayout(self.inputBoxLayout)
        self.vBoxLayout.addLayout(self.sliderBoxLayout)
        self.setLayout(self.vBoxLayout)

        self.initUI()

    def initUI(self):
        self.weightSlider.setRange(0, 100)
        self.weightSlider.setValue(50)
        self.weightBox.setRange(0, 100)
        self.weightBox.setValue(50)

        self.weightSlider.valueChanged.connect(self.weightBox.setValue)
        self.weightBox.valueChanged.connect(self.weightSlider.setValue)
