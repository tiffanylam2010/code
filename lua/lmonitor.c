#include <sys/time.h>
#include <lua.h>
#include <lauxlib.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>

// result_queue
// running_stack


#define REPORT_MAX (1024*1024)
#define FNAME_MAX 1024

// flag
#define SELF_TIME 1
#define TOTAL_TIME 2
#define COUNT  3

#define SHOW_MAX_LINE 100

#define SORT_ARGV_SELF 1
#define SORT_TOTAL_SELF 2
#define SORT_TYPE 1

struct running_item {
    char name[FNAME_MAX]; //名字:src:line:name
    unsigned long total_start_time; // 开始时间
    unsigned long self_start_time;
};

typedef struct result_item {
    char name[FNAME_MAX]; //名字
    unsigned long total_time; // 总时间
    unsigned long self_time; // 不包括递归的时间
    int count; // 调用次数
    unsigned long sort_time; //
    struct result_item *next;
    struct result_item *prev;
} result_item;

struct status {
    struct result_item *p_result;
    struct running_item  running_list[REPORT_MAX];
    int running_idx;
    char buffer[REPORT_MAX];
    int size;
};

static struct status * G = NULL;

static void
monitor_init(struct status * st) {
    st->p_result = NULL;
    st->running_idx = -1;
}

unsigned long get_now(){
    unsigned long t;
	struct timeval tv;
	gettimeofday(&tv, NULL);
	t = (unsigned long)tv.tv_sec * 1000000;
	t += tv.tv_usec ;
	return t;
}

unsigned long get_delta(unsigned long start_time) {
    return get_now() -start_time;
}

void add_time(struct status* st, char* name, unsigned long delta, int flag){
    struct result_item *p = st->p_result;
    struct result_item *last = NULL;
    while (p) {
        if(strcmp(p->name,name) == 0){
            break;
        }
        last = p;
        p = p->next;
    }
    if(p==NULL){
        p = (struct result_item*)malloc(sizeof(struct result_item));
        p->next = NULL;
        p->prev = NULL;
        p->total_time = 0;
        p->self_time = 0;
        p->count = 0;
        strcpy(p->name, name);
        //snprintf(p->name, FNAME_MAX, "%s", name);
        if (st->p_result==NULL){
            st->p_result = p;
        }
        if(last){
            last->next=p;
            p->prev=last;
        }
    }
    if(flag ==TOTAL_TIME){
        p->total_time += delta;
    }else if(flag == SELF_TIME){
        p->self_time += delta;
    }
    else if(flag==COUNT) {
        p->count ++;
    }
    //printf("add_time %s flag:%d cnt:%d\n",p->name,flag,p->count);

}

void show_name(struct result_item *item){
    struct result_item *tmp = item;
    printf("---------------------------\n");
    while (tmp) {
        printf("[%s](%u) -> ",tmp->name, (unsigned int)tmp->sort_time);
        tmp = tmp->next;
    }
    printf("\n");
    printf("---------------------------\n");
}
void sort_time(struct status *st){
    struct result_item *head=st->p_result;
    struct result_item *next=head;
    struct result_item *tmp;
    struct result_item *item;
    struct result_item *prev;
    //show_name(head);

    // 排序一下
    while (next){
        item = next;
        next = next->next;

        if (SORT_TYPE == SORT_ARGV_SELF) {
            item->sort_time = 0;
            if (item->count>0){
                item->sort_time = (unsigned long) (item->self_time/item->count);
            }

        }else{
            item->sort_time = (unsigned long) (item->self_time);
        }

        for(tmp=head;tmp != item; tmp=tmp->next){

            if (tmp->sort_time < item->sort_time) {

                (item->prev)->next = item->next;
                if (item->next){
                    (item->next)->prev = item->prev;
                }

                prev = tmp->prev;
                if (prev) {
                    prev->next = item;
                    item->prev = prev;
                    item->next = tmp;
                    tmp->prev = item;
                }else{
                    // it's head
                    item->prev = NULL;
                    item->next = tmp;
                    tmp->prev = item;
                    head = item;
                }
                //show_name(head);
                break;
            }
        }
    }
    st->p_result = head;

}


void show_time(struct status *st){
    int i=0;
    struct result_item *item;

    sort_time(st);
    item = st->p_result;

    st->size = snprintf(st->buffer, REPORT_MAX, "%10s %10s %10s %10s %10s %20s \n", 
            "count", "total_time", "argv_total", "self_time", "argv_self", "name");

    while(item){
        st->size += snprintf(st->buffer+st->size, REPORT_MAX, "%10d %10u %10u %10u %10u %20s\n", 
                item->count, 
                (unsigned int)item->total_time, 
                (unsigned int)((item->total_time)/(item->count)),
                (unsigned int)item->self_time, 
                (unsigned int)((item->self_time)/(item->count)),
                item->name
                );
        item=item->next;
        i++;
        if (i>=SHOW_MAX_LINE){
            break;
        }
    }
}

void record_call(struct status *s, lua_Debug *ar) {
    unsigned long delta;
    int flag;
    struct running_item * item;
	
    // 获取当前的tmp_idx时间，记录为is_self_time;
    if (s->running_idx>=0){
        item = &(s->running_list[s->running_idx]);
        delta = get_delta(item->self_start_time);
        flag= SELF_TIME;
        add_time(s, item->name, delta, flag);
    }

    s->running_idx ++;
    item = &(s->running_list[s->running_idx]);
    item->total_start_time = get_now();
    item->self_start_time = get_now();

    snprintf(item->name, FNAME_MAX, "%s:%d:%s",ar->short_src,ar->linedefined,ar->name);
    flag= COUNT;
    add_time(s, item->name, delta, flag);
    //printf("HOOKCALL %s:%d:%s\n", ar->short_src,ar->linedefined,ar->name);

}

void record_ret(struct status *s, lua_Debug *ar) {
    unsigned long delta;
    int flag;
    struct running_item * item;

    if (s->running_idx<0){
        return ;
    }
    item = &(s->running_list[s->running_idx]);
    delta = get_delta(item->total_start_time);
    flag = TOTAL_TIME;
    add_time(s, item->name, delta, flag);

    delta = get_delta(item->self_start_time);
    flag = SELF_TIME;
    add_time(s, item->name, delta, flag);

    s->running_idx --;

    if (s->running_idx>=0) {
        item = &(s->running_list[s->running_idx]);
        item->self_start_time = get_now();
    }

    //printf(">>> HOOKRET %s:%d:%s\n", ar->short_src,ar->linedefined,ar->name);
}
 
static void 
monitor_detailreport(lua_State *L, lua_Debug *ar) {
    unsigned long delta;
    int flag;
	struct status * s = G;
    struct running_item * item;
	lua_getinfo(L, "nS", ar);
	switch (ar->event) {
	case LUA_HOOKCALL:
        //printf(">> LUA_HOOKCALL %s:%d:%s\n", ar->short_src, ar->linedefined, ar->name);
        record_call(s, ar);
		break;
	case LUA_HOOKTAILCALL:
        //printf(">> LUA_HOOKTAILCALL %s:%d:%s\n", ar->short_src, ar->linedefined, ar->name);
        record_ret(s, ar);
        record_call(s, ar);
		break;

	case LUA_HOOKRET:
        //printf(">> LUA_HOOKRET %s:%d:%s\n", ar->short_src, ar->linedefined, ar->name);
        record_ret(s, ar);
        break;
	}
}

static int
ldetailreport(lua_State *L) {
	luaL_checktype(L, 1, LUA_TFUNCTION);
	lua_sethook(L, monitor_detailreport, LUA_MASKCALL | LUA_MASKRET | LUA_MASKLINE, 0);
	int args = lua_gettop(L) - 1;
	lua_call(L, args, 0);
	lua_sethook(L, NULL, 0 , 0);
	return 0;
}
static int
lshowret(lua_State *L){
    show_time(G);
	lua_pushlstring(L, G->buffer, G->size);
    return 1;
}

static int
lstart(lua_State *L){
    lua_sethook(L, monitor_detailreport, LUA_MASKCALL | LUA_MASKRET | LUA_MASKLINE, 0);
    return 0;
}

static int
lstop(lua_State *L){
    lua_sethook(L, NULL, 0, 0);
    return 0;
}

int
luaopen_timemonitor(lua_State *L) {
    G = malloc(sizeof(struct status));
    monitor_init(G);

	luaL_checkversion(L);
	luaL_Reg l[] = {
		{ "detailreport", ldetailreport },
        { "start", lstart},
        { "stop", lstop},
        { "showret", lshowret},
		{ NULL, NULL },
	};
	luaL_newlib(L,l);
	return 1;
}

