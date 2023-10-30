import time
import traceback
from typing import Optional
from collections import deque
from collections.abc import Callable
from functools import partial, wraps
from typing import ParamSpec, TypeVar

from qtpy.QtCore import Qt, QThread, QTimer, Signal
from qtpy.QtGui import QCloseEvent
from qtpy.QtWidgets import QProgressBar, QVBoxLayout, QWidget


P = ParamSpec("P")
R = TypeVar("R")


class PredictionTime:
    """
    A class to keep track of prediction time for different functions.
    """
    QUEUE_LEN = 3

    def __init__(self, dict_: dict[str, deque] | None = None):
        """
        Initialize the PredictionTime instance.

        Parameters
        ----------
        dict_ : dict[str, deque] | None, optional
            A dictionary to initialize the times, by default None
        """
        if dict_ is None:
            self.times = {}
        else:
            self.times = dict_

    def _set_time(self, key: str, end_time: float):
        """
        Set the time for a given key.

        Parameters
        ----------
        key : str
            The key identifier for the function.
        end_time : float
            The end time for the function execution.
        """
        if key in self.times:
            if len(self.times[key]) >= self.QUEUE_LEN:
                self.times[key].popleft()
            self.times[key].append(end_time)
        else:
            self.times[key] = deque([end_time])

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
        if key not in self.times:
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
        time_queue = self.times.get(key, [])
        return sum(time_queue) / len(time_queue) if time_queue else 0


prediction_time = PredictionTime()


class RunFunctionProgressBar(QWidget):
    """
    A class to display a progress bar for a running function.
    """

    finish_signal = Signal()
    error_signal = Signal()

    def __init__(self, closure: Callable[[], R],
               init_end_time: float,
               title: str | None = None,
               parent: QWidget | None = None,
               offset_pos: tuple[int, int] | None = None,
               ):
        """
        Initialize the RunFunctionProgressBar.

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
        self.key_name = (self.function_name
                         + repr(closure.args) + repr(closure.kwargs) + repr(closure.optional))
        print(self.key_name)

        self._init_ui(title=title)
        self._init_func_thread(closure=closure)
        prediction_time.init_time(key=self.key_name, end_time=init_end_time)
        self.function_timer = FunctionTimer(end_time=init_end_time, parent=self)

    def _init_ui(self, title: str | None):
        """
        Initialize the user interface.

        Parameters
        ----------
        title : str | None
            The title of the progress bar window.
        """
        self.setWindowTitle(
            f"{self.function_name} Progress Bar" if title is None else title)
        self.v_layout = QVBoxLayout()
        self.setLayout(self.v_layout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.v_layout.addWidget(self.progress_bar)

    def _init_func_thread(self, closure: Callable[[], R]):
        """Initialize the function worker thread.

        Parameters
        ----------
        closure : Callable
            The closure function to be executed in the worker thread.
        """
        self.func_thread = FunctionWorker(closure=closure, parent=self)

        self.func_thread.finished_signal.connect(self._finished)
        self.func_thread.result_signal.connect(self._result)
        self.func_thread.error_signal.connect(self._error)

    def _reset_timer(self):
        """
        Reset the timer.
        """
        del self.function_timer
        self.predicted_time = prediction_time.get_time(key=self.key_name)

        print(f'Get predicted_time: {self.predicted_time}')

        self.function_timer = FunctionTimer(end_time=self.predicted_time, parent=self)
        self.function_timer.progress_changed.connect(self._update_progressbar)

    def run(self):
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

    def _finished(self):
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

    def _result(self, values: object):
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

    def _error(self, err: tuple[Exception, str]):
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

    def _update_progressbar(self, i: int):
        """
        Update the progress bar value.

        Parameters
        ----------
        i : int
            The progress bar value.
        """
        self.progress_bar.setValue(i)

    def closeEvent(self, event: QCloseEvent):
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
    def make_closure(func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Callable[[], R]:
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
        Callable
            The closure function with arguments.
        """
        @wraps(func)
        def _func():
            return func(*args, **kwargs)

        _func.args = args
        _func.kwargs = kwargs
        _func.optional = None

        return _func


class FunctionTimer(QWidget):
    """
    A class to keep track of the progress of a running function.
    """

    progress_changed = Signal(int)

    def __init__(self, end_time: float,
                 parent: QWidget | None = None):
        """
        Parameters
        ----------
        end_time : float
            The time for the function execution.
        parent : QWidget | None, optional
            The parent widget, by default None
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

    def start(self):
        """
        Start the timer.
        """
        self.timer.start(self.millisec)

    def increment(self):
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

    def finish(self):
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

    def __init__(self, closure: Callable[[], R], parent: QWidget | None = None):
        """
        Parameters
        ----------
        closure : Callable
            The closure function to be executed in the worker thread.
        parent : QWidget | None, optional
            The parent object, by default None
        """
        super().__init__(parent)

        self.closure = closure

    def run(self):
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
