import re
import json
import sys
import random
import threading
import time

import requests
from requests.adapters import HTTPAdapter

from project_utils.project_util import generate_login_data, ip_proxy, get_new_article, MysqlHandler, \
    generate_random_string, get_new_title_and_link, get_Session
from project_utils import g_var

def generate_headers(signal, loginData = None):
    try:
        headers = {
            'Connection': 'close',
        }
        requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
        with requests.get(url=g_var.INTERFACE_HOST + "/v1/get/user_agent/", headers=headers, timeout=g_var.TIMEOUT) as r:
            user_agent = r.text
    except:
        g_var.ERR_CODE = 2005
        g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "user_agent获取失败!"
        g_var.logger.error("user_agent获取失败!")
        return -1

    if signal == 0:
        # 注册登录使用的header
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Host": "www.indiegogo.com",
            "User-Agent": user_agent,
        }
    elif signal == 1:
        headers = {
            "accept": "application/json",
            "content-type": "application/json;charset=UTF-8",
            "user_agent": user_agent,
        }
    elif signal == 2:
        headers = {
            'referer': 'https://www.indiegogo.com/',
            "user_agent": user_agent,
        }
    elif signal == 3:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://www.indiegogo.com',
            'referer': 'https://www.indiegogo.com/individuals/' + str(loginData["id"]) + '/edit',
            'user_agent': user_agent,
            'x-csrf-token': loginData["token"],
        }
    return headers

def generate_register_data():
    # 生成注册数据返回
    try:
        registerData = {}
        registerData['domain_code'] = "www"
        registerData['captcha_response'] = None
        firstname = generate_random_string(8, 12)
        lastname = generate_random_string(8, 12)
        password = generate_random_string(10, 14)
        email = firstname + '@hotmail.com'
        account = {
            'email': email,
            'password': password,
            'firstname': firstname,
            'lastname': lastname,
            'disclaimer_input': True,
            'general_opt_in': False,
            'source': None
        }
        registerData['account'] = account
    except Exception as e:
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "注册数据生成中出现异常..."
        g_var.logger.info("注册数据生成中出现异常...")
        g_var.logger.info(e)
        return -2
    return registerData

# 获取csrf
def get_csrf(Session, header=None):
    try:
        url = 'https://www.indiegogo.com'
        res = Session.get(url, timeout=g_var.TIMEOUT)
        if res == -1:
            return res
        csrf = re.findall('<meta name="csrf-token" content="(.*?)" />', res.text)
        if not csrf:
            g_var.logger.info("未获取到x-csrf-token...")
            return -2
        return csrf[0]
    except:
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取x-csrf-token出现异常..."
        g_var.logger.info("获取x-csrf-token出现异常...")
        return -2

# 发送链接数据
def get_put_data(loginData):
    try:
        data_url = []
        for i in range(20):
            title_and_link = get_new_title_and_link()
            new_data = {"title": title_and_link[0][:10], "link": title_and_link[1]}
            data_url.append(new_data)
        put_data = {
            "profile": {
                "state": None,
                "firstname": loginData['firstname'],
                "lastname": loginData['lastname'],
                "country": None,
                "city": None,
                "zipcode": None,
                "tagline": None,
                "description_html": None,
                "facebook_url": None,
                "youtube_url": None,
                "imdb_url": None,
                "website_url": None,
                "twitter_url": None,
                "links": data_url,
            }
        }
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "获取个人资料页数据出现异常。。。"
        return -2
    return put_data

class IndiegogoCom(object):
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

    def __register_one(self, Session, present_website):
        g_var.logger.info("register...")
        headers = generate_headers(0)
        if headers == -1:
            g_var.logger.info("获取注册headers失败...")
            return -1
        csrf_token = get_csrf(Session, headers)
        if csrf_token == -1:
            return -1
        elif csrf_token == -2:
            return -2

        del headers["Host"]
        del headers["Accept"]
        headers["accept"] = "application/json"
        headers["x-csrf-token"] = csrf_token
        registerData = generate_register_data()
        if registerData == -2:
            g_var.logger.info("未生成正确注册数据...")
            return -2
        url_register = 'https://www.indiegogo.com/accounts.json'
        g_var.logger.info("提交注册中...")
        html = Session.post(url_register, json=registerData, headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html
        # 注册成功与否验证
        if html.status_code not in [200, 201]:
            g_var.logger.info(html.status_code)
            return -2

        try:
            cookie = str(html.cookies.get_dict())
            success_user = json.loads(html.content)
            sql = "INSERT INTO indiegogo_com(id, firstname, lastname, password, mail) VALUES('" + str(success_user['account']['id']) + \
                  "', '" + success_user['account']['first_name'] + "', '" + success_user['account']['last_name'] + "', '" + \
                  registerData['account']['password'] + "', '" + success_user['account']['email'] + "');"
            last_row_id = MysqlHandler().insert(sql)
            userData = {}
            if last_row_id != -1:
                userData["id"] = last_row_id
                userData["firstname"] = success_user['account']['first_name']
                userData["lastname"] = success_user['account']['last_name']
                userData["cookie"] = cookie
                return userData
            else:
                g_var.ERR_CODE = 2004
                g_var.ERR_MSG = "数据库插入失败..."
                g_var.logger.error("数据库插入失败")
                return 0
        except Exception as e:
            g_var.logger.info(e)
            g_var.ERR_CODE = 2004
            g_var.ERR_MSG = "数据库插入失败..."
            g_var.logger.error("数据库插入失败")
            return 0

    def __login(self, Session, VPN, userInfo):
        g_var.logger.info("login...")
        headers = generate_headers(1)
        if headers == -1:
            g_var.logger.info("获取登录headers失败...")
            return -1

        csrf_token = get_csrf(Session)
        if csrf_token == -1:
            g_var.logger.info("获取x-csrf-token失败...")
            return -1

        headers["x-csrf-token"] = csrf_token
        user_id = userInfo[0]
        data_user = {
            "account": {
                'email': userInfo[4],
                'password': userInfo[3],
            }
        }
        g_var.logger.info("使用账号密码登录...")
        html = Session.post(url_login, headers=headers, json=data_user, timeout=g_var.TIMEOUT)
        if html == -1:
            return -1

        if 'account' not in json.loads(html.text).keys():
            # 如果登录失败将数据库中的status改为异常
            sql = "UPDATE indiegogo_com SET status=1 WHERE id=" + str(user_id) + ";"
            MysqlHandler().update(sql)
            g_var.ERR_CODE = 2003
            g_var.ERR_MSG = "用户无法使用..."
            return 1  # 账号异常，重新取号登录
        cookie = str(html.cookies.get_dict())
        g_var.logger.info(cookie)
        loginSuccessData = {
            'id': user_id,
            'firstname': userInfo[1],
            'lastname': userInfo[2],
            'cookie': cookie,
        }
        return loginSuccessData

    def __personal_data(self, Session, loginData, VPN):
        g_var.logger.info("personal data...")
        headers = generate_headers(2)
        if headers == -1:
            g_var.logger.info("获取登录headers失败...")
            return -1

        g_var.logger.info("正在获取个人资料页数据...")
        url_personal_data = 'https://www.indiegogo.com/individuals/' + str(loginData["id"]) + '/edit'
        html = requests.get(url_personal_data, cookies=eval(loginData['cookie']), headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html

        prove = 'Sign up or Log in | Indiegogo'
        if prove in html.text:
            g_var.logger.info(html.status_code)
            return -2
        res_token = re.findall('name="csrf-token" content="(.*?)"', html.text)
        if res_token == []:
            g_var.logger.info(html.status_code)
            return -2
        return res_token[0]

    def __postMessage(self, Session, loginData, personalData, VPN):
        g_var.logger.info("send link...")
        loginData['token'] = personalData
        headers = generate_headers(3, loginData)
        if headers == -1:
            g_var.logger.info("获取登录headers失败...")
            return -1

        put_data = get_put_data(loginData)
        if put_data == -2:
            g_var.logger.info("获取链接数据失败...")
            return -2

        g_var.logger.info("正在发送个人链接...")
        url_sendLink = 'https://www.indiegogo.com/private_api/profiles/' + str(loginData['id'])
        html = Session.put(url_sendLink, json=put_data, cookies=eval(loginData['cookie']), headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return -1

        if html.status_code == 200:
            g_var.logger.info("链接发送成功！" + loginData["firstname"])
            # 将链接、用户存入indiegogo_com_article表
            url = 'https://www.indiegogo.com/individuals/' + str(loginData['id'])
            sql = "INSERT INTO indiegogo_com_article(url, user_id) VALUES('" + url + "', '" + str(loginData['id']) + "');"
            if g_var.insert_article_lock.acquire():
                last_row_id = MysqlHandler().insert(sql)
                g_var.insert_article_lock.release()
            if last_row_id != -1:
                g_var.logger.info("insert article OK")
            else:
                g_var.logger.error("数据库插入链接错误!")
                return 0
            return loginData
        else:
            g_var.logger.error("链接发送失败！\n" + html.status_code)
            g_var.ERR_CODE = 5000
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "链接发送失败，未知错误!"
            return 0

    def registers(self, present_website, VPN):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1
            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue

            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(Session, present_website)
                if registerData != -1:
                    # registerData != -1说明注册成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    break
                else:
                    self.failed_count = self.failed_count + 1
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    time.sleep(g_var.SLEEP_TIME)
                    continue
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = "连续注册出错，程序停止"
                g_var.logger.error("register:连续注册失败！程序停止")
                break

        g_var.logger.info("g_var.SPIDER_STATUS" + str(g_var.SPIDER_STATUS))
        g_var.logger.info("本线程共成功注册'self.success_count'=" + str(self.success_count) + "个账户")

    def loginAndPostMessage(self, present_website, VPN):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1

            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue

            userInfo = generate_login_data(present_website)
            if userInfo == None:
                g_var.logger.error("数据库中获取用户失败，本线程停止！")
                return {"error": -1}
            # 1、登录
            retry_count = 0
            login_signal = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                loginData = self.__login(Session, VPN, userInfo)
                if loginData == -1:
                    # 登录报错，停止运行
                    g_var.ERR_MSG = "登录出错"
                    self.failed_count = self.failed_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    continue
                elif loginData == 1:
                    # 账号异常，重新取新账号登录
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
                g_var.ERR_MSG = "连续登录出错，程序停止"
                g_var.logger.error("login:连续登录失败！程序停止")
                break

            if login_signal == 1:
                continue
            # 2、获取个人数据
            retry_count = 0
            personal_signal = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                personalData = self.__personal_data(Session, loginData)
                if personalData == -1:
                    g_var.ERR_MSG = "个人数据获取出错"
                    self.failed_count = self.failed_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    continue
                elif personalData == 1:
                    # 账号异常，重新取新账号登录
                    self.failed_count = self.failed_count + 1
                    personal_signal = 1
                    break
                else:
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = "连续登录出错，程序停止"
                g_var.logger.error("login:连续登录失败！程序停止")
                break

            if personal_signal == 1:
                continue

            # 3、发链接
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                status = self.__postMessage(Session, loginData, personalData)
                if status == 0:  # 发链接成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
                elif status == 1:
                    self.failed_count = self.failed_count + 1
                    self.proxy_err_count = self.proxy_err_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    continue
                elif status == -1:
                    # 获取不到链接，程序停止
                    self.failed_count = self.failed_count + 1
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = "连续发链接出错，程序停止"
                g_var.logger.error("连续发链接出错，程序停止")
                break
        g_var.logger.info("成功发送" + str(self.success_count) + "个链接。")

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
            retry_count = 0
            register_signal = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                userData = self.__register_one(Session, present_website)
                if userData == -1:
                    # 失败更换代理
                    g_var.ERR_CODE = 3003
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif userData == -2:
                    # 注册过程中出现失败！
                    g_var.logger.info("注册过程中出现失败！")
                    continue
                elif userData == 0:
                    # 注册成功，但存库失败
                    g_var.logger.info("注册成功,但存库失败！")
                    register_signal = 1
                    break
                else:
                    # 说明注册成功
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("start:连续注册失败！程序停止")
                break

            if register_signal == 1:
                continue

            # 2、获取个人数据
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                personalData = self.__personal_data(Session, userData, VPN)
                if personalData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif personalData == -2:
                    # 获取用户资料过程中出现失败！
                    g_var.logger.info("获取用户资料过程中出现失败！")
                    continue
                else:
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("login:连续登录失败！程序停止")
                break

            # 3、发链接
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                status = self.__postMessage(Session, userData, personalData, VPN)
                if status == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == -2:
                    # 发送链接数据过程中出现失败！
                    g_var.logger.info("发送链接数据过程中出现失败！")
                    continue
                elif status == 0:
                    # 链接数据存库失败
                    g_var.logger.info("注册成功,但存库失败！")
                    register_signal = 1
                    break
                else:
                    self.success_count += 1
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("连续发链接出错，程序停止")
                break
        g_var.logger.info("成功注册账户并发送链接" + str(self.success_count) + "个。")
