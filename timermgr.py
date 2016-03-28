# coding: utf8

"""
写测试机器人的时候经常需要一个非阻塞的定时器
python自带的sched模块， 输入的timefunc如果是sleep，会阻塞，因此修改了run。
"""

import sched
import heapq
import time


class CTimerManager(sched.scheduler):
	def __init__(self, timefunc=None):
		if not timefunc:
			timefunc = time.time
		delayfun = None
		sched.scheduler.__init__(self, timefunc, delayfun)

	def run(self):
		while self._queue:
			runtime, priority, action, argument = checked_event = self._queue[0]
			now = self.timefunc()
			if now < runtime:
				return
			else:
				event = heapq.heappop(self._queue)
				if event is checked_event:
					action(*argument)
				else:
					heapq.heappush(self._queue, event)



if __name__ == '__main__':

	import sys
	usage = """
	python %(filename)s sched 
	python %(filename)s timer 
	"""%{"filename":sys.argv[0]}
	try:
		opt = sys.argv[1]
		if opt not in ('timer', 'sched'):
			raise Exception("bad option")
	except:
		print usage
	else:
		if opt == 'timer':
			timer = CTimerManager()
		else:
			timer = sched.scheduler(time.time, time.sleep)

		def callme():
			print time.strftime("%H:%M:%S"), "in callme"
			timer.enter(1,1, callme, ())

		timer.enter(1, 1, callme, ())

		i = 0
		while True:
			timer.run()
			i += 1
			time.sleep(0.5) # 客户端做其他事情
			print time.strftime("%H:%M:%S"), "something else...", i
			
			
			


