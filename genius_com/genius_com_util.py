import re
import json
import sys
import random
import threading
import time
import requests
from project_utils import requestsW
from requests.adapters import HTTPAdapter

from project_utils.project_util import generate_random_string, ip_proxy, MysqlHandler, get_new_link, get_Session
from project_utils import g_var

def generate_headers(signal, csrf_token=None, rapgenius_session=None, loginData=None):
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
        #注册headers
        headers = {
            'Host': 'genius.com',
            'Origin': 'https://genius.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://genius.com/signup',
            'Cookie': '_csrf_token='+csrf_token+ '; _rapgenius_session='+rapgenius_session,
            'User-Agent': user_agent,
        }
    elif signal == 1:
        #登陆headers
        headers = {
            'Host': 'genius.com',
            'Origin': 'https://genius.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://genius.com/login',
            'Cookie': '_csrf_token='+csrf_token+ '; _rapgenius_session='+rapgenius_session,
            'User-Agent': user_agent,
        }
    elif signal == 2:
        # 修改个人资料headers
        headers = {
            'Host': 'genius.com',
            'Origin': 'https://genius.com',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Referer': 'https://genius.com/'+loginData['name'],
            'X-CSRF-Token': loginData['authenticity_token'],
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': '_rapgenius_session='+loginData['rapgenius_session'],
            'User-Agent': user_agent,
        }
    return headers

def generate_register_data(authenticity_token):
    # 生成注册数据返回
    name = generate_random_string(8, 12)
    email = name + '@hotmail.com'
    password = generate_random_string(10, 14)
    registerData = {
        'authenticity_token': authenticity_token,
        'user[login]': name,
        'user[email]': email,
        'user[password]': password,
        'commit': 'Create Account',
    }
    return registerData

# 注册：获取authenticity_token、_csrf_token、_rapgenius_session值
def get_authenticity_token_signup():
    try:
        url = 'https://genius.com/signup'
        res = requestsW.get(url, proxies=ip_proxy('ch'), timeout=g_var.TIMEOUT, vpn='ch')
        if res == -1:
            return 0, 0, 0
        token_list = re.findall('name="authenticity_token" type="hidden" value="(.*?)" /></div>', res.text)
        res_headers = json.dumps(dict(res.headers))
        csrf_token_list = re.findall('_csrf_token=(.*?);', res_headers)
        session_list = re.findall('_rapgenius_session=(.*?);', res_headers)
        if not token_list or not csrf_token_list or not session_list:
            g_var.ERR_CODE = "2001"
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "获取注册authenticity_token值或_csrf_token值或_rapgenius_session值失败。。。"
            g_var.logger.info('获取注册authenticity_token值或_csrf_token值或_rapgenius_session值失败。。。')
            return -1, -1, -1
    except:
        g_var.logger.info("访问注册页失败。。。")
        return -1, -1, -1
    return token_list[0], csrf_token_list[0], session_list[0]

# 登录：获取authenticity_token、_csrf_token、_rapgenius_session值
def get_authenticity_token_login(Session):
    try:
        url = 'https://genius.com/login'
        res = Session.get(url, timeout=g_var.TIMEOUT)
        token_list = re.findall('name="authenticity_token" type="hidden" value="(.*?)" /></div>', res.text)
        res_headers = json.dumps(dict(res.headers))
        csrf_token_list = re.findall('_csrf_token=(.*?);', res_headers)
        session_list = re.findall('_rapgenius_session=(.*?);', res_headers)
        if not token_list or not csrf_token_list or not session_list:
            g_var.ERR_CODE = "2001"
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "获取登录authenticity_token值或_csrf_token值或_rapgenius_session值失败。。。"
            g_var.logger.info('获取注册authenticity_token值或_csrf_token值或_rapgenius_session值失败。。。')
            return -1, -1, -1
    except Exception as e:
        g_var.logger.info(e)
        g_var.logger.info("访问登录页失败。。。")
        return -1, -1, -1
    return token_list[0], csrf_token_list[0], session_list[0]

def generate_login_data():
    # 获取登录数据
    # 定义一个id的全局变量，初始值为-1，如果为-1，就去读一下config.json，获取id值。之后所有登录都是对这个id操作，而不用再去读config.json

    if g_var.USER_ID == -1:
        # 如果g_var.USER_ID == -1，就让第一个线程去config.json中读取id值到全局变量g_var.USER_ID中
        if g_var.login_data_config_lock.acquire():
            if g_var.USER_ID == -1:
                with open(g_var.ENV_DIR+'/genius_com/config.json', encoding='utf-8') as f:
                    data = json.load(f)
                g_var.USER_ID = data["currentId"]
            g_var.login_data_config_lock.release()
    else:
        pass

    # 从全局变量g_var.USER_ID获取上一个被使用的id，并用这个id去数据库取下一个可用id，在最后主线程结束时，将g_var.USER_ID保存到config.json中
    if g_var.login_data_g_var_lock.acquire():
        sql = "SELECT * FROM genius_com AS g WHERE g.`id` > " + str(g_var.USER_ID) + " and g.`status` = 0 ORDER BY g.`id` LIMIT 0, 1;"
        userInfo = MysqlHandler().select(sql)
        g_var.logger.info("logindata:"+str(userInfo))

        # 如果userInfo == None，再从头开始取数据
        if userInfo == None:
            g_var.USER_ID = 0
            sql = "SELECT * FROM genius_com AS g WHERE g.`id` > " + str(g_var.USER_ID) + " and g.`status` = 0 ORDER BY g.`id` LIMIT 0, 1;"
            userInfo = MysqlHandler().select(sql)
            g_var.logger.info(userInfo)
            # 如果再次取还是为空，则说明数据库中没有可用账号
            if userInfo == None:
                g_var.logger.error("当前数据库账号池为空，或所有账号状态异常")
                g_var.ERR_CODE = 2003
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "数据库中没有可用用户，请先注册后再启动本程序！"
                # 数据库中没有可用用户，则停止程序
                g_var.SPIDER_STATUS = 3  # 停止定时发送状态线程
            else:
                g_var.USER_ID = userInfo[0]
        else:
            g_var.USER_ID = userInfo[0]

        g_var.login_data_g_var_lock.release()
        return userInfo

def generate_new_link_data():
    # 这边连续获取失败就报3004错误
    try:
        links = []
        for i in range(20):
            link = get_new_link()
            links.append(link)
        if links == -1:
            return -1
        linkMore = '\n'.join(links)
        linkData = {"user": {"about_me": linkMore}}

        return linkData
    except Exception as e:
        g_var.logger.info(e)
        g_var.logger.info('超链接数据拼接出现异常...')
        return -1

class GeniusCom(object):

    def __init__(self, assignment_num):
        self.assignment_num = assignment_num  # 分配任务的数量
        self.now_count = 0  # 本线程执行总数
        self.success_count = 0  # 本线程执行成功数
        self.register_success_count = 0  # start方法中register成功数
        self.login_and_post_success_count = 0  # start方法中login_and_post成功数
        self.failed_count = 0  # 本线程执行失败数
        self.proxy_err_count = 0  # 本线程代理连接连续失败数
        self.captcha_err_count = 0  # 当前验证码识别连续错误次数

    def __monitor_status(self):
        if g_var.SPIDER_STATUS == 3 or self.failed_count > g_var.ERR_COUNT:
            g_var.logger.error("g_var.SPIDER_STATUS=3 or self.failed_count > g_var.ERR_COUNT，本线程将停止运行")
            g_var.logger.info("self.failed_count="+str(self.failed_count))
            return -1
        return 0

    def __register_one(self):
        g_var.logger.info("register。。。")
        # 获取authenticity_token、_csrf_token、_rapgenius_session值
        authenticity_token, csrf_token, rapgenius_session = get_authenticity_token_signup()
        if authenticity_token == 0:
            return -1
        elif authenticity_token == -1:
            return -2
        # 获取headers
        headers = generate_headers(0, csrf_token, rapgenius_session)
        if headers == -1:
            g_var.logger.info("获取headers失败。。。")
            return -2

        # 注册数据
        registerData = generate_register_data(authenticity_token)
        url_register = 'https://genius.com/account'
        g_var.logger.info("提交注册中。。。")
        html = requestsW.post(url_register, proxies=ip_proxy("ch") , data=registerData, headers=headers, timeout=g_var.TIMEOUT, vpn='ch')
        if html == -1:
            return html

        # 注册成功验证
        user_id_list = re.findall('CURRENT_USER = {"id":(.*?),"login":', html.text)
        if not user_id_list:
            g_var.logger.info(html.status_code)
            return -2
        session_list = re.findall('_rapgenius_session=(.*?);', html.headers['Set-Cookie'])
        # 插入数据库
        try:
            sql = "INSERT INTO genius_com(username, password, mail, user_id) VALUES('" + registerData['user[login]'] + \
                  "', '" + registerData['user[password]'] + "', '" + registerData['user[email]'] + "', '" + user_id_list[0] +"');"
            last_row_id = MysqlHandler().insert(sql)
            if last_row_id != -1:
                registerData["id"] = last_row_id
                registerData["user_id"] = user_id_list[0]
                registerData["name"] = registerData['user[login]']
                registerData["rapgenius_session"] = session_list[0]
                return registerData
            else:
                g_var.ERR_CODE = 2004
                g_var.ERR_MSG = "数据库插入用户注册数据失败..."
                g_var.logger.error("数据库插入用户注册数据失败...")
                return 0
        except Exception as e:
            g_var.logger.info(e)
            g_var.ERR_CODE = 2004
            g_var.ERR_MSG = "数据库插入用户注册数据出现异常..."
            g_var.logger.error("数据库插入用户注册数据出现异常...")
            return 0

    def __login(self, Session, VPN, userInfo):
        g_var.logger.info('login。。。。。。')
        # 获取authenticity_token、_csrf_token、_rapgenius_session值
        authenticity_token, csrf_token, rapgenius_session = get_authenticity_token_login(Session)
        if authenticity_token == -1:
            g_var.logger.info('登陆账号前未获取到authenticity_token值或_csrf_token值或_rapgenius_session值。。。')
            return -1
        # 获取headers
        headers = generate_headers(1, csrf_token, rapgenius_session)
        if headers == -1:
            g_var.logger.info("获取headers失败。。。")
            return -1

        username = userInfo[1]
        password = userInfo[2]
        loginData = {
            'authenticity_token': authenticity_token,
            'user_session[login]': userInfo[1],
            'user_session[password]': userInfo[2],
            'user_session[remember_me]': '0',
            'user_session[remember_me]': '1',
        }
        retry_count = 0
        while retry_count < g_var.RETRY_COUNT_MAX:
            retry_count = retry_count + 1
            url_login = 'https://genius.com/user_session'
            try:
                g_var.logger.info("使用账号密码登录...")
                html = Session.post(url=url_login, headers=headers, data=loginData, timeout=g_var.TIMEOUT)
                break
            except Exception as e:
                g_var.logger.error(e)
                g_var.logger.error("账号密码登录超时")
                g_var.ERR_CODE = "5000"
                g_var.ERR_MSG = "登录出错|_|" + str(e)
                continue
        if retry_count == g_var.RETRY_COUNT_MAX:
            g_var.SPIDER_STATUS = 3
            g_var.logger.error("连续登录失败！程序停止")
            return -1

        prove = "Looks like the site is more popular than we thought! We're going to send you on your way in just a sec."
        if prove in html.text:
            g_var.ERR_CODE = "2001"
            g_var.ERR_MSG = '代理异常。。。'
            g_var.logger.info("使用账号密码登录被识别为机器人登录，需要更换代理...")
            return -1
        user_id_list = re.findall('CURRENT_USER = {"id":(.*?),"login":', html.text)
        g_var.logger.info(user_id_list)
        if not user_id_list:
            # 如果登录失败将数据库中的status改为异常
            sql = "UPDATE genius_com SET status=1 WHERE id=" + str(id) + ";"
            MysqlHandler().update(sql)
            return 1
        session_list = re.findall('_rapgenius_session=(.*?);', html.headers['Set-Cookie'])
        g_var.logger.info(session_list)
        if not session_list:
            # 如果登录失败将数据库中的status改为异常
            sql = "UPDATE genius_com SET status=1 WHERE id=" + str(id) + ";"
            MysqlHandler().update(sql)
            return 1    # 账号异常，重新取号登录

        # 返回使用账号密码登录的loginData
        loginSuccessData = {
            'id': userInfo[0],
            'user_id': user_id_list[0],
            'name': loginData['user_session[login]'],
            'authenticity_token': authenticity_token,
            'rapgenius_session': session_list[0]
        }
        return loginSuccessData

    def __postMessage(self, loginData):

        # 获取headers
        headers = generate_headers(2, loginData=loginData)
        if headers == -1:
            g_var.logger.info("获取headers失败。。。")
            return -1

        data = generate_new_link_data()
        g_var.logger.info(data)
        if data == -1:
            # 获取不到链接，程序停止
            g_var.SPIDER_STATUS = 3
            return -1

        url_postLink = 'https://genius.com/api/users/'+str(loginData['user_id'])+'?text_format=html,markdown'
        g_var.logger.info("发送链接中...")
        res = requestsW.put(url_postLink, proxies=ip_proxy("ch") , headers=headers, json=data, timeout=g_var.TIMEOUT, vpn='ch')
        if res == -1:
            return res

        if res.status_code == 200:
            g_var.logger.info("链接发送成功！" + loginData["name"])
            # 将链接、用户id存入article表
            url = 'https://genius.com/' + loginData["name"]
            sql = "INSERT INTO genius_com_article(url, user_id) VALUES('" + url + "', '" + str(loginData['id']) + "');"
            if g_var.insert_article_lock.acquire():
                last_row_id = MysqlHandler().insert(sql)
                g_var.insert_article_lock.release()
                if last_row_id != -1:
                    g_var.logger.info("insert article OK")
                else:
                    g_var.logger.error("数据库插入连接数据错误!")
                    return 0
            return loginData
        else:
            g_var.logger.error("链接发送失败！" + str(res.status_code))
            g_var.ERR_CODE = 5000
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "链接发送失败，未知错误!"
            return 0

    def registers(self, present_website, VPN):
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

            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(Session)
                if registerData != -1:
                    # registerData != -1说明注册成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    break
                else:
                    g_var.logger.info("更换代理...")
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

    def loginAndPostMessage(self, VPN):
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

            userInfo = generate_login_data()
            # 从数据库中获取用户信息
            if userInfo == None:
                g_var.logger.error("数据库中获取用户失败，本线程停止！")
                return {"error": -1}
            # 1、登录
            login_signal = 0
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                g_var.logger.info('userInfo。。。。。。')
                retry_count = retry_count + 1
                loginData = self.__login(Session, VPN, userInfo)
                if loginData == -1:
                    # 登录报错，停止运行
                    g_var.logger.info('login error。。。。。。')
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
            # 2、发文章
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                status = self.__postMessage(Session, loginData)
                if status == {"ok": 0}:  # 发链接成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
                elif status == {"error": 1}:
                    self.failed_count = self.failed_count + 1
                    self.proxy_err_count = self.proxy_err_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                elif status == {"error": -1}:
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
            # 1、注册
            retry_count = 0
            register_signal = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one()
                if registerData == -1:
                    # 失败更换代理
                    g_var.ERR_CODE = 3003
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif registerData == -2:
                    # 注册过程中出现失败！
                    g_var.logger.info("注册过程中出现失败！")
                    continue
                elif registerData == 0:
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

            # 2、发链接
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                status = self.__postMessage(registerData)
                if status == -1:
                    g_var.ERR_CODE = 3003
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == 0:
                    # 链接数据存库失败
                    sself.failed_count = self.failed_count + 1
                    continue
                else:  # 发链接成功
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
