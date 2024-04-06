import os

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QStackedWidget, QApplication
from qfluentwidgets import FluentIcon, InfoBar, PushButton, SimpleCardWidget, SegmentedWidget, PrimaryPushButton
from PyQt5.QtGui import QImage, QKeySequence

import utils
import clip_model
import ocr_model
from components.fusion_input import FusionInput
from components.image_gallery import ImageGallery
from components.image_input import ImageInput
from components.text_input import PromptInput, OCRInput
from config import cfg
from search_services import SearchService
from import_images import import_single_image


class LocalSearchInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Local-Search-Interface")
        layout = QVBoxLayout()
        self.mongo_collection = utils.get_mongo_collection()
        self.inputCard = SearchMethods(parent=self)
        self.inputCard.setFocus()
        self.setFocusPolicy(Qt.StrongFocus)
        QTimer.singleShot(0, self.inputCard.ImageInterface.setFocus)
        self.updateInputCardHeight()
        self.outputCard = ImageGallery(isRemote=False)
        layout.addWidget(self.inputCard)
        layout.addWidget(self.outputCard)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste):
            self.pasteImageFromClipboard()
        else:
            super().keyPressEvent(event)

    def pasteImageFromClipboard(self):
        clipboard = QApplication.clipboard()
        mimeData = clipboard.mimeData()
        if mimeData.hasImage():
            image = QImage(mimeData.imageData())
            if isinstance(self.inputCard.stackedWidget.currentWidget(), ImageInput):
                self.inputCard.ImageInterface.setImage(image)
            elif isinstance(self.inputCard.stackedWidget.currentWidget(), FusionInput):
                self.inputCard.FusionInterface.imageInput.setImage(image)
            else:
                pass

        elif mimeData.hasUrls():
            urls = mimeData.urls()
            if len(urls) > 0:
                url = urls[0].toLocalFile()
                image = QImage(url)
                if isinstance(self.inputCard.stackedWidget.currentWidget(), ImageInput):
                    self.inputCard.ImageInterface.setImage(image)
                elif isinstance(self.inputCard.stackedWidget.currentWidget(), FusionInput):
                    self.inputCard.FusionInterface.imageInput.setImage(image)
                else:
                    pass

    def updateInputCardHeight(self):
        currentWidget = self.inputCard.stackedWidget.currentWidget()
        if currentWidget == self.inputCard.PromptInterface or currentWidget == self.inputCard.OCRInterface:
            self.inputCard.setFixedHeight(200)
        elif currentWidget == self.inputCard.ImageInterface:
            self.inputCard.setFixedHeight(300)
        elif currentWidget == self.inputCard.FusionInterface:
            self.inputCard.setFixedHeight(350)


class SearchMethods(SimpleCardWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.resize(400, 400)

        self.pivot = SegmentedWidget(self)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)

        self.search_service = SearchService()
        self.PromptInterface = PromptInput()
        self.OCRInterface = OCRInput()
        self.ImageInterface = ImageInput()
        self.FusionInterface = FusionInput()

        self.addSubInterface(self.PromptInterface, 'PromptInterface', self.tr('By Prompt'))
        self.addSubInterface(self.OCRInterface, 'OCRInterface', self.tr('By OCR'))
        self.addSubInterface(self.ImageInterface, 'ImageInterface', self.tr('By Image'))
        self.addSubInterface(self.FusionInterface, 'FusionInterface', self.tr('Fusion'))

        self.clearButton = PushButton(FluentIcon.DELETE, self.tr("Clear"))
        self.clearButton.clicked.connect(self.onClearButtonClicked)
        self.searchButton = PrimaryPushButton(FluentIcon.SEARCH, self.tr("Search"))
        self.searchButton.clicked.connect(self.onSearchButtonClicked)
        self.updateButton = PrimaryPushButton(FluentIcon.UPDATE, self.tr("Update"))
        self.updateButton.clicked.connect(self.onUpdateButtonClicked)
        self.clearButton.setFixedWidth(120)
        self.searchButton.setFixedWidth(120)
        self.updateButton.setFixedWidth(120)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.clearButton)
        buttonsLayout.addWidget(self.updateButton)
        buttonsLayout.addWidget(self.searchButton)


        self.vBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(30, 10, 30, 10)
        self.vBoxLayout.addLayout(buttonsLayout)

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.stackedWidget.currentChanged.connect(self.parent().updateInputCardHeight)
        self.stackedWidget.setCurrentWidget(self.PromptInterface)
        self.pivot.setCurrentItem(self.PromptInterface.objectName())

    def addSubInterface(self, widget: QLabel, objectName, text):
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget),
        )

    def onSearchButtonClicked(self):
        global results
        if not self.checkImportStatus():
            return

        currentInterface = self.stackedWidget.currentWidget()
        if isinstance(currentInterface, (PromptInput, OCRInput, ImageInput)):
            query = self.getQueryFromInterface(currentInterface)
            if query is None:
                return
            if isinstance(query, str):
                if isinstance(currentInterface, PromptInput):
                    results = self.search_service.search_image(query, topn=20)
                elif isinstance(currentInterface, OCRInput):
                    results = self.search_service.search_ocr(query, topn=20)
            elif isinstance(query, QImage):
                results = self.search_service.search_image(query, topn=20)
            if results is not None:
                filenames = [filename for filename, _ in results]
                self.parent().outputCard.updateGallery(filenames)
        else:
            print("Unknown interface")


    def onClearButtonClicked(self):
        currentInterface = self.stackedWidget.currentWidget()
        if isinstance(currentInterface, PromptInput):
            currentInterface.clear()
        elif isinstance(currentInterface, OCRInput):
            currentInterface.clear()
        elif isinstance(currentInterface, ImageInput):
            currentInterface.clearContent()
        elif isinstance(currentInterface, FusionInput):
            currentInterface.propmtInput.clear()
            currentInterface.imageInput.clearContent()
        else:
            print("Unknown interface")
            return

    def onUpdateButtonClicked(self):
        if not self.checkImportStatus():
            return
        self.clearButton.setEnabled(False)
        self.searchButton.setEnabled(False)
        print("Start updating...\n")
        base_dirs = cfg.folder.value
        cursor = self.parent().mongo_collection.find({}, {"filename": 1})
        saved_filename_list = [obj["filename"] for obj in cursor]
        current_filename_list = []
        for base_dir in base_dirs:
            abs_files = [os.path.join(base_dir, file) for file in os.listdir(base_dir)]
            current_filename_list.extend(abs_files)
        
        # 检测新增
        cnt = 0
        for current_filename in current_filename_list:
            if current_filename not in saved_filename_list:
                cnt += 1
                import_single_image(current_filename, clip_model.get_model(), 
                                    ocr_model.get_ocr_model(), 
                                    utils.get_config(), 
                                    utils.get_mongo_collection())

        print("Finish updating. Updated {} item(s)".format(cnt))
        self.clearButton.setEnabled(True)
        self.searchButton.setEnabled(True)
        self.parent().outputCard.updateGallery()

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.pivot.setCurrentItem(widget.objectName())

    def checkImportStatus(self):
        if cfg.importFinished is False:
            InfoBar.error(
                title=self.tr("Error"),
                content=self.tr("Importing images, please wait."),
                parent=self
            ).show()
            return False
        return True

    def getQueryFromInterface(self, interface):
        if isinstance(interface, ImageInput):
            image = interface.convertToImage(interface.currentImage)
            if image is None:
                InfoBar.warning(
                    title=self.tr("Error"),
                    content=self.tr("Please upload an image first."),
                    parent=self
                ).show()
            return image
        else:
            if interface.toPlainText() == "":
                InfoBar.warning(
                    title=self.tr("Error"),
                    content=self.tr("Please enter your input."),
                    parent=self
                ).show()
                return None
            return interface.toPlainText()



