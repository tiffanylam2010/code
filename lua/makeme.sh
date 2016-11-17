#gcc -g -fPIC -o cpu_profile.so --shared -I/home/ltt/src/mmd/skynet/3rd/lua -L/home/ltt/src/mmd/build/static_lib -llua lua_cpu_profile.c 
gcc -g -fPIC -o cpu_profile.so --shared -I/home/ltt/src/mmd/skynet/3rd/lua -L/home/ltt/src/mmd/build/static_lib -llua lua_cpu_profile.c storage.c
gcc -g -fPIC -o storage.so --shared  storage.c

