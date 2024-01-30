import pandas as pd

#任务类
class Task:

    def __init__(self, name:str, Ob, Le_C, Delay, Compute, Sequence,sor=0):
        """
        :param name:
        :param Ob:          任务作用对象
        :param Le_C:        任务安全等级
        :param Delay:       任务时延
        :param Compute:     任务计算资源消耗（暂时没用）
        :param Sequence:    任务执行顺序指标，0和1之间，排序时用
        :param sor:         表示任务是发送端还是接收端的任务，0表示发送端，1表示接收端
        """
        self.name: str = name            #任务名
        self.Ob = Ob                #任务作用对象
        self.Le_C = Le_C            #任务安全等级
        self.Delay = Delay          #任务时延
        self.Compute = Compute      #任务计算资源消耗（暂时没用）
        self.Sequence = Sequence    #任务执行顺序指标，0和1之间，排序时用
        self.sor = sor              #表示任务是发送端还是接收端的任务，0表示发送端，1表示接收端

#策略类
class Policy:
    def __init__(self,Name:str,Tp,Ob,Influence,Le_T,Table,Tasks,Le_original=0):
        """
        :param Name: 策略名
        :param Tp: 策略类型，信息安全任务or功能安全任务
        :param Ob: 策略作用对象
        :param Influence: 策略影响指标['Ob', 'SIL', 'IAC', 'UC', 'SI', 'DC', 'RDF', 'TRE', 'RA']
        :param Le_T: 策略安全等级
        :param Table: 策略对系统中其它组件的影响，Dataframe类型
        :param Tasks: 策略的任务集
        """
        self.Name:str = Name            #策略名
        self.Tp = Tp                #策略类型，信息安全任务or功能安全任务
        self.Ob = Ob                #策略作用对象
        self.Influence = Influence  #策略影响指标['Ob', 'SIL', 'IAC', 'UC', 'SI', 'DC', 'RDF', 'TRE', 'RA']
        self.Le_T = Le_T            #策略安全等级
        self.Table = Table          #策略对系统中其它组件的影响，Dataframe类型
        self.Tasks = Tasks          #策略的任务集
        self.Le_original = Le_original        #保持原来的le_T




