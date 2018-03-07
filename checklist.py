#!/usr/local/python27/bin/python2.7
# author:caopeng
# -*- coding: utf8 -*-
from aliyunsdkcore import client
from aliyunsdkrds.request.v20140815 import DescribeResourceUsageRequest,DescribeDBInstancePerformanceRequest,DescribeDBInstanceAttributeRequest,DescribeBackupsRequest,DescribeErrorLogsRequest,DescribeDBInstancesRequest,DescribeBackupPolicyRequest
import json,datetime,time,sys
import exceptions,_strptime
import heapq
import MySQLdb

ID = 'XXXX'
Secret = 'XXXX'
RegionId = 'cn-shenzhen-XXX'
clt = client.AcsClient(ID,Secret,RegionId)

UTC_End = datetime.datetime.today() - datetime.timedelta(hours=8)
UTC_Start = UTC_End - datetime.timedelta(days=1)
StartTime = datetime.datetime.strftime(UTC_Start, '%Y-%m-%dT%H:%MZ')
EndTime = datetime.datetime.strftime(UTC_End, '%Y-%m-%dT%H:%MZ')

###获取rds列表
DBInstanceIdList = []
def GetRdsList():
    RdsRequest = DescribeDBInstancesRequest.DescribeDBInstancesRequest()
    RdsRequest.set_accept_format('json')
    RdsInfo = clt.do_action_with_exception(RdsRequest)
    for RdsInfoJson in (json.loads(RdsInfo))['Items']['DBInstance']:
        DBInstanceIdList.append(RdsInfoJson['DBInstanceId'])
    print DBInstanceIdList
GetRdsList()


### 时间转换(格式为精确到分钟)
def TransferTime(TimeBefore):
    format_time = time.strptime(TimeBefore, "%Y-%m-%d %H:%M")
    y, m, d, H, M = format_time[0:5]
    global TimeEnd
    TimeEnd = datetime.datetime(y, m, d, H, M) + datetime.timedelta(hours=8)
### 时间转换（格式精确到秒）
def TimeTransfer(TimeBefore):
    format_time = time.strptime(TimeBefore, "%Y-%m-%d %H:%M:%S")
    y, m, d, H, M, S = format_time[0:6]
    global  TimeEnd
    TimeEnd = datetime.datetime(y, m, d, H, M, S) + datetime.timedelta(hours=8)

### 实例详情（版本、锁、锁理由、运行状态、实例总空间）
def GetRdsAttribute(DBInstanceId):
    RdsAttribute = DescribeDBInstanceAttributeRequest.DescribeDBInstanceAttributeRequest()
    RdsAttribute.set_accept_format('json')
    RdsAttribute.set_DBInstanceId(DBInstanceId)
    RdsAttributeInfo = clt.do_action_with_exception(RdsAttribute)
    Info = (json.loads(RdsAttributeInfo))
    Version = Info['Items']['DBInstanceAttribute'][0]['Engine'] +   Info['Items']['DBInstanceAttribute'][0]['EngineVersion']
    Lock =  Info['Items']['DBInstanceAttribute'][0]['LockMode']
    Status = Info['Items']['DBInstanceAttribute'][0]['DBInstanceStatus']
    Description = Info['Items']['DBInstanceAttribute'][0]['DBInstanceDescription']
    DBInstanceStorage = Info['Items']['DBInstanceAttribute'][0]['DBInstanceStorage']
    if Info['Items']['DBInstanceAttribute'][0]['LockMode'] != 'Unlock':
        LockReason = Info['Items']['DBInstanceAttribute'][0]['LockReason']
        print Description, '\t', Version, '\t', Lock, '\t', Status + '\t'+ '\tLockReason' + Info['Items']['DBInstanceAttribute'][0]['LockReason']
    else:
        LockReason = 'NULL'
        print Description, '\t', Version, '\t', Lock, '\t', Status + '\tLockReason' + '\tNULL'
    Sql = "update checklist set description='%s',version='%s',status='%s',lock_about='%s',lock_reason='%s',disktotal='%s' where item='%s'and date=curdate()" %(Description,Version,Status,Lock,LockReason,DBInstanceStorage,DBInstanceId)
    DatabaseConnect(Sql)
    print DBInstanceStorage

###备份策略(下次备份时间)
def GetBackupPolicy(DBInstanceId):
    BackupPolicy = DescribeBackupPolicyRequest.DescribeBackupPolicyRequest()
    BackupPolicy.set_accept_format('json')
    BackupPolicy.set_DBInstanceId(DBInstanceId)
    BackupPolicyInfo = clt.do_action_with_exception(BackupPolicy)
    Info = (json.loads(BackupPolicyInfo))
    TimeBefore = Info['PreferredNextBackupTime'] .replace('T',' ').replace('Z','')
    TransferTime(TimeBefore)
    Sql = "update checklist set nextbackuptime='%s' where item='%s'and date=curdate()" % (TimeEnd, DBInstanceId)
    DatabaseConnect(Sql)
    print TimeEnd

###备份情况
def GetBackup(DBInstanceId,StartTime,EndTime):
        Backup = DescribeBackupsRequest.DescribeBackupsRequest()
        Backup.set_DBInstanceId(DBInstanceId)
        Backup.set_StartTime(StartTime)
        Backup.set_EndTime(EndTime)
        Backup.set_accept_format('json')
        BackupInfo = clt.do_action_with_exception(Backup)
        Info = (json.loads(BackupInfo))
        BackupEndTime = Info['Items']['Backup']
        if BackupEndTime :
            TimeBefore =BackupEndTime[0]['BackupEndTime'].replace('T', ' ').replace('Z', '')
            TimeTransfer(TimeBefore)
            Sql = "update checklist set lastbackuptime='%s' where item='%s'and date=curdate()" % (TimeEnd, DBInstanceId)
            print TimeEnd
        else:
            global TimeEnd_v2
            TimeEnd_v2 = 'NULL'
            Sql = "update checklist set lastbackuptime='%s' where item='%s'and date=curdate()" % (TimeEnd_v2, DBInstanceId)
            print 'NULL'
        DatabaseConnect(Sql)



###错误日志数
def GetErrorLog(DBInstanceId,StartTime,EndTime):
    ErrorLog = DescribeErrorLogsRequest.DescribeErrorLogsRequest()
    ErrorLog.set_accept_format('json')
    ErrorLog.set_StartTime(StartTime)
    ErrorLog.set_EndTime(EndTime)
    ErrorLog.set_DBInstanceId(DBInstanceId)
    ErrorLogInfo = clt.do_action_with_exception(ErrorLog)
    Info = (json.loads(ErrorLogInfo))
    TotalRecordCount = Info['TotalRecordCount']
    Sql = "update checklist set errorlogcount='%s' where item='%s'and date=curdate()" % (TotalRecordCount, DBInstanceId)
    DatabaseConnect(Sql)
    print TotalRecordCount

### 监控相关
MasterKeyList = ['MySQL_QPSTPS','MySQL_MemCpuUsage']
def GetPerformance(DBInstanceId,MasterKey,StartTime,EndTime):
    Performance = DescribeDBInstancePerformanceRequest.DescribeDBInstancePerformanceRequest()
    Performance.set_accept_format('json')
    Performance.set_DBInstanceId(DBInstanceId)
    Performance.set_Key(MasterKey)
    Performance.set_StartTime(StartTime)
    Performance.set_EndTime(EndTime)
    PerformanceInfo = clt.do_action_with_exception(Performance)
    Info = (json.loads(PerformanceInfo))
    FirstList = []
    SecondList = []
    for i in Info['PerformanceKeys']['PerformanceKey'][0]['Values']['PerformanceValue']:
        FirstList.append(i['Value'].split('&')[0])
    for i in range(0, len(FirstList)):
        for j in range(i + 1, len(FirstList)):
            first = float(FirstList[i])
            second = float(FirstList[j])
            if first < second:
                FirstList[i] = FirstList[j]
                FirstList[j] = first
    MaxFirst = FirstList[0]
    for i in Info['PerformanceKeys']['PerformanceKey'][0]['Values']['PerformanceValue']:
        SecondList.append(i['Value'].split('&')[1])
    for i in range(0, len(SecondList)):
        for j in range(i + 1, len(SecondList)):
            first = float(SecondList[i])
            second = float(SecondList[j])
            if first < second:
                SecondList[i] = SecondList[j]
                SecondList[j] = first
    MaxSecond = SecondList[0]
    if (MasterKey == 'MySQL_QPSTPS'):
        QPS = MaxFirst
        TPS = MaxSecond
        Sql = "update checklist set max_QPS='%s',max_TPS='%s' where item='%s' and date=curdate()" % (QPS,TPS, DBInstanceId)
        print QPS, TPS
    elif (MasterKey == 'MySQL_MemCpuUsage'):
        CpuUsage = MaxFirst
        MemUsage = MaxSecond
        Sql = "update checklist set max_cpu='%s',max_mem='%s' where item='%s' and date=curdate()" % (CpuUsage, MemUsage, DBInstanceId)
        print CpuUsage,MemUsage
    DatabaseConnect(Sql)

###资源使用情况(硬盘)
def GetResourceUsage(DBInstanceId,Key):
    ResourceUsage = DescribeResourceUsageRequest.DescribeResourceUsageRequest()
    ResourceUsage.set_accept_format('json')
    ResourceUsage.set_DBInstanceId(DBInstanceId)
    ResourceUsageInfo = clt.do_action_with_exception(ResourceUsage)
    #print ResourceUsageInfo
    Info = (json.loads(ResourceUsageInfo))[Key]
    DiskUsage = format(float(Info)/float(1024*1024*1024),'.2f')
    Sql = "update checklist set diskusage='%s' where item='%s' and date=curdate()" % (DiskUsage, DBInstanceId)
    DatabaseConnect(Sql)
    print DiskUsage

### 入库操作
def DatabaseConnect(Sql):
    db =MySQLdb.connect("HOST","USER","PASSWORD","DB")
    cursor = db.cursor()
    cursor.execute(Sql)
    cursor.close()
    db.commit()



for DBInstanceId in DBInstanceIdList:
    Sql = "Insert into  checklist(date,item) VALUES (curdate(),'%s')" % DBInstanceId
    DatabaseConnect(Sql)
### 只读实例，有些状态不存在，故单独对待
    if DBInstanceId == '只读实例ID':
        GetRdsAttribute(DBInstanceId)
        GetErrorLog(DBInstanceId, StartTime, EndTime)
        for MasterKey in MasterKeyList:
            GetPerformance(DBInstanceId, MasterKey, StartTime, EndTime)
        GetResourceUsage(DBInstanceId,'DiskUsed')
    else:
        GetRdsAttribute(DBInstanceId)
        GetBackup(DBInstanceId, StartTime, EndTime)
        GetErrorLog(DBInstanceId, StartTime, EndTime)
        GetBackupPolicy(DBInstanceId)
        for MasterKey in MasterKeyList:
            GetPerformance(DBInstanceId, MasterKey, StartTime, EndTime)
        GetResourceUsage(DBInstanceId,'DiskUsed')
