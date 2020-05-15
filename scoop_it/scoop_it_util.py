import re
import json
import sys
import random
import threading
import time

import requests
from requests.adapters import HTTPAdapter

from project_utils.project_util import generate_login_data, ip_proxy, get_new_article, MysqlHandler, get_Session, \
    get_email, EmailVerify, account_activation, google_captcha, generate_random_string
from project_utils import g_var

# @#$ 3、本处定义小项目通用的函数

# @#$ 4、定义对象，需要实现__register_one、__login、__postMessage三个功能
# 每个函数都有指定的传入传出参数
class ScoopIt(object):
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
        """
        注册一个账户
        Args:
            Session：Session对象
            present_website：当前网站名，用于数据库表名
            email_and_passwd：邮箱账户和密码，email_and_passwd[0]是邮箱，[1]是密码
        Returns:
            注册成功返回注册数据字典对象registerData，需要包含user_id, username, password, email
                user_id这样获取：（示例）
                    # 将注册的账户写入数据库（sql自己写，这边只是个示例）
                    sql = "INSERT INTO "+present_website+"(username, password, mail, status) VALUES('" + name + \
                          "', '" + psd + "', '" + email_and_passwd[0] + "', '" + str(0) + "');"
                    last_row_id = MysqlHandler().insert(sql)
                    if last_row_id != -1:
                        registerData["user_id"] = last_row_id
                        return registerData
                    else:
                        g_var.logger.error("数据库插入用户注册数据失败")
                        return 0
            注册失败返回状态码
            0：注册成功，但是激活失败或插入数据库失败
            -1:表示requests请求页面失败，需要更换代理
            -2:注册失败，可能是邮箱密码不符合要求、或ip被封等原因，需要排查
        """
        FullName = generate_random_string(15, 20)
        password = generate_random_string(10, 15)

        googlekey = "6LevIjoUAAAAAEJnsStYfxxf5CEQgST01NxAwH8v"
        pageurl = "https://www.scoop.it/subscribe?&token=&sn=&showForm=true"
        recaptcha_value = google_captcha(Session, googlekey, pageurl)
        # recaptcha_value = input("请输入验证码：")

        registerData = {
            'jsDetectedTimeZone': 'Asia/Shanghai',
            'pc': '',
            'displayName': FullName,
            'shortName': FullName,
            'email': email_and_passwd[0],
            'password': password,
            'avatar': '',
            'upload-image-original-url': '',
            'job': 'My personal brand or blog',
            'g-recaptcha-response': recaptcha_value,
            'subscribe': ''
        }

        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': 'messagesUtk=beaaffd5ab3d4039b7e27015e4203fda;',
            'origin': 'https://www.scoop.it',
            'referer': 'https://www.scoop.it/subscribe?&token=&sn=&showForm=true',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36',
        }
        url = "https://www.scoop.it/subscribe?&token=&sn=&showForm=true"
        Session.get(url, headers=headers, timeout=g_var.TIMEOUT)
        html = Session.post(url, headers=headers, data=registerData, timeout=g_var.TIMEOUT).text

        re_text = '(https://www.scoop.it/confirm\?.*?)" '
        email_verify_obj = EmailVerify(email_and_passwd[0], email_and_passwd[1], re_text)
        verify_url = account_activation(Session, email_verify_obj)
        result = Session.get(url=verify_url, headers=headers, timeout=g_var.TIMEOUT)
        if result == -1:
            g_var.logger.error("访问激活链接超时")
            return -1

        sql = "INSERT INTO "+present_website+"(username, password, mail, status, cookie) VALUES('" + FullName + \
              "', '" + password + "', '" + email_and_passwd[0] + "', '" + str(0) + str(result.cookies.get_dict()) +"');"
        last_row_id = MysqlHandler().insert(sql)

    def __login(self, Session, present_website: str, VPN, userInfo):
        """
        登录
        根据用户信息userInfo中是否包含cookie
        1、有cookie直接构造loginData返回，跳过登录流程
        2、没有cookie，需要post登录请求，获取到cookie，再构造loginData返回
        Args:
            Session：Session对象
            present_website：当前网站名，用于数据库表名
            VPN：使用国内or国外代理
            userInfo：用户信息
        Returns:
            成功返回loginData
                loginData = {
                    'id': user_id,
                    'username': username,
                    'password': password,
                    'cookie': cookie,
                }
            失败返回状态值：
                1:表示账号密码失效，密码被改或账号被网站删除
                -1:表示requests请求页面失败，需要更换代理
                -2:页面发生改变，获取不到页面上的一些token值
                -3:数据库插入更新等错误
        """

        if userInfo[5] != None and userInfo[5] != "":
            # userInfo[5]保存cookie值，如果cookie不为空，则使用cookie
            g_var.logger.info("返回cookie" + userInfo[5])
            user_id = userInfo[0]
            username = userInfo[1]
            password = userInfo[2]
            cookie = userInfo[5]
            loginData = {
                'id': user_id,
                'username': username,
                'password': password,
                'cookie': cookie,
            }
            return loginData
        else:
            # cookie为空，使用账号密码登录
            pass

    def __postMessage(self, Session, loginData: dict, present_website):
        """
        发文章
        Args:
            Session：Session对象
            loginData：用户信息，包括user_id,username,password,cookie
            present_website：当前网站名，用于数据库表名
        Returns:
            成功返回状态值：0
            失败返回状态值：
                1:表示账号密码失效，密码被改或账号被网站删除
                -1:表示requests请求页面失败，需要更换代理
                -2:页面发生改变，获取不到页面上的一些token值
                -3:数据库插入更新等错误
        """
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

            # @#$ 5、获取邮箱,如果不需要邮箱，这边改成传空值
            email_and_passwd = get_email(present_website)
            if email_and_passwd == -1:
                self.failed_count = self.failed_count + 1
                continue
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(Session, present_website, email_and_passwd)
                if registerData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG+"|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count=g_var.RETRY_COUNT_MAX
                elif registerData == -2:
                    g_var.logger.info("注册失败,可能是邮箱密码不符合要求、或ip被封等原因，请排查！")
                    self.proxy_err_count = self.proxy_err_count + 1
                    proxies = ip_proxy(VPN)
                    if proxies == {"error": -1}:
                        g_var.logger.info("获取代理错误")
                        self.failed_count = self.failed_count + 1
                    Session.proxies = proxies
                elif registerData == 0:
                    # 注册成功，但激活失败
                    g_var.logger.info("注册成功,但激活失败！")
                    break
                else:
                    # 注册成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
                time.sleep(g_var.SLEEP_TIME)

            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG =  g_var.ERR_MSG+"|_|连续注册出错，程序停止"
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

                loginData = self.__login(Session, present_website, VPN, userInfo)
                if loginData == -1:
                    # 代理问题，更换代理
                    g_var.ERR_MSG = g_var.ERR_MSG+"|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count=g_var.RETRY_COUNT_MAX
                elif loginData == -2:
                    # 账号异常，跳出本循环
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                else:
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG+"|_|连续登录出错，程序停止"
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
                if status == 0:  # 发文章成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
                elif status == -1:
                    # 返回值为-1，更换代理
                    g_var.ERR_MSG = g_var.ERR_MSG+"|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count=g_var.RETRY_COUNT_MAX
                elif status == -2:
                    # 返回值为-1，某些必须停止的错误，程序停止
                    self.failed_count = self.failed_count + 1
                    g_var.SPIDER_STATUS = 3
                    break
                elif status == -3:
                    # 返回值为-1，数据库错误
                    self.failed_count = self.failed_count + 1
                elif status == -4:
                    # 返回值为-4，cookie过期，跳出循环从开头重新取值
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG+"|_|连续发文章出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功发送" + str(self.success_count) + "篇文章")

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
            # 获取邮箱
            email_and_passwd = get_email(present_website)
            if email_and_passwd == -1:
                self.failed_count = self.failed_count + 1
                continue
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(Session, present_website, email_and_passwd)

                if registerData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG+"|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count=g_var.RETRY_COUNT_MAX
                elif registerData == 0:
                    # 注册成功，但激活失败
                    g_var.logger.info("注册成功,但激活失败！")
                    break
                else:
                    # 注册成功
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG =  g_var.ERR_MSG+"|_|连续注册出错，程序停止"
                g_var.logger.error("start:连续注册失败！程序停止")
                break

            # 2、登录
            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue

            # 构造一个userInfo
            userInfo: tuple = (registerData['user_id'], registerData['user[login]'], registerData['user[password]'],
                               registerData['user[email]'], '0', "")

            login_signal = 0   # 记录状态，成功为0，失败为1
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1

                loginData = self.__login(Session, present_website, VPN, userInfo)
                if loginData == -1:
                    # 代理问题，更换代理
                    g_var.ERR_MSG = g_var.ERR_MSG+"|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count=g_var.RETRY_COUNT_MAX
                elif loginData == -2:
                    # 账号异常，跳出本循环
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                else:
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG =  g_var.ERR_MSG+"|_|连续登录出错，程序停止"
                g_var.logger.error("start:连续登录失败！程序停止")
                break
            if login_signal == 1:
                continue

            # 3、发文章
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                status = self.__postMessage(Session, loginData, present_website)
                if status == 0:  # 发文章成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
                elif status == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG+"|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count=g_var.RETRY_COUNT_MAX
                elif status == -2:
                    # 某些必须停止的错误，程序停止
                    self.failed_count = self.failed_count + 1
                    g_var.SPIDER_STATUS = 3
                    break
                elif status == -3:
                    self.failed_count = self.failed_count + 1
                elif status == -4:
                    # 返回值为-4，cookie过期，跳出循环从开头重新取值
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG+"|_|连续发文章出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功注册账户并发送文章" + str(self.success_count) + "篇")      
