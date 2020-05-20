import re
import json
import string
import sys
import random
import threading
import time

import requests
from requests.adapters import HTTPAdapter
from requests_toolbelt.multipart.encoder import MultipartEncoder

from project_utils.project_util import generate_login_data, ip_proxy, get_new_article, MysqlHandler, get_Session, get_email, \
    generate_random_string, get_new_link
from project_utils import g_var

def generate_headers(signal, csrftoken = None):
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
            "Accept": "*/*",
            "Origin": "https://www.mixcloud.com",
            "Referer": "https://www.mixcloud.com/",
            "Cookie": "csrftoken=" + csrftoken,
            "User-Agent": user_agent,
            "x-csrftoken": csrftoken,
            "X-Requested-With": "XMLHttpRequest",
        }
    elif signal == 1:
        headers = {
            'Accept': 'application/json',
            'Origin': 'https://www.mixcloud.com',
            'Referer': 'https://www.mixcloud.com/settings/profile/',
            'User-Agent': user_agent,
            "x-CSRFToken": csrftoken,
            "X-Requested-With": "XMLHttpRequest",
        }
    return headers

# 获取csrf
def get_csrf(Session):
    try:
        url = 'https://www.mixcloud.com/'
        res = Session.get(url, timeout=g_var.TIMEOUT)
        if res == -1:
            return res
        cookie = res.headers['Set-Cookie']
        csrftoken = re.findall('csrftoken=(.*?);', cookie)
        if not csrftoken:
            g_var.logger.info("未获取到csrftoken...")
            return -2
        return csrftoken[0]
    except:
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取csrftoken出现异常..."
        g_var.logger.info("获取csrftoken出现异常...")
        return -2

class MixcloudCom(object):
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

    def __register_one(self, Session):
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
        g_var.logger.info("register...")
        csrftoken = get_csrf(Session)
        if csrftoken == -1:
            return -1
        elif csrftoken == -2:
            return -2
        headers = generate_headers(0, csrftoken)
        if headers == -1:
            g_var.logger.info("获取注册headers失败...")
            return -1
        try:
            username = generate_random_string(8, 12)
            password = generate_random_string(10, 14)
            email = username + '@hotmail.com'
            multipart_encoder = MultipartEncoder(
                fields={
                    'email': email,
                    'password': password,
                    'username': username,
                    'ch': 'y',
                },
                boundary='----WebKitFormBoundary' + generate_random_string(16, 16, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'),
            )
            headers['Content-Type'] = multipart_encoder.content_type
        except Exception as e:
            g_var.ERR_CODE = 5000
            g_var.ERR_MSG = "注册数据生成中出现异常..."
            g_var.logger.info("注册数据生成中出现异常...")
            g_var.logger.info(e)
            return -2

        url_register = 'https://www.mixcloud.com/authentication/email-register/'
        g_var.logger.info("提交注册中...")
        html = Session.post(url_register, data= multipart_encoder, headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html
        try:
            text = json.loads(html.text)
            if not text['success']:
                g_var.logger.info(text)
                return -2
        except Exception as e:
            g_var.logger.info(e)
            g_var.ERR_CODE = 5000
            g_var.ERR_MSG = "此次注册未完成安全检查(IP问题)..."
            g_var.logger.error("此次注册未完成安全检查(IP问题)")
            return -2

        try:
            cookie = html.headers['Set-Cookie']
            csrftoken = re.findall('csrftoken=(.*?);', cookie)
            c = re.findall('secure, c=(.*?);', cookie)
            sql = "insert into mixcloud_com (id, username, password, mail) values('{0}', '{1}', '{2}', '{3}');" \
                .format(str(text['authentication']['currentUser']['id']), username, password, email)
            last_row_id = MysqlHandler().insert(sql)
            userData = {}
            if last_row_id != -1:
                userData["id"] = last_row_id
                userData["username"] = username
                userData["password"] = password
                userData["csrftoken"] = csrftoken[0]
                userData["c"] = c[0]
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

    def __login(self, Session, present_website, VPN, userInfo):
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

    def __postMessage(self, Session, loginData, present_website):
        """
        发文章
        Args:
            Session：Session对象
            loginData：用户信息，包括user_id,username,password,cookie
            present_website：当前网站名，用于数据库表名
        Returns:
            成功返回状态值：loginData
            失败返回状态值：
                -1:表示requests请求页面失败，需要更换代理
                -2:页面发生改变，获取不到页面上的一些token值
                0:数据库插入更新等错误
        """
        g_var.logger.info("post link...")
        headers = generate_headers(1, loginData['csrftoken'])
        if headers == -1:
            g_var.logger.info("获取注册headers失败...")
            return -1
        cookie = 'csrftoken=' + loginData['csrftoken'] + '; c=' + loginData['c']
        headers['Cookie'] = cookie
        biog = get_new_link()
        if biog == -1:
            return -1
        try:
            num = string.ascii_letters + string.digits
            i = random.choice(num)
            variables = '{"input_0":{"country":null,"birthyear":null,"menuItems":[{"itemType":"STREAM","hidden":false,"inDropdown":false},{"itemType":"UPLOADS","hidden":false,"inDropdown":false},{"itemType":"FAVORITES","hidden":false,"inDropdown":false},{"itemType":"LISTENS","hidden":false,"inDropdown":false}],"displayName":"' + loginData['username'] + '","biog":"' + biog + '","city":null,"gender":null,"brandedProfile":{"backgroundTiled":null,"backgroundColor":null},"clientMutationId":"' + i + '"}}'
            multipart_encoder = MultipartEncoder(
                fields={
                    'id': i,
                    'query': 'mutation ChangeProfileMutation($input_0:ChangeProfileMutationInput!) {changeProfile(input:$input_0) {viewer {me {percentageComplete,displayName,biog,city,countryCode,country,gender,birthYear,brandedProfile {backgroundTiled,backgroundPicture {urlRoot},backgroundColor},picture {urlRoot,primaryColor},coverPicture {urlRoot,primaryColor},_profileNavigation3Jqt8o:profileNavigation(showHidden:true) {menuItems {__typename,...F0,...F1,...F2}},profileNavigation {menuItems {__typename,...F0,...F1,...F2}},id},id},clientMutationId}} fragment F0 on NavigationItemInterface {inDropdown,__typename} fragment F1 on HideableNavigationItemInterface {hidden,__typename} fragment F2 on PlaylistNavigationItem {count,playlist {id,name,slug}}',
                    'variables': variables,
                    'picture': 'undefined',
                    'coverPicture': 'undefined',
                    'backgroundPicture': 'undefined',
                    '_onProgress': 'function(e,n){t.forEach(function(t){t(e,n)})}',
                    '_aborter': '[object Object]',
                    '_useUploadServers': 'undefined',
                },
                boundary='------WebKitFormBoundary' + generate_random_string(16, 16, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'),
            )
            headers['Content-Type'] = multipart_encoder.content_type
        except Exception as e:
            g_var.ERR_CODE = 5000
            g_var.ERR_MSG = "推送个人链接数据生成中出现异常..."
            g_var.logger.info("推送个人链接数据生成中出现异常...")
            g_var.logger.info(e)
            return -2

        url_link = 'https://www.mixcloud.com/graphql'
        g_var.logger.info("推送链接中...")
        html = Session.post(url_link, data=multipart_encoder, headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html
        if biog in html.text:
            g_var.logger.info("链接发送成功！" + loginData["username"])
            # 将链接、用户存入mixcloud_com_article表
            url = 'https://www.mixcloud.com/' + loginData['username'] + '/'
            sql = "INSERT INTO mixcloud_com_article(url, user_id) VALUES('" + url + "', '" + str(loginData['id']) + "');"
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
            g_var.logger.error("链接发送失败！..." + str(html.status_code))
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
                    g_var.logger.info("代理错误")
                    self.proxy_err_count = self.proxy_err_count + 1
                    proxies = ip_proxy(VPN)
                    if proxies == {"error": -1}:
                        g_var.logger.info("获取代理错误")
                        self.failed_count = self.failed_count + 1
                    Session.proxies = proxies
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
                g_var.ERR_MSG = "连续注册出错，程序停止"
                g_var.logger.error("连续注册失败！程序停止")
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
                    g_var.ERR_MSG = "登录出错"
                    self.failed_count = self.failed_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    if proxies == {"error": -1}:
                        self.failed_count = self.failed_count + 1
                        continue
                    Session.proxies = proxies
                    continue
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
                g_var.ERR_MSG = "连续登录出错，程序停止"
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
                    self.failed_count = self.failed_count + 1
                    self.proxy_err_count = self.proxy_err_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    if proxies == {"error": -1}:
                        self.failed_count = self.failed_count + 1
                        continue
                    Session.proxies = proxies
                    # g_var.logger.info("proxies"+str(proxies))
                elif status == -2:
                    # 返回值为-1，某些必须停止的错误，程序停止
                    self.failed_count = self.failed_count + 1
                    g_var.SPIDER_STATUS = 3
                    break
                elif status == -3:
                    # 返回值为-1，数据库错误
                    self.failed_count = self.failed_count + 1
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
            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue
            retry_count = 0
            register_signal = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                userData = self.__register_one(Session)
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

            # 2、发链接
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                status = self.__postMessage(Session, userData, present_website)
                if status == -1:
                    g_var.ERR_CODE = 3003
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == 0:
                    # 链接数据存库失败
                    self.failed_count = self.failed_count + 1
                    continue
                else:  # 发链接成功
                    self.success_count += 1
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续发链接出错，程序停止"
                g_var.logger.error("连续发链接出错，程序停止")
                break
        g_var.logger.info("成功注册账户并发送链接" + str(self.success_count) + "个。")
