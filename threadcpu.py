# coding: utf-8

"""
通过psutil模块定时监控指定进程的各线程cpu
"""

from psutil import Process
from psutil import _timer
from psutil import cpu_count


class ThreadInfo(object):
    def __init__(self, id, num_cpus):
        self.id = id
        self.num_cpus = num_cpus
        self._last_sys_cpu_times = None
        self._last_user_cpu_times = None
        self._last_timer = None
        self._cpu_percent = 0.0

    def update_cpu_percent(self, sys_cpu_times, user_cpu_times, timer):
        delta_proc, delta_time = None, None
        if self._last_user_cpu_times is not None:
            delta_proc = (user_cpu_times - self._last_user_cpu_times) + (sys_cpu_times - self._last_sys_cpu_times)
            delta_time = timer - self._last_timer

        self._last_user_cpu_times = user_cpu_times
        self._last_sys_cpu_times = sys_cpu_times
        self._last_timer = timer

        if delta_proc and delta_time:
            overall_cpus_percent = ((delta_proc / delta_time) * 100)
            single_cpu_percent = overall_cpus_percent * self.num_cpus
            self._cpu_percent = round(single_cpu_percent, 1)
        else:
            self._cpu_percent = 0.0
        return self._cpu_percent


class ThreadCPU(object):
    def __init__(self, process_or_pid):
        if isinstance(process_or_pid, Process):
            self.process = process_or_pid
        else:
            self.process = Process(process_or_pid)

        self._thread_map = {}
        self.num_cpus = cpu_count() or 1

    def cpu_percent(self):
        result = {}
        timer = _timer() * self.num_cpus
        for th in self.process.threads():
            thread_info = self._thread_map.get(th.id)
            if not thread_info:
                thread_info = ThreadInfo(th.id, self.num_cpus)
                self._thread_map[th.id] = thread_info
            cpu_percent = thread_info.update_cpu_percent(th.system_time, th.user_time, timer)
            result[th.id] = cpu_percent

        return result


if __name__ == "__main__":
    import time
    import sys

    pid = int(sys.argv[1])
    thcpu = ThreadCPU(pid)
    for x in range(100):
        ret = thcpu.cpu_percent()
        print ret[pid], ret, thcpu.process.cpu_percent()
        time.sleep(3)
