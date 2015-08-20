# coding: utf8

import os
import sys
import types
import zipfile
import marshal

"""	
import的搜索顺序:
	-> sys.meta_path (CFinder)
	-> frozen 
	-> sys.path_importer_cache + sys.path_hooks (CLoader)
	-> buid-in import

import(name):
	if name in sys.modules:
		return sys.modules[name]
		
	else:
		loader = None
		loader = find_module(name)
		if loader:
			module = loader.load_module(name)
			return module
		raise ImportError

find_module(name):

	# 1. 先搜索sys.meta_path:
	for finder in sys.meta_path:
		try:
			loader = finder.find_module(name, path)		
		except ImportError:
			continue
		if loader:
			return loader	
		
	# 2. 搜索frozen的
	try:
		loader = find_frozen(name)
	except ImportError:
		pass
	if loader:
		return loader
			
	# 3.搜索 sys.path_importer_cache + sys.path_hooks
	for path in sys.path:
		importer = None
		if path in sys.path_importer_cache:
			loader = sys.path_importer_cache[path]
		else:
			sys.path_importer_cache[path] = None
			
			for loaderclass in sys.path_hooks:
				try:
					loader = loaderclass(path)
					sys.path_importer_cache[path] = loader
					break
				except ImportError:
					continue
					
		if loader:
			try:
				if loader.find_module(name):
					return loader
			except:
				pass
	
	return None
			
----
后续: 
	test reload
	使用setup.py生成自己的zip包
	
"""

#  不用sys.path.sep, 因为windows和linux的不一样, 所以强制指定
PATH_SEP = "/"

def debug(msg):
	print ">>>  debug:", msg
	# pass
	
class CFinder(object):
	@classmethod
	def find_module(self, name, path=None):
		# 如果找到能处理的模块,则返回一个loader对象,
		# 否则返回None,或raise ImportError
		
		debug("CFinder.find_module(%r, %r)"%(name, path))
		if path is None:		
			# 把sys.path下的所有目录, 如果存在".myzip"结尾的,就主动把它加入sys.path中;
			for p in sys.path[:]:
				if not os.path.isdir(p): 
					continue
				# p is dir
				for name in os.listdir(p):
					if not name.endswith(CLoader.FILE_POSTFIX): 
						continue
					# name.endswith(CLoader.FILE_POSTFIX)
					filename = os.path.abspath( os.path.join(p, name) )
					if filename not in sys.path:
						debug("CFinder sys.path.insert(0, %r)"%filename)
						sys.path.insert(0, filename )

		return None

class CLoader(object):
	FILE_POSTFIX = ".myzip"

	TYPE_PACKAGE = 2
	TYPE_MODULE = 1
	TYPE_NONE = 0

	def __init__(self, path):
		# 如果此path不是自己要处理的,需要raise Exception 出来
		# 否则 认为此路径这个CLoader模块可以处理, 会被cache到sys.path_importer_cache中,
		# 下次遇到这个路径, 就会直接调用这个loader, 不会去找sys.path_hooks中的其他loader了

		debug("CLoader.__init__(%r)"%(path,))
		idx = path.find(self.FILE_POSTFIX)
		if idx >= 0:
			self.filename = path[:idx] + self.FILE_POSTFIX
			self.zipfile = zipfile.ZipFile(self.filename)
		else:
			raise ImportError("cannot load it")
		
	def find_module(self, name, path=None):
		# 如果找到,则返回一个loader对象(一般是self), 
		# 否则返回None,或raise ImportError

		debug("CLoader.find_module(%r, %r)"%(name, path))

		ptype, filename = self.__get_type_and_file(name)
		if ptype != self.TYPE_NONE:
			return self
		else:
			return None


	def load_module(self, name):
		"""
		新的module需要设在一下几个属性：
		__file__
		__name__
		__loader__
		__package__
		__path__： 如果是package，必须设置
		"""

		debug("CLoader.load_module(%r)"%name)

		realname = self.__realname(name.replace(".", PATH_SEP))

		module = types.ModuleType(name)
		module.__file__ = realname
		module.__loader__ = self

		if self.is_package(name):
			module.__path__ = [realname,]
			module.__package__ = name
		else:
			module.__package__ = name.rpartition('.')[0]
			
		code = self.get_code(name)
		sys.modules[name] = module
		exec code in module.__dict__
		
		return module


	def is_package(self, name):
		ptype, filename = self.__get_type_and_file(name)
		return ptype == self.TYPE_PACKAGE

	def __get_type_and_file(self, name):
		name = name.replace(".", PATH_SEP)

		ptype = self.TYPE_NONE

		filename = self.__check_exits(name + PATH_SEP + "__init__")
		if filename:
			ptype = self.TYPE_PACKAGE

		else: 
			filename = self.__check_exits(name)
			if filename:
				ptype = self.TYPE_MODULE

		return ptype, filename


	def __check_exits(self, name):
		name = name.replace(".", PATH_SEP)
		for ext in (".py", ".pyc", ".pyo"):
			filename = name + ext 
			# debug("__check_exits %r %r"%(filename, self.zipfile.namelist()))
			if filename in self.zipfile.namelist():
				return filename 
		return None

	def __realname(self, name):
		ptype, filename = self.__get_type_and_file(name)
		return self.filename + PATH_SEP + filename

	def get_source(self, name):
		return self.__get_data(name, only_pyfile=True)

	def get_code(self, name):
		ptype, filename = self.__get_type_and_file(name)
		data = self.get_data(name)
		
		# 如果对文件做过加密, 这里需要做解密操作
		data = self.do_decrypt(data)
		
		if filename.endswith(".py"):
			code = compile(data, self.__realname(name), 'exec')
		else:
			code = marshal.loads(data[8:])
		return code
		
	def do_decrypt(self, data):
		# 自己写自己的解密部分
		return data

	def get_data(self, name):
		return self.__get_data(name, only_pyfile=False)

	def __get_data(self, name, only_pyfile=False):
		ptype, filename = self.__get_type_and_file(name)
		if (not only_pyfile) or filename.endswith(".py"):
			return self.zipfile.read(filename)
		else:
			return None


sys.meta_path.insert(0, CFinder)
sys.path_hooks.insert(0, CLoader)

if __name__ == '__main__':
	# sys.path.append("src.myzip")
	
	# 临时用base64做一下所谓的加密(注意:base64不是加密!实际应用中不要用)
	import base64
	def encode(s):
		return base64.b64encode(s)
	def decode(s):
		return base64.b64decode(s)
	
	def create_myzip(zipfilename):
		"""
		生成一个src.myzip的zip文件:
		a.py
		pkg/
			__init__.py
			subpkg/
				__init__.py
		"""
		zipobj = zipfile.ZipFile(zipfilename, 'w')
		zipobj.writestr("a.py", encode("def show():\n\tprint 'show in a'"))
		zipobj.writestr("pkg/__init__.py", encode("def show():\n\tprint 'show in pkg.__init__'"))
		zipobj.writestr("pkg/subpkg/__init__.py", encode("def show():\n\tprint 'show in pkg/subpkg/__init__'"))
		zipobj.close()
		
	# 在当前目录下创建一个src.myzip文件;
	# 由于CFinder会自动把src.myzip加入sys.path中
	# 所以会触发path_hooks的CLoader来解析src.myzip
	create_myzip("src.myzip")
	
	def do_decrypt(cls, s):
		return decode(s)
	CLoader.do_decrypt = do_decrypt
	
	def test_import(name):
		module = __import__(name)
		print module
		module.show()
		print
		print "reload(%s):"%name
		print reload(module)
		print "-"*80
		
	
	test_import("a")
	test_import("pkg")
	test_import("pkg.subpkg")

