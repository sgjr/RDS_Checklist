# RDS_Checklist
- 用途：通过调用阿里云API接口，将巡检数据记录到本地数据库，方便书写巡检报告
- 环境：python2.7
- 需要安装：
```
/usr/local/python27/bin/pip2.7 install aliyun-python-sdk-core aliyun-python-sdk-rds datetime
```
- 设置定时任务，每日凌晨巡检
```
0 0 * * * python2.7 /usr/local/python27/checklist.py
```
