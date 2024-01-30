# -*- coding: utf-8 -*-
import copy
import re
import threading
import time
import random
# from multiprocessing import Lock
# from multiprocessing import Queue
# from multiprocessing import Process as Thread
from threading import Thread, Event, Lock
from queue import Queue
import numpy as np
from sko.PSO import PSO
import Policy_Example
from TSN_Class import *
from conflict_elimination import conflict_indentify, conflict_elimination
from sko.tools import set_run_mode

class Frame:
    def __init__(self, name, sender, receiver, priority=7, size=100, frequency=10, lis_SFC=None,time_limit=1000,dic_microburst=None,loop=-1,end_queue=None):
        # 例： sensor_pressure2 = frame("sensor_pressure", "machine2", "controller2", 5, 100, 100, [se1, se5])  # size的单位是bit
        self.name = name
        #self.type=name.split("-")[0]#数据包的类型，用正则表达式也能处理，正则表达式语句为
        self.size = size
        self.frequency = frequency
        self.priority = priority
        self.timestamp = time.time()
        self.time = 0  # 最后，记录下总的传输时间
        self.sender = sender
        self.receiver = receiver
        self.lis_SFC = lis_SFC
        self.path = []
        self.current_node = 0  # path列表中的指示器
        self.dic_microburst = dic_microburst  #处理具有微突发性特征的信息流，如视频流,字典中包括三个键值对：p,amount,interval
        self.time_limit = time_limit  # 用于判断是否超时,单位为ms
        self.log=[]  # log the time on the way
        self.loop=loop

class Monitor(Thread):
    def __init__(self,dic_queue_res,dic_task_str,interval,accept_rate=0.,dic_time_avg={},frame_pool=[]):
        super(Monitor, self).__init__()
        self.accept_rate = accept_rate
        self.dic_queue_res=dic_queue_res
        self.interval=interval
        self.dic_task_str=dic_task_str
        self.dic_time_avg=dic_time_avg
        self.frame_pool=frame_pool

    def run(self):
        global loop
        with loop_lock:
            loop+=1
            loop_now=loop
        dic_total = {}
        dic_fail = {}
        monitor_loop=0
        dic_time_percent={}
        ind_end = 0
        dic_time_percent.clear()
        fp = open("txt_folder/result"+str(loop_now)+".txt", "a")
        for frame in self.frame_pool:
            if (frame.priority == 7 or frame.priority == 6) and frame.frequency < 50:  # 创建所有TT流且非突发流的字典
                dic_time_percent[frame.name] = []
                self.dic_time_avg[frame.name] = 0
            fp.write("frame.name: %s\n" % frame.name)
            # print("frame.name: %s" % frame.name)
            for vnf in frame.lis_SFC:
                fp.write("----vnf.name: %s\n" % vnf.name)
                # print("----vnf.name: %s " % vnf.name)
            fp.write("***********\n")
            # print("*******")
        time.sleep(30 * time_plus)  # 清空上一轮队列中的垃圾数据
        for key in self.dic_queue_res.keys():
            self.dic_queue_res[key].queue.clear()
            dic_total[key] = 0
            dic_fail[key] = 0
            dic_valid[key] = []
        time.sleep(self.interval * time_plus)
        for key in self.dic_queue_res.keys():  # key是字符串形式
            conflict_set = set()
            conflict_set.clear()
            while self.dic_queue_res[key].qsize() > 0:
                try:
                    result = self.dic_queue_res[key].get(timeout=time_thread_life)  ###此时其内容只是True或False
                except:
                    break
                dic_total[key] = dic_total[key] + 1
                if result[0]:
                    dic_fail[key] = dic_fail[key] + 1
                # 只查看TT流，求平均数据
                if key in dic_time_percent.keys():
                    dic_time_percent[key].append(result[3])
                    self.dic_time_avg[key] += result[3]
                # if result[1] == monitor_loop:  # 只记录该回合的数据
                #     dic_total[key] = dic_total[key] + 1
                #     if result[0]:
                #         dic_fail[key] = dic_fail[key] + 1
                #     # 只查看TT流，求平均数据
                #     if key in dic_time_percent.keys():
                #         dic_time_percent[key].append(result[3])
                #         self.dic_time_avg[key] += result[3]
            if key in dic_time_percent.keys():
                if len(dic_time_percent[key]) > 0:
                    self.dic_time_avg[key] = self.dic_time_avg[key] / len(dic_time_percent[key])
                else:
                    self.dic_time_avg[key] = 1000
            if (dic_total[key] > 0):
                fail_rate = dic_fail[key] / dic_total[key]
                fp.write(key + ":                                                   失效率%.2f\n" % fail_rate)
                # print("monitor:                                                   失效率%.2f" % fail_rate)
                if fail_rate > 2 * self.accept_rate:
                    ind_end = 1
                    for task in self.dic_task_str[key]:
                        conflict_set.add(task)
                    dic_has_conflict[key].append(conflict_set.copy())
                elif fail_rate > self.accept_rate and np.random.rand() < 0.5:  # 超出不多，有一定接收度
                    ind_end = 1
                    for task in self.dic_task_str[key]:
                        conflict_set.add(task)
                    dic_has_conflict[key].append(conflict_set.copy())
                else:
                    dic_valid[key].append(self.dic_task_str[key].copy())
            else:
                if dic_str_frame[key].frequency > self.interval:
                    dic_valid[key].append(self.dic_task_str[key].copy())
                elif dic_str_frame[key].frequency < self.interval / 2:
                    ind_end = 1
                    for task in self.dic_task_str[key]:
                        conflict_set.add(task)
                    dic_has_conflict[key].append(conflict_set.copy())
                else:
                    ind_end = 1
                # fp.write("monitor:                                                   没数据\n")
                fp.write(key + ":                                                   没数据\n")
                # print("monitor:                                                   没数据")
        monitor_loop += 1
        if ind_end == 0:
            fp.write("monitor:                                                   有可行解\n")
            # print("monitor:                                                   本轮失败率%.2f，低于接受率%.2f，结束仿真"%(dic_fail[key] / dic_total[key],self.accept_rate))
        fp.close()

    def stop(self):
        self.stop()
    def kill(self):
        self.kill()

class VNF:  # 待完成，里面有VNF的种类以及处理速度信息
    def __init__(self, name, speed,Le=1):
        super(VNF, self).__init__()
        self.id = id
        self.name = name
        self.speed = speed  # 单位Mbps
        self.Le=Le
    # code for multiprocess
    def __hash__(self):
        return hash(self.name+str(self.speed))

    def __eq__(self,other):
        return self.name==other.name and self.speed==other.speed


# 将TSN数控系统中的每一个组件，如video、controler等，抽象为一个类
class Object(Thread):
    def __init__(self, name, lst_message, bw, queue_in, queue_out, dic_vnf_q,dic_queue_result,end_queue=None):
        super(Object, self).__init__()
        self.name = name
        self.lst_message = lst_message  # 是list, 内装 dict  定义设备所produce的数据：frame及 间隔
        self.bw = bw  # 如 {"in": 0.1, "out": 0.1}  单位是多少？
        self.queue_in = queue_in  # 如果设备需从多个源读数据呢：按端口分类？  如果设备从多个端口读数据呢？
        self.queue_out = queue_out  # 如果设备 要产生多个端口的数据，怎么办？
        self.queue_wait = Queue()  # 自带的缓冲区
        self.dic_vnf_q = dic_vnf_q
        self.dic_queue_result=dic_queue_result
        self.end_queue=end_queue

    def run(self):
        if (self.queue_in):  # 指定了读入队列时，才启动读
            Thread(target=self.read, name=self.name + "_read").start()  # 读启动

        for msg in self.lst_message:  # 不同的message类型，启动不同的produce  注意！！，这些不同类型的message是混杂发送的
            Thread(target=self.produce, args=(msg,), name=self.name + "_produce_msg").start()

        if (self.queue_out):
            Thread(target=self.output, name=self.name + "_output").start()  # 输出启动

    def read(self):
        while self.end_queue.qsize()==0:
            try:
                msg = self.queue_in.get(timeout=time_thread_life)  # 如果没有数据会阻塞
            except:
                break
            msg.log.append("%s_%s_in" % (self.name,msg.name))
            msg.log.append(round(time.time()-msg.timestamp,6))
            msg.current_node += 1
            time.sleep((msg.size * 1000 / (self.bw["in"] * pow(1024, 3)))*time_plus)  # 读数据的时延,单位为ms，但是放大了1000倍
            tt=time.time()
            transportation_time = tt - msg.timestamp
            msg.time = transportation_time/time_plus
            is_exceed = msg.time > msg.time_limit
            #时延占据时延限制的比例
            time_percent=msg.time/msg.time_limit
            frame_priority=msg.priority
            #用正则表达式取字符串msg.name中字符“：”与字符“-”之间的内容，整句话为name= re.findall(r'(?<=:).*?(?=-)', msg.name)
            name = re.findall(r'(?<=:).*?(?=-)', msg.name)[0]
            #if msg.priority==6 or msg.priority==7:
            self.dic_queue_result[name].put(([is_exceed,msg.loop,frame_priority,time_percent]))  # 延时收集,为是否超时以及数据流属于第几次迭代,数据流优先级，时延占据时延限制的比例
            #data = [msg.name,msg.path,msg.time_limit,msg.time,is_exceed]
            data = (str(tt))+" "+ str(name) + " " + str(msg.time_limit) + " " + str(msg.time) + " " + str(is_exceed)    ########加了一个标记，以便区分不同次数的数据
            #data = "%s %s %s %s %s %s %s" % (name,tt,msg.log,msg.time,msg.time_limit,is_exceed,msg.path)
            #print(data)
            # print("  %s read: 数据包 %s，传输时间为%s ms" % (self.name, msg.name, transportation_time))
            #fp = open("txt_folder/"+str(name)+"_data.txt","a")
            # fp = open("txt_folder/data.txt", "a")
            #fp.write(data+"\n")
            #fp.close()
            # print("           数据包%s的路径是%s，指针是%s" % (msg.name, msg.path, msg.current_node))

    def output(self):
        while self.end_queue.qsize()==0:
            try:
                msg = self.queue_wait.get(timeout=time_thread_life)
            except:
                break
            # print("  %s output: 数据包 %s" % (self.name, msg.name,))
            time.sleep(msg.size * 1000 / (self.bw["out"] * pow(1024, 3))*time_plus)
            msg.log.append("%s_%s_out" % (self.name,msg.name))
            msg.log.append(round(time.time()-msg.timestamp,6))
            self.queue_out.put(msg)

    def produce(self, msgType):  # dict_msg是 frame
        time.sleep(random.randint(0,60)*time_plus)   ###即每个线程启动时停0到60毫秒
        i = 0
        # for j in range(1):
        while self.end_queue.qsize()==0:
            if msgType.dic_microburst is None:
                # 产生数据流
                name = self.name + ":" + msgType.name + "-" + str(i)
                #name = msg.name + "-" + str(i)
                frame_produce = Frame(name, self.name, msgType.receiver, msgType.priority,
                                      msgType.size, msgType.frequency, msgType.lis_SFC, msgType.time_limit, msgType.dic_microburst,loop)  ######如果设备固定SFC，则在这里进行处理，这里还能插入路径选择1算法
                i = i + 1
                frame_produce.path = self.calc_new_path(msgType)
                self.queue_wait.put(frame_produce)
                #print("  %s produce: 数据包 %s,队列长度为%d" % (self.name, name,len(frame_produce.lis_SFC)))
                time.sleep(msgType.frequency*time_plus)
            else:
                ind = random.random()    # [0,1)之间
                if ind < msgType.dic_microburst['p']:
                    for j in range(msgType.dic_microburst["amount"]):    ####微突发是同时无间隙发出大量数据
                        # 产生数据流
                        name = self.name + ":" + msgType.name + "-" + str(i)
                        frame_produce = Frame(name, self.name, msgType.receiver, msgType.priority,
                                              msgType.size, msgType.frequency, msgType.lis_SFC, msgType.time_limit,
                                              msgType.dic_microburst,loop)  ##如果设备固定SFC，则在这里进行处理，这里还能插入路径选择1算法
                        i = i + 1
                        frame_produce.path = self.calc_new_path(msgType)
                        self.queue_wait.put(frame_produce)
                        #print("  %s produce: 微突发数据包 %s" % (self.name, name,))
                time.sleep(msgType.dic_microburst["interval"]*time_plus)

    def calc_new_path(self, msgType):
        # 根据VNF序列决定path路径表，选取最短路径
        msgType.path.clear()
        msgType.path.append(self.name)
        for se in msgType.lis_SFC:  # msg.lis_SFC 举例：[se1, se3, se6]
            # 初始化，len取int的最大值
            len1 = 10000000  ############ 够大么？
            short_server = ""
            for server_name in self.dic_vnf_q[se.name].keys():  # dir_vnf_q 由se找到server及其queue 的dict
                # 打印每种vnf的每个队列中排队数
                # print("vnf %s, server %s, queue size %s" % (se.id, server_now, dir_vnf_q[se][server_now].qsize()))
                if len1 > self.dic_vnf_q[se.name][server_name].qsize():
                    len1 = self.dic_vnf_q[se.name][server_name].qsize()
                    short_server = server_name
            msgType.path.append(short_server)  #######每个frame在产生时就 决定了 se server的路径 ?
        msgType.path.append(msgType.receiver)  ########路径不应在开始固定，且数据无需总是在server与switch之间移动，也可能是直接在server上连续处理
        return msgType.path.copy()


# 一个带时钟的switch：switch启动时，时钟启动
# 在输入端：交换机持续读取输入数据，处理后，按数据敏感，把数据分别放入缓冲区：敏感队列1与非敏感队列2
# 在输出端：交换机按状态时间窗口，分别输出敏感数据与普通数据
# 问题：交换机的缓冲区有无大小限制
class Switch(Thread):
    def __init__(self, name, bw, dic_phy, in_q, out_q,end_queue=None):
        super(Switch, self).__init__()
        self.name = name
        self.bw = bw
        self.dic_phy = dic_phy
        self.in_q = in_q  # 输入队列
        self.out_q = out_q  # 输出队列
        self.status = 0  # 交换机的初始门控状态为0

        self.list_temp_q=[Queue() for i in range(8)]
        self.lst_event=[Event() for i in range(8)]
        self.end_queue=end_queue

    def run(self):
        Thread(target=self.tick).start()  # 时钟启动
        #Thread(target=self.read).start()  # 读启动
        for queue_in in self.in_q:
            Thread(target=self.read, args=(self.in_q[queue_in],)).start()
        Thread(target=self.pri,args=(7,0)).start()
        Thread(target=self.pri,args=(6,0)).start()
        Thread(target=self.pri,args=(5,2)).start()
        Thread(target=self.pri, args=(4,2)).start()
        Thread(target=self.pri, args=(3, 4)).start()
        Thread(target=self.pri, args=(2, 4)).start()
        Thread(target=self.pri, args=(1, 4)).start()
        Thread(target=self.pri, args=(0, 4)).start()
        # Thread(target=self.guard_TT).start()
        # Thread(target=self.gurad_AVB).start()

    def read(self, queue_in):
        while self.end_queue.qsize()==0:
            try:
                msg = queue_in.get(timeout=time_thread_life)  # 从输入队列中读取数据
            except:
                break
            msg.log.append("%s_%s_in" % (self.name,msg.name))
            msg.log.append(round(time.time()-msg.timestamp,6))
            # print("    switch read: 数据包 %s" % (msg.name,))
            time.sleep((msg.size * 1000 / (self.bw["in"] * pow(1024, 3)) + self.dic_phy["l_phy1"])*time_plus)  # 处理一个数据的时延
            # time.sleep(self.l_phy["l_phy1"])  # 读数据的时延
            # msg.path = msg.path + self.name  # 记录路径
            # if (msg.priority == 7 or msg.priority == 6):  ###### 这里王志通错了
            #     self.temp_hi_q.put(msg)  # 敏感数据放入缓冲区
            # else:
            #     self.temp_normal_q.put(msg)
            pri=msg.priority
            self.list_temp_q[pri].put(msg)  # 数据放入优先级队列

    def pri(self,priority,stat):
        while self.end_queue.qsize()==0:
            if (self.status == stat):
                try:
                    msg = self.list_temp_q[priority].get(timeout=time_thread_life)  # 如果队列没有数据，线程会阻塞
                except:
                    break
                time.sleep((msg.size * 1000 / (self.bw["out"] * pow(1024, 3)) + self.dic_phy["l_phy2"])*time_plus)  # 缓存输出所需的延时
                next_device = msg.path[msg.current_node + 1]  # 修改path列表的指针
                if (next_device in self.out_q.keys()):
                    msg.log.append("%s_%s_out" % (self.name,msg.name))
                    msg.log.append(round(time.time()-msg.timestamp,6))
                    self.lst_event[priority].wait(time_thread_life)
                    #print("    --switch: pri_%s输出数据 %s %s  %s:" % (priority, stat, self.status, msg.name))
                    self.out_q[next_device].put(msg)
                else:
                    print("error: %s not in out_q" % next_device)
            else:
                #print("pri_%s %s %s not equal1" % (priority,stat,self.status))
                self.lst_event[priority].wait(time_thread_life)
                #print("pri_%s %s %s not equal----" % (priority, stat, self.status))

    def tick(self):
        while self.end_queue.qsize()==0:
            #TT流
            #print("TT流 76")
            self.status = 0
            self.open_event([7, 6])
            time.sleep(0.4*time_plus)
            #TT流保护带
            #print("TT流保护带")
            self.status = 1
            self.open_event([])
            time.sleep((1518 * 1000 / (self.bw["out"] * pow(1024, 3)) + self.dic_phy["l_phy2"])*time_plus)
            #AVB流
            #print("AVB流 54")
            self.open_event([5,4])
            self.status = 2
            time.sleep(0.4*time_plus)
            #AVB流保护带
            #print("AVB流保护带")
            self.status=3
            self.open_event([])
            time.sleep((1518 * 1000 / (self.bw["out"] * pow(1024, 3)) + self.dic_phy["l_phy2"])*time_plus)
            #BE流
            #print("BE流 3210")
            self.open_event([3,2,1,0])
            self.status = 4
            time.sleep(0.2*time_plus)

    def open_event(self,lst):
        [eve.clear() for eve in self.lst_event]
        [self.lst_event[i].set() for i in lst]

    def deepcopy(self):
        return Switch(self.name,self.bw.copy,self.dic_phy.copy,self.in_q.copy,self.out_q.copy)


class Server(Thread):
    def __init__(self, name, dic_bw, queue_in, queue_out, dic_vnf_queue,end_queue=None):  # dic_vnfqueue为一个字典，key为vnf，value为一个队列
        # read操作为将queue_in中的数据读出，然后放入对应的dic_vnf_queue中的队列中
        # process操作为将dic_vnf_queue中的元素取出，处理一定的时间，放入queue_wait中
        # output操作为将queue_wait中的元素取出，放入queue_out中
        super(Server, self).__init__()
        self.name = name
        # self.lis_vnf=lis_vnf
        self.dic_bw = dic_bw
        self.queue_in = queue_in
        self.queue_wait = Queue()
        self.queue_out = queue_out
        self.dic_vnf_queue = dic_vnf_queue
        self.end_queue=end_queue

    def run(self):
        Thread(target=self.read).start()
        for vnf in self.dic_vnf_queue.keys():  # 一个VNF对象的queue, 开一个线程
            Thread(target=self.process, args=(vnf,)).start()
        Thread(target=self.output).start()

    def read(self):
        while self.end_queue.qsize()==0:
            try:
                msg = self.queue_in.get(timeout=time_thread_life)
            except:
                break
            msg.log.append("%s_%s_in" % (self.name,msg.name))
            msg.log.append(round(time.time()-msg.timestamp,6))
            msg.current_node += 1
            sleep_time = msg.size * 1000 / (self.dic_bw["in"] * pow(1024, 3))
            time.sleep(sleep_time*time_plus)
            # print("    server %s read： msg %s" % (self.name, msg.name))
            # 根据current_node指定的sfc_chain值放入指定队列   msg.lis_SFC 内容举例：[se1, se3, se6] 由se在dic_vnf_queue中找到相关server的队列
            self.dic_vnf_queue[msg.lis_SFC[msg.current_node - 1]].put(msg)  # se的位置总比path中的位置差一个

    def process(self, vnf):
        while self.end_queue.qsize()==0:
            try:
                msg = self.dic_vnf_queue[vnf].get(timeout=time_thread_life)
            except:
                break
            sleep_time = msg.size * 1000 / (vnf.speed * pow(1024, 2))  ####是Mbps, 2次方
            time.sleep(sleep_time*time_plus)
            self.queue_wait.put(msg)
            # print("    server %s process: msg %s,vnf.id is %s"%(self.name,msg.name,vnf.name))

    def output(self):
        while self.end_queue.qsize()==0:
            try:
                msg = self.queue_wait.get(timeout=time_thread_life)
            except:
                break
            sleep_time = msg.size * 1000 / (self.dic_bw["out"] * pow(1024, 3))
            time.sleep(sleep_time*time_plus)
            msg.log.append("%s_%s_out" % (self.name,msg.name))
            msg.log.append(round(time.time()-msg.timestamp,6))
            self.queue_out.put(msg)  ####server的输出不应总是 switch, 也可能是自己
            # print("    server %s output: msg %s"%(self.name,msg.name))
    def deepcopy(self):
        que_in=Queue()
        que_out=Queue()
        return Server(self.name, self.dic_bw.copy, que_in, que_out, copy.deepcopy(self.dic_vnf_queue))

def simulate(switch_pool, server_pool, object_pool):
    # 任务启动
    for switch in switch_pool:
        switch.daemon = True
        switch.start()
    for obj in object_pool:
        obj.daemon = True
        obj.start()
    for server in server_pool:
        server.daemon = True
        server.start()

def task_least_time(policy):
    # 任务最少时间
    ind=0
    task_least_time = 0x7fffffff
    i=0
    for tasks in policy.Tasks:
        time_plus=0
        for task in tasks:
            time_plus+=1000/(task.Delay*pow(1024,2))
        if time_plus<task_least_time:
            task_least_time=time_plus
            ind=i
        i+=1
    return ind
def task_choose(policy):
    #选择贪婪值最高的任务
    ind=0
    greedy_max=0
    i=0
    for tasks in policy.Tasks:
        greedy_plus=0
        for task in tasks:
            greedy_plus+=1/task.Delay
        greedy_plus=1/greedy_plus
        greedy_plus=greedy_plus*tasks[0].Le_C
        if greedy_plus>greedy_max:
            greedy_max=greedy_plus
            ind=i
        i+=1
    return ind
def target_function(p):
    end_q=Queue()
    '''所有的数据'''
    se1 = VNF("AES加密", 500, 1)
    se2 = VNF("DES加密", 60, 2)
    se3 = VNF("RSA-1024加密", 5, 3)
    se4 = VNF("RSA-2048加密", 1, 4)
    se5 = VNF("RSA-4096加密", 0.2, 4)
    se6 = VNF("AES解密", 500, 1)
    se7 = VNF("DES解密", 60, 1)
    se8 = VNF("RSA-1024解密", 1, 3)
    se9 = VNF("RSA-2048解密", 0.2, 4)
    se10 = VNF("RSA-4096解密", 0.05, 4)
    se11 = VNF("流量过滤1", 1000, 1)
    se12 = VNF("流量过滤2", 500, 3)
    se13 = VNF("RSA-1024数字签名", 1, 2)
    se14 = VNF("RSA-2048数字签名", 0.2, 3)
    se15 = VNF("RSA-4096数字签名", 0.05, 4)
    se16 = VNF("RSA-1024认证", 5, 2)
    se17 = VNF("RSA-2048认证", 1, 3)
    se18 = VNF("RSA-4096认证", 0.2, 4)

    vnf_pool = [se1, se2, se3, se4, se5, se6, se7, se8, se9, se10, se11, se12, se13, se14, se15, se16, se17, se18]
    vnf_cluster = [[se1, se6], [se2, se7], [se3, se8], [se4, se9], [se5, se10], [se11, ], [se12, ], [se13, se16],
                   [se14, se17], [se15, se18]]
    # dic_str_vnf= {"AES加密": se1, "DES加密": se2, "RSA-1024加密": se3, "RSA-2048加密": se4, "RSA-4096加密": se5, "AES解密": se6,
    #                 "DES解密": se7, "RSA-1024解密": se8, "RSA-2048解密": se9, "RSA-4096解密": se10, "流量过滤1": se11,
    #                 "流量过滤2": se12, "RSA-1024数字签名": se13, "RSA-2048数字签名": se14, "RSA-4096数字签名": se15, "RSA-1024认证": se16,
    #                 "RSA-2048认证": se17, "RSA-4096认证": se18}

    dic_vnf_q = {}  # 是一个二维字典，由vnf，找到服务器上的queue {se1:{server1:queue,server2:queue},......}
    dic_str_vnf = {}  # 由 se名字反查se
    for vnf in vnf_pool:
        dic_vnf_q[vnf.name] = {}
        dic_str_vnf[vnf.name] = vnf

    # 立式加工中心的数据流
    sensor_displayment1 = Frame("sensor_displayment1", "立式加工中心", "数控系统1", 7, 50, 5, [], 5)  # size的单位是bit
    sensor_acceleration1 = Frame("sensor_acceleration1", "立式加工中心", "数控系统1", 6, 50, 10, [], 20)  # size的单位是bit
    sensor_temperature1 = Frame("sensor_temperature1", "立式加工中心", "数控系统1", 5, 50, 100, [], 500)  # size的单位是bit
    sensor_pressure1 = Frame("sensor_pressure1", "立式加工中心", "数控系统1", 5, 50, 100, [], 500)  # size的单位是bit
    sensor_electricity1 = Frame("sensor_electricity1", "立式加工中心", "数控系统1", 5, 50, 100, [], 200)  # size的单位是bit
    sensor_alarm1 = Frame("sensor_alarm1", "立式加工中心", "数控系统1", 7, 500, 10000, [], 2,
                          {"p": 0.0001, "amount": 1, "interval": 100})  # size的单位是bit

    # 五轴精密加工中心的数据流
    sensor_displayment2 = Frame("sensor_displayment2", "五轴精密加工中心", "数控系统2", 7, 50, 5, [],
                                5)  # size的单位是bit
    sensor_acceleration2 = Frame("sensor_acceleration2", "五轴精密加工中心", "数控系统2", 6, 50, 10, [],
                                 20)  # size的单位是bit
    sensor_temperature2 = Frame("sensor_temperature2", "五轴精密加工中心", "数控系统2", 5, 50, 100, [],
                                500)  # size的单位是bit
    sensor_pressure2 = Frame("sensor_pressure2", "五轴精密加工中心", "数控系统2", 5, 50, 100, [],
                             500)  # size的单位是bit
    sensor_electricity2 = Frame("sensor_electricity2", "五轴精密加工中心", "数控系统2", 5, 50, 100, [],
                                200)  # size的单位是bit
    sensor_alarm2 = Frame("sensor_alarm2", "五轴精密加工中心", "数控系统2", 7, 500, 10000, [], 2,
                          {"p": 0.0001, "amount": 1, "interval": 100})  # size的单位是bit

    # 华数机器人的数据流
    sensor_displayment3 = Frame("sensor_displayment3", "华数机器人", "数控系统3", 7, 50, 5, [],
                                5)  # size的单位是bit
    sensor_acceleration3 = Frame("sensor_acceleration3", "华数机器人", "数控系统3", 6, 50, 10, [],
                                 20)  # size的单位是bit
    sensor_temperature3 = Frame("sensor_temperature3", "华数机器人", "数控系统3", 5, 50, 100, [],
                                500)  # size的单位是bit
    sensor_pressure3 = Frame("sensor_pressure3", "华数机器人", "数控系统3", 5, 50, 100, [], 500)  # size的单位是bit
    sensor_electricity3 = Frame("sensor_electricity3", "华数机器人", "数控系统3", 5, 50, 100, [],
                                200)  # size的单位是bit
    sensor_alarm3 = Frame("sensor_alarm3", "华数机器人", "数控系统3", 7, 500, 10000, [], 2,
                          {"p": 0.0001, "amount": 1, "interval": 100})  # size的单位是bit

    # 数控系统1的数据流
    control_instruction1 = Frame("control_instruction1", "数控系统1", "立式加工中心", 7, 50, 10, [],
                                 5)  # size的单位是bit
    control_instruction2 = Frame("control_instruction2", "数控系统1", "立式加工中心", 6, 50, 20, [],
                                 5)  # size的单位是bit
    control_instruction3 = Frame("control_instruction3", "数控系统1", "立式加工中心", 6, 50, 20, [],
                                 10)  # size的单位是bit
    data_feedback1 = Frame("data_feedback1", "数控系统1", "操作台", 3, 1200, 2000, [],
                           1000)  # size的单位是bit

    # 数控系统2的数据流
    control_instruction4 = Frame("control_instruction4", "数控系统2", "五轴精密加工中心", 7, 50, 10, [],
                                 5)  # size的单位是bit
    control_instruction5 = Frame("control_instruction5", "数控系统2", "五轴精密加工中心", 6, 50, 20, [],
                                 5)  # size的单位是bit
    control_instruction6 = Frame("control_instruction6", "数控系统2", "五轴精密加工中心", 6, 50, 20, [],
                                 10)  # size的单位是bit
    data_feedback2 = Frame("data_feedback2", "数控系统2", "操作台", 3, 1200, 2000, [],
                           1000)  # size的单位是bit

    # 数控系统3的数据流
    control_instruction7 = Frame("control_instruction7", "数控系统3", "华数机器人", 7, 50, 10, [],
                                 5)  # size的单位是bit
    control_instruction8 = Frame("control_instruction8", "数控系统3", "华数机器人", 6, 50, 20, [],
                                 5)  # size的单位是bit
    control_instruction9 = Frame("control_instruction9", "数控系统3", "华数机器人", 6, 50, 20, [],
                                 10)  # size的单位是bit
    data_feedback3 = Frame("data_feedback3", "数控系统3", "操作台", 3, 1200, 2000, [],
                           1000)  # size的单位是bit

    # 操作台的数据流
    process_instruction1 = Frame("process_instruction1", "操作台", "数控系统1", 2, 1000, 10000, [],
                                 1000)  # size的单位是bit
    process_instruction2 = Frame("process_instruction2", "操作台", "数控系统2", 2, 1000, 10000, [],
                                 1000)  # size的单位是bit
    process_instruction3 = Frame("process_instruction3", "操作台", "数控系统3", 2, 1000, 10000, [],
                                 1000)  # size的单位是bit

    # 录像机
    video = Frame("video", "录像机", "操作台", 4, 1518, 100, [], 1000,
                  {"p": 1, "amount": 200, "interval": 100})

    # 所有数据流集合
    frame_pool = [sensor_displayment1, sensor_acceleration1, sensor_temperature1, sensor_pressure1,
                  sensor_electricity1, sensor_alarm1,
                  sensor_displayment2, sensor_acceleration2, sensor_temperature2, sensor_pressure2,
                  sensor_electricity2, sensor_alarm2,
                  sensor_displayment3, sensor_acceleration3, sensor_temperature3, sensor_pressure3,
                  sensor_electricity3, sensor_alarm3,
                  control_instruction1, control_instruction2, control_instruction3, data_feedback1,
                  control_instruction4, control_instruction5, control_instruction6, data_feedback2,
                  control_instruction7, control_instruction8, control_instruction9, data_feedback3,
                  process_instruction1, process_instruction2, process_instruction3,
                  video]
    dic_str_frame = {}
    dic_queue_result = {}  # 由数据流名字找到对应的queue
    # 数据流的时延队列生成
    for frame in frame_pool:
        locals()[frame.name + "_queue"] = Queue()
        dic_queue_result[frame.name] = locals()[frame.name + "_queue"]
        dic_has_conflict[frame.name] = []
        dic_valid[frame.name] = []
        dic_str_frame[frame.name] = frame

    # 交换机输入队列
    switch1_in = {}
    # 流表: 记录与switch相连的设备的queue
    switch1_out = {}

    # 数据集用字典对应
    dic_message = {"立式加工中心": [sensor_displayment1, sensor_acceleration1, sensor_temperature1, sensor_pressure1,
                                    sensor_electricity1, sensor_alarm1],
                   "五轴精密加工中心": [sensor_displayment2, sensor_acceleration2, sensor_temperature2,
                                        sensor_pressure2, sensor_electricity2, sensor_alarm2],
                   "华数机器人": [sensor_displayment3, sensor_acceleration3, sensor_temperature3, sensor_pressure3,
                                  sensor_electricity3, sensor_alarm3],
                   "数控系统1": [control_instruction1, control_instruction2, control_instruction3, data_feedback1],
                   "数控系统2": [control_instruction4, control_instruction5, control_instruction6, data_feedback2],
                   "数控系统3": [control_instruction7, control_instruction8, control_instruction9, data_feedback3],
                   "操作台": [process_instruction1, process_instruction2, process_instruction3],
                   "录像机": [video]}

    # object出入口带宽的字典
    dic_bw = {"立式加工中心": {"in": 0.1, "out": 0.1},
              "五轴精密加工中心": {"in": 0.1, "out": 0.1},
              "华数机器人": {"in": 0.1, "out": 0.1},
              "数控系统1": {"in": 0.1, "out": 0.1},
              "数控系统2": {"in": 0.1, "out": 0.1},
              "数控系统3": {"in": 0.1, "out": 0.1},
              "操作台": {"in": 0.1, "out": 0.1},
              "录像机": {"in": 0.1, "out": 1}}

    object_pool = []

    # 自动循环生成Object的队列与Object对象,并将其输入队列加入switch1_out字典
    for object_name in dic_message.keys():  # 把键值当成object_pool了
        # 每个设备对象对应的queue，后边入switch_out字典
        # currentObject_Q_in = locals()[object_name + "_in"] = Queue()
        currentObject_Q_in = locals()["switch1_" + object_name] = Queue()
        currentObject_Q_out = locals()[object_name + "_switch1"] = Queue()
        # 生成每个object对象, 示例： machine1 = Object("machine1", lst_machine1_message, {"in": 0.1, "out": 0.1}, machine1_in,switch1_in)
        currentObject = locals()[object_name] = Object(object_name, dic_message[object_name], dic_bw[object_name],
                                                       currentObject_Q_in, currentObject_Q_out, dic_vnf_q,dic_queue_result,end_q)  # 生成Object对象
        # 将Object对象 入池
        object_pool.append(currentObject)
        # switch1_out示例：switch1_out = {"machine1": machine1_in, "controller1": controler_in, "machine2": machine2_in......}
        switch1_out[object_name] = currentObject_Q_in
        switch1_in[object_name] = currentObject_Q_out

    # 生成server对象和由vnf查找server队列的字典
    dic_server = {"server1": [se1, se2, se3, se4, se5, se6, se7, se8, se9, se10],
                  "server2": [se3, se4, se5, se8, se9, se10, se13, se14, se15, se16, se17, se18],
                  "server3": [se11, se12, se13, se14, se15, se16, se17, se18],
                  "server4": [se1, se2, se6, se7, se11, se12],
                  'server5': [se1, se2, se3, se4, se5, se6, se7, se8, se9, se10],
                  "server6": [se3, se4, se5, se8, se9, se10, se13, se14, se15, se16, se17, se18],
                  "server7": [se11, se12, se13, se14, se15, se16, se17, se18],
                  "server8": [se1, se2, se6, se7, se11, se12]}
    dic_server_bw = {"server1": {"in": 0.1, "out": 0.1}, "server2": {"in": 0.1, "out": 0.1},
                     "server3": {"in": 0.1, "out": 0.1}, "server4": {"in": 0.1, "out": 0.1},
                     "server5": {"in": 0.1, "out": 0.1}, "server6": {"in": 0.1, "out": 0.1},
                     "server7": {"in": 0.1, "out": 0.1}, "server8": {"in": 0.1, "out": 0.1}}

    server_pool = []
    # 根据字典循环生成server_in队列，根据server和vnf对应关系生成dir_server_q二维字典，以及dir_vnf_q二维字典，二维字典装的是queue类型数据，并将其输入队列加入switch1_out字典
    for serverName in dic_server.keys():
        # currentServer_Q_in = locals()[serverName + "_in"] = Queue()  # 生成server_in队列
        currentServer_Q_in = locals()["switch1_" + serverName] = Queue()  # 生成server_in队列
        currentServer_Q_out = locals()[serverName + "_switch1"] = Queue()
        dic_currentServer_se_queue = locals()[
            "dic_" + serverName] = {}  # 生成dic_server1字典，对于每个server，生成一个字典，key是vnf，value是queue
        for vnf in dic_server[serverName]:  # 循环生成dir_server字典,同时生成dir_vnf_q字典
            # 对每一个服务器上的VNF都生成一个queue
            currentServerVNFQueue = locals()[serverName + "-" + vnf.name] = Queue()
            # 生成类似这样：dic_server1 = {se1: q1_1, se2: q1_2, se3: q1_3, se8: q1_8}
            locals()["dic_" + serverName][vnf] = currentServerVNFQueue  # 把 queue放到 dic_server1，dic_server2
            # 生成由 se 查找 server的字典  示例：dir_vnf_q[se1] = {"server1": q1_1}
            dic_vnf_q[vnf.name][serverName] = currentServerVNFQueue

        # 生成server对象，最后样子 server1 = Server("server1", {"in": 0.1, "out": 0.1}, server1_in, switch1_in, dic_server1)
        currentServer = locals()[serverName] = Server(serverName, dic_server_bw[serverName], currentServer_Q_in,
                                                      currentServer_Q_out, dic_currentServer_se_queue,end_q)
        # 将所有server对象加入server_pool
        server_pool.append(currentServer)
        # 最后可能样子： switch1_out = {"machine1": machine1_in, "controller1": controler_in, "machine2": machine2_in......}
        switch1_out[serverName] = currentServer_Q_in  # 将server_in队列加入switch1_out字典
        switch1_in[serverName] = currentServer_Q_out  # 将server_in队列加入switch1_out字典

    # 各种交换机的集合
    switch_pool = []
    switch1 = Switch("switch1", {"in": 1, "out": 1}, {"l_phy1": 0.01, "l_phy2": 0.01}, switch1_in, switch1_out,end_q)
    switch_pool.append(switch1)

    # 遍历vnf_cluster与object_pool,
    # 生成与vnf_cluster对应的task放入task_pool
    # 各种任务定义，为了省事，直接将VNF的name和speed复制
    task_pool = []
    for i in range(len(vnf_cluster)):
        lis_vnf = vnf_cluster[i].copy()
        for k in range(len(object_pool)):
            obj = object_pool[k]
            task_cluster = []
            for j in range(len(lis_vnf)):
                name = lis_vnf[j].name  # se的两个属性是name与speed
                delay = lis_vnf[j].speed
                le_C = lis_vnf[j].Le
                compute = 0
                if "加密" in name:
                    sequence = 0.1
                    sor = 0
                elif "解密" in name:
                    sequence = 0.9
                    sor = 0
                elif "数字签名" in name:
                    sequence = 0.2
                    sor = 1
                elif "认证" in name:
                    sequence = 0.8
                    sor = 1
                elif "过滤" in name:
                    sequence = 0.5
                    sor = 1
                else:
                    sequence = 0.5
                    sor = 1
                task_cluster.append(Task(name, obj, le_C, delay, compute, sequence, sor))  # wp: 这里的delay与se的speed相等
            # wp:含所有的机器与vnf组合的所有可能
            task_pool.append(task_cluster.copy())  # 是否要copy，要回头看一下  wp:这个不需要copy，因为每次都是不同的task_cluster
    simulate(switch_pool,server_pool,object_pool)  # 仿真模拟，这里是开启
    '''下一阶段'''
    #将p中所有元素取整
    p=np.array(p)
    p=p.astype(int)
    ind=0
    dic_task={}
    dic_task_str={}
    global dic_frame_policy_task_candidate
    dic_s={}#记录安全指标
    for frame_name in dic_frame_policy_task_candidate.keys():
        dic_s[frame_name]=[]
        task_arrange = []
        dic_task_str[frame_name] = set()  # 将set初始化
        dic_task_str[frame_name].clear()
        for policy in dic_frame_policy_task_candidate[frame_name].keys():
            le_t=policy.Le_original
            le_c=0
            for task in dic_frame_policy_task_candidate[frame_name][policy][p[ind]]:#基因点的值
                task_arrange.append(task)
                dic_task_str[frame_name].add(task.name)
                le_c=task.Le_C
            s=le_c/le_t
            dic_s[frame_name].append(s)
            ind+=1
        task_arrange.sort(key=lambda x: x.Sequence)
        dic_task[frame_name]=task_arrange.copy()
    le=0x7fffffff
    for frame_name in dic_s.keys():
        avg=0
        for s in dic_s[frame_name]:
            #print(s)
            avg+=s
        avg=avg/len(dic_s[frame_name])
        if(avg<le):
            le=avg
    for fr in frame_pool:#策略分配给数据流
        fr.lis_SFC=[]
        if fr.name in dic_task.keys():
            for task in dic_task[fr.name]:
                fr.lis_SFC.append(dic_str_vnf[task.name])
    dic_time_avg={}
    monitor = Monitor(dic_queue_result, dic_task_str, time_interval, 0.05,dic_time_avg,frame_pool)
    monitor.start()
    monitor.join()
    end_q.put("end")
    #清空所有交换机、容器、设备中的队列
    #取出dic_time_avg中value的最大值
    max_time=max(dic_time_avg.values())
    #print(le)
    #print(max_time)
    fitness=max_time*w_t+1/le*w_s
    print(fitness)
    return fitness
def queue_clear():
    for switch in switch_pool:
        for i in range(8):
            while not switch.list_temp_q[i].empty():
                switch.list_temp_q[i].get()
    for server in server_pool:
        while not server.queue_wait.empty():
            server.queue_wait.get()
        for vnf in server.dic_vnf_queue.keys():
            while not server.dic_vnf_queue[vnf].empty():
                server.dic_vnf_queue[vnf].get()
    for obj in object_pool:
        while not obj.queue_wait.empty():
            obj.queue_wait.get()
    for queue in switch1_in.values():
        while not queue.empty():
            queue.get()
    for queue in switch1_out.values():
        while not queue.empty():
            queue.get()
def policy_analyze(none_conflict,frame_pool):
    analyze_loop=0
    dic_task = {}
    dic_task_str = {}
    #构建候选集
    global dic_frame_policy_task_candidate
    dic_frame_policy_task_candidate={}
    dim=0
    ub=[]#记录每个数据流的每个策略的上界
    for frame in frame_pool:
        new_dic={}
        for policy in none_conflict:
            if policy.Tasks == []:
                continue
            new_dic[policy] = []
            if policy.Ob == frame.sender:
                count=-1
                for tasks in policy.Tasks:
                    if tasks[0].sor==0:
                        count+=1
                        new_dic[policy].append(tasks)
                if count>-1:
                    dim+=1
                    ub.append(count)
            if policy.Ob == frame.receiver:
                count=-1
                for tasks in policy.Tasks:
                    if tasks[0].sor==1:
                        count+=1
                        new_dic[policy].append(tasks)
                if count>-1:
                    dim+=1
                    ub.append(count)
            if new_dic[policy]==[]:
                new_dic.pop(policy)
        dic_frame_policy_task_candidate[frame.name]=new_dic.copy()
    #创建lb，一个dim维的0向量
    lb=np.zeros(dim)#后续可以优化，这些是定值，可以作为全局变量
    set_run_mode(target_function,'multithreading')#很关键，去掉这一行就是单线程
    #将dic_frame_policy_task_candidate存入dataFrame结构中
    #func是目标函数，n_dim是基因点的个数，size_pop是种群的个数，max_iter是迭代次数，prob_mut是变异概率，lb是基因点的下界，ub是基因点的上界，precision是精度
    pso=PSO(func=target_function,n_dim=dim,pop=24,max_iter=15,lb=lb,ub=ub)
    best_x,best_y=pso.run()
    dic_task_str={}
    ind=0
    ft=open("txt_folder/ft.txt","a")
    for frame in dic_frame_policy_task_candidate.keys():
        dic_task_str[frame] = set()  # 将set初始化
        dic_task_str[frame].clear()
        ft.write(frame+"----------------------------------------\n")
        for policy in dic_frame_policy_task_candidate[frame].keys():
            ft.write(policy.Name+"-----:\n")
            index=best_x[ind].astype(int)
            for task in dic_frame_policy_task_candidate[frame][policy][index]:  # 基因点的值
                dic_task_str[frame].add(task.name)
                ft.write(task.name+"\n")
            ind += 1
    ft.close()
dic_frame_policy_task_candidate = {}#形式为{frame:{policy:[task1,task2,task3],policy:[task1,task2,task3]},frame:{policy:[task1,task2,task3],policy:[task1,task2,task3]}}
dic_simple_candidate = {}#形式为{frame-policy:[task1,task2,task3],frame-policy:[task1,task2,task3]}
dic_has_conflict = {}
dic_valid = {}
policy_analyze_block_event = Event() #阻塞策略解析循环
monitor_block_event= Event()         #阻塞传值循环
monitor_block_event.set()
end_loop_event=Event()#结束循环
time_scale=10
time_plus=time_scale/1000
time_interval=1800          # monitor线程开始工作前的的等待运行时间
time_thread_life=time_interval*time_plus*1.2  # thread 队列 阻塞的最长时间
loop_lock=Lock()
loop=-1
w_t=0.8
w_s=0.2
if __name__ == '__main__':
    se1 = VNF("AES加密", 500,1)
    se2 = VNF("DES加密", 60,2)
    se3 = VNF("RSA-1024加密", 5,3)
    se4 = VNF("RSA-2048加密", 1,4)
    se5 = VNF("RSA-4096加密", 0.2,4)
    se6 = VNF("AES解密", 500,1)
    se7 = VNF("DES解密", 60,1)
    se8 = VNF("RSA-1024解密", 1,3)
    se9 = VNF("RSA-2048解密", 0.2,4)
    se10 = VNF("RSA-4096解密", 0.05,4)
    se11 = VNF("流量过滤1", 1000,1)
    se12 = VNF("流量过滤2", 500,3)
    se13 = VNF("RSA-1024数字签名", 1,2)
    se14 = VNF("RSA-2048数字签名", 0.2,3)
    se15 = VNF("RSA-4096数字签名", 0.05,4)
    se16 = VNF("RSA-1024认证", 5,2)
    se17 = VNF("RSA-2048认证", 1,3)
    se18 = VNF("RSA-4096认证", 0.2,4)

    vnf_pool = [se1, se2, se3, se4, se5, se6, se7, se8, se9, se10, se11, se12, se13, se14, se15, se16, se17, se18]
    vnf_cluster=[[se1,se6],[se2,se7],[se3,se8],[se4,se9],[se5,se10],[se11,],[se12,],[se13,se16],[se14,se17],[se15,se18]]
    # dic_str_vnf= {"AES加密": se1, "DES加密": se2, "RSA-1024加密": se3, "RSA-2048加密": se4, "RSA-4096加密": se5, "AES解密": se6,
    #                 "DES解密": se7, "RSA-1024解密": se8, "RSA-2048解密": se9, "RSA-4096解密": se10, "流量过滤1": se11,
    #                 "流量过滤2": se12, "RSA-1024数字签名": se13, "RSA-2048数字签名": se14, "RSA-4096数字签名": se15, "RSA-1024认证": se16,
    #                 "RSA-2048认证": se17, "RSA-4096认证": se18}

    dic_vnf_q = {}  # 是一个二维字典，由vnf，找到服务器上的queue {se1:{server1:queue,server2:queue},......}
    dic_str_vnf={}  # 由 se名字反查se
    for vnf in vnf_pool:
        dic_vnf_q[vnf.name] = {}
        dic_str_vnf[vnf.name]=vnf

    # 立式加工中心的数据流
    sensor_displayment1 = Frame("sensor_displayment1", "立式加工中心", "数控系统1", 7, 50, 5, [],5)  # size的单位是bit
    sensor_acceleration1 = Frame("sensor_acceleration1", "立式加工中心", "数控系统1", 6, 50, 10, [],20)  # size的单位是bit
    sensor_temperature1 = Frame("sensor_temperature1", "立式加工中心", "数控系统1", 5, 50, 100, [],500)  # size的单位是bit
    sensor_pressure1 = Frame("sensor_pressure1", "立式加工中心", "数控系统1", 5, 50, 100, [],500)  # size的单位是bit
    sensor_electricity1 = Frame("sensor_electricity1", "立式加工中心", "数控系统1", 5, 50, 100, [],200)  # size的单位是bit
    sensor_alarm1 = Frame("sensor_alarm1", "立式加工中心", "数控系统1", 7, 500, 10000, [], 2,{"p": 0.0001, "amount": 1, "interval": 100})  # size的单位是bit

    # 五轴精密加工中心的数据流
    sensor_displayment2 = Frame("sensor_displayment2", "五轴精密加工中心", "数控系统2", 7, 50, 5, [],
                                5)  # size的单位是bit
    sensor_acceleration2 = Frame("sensor_acceleration2", "五轴精密加工中心", "数控系统2", 6, 50, 10, [],
                                 20)  # size的单位是bit
    sensor_temperature2 = Frame("sensor_temperature2", "五轴精密加工中心", "数控系统2", 5, 50, 100, [],
                                500)  # size的单位是bit
    sensor_pressure2 = Frame("sensor_pressure2", "五轴精密加工中心", "数控系统2", 5, 50, 100, [],
                             500)  # size的单位是bit
    sensor_electricity2 = Frame("sensor_electricity2", "五轴精密加工中心", "数控系统2", 5, 50, 100, [],
                                200)  # size的单位是bit
    sensor_alarm2 = Frame("sensor_alarm2", "五轴精密加工中心", "数控系统2", 7, 500, 10000, [], 2,
                          {"p": 0.0001, "amount": 1, "interval": 100})  # size的单位是bit

    # 华数机器人的数据流
    sensor_displayment3 = Frame("sensor_displayment3", "华数机器人", "数控系统3", 7, 50, 5, [],
                                5)  # size的单位是bit
    sensor_acceleration3 = Frame("sensor_acceleration3", "华数机器人", "数控系统3", 6, 50, 10, [],
                                 20)  # size的单位是bit
    sensor_temperature3 = Frame("sensor_temperature3", "华数机器人", "数控系统3", 5, 50, 100, [],
                                500)  # size的单位是bit
    sensor_pressure3 = Frame("sensor_pressure3", "华数机器人", "数控系统3", 5, 50, 100, [], 500)  # size的单位是bit
    sensor_electricity3 = Frame("sensor_electricity3", "华数机器人", "数控系统3", 5, 50, 100, [],
                                200)  # size的单位是bit
    sensor_alarm3 = Frame("sensor_alarm3", "华数机器人", "数控系统3", 7, 500, 10000, [], 2,
                          {"p": 0.0001, "amount": 1, "interval": 100})  # size的单位是bit

    # 数控系统1的数据流
    control_instruction1 = Frame("control_instruction1", "数控系统1", "立式加工中心", 7, 50, 10, [],
                                 5)  # size的单位是bit
    control_instruction2 = Frame("control_instruction2", "数控系统1", "立式加工中心", 6, 50, 20, [],
                                 5)  # size的单位是bit
    control_instruction3 = Frame("control_instruction3", "数控系统1", "立式加工中心", 6, 50, 20, [],
                                 10)  # size的单位是bit
    data_feedback1 = Frame("data_feedback1", "数控系统1", "操作台", 3, 1200, 2000, [],
                           1000)  # size的单位是bit

    # 数控系统2的数据流
    control_instruction4 = Frame("control_instruction4", "数控系统2", "五轴精密加工中心", 7, 50, 10, [],
                                 5)  # size的单位是bit
    control_instruction5 = Frame("control_instruction5", "数控系统2", "五轴精密加工中心", 6, 50, 20, [],
                                 5)  # size的单位是bit
    control_instruction6 = Frame("control_instruction6", "数控系统2", "五轴精密加工中心", 6, 50, 20, [],
                                 10)  # size的单位是bit
    data_feedback2 = Frame("data_feedback2", "数控系统2", "操作台", 3, 1200, 2000, [],
                           1000)  # size的单位是bit

    # 数控系统3的数据流
    control_instruction7 = Frame("control_instruction7", "数控系统3", "华数机器人", 7, 50, 10, [],
                                 5)  # size的单位是bit
    control_instruction8 = Frame("control_instruction8", "数控系统3", "华数机器人", 6, 50, 20, [],
                                 5)  # size的单位是bit
    control_instruction9 = Frame("control_instruction9", "数控系统3", "华数机器人", 6, 50, 20, [],
                                 10)  # size的单位是bit
    data_feedback3 = Frame("data_feedback3", "数控系统3", "操作台", 3, 1200, 2000, [],
                           1000)  # size的单位是bit

    # 操作台的数据流
    process_instruction1 = Frame("process_instruction1", "操作台", "数控系统1", 2, 1000, 10000, [],
                                 1000)  # size的单位是bit
    process_instruction2 = Frame("process_instruction2", "操作台", "数控系统2", 2, 1000, 10000, [],
                                 1000)  # size的单位是bit
    process_instruction3 = Frame("process_instruction3", "操作台", "数控系统3", 2, 1000, 10000, [],
                                 1000)  # size的单位是bit

    # 录像机
    video = Frame("video", "录像机", "操作台", 4, 1518, 100, [], 1000,
                  {"p": 1, "amount": 200, "interval": 100})

    #所有数据流集合
    frame_pool = [sensor_displayment1, sensor_acceleration1, sensor_temperature1, sensor_pressure1,
                sensor_electricity1, sensor_alarm1,
                sensor_displayment2, sensor_acceleration2, sensor_temperature2, sensor_pressure2,
                sensor_electricity2, sensor_alarm2,
                sensor_displayment3, sensor_acceleration3, sensor_temperature3, sensor_pressure3,
                sensor_electricity3, sensor_alarm3,
                control_instruction1, control_instruction2, control_instruction3, data_feedback1,
                control_instruction4, control_instruction5, control_instruction6, data_feedback2,
                control_instruction7, control_instruction8, control_instruction9, data_feedback3,
                process_instruction1, process_instruction2, process_instruction3,
                video]
    dic_str_frame={}
    #数据流的时延队列生成
    for frame in frame_pool:
        locals()[frame.name + "_queue"] = Queue()
        dic_has_conflict[frame.name] = []
        dic_valid[frame.name] = []
        dic_str_frame[frame.name]=frame

    # 交换机输入队列
    switch1_in = {}
    # 流表: 记录与switch相连的设备的queue
    switch1_out = {}

    # 数据集用字典对应
    dic_message = {"立式加工中心": [sensor_displayment1, sensor_acceleration1, sensor_temperature1, sensor_pressure1,
                                    sensor_electricity1, sensor_alarm1],
                   "五轴精密加工中心": [sensor_displayment2, sensor_acceleration2, sensor_temperature2,
                                        sensor_pressure2, sensor_electricity2, sensor_alarm2],
                   "华数机器人": [sensor_displayment3, sensor_acceleration3, sensor_temperature3, sensor_pressure3,
                                  sensor_electricity3, sensor_alarm3],
                   "数控系统1": [control_instruction1, control_instruction2, control_instruction3, data_feedback1],
                   "数控系统2": [control_instruction4, control_instruction5, control_instruction6, data_feedback2],
                   "数控系统3": [control_instruction7, control_instruction8, control_instruction9, data_feedback3],
                   "操作台": [process_instruction1, process_instruction2, process_instruction3],
                   "录像机": [video]}

    # object出入口带宽的字典
    dic_bw = {"立式加工中心": {"in": 0.1, "out": 0.1},
              "五轴精密加工中心": {"in": 0.1, "out": 0.1},
              "华数机器人": {"in": 0.1, "out": 0.1},
              "数控系统1": {"in": 0.1, "out": 0.1},
              "数控系统2": {"in": 0.1, "out": 0.1},
              "数控系统3": {"in": 0.1, "out": 0.1},
              "操作台": {"in": 0.1, "out": 0.1},
              "录像机": {"in": 0.1, "out": 1}}

    object_pool = []

    # 自动循环生成Object的队列与Object对象,并将其输入队列加入switch1_out字典
    for object_name in dic_message.keys():  # 把键值当成object_pool了
        # 每个设备对象对应的queue，后边入switch_out字典
        # currentObject_Q_in = locals()[object_name + "_in"] = Queue()
        currentObject_Q_in = locals()["switch1_" + object_name] = Queue()
        currentObject_Q_out = locals()[object_name + "_switch1"] = Queue()
        # 生成每个object对象, 示例： machine1 = Object("machine1", lst_machine1_message, {"in": 0.1, "out": 0.1}, machine1_in,switch1_in)
        currentObject = locals()[object_name] = Object(object_name, dic_message[object_name], dic_bw[object_name],
                                                       currentObject_Q_in, currentObject_Q_out, {},dic_vnf_q)  # 生成Object对象
        # 将Object对象 入池
        object_pool.append(currentObject)
        # switch1_out示例：switch1_out = {"machine1": machine1_in, "controller1": controler_in, "machine2": machine2_in......}
        switch1_out[object_name] = currentObject_Q_in
        switch1_in[object_name] = currentObject_Q_out

    # 生成server对象和由vnf查找server队列的字典
    dic_server = {"server1": [se1, se2,se3,se4,se5, se6,se7,se8,se9,se10], "server2": [se3,se4,se5,se8,se9,se10,se13,se14,se15,se16,se17,se18],
                  "server3": [se11,se12,se13,se14,se15,se16,se17,se18],
                  "server4": [se1,se2,se6,se7,se11,se12],'server5':[se1, se2,se3,se4,se5, se6,se7,se8,se9,se10],
                  "server6": [se3,se4,se5,se8,se9,se10,se13,se14,se15,se16,se17,se18],"server7": [se11,se12,se13,se14,se15,se16,se17,se18],
                  "server8": [se1,se2,se6,se7,se11,se12]}
    dic_server_bw = {"server1": {"in": 0.1, "out": 0.1}, "server2": {"in": 0.1, "out": 0.1},
                     "server3": {"in": 0.1, "out": 0.1}, "server4": {"in": 0.1, "out": 0.1},
                     "server5": {"in": 0.1, "out": 0.1}, "server6": {"in": 0.1, "out": 0.1},
                        "server7": {"in": 0.1, "out": 0.1}, "server8": {"in": 0.1, "out": 0.1}}

    server_pool = []
    # 根据字典循环生成server_in队列，根据server和vnf对应关系生成dir_server_q二维字典，以及dir_vnf_q二维字典，二维字典装的是queue类型数据，并将其输入队列加入switch1_out字典
    for serverName in dic_server.keys():
        # currentServer_Q_in = locals()[serverName + "_in"] = Queue()  # 生成server_in队列
        currentServer_Q_in = locals()["switch1_" + serverName] = Queue()  # 生成server_in队列
        currentServer_Q_out = locals()[serverName + "_switch1"] = Queue()
        dic_currentServer_se_queue = locals()[
            "dic_" + serverName] = {}  # 生成dic_server1字典，对于每个server，生成一个字典，key是vnf，value是queue
        for vnf in dic_server[serverName]:  # 循环生成dir_server字典,同时生成dir_vnf_q字典
            # 对每一个服务器上的VNF都生成一个queue
            currentServerVNFQueue = locals()[serverName + "-" + vnf.name] = Queue()
            # 生成类似这样：dic_server1 = {se1: q1_1, se2: q1_2, se3: q1_3, se8: q1_8}
            locals()["dic_" + serverName][vnf] = currentServerVNFQueue  # 把 queue放到 dic_server1，dic_server2
            # 生成由 se 查找 server的字典  示例：dir_vnf_q[se1] = {"server1": q1_1}
            dic_vnf_q[vnf.name][serverName] = currentServerVNFQueue

        # 生成server对象，最后样子 server1 = Server("server1", {"in": 0.1, "out": 0.1}, server1_in, switch1_in, dic_server1)
        currentServer = locals()[serverName] = Server(serverName, dic_server_bw[serverName], currentServer_Q_in,
                                                      currentServer_Q_out, dic_currentServer_se_queue)
        # 将所有server对象加入server_pool
        server_pool.append(currentServer)
        # 最后可能样子： switch1_out = {"machine1": machine1_in, "controller1": controler_in, "machine2": machine2_in......}
        switch1_out[serverName] = currentServer_Q_in  # 将server_in队列加入switch1_out字典
        switch1_in[serverName] = currentServer_Q_out  # 将server_in队列加入switch1_out字典

    # 各种交换机的集合
    switch_pool=[]
    switch1 = Switch("switch1", {"in": 1, "out": 1}, {"l_phy1": 0.01, "l_phy2": 0.01}, switch1_in, switch1_out)
    switch_pool.append(switch1)

    # 遍历vnf_cluster与object_pool,
    # 生成与vnf_cluster对应的task放入task_pool
    # 各种任务定义，为了省事，直接将VNF的name和speed复制
    task_pool = []
    for i in range(len(vnf_cluster)):
        lis_vnf = vnf_cluster[i].copy()
        for k in range(len(object_pool)):
            obj = object_pool[k]
            task_cluster = []
            for j in range(len(lis_vnf)):
                name = lis_vnf[j].name       # se的两个属性是name与speed
                delay = lis_vnf[j].speed
                le_C = lis_vnf[j].Le
                compute = 0
                if "加密" in name:
                    sequence = 0.1
                    sor=0
                elif "解密" in name:
                    sequence = 0.9
                    sor=0
                elif "数字签名" in name:
                    sequence = 0.2
                    sor=1
                elif "认证" in name:
                    sequence = 0.8
                    sor=1
                elif "过滤" in name:
                    sequence = 0.5
                    sor=1
                else:
                    sequence = 0.5
                    sor=1
                task_cluster.append(Task(name, obj, le_C, delay, compute, sequence, sor)) #wp: 这里的delay与se的speed相等
            # wp:含所有的机器与vnf组合的所有可能
            task_pool.append(task_cluster.copy())  #是否要copy，要回头看一下  wp:这个不需要copy，因为每次都是不同的task_cluster

    # wp: 根据Policy中的arrange, 生成两个policy pool：se_pool sa_pool
    se_pool = []
    sa_pool = []
    for object_name in dic_message.keys():
        Policy_Example.get_Policy(object_name,se_pool,sa_pool,task_pool)     # wp: 这个函数写得有问题，输入与输出分开

    # 冲突识别，判断是否有冲突，返回冲突集合lis_cof
    lis_conf = conflict_indentify(se_pool,sa_pool)
    # 冲突消解，返回无冲突策略集合
    none_conflict = conflict_elimination(lis_conf,se_pool,sa_pool)
    fp=open("txt_folder/none_conflict.txt","a")
    #print("输出none_conflict表")
    fp.write("输出none_conflict表\n")
    for policy in none_conflict:
        #print("  policy name: %s" % policy.Name)
        #print("  policy.ob: %s" % policy.Ob)
        fp.write("  policy name: %s\n" % policy.Name)
        fp.write("  policy.ob: %s\n" % policy.Ob)
    #print("++++++++++++++ end\n")
    fp.write("++++++++++++++ end\n")
    fp.close()

    # 以下填写每个frame的se清单：      ############清单的个数如何保证？？？？  如果没冲突，但策略会被去掉么？
    lis_vnf_name = []
    for vnf in vnf_pool:
        lis_vnf_name.append(vnf.name)

    #policy_analyze(none_conflict,frame_pool)  # 策略分析
    Tread1= threading.Thread(target=policy_analyze, args=(none_conflict,frame_pool))#策略解析闭环
    Tread1.daemon = True
    Tread1.start()
    Tread1.join()


####总体思路：
## 所有的se对象（VNF对象）放pool中  (自动生成对应的queue)
## 所有的frame对象 （其中的SFC表放有se对象）

## 所有object的带宽表
## 所有object要产生的frame的对应表
## -->所有的object对象放pool中 (自动生成对应的queue)

## server与se对象的对应表  （server.name为键）

## 所有server的带宽表
# --> 所有的server对象放pool中 （自动生成对应的queue）
# --> se查找server对象的表 （用se.name作键）

## switch对象单独定义，switch_in单独定义

#学会了setDeamon()函数的用法
#学会了join()的用法
"""
python字典的有关记录：
python字典可用对象作键：
1, 对象默认用id算hash键值
2, 字典中比较键值对时：
   先比较hash键值， 后比较eq  (如果两对象地址相同，则不比较eq)
"""

"""
pstree -aup

top下按1，显示cpu0  cpu1  cpu2 cup3
"""
