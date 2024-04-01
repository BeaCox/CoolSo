import sys
from PyQt5.QtCore import Qt, QTimer, QSize, QTranslator
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStackedWidget, QHBoxLayout, QLabel, QWidget, QFrame

from qfluentwidgets import (NavigationItemPosition, isDarkTheme, setTheme, Theme, qconfig, SplashScreen,
                            FluentTranslator, NavigationInterface)
from qfluentwidgets import FluentIcon as FIF
from qframelesswindow import FramelessWindow, StandardTitleBar


from config import cfg
from import_images import ImportThread
from search_ui import SearchInterface
from settings import SettingInterface


class Widget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.label = QLabel(text, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
        self.setObjectName(text.replace(' ', '-'))


class Window(FramelessWindow):

    def __init__(self):
        super().__init__()
        if sys.platform == "win32":  # taskbar icon
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CoolSo")

        self.splashScreen = SplashScreen(QIcon('resource/logo.ico'), self)
        self.splashScreen.setIconSize(QSize(120, 120))
        self.splashScreen.show()

        QApplication.processEvents()

        self.setTitleBar(StandardTitleBar(self))

        self.hBoxLayout = QHBoxLayout(self)
        self.navigationInterface = NavigationInterface(self, showMenuButton=True)
        self.stackWidget = QStackedWidget(self)

        cfg.themeChanged.connect(self.onThemeChanged)

        # create sub interface
        self.localSearchInterface = SearchInterface("local")
        self.onlineSearchInterface = SearchInterface("online")
        self.historyInterface = Widget(self.tr("To be finished..."), self)
        self.settingInterface = SettingInterface()

        self.stackWidget.addWidget(self.localSearchInterface)
        self.stackWidget.addWidget(self.onlineSearchInterface)
        self.stackWidget.addWidget(self.historyInterface)
        self.stackWidget.addWidget(self.settingInterface)

        # initialize layout
        self.initLayout()

        # add items to navigation interface
        self.initNavigation()

        self.startImportThread()

        QTimer.singleShot(1600, self.splashScreen.close)

        self.initWindow()

    def initLayout(self):
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, self.titleBar.height(), 0, 0)
        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addWidget(self.stackWidget)
        self.hBoxLayout.setStretchFactor(self.stackWidget, 1)

    def initNavigation(self):
        self.addSubInterface(self.localSearchInterface, FIF.HOME, self.tr("Local Search"))
        self.addSubInterface(self.onlineSearchInterface, FIF.GLOBE, self.tr("Pivix Search"))
        self.addSubInterface(self.historyInterface, FIF.HISTORY, self.tr("History"))
        # add item to bottom
        self.navigationInterface.addItem(
            routeKey='switch-theme',
            icon=FIF.CONSTRACT,
            text=self.tr("Switch Theme"),
            onClick=self.switchTheme,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )
        self.addSubInterface(self.settingInterface, FIF.SETTING, self.tr("Settings"), NavigationItemPosition.BOTTOM)

        self.stackWidget.currentChanged.connect(self.onCurrentInterfaceChanged)
        self.stackWidget.setCurrentIndex(0)
        initialWidget = self.stackWidget.currentWidget()
        self.navigationInterface.setCurrentItem(initialWidget.objectName())

    def initWindow(self):
        self.resize(1010, 800)
        self.setWindowIcon(QIcon('resource/logo.ico'))
        self.setWindowTitle('CoolSo')
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.setQss()

    def addSubInterface(self, w: QWidget, icon, text, position=NavigationItemPosition.TOP, parent=None):
        self.stackWidget.addWidget(w)
        self.navigationInterface.addItem(
            routeKey=w.objectName(),
            icon=icon,
            text=text,
            onClick=lambda: self.switchTo(w),
            position=position,
            tooltip=text,
            parentRouteKey=parent.objectName() if parent else None
        )

    def startImportThread(self):
        self.importThread = ImportThread(cfg.folder.value)
        self.importThread.start()

    def switchTo(self, widget):
        self.stackWidget.setCurrentWidget(widget)

    def onCurrentInterfaceChanged(self, index):
        widget = self.stackWidget.widget(index)
        self.navigationInterface.setCurrentItem(widget.objectName())

    def switchTheme(self):
        newTheme = Theme.LIGHT if isDarkTheme() else Theme.DARK
        qconfig.set(qconfig.themeMode, newTheme)
        return False

    def onThemeChanged(self, theme: Theme):
        setTheme(theme)
        self.setQss()

    def setQss(self):
        color = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/{color}.qss', encoding='utf-8') as f:
            self.setStyleSheet(f.read())


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)

    language = cfg.get(cfg.language).value

    fluentTranslator = FluentTranslator(language)
    translator = QTranslator()
    translator.load(language, "", "", "resource")

    app.installTranslator(fluentTranslator)
    app.installTranslator(translator)

    w = Window()
    w.show()
    app.exec_()
