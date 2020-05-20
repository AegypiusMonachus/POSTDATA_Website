from project_utils import g_var
from project_utils.project_util import get_global_params
from boredpanda_com.boredpanda_com_dome import register_test

if __name__ == '__main__':
    present_website = "reddit_com"
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
    get_global_params(present_website,True)
    #注册测试
    # RedditCom(2).registers(present_website,VPN)

    ##登录测试
    # s = requestsW.session()
    # userInfo = generate_login_data(present_website,"/Users/a/Desktop/python/spider/web2_shezhen/SendArticle/reddit_com/config.json")#网站下json绝对路径
    # loginData = RedditCom(3).login(s, present_website, VPN, userInfo)

    ##发送文章测试
    # userInfo = generate_login_data(present_website,"/Users/a/Desktop/python/spider/web2_shezhen/SendArticle/reddit_com/config.json")#网站下json绝对路径
    # RedditCom(1).loginAndPostMessage(present_website,VPN)

    # s=requestsW.session()
    # s.proxies=ip_proxy("en")
    # rlist=[]
    # for i in range(15):
    #     r=register_one(s)
    #     rlist.append(r)
    # print(rlist)
    # register()

    register_test()

"""
user_email: 873271861@qq.com
user_full_name: hj17752545956
user_pass: Hj17752545956"""