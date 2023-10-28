import time
import traceback
from collections import UserDict, deque
from collections.abc import Callable
from functools import partial, wraps

from qtpy.QtCore import QObject, Qt, QThread, QTimer, Signal
from qtpy.QtGui import QCloseEvent
from qtpy.QtWidgets import (QApplication, QMainWindow, QProgressBar,
                            QPushButton, QVBoxLayout, QWidget)


class PredictionTime(UserDict[str, deque]):
    """
    A class to keep track of prediction time for different functions.
    """
    QUEUE_LEN = 3

    def __init__(dict_=None, /, **kwargs):
        super().__init__(dict_, **kwargs)

    def _set_time(self, key: str, end_time:float):
        """
        Set the time for a given key.

        Parameters
        ----------
        key : str
            The key identifier for the function.
        end_time : float
            The end time for the function execution.
        """
        if key in self:
            if len(self[key]) >= self.QUEUE_LEN:
                self[key].popleft()
            self[key].append(end_time)
        else:
            time_queue = deque([end_time])
            super().__setitem__(key=key, item=time_queue)

    def update_time(self, key: str, end_time: float):
        """
        Update the time for a given key.

        Parameters
        ----------
        key : str
            The key identifier for the function.
        end_time : float
            The end time for the function execution.
        """
        self._set_time(key=key, end_time=end_time)

    def init_time(self, key: str, end_time: float):
        """
        Initialize the time for a given key if it doesn't exist.

        Parameters
        ----------
        key : str
            The key identifier for the function.
        end_time : float
            The end time for the function execution.
        """
        if not key in self:
            self._set_time(key=key, end_time=end_time)

    def get_time(self, key: str) -> float:
        """
        Get the average time for a given key.

        Parameters
        ----------
        key : str
            The key identifier for the function.

        Returns
        -------
        float
            The average time for the function execution.
        """
        time_queue = super().__getitem__(key=key)
        return sum(time_queue)/len(time_queue)


prediction_time = PredictionTime()


class Closure(Callable):
    __name__ = Callable.__name__
    __args_repr__ = repr
    __kwargs_repr__ = repr


class RunFunctionProgressBar(QWidget):
    """
    A class to display a progress bar for a running function.
    """

    finish_signal = Signal()
    error_signal = Signal()

    def __init__(self, closure: Closure,
               init_end_time: float,
               title: str | None = None,
               parent: QWidget | None = None,
               offset_pos: tuple[int, int] | None = None,
               ) -> None:
        """
        Parameters
        ----------
        closure : Closure
            The closure function to be executed in the worker thread.
        init_end_time : float
            The time for the function execution.
        title : str | None, optional
            The title of the progress bar window, by default None
        parent : QWidget | None, optional
            The parent widget, by default None
        offset_pos : tuple[int, int] | None, optional
            The window position offset from the parent window, by default None
        """
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint
                            | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        if parent is not None:
            self.setFont(parent.font())
            if offset_pos is None:
                offset_pos = (150, 0)
            self.move(
                parent.geometry().x() + offset_pos[0],
                parent.geometry().y() + offset_pos[1]
            )

        self.function_name = closure.__name__
        self.key_name = (closure.__name__
                         + closure.__args_repr__ + closure.__kwargs_repr__)
        print(self.function_name)

        self._init_ui(title=title)
        self._init_func_thread(closure=closure)
        prediction_time.init_time(key=self.key_name, end_time=init_end_time)
        self.function_timer = FunctionTimer(end_time=init_end_time, parent=self)

    def _init_ui(self, title: str | None) -> None:
        """
        Initialize the user interface.

        Parameters
        ----------
        title : str | None
            The title of the  progress bar window.
        """
        self.setWindowTitle(
            f"{self.function_name} Progress Bar" if title is None else title)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.layout.addWidget(self.progress_bar)

    def _init_func_thread(self, closure: Closure) -> None:
        """Initialize the function worker thread.

        Parameters
        ----------
        closure : Closure
            The closure function to be executed in the worker thread.
        """
        self.func_thread = FunctionWorker(closure=closure, parent=self)

        self.func_thread.finished_signal.connect(self._finished)
        self.func_thread.result_signal.connect(self._result)
        self.func_thread.error_signal.connect(self._error)

    def _reset_timer(self) -> None:
        """
        Reset the timer.
        """
        del self.function_timer
        self.predicted_time = prediction_time.get_time(key=self.key_name)

        print(f'Get predicted_time: {self.predicted_time}')

        self.function_timer = FunctionTimer(end_time=self.predicted_time, parent=self)
        self.function_timer.progress_changed.connect(self._update_progressbar)

    def run(self,) -> None:
        """
        Run the function and start the progress timer.
        """
        if self.func_thread.isRunning():
            print("Working now")
        else:
            self.show()

            self.working_flag = True

            self._reset_timer()
            self.start_time = time.time()
            self.func_thread.start()
            self.function_timer.start()

    def _finished(self) -> None:
        """
        Handle the finishing of the function execution.

        This method is called when the function execution finished.
        It emits the finished_signal and updates the prediction time.
        """
        print('Finished!')
        self.finish_signal.emit()
        p_time = time.time() - self.start_time

        prediction_time.update_time(key=self.key_name, end_time=p_time)

        print('Take time:', p_time)

        self.function_timer.finish()
        self.close()

    def _result(self, values: object) -> None:
        """
        Handle the result of the function execution.

        Parameters
        ----------
        values : object
            The result values of the function execution.
        """
        print('Get result!')
        self.result_values = values
        self.error_status = None

    def _error(self, err: tuple[Exception, str]) -> None:
        """
        Handle the error during the function execution.

        Parameters
        ----------
        err : tuple[Exception, str]
            The exception raised during the function execution.
        """
        print('Error')
        self.error_status = err
        self.result_values = None
        self.error_signal.emit()

    def _update_progressbar(self, i: int) -> None:
        """
        Update the progress bar value.

        Parameters
        ----------
        i : int
            The progress bar value.
        """
        self.progress_bar.setValue(i)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handle the closing of the progress bar window.

        Parameters
        ----------
        event : QCloseEvent
            The close event.
        """
        if not self.func_thread.isFinished():
            self.result_values = None
            self.error_status = None
            self.func_thread.terminate()
            self.finish_signal.emit()
            self.error_signal.emit()
        return super().closeEvent(event)

    @staticmethod
    def make_closure(func: Callable, *args, **kwargs) -> Closure:
        """
        Create a closure function with arguments.

        Parameters
        ----------
        func : Callable
            The original function to be executed.
        *args
            The positional arguments for the function.
        **kwargs
            The keyword arguments for the function.

        Returns
        -------
        Closure
            The closure function with arguments.
        """
        @wraps(func)
        def _func():
            return func(*args, **kwargs)

        _func.__args_repr__ = repr(args)
        _func.__kwargs_repr__ = repr(kwargs)

        return _func


class FunctionTimer(QObject):
    """
    A class to keep track of the progress of a running function.
    """

    progress_changed = Signal(int)

    def __init__(self, end_time: float,
                 parent: QObject | None = None) -> None:
        """
        Parameters
        ----------
        end_time : float
            The time for the function execution.
        parent : QObject | None, optional
            The parent object, by default None
        """
        super().__init__(parent)

        self.end_time = end_time
        self.millisec = int(self.end_time*10)  # the millisec of 1 percent progress
                                               # self.end_time/100*1000
        self.timer = QTimer()

        self.timer.timeout.connect(self.increment)
        self.i = 0

        self.start_time = time.time()
        self.finish_flag = False

    def start(self) -> None:
        """
        Start the timer.
        """
        self.timer.start(self.millisec)

    def increment(self) -> None:
        """
        Increment the progress and emit the progress_changed signal.
        """
        if not self.finish_flag:
            self.i += 1
            if self.i < 100:
                self.timer.start(self.millisec)
                self.progress_changed.emit(self.get_percentage())

    def get_percentage(self, max_per: int = 99) -> float:
        """
        Calculate the percentage of progress.

        Parameters
        ----------
        max_per : int, optional
            The maximum percentage value, by default 99

        Returns
        -------
        float
            The percentage of progress.
        """
        percentage = int((time.time() - self.start_time)/self.end_time*100)
        return min(percentage, max_per)

    def finish(self) -> None:
        """
        Finish the progress and emit the progress_changed signal with 100.
        """
        self.progress_changed.emit(100)
        self.finish_flag = True
        self.timer.stop()


class FunctionWorker(QThread):
    """
    A worker thread to execute a function.
    """

    result_signal = Signal(object)
    error_signal = Signal(object)
    finished_signal = Signal()

    def __init__(self, closure: Closure ,parent: QObject | None = None) -> None:
        """
        Parameters
        ----------
        closure : Closure
            The closure function to be executed in the worker thread.
        parent : QObject | None, optional
            The parent object, by default None
        """
        super().__init__(parent)

        self.closure = closure

    def run(self) -> None:
        """
        Run the closure function and emit the result or error signal.

        If the closure function raises an exception, the error signal is emitted.
        Otherwise, the result signal is emitted with the result values.
        """
        try:
            r = self.closure()
        except Exception as e:
            self.error_signal.emit((e, traceback.format_exc()))
        else:
            self.result_signal.emit(r)
        finally:
            self.finished_signal.emit()


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


#alias
RFPB = RunFunctionProgressBar


class MainWindow(QMainWindow):
    """
    The main window class of the application.
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Main Window")
        self.setGeometry(300, 300, 200, 100)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.object_list: list[RFPB] = []

        self.start_button1 = QPushButton("Start 1")
        self.start_button1.clicked.connect(self.show_progress_bar1)
        self.layout.addWidget(self.start_button1)

        self.start_button2 = QPushButton("Start 2")
        self.start_button2.clicked.connect(self.show_progress_bar2)
        self.layout.addWidget(self.start_button2)

        self.start_button3 = QPushButton("Start 3")
        self.start_button3.clicked.connect(self.show_progress_bar3)
        self.layout.addWidget(self.start_button3)

    def finished(self, window: RFPB, button: QPushButton):
        """
        Handle the finishing of function.
        """
        print("Returned Values: ", window.result_values)
        err = window.error_status
        if err is not None:
            print("Raise Error: \n" + err[1])
        button.setEnabled(True)

    def show_progress_bar1(self) -> None:
        """
        SHow the progress bar window for function 1.
        """
        self.start_button1.setEnabled(False)
        progress_bar_window = RFPB(
            RFPB.make_closure(heavy_function, 10), init_end_time=7,
            parent=self, offset_pos=(300, 0),
        )
        progress_bar_window.finish_signal.connect(
            partial(self.finished, progress_bar_window, self.start_button1)
        )
        self.object_list.append(progress_bar_window)
        progress_bar_window.run()

    def show_progress_bar2(self) -> None:
        """
        SHow the progress bar window for function 2.
        """
        self.start_button2.setEnabled(False)
        progress_bar_window = RFPB(
            RFPB.make_closure(heavy_function, t=5), init_end_time=7,
            parent=self, offset_pos=(300, 100),
        )
        progress_bar_window.finish_signal.connect(
            partial(self.finished, progress_bar_window, self.start_button2)
        )
        self.object_list.append(progress_bar_window)
        progress_bar_window.run()

    def show_progress_bar3(self) -> None:
        """
        SHow the progress bar window for function 3.
        """
        self.start_button3.setEnabled(False)
        progress_bar_window = RFPB(
            RFPB.make_closure(error_function, 10), init_end_time=7,
            parent=self, offset_pos=(300, 200),
        )
        progress_bar_window.finish_signal.connect(
            partial(self.finished, progress_bar_window, self.start_button3)
        )
        self.object_list.append(progress_bar_window)
        progress_bar_window.run()

    def closeEvent(self, event: QCloseEvent) -> None:
        for w in self.object_list:
            w.close()
        return super().closeEvent(event)

if __name__=="__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()

