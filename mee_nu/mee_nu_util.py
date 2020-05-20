import re
import json
import sys
import random
import threading
import time

import requests
from requests.adapters import HTTPAdapter

from project_utils.project_util import generate_random_string, ip_proxy, get_new_article, MysqlHandler
from project_utils import g_var



def generate_headers(signal: int, loginData: dict={}) -> dict:

    try:
        # user_agent = requests.get(url=g_var.INTERFACE_HOST + "/v1/get/user_agent/", timeout=g_var.TIMEOUT).text
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
        return {"error": -1}

    if signal == 0:
        #使用固定header
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': user_agent,
        }
    elif signal == 1:
        #添加cookie
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': user_agent,
            'cookie': loginData['cookie'],
        }
    return headers


def generate_random_theme() -> str:
    list = ["Blue", "Green", "Grey", "Orange", "White", "Beans", "Bug", "Butterfly", "Cheese", "Chips", "Clover",
            "Fire", "Gargoyle", "GreenTomatoes", "Ireland", "Mountains", "Rosebud", "SaltnPepper", "Sunrise", "Sunset"]
    theme_digit = random.randint(0, len(list)-1)
    return list[theme_digit]


def generate_register_data(present_website: str, captcha_code: str) -> dict:
    # 生成注册数据返回，并存入数据库
    # 只需生成用户名
    username: str = generate_random_string(8, 12)
    password: str = generate_random_string(10, 16)
    theme: str = generate_random_theme()
    # mail: str = get_email(present_website)
    # if mail == "-1":
    #     return {"error": -1}
    mail: str = username + "@mail.com"

    registerData: dict = {
        'form': 'form.register',
        'name': username,
        'password': password,
        'mail': mail,
        'site': username+".mee.nu",
        'sitename': username,
        'theme': theme,
        'captcha': captcha_code,
        'terms_ok': '1',
        'age_ok': '1',
        'register': 'register',
    }

    return registerData


def generate_login_data() -> list:
    # 获取登录数据
    # 定义一个id的全局变量，初始值为-1，如果为-1，就去读一下config.json，获取id值。之后所有登录都是对这个id操作，而不用再去读config.json

    if g_var.USER_ID == -1:
        # 如果g_var.USER_ID == -1，就让第一个线程去config.json中读取id值到全局变量g_var.USER_ID中
        if g_var.login_data_config_lock.acquire():
            if g_var.USER_ID == -1:
                with open(g_var.ENV_DIR+'/mee_nu/config.json', encoding='utf-8') as f:
                    data = json.load(f)
                g_var.USER_ID = data["currentId"]
            g_var.login_data_config_lock.release()
    else:
        pass

    # 从全局变量g_var.USER_ID获取上一个被使用的id，并用这个id去数据库取下一个可用id，在最后主线程结束时，将g_var.USER_ID保存到config.json中
    if g_var.login_data_g_var_lock.acquire():
        sql = "SELECT * FROM mee_nu AS m WHERE m.`id` > " + str(g_var.USER_ID) + " and m.`status` = 0 ORDER BY m.`id` LIMIT 0, 1;"
        userInfo = MysqlHandler().select(sql)
        g_var.logger.info("logindata:"+str(userInfo))

        # 如果userInfo == None，再从头开始取数据
        if userInfo == None:
            g_var.USER_ID = 0
            sql = "SELECT * FROM mee_nu AS m WHERE m.`id` > " + str(g_var.USER_ID) + " and m.`status` = 0 ORDER BY m.`id` LIMIT 0, 1;"
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


def generate_new_article_data() -> dict:

    # 这边连续获取失败就报3004错误
    article = get_new_article()
    if article == -1:
        return {"error": -1}

    articleData = {
        'post': '-1',
        'form': 'post',
        'editor': 'innova',
        'title': article[0],
        'category': 'Example',
        'status': 'Publish',
        'text': article[1],
        'more': '',
        'show.html': '1',
        'show.bbcode': '1',
        'show.smilies': '1',
        'allow.comments': '1',
        'allow.pings': '1',
        'type': 'Post',
        'sticky': '0',
        'date': '',
        'path': '',
        'Save': 'Save'
    }
    return articleData


def get_article_url(Session, username: str):
    # 获取新文章的id
    # http://q4aswgg92.mee.nu/ GET
    url_article = "http://" + username + ".mee.nu/"
    #reponse = urllib.request.urlopen(url=url_article)
    # html = requests.get(url_article).text
    try:
        html = Session.get(url=url_article, timeout=g_var.TIMEOUT).text
    except:
        return -1

    #get_article_list_code = reponse.read().decode()
    pattern = '<a href="(.*?)">Add Comment</a>'
    article_url = re.search(pattern, html)
    # http://q4aswgg92.mee.nu/25132876
    article_url = url_article + article_url.groups()[0]
    return article_url


def identify_captcha_1(present_website: str):
    """
    下载识别字母和数字的验证码
    :param
        Session:Session
        present_website:当前网站名
    :return:
        验证码识别结果
    """

    file_data = {
        "key": (None, g_var.VERIFY_KEY1),
        'file': ('chaptcha.png', open(g_var.ENV_DIR + '/captcha/' + present_website + '/' +
                                      threading.currentThread().name + '.png', 'rb'))
    }
    url_answer = g_var.VERIFY_URL1 + "/in.php"
    try:
        res = requests.post(url=url_answer, files=file_data, timeout=g_var.TIMEOUT).text
    except:
        g_var.ERR_CODE = 2001
        g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "无法连接验证码识别接口"
        g_var.logger.error("无法连接验证码识别接口")
        return -1
    id_code = res.split("|")[1]

    url_code = g_var.VERIFY_URL1 + "/res.php?key=" + g_var.VERIFY_KEY1 + "&action=get&id=" + id_code
    try:
        headers = {
            'Connection': 'close',
        }
        requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
        with requests.get(url=url_code, headers=headers, timeout=g_var.TIMEOUT) as r:
            text = r.text
            if text != -1:
                return text.split("|")[1]
            else:
                return -1
    except:
        g_var.ERR_CODE = 2001
        g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "无法获取验证码识别结果!"
        g_var.logger.error("无法获取验证码识别结果!")
        return -1


class MeeNu(object):
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

    def __register_one(self, Session, present_website: str):
        # 获取验证码
        url_image = 'http://mee.nu/captcha/'

        try:
            g_var.logger.info("获取验证码中...")
            picture = Session.get(url_image, timeout=g_var.TIMEOUT).content
            self.proxy_err_count = 0
        except:
            self.proxy_err_count = self.proxy_err_count + 1
            g_var.logger.info("获取验证码失败")
            return -1

        with open(g_var.ENV_DIR+'/captcha/'+present_website+'/'+threading.currentThread().name+'.png', 'wb') as file:
            file.write(picture)

        # 识别验证码
        captcha_code = identify_captcha_1(present_website)
        if captcha_code == -1:
            g_var.logger.info("识别验证码失败")
            return -1
        g_var.logger.info("captcha_code:" + captcha_code)

        headers = generate_headers(0)
        if headers == {"error": -1}:
            g_var.logger.info("获取headers失败")
            return -1
        registerData = generate_register_data(present_website, captcha_code)
        if registerData == {"error": -1}:
            g_var.logger.info("获取注册邮箱失败")
            return -1

        url_register = 'https://mee.nu/'
        try:
            g_var.logger.info("提交注册中...")
            html = Session.post(url_register, headers=headers, data=registerData, timeout=g_var.TIMEOUT).text
            self.proxy_err_count = 0
        except:
            g_var.logger.error("提交注册信息超时")
            self.proxy_err_count = self.proxy_err_count + 1
            return -1

        # result中包含"Thank you for registering"，则表示注册成功。注册成功，将数据保存到数据库
        sucsess_sign = "Thank you for registering"
        if sucsess_sign in html:
            self.captcha_err_count = 0
            sql = "INSERT INTO mee_nu(username, password, mail, status) VALUES('" + registerData['name'] + \
                  "', '" + registerData['password'] + "', '" + registerData['mail'] + "', '" + str(0) + "');"
            last_row_id = MysqlHandler().insert(sql)
            if last_row_id != -1:
                registerData["user_id"] = last_row_id
                return registerData
            else:
                g_var.logger.error("数据库插入失败")
                return -1
        else:
            g_var.logger.info("验证码错误或邮箱名重复!")
            self.captcha_err_count = self.captcha_err_count + 1
            return -1

    def __login(self, Session, VPN, userInfo) -> dict:
        # 从传入的userInfo中判断是否包含cookie，有cookie直接跳过登录流程，
        # 没有cookie或cookie过期再执行登录流程

        # 判断用户信息中是否包含cookie
        if userInfo[5] != None and userInfo[5] != "":
            # userInfo[5]保存cookie值，如果cookie不为空，则使用cookie
            g_var.logger.info("返回cookie" + userInfo[5])
            user_id = userInfo[0]
            username = userInfo[1]
            Cookie = userInfo[5]
            # 长度为3，loginData包含cookie
            loginData = {
                'id': user_id,
                'name': username,
                'cookie': Cookie
            }
            return loginData
        else:
            # cookie为空，使用账号密码登录
            user_id = userInfo[0]
            username = userInfo[1]
            password = userInfo[2]
            loginData = {
                'form': 'login',
                'redirect': '[page.redirect]',
                'magic.word': 'please',
                'name': username,
                'password': password,
                'sign_in': 'Sign In',
            }

            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1

                url_login = 'https://mee.nu/'
                try:
                    g_var.logger.info("使用账号密码登录...")
                    headers = generate_headers(0)
                    if headers == {"error": -1}:
                        return {"error": -1}
                    html = Session.post(url_login, headers=headers, data=loginData, timeout=g_var.TIMEOUT).text
                    self.proxy_err_count = 0
                    break
                except:
                    g_var.logger.error("账号密码登录超时")
                    self.proxy_err_count = self.proxy_err_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    continue
            if retry_count == g_var.RETRY_COUNT_MAX:
                g_var.SPIDER_STATUS = 3
                g_var.logger.error("连续登录失败！程序停止")
                return {"error": -1}

            login_fail_signal = "Login failed."
            if login_fail_signal in html:
                # 如果登录失败将数据库中的status改为异常
                sql = "UPDATE mee_nu SET status=1 WHERE id=" + str(user_id) + ";"
                MysqlHandler().update(sql)
                return {"error": 1}    # 账号异常，重新取号登录
            else:
                # 如果登录成功，则返回id和username给下一步发新文章
                user_id = userInfo[0]
                # 长度为2，使用账号密码登录的loginData
                loginData = {
                    'id': user_id,
                    'name': loginData['name']
                }
            return loginData

    def __postMessage(self, Session, loginData: dict) -> dict:
        # 根据loginData的长度，长度为2表示账号密码登录，长度为3表示cookie登录
        if len(loginData) == 2:
            # 账号密码登录
            headers = generate_headers(0)
        elif len(loginData) == 3:
            # 使用cookie来发文章，cookie加在header中，伪装登录
            headers = generate_headers(1, loginData)

        article = generate_new_article_data()
        if article == {"error": -1}:
            # 获取不到文章，程序停止
            g_var.SPIDER_STATUS = 3
            return {"error": -1}
        else:
            url_postMessage = 'http://' + loginData['name'] + '.mee.nu/edit/entry/'

            try:
                g_var.logger.info("发送文章中...")
                html = Session.post(url_postMessage, headers=headers, data=article, timeout=g_var.TIMEOUT).text
            except:
                g_var.logger.error("发文章超时!")
                return {"error": 1}

            cookie_failure_signal = "You are not authorised to access this page."
            send_success_signal = "<div class=\"pager\">"
            if cookie_failure_signal in html:
                # 如果cookie失效，将该cookie从数据库中清除，并重新从数据库中获取登录账号密码
                sql = "UPDATE mee_nu SET cookie='' WHERE id=" + str(loginData['id']) + ";"
                status = MysqlHandler().update(sql)
                if status == 0:
                    g_var.logger.info("cookie失效，清除cookie update OK")
                    return {"error": -2}
                else:
                    g_var.logger.error("数据库清除cookie错误!")
                    return {"error": 1}

            elif send_success_signal in html:
                g_var.logger.info("文章发送成功！" + loginData["name"])
                article_url = get_article_url(Session, loginData['name'])
                if article_url == -1:
                    return {"error": 1}

                # 将文章链接、标题、用户存入article表
                sql = "INSERT INTO mee_nu_article(url, keyword, user_id) VALUES('" + article_url + "', '" + article[
                    'title'] + "', '" + str(loginData['id']) + "');"

                if g_var.insert_article_lock.acquire():
                    last_row_id = MysqlHandler().insert(sql)
                    g_var.insert_article_lock.release()

                if last_row_id != -1:
                    g_var.logger.info("insert article OK")
                else:
                    g_var.logger.error("数据库插入文章错误!")
                    return {"error": 1}

                if len(loginData) == 2:
                    # 如果使用账号密码登录文章发送成功，将cookie保存到数据库
                    # 这边如何将cookie存入数据库
                    for item in Session.cookies:
                        cookie_value = item.value

                    sql = "UPDATE mee_nu SET cookie='session_id=" + cookie_value + "' WHERE id=" + str(
                        loginData['id']) + ";"
                    status = MysqlHandler().update(sql)
                    if status == 0:
                        g_var.logger.info("update cookie OK")
                    else:
                        g_var.logger.error("数据库更新cookie错误!")
                        return {"error": 1}
                return {"ok": 0}
            else:
                g_var.logger.error("文章发送失败！\n" + html)
                g_var.ERR_CODE = 5000
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "文章发送失败，未知错误!"
                return {"error": 1}

    def registers(self, present_website: str, VPN: str):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1

            Session = requests.Session()
            # 获取代理设置
            proxies = ip_proxy(VPN)
            if proxies == {"error": -1}:
                self.failed_count = self.failed_count + 1
                continue
            self.failed_count = 0
            Session.proxies = proxies
            # 设置最大重试次数
            Session.mount('http://', HTTPAdapter(max_retries=1))
            Session.mount('https://', HTTPAdapter(max_retries=1))

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

    def loginAndPostMessage(self, VPN: str):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1

            Session = requests.Session()
            # 获取代理设置
            proxies = ip_proxy(VPN)
            if proxies == {"error": -1}:
                self.failed_count = self.failed_count + 1
                continue

            Session.proxies = proxies
            Session.mount('http://', HTTPAdapter(max_retries=1))
            Session.mount('https://', HTTPAdapter(max_retries=1))

            # 从数据库中获取用户信息
            userInfo = generate_login_data()
            if userInfo == None:
                g_var.logger.error("数据库中获取用户失败，本线程停止！")
                return {"error": -1}

            # 1、登录
            login_signal = 0
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1

                loginData = self.__login(Session, VPN, userInfo)
                if loginData == {"error": -1}:
                    # 登录报错，停止运行
                    g_var.ERR_MSG = "登录出错"
                    self.failed_count = self.failed_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    continue
                elif loginData == {"error": 1}:
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
                if status == {"ok": 0}:  # 发文章成功
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
                    # g_var.logger.info("proxies"+str(proxies))
                elif status == {"error": -1}:
                    # 获取不到文章，程序停止
                    self.failed_count = self.failed_count + 1
                    break
                elif status == {"error": -2}:
                    # cookie过期
                    self.failed_count = self.failed_count + 1
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = "连续发文章出错，程序停止"
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
            Session = requests.Session()
            proxies = ip_proxy(VPN)
            if proxies == {"error": -1}:
                self.failed_count = self.failed_count + 1
                continue
            Session.proxies = proxies
            Session.mount('http://', HTTPAdapter(max_retries=1))
            Session.mount('https://', HTTPAdapter(max_retries=1))

            # 1、注册
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(Session, present_website)

                if registerData != -1:     # 说明注册成功
                    break
                else:
                    # 失败更换代理
                    g_var.logger.info("注册失败" + str(registerData))
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    continue
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.logger.error("start:连续注册失败！程序停止")
                break

            # 2、登录
            login_signal = 0
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                # 构造一个userInfo
                userInfo: tuple = (registerData['user_id'], registerData['name'], registerData['password'],
                                   registerData['mail'], '0', "")

                loginData = self.__login(Session, VPN, userInfo)
                if loginData == {"error": -1}:
                    # 登录报错，停止运行
                    g_var.ERR_MSG = "登录中代理错误"
                    self.failed_count = self.failed_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    continue
                elif loginData == {"error": 1}:
                    # 账号异常，重新取新账号登录
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                else:
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                g_var.SPIDER_STATUS = 3
                g_var.logger.error("连续登录失败！程序停止")
                break
            if login_signal == 1:
                continue

            # 3、发文章
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                status = self.__postMessage(Session, loginData)
                if status == {"ok": 0}:  # 发文章成功
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
                    # g_var.logger.info("proxies"+str(proxies))
                elif status == {"error": -1}:
                    # 获取不到文章，程序停止
                    self.failed_count = self.failed_count + 1
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = "连续发文章出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功注册账户并发送文章" + str(self.success_count) + "篇")
