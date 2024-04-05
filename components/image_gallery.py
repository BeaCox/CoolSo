from PyQt5.QtCore import QEasingCurve
from qfluentwidgets import SingleDirectionScrollArea, SmoothMode, SimpleCardWidget, FlowLayout, isDarkTheme

import utils
from components.image_card import ImageCard
from config import cfg


class ImageGallery(SingleDirectionScrollArea):
    def __init__(self, isRemote=False):
        super().__init__()
        self.isRemote = isRemote
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
        self.updateGallery()

        self.__setQss()

    def updateGallery(self, filename=None):
        # clear all images
        self.imageFlow.removeAllWidgets()

        if filename is None:
            cursor = utils.get_mongo_collection(isRemote=self.isRemote).find({}, {"filename": 1})
            image_paths = [obj["filename"] for obj in cursor]
            for imagePath in image_paths:
                imageCard = ImageCard(imagePath)
                imageCard.setFixedSize(162, 162)
                self.imageFlow.addWidget(imageCard)
        else:
            for imagePath in filename:
                imageCard = ImageCard(imagePath)
                imageCard.setFixedSize(162, 162)
                self.imageFlow.addWidget(imageCard)

    def __setQss(self):
        self.imageContainer.setObjectName('imageContainer')
        theme = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/{theme}.qss', 'r') as f:
            self.setStyleSheet(f.read())
