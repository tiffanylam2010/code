# coding:utf8
import ctypes
import pprint

EVENT_RET = 1 
EVENT_CALL = 0 
EVENT_TAILCALL = 4 
NANOSEC = 1000000000

EVT2NAME = {
        EVENT_RET: "EVENT_RET",
        EVENT_CALL: "EVENT_CALL",
        EVENT_TAILCALL: "EVENT_TAILCALL",
}

FILENAME = "./storage.so"
Lib = ctypes.cdll.LoadLibrary(FILENAME)

Lib.open.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
        ]
Lib.open.restype = ctypes.c_void_p

Lib.read_record.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulong), #nanosec
            ctypes.POINTER(ctypes.c_int),#event
            ctypes.c_char_p, #filename
            ctypes.POINTER(ctypes.c_int),#line
            ctypes.c_char_p, #funcname
        ]
Lib.read_record.restype = ctypes.c_int

def load(evt_shmkey, str_shmkey):
    st = Lib.open(10123,10124)
    st = Lib.open(evt_shmkey,str_shmkey)

    while True:
        filename = ctypes.create_string_buffer("NULL", 256)
        funcname = ctypes.create_string_buffer("NULL", 256)
        nanosec = ctypes.c_ulong(0)
        event = ctypes.c_int(0)
        line = ctypes.c_int(0)
        ret = Lib.read_record(st, nanosec, event, filename, line, funcname)
        if(ret==0):
            break
        else:
            # print("nanosec:%s event:%s file:%s line:%s func:%s"%(nanosec.value, event.value, filename.value, line.value, funcname.value))
            yield (nanosec.value, event.value, filename.value, line.value, funcname.value)
                
def parse(evt_shmkey, str_shmkey, output_file=None):
    parser = Parser()
    for nanosec, event, filename, line, funcname in load(evt_shmkey, str_shmkey):
        print("nanosec:%s event:%s file:%s line:%s func:%s"%(nanosec, event, filename, line, funcname))
        parser.add_record(nanosec, event, filename, line, funcname)
    #parser.to_csv(output_file)


class StackInfo(object):
    def __init__(self, nanosec, event, filename, line, funcname):
        self.nanosec = nanosec
        self.event = event
        self.filename = filename
        self.line = line
        self.funcname = funcname
        self.id = self.__id()
        self.last_nanosec = nanosec;

    def __id(self):
        if self.line > 0:
            return "%s:%s"%(self.filename, self.line)
        else:
            return "%s:%s:%s"%(self.filename, self.line, self.funcname)

    def __repr__(self):
        s = "time:%s event:%s filename:%s line:%s funcname:%s id:%s"\
                %(self.nanosec, EVT2NAME[self.event], self.filename, self.line, self.funcname, self.id)
        return s


class ResultInfo(object):
    def __init__(self, filename, line, funcname):
        self.filename = filename
        self.line = line
        self.funcname = funcname

        self.runtime_total = 0
        self.runtime_internal = 0
        self.call_count = 0
        self.caller_map = {}

    def __repr__(self):
        s = "file:%s line:%s func:%s total:%.5f internal:%.5f count:%s"\
                %(self.filename, self.line, self.funcname,
                        self.runtime_total*1.0/NANOSEC, self.runtime_internal*1.0/NANOSEC, self.call_count)

        pprint.pprint(self.caller_map)
        return s

class Parser(object):
    def __init__(self):
        self.stack = []
        self.result = {}

    def show(self):
        print("="*80)
        for id, info in self.result.iteritems():
            print(info)

    def add_record(self, nanosec, event, filename, line, funcname):
        info = StackInfo(nanosec, event, filename, line, funcname)
        if event == EVENT_CALL:
            self.__on_call(info)
        elif event == EVENT_TAILCALL:
            self.__on_call(info)
        else: 
            self.__on_ret(info.id, info.nanosec)

    def __get_ret(self, info):
        ret = self.result.get(info.id)
        if not ret:
            ret = ResultInfo(info.filename, info.line, info.funcname)
            self.result[info.id] = ret

        if info.funcname != ret.funcname and info.funcname != "NULL":
            ret.funcname = info.funcname

        return ret


    def __on_call(self, info):
        ret = self.__get_ret(info)

        caller = None
        if self.stack:
            caller = self.stack[-1]
            # 开始调用之前，先更新调用者的内部时间
            delta = info.nanosec - caller.last_nanosec
            self.result[caller.id].runtime_internal += delta

        self.stack.append(info)

    def __on_ret(self, id, now):
        last_info = self.stack.pop(-1)
        assert(last_info.id == id)

        ret = self.result[id]
        ret.call_count += 1

        delta_total = now - last_info.nanosec # 此函数运行的总时间
        ret.runtime_total += delta_total

        delta_internal = now - last_info.last_nanosec # 
        ret.runtime_internal += delta_internal

        if self.stack:
            caller = self.stack[-1]
            caller.last_nanosec = now

            if caller.id not in ret.caller_map:
                ret.caller_map[caller.id] = {"cnt":0, "time": 0}
            ret.caller_map[caller.id]["cnt"] += 1
            ret.caller_map[caller.id]["time"] += delta_total

            if last_info.event == EVENT_TAILCALL:
                self.__on_ret(caller.id, now)


if __name__ == '__main__':
    parse(10123, 10124)

