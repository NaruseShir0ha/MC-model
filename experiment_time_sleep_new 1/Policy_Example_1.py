# -*- coding: utf-8 -*-
#不同种类任务提供样板
import copy
import numpy as np
import pandas as pd
from TSN_Class import Policy


#各种机器的策略分配  wp: 下边这些1,3等数字代表什么? 代表安全等级，即重要性
arrange={"立式加工中心":{"加密":1,"认证":1,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
         "五轴精密加工中心":{"加密":1,"认证":1,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
         "华数机器人":{"加密":1,"认证":1,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
         "数控系统1":{"加密":1,"认证":1,"流量过滤":2,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
         "数控系统2":{"加密":1,"认证":1,"流量过滤":2,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
         "数控系统3":{"加密":1,"认证":1,"流量过滤":2,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
         "操作台":{"加密":2,"认证":2,"流量过滤":2},
         "录像机":{"加密":2,"软件过程和设备识别":3,"只和匹配的设备进行数据交互":2}}

dic_policy={}
# lst_objName 例:["立式加工中心","五轴精密加工中心","华数机器人","数控系统1","数控系统2","数控系统3","操作台","录像机"]
lst_objName=[objName for objName in arrange.keys()]
lst_influence=['Ob', 'SIL', 'IAC', 'UC', 'SI', 'DC', 'RDF', 'TRE', 'RA']
# 生成空样表table_temple: 行是各种机器，列是各influence
table_temple=pd.DataFrame(columns=lst_influence, index=lst_objName, data=np.zeros(shape=(len(lst_objName), len(lst_influence))))
table_temple['Ob']=lst_objName

#加密的样板
table1=copy.deepcopy(table_temple)
table1['SIL']=[1,1,1,1,1,1,1,1]
dic_policy["加密"]=Policy('加密','Se','','DC',0,table1,[])

#认证的样板
table2=copy.deepcopy(table_temple)
table2['SIL']=[1,1,1,1,1,1,1,1]
dic_policy["认证"]=Policy('认证','Se','','DC',0,table2,[])

#流量过滤的样板
table3=copy.deepcopy(table_temple)
table3['SIL']=[1,1,1,1,1,1,1,1]
dic_policy["流量过滤"]=Policy('流量过滤','Se','','DC',0,table3,[])
#网络隔离的样板
table4=copy.deepcopy(table_temple)
table4['SIL']=[1,1,1,1,1,1,1,1]
dic_policy["网络隔离"]=Policy('网络隔离','Se','','DC',0,table4,[])
#软件过程和设备识别
table5=copy.deepcopy(table_temple)
table5['SIL']=[-1,-1,-1,-1,-1,-1,-1,-1]
dic_policy["软件过程和设备识别"]=Policy('软件过程和设备识别','Se','','IAC',0,table5,[])
#控制系统的恢复与重建
table6=copy.deepcopy(table_temple)
table6['SIL']=[-1,-1,-1,-1,-1,-1,-1,-1]
dic_policy["控制系统的恢复与重建"]=Policy('控制系统的恢复与重建','Se','','RA',0,table6,[])
#最小功能
table7=copy.deepcopy(table_temple)
table7['SIL']=[-1,-1,-1,-1,-1,-1,-1,-1]
dic_policy["最小功能"]=Policy('最小功能','Se','','RA',0,table7,[])

#只和匹配的设备进行数据交互
table8=copy.deepcopy(table_temple)
table8['IAC']=[-1,-1,-1,-1,-1,-1,-1,-1]
dic_policy["只和匹配的设备进行数据交互"]=Policy('只和匹配的设备进行数据交互','Sa','','requirement_rate',0,table8,[])

#设备失效后，保持在安全状态，不可自动重启恢复
table9=copy.deepcopy(table_temple)
table9['RA']=[-1,-1,-1,-1,-1,-1,-1,-1]
dic_policy["设备失效后，保持在安全状态，不可自动重启恢复"]=Policy('设备失效后，保持在安全状态，不可自动重启恢复','Sa','','requirement_rate',0,table9,[])

#传输冗余链路
table10=copy.deepcopy(table_temple)
table10['RA']=[-1,-1,-1,-1,-1,-1,-1,-1]
dic_policy["传输冗余链路"]=Policy('传输冗余链路','Sa','','requirement_rate',0,table10,[])

# arrange={"立式加工中心":{"加密":1,"认证":1,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
#          "五轴精密加工中心":{"加密":1,"认证":1,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
#          "华数机器人":{"加密":1,"认证":1,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
#          "数控系统1":{"加密":1,"认证":1,"流量过滤":2,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
#          "数控系统2":{"加密":1,"认证":1,"流量过滤":2,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
#          "数控系统3":{"加密":1,"认证":1,"流量过滤":2,"最小功能":1,"软件过程和设备识别":3,"控制系统的恢复与重建":2,"只和匹配的设备进行数据交互":3,"设备失效后，保持在安全状态，不可自动重启恢复":2,"传输冗余链路":3},
#          "操作台":{"加密":2,"认证":2,"流量过滤":2},
#          "录像机":{"加密":2,"软件过程和设备识别":3,"只和匹配的设备进行数据交互":2}}
reference_weigh = {'IAC': 0.091, 'UC': 0.039, 'SI': 0.017, 'DC': 0.234, 'RDF': 0.091, 'TRE': 0.017, 'RA': 0.139,
                   'requirement_rate': 0.234, 'failure_rate': 0.139}
weigh_key = list(reference_weigh.keys())
#对每个组件Obj，将信息安全策略填入Se中，功能安全策略填入Sa中,涉及的安全任务日安如task_pool中    ？？？？？？文字有错
def get_Policy(Obj_Name, Se, Sa, task_pool):
    arrange_item=arrange[Obj_Name]          # 所有和Obj有关联的策略
    #设备的序数
    i=list(arrange.keys()).index(Obj_Name)  # 废话
    j=0
    task_cluster=[]
    # 筛选出obj相关的Task
    for task in task_pool:
        if task[0].Ob.name==Obj_Name:
            task_cluster.append(task)
    for key in arrange_item.keys():
        ii=str(i)
        jj=str(j)
        policy1=locals()[ii+"+"+jj]=copy.deepcopy(dic_policy[key])
        policy1.Ob=Obj_Name                    # wp: 这里把 policy与具体obj关联
        #policy1.Le_T=arr[key]*reference_weigth[policy1.Influence]
        policy1.Le_T = arrange_item[key]        # wp: 例： key是“加密” 或 “认证”等  Le_T是安全等级
        policy1.Le_original=policy1.Le_T
        if policy1.Tp=='Sa':
            policy1.Le_T*=reference_weigh['requirement_rate']
        else:
            policy1.Le_T*=reference_weigh[policy1.Influence]
        for tasks in task_cluster:
            lis_task=[]
            if tasks[0].Le_C<policy1.Le_T:
                continue#如果任务的安全等级小于策略的安全等级，不考虑
            for ta in tasks:
                if key == '加密':
                    if ("加密" in ta.name) or ("解密" in ta.name):
                        lis_task.append(ta)
                if key == '认证':
                    if ("认证" in ta.name) or ('数字签名' in ta.name):
                        lis_task.append(ta)
                if key == '流量过滤':
                    if "过滤" in ta.name:
                        lis_task.append(ta)
            if lis_task:
                policy1.Tasks.append(lis_task.copy())
        if policy1.Tp=='Se':
            # policy1.Table[policy1.Influence][Obj_Name]=1
            policy1.Table.loc[Obj_Name,policy1.Influence]=1
            # print(policy1.Table)
            Se.append(Policy(policy1.Name,policy1.Tp,policy1.Ob,policy1.Influence,policy1.Le_T,policy1.Table,policy1.Tasks,policy1.Le_original))
        else:
            # policy1.Table['SIL'][Obj_Name]=1
            policy1.Table.loc[Obj_Name, 'SIL'] = 1
            Sa.append(Policy(policy1.Name,policy1.Tp,policy1.Ob,policy1.Influence,policy1.Le_T,policy1.Table,policy1.Tasks,policy1.Le_original))
        #将dataframe类型的policy1.Table写入excel中
        fp=open('excel_folder/'+policy1.Name+'_'+policy1.Ob+'.xlsx','wb')
        policy1.Table.to_excel(fp,sheet_name=policy1.Name+'_'+policy1.Ob)
        fp.close()

