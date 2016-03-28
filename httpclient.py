# coding: utf8

import cStringIO
import pycurl
import urllib
import time
import logging

class CContext(object):
	def __init__(self):
		self.url = '' 
		self.callback = None 
		self.ctx = None 
		self.localfile = ''
		self.fd = None

	def clean(self):
		self.url = None
		self.callback = None
		self.ctx = None
		self.localfile = ''
		if self.fd:
			self.fd.close()
		self.fd = None

class CHttpClientManager(object):
	def __init__(self):
		self.curlmulti = pycurl.CurlMulti()
		self.handlemap = {}

	def on_handle_result(self, handle, errno=None, errmsg=None):
		my_ctx = self.handlemap.get(handle)
		if my_ctx:
			status = 0
			data = ''
			try:
				if errno is None and errmsg is None:
					status = handle.getinfo(handle.HTTP_CODE)
					if my_ctx.localfile:
						data = my_ctx.localfile
					else:
						data = my_ctx.fd.getvalue()
				else:
					data = errmsg
					
				if my_ctx.callback:
					my_ctx.callback(status, data, my_ctx.ctx)
			except:
				logging.exception("on_handle_result failed")

			my_ctx.clean()
			del self.handlemap[handle]

		handle.close()
		self.curlmulti.remove_handle(handle)
			
	def update(self):
		while True:
			ret, num = self.curlmulti.perform()
			if ret != pycurl.E_CALL_MULTI_PERFORM:
				break
			print ret

		while True:
			(num, ok_list, err_list) = self.curlmulti.info_read()

			for handle in ok_list:
				self.on_handle_result(handle)

			for handle, errno, errmsg in err_list:
				self.on_handle_result(handle, errno, errmsg)

			if num == 0:
				break			

			
	def request(self, url, args=None, headers=None, localfile=None, 
				callback=None, ctx=None, method='GET', timeout=30):
		handle = pycurl.Curl()
		my_ctx = CContext()
		my_ctx.url = url
		my_ctx.callback = callback
		my_ctx.ctx = ctx
		my_ctx.localfile = localfile

		#  必须把handle放入handlemap中保存
		#  否则离开这个函数, handle就会被释放
		self.handlemap[handle] = my_ctx

		if headers:
			headlist = []
			for key, value in headers:
				headlist.append( '%s: %s'%(key, value))
			handle.setopt(pycurl.HTTPHEADER, headlist)

		if method.upper() == 'POST':
			handle.setopt(pycurl.URL, url)
			handle.setopt(pycurl.POST, 1)
			if args:
				handle.setopt(pycurl.POSTFIELDS, urllib.urlencode(args))

		elif method.upper() == 'GET':
			if args:
				url = url.strip("?").strip()
				url += "?" + urllib.urlencode(args)
			handle.setopt(pycurl.URL, url)

		else:
			raise Exception("nonsupport method")

		my_ctx.fd = None
		if localfile:
			my_ctx.fd = open(localfile, 'wb')
		else:
			my_ctx.fd = cStringIO.StringIO()
		handle.setopt(pycurl.WRITEFUNCTION, my_ctx.fd.write)

		handle.setopt(pycurl.TIMEOUT, timeout)

		self.curlmulti.add_handle(handle)


if __name__ == '__main__':
	import gen

	@gen.coroutine
	def get(mgr, url):
		argv ={
			"url": url,
			"method": "GET",
		}
		print time.strftime("%H:%M:%S"), "begin to request", time.time()
		response = yield(mgr.request, argv)
		print time.strftime("%H:%M:%S"), "recv response:", time.time(), response

	mgr = CHttpClientManager()
	starttime = time.time()
	runflag = False
	while True:
		time.sleep(0.5) # TODO：这个时间的长短似乎会影响get的时间，需要看看curl的源码
		mgr.update()
		print time.strftime("%H:%M:%S"), "i'm doing sth else..."

		if time.time() - starttime>1 and (not runflag):
			get(mgr, url='http://baidu.com')
			runflag = True

		if time.time()-starttime>10:
			break


