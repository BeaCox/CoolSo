import io

from PyQt5.QtCore import Qt, QByteArray, QBuffer, QIODevice
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QVBoxLayout, QFileDialog
from qfluentwidgets import SimpleCardWidget, BodyLabel, ImageLabel, InfoBar
from PIL import Image

class ImageInput(SimpleCardWidget):
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

        scaledPixmap = self.scaleToSize(pixmap, 430, 180)
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
