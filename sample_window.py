import time
from collections.abc import Callable
from functools import partial
from typing import Optional
import random

from qtpy.QtWidgets import QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSpinBox, QApplication
from qtpy.QtGui import QCloseEvent

from progress_bar import RunFunctionProgressBar

def heavy_function(t: int) -> int:
    """
    The heavy function for test.
    """
    for i in range(t):
        time.sleep(1)
        print("Count: ", i+1)

    return t*10

def error_function(t: int) -> int:
    """
    The heavy function for test.
    """
    for i in range(t):
        time.sleep(1)
        print("Count: ", i+1)

        if i == 5:
            raise ValueError("Five!!")

    return t*10

def list_function(l : list[float]) -> float:
    sum = 0
    for f in l:
        for _ in range(10):
            time.sleep(0.1)
        sum += f
        print('Sum: ', f)
    return sum


# Alias for RunFunctionProgressBar
RFPB = RunFunctionProgressBar


class MainWindow(QMainWindow):
    """
    The main window class of the application.
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowTitle("Main Window")
        self.setGeometry(300, 300, 400, 100)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.v_layout = QVBoxLayout()
        self.central_widget.setLayout(self.v_layout)

        self.object_dict: dict[int, RFPB] = {}

        self.start_button1 = QPushButton("Start 1")
        self.progress_bar_window1 = self.init_progress_bar(0, self.start_button1)
        self.start_button1.clicked.connect(
            partial(self.show_progress_bar, self.progress_bar_window1,
                    closure=RFPB.make_closure(heavy_function, 10),
                    init_time=7, button=self.start_button1))
        self.v_layout.addWidget(self.start_button1)

        self.start_button2 = QPushButton("Start 2")
        self.progress_bar_window2 = self.init_progress_bar(1, self.start_button2)
        self.start_button2.clicked.connect(
            partial(self.show_progress_bar, self.progress_bar_window2,
                    closure=RFPB.make_closure(heavy_function, t=5),
                    init_time=7, button=self.start_button2))
        self.v_layout.addWidget(self.start_button2)

        self.start_button3 = QPushButton("Start 3")
        self.progress_bar_window3 = self.init_progress_bar(2, self.start_button3)
        self.start_button3.clicked.connect(
            partial(self.show_progress_bar, self.progress_bar_window3,
                    closure=RFPB.make_closure(error_function, 10),
                    init_time=7, button=self.start_button3))
        self.v_layout.addWidget(self.start_button3)

        self.h_layout = QHBoxLayout()
        self.start_button4 = QPushButton("Start 4")
        self.spin_box = QSpinBox(self)
        self.progress_bar_window4 = self.init_progress_bar(4, self.start_button4)
        self.start_button4.clicked.connect(
            partial(self.show_progressbar_w_spinbox, self.spin_box,
                    progress_bar=self.progress_bar_window4, button=self.start_button4))
        self.h_layout.addWidget(self.start_button4)
        self.h_layout.addWidget(self.spin_box)
        self.v_layout.addLayout(self.h_layout)

    def finished(self, window: RFPB, button: QPushButton):
        """
        Handle the finishing of function.
        """
        print("Returned Values: ", window.result_values)
        err = window.error_status
        if err is not None:
            print("Raise Error: \n" + err[1])
        button.setEnabled(True)

    def init_progress_bar(self, number: int, button: QPushButton) -> RFPB:
        progress_bar = RFPB(parent=self, offset_pos=(400, number*100))
        progress_bar.finish_signal.connect(partial(self.finished, progress_bar, button))
        self.object_dict[number] = progress_bar
        return progress_bar

    def show_progress_bar(self, progress_bar: RFPB, closure: Callable, init_time: float,
                          button: QPushButton, title: Optional[str] = None):
        """
        Show the progress bar window
        """
        button.setEnabled(False)
        progress_bar.set_closure(closure=closure, init_end_time=init_time)
        progress_bar.setWindowTitle(closure.__name__ if title is None else title)
        progress_bar.run()

    def show_progressbar_w_spinbox(self, spin_box: QSpinBox, *args, **kwargs):
        v = spin_box.value()
        closure = RFPB.make_closure(
            list_function, [random.random() for _ in range(v)])
        closure.args = None
        closure.kwargs = None
        closure.option = v
        title = f'List len = {v}'
        self.show_progress_bar(closure=closure, title=title, init_time=v, *args, **kwargs)

    def closeEvent(self, event: QCloseEvent):
        print(self.object_dict)
        for w in self.object_dict.values():
            w.close()
        return super().closeEvent(event)

if __name__=="__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
