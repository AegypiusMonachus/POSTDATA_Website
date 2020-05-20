import json
import os

import MySQLdb
import requests


def mkdir(path):
    folder = os.path.exists(path)

    if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)  # makedirs 创建文件时如果路径不存在会创建这个路径
        print("---  new folder...  ---")
        print("---  OK  ---")
    else:
        print("---  There is this folder!  ---")


def mkfile(dir_name, class_name, VPN):  # 定义函数名
    mkdir(dir_name)

    with open(dir_name + "/__init__.py", 'w', encoding='utf-8') as f1:
        pass
    with open(dir_name + "/config.json", 'w', encoding='utf-8') as f2:
        str2 = """{"currentId": 0}"""
        f2.write(str2)
    with open(dir_name + "/register.py", 'w', encoding='utf-8') as f3:
        str3 = """import json
import time
import threading
import sys
sys.path.append('./')                 # 在SendArticle目录执行
sys.path.append('/home/web_python/project/SendArticle')

import psutil
""" + "from " + dir_name + "." + dir_name + "_util import " + class_name + """
from project_utils.project_util import get_command_line_arguments, get_global_params, send_spider_status, \\
    send_spider_block_status, MysqlHandler
from project_utils import g_var


if __name__ == "__main__":
""" + """
    present_website = \"""" + dir_name + """\"
    VPN = \"""" + VPN + """\"

    # 获取命令行传入参数
    args = get_command_line_arguments()
    g_var.ALL_COUNT = int(args.count)
    g_var.INTERFACE_HOST = args.host
    g_var.UUID = args.uuid

    # 获取配置参数
    get_global_params(present_website)

    # 检查cpu和内存状态
    while psutil.virtual_memory().percent > g_var.RAM_MAX or psutil.cpu_percent(None) > g_var.CPU_MAX:
        g_var.logger.info("cpu或内存不足，挂起"+str(g_var.SEND_STATUS_INTERVAL)+"s")
        g_var.SPIDER_STATUS = 1
        close_signal = send_spider_block_status()
        if close_signal == 1:
            quit()
        time.sleep(g_var.SEND_STATUS_INTERVAL)

    # 在注册的主线程前，先取出数据库中最后的id存入config.json中，这样下次发文章开始取到的就是最新注册的账号
    sql = "select * from "+present_website+" order by id DESC limit 1"
    userInfo = MysqlHandler().select(sql)
    if userInfo != None:
        user_id = int(userInfo[0])
    else:
        user_id = 0

    current_id = {"currentId": user_id}
    with open(g_var.ENV_DIR+'/'+present_website+'/config.json', 'w') as f:
        json.dump(current_id, f)

    # 开始执行程序
    g_var.SPIDER_STATUS = 2

    # 考虑平均分配不是正好分的情况:例如94个任务分配给10个线程，先94/10取整，每个线程9个任务，剩余4个任务给前4个线程每个加1个任务
    EACH_THREAD_ASSIGNMENT_NUM = int(g_var.ALL_COUNT / g_var.THREAD_COUNT)  # 每个线程分配的基本任务数量
    ADD_ONE_ASSIGNMENT_THREAD_NUM = g_var.ALL_COUNT % g_var.THREAD_COUNT    # 需要增加一个任务的线程个数
    REMAIN_THREAD_NUM = g_var.THREAD_COUNT - ADD_ONE_ASSIGNMENT_THREAD_NUM  # 剩余不用增加任务的线程个数
    g_var.logger.info("EACH_THREAD_ASSIGNMENT_NUM" + str(EACH_THREAD_ASSIGNMENT_NUM))

    # 创建一个对象列表
    obj_list = []
    for i in range(0, ADD_ONE_ASSIGNMENT_THREAD_NUM):
        obj_list.append(""" + class_name + """(EACH_THREAD_ASSIGNMENT_NUM + 1))
    if EACH_THREAD_ASSIGNMENT_NUM != 0:
        for i in range(0, REMAIN_THREAD_NUM):
            obj_list.append(""" + class_name + """(EACH_THREAD_ASSIGNMENT_NUM))

    # 为每个对象开一个线程，加入到线程列表中统一管理
    t_list = []
    for i in range(0, len(obj_list)):
        t = threading.Thread(target=obj_list[i].registers, args=(present_website, VPN))
        t_list.append(t)

    # 线程开始执行
    for i in range(0, len(t_list)):
        t_list[i].setDaemon(True)
        t_list[i].start()

    # 定时发送状态
    close_send_status_signal = 0  # 发送消息的循环要等所有线程停止才能跳出循环
    wait_signal = 0

    while g_var.SPIDER_STATUS != 3 or close_send_status_signal != 1:
        close_send_status_signal, wait_signal = send_spider_status(obj_list, t_list)
        time.sleep(g_var.SEND_STATUS_INTERVAL)

    if wait_signal == 0:
        # 等待所有线程结束
        g_var.logger.info("等待所有线程结束")
        for i in range(0, len(t_list)):
            t_list[i].join()
    elif wait_signal == 1:
        # 不等待其他线程结束，直接停止
        g_var.logger.info("不等待其他线程结束，直接停止")

    MysqlHandler().dbclose()     # 关闭数据库
    g_var.logger.info("主线程结束！共计完成" + str(g_var.SUCCESS_COUNT) + "个\\n\\n\\n\\n\\n")
"""
        f3.write(str3)

    with open(dir_name + "/send_article.py", 'w', encoding='utf-8') as f4:
        str4 = """import json
import time
import threading
import sys
sys.path.append('./')                 # 在SendArticle目录执行
sys.path.append('/home/web_python/project/SendArticle')

import psutil
""" + "from " + dir_name + "." + dir_name + "_util import " + class_name + """
from project_utils.project_util import get_command_line_arguments, get_global_params, send_spider_status, \\
    send_spider_block_status, MysqlHandler
from project_utils import g_var


if __name__ == "__main__":
""" + """
    present_website = \"""" + dir_name + """\"
    VPN = \"""" + VPN + """\"

    # 获取命令行传入参数
    args = get_command_line_arguments()
    g_var.ALL_COUNT = int(args.count)
    g_var.INTERFACE_HOST = args.host
    g_var.UUID = args.uuid

    # 获取配置参数
    get_global_params(present_website)

    # 检查cpu和内存状态
    while psutil.virtual_memory().percent > g_var.RAM_MAX or psutil.cpu_percent(None) > g_var.CPU_MAX:
        g_var.logger.info("cpu或内存不足，挂起"+str(g_var.SEND_STATUS_INTERVAL)+"s")
        g_var.SPIDER_STATUS = 1
        close_signal = send_spider_block_status()
        if close_signal == 1:
            quit()
        time.sleep(g_var.SEND_STATUS_INTERVAL)

    # 开始执行程序
    g_var.SPIDER_STATUS = 2

    # 考虑平均分配不是正好分的情况:例如94个任务分配给10个线程，先94/10取整，每个线程9个任务，剩余4个任务给前4个线程每个加1个任务
    EACH_THREAD_ASSIGNMENT_NUM = int(g_var.ALL_COUNT / g_var.THREAD_COUNT)  # 每个线程分配的基本任务数量
    ADD_ONE_ASSIGNMENT_THREAD_NUM = g_var.ALL_COUNT % g_var.THREAD_COUNT    # 需要增加一个任务的线程个数
    REMAIN_THREAD_NUM = g_var.THREAD_COUNT - ADD_ONE_ASSIGNMENT_THREAD_NUM  # 剩余不用增加任务的线程个数
    g_var.logger.info("EACH_THREAD_ASSIGNMENT_NUM" + str(EACH_THREAD_ASSIGNMENT_NUM))

    # 创建一个对象列表
    obj_list = []
    for i in range(0, ADD_ONE_ASSIGNMENT_THREAD_NUM):
        obj_list.append(""" + class_name + """(EACH_THREAD_ASSIGNMENT_NUM + 1))
    if EACH_THREAD_ASSIGNMENT_NUM != 0:
        for i in range(0, REMAIN_THREAD_NUM):
            obj_list.append(""" + class_name + """(EACH_THREAD_ASSIGNMENT_NUM))

    # 为每个对象开一个线程，加入到线程列表中统一管理
    t_list = []
    for i in range(0, len(obj_list)):
        t = threading.Thread(target=obj_list[i].loginAndPostMessage, args=(present_website, VPN))
        t_list.append(t)

    # 线程开始执行
    for i in range(0, len(t_list)):
        t_list[i].setDaemon(True)
        t_list[i].start()

    # 定时发送状态
    close_send_status_signal = 0  # 发送消息的循环要等所有线程停止才能跳出循环
    wait_signal = 0

    while g_var.SPIDER_STATUS != 3 or close_send_status_signal != 1:
        close_send_status_signal, wait_signal = send_spider_status(obj_list, t_list)
        time.sleep(g_var.SEND_STATUS_INTERVAL)

    if wait_signal == 0:
        # 等待所有线程结束
        g_var.logger.info("等待所有线程结束")
        for i in range(0, len(t_list)):
            t_list[i].join()
    elif wait_signal == 1:
        # 不等待其他线程结束，直接停止
        g_var.logger.info("不等待其他线程结束，直接停止")

    # 程序结束前，将全局变量g_var.USER_ID写入config.json
    current_id = {"currentId": g_var.USER_ID}
    with open(g_var.ENV_DIR+'/'+present_website+'/config.json', 'w') as f:
        json.dump(current_id, f)

    MysqlHandler().dbclose()     # 关闭数据库
    g_var.logger.info("主线程结束！共计完成" + str(g_var.SUCCESS_COUNT) + "个\\n\\n\\n\\n\\n")
"""
        f4.write(str4)

    with open(dir_name + "/start.py", 'w', encoding='utf-8') as f5:
        str5 = """import json
import time
import threading
import sys
sys.path.append('./')                 # 在SendArticle目录执行
sys.path.append('/home/web_python/project/SendArticle')

import psutil
""" + "from " + dir_name + "." + dir_name + "_util import " + class_name + """
from project_utils.project_util import get_command_line_arguments, get_global_params, send_spider_status, \\
    send_spider_block_status, MysqlHandler
from project_utils import g_var


if __name__ == "__main__":
""" + """
    present_website = \"""" + dir_name + """\"
    VPN = \"""" + VPN + """\"

    # 获取命令行传入参数
    args = get_command_line_arguments()
    g_var.ALL_COUNT = int(args.count)
    g_var.INTERFACE_HOST = args.host
    g_var.UUID = args.uuid

    # 获取配置参数
    get_global_params(present_website)

    # 检查cpu和内存状态
    while psutil.virtual_memory().percent > g_var.RAM_MAX or psutil.cpu_percent(None) > g_var.CPU_MAX:
        g_var.logger.info("cpu或内存不足，挂起"+str(g_var.SEND_STATUS_INTERVAL)+"s")
        g_var.SPIDER_STATUS = 1
        close_signal = send_spider_block_status()
        if close_signal == 1:
            quit()
        time.sleep(g_var.SEND_STATUS_INTERVAL)

    # 开始执行程序
    g_var.SPIDER_STATUS = 2

    # 考虑平均分配不是正好分的情况:例如94个任务分配给10个线程，先94/10取整，每个线程9个任务，剩余4个任务给前4个线程每个加1个任务
    EACH_THREAD_ASSIGNMENT_NUM = int(g_var.ALL_COUNT / g_var.THREAD_COUNT)  # 每个线程分配的基本任务数量
    ADD_ONE_ASSIGNMENT_THREAD_NUM = g_var.ALL_COUNT % g_var.THREAD_COUNT    # 需要增加一个任务的线程个数
    REMAIN_THREAD_NUM = g_var.THREAD_COUNT - ADD_ONE_ASSIGNMENT_THREAD_NUM  # 剩余不用增加任务的线程个数
    g_var.logger.info("EACH_THREAD_ASSIGNMENT_NUM" + str(EACH_THREAD_ASSIGNMENT_NUM))

    # 创建一个对象列表
    obj_list = []
    for i in range(0, ADD_ONE_ASSIGNMENT_THREAD_NUM):
        obj_list.append(""" + class_name + """(EACH_THREAD_ASSIGNMENT_NUM + 1))
    if EACH_THREAD_ASSIGNMENT_NUM != 0:
        for i in range(0, REMAIN_THREAD_NUM):
            obj_list.append(""" + class_name + """(EACH_THREAD_ASSIGNMENT_NUM))

    # 为每个对象开一个线程，加入到线程列表中统一管理
    t_list = []
    for i in range(0, len(obj_list)):
        t = threading.Thread(target=obj_list[i].start, args=(present_website, VPN))
        t_list.append(t)

    # 线程开始执行
    for i in range(0, len(t_list)):
        t_list[i].setDaemon(True)
        t_list[i].start()

    # 定时发送状态
    close_send_status_signal = 0  # 发送消息的循环要等所有线程停止才能跳出循环
    wait_signal = 0

    while g_var.SPIDER_STATUS != 3 or close_send_status_signal != 1:
        close_send_status_signal, wait_signal = send_spider_status(obj_list, t_list)
        time.sleep(g_var.SEND_STATUS_INTERVAL)

    if wait_signal == 0:
        # 等待所有线程结束
        g_var.logger.info("等待所有线程结束")
        for i in range(0, len(t_list)):
            t_list[i].join()
    elif wait_signal == 1:
        # 不等待其他线程结束，直接停止
        g_var.logger.info("不等待其他线程结束，直接停止")

    MysqlHandler().dbclose()     # 关闭数据库
    g_var.logger.info("主线程结束！共计完成" + str(g_var.SUCCESS_COUNT) + "个\\n\\n\\n\\n\\n")
"""
        f5.write(str5)

    with open(dir_name + "/" + dir_name + "_util.py", 'w', encoding='utf-8') as f6:
        str6 = """import time

from project_utils.project_util import generate_login_data, MysqlHandler, get_Session, get_email
from project_utils import g_var

# @#$ 3、本处定义小项目通用的函数

# @#$ 4、定义对象，需要实现__register_one、login、__postMessage三个功能
# 每个函数都有指定的传入传出参数
class """ + class_name + """(object):
    def __init__(self, assignment_num):
        self.assignment_num = assignment_num    # 分配任务的数量
        self.now_count = 0                      # 本线程执行总数
        self.success_count = 0                  # 本线程执行成功数
        self.register_success_count = 0         # start方法中register成功数
        self.login_and_post_success_count = 0   # start方法中login_and_post成功数
        self.failed_count = 0                   # 本线程执行失败数
        self.proxy_err_count = 0                # 本线程代理连接连续失败数
        self.captcha_err_count = 0              # 当前验证码识别连续错误次数

    def __monitor_status(self):
        if g_var.SPIDER_STATUS == 3 or self.failed_count > g_var.ERR_COUNT:
            g_var.logger.error("g_var.SPIDER_STATUS=3 or self.failed_count > g_var.ERR_COUNT，本线程将停止运行")
            g_var.logger.info("self.failed_count="+str(self.failed_count))
            return -1
        return 0

    def __register_one(self, Session, present_website: str, email_and_passwd):
        \"\"\"
        注册一个账户,需要实现注册、激活、并将注册数据存入数据库的功能
        Args:
            Session：Session对象
            present_website：当前网站名，用于数据库表名
            email_and_passwd：邮箱账户和密码，email_and_passwd[0]是邮箱，[1]是密码
        Returns:
            注册成功返回注册数据字典对象registerData，需要包含id, username, password, email, cookie(在访问激活链接时能取到，\\
            取不到返回空)
                user_id这样获取：（示例）
                    # 将注册的账户写入数据库（sql自己写，这边只是个示例）
                    sql = "INSERT INTO "+present_website+"(username, password, mail, status, cookie) VALUES('" + \\
                    username + "', '" + password + "', '" + email + "', '" + str(0) + cookie + "');"
                    last_row_id = MysqlHandler().insert(sql)
                    if last_row_id != -1:
                        registerData["user_id"] = last_row_id
                        return registerData
                    else:
                        g_var.logger.error("数据库插入用户注册数据失败")
                        return 0
            注册失败返回状态码
            0：某些报错需要跳出while循环，更换邮箱
            -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
            -2:注册失败，可能是打码出错等原因，邮箱可以继续使用（邮箱资源成本较高，因此要确保注册成功后再更换邮箱），不跳出循环
        \"\"\"
        pass

    def login(self, Session, present_website: str, VPN, userInfo):
        \"\"\"
        登录
        根据用户信息userInfo中cookie是否为空
        1、有cookie，跳过登录流程，直接构造loginData返回
        2、没有cookie，需要post登录请求，获取到cookie存入数据库，再构造loginData返回
        Args:
            Session：Session对象
            present_website：当前网站名，用于数据库表名
            VPN：使用国内or国外代理
            userInfo：用户信息  userInfo[0]:id [1]:username [2]passwod [3]:emial [4]:status [5]cookie
        Returns:
            成功返回loginData
                loginData = {
                    'id': user_id,
                    'username': username,
                    'password': password,
                    'email': email,
                    'cookie': cookie,
                }
            失败返回状态值：
                1:表示账号密码失效，密码被改或账号被网站删除，将数据库中状态改为1，并跳出循环重新取账号
                0:跳出循环，重新取号
                -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
                -2:本次出错，不跳出循环
        Mysql Update示例:
            # 如果cookie失效，将该cookie从数据库中清除，并重新从数据库中获取登录账号密码
            sql = "UPDATE %s SET cookie='%s' WHERE id=%s ;" % (""" + dir_name + """, save_cookies, user_id)
            status = MysqlHandler().update(sql)
            if status == 0:
                g_var.logger.info("cookie失效，清除cookie update OK")
                return {"error": -2}
            else:
                g_var.logger.error("数据库清除cookie错误!")
                return {"error": 1}    
        \"\"\"
        user_id = userInfo[0]
        username = userInfo[1]
        password = userInfo[2]
        email = userInfo[3]
        cookie = userInfo[5]
        
        # 1、有cookie，跳过登录流程，直接构造loginData返回
        if userInfo[5] != None and userInfo[5] != "":
            # userInfo[5]保存cookie值，如果cookie不为空，则使用cookie
            g_var.logger.info("返回cookie" + userInfo[5])
            loginData = {
                'id': user_id,
                'username': username,
                'password': password,
                'email': email,
                'cookie': cookie,
            }
            return loginData
        # 2、没有cookie，需要post登录请求，获取到cookie存入数据库，再构造loginData返回
        else:
            # cookie为空，使用账号密码登录
            pass

    def __postMessage(self, Session, loginData: dict, present_website):
        \"\"\"
        发文章
        Args:
            Session：Session对象
            loginData：用户信息，包括user_id,username,password,email,cookie
            present_website：当前网站名，用于数据库表名
        Returns:
            成功返回:"ok"
            失败返回状态值：
                1:跳出循环，重新取号
                0:cookie失效，将cookie清空，跳出循环重新取号
                -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
                -2:本次出错，继续循环
        \"\"\"
        pass
    
    def __send_profile(self, Session, loginData: dict):
        \"\"\"
        发个人简介
        Args:
            Session：Session对象
            loginData：用户信息，包括user_id,username,password,email,cookie
        Returns:
            成功返回:'ok'
            失败返回状态值：
                1:跳出循环，重新取号
                0:cookie失效，将cookie清空，跳出循环重新取号
                -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
                -2:本次出错，继续循环
        \"\"\"
        pass

    def registers(self, present_website: str, VPN: str):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1

            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue

            email_and_passwd = get_email(present_website)
            if email_and_passwd == -1:
                self.failed_count = self.failed_count + 1
                continue

            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(Session, present_website, email_and_passwd)
                if registerData == 0:
                    g_var.logger.info("注册失败，报错原因需要更换邮箱，跳出本循环")
                    self.failed_count = self.failed_count + 1
                    break
                elif registerData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理连续错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif registerData == -2:
                    g_var.logger.info("注册失败，可能是邮箱密码不符合要求等原因，邮箱可以继续使用，不跳出循环")
                    self.failed_count = self.failed_count + 1
                    continue
                else:
                    # 注册成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    break
                time.sleep(g_var.SLEEP_TIME)

            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("连续注册失败！程序停止")
                break

        g_var.logger.info("g_var.SPIDER_STATUS" + str(g_var.SPIDER_STATUS))
        g_var.logger.info("本线程共成功注册'self.success_count'=" + str(self.success_count) + "个账户")

    def loginAndPostMessage(self, present_website, VPN: str):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1

            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue

            # 从数据库中获取用户信息
            userInfo = generate_login_data(present_website)
            g_var.logger.info(userInfo)
            if userInfo == None:
                g_var.ERR_CODE = 2001
                g_var.ERR_MSG = g_var.ERR_MSG + "无法获取proxy!"
                g_var.logger.error("数据库中获取用户失败，本线程停止！")
                return -1

            # 1、登录
            login_signal = 0
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                loginData = self.login(Session, present_website, VPN, userInfo)
                if loginData == 1:
                    # 返回1表示登录失败，将数据库中的status改为异常
                    g_var.logger.info('使用当前账号密码登录失败。。。')
                    sql = "UPDATE" + present_website + "SET status=1 WHERE id=" + str(userInfo[0]) + ";"
                    status = MysqlHandler().update(sql)
                    if status == -1:
                        return -1
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                elif loginData == 0:
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                elif loginData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif loginData == -2:
                    g_var.logger.info("登录失败，但可以使用此账户继续尝试，不跳出循环")
                    self.failed_count = self.failed_count + 1
                    continue
                else:
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续登录出错，程序停止"
                g_var.logger.error("login:连续登录失败！程序停止")
                break
            if login_signal == 1:
                continue

            # 2、发文章
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                time.sleep(g_var.SLEEP_TIME)
                retry_count = retry_count + 1
                status = self.__postMessage(Session, loginData, present_website)
                if status == 'ok':  # 发文章成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    break
                elif status == 1:
                    sql = "UPDATE " + present_website + " SET cookie='' WHERE id=" + str(loginData['id']) + ";"
                    status = MysqlHandler().update(sql)
                    if status == 0:
                        g_var.logger.info("cookie失效，清除cookie update OK")
                    else:
                        g_var.logger.error("数据库清除cookie错误!")
                    self.failed_count = self.failed_count + 1
                    break
                elif status == 0:
                    self.failed_count = self.failed_count + 1
                    break
                elif status == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == -2:
                    self.failed_count = self.failed_count + 1
                    continue
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续发文章出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功发送" + str(self.success_count) + "篇文章")
    
    def registerAndSendProfile(self, present_website, VPN: str):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1

            # 设置Session对象
            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue

            # 1、注册
            email_and_passwd = get_email(present_website)
            if email_and_passwd == -1:
                self.failed_count = self.failed_count + 1
                continue

            retry_count = 0
            register_signal = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(Session, present_website, email_and_passwd)

                if registerData == 0:
                    g_var.logger.info("注册失败，报错原因需要更换邮箱，跳出本循环")
                    self.failed_count = self.failed_count + 1
                    register_signal = 1
                    break
                elif registerData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif registerData == -2:
                    g_var.logger.info("注册失败，可能是邮箱密码不符合要求等原因，邮箱可以继续使用，不跳出循环")
                    self.failed_count = self.failed_count + 1
                    continue
                else:
                    # 注册成功
                    self.failed_count = 0
                    break
                time.sleep(g_var.SLEEP_TIME)
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("连续注册失败！程序停止")
                break
            if register_signal == 1:
                continue

            # 2、登录
            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue

            # 构造一个userInfo
            userInfo: tuple = (registerData['id'], registerData['username'], registerData['password'],
                               registerData['email'], '0', registerData['cookie'])

            login_signal = 0   # 记录状态，成功为0，失败为1
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1

                loginData = self.login(Session, present_website, VPN, userInfo)
                if loginData == 1:
                    # 返回1表示登录失败，将数据库中的status改为异常
                    g_var.logger.info('使用当前账号密码登录失败。。。')
                    sql = "UPDATE" + present_website + "SET status=1 WHERE id=" + str(userInfo[0]) + ";"
                    status = MysqlHandler().update(sql)
                    if status == -1:
                        return -1
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                elif loginData == 0:
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                elif loginData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif loginData == -2:
                    g_var.logger.info("登录失败，但可以使用此账户继续尝试，不跳出循环")
                    self.failed_count = self.failed_count + 1
                    continue
                else:
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续登录出错，程序停止"
                g_var.logger.error("连续登录失败！程序停止")
                break
            if login_signal == 1:
                continue
                
            # 3、发个人简介
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                time.sleep(g_var.SLEEP_TIME)
                retry_count = retry_count + 1
                status = self.__send_profile(Session, loginData)
                                if status == 'ok':  # 发个人简介成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    break
                elif status == 1:
                    sql = "UPDATE " + present_website + " SET cookie='' WHERE id=" + str(loginData['id']) + ";"
                    status = MysqlHandler().update(sql)
                    if status == 0:
                        g_var.logger.info("cookie失效，清除cookie update OK")
                    else:
                        g_var.logger.error("数据库清除cookie错误!")
                    self.failed_count = self.failed_count + 1
                    break
                elif status == 0:
                    g_var.logger.info("发个人简介失败，跳出本循环更换账号")
                    self.failed_count = self.failed_count + 1
                    break
                elif status == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == -2:
                    self.failed_count = self.failed_count + 1
                    continue
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续发文章出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功发送" + str(self.success_count) + "则个人简介")

    def start(self, present_website, VPN):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1

            # 设置Session对象
            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue

            # 1、注册
            email_and_passwd = get_email(present_website)
            if email_and_passwd == -1:
                self.failed_count = self.failed_count + 1
                continue

            retry_count = 0
            register_signal = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(Session, present_website, email_and_passwd)

                if registerData == 0:
                    g_var.logger.info("注册失败，报错原因需要更换邮箱，跳出本循环")
                    self.failed_count = self.failed_count + 1
                    register_signal = 1
                    break
                elif registerData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif registerData == -2:
                    g_var.logger.info("注册失败，可能是邮箱密码不符合要求等原因，邮箱可以继续使用，不跳出循环")
                    self.failed_count = self.failed_count + 1
                    continue
                else:
                    # 注册成功
                    self.failed_count = 0
                    break
                time.sleep(g_var.SLEEP_TIME)
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("连续注册失败！程序停止")
                break
            if register_signal == 1:
                continue

            # 2、登录
            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue

            # 构造一个userInfo
            userInfo: tuple = (registerData['id'], registerData['username'], registerData['password'],
                               registerData['email'], '0', registerData['cookie'])

            login_signal = 0   # 记录状态，成功为0，失败为1
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1

                loginData = self.login(Session, present_website, VPN, userInfo)
                if loginData == 1:
                    # 返回1表示登录失败，将数据库中的status改为异常
                    g_var.logger.info('使用当前账号密码登录失败。。。')
                    sql = "UPDATE" + present_website + "SET status=1 WHERE id=" + str(userInfo[0]) + ";"
                    status = MysqlHandler().update(sql)
                    if status == -1:
                        return -1
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                elif loginData == 0:
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                elif loginData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif loginData == -2:
                    g_var.logger.info("登录失败，但可以使用此账户继续尝试，不跳出循环")
                    self.failed_count = self.failed_count + 1
                    continue
                else:
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续登录出错，程序停止"
                g_var.logger.error("连续登录失败！程序停止")
                break
            if login_signal == 1:
                continue

            # 3、发文章
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                time.sleep(g_var.SLEEP_TIME)
                retry_count = retry_count + 1
                status = self.__postMessage(Session, loginData, present_website)
                if status == 'ok':  # 发文章成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    break
                elif status == 1:
                    sql = "UPDATE " + present_website + " SET cookie='' WHERE id=" + str(loginData['id']) + ";"
                    status = MysqlHandler().update(sql)
                    if status == 0:
                        g_var.logger.info("cookie失效，清除cookie update OK")
                    else:
                        g_var.logger.error("数据库清除cookie错误!")
                    self.failed_count = self.failed_count + 1
                    break
                elif status == 0:
                    self.failed_count = self.failed_count + 1
                    break
                elif status == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == -2:
                    self.failed_count = self.failed_count + 1
                    continue
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续发文章出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功注册账户并发送文章" + str(self.success_count) + "篇")
"""
        f6.write(str6)
    with open(dir_name + "/" + dir_name + "_test.py", 'w', encoding='utf-8') as f7:
        str7 = """import sys
sys.path.append('./')
from """ + dir_name + "." + dir_name + """_util import """ + class_name + """
from project_utils import g_var, requestsW
from project_utils.project_util import get_command_line_arguments, get_global_params, generate_login_data


if __name__ == '__main__':
    present_website = \"""" + dir_name + """\"
    VPN = \"""" + VPN + """\"
    uuid = "1234567890"
    host = "http://192.168.31.234:8080"
    count = 10
    g_var.ALL_COUNT = count
    g_var.INTERFACE_HOST = host
    g_var.UUID = uuid
    # 获取全局配置参数
    get_global_params(present_website,True)
    # 1、注册测试
    # """ + class_name + """(3).registers(present_website,VPN)

    # 2、登录测试
    # s = requestsW.session()
    # userInfo = generate_login_data(present_website,"网站json/config.json")#网站下json绝对路径
    # loginData = """ + class_name + """(3).login(s, present_website, VPN, userInfo)

    # 3、发送文章测试
    # userInfo = generate_login_data(present_website,"网站json/config.json")#网站下json绝对路径
    # """ + class_name + """(1).loginAndPostMessage(present_website,VPN)
"""
        f7.write(str7)

    with open(dir_name + "/send_profile.py", 'w', encoding='utf-8') as f8:
        str8 = """import json
import time
import threading
import sys
sys.path.append('./')                 # 在SendArticle目录执行
sys.path.append('/home/web_python/project/SendArticle')

import psutil
""" + "from " + dir_name + "." + dir_name + "_util import " + class_name + """
from project_utils.project_util import get_command_line_arguments, get_global_params, send_spider_status, \\
    send_spider_block_status, MysqlHandler
from project_utils import g_var


if __name__ == "__main__":
""" + """
    present_website = \"""" + dir_name + """\"
    VPN = \"""" + VPN + """\"

    # 获取命令行传入参数
    args = get_command_line_arguments()
    g_var.ALL_COUNT = int(args.count)
    g_var.INTERFACE_HOST = args.host
    g_var.UUID = args.uuid

    # 获取配置参数
    get_global_params(present_website)

    # 检查cpu和内存状态
    while psutil.virtual_memory().percent > g_var.RAM_MAX or psutil.cpu_percent(None) > g_var.CPU_MAX:
        g_var.logger.info("cpu或内存不足，挂起"+str(g_var.SEND_STATUS_INTERVAL)+"s")
        g_var.SPIDER_STATUS = 1
        close_signal = send_spider_block_status()
        if close_signal == 1:
            quit()
        time.sleep(g_var.SEND_STATUS_INTERVAL)

    # 开始执行程序
    g_var.SPIDER_STATUS = 2

    # 考虑平均分配不是正好分的情况:例如94个任务分配给10个线程，先94/10取整，每个线程9个任务，剩余4个任务给前4个线程每个加1个任务
    EACH_THREAD_ASSIGNMENT_NUM = int(g_var.ALL_COUNT / g_var.THREAD_COUNT)  # 每个线程分配的基本任务数量
    ADD_ONE_ASSIGNMENT_THREAD_NUM = g_var.ALL_COUNT % g_var.THREAD_COUNT    # 需要增加一个任务的线程个数
    REMAIN_THREAD_NUM = g_var.THREAD_COUNT - ADD_ONE_ASSIGNMENT_THREAD_NUM  # 剩余不用增加任务的线程个数
    g_var.logger.info("EACH_THREAD_ASSIGNMENT_NUM" + str(EACH_THREAD_ASSIGNMENT_NUM))

    # 创建一个对象列表
    obj_list = []
    for i in range(0, ADD_ONE_ASSIGNMENT_THREAD_NUM):
        obj_list.append(""" + class_name + """(EACH_THREAD_ASSIGNMENT_NUM + 1))
    if EACH_THREAD_ASSIGNMENT_NUM != 0:
        for i in range(0, REMAIN_THREAD_NUM):
            obj_list.append(""" + class_name + """(EACH_THREAD_ASSIGNMENT_NUM))

    # 为每个对象开一个线程，加入到线程列表中统一管理
    t_list = []
    for i in range(0, len(obj_list)):
        t = threading.Thread(target=obj_list[i].registerAndSendProfile, args=(present_website, VPN))
        t_list.append(t)

    # 线程开始执行
    for i in range(0, len(t_list)):
        t_list[i].setDaemon(True)
        t_list[i].start()

    # 定时发送状态
    close_send_status_signal = 0  # 发送消息的循环要等所有线程停止才能跳出循环
    wait_signal = 0

    while g_var.SPIDER_STATUS != 3 or close_send_status_signal != 1:
        close_send_status_signal, wait_signal = send_spider_status(obj_list, t_list)
        time.sleep(g_var.SEND_STATUS_INTERVAL)

    if wait_signal == 0:
        # 等待所有线程结束
        g_var.logger.info("等待所有线程结束")
        for i in range(0, len(t_list)):
            t_list[i].join()
    elif wait_signal == 1:
        # 不等待其他线程结束，直接停止
        g_var.logger.info("不等待其他线程结束，直接停止")

    MysqlHandler().dbclose()     # 关闭数据库
    g_var.logger.info("主线程结束！共计完成" + str(g_var.SUCCESS_COUNT) + "个\\n\\n\\n\\n\\n")
"""
        f8.write(str8)

    print('ok')


if __name__ == '__main__':
    website_name = input("请输入网站名：")
    VPN = input("请输入VPN：")

    INTERFACE_HOST = "http://192.168.31.234:8080/"

    dir_name = "_".join(website_name.split(".")[-2:])
    class_name = website_name.split(".")[-2].title() + website_name.split(".")[-1].title()
    mkfile(dir_name, class_name, VPN)

    # 从中控获取数据库信息，在数据库中创建表
    with requests.get(url=INTERFACE_HOST + "/v1/get/config/?UUID=1234567890", timeout=15) as r:
        global_config = json.loads(r.text)
        sql_host = global_config["sql_host"]
        sql_port = int(global_config["sql_port"])
        sql_user = global_config["sql_user"]
        sql_pass = global_config["sql_pass"]
        sql_database = global_config["sql_database"]

    db = MySQLdb.connect(host=sql_host, port=sql_port, user=sql_user, password=sql_pass, db=sql_database,
                         charset='utf8')
    cursor = db.cursor()  # 创建游标

    sql1 = "CREATE TABLE if not exists " + dir_name + """
    (
        id int(11) NOT NULL AUTO_INCREMENT COMMENT 'id',
        username varchar(64) COLLATE utf8mb4_bin NOT NULL COMMENT '用户名',
        password varchar(64) COLLATE utf8mb4_bin NOT NULL COMMENT '密码',
        mail varchar(124) COLLATE utf8mb4_bin DEFAULT NULL COMMENT '邮箱',
        status int(1) unsigned zerofill NOT NULL COMMENT '状态0 正常， 1异常',
        cookie text COLLATE utf8mb4_bin COMMENT 'cookie',
        PRIMARY KEY (id)
    ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
    """
    cursor.execute(sql1)  # 执行sql
    sql2 = "CREATE TABLE if not exists " + dir_name + "_article" + """
    (
        id int(11) NOT NULL AUTO_INCREMENT COMMENT 'id',
        url varchar(2048) COLLATE utf8mb4_bin NOT NULL COMMENT 'url',
        keyword text COLLATE utf8mb4_bin COMMENT 'keyword',
        user_id int(11) DEFAULT NULL COMMENT '用户id',
        PRIMARY KEY (id)
    ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
    """
    cursor.execute(sql2)
    db.commit()  # 手动提交

    print("提示：项目创建成功！全局搜索@#$，查看项目创建后需要修改的地方")
