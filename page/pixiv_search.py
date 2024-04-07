from PIL.Image import Image
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QStackedWidget, QApplication
from qfluentwidgets import FluentIcon, InfoBar, PushButton, SimpleCardWidget, SegmentedWidget, PrimaryPushButton
from PyQt5.QtGui import QImage, QKeySequence

import utils
from components.fusion_input import FusionInput
from components.image_gallery import ImageGallery
from components.image_input import ImageInput
from components.pixiv_filter import SearchOptionCard
from components.text_input import PromptInput, OCRInput
from config import cfg
from import_remote import BookmarkCrawler, UserCrawler, KeywordCrawler
from search_services import SearchService

class PixivSearchInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Pixiv-Search-Interface")
        layout = QVBoxLayout()
        self.mongo_collection = utils.get_mongo_collection(isRemote=True)
        self.inputCard = SearchMethods(parent=self)
        self.inputCard.setFocus()
        self.setFocusPolicy(Qt.StrongFocus)
        QTimer.singleShot(0, self.inputCard.ImageInterface.setFocus)
        self.updateInputCardHeight()
        self.search_options = SearchOptionCard(FluentIcon.FILTER, self.tr("Search Options"))
        self.outputCard = ImageGallery(isRemote=True)
        layout.addWidget(self.inputCard)
        layout.addWidget(self.search_options)
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

        self.search_service = SearchService(isRemote=True)
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
        self.importButton = PrimaryPushButton(FluentIcon.DOWNLOAD, self.tr("Import"))
        self.importButton.clicked.connect(self.onImportButtonClicked)
        self.clearButton.setFixedWidth(120)
        self.searchButton.setFixedWidth(120)
        self.importButton.setFixedWidth(120)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.clearButton)
        buttonsLayout.addWidget(self.importButton)
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

    def onSearchButtonClicked(self):
        results = None
        if not self.checkDatabase():
            return
        currentInterface = self.stackedWidget.currentWidget()
        query = self.getQueryFromInterface(currentInterface)
        if query is None:
            return
        if isinstance(currentInterface, FusionInput):
            results = self.search_service.search_fusion(query['text'], query['image'], query['weight'], topn=20)
        elif isinstance(query, str):
            if isinstance(currentInterface, PromptInput):
                results = self.search_service.search_image(query, topn=20)
            elif isinstance(currentInterface, OCRInput):
                results = self.search_service.search_ocr(query, topn=20)
        elif isinstance(query, Image):
            results = self.search_service.search_image(query, topn=20)

        if results is not None:
            filenames = [filename for filename, _ in results]
            self.parent().outputCard.updateGallery(filenames)
        else:
            print("Unknown interface")

    def checkDatabase(self):
        if self.parent().mongo_collection.count_documents({}) == 0:
            InfoBar.error(
                title=self.tr("Error"),
                content=self.tr("Database is empty, check the settings or update."),
                parent=self
            ).show()
            return False
        return True

    def checkCookie(self):
        if cfg.cookie.value == "":
            InfoBar.error(
                title=self.tr("Error"),
                content=self.tr("Please enter your cookie in settings. \n Get it from F12 - Network - refresh - "
                                "copy the cookie"),
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
        elif isinstance(interface, FusionInput):
            image = interface.imageInput.convertToImage(interface.imageInput.currentImage)
            text = interface.propmtInput.toPlainText()
            weight = interface.weightBox.value() / 100
            if image is None or text == "":
                InfoBar.warning(
                    title=self.tr("Error"),
                    content=self.tr("Please complete both text and image inputs for fusion search."),
                    parent=self
                ).show()
                return None
            return {'image': image, 'text': text, 'weight': weight}
        else:
            text = interface.toPlainText()
            if text == "":
                InfoBar.warning(
                    title=self.tr("Error"),
                    content=self.tr("Please enter your input."),
                    parent=self
                ).show()
                return None
            return text

    def onImportButtonClicked(self):
        if not self.checkCookie():
            return
        self.clearButton.setEnabled(False)
        self.searchButton.setEnabled(False)
        if self.parent().search_options.buttonGroup.checkedButton() == self.parent().search_options.bookmarkOption:
            uid = self.parent().search_options.uidInput.text() or cfg.uid.value
            if uid:
                app = BookmarkCrawler(uid=uid)
            else:
                InfoBar.error(
                    title=self.tr("Error"),
                    content=self.tr("Please enter target uid in settings or search options.\n Get it from profile "
                                    "page: https://www.pixiv.net/users/{UID}"),
                    parent=self
                ).show()
                self.clearButton.setEnabled(True)
                self.searchButton.setEnabled(True)
                return None
        elif self.parent().search_options.buttonGroup.checkedButton() == self.parent().search_options.artistOption:
            artist_id = self.parent().search_options.artistIdInput.text()
            if artist_id:
                app = UserCrawler(artist_id=artist_id)
            else:
                InfoBar.error(
                    title=self.tr("Error"),
                    content=self.tr("Please enter an artist's uid."),
                    parent=self
                ).show()
                self.clearButton.setEnabled(True)
                self.searchButton.setEnabled(True)
                return None
        elif self.parent().search_options.buttonGroup.checkedButton() == self.parent().search_options.keywordOption:
            keyword = self.parent().search_options.keywordInput.text()
            if keyword:
                order = bool(self.parent().search_options.orderBox.currentIndex() == "Hottest")
                mode = self.parent().search_options.restrictBox.currentText()
                app = KeywordCrawler(keyword=keyword, order=order, mode=mode)
            else:
                InfoBar.error(
                    title=self.tr("Error"),
                    content=self.tr("Please enter a keyword."),
                    parent=self
                ).show()
                self.clearButton.setEnabled(True)
                self.searchButton.setEnabled(True)
                return None
        else:
            return None
        self.parent().mongo_collection.drop()
        app.run()
        self.clearButton.setEnabled(True)
        self.searchButton.setEnabled(True)
        self.parent().outputCard.updateGallery()

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.pivot.setCurrentItem(widget.objectName())

