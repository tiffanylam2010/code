local profile = require "cpu_profile"
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
	cb = foo
    mod.bar()
    cb()
	for i=1,n do
	end
	return test(n-1)
end

--profile.init()
--profile.profile(test, 2)
--profile.profile(test, 3)
profile.dump_stats()
