import io
import os

from PIL import Image
from PyQt5.QtCore import QEasingCurve, Qt, QByteArray, QBuffer, QTimer, QPoint, QIODevice
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QStackedWidget, QFileDialog, QApplication
from qfluentwidgets import (FluentIcon, PlainTextEdit, isDarkTheme, InfoBar, PushButton, FlowLayout, SimpleCardWidget,
                            ImageLabel, SingleDirectionScrollArea, SegmentedWidget, BodyLabel, PrimaryPushButton,
                            CommandBarView, Action, Flyout, FlyoutAnimationType, SmoothMode)
from PyQt5.QtGui import QFont, QPixmap, QImage, QKeySequence

import utils
import clip_model
import ocr_model
from config import cfg
from search_services import SearchService
from import_images import import_single_image


class SearchInterface(QWidget):
    def __init__(self, search_type="local", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.inputCard = SearchMethods()
        self.inputCard.setFocus()
        self.setFocusPolicy(Qt.StrongFocus)
        QTimer.singleShot(0, self.inputCard.ImageInterface.setFocus)
        self.outputCard = ImageGallery(search_type)
        self.inputCard.setFixedHeight(250)
        layout.addWidget(self.inputCard)
        layout.addWidget(self.outputCard)
        self.setLayout(layout)
        if search_type == "local":
            self.setObjectName("Local-Search-Interface")
        else:
            self.setObjectName("Online-Search-Interface")

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
            self.inputCard.ImageInterface.setImage(image)
        elif mimeData.hasUrls():
            urls = mimeData.urls()
            if urls:
                path = urls[0].toLocalFile()
                image = QImage(path)
                if not image.isNull():
                    self.inputCard.ImageInterface.setImage(image)
                else:
                    InfoBar.warning(
                        title=self.tr("Error"),
                        content=self.tr("Cannot load image from path."),
                        parent=self
                    ).show()

class SearchMethods(SimpleCardWidget):

    def __init__(self):
        super().__init__()
        self.resize(400, 400)

        self.pivot = SegmentedWidget(self)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)
        self.mongo_collection = utils.get_mongo_collection()

        self.search_service = SearchService()
        self.PromptInterface = PromptInterface()
        self.OCRInterface = OCRInterface()
        self.ImageInterface = ImageInterface()

        self.addSubInterface(self.PromptInterface, 'PromptInterface', self.tr('By Prompt'))
        self.addSubInterface(self.OCRInterface, 'OCRInterface', self.tr('By OCR'))
        self.addSubInterface(self.ImageInterface, 'ImageInterface', self.tr('By Image'))

        self.clearButton = PushButton(FluentIcon.BROOM, self.tr("Reset"))
        self.clearButton.clicked.connect(self.onClearButtonClicked)
        self.recognizeButton = PrimaryPushButton(FluentIcon.SEARCH, self.tr("Search"))
        self.recognizeButton.clicked.connect(self.onSearchButtonClicked)
        self.updateButton = PrimaryPushButton(FluentIcon.UPDATE, self.tr("Update"))
        self.updateButton.clicked.connect(self.onUpdateButtonClicked)
        self.clearButton.setFixedWidth(120)
        self.recognizeButton.setFixedWidth(120)
        self.updateButton.setFixedWidth(120)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.clearButton)
        buttonsLayout.addWidget(self.recognizeButton)
        buttonsLayout.addWidget(self.updateButton)

        self.vBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(30, 10, 30, 10)
        self.vBoxLayout.addLayout(buttonsLayout)

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
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
        currentInterface = self.stackedWidget.currentWidget()
        if self.mongo_collection.count_documents({}) == 0:
            InfoBar.error(
                title=self.tr("Error"),
                content=self.tr("Database is empty, check the settings or update."),
                parent=self
            ).show()
            return
        elif cfg.importFinished is False:
            InfoBar.error(
                title=self.tr("Error"),
                content=self.tr("Importing images, please wait."),
                parent=self
            ).show()
            return
        else:
            if isinstance(currentInterface, PromptInterface):
                query = currentInterface.toPlainText()
                results = self.search_service.search_image(query, topn=20)
            elif isinstance(currentInterface, OCRInterface):
                query = currentInterface.toPlainText()
                results = self.search_service.search_ocr(query, topn=20)
            elif isinstance(currentInterface, ImageInterface):
                image = currentInterface.convertToImage(currentInterface.currentImage)
                if image is None:
                    InfoBar.warning(
                        title=self.tr("Error"),
                        content=self.tr("Please upload an image first."),
                        parent=self
                    ).show()
                    return
                results = self.search_service.search_image(image, topn=20)
            else:
                print("Unknown interface")
                return

            filenames = [filename for filename, _ in results]
            self.parent().outputCard.updateGallery(filenames)

    def onClearButtonClicked(self):
        currentInterface = self.stackedWidget.currentWidget()
        if isinstance(currentInterface, PromptInterface):
            currentInterface.clear()
        elif isinstance(currentInterface, OCRInterface):
            currentInterface.clear()
        elif isinstance(currentInterface, ImageInterface):
            currentInterface.clearContent()
        else:
            print("Unknown interface")
            return
        self.parent().outputCard.updateGallery(self.parent().outputCard.get_image_paths(cfg.folder.value))

    def onUpdateButtonClicked(self):
        self.clearButton.setEnabled(False)
        self.recognizeButton.setEnabled(False)
        print("Start updating...\n")
        base_dirs = cfg.folder.value
        cursor = self.mongo_collection.find({}, {"filename": 1})  
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
        self.recognizeButton.setEnabled(True)
        self.onClearButtonClicked() # 刷新图库

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.pivot.setCurrentItem(widget.objectName())


class PromptInterface(PlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText(self.tr("Enter the description of the picture"))
        font = QFont()
        font.setFamily("Consolas")
        font.setPointSize(13)
        self.setFont(font)


class OCRInterface(PlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText(self.tr("Enter the text contained in the image"))
        font = QFont()
        font.setFamily("Consolas")
        font.setPointSize(13)
        self.setFont(font)


class ImageInterface(SimpleCardWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.currentImage = None
        self.initUI()

    def initUI(self):
        self.textLabel = BodyLabel(self.tr("Click to Upload / Drag & Drop / Paste (Ctrl + V)  an Image Here"), self)
        self.textLabel.setAlignment(Qt.AlignCenter)

        self.imageLabel = ImageLabel(parent=self)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setVisible(False)

        layout = QVBoxLayout()
        layout.addWidget(self.textLabel)
        layout.addWidget(self.imageLabel, 0, Qt.AlignCenter)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasImage() or event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        mimeData = event.mimeData()
        if mimeData.hasImage():
            self.currentImage = mimeData.imageData()
        elif mimeData.hasUrls():
            url = mimeData.urls()[0].toLocalFile()
            self.currentImage = QImage(url)
        if self.currentImage and not self.currentImage.isNull():
            self.switchToImageLabel(QPixmap.fromImage(self.currentImage))
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            fileName, _ = QFileDialog.getOpenFileName(self, self.tr("Open Image"), "", self.tr("Image Files (*.png "
                                                                                               "*.jpg *.bmp)"))
            if fileName:
                # load image from path
                image = QImage(fileName)
                self.currentImage = image
                pixmap = QPixmap.fromImage(image)
                self.switchToImageLabel(pixmap)

    def setImage(self, image):
        if isinstance(image, QImage) and not image.isNull():
            self.currentImage = image
            pixmap = QPixmap.fromImage(image)
            self.switchToImageLabel(pixmap)

    def paintEvent(self, event):
        super().paintEvent(event)

    @staticmethod
    def scaleToSize(pixmap, targetWidth, targetHeight):
        if pixmap.isNull():
            return QPixmap()

        scaledPixmap = pixmap.scaled(targetWidth, targetHeight, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return scaledPixmap

    def switchToImageLabel(self, pixmap):
        if pixmap.isNull():
            InfoBar.warning(
                title=self.tr("Image Load Error"),
                content=self.tr("Could not load the image."),
                parent=self.parent()
            ).show()
            return

        scaledPixmap = self.scaleToSize(pixmap, 500, 135)

        self.imageLabel.setPixmap(scaledPixmap)
        self.textLabel.setVisible(False)
        self.imageLabel.setVisible(True)

    def clearContent(self):
        self.imageLabel.clear()
        self.currentImage = None
        self.textLabel.setVisible(True)
        self.imageLabel.setVisible(False)

    def convertToImage(self, qimage):
        qbyte_array = QByteArray()
        buffer = QBuffer(qbyte_array)
        buffer.open(QIODevice.WriteOnly)
        qimage.save(buffer, "PNG")

        pil_image = Image.open(io.BytesIO(qbyte_array.data()))
        return pil_image


class ImageGallery(SingleDirectionScrollArea):
    def __init__(self, search_type="local"):
        super().__init__()
        self.setSmoothMode(SmoothMode.NO_SMOOTH)
        self.imageContainer = SimpleCardWidget()
        self.setWidget(self.imageContainer)
        self.setWidgetResizable(True)
        cfg.themeChanged.connect(self.__setQss)

        # image flow
        self.imageFlow = FlowLayout(self.imageContainer, needAni=False)
        self.imageFlow.setAnimation(250, QEasingCurve.OutQuad)
        self.imageFlow.setContentsMargins(30, 30, 30, 30)
        self.imageFlow.setVerticalSpacing(20)
        self.imageFlow.setHorizontalSpacing(10)
        if search_type == "local":
            imagePaths = self.get_image_paths(cfg.folder.value)
            for imagePath in imagePaths:
                imageCard = ImageCard(imagePath)
                imageCard.setFixedSize(168, 168)
                self.imageFlow.addWidget(imageCard)
        else:
            pass

        self.__setQss()

    def updateGallery(self, imagePaths):
        # clear all images
        self.imageFlow.removeAllWidgets()

        # add new images
        for imagePath in imagePaths:
            imageCard = ImageCard(imagePath)
            imageCard.setFixedSize(168, 168)
            self.imageFlow.addWidget(imageCard)

    def __setQss(self):
        self.imageContainer.setObjectName('imageContainer')
        theme = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/{theme}.qss', 'r') as f:
            self.setStyleSheet(f.read())

    def get_image_paths(self, directories):
        supported_extensions = {'.jpg', '.png', '.bmp', '.gif', '.jpeg'}
        image_paths = []
        for directory in directories:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if os.path.splitext(file)[1].lower() in supported_extensions:
                        image_paths.append(os.path.join(root, file))
        return image_paths


class ImageCard(ImageLabel):
    def __init__(self, imagePath, parent=None):
        super().__init__(parent)
        self.imagePath = imagePath
        self.image = QImage(imagePath)
        self.setBorderRadius(8, 8, 8, 8)

    def mousePressEvent(self, event):
        view = CommandBarView(self)
        view.addAction(Action(FluentIcon.COPY, self.tr('Copy'), triggered=self.copyImage))
        view.addAction(Action(FluentIcon.SAVE, self.tr('Save'), triggered=self.saveImage))
        view.resizeToSuitableWidth()

        x = self.width() / 3
        pos = self.mapToGlobal(QPoint(x, 0))
        Flyout.make(view, pos, self, FlyoutAnimationType.FADE_IN)

    def copyImage(self):
        pixmap = QPixmap(self.imagePath)
        if pixmap.isNull():
            InfoBar.error(
                title=self.tr("Error"),
                content=self.tr("Cannot load image from path."),
                parent=self.parent()
            ).show()
        else:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            InfoBar.success(
                title=self.tr("Success"),
                content=self.tr("Image copied to clipboard."),
                parent=self.parent()
            ).show()

    def saveImage(self):
        savePath, _ = QFileDialog.getSaveFileName(self, self.tr("Save Image"), "", "Image Files (*.png *.jpg *.bmp)")
        if savePath and not self.image.save(savePath):
            InfoBar.error(
                title=self.tr("Error"),
                content=self.tr("Failed to save the image."),
                parent=self.parent()
            ).show()
        elif savePath:
            InfoBar.success(
                title=self.tr("Success"),
                content=self.tr("Image successfully saved."),
                parent=self.parent()
            ).show()

