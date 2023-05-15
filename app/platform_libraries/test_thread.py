__author__ = 'Estvan Huang <Estvan.Huang@wdc.com>'

# std modules
import sys
import threading


class TestThread(threading.Thread):
    """ A thread can keep exception object and return data. """

    def __init__(self, event, wait_time=60, **kwargs):
        super(TestThread, self).__init__(**kwargs)
        self.event = event
        self.wait_time = wait_time
        self.result = None # Return data from target function.
        self.exc_info = None # Exception object from target function.

    def run(self):
        """ DO NOT OVERWRITE ME """
        self.event.wait(self.wait_time) # For all thread start at same time.
        try:
            if self._Thread__target:
                self.result = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)
        except:
            self.exc_info = sys.exc_info() # exc_type, exc_obj, exc_trace
            raise
        finally:
            del self._Thread__target, self._Thread__args, self._Thread__kwargs

class MultipleThreadExecutor(object):
    """ A tool to execute a list of thread and raise exception during execution. """

    def __init__(self, logging=None):
        self.event = threading.Event() # for start thread.
        self.threads = []
        self.logging = logging

    def append_thread(self, thread):
        if not isinstance(thread, TestThread):
            raise ValueError('Not a TestThread')
        self.threads.append(thread)

    def append_thread_by_func(self, target, group=None, name=None, args=None, kwargs=None, wait_time=60):
        if not args: args = ()
        if not kwargs: kwargs = {}
        self.append_thread(TestThread(self.event, wait_time, target=target, group=group, name=name, args=args, kwargs=kwargs))

    def add_threads_by_func(self, number_of_thread, target, group=None, name=None, args=None, kwargs=None, wait_time=60):
        for idx in xrange(number_of_thread):
            self.append_thread_by_func(target, group, name, args, kwargs, wait_time)

    def run_threads(self):
        if self.logging: self.logging('Start run test threads...')
        for thread in self.threads: thread.start()
        self.event.set() # Release lock to start thread at the same time.
        for thread in self.threads: thread.join()
        for thread in self.threads:
            # Raise exceprion from thread.
            if thread.exc_info:
                if self.logging: self.logging('Catch an exception from thread: {}, and re-raise this exception'.format(thread._Thread__name))
                raise thread.exc_info[1]
        if self.logging: self.logging('Run test threads finish')
