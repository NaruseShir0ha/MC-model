reference_weigh = {'IAC': 0.091, 'UC': 0.039, 'SI': 0.017, 'DC': 0.234, 'RDF': 0.091, 'TRE': 0.017, 'RA': 0.139,
                   'requirement_rate': 0.234, 'failure_rate': 0.139}
weigh_key = list(reference_weigh.keys())


def conflict_indentify(se_pool, sa_pool):
    lis_conf = []
    for se in se_pool:
        table1 = se.Table
        for sa in sa_pool:
            table2 = sa.Table
            Obj_num = len(table1)
            # 遍历table(DataFrame类型)的行
            for i in range(0, Obj_num):
                for j in range(1, len(weigh_key)):
                    if table1.iloc[i, j] * (table2.iloc[i, j]) == -1:
                        dic_conf = {'se': se, 'sa': sa, 'Ob': table1['Ob'][i],
                                    'Influence': table1.columns[j]}
                        lis_conf.append(dic_conf)
                        #将dic_conf输出
                        fp=open('txt_folder/conflict.txt','a')
                        fp.write('se:'+se.Name+' sa:'+sa.Name+' Ob:'+table1['Ob'][i]+' Influence:'+table1.columns[j]+'se_level:'+str(se.Le_T)+'sa_level:'+str(sa.Le_T)+'\n')
                        fp.close()
    return lis_conf


def conflict_elimination(lis_conf, se_pool, sa_pool):
    none_conf = sa_pool.copy() + se_pool.copy()
    for conf in lis_conf:
        se = conf['se']
        sa = conf['sa']
        Ob = conf['Ob']
        Influence = conf['Influence']
        # 前提条件是lis_Po中存在Po1和Po2
        if se not in none_conf or sa not in none_conf:
            continue
        if se.Le_T < sa.Le_T:
            none_conf.remove(se)  ########### 逻辑自己优化一下
        elif se.Le_T > sa.Le_T:
            none_conf.remove(sa)
        else:
            if se.Tp == 'Se':
                none_conf.remove(sa)
            else:
                none_conf.remove(se)
    return none_conf
