# coding: utf8

import functools
import time

class CContext(object):
	def __init__(self, idx, generator):
		self.idx = idx
		self.generator = generator
		self.uptime = time.time()
	
	def generator_send(self, response):
		try:
			func, argv, = self.generator.send(response)
			self.uptime = time.time()
		except StopIteration:
			self.clean()
			return

		argv['callback'] = self.callback
		func(**argv)
		
	def clean(self):
		self.generator = None
		self.idx = 0
		
	def callback(self, *args, **argv):
		response = (args, argv)
		self.generator_send(response)
		
	def is_timeout(self, timeout):
		return time.time() - self.uptime>timeout



class CGeneratorManager(object):
	def __init__(self):
		self._idx = 0

	def coroutine(self, function):
		@functools.wraps(function)
		def wrapper(*args, **argv):
			self._idx += 1
			generator = function(*args, **argv)
			ctx = CContext(self._idx, generator)
			ctx.generator_send(None)
		return wrapper

		
manager = CGeneratorManager()
def coroutine(function):
	global manager
	return manager.coroutine(function)



if __name__ == '__main__':

	class CServer(object):
		def __init__(self):
			self.__reqmap = {}
			self.__idx = 0

		def update(self):
			timeout_list = []
			for idx, req in self.__reqmap.iteritems():
				if req["deadline"]<=time.time():
					timeout_list.append( idx )

			for idx in timeout_list:
				req = self.__reqmap.pop(idx)
				result = "hello: %s"%req['x']
				req["callback"](result)


		def req(self, x, callback):
			print time.strftime("%H:%M:%S"), "put req", x
			self.__idx += 1
			idx = self.__idx
			self.__reqmap[idx] = {'x':x,"callback": callback, "deadline": time.time()+2}
			return idx

	@coroutine
	def runme(svr):
		print "runme"
		for x in (11, 22, 33):
			response = yield(svr.req, {"x":x})
			print time.strftime("%H:%M:%S"), 'recv response.', response
		print "runme done=============="



	server = CServer()
	
	starttime = time.time()
	hasrun = False
	while True:
		time.sleep(0.5)
		server.update()
		print time.strftime("%H:%M:%S"), "i'm running...."

		if time.time()-starttime>1 and (not hasrun):
			it = runme(server)
			hasrun = True

		if time.time()-starttime>10:
			break
		


