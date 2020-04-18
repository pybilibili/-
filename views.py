#-*- coding:UTF-8 -*-
import operator
import string
import logging
import redis
import traceback

from rest_framework.views import APIView
from django.conf import settings
from dashboard.utils.JSONHttpResponse import JSONHttpResponse
from vec_dashboard_auth.decorator import login_required
from vec_client import client as vecclient
from cluster_mgr import cluster_server  
from vec_client.common import timeutils
from vec_client.db.sqlAlchmey import api as db_api

LOG = logging.getLogger("vec_dashboard")

# 首页
class HomeInfoView(APIView):
    @login_required
    def post(self, request, format=None):
        vc = vecclient.Client()
        host_ip = request.DATA.get('host_ip')
        classroom_id = request.DATA.get('classroom_id', None)
        
        resp = {"errcode":0,"msg":"success"}
        resp["classrooms"] = []
        resp["classroom"] = {}
        
        # 集群列表
        result_classrooms = vc.vec_home.classrooms_list(vc.vec_server_client)
        if not classroom_id or classroom_id == '-1':
            resp["classroom"] = vc.vec_home.get_classroom_self(host_ip, vc.vec_server_client)
        
        if result_classrooms['errcode'] == 0 and len(result_classrooms['rooms']) != 0:
            resp["classrooms"] = result_classrooms['rooms']
            if classroom_id and classroom_id != '-1':
                result_classroom = vc.vec_home.classroom_by_id(vc.vec_server_client, classroom_id)
                # 终端运行信息 模版信息
                if result_classroom['errcode'] == 0:
                    resp["classroom"] = result_classroom['room']
        
        local_classroom_name = vc.vec_home.get_local_classname()
        resp['classrooms'].append({
                'id': '-1',
                'state': 'active',
                'address': host_ip,
                'name': local_classroom_name
            })
        # 日志
        # 警报
        # 计划任务

        # resp["count"] = {
        #     'log': vc.vec_home.count_log_error(),
        #     'crontab': vc.vec_home.count_crontab(),
        #     'alarm': vc.vec_home.count_alarm(vc, host_ip),
        # }
        # 授权信息
        # resp['auth'] = {}
        # result_auth = vc.vec_home.getinfo_for_web(vc)
        # if result_auth['errcode'] == 0:
        #     resp['auth'] = result_auth['info']
        # 网卡信息
        # resp['network'] = []
        # key = request.DATA.get('key')
        # r = redis.Redis(host='controller', port=6379, db=0)
        # key = host_ip + ":" + key 
       
        now = timeutils.utcnow_ts()
        start_time = request.DATA.get('start_time', 'none')
        if start_time == "none":
            start_time = now - 600
        
        resp['time_server'] = timeutils.iso8601_from_timestamp(now)
        # resp['network'] = vc.vec_home.network_info(r, host_ip, key, start_time, now)
        return JSONHttpResponse(resp)

class ClassroomByIdView(APIView):
    @login_required
    def post(self, request, format=None):
        resp = {"errcode":0,"msg":"success"}
        classroom_id = request.DATA.get('id')
        vc = vecclient.Client()
        result_classroom = vc.vec_home.classroom_by_id(vc.vec_server_client, classroom_id)
        if result_classroom['errcode'] == 0:
            resp["classroom"] = result_classroom['room']
        return JSONHttpResponse(resp)

# 保存接口
class SaveInfoView(APIView):
    @login_required
    def post(self, request, format=None):
        resp = {"errcode":0,"msg":"success"}
        client = request.DATA.get('client', None)
        score = request.DATA.get('score', None)
        try:
            # db_api 是sqlAlchmey查询数据库文件  是对数据库的增删改查操作
            DATA = db_api.git_info(client)
            if DATA:  # 如果有就替换，没有就增加。
                db_api.revamp(client,score)
            else:
                db_api.save(client,score)
        except Exception as e:
            LOG.error(traceback.format_exc())
            resp['msg'] = traceback.format_exc()
            return JSONHttpResponse(resp)

        return JSONHttpResponse(resp)

# 查询接口
class GitInfoView(APIView):
    @login_required
    def post(self, request, format=None):
        resp = {"errcode":0,"msg":"success"}
        client = request.DATA.get('client', None)
        start = request.DATA.get('start', None)
        end = request.DATA.get('end', None)
        try:
            DATA = db_api.git_all(client)
            # 假设查出来的数据是DATA
            DATA = [{ "ranking" : 0 , "client" : "客户端1", "score" : 99},  
                    { "ranking" : 0 , "client" : "客户端2", "score" : 92}, 
                    { "ranking" : 0 , "client" : "客户端3", "score" : 54}, 
                    { "ranking" : 0 , "client" : "客户端4" , "score" : 23}] 

            data_list = sorted(DATA, key = lambda i: i['score']) # 用sorted对字典排序


            for i in range(len(data_list)): # 循环一下加上ranking
                data_list[i]["ranking"] = i+1
            
            if start and end:  # 根据区间把多余的删掉
                for one in data_list:
                    if one["ranking"] <= start or one["ranking"] >= end:
                        data_list.remove(one)

            data_list.append({ "ranking" : data_list[-1]['ranking']+1 , "client" : client , "score" : db_api.git_score(client)}) # 把查询者数据放最后
            
            resp['data'] = data_list
        except Exception as e:
            LOG.error(traceback.format_exc())
            resp['msg'] = traceback.format_exc()
            return JSONHttpResponse(resp)

        return JSONHttpResponse(resp)