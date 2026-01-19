import numpy as np
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QWidget, QToolBar, QTabWidget, QTableWidget, QToolButton
from PySide6.QtWidgets import QVBoxLayout, QGridLayout
from . import resources
from .resources import Icons
from .widgets.hex_editor_widget import HexEditorWidget


class TabPageWidget(QWidget):
    def __init__(self, tab_widget: QTabWidget, page_label: str):
        super().__init__(tab_widget)
        tab_widget.addTab(self, page_label)


class R3000PageCoderPageWidget(TabPageWidget):
    def __init__(self, tab_widget: QTabWidget):
        super().__init__(tab_widget, page_label='R3000 coder')
        self._main_layout = QVBoxLayout(self)
        self._toolbar = QToolBar(self)
        self._tt = QToolButton(self._toolbar)
        self._tt.setIcon(resources.load_icon(Icons.binary_24))
        #self._tt.triggered.connect(self._clicked)
        self._act = self._toolbar.addWidget(self._tt)
        self._tt.pressed.connect(self._clicked)
        self._act2 = QAction("Test action", self)
        self._act2.triggered.connect(self._clicked)
        self._toolbar.addAction(self._act2)
        self._coder_table_widget = QTableWidget(self)
        self._coder_table_widget.setColumnCount(5)
        self._coder_table_widget.setHorizontalHeaderLabels(["Encoding", "Opcode", "Arg 1", "Arg 2", "Arg 3"])
        self._main_layout.addWidget(self._toolbar)
        self._main_layout.addWidget(self._coder_table_widget)
        self._hex_widget = HexEditorWidget(self)
        self._hex_widget.set_column_bytes_count(16, group_size=2)
        self._hex_widget.set_data(np.arange(50, dtype=np.uint8))
        self._main_layout.addWidget(self._hex_widget, stretch=1)

    def _clicked(self):
        print("Triggered")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('AzureDreams Toolbox')
        self.resize(800, 600)
        self._main_tab_widget = QTabWidget(self)
        self._r3000_coder_page_widget = R3000PageCoderPageWidget(self._main_tab_widget)
        self.setCentralWidget(self._main_tab_widget)
