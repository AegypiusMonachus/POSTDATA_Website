import time

import psutil

from diigo_com.diigo_com_util import DiigoCom
from diigo_com.dome_test import register_one
from project_utils import g_var,requestsW
from project_utils.project_util import get_command_line_arguments, get_global_params, send_spider_block_status, \
    ip_proxy, MysqlHandler, generate_login_data

# def testrequestsW():
#     proxies=ip_proxy("en")
#     print(proxies)
#     s=requests.session()
#     s.proxies=proxies
#     res=requests.get("https://www.baidu.com",proxies=proxies)
#     # res=s.get("https://blog.csdn.net/sj349781478/article/details/79552218",headers={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"},verify=False,timeout=10)
#     print(res)


if __name__ == '__main__':
    present_website = "diigo_com"
    VPN = "en"
    uuid="diggo_com_test"
    host="http://192.168.31.234:8080"
    count=10
    # 获取命令行传入参数
    # args = get_command_line_arguments()
    g_var.ALL_COUNT = count
    g_var.INTERFACE_HOST = host
    g_var.UUID = uuid
    # 获取配置参数
    # get_global_params(present_website,True)
    #注册测试
    # DiigoCom(3).registers(present_website,VPN)

    ##登录测试
    # s = requestsW.session()
    # userInfo = generate_login_data(present_website,"/Users/a/Desktop/python/spider/web2_shezhen/SendArticle/diigo_com/config.json")
    # loginData = DiigoCom(3).login(s, present_website, VPN, userInfo)

    ##发送文章测试
    # userInfo = generate_login_data(present_website,"/Users/a/Desktop/python/spider/web2_shezhen/SendArticle/diigo_com/config.json")
    # DiigoCom(1).loginAndPostMessage(present_website,VPN)

    # s=requestsW.session()
    # s.proxies=ip_proxy("en")
    # rlist=[]
    # for i in range(15):
    #     r=register_one(s)
    #     rlist.append(r)
    # print(rlist)