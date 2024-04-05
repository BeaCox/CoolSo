from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QFileDialog
from qfluentwidgets import ImageLabel, CommandBarView, Action, FluentIcon, FlyoutAnimationType, Flyout, InfoBar


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
