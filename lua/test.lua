local monitor = require "timemonitor"
local mod = require "mod"

local function  bar()
    local k = 0
    for i=1, 10000 do
        k = i*i
    end
    return
end
local function foo()
    bar()
end


local function test(n, a)
	if n == 0 then
		return
	end
	for i=1,n do
	end
	foo()
    mod.bar()
	for i=1,n do
	end
	return test(n-1)
end

--print(monitor.depth(test, 2))
--print(monitor.depth(8, test, 10))
--print(monitor.report(test, 2))
monitor.detailreport(test, 2, 'aaa')
monitor.detailreport(test, 3, 'aaa')
print(monitor.showret())
