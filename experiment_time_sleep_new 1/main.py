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

import networkx as nx
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
        self.current_vnf=0
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
            if (frame.priority <= 7 or frame.priority >= 0) and frame.frequency < 1000:  # 创建所有TT流和音视频流的时延占比字典
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

class VNF:  # 待完成，里面有VNF的种类以及处理速度信息，更新加上是发送端的还是接收端的
    def __init__(self, name, speed,Le=1,sor=0):
        super(VNF, self).__init__()
        self.id = id
        self.name = name
        self.speed = speed  # 单位Mbps
        self.Le=Le
        self.sor=sor
    # code for multiprocess
    def __hash__(self):
        return hash(self.name+str(self.speed))

    def __eq__(self,other):
        return self.name==other.name and self.speed==other.speed


# 将TSN数控系统中的每一个组件，如video、controler等，抽象为一个类
class Object(Thread):
    def __init__(self, name, lst_message, bw, queue_in, queue_out, dic_vnf_q,dic_queue_result,lis_link,end_queue=None):
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
        self.lis_link=lis_link

    def run(self):
        if (self.queue_in):  # 指定了读入队列时，才启动读
            Thread(target=self.read, name=self.name + "_read").start()  # 读启动

        for msg in self.lst_message:  # 不同的message类型，启动不同的produce  注意！！，这些不同类型的message是混杂发送的
            Thread(target=self.produce, args=(msg,), name=self.name + "_produce_msg").start()

        if (self.queue_wait):
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
            #print("  %s read: 数据包 %s，传输时间为%s ms" % (self.name, msg.name, transportation_time))
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
            #print("  %s output: 数据包 %s" % (self.name, msg.name,))
            time.sleep(msg.size * 1000 / (self.bw["out"] * pow(1024, 3))*time_plus)
            msg.log.append("%s_%s_out" % (self.name,msg.name))
            msg.log.append(round(time.time()-msg.timestamp,6))
            #print("  %s output: 数据包 %s" % (self.name, msg.name,))
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
                frame_produce.path = self.calc_new_path(msgType)#换成确定路径
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
        #返回图G中self.name到msgType.receiver的最短路径
        msgType.path = nx.shortest_path(G, source=self.name, target=msgType.receiver, weight='weight')
        return msgType.path.copy()


# 一个带时钟的switch：switch启动时，时钟启动
# 在输入端：交换机持续读取输入数据，处理后，按数据敏感，把数据分别放入缓冲区：敏感队列1与非敏感队列2
# 在输出端：交换机按状态时间窗口，分别输出敏感数据与普通数据
# 问题：交换机的缓冲区有无大小限制
class Switch(Thread):
    def __init__(self, name, bw, dic_phy, in_q, out_q,lis_link,end_queue=None):
        super(Switch, self).__init__()
        self.name = name
        self.bw = bw
        self.dic_phy = dic_phy
        self.in_q = in_q  # 输入队列
        self.out_q = out_q  # 输出队列
        self.lis_link=lis_link
        self.status = 0  # 交换机的初始门控状态为0
        self.list_temp_q=[Queue() for i in range(8)]
        self.lst_event=[Event() for i in range(8)]
        self.end_queue=end_queue

    def run(self):
        Thread(target=self.tick).start()  # 时钟启动
        #Thread(target=self.read).start()  # 读启动
        for queue_in in self.in_q.keys():
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
            #print("    switch read: 数据包 %s" % (msg.name,))
            time.sleep((msg.size * 1000 / (self.bw["in"] * pow(1024, 3)) + self.dic_phy["l_phy1"])*time_plus)  # 处理一个数据的时延
            # time.sleep(self.l_phy["l_phy1"])  # 读数据的时延
            # msg.path = msg.path + self.name  # 记录路径
            # if (msg.priority == 7 or msg.priority == 6):  ###### 这里王志通错了
            #     self.temp_hi_q.put(msg)  # 敏感数据放入缓冲区
            # else:
            #     self.temp_normal_q.put(msg)
            pri=msg.priority
            msg.current_node += 1
            self.list_temp_q[pri].put(msg)  # 数据放入优先级队列

    def pri(self,priority,stat):
        while self.end_queue.qsize()==0:
            if (self.status == stat):
                try:
                    msg = self.list_temp_q[priority].get(timeout=time_thread_life)  # 如果队列没有数据，线程会阻塞
                except:
                    break
                time.sleep((msg.size * 1000 / (self.bw["out"] * pow(1024, 3)) + self.dic_phy["l_phy2"])*time_plus)  # 缓存输出所需的延时
                next_device = msg.path[msg.current_node+1]  # 修改path列表的指针
                if (next_device in self.out_q.keys()):
                    msg.log.append("%s_%s_out" % (self.name,msg.name))
                    msg.log.append(round(time.time()-msg.timestamp,6))
                    self.lst_event[priority].wait(time_thread_life)
                    #print("    --switch: 输出数据 %s:下一节点%s" % (msg.name,next_device))
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
            #print("current bw_out:")
            #print(self.bw)
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


class Gate(Thread):
    def __init__(self,name,dic_bw,queue_in,queue_out,dic_vnf,lis_link,end_queue=None):
        super(Gate, self).__init__()
        self.name=name
        self.dic_bw=dic_bw
        self.queue_in=queue_in
        self.queue_out=queue_out
        self.dic_vnf=dic_vnf
        self.end_queue=end_queue
        self.lis_link=lis_link
        self.queue_wait=Queue()
    def run(self):
        for in_q in self.queue_in.keys():
            Thread(target=self.read,args=(self.queue_in[in_q],)).start()
        for vnf in self.dic_vnf.keys():
            Thread(target=self.process,args=(vnf,)).start()
        Thread(target=self.output).start()
    def read(self,in_q):
        while self.end_queue.qsize()==0:
            try:
                msg = in_q.get(timeout=time_thread_life)  # 如果没有数据会阻塞
            except:
                break
            msg.log.append("%s_%s_in" % (self.name,msg.name))
            msg.log.append(round(time.time()-msg.timestamp,6))
            msg.current_node += 1
            #print("gate is reading %s" % msg.name)
            time.sleep((msg.size * 1000 / (self.dic_bw["in"] * pow(1024, 3)))*time_plus)
            #print(msg.lis_SFC)
            #print(msg.name+"-------current vnf"+"---------"+str(msg.current_vnf))
            self.dic_vnf[msg.lis_SFC[msg.current_vnf]].put(msg)
    def process(self,vnf):
        while self.end_queue.qsize()==0:
            try:
                msg = self.dic_vnf[vnf].get(timeout=time_thread_life)  # 如果没有数据会阻塞
            except:
                break
            msg.log.append("%s_%s_process" % (self.name,msg.name))
            msg.log.append(round(time.time()-msg.timestamp,6))
            #print("gate is processing %s" % msg.name)
            time.sleep((msg.size * 1000 / (vnf.speed * pow(1024, 2)))*time_plus)
            sor=msg.lis_SFC[msg.current_vnf].sor
            msg.current_vnf+=1
            #print(msg.name+"-------current vnf"+"---------"+str(msg.current_vnf-1)+"---------vnf name"+vnf.name)
            #判断lis_vnf队列目前是否到底
            if msg.current_vnf<len(msg.lis_SFC):
                if sor==msg.lis_SFC[msg.current_vnf].sor:
                    self.dic_vnf[msg.lis_SFC[msg.current_vnf-1]].put(msg)
                else:
                    self.queue_wait.put(msg)
            else:
                self.queue_wait.put(msg)
    def output(self):
        while self.end_queue.qsize()==0:
            try:
                msg = self.queue_wait.get(timeout=time_thread_life)  # 如果没有数据会阻塞
            except:
                break
            msg.log.append("%s_%s_out" % (self.name,msg.name))
            msg.log.append(round(time.time()-msg.timestamp,6))
            time.sleep((msg.size * 1000 / (self.dic_bw["out"] * pow(1024, 3)))*time_plus)
            next_device = msg.path[msg.current_node+1]  # 修改path列表的指针
            self.queue_out[next_device].put(msg)

def simulate(switch_pool, gate_pool, object_pool):
    # 任务启动
    for switch in switch_pool:
        switch.daemon = True
        switch.start()
    for obj in object_pool:
        obj.daemon = True
        obj.start()
    for gate in gate_pool:
        gate.daemon = True
        gate.start()

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
    # 输入
    vnf_data = pd.read_excel("data/" + scene + "/vnf.xlsx")
    link_data = pd.read_excel("data/" + scene + "/link.xlsx")
    frame_data = pd.read_excel("data/" + scene + "/frame.xlsx")
    object_data = pd.read_excel("data/" + scene + "/object.xlsx")
    gate_data = pd.read_excel("data/" + scene + "/gate.xlsx")
    switch_data = pd.read_excel("data/" + scene + "/switch.xlsx")
    # vnf数据处理
    vnf_pool = []
    for i in range(len(vnf_data)):
        vnf_pool.append(VNF(vnf_data.iloc[i, 0], vnf_data.iloc[i, 1], vnf_data.iloc[i, 2], vnf_data.iloc[i, 3]))
    vnf_cluster = []
    for i in range(len(vnf_data)):
        if vnf_data.iloc[i, 4] > len(vnf_cluster):
            vnf_cluster.append([vnf_pool[i]])
        else:
            vnf_cluster[vnf_data.iloc[i, 4] - 1].append(vnf_pool[i])
    # 构造图，点为设备、TSN网关，边为连接关系
    G = nx.Graph()  # 记录图，节点是字符串类型
    dic_vnf_q = {}  # 是一个二维字典，由vnf，找到服务器上的queue {se1:{server1:queue,server2:queue},......}
    dic_str_vnf = {}  # 由 se名字反查se
    for vnf in vnf_pool:
        dic_vnf_q[vnf.name] = {}
        dic_str_vnf[vnf.name] = vnf
    # 连接数据处理
    dic_lis_link = {}
    for i in range(len(link_data)):
        dic_lis_link[link_data.iloc[i, 0]] = link_data.iloc[i, 1].split(",")
    # 数据流数据处理
    frame_pool = []
    dic_str_frame = {}
    dic_message = {}
    dic_queue_result = {}
    for i in range(len(frame_data)):
        if (frame_data.iloc[i, 7] is np.nan):
            frame_pool.append(
                Frame(frame_data.iloc[i, 0], frame_data.iloc[i, 1], frame_data.iloc[i, 2], frame_data.iloc[i, 3],
                      frame_data.iloc[i, 4], frame_data.iloc[i, 5], [], frame_data.iloc[i, 6]))
        else:
            burst = {}
            burst["p"] = float(frame_data.iloc[i, 7].split(":")[0])
            burst["amount"] = int(frame_data.iloc[i, 7].split(":")[1])
            burst["interval"] = float(frame_data.iloc[i, 7].split(":")[2])
            frame_pool.append(
                Frame(frame_data.iloc[i, 0], frame_data.iloc[i, 1], frame_data.iloc[i, 2], frame_data.iloc[i, 3],
                      frame_data.iloc[i, 4], frame_data.iloc[i, 5], [], frame_data.iloc[i, 6], burst))
        if frame_data.iloc[i, 1] not in dic_message.keys():
            dic_message[frame_data.iloc[i, 1]] = [frame_pool[i], ]
        else:
            dic_message[frame_data.iloc[i, 1]].append(frame_pool[i])
    # 数据流的时延队列生成
    for frame in frame_pool:
        locals()[frame.name + "_queue"] = Queue()
        dic_queue_result[frame.name] = locals()[frame.name + "_queue"]
        dic_has_conflict[frame.name] = []
        dic_valid[frame.name] = []
        dic_str_frame[frame.name] = frame


    # object出入口带宽的字典
    dic_bw = {}
    for i in range(len(object_data)):
        dic_bw[object_data.iloc[i, 0]] = {"in": object_data.iloc[i, 1], "out": object_data.iloc[i, 2]}

    dic_object_pool = {}
    # 自动循环生成Object的队列与Object对象,并将其输入队列加入switch1_out字典
    for object_name in dic_message.keys():  # 把键值当成object_pool了
        # 每个设备对象对应的queue，后边入switch_out字典
        # currentObject_Q_in = locals()[object_name + "_in"] = Queue()
        currentObject_Q_in = locals()["gate_" + object_name] = Queue()
        currentObject_Q_out = locals()[object_name + "_gate"] = Queue()
        currentObject_link = dic_lis_link[object_name]  # 当前设备的连接关系
        # 生成每个object对象, 示例： machine1 = Object("machine1", lst_machine1_message, {"in": 0.1, "out": 0.1}, machine1_in,switch1_in)
        currentObject = locals()[object_name] = Object(object_name, dic_message[object_name], dic_bw[object_name],currentObject_Q_in, currentObject_Q_out, dic_vnf_q,dic_queue_result,currentObject_link,end_q)  # 生成Object对象
        G.add_node(object_name)
        # 将Object对象 入池
        dic_object_pool[object_name] = currentObject

    # 生成server对象和由vnf查找server队列的字典
    dic_gate = {}
    for i in range(len(gate_data)):
        dic_gate[gate_data.iloc[i, 0]] = vnf_pool.copy()
    dic_gate_bw = {}
    for i in range(len(gate_data)):
        dic_gate_bw[gate_data.iloc[i, 0]] = {"in": gate_data.iloc[i, 1], "out": gate_data.iloc[i, 2]}

    dic_gate_pool = {}
    # 根据字典循环生成server_in队列，根据server和vnf对应关系生成dir_server_q二维字典，以及dir_vnf_q二维字典，二维字典装的是queue类型数据，并将其输入队列加入switch1_out字典
    for gateName in dic_gate.keys():
        # currentServer_Q_in = locals()[serverName + "_in"] = Queue()  # 生成server_in队列
        currentGate_Q_in = {}
        currentGate_Q_out = {}
        dic_currentGate_se_queue = locals()[
            "dic_" + gateName] = {}  # 生成dic_server1字典，对于每个server，生成一个字典，key是vnf，value是queue
        currentGate_link = dic_lis_link[gateName]
        for vnf in dic_gate[gateName]:  # 循环生成dir_server字典,同时生成dir_vnf_q字典
            # 对每一个服务器上的VNF都生成一个queue
            currentGateVNFQueue = locals()[gateName + "-" + vnf.name] = Queue()
            # 生成类似这样：dic_server1 = {se1: q1_1, se2: q1_2, se3: q1_3, se8: q1_8}
            locals()["dic_" + gateName][vnf] = currentGateVNFQueue  # 把 queue放到 dic_server1，dic_server2
            # 生成由 se 查找 server的字典  示例：dir_vnf_q[se1] = {"server1": q1_1}
            dic_vnf_q[vnf.name][gateName] = currentGateVNFQueue
        # 生成gate对象
        currentGate = locals()[gateName] = Gate(gateName, dic_gate_bw[gateName], currentGate_Q_in, currentGate_Q_out,
                                                dic_currentGate_se_queue, currentGate_link,end_q)
        G.add_node(gateName)
        # 将所有server对象加入server_pool
        dic_gate_pool[gateName] = currentGate
        # 最后可能样子： switch1_out = {"machine1": machine1_in, "controller1": controler_in, "machine2": machine2_in......}

    switch_bw = {}
    for i in range(len(switch_data)):
        switch_bw[switch_data.iloc[i, 0]] = {"in": switch_data.iloc[i, 1], "out": switch_data.iloc[i, 2]}
    switch_phy = {}
    for i in range(len(switch_data)):
        switch_phy[switch_data.iloc[i, 0]] = {"l_phy1": switch_data.iloc[i, 3], "l_phy2": switch_data.iloc[i, 4]}
    dic_switch_pool = {}
    # 各种交换机的集合
    for switchName in switch_data.iloc[:, 0]:
        currentSwitch_Q_in = {}  # 生成server_in队列
        currentSwitch_Q_out = {}
        currentSwitch_link = dic_lis_link[switchName]
        currentSwitch = locals()[switchName] = Switch(switchName, switch_bw[switchName], switch_phy[switchName], currentSwitch_Q_in,
                                                      currentSwitch_Q_out, currentSwitch_link,end_q)
        G.add_node(switchName)
        dic_switch_pool[switchName] = currentSwitch

    for object in dic_object_pool.values():
        for gateName in object.lis_link:
            G.add_edge(object.name, gateName)
            dic_gate_pool[gateName].queue_in[object.name] = object.queue_out
    for switch in dic_switch_pool.values():
        for Name in switch.lis_link:
            if Name in dic_gate_pool.keys():
                G.add_edge(switch.name, Name)
                switch.out_q[Name] = Queue()
                dic_gate_pool[Name].queue_in[switch.name] = switch.out_q[Name]
            elif Name in dic_switch_pool.keys():
                G.add_edge(switch.name, Name)
                switch.out_q[Name] = Queue()
                dic_switch_pool[Name].in_q[switch.name] = switch.out_q[Name]
            else:
                G.add_edge(switch.name, Name)
                switch.in_q[Name] = dic_object_pool[Name].queue_out
    for gate in dic_gate_pool.values():
        for Name in gate.lis_link:
            if Name in dic_switch_pool.keys():
                G.add_edge(gate.name, Name)
                dic_switch_pool[Name].in_q[gate.name] = Queue()
                gate.queue_out[Name] = dic_switch_pool[Name].in_q[gate.name]
            else:
                G.add_edge(gate.name, Name)
                gate.queue_out[Name] = dic_object_pool[Name].queue_in

    #simulate(dic_switch_pool.values(),dic_gate_pool.values(),dic_object_pool.values())  # 仿真模拟，这里是开启
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
    simulate(dic_switch_pool.values(), dic_gate_pool.values(), dic_object_pool.values())  # 仿真模拟，这里是开启
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
    #一排输出fitness和le的数值
    print("fitness:%s" % fitness,end=" ")
    print("le:%s" % le,end=" ")
    print("max_time:%s" % max_time)
    return fitness
def queue_clear():
    for switch in dic_switch_pool.values():
        for i in range(8):
            while not switch.list_temp_q[i].empty():
                switch.list_temp_q[i].get()
    for gate in dic_gate_pool.values():
        while not gate.queue_wait.empty():
            gate.queue_wait.get()
        for vnf in gate.dic_vnf.keys():
            while not gate.dic_vnf[vnf].empty():
                gate.dic_vnf[vnf].get()
    for obj in dic_object_pool.values():
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
    pso=PSO(func=target_function,n_dim=dim,pop=24,max_iter=12,lb=lb,ub=ub)
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
time_scale=100
time_plus=time_scale/1000
time_interval=1800          # monitor线程开始工作前的的等待运行时间
time_thread_life=time_interval*time_plus*1.2  # thread 队列 阻塞的最长时间
loop_lock=Lock()
loop=-1
w_t=0.8
w_s=0.2
scene="scene2"
if __name__ == '__main__':
    #输入
    vnf_data = pd.read_excel("data/"+scene+"/vnf.xlsx")
    link_data = pd.read_excel("data/"+scene+"/link.xlsx")
    frame_data = pd.read_excel("data/"+scene+"/frame.xlsx")
    object_data = pd.read_excel("data/"+scene+"/object.xlsx")
    gate_data = pd.read_excel("data/"+scene+"/gate.xlsx")
    switch_data = pd.read_excel("data/"+scene+"/switch.xlsx")
    #vnf数据处理
    vnf_pool = []
    for i in range(len(vnf_data)):
        vnf_pool.append(VNF(vnf_data.iloc[i,0],vnf_data.iloc[i,1],vnf_data.iloc[i,2],vnf_data.iloc[i,3]))
    vnf_cluster = []
    for i in range(len(vnf_data)):
        if vnf_data.iloc[i,4]>len(vnf_cluster):
            vnf_cluster.append([vnf_pool[i]])
        else:
            vnf_cluster[vnf_data.iloc[i,4]-1].append(vnf_pool[i])
    #构造图，点为设备、TSN网关，边为连接关系
    G=nx.Graph()#记录图，节点是字符串类型
    dic_vnf_q = {}  # 是一个二维字典，由vnf，找到服务器上的queue {se1:{server1:queue,server2:queue},......}
    dic_str_vnf={}  # 由 se名字反查se
    for vnf in vnf_pool:
        dic_vnf_q[vnf.name] = {}
        dic_str_vnf[vnf.name]=vnf
    #连接数据处理
    dic_lis_link={}
    for i in range(len(link_data)):
        dic_lis_link[link_data.iloc[i,0]]=link_data.iloc[i,1].split(",")
    #数据流数据处理
    frame_pool=[]
    dic_str_frame={}
    dic_message={}
    for i in range(len(frame_data)):
        if(frame_data.iloc[i,7] is np.nan):
            frame_pool.append(Frame(frame_data.iloc[i,0],frame_data.iloc[i,1],frame_data.iloc[i,2],frame_data.iloc[i,3],frame_data.iloc[i,4],frame_data.iloc[i,5],[],frame_data.iloc[i,6]))
        else:
            burst={}
            burst["p"] = float(frame_data.iloc[i, 7].split(":")[0])
            burst["amount"] = int(frame_data.iloc[i, 7].split(":")[1])
            burst["interval"] = float(frame_data.iloc[i, 7].split(":")[2])
            frame_pool.append(Frame(frame_data.iloc[i,0],frame_data.iloc[i,1],frame_data.iloc[i,2],frame_data.iloc[i,3],frame_data.iloc[i,4],frame_data.iloc[i,5],[],frame_data.iloc[i,6],burst))
        if frame_data.iloc[i,1] not in dic_message.keys():
            dic_message[frame_data.iloc[i,1]]=[frame_pool[i],]
        else:
            dic_message[frame_data.iloc[i,1]].append(frame_pool[i])
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


    # object出入口带宽的字典
    dic_bw={}
    for i in range(len(object_data)):
        dic_bw[object_data.iloc[i,0]]={"in":object_data.iloc[i,1],"out":object_data.iloc[i,2]}

    dic_object_pool = {}
    # 自动循环生成Object的队列与Object对象,并将其输入队列加入switch1_out字典
    for object_name in dic_message.keys():  # 把键值当成object_pool了
        # 每个设备对象对应的queue，后边入switch_out字典
        # currentObject_Q_in = locals()[object_name + "_in"] = Queue()
        currentObject_Q_in = locals()["gate_" + object_name] = Queue()
        currentObject_Q_out = locals()[object_name + "_gate"] = Queue()
        currentObject_link = dic_lis_link[object_name]  # 当前设备的连接关系
        # 生成每个object对象, 示例： machine1 = Object("machine1", lst_machine1_message, {"in": 0.1, "out": 0.1}, machine1_in,switch1_in)
        currentObject = locals()[object_name] = Object(object_name, dic_message[object_name], dic_bw[object_name],currentObject_Q_in, currentObject_Q_out, {},dic_vnf_q,currentObject_link)  # 生成Object对象
        G.add_node(object_name)
        # 将Object对象 入池
        dic_object_pool[object_name] = currentObject

    # 生成server对象和由vnf查找server队列的字典
    dic_gate={}
    for i in range(len(gate_data)):
        dic_gate[gate_data.iloc[i,0]]=vnf_pool.copy()
    dic_gate_bw={}
    for i in range(len(gate_data)):
        dic_gate_bw[gate_data.iloc[i,0]]={"in":gate_data.iloc[i,1],"out":gate_data.iloc[i,2]}

    dic_gate_pool = {}
    # 根据字典循环生成server_in队列，根据server和vnf对应关系生成dir_server_q二维字典，以及dir_vnf_q二维字典，二维字典装的是queue类型数据，并将其输入队列加入switch1_out字典
    for gateName in dic_gate.keys():
        # currentServer_Q_in = locals()[serverName + "_in"] = Queue()  # 生成server_in队列
        currentGate_Q_in = {}
        currentGate_Q_out = {}
        dic_currentGate_se_queue = locals()["dic_" + gateName] = {}  # 生成dic_server1字典，对于每个server，生成一个字典，key是vnf，value是queue
        currentGate_link=dic_lis_link[gateName]
        for vnf in dic_gate[gateName]:  # 循环生成dir_server字典,同时生成dir_vnf_q字典
            # 对每一个服务器上的VNF都生成一个queue
            currentGateVNFQueue = locals()[gateName + "-" + vnf.name] = Queue()
            # 生成类似这样：dic_server1 = {se1: q1_1, se2: q1_2, se3: q1_3, se8: q1_8}
            locals()["dic_" + gateName][vnf] = currentGateVNFQueue  # 把 queue放到 dic_server1，dic_server2
            # 生成由 se 查找 server的字典  示例：dir_vnf_q[se1] = {"server1": q1_1}
            dic_vnf_q[vnf.name][gateName] = currentGateVNFQueue
        # 生成gate对象
        currentGate=locals()[gateName]=Gate(gateName, dic_gate_bw[gateName], currentGate_Q_in,currentGate_Q_out, dic_currentGate_se_queue,currentGate_link)
        G.add_node(gateName)
        # 将所有server对象加入server_pool
        dic_gate_pool[gateName]=currentGate
        # 最后可能样子： switch1_out = {"machine1": machine1_in, "controller1": controler_in, "machine2": machine2_in......}

    switch_bw={}
    for i in range(len(switch_data)):
        switch_bw[switch_data.iloc[i,0]]={"in":switch_data.iloc[i,1],"out":switch_data.iloc[i,2]}
    switch_phy={}
    for i in range(len(switch_data)):
        switch_phy[switch_data.iloc[i,0]]={"l_phy1":switch_data.iloc[i,3],"l_phy2":switch_data.iloc[i,4]}
    dic_switch_pool = {}
    # 各种交换机的集合
    for switchName in switch_data.iloc[:,0]:
        currentSwitch_Q_in = {}  # 生成server_in队列
        currentSwitch_Q_out = {}
        currentSwitch_link=dic_lis_link[switchName]
        currentSwitch=locals()[switchName]=Switch(switchName, switch_bw[switchName], switch_phy[switchName],currentSwitch_Q_in,currentSwitch_Q_out,currentSwitch_link)
        G.add_node(switchName)
        dic_switch_pool[switchName]=currentSwitch

    for object in dic_object_pool.values():
        for gateName in object.lis_link:
            G.add_edge(object.name,gateName)
            dic_gate_pool[gateName].queue_in[object.name]=object.queue_out
    for switch in dic_switch_pool.values():
        for Name in switch.lis_link:
            if Name in dic_gate_pool.keys():
                G.add_edge(switch.name,Name)
                switch.out_q[Name]=Queue()
                dic_gate_pool[Name].queue_in[switch.name]=switch.out_q[Name]
            elif Name in dic_switch_pool.keys():
                G.add_edge(switch.name,Name)
                switch.out_q[Name]=Queue()
                dic_switch_pool[Name].in_q[switch.name]=switch.out_q[Name]
            else:
                G.add_edge(switch.name,Name)
                switch.in_q[Name]=dic_object_pool[Name].queue_out
    for gate in dic_gate_pool.values():
        for Name in gate.lis_link:
            if Name in dic_switch_pool.keys():
                G.add_edge(gate.name,Name)
                dic_switch_pool[Name].in_q[gate.name]=Queue()
                gate.queue_out[Name]=dic_switch_pool[Name].in_q[gate.name]
            else:
                G.add_edge(gate.name,Name)
                gate.queue_out[Name]=dic_object_pool[Name].queue_in

    # 遍历vnf_cluster与object_pool,
    # 生成与vnf_cluster对应的task放入task_pool
    # 各种任务定义，为了省事，直接将VNF的name和speed复制
    task_pool = []
    for i in range(len(vnf_cluster)):
        lis_vnf = vnf_cluster[i].copy()
        for obj in dic_object_pool.values():
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
        Policy_Example.get_Policy(object_name,se_pool,sa_pool,task_pool,scene)     # wp: 这个函数写得有问题，输入与输出分开

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
