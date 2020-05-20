import re
import json
import sys
import random
import threading
import time
import uuid
import requests
from project_utils import requestsW
from requests.adapters import HTTPAdapter

from project_utils.project_util import generate_login_data, ip_proxy, get_new_article, MysqlHandler, \
    get_email, google_captcha, generate_random_string
from project_utils import g_var


def generate_headers(signal, accessToken=None, item_id=None):
    try:
        headers = {
            'Connection': 'close',
        }
        requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
        with requests.get(url=g_var.INTERFACE_HOST + "/v1/get/user_agent/", headers=headers,
                          timeout=g_var.TIMEOUT) as r:
            user_agent = r.text
    except:
        g_var.ERR_CODE = 2005
        g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "user_agent获取失败!"
        g_var.logger.error("user_agent获取失败!")
        return -1

    if signal == 0:
        # 使用固定header
        headers = {
            'Host': 'login.ex.co',
            'Accept': 'application/json',
            'User-Agent': user_agent,
            'Content-Type': 'application/json',
            'Origin': 'https://login.ex.co',
        }
    elif signal == 1:
        # 添加cookie
        headers = {
            'Host': 'login.ex.co',
            'Accept': 'application/json',
            'User-Agent': user_agent,
            'Content-Type': 'application/json',
            'Origin': 'https://login.ex.co',
            'Referer': 'https://login.ex.co/additional-data',
            'Cookie': 'PlaybuzzToken=' + accessToken,
        }
    elif signal == 2:
        # 发布文章
        headers = {
            'Host': 'editor.ex.co',
            'Accept': 'application/json',
            'User-Agent': user_agent,
            'Content-Type': 'application/json',
            'Origin': 'https://app.ex.co',
            'Referer': 'https://app.ex.co/create/item/' + item_id + '/complete',
            'Cookie': 'PlaybuzzToken=' + accessToken,
        }
    return headers

# 获取k值，用于得到人机身份验证返回码
def get_googlekey():
    try:
        url = 'https://login.ex.co/signup'
        res = requestsW.get(url)
        k_value = re.findall("window.pbRecaptchaSiteKey = '(.*?)';", res.text)
        if k_value:
            return k_value[0]
        else:
            g_var.ERR_CODE = 2001
            g_var.ERR_MSG = "使用当前代理无法获取googlekey值..."
            g_var.logger.error("使用当前代理无法获取googlekey值...")
            return -1
    except Exception as e:
        g_var.ERR_CODE = 2005
        g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "googlekey值出现异常!"
        g_var.logger.error("googlekey值出现异常!")
        g_var.logger.info(e)
        return -1

def generate_register_data(email_info, captcha_value):
    # 生成注册数据返回
    try:
        name = generate_random_string(10, 12)
        password = generate_random_string(10, 14)
        registerData = {
            "firstName": name,
            "lastName": "",
            "email": email_info[0],
            "password": password,
            "approvedEmailMarketing": False,
            "captchaResponse": captcha_value,
        }
    except Exception as e:
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "注册数据生成中出现异常..."
        g_var.logger.info("注册数据生成中出现异常...")
        g_var.logger.info(e)
        return -1
    return registerData

#  获取文章内容
def get_article():
    try:
        article = get_new_article()
        title = article[0]
        text_content = article[1]
        text_sub = re.sub('<a href="(.*?)" target="_blank">([\s\S]*?)</a>', "|_|[md5url]|_|", text_content)
        content = re.sub(r'<.*?>', '', text_sub)
        final_content = content.split('|_|')
        a_list = re.findall('<a href="(.*?)" target="_blank">([\s\S]*?)</a>', text_content)
        a_res = []
        # 获取超链接及相对应的文本内容
        for a in a_list:
            a = list(a)
            a_sub = re.sub(r'<.{0,5}>', '', a[1])
            a_split = a_sub.split()
            a[1] = a_split[0]
            a_res.append(a)
        ops = []
        l = len(final_content)
        z = 0
        for s in range(l):
            if final_content[s] != '[md5url]':
                data = {
                    'insert': final_content[s]
                }
            else:
                data = {
                    "attributes": {
                        "link": a_res[z][0]
                    },
                    "insert": a_res[z][1]
                }
                z += 1
            ops.append(data)
        return title, ops
    except Exception as e:
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取对应文章格式内容出现异常..."
        g_var.logger.info("获取对应文章格式内容出现异常...")
        g_var.logger.info(e)
        return -1, -1

def generate_post_article_data(loginData, item_id, sections_id, captcha_value, title, ops):
    # 生成注册数据返回
    try:
        article_data = {
            "item":
                {
                    "id": item_id,
                    "tags": [],
                    "thumbnail": {},
                    "socialThumbnail": {},
                    "locale": "en-US",
                    "status": "draft",
                    "translation": {"enabled": False},
                    "sponsored": {"enabled": False},
                    "permission": {"view": "only-direct-link"},
                    "formatId": "story",
                    "cover": {},
                    "showItemInfo": False,
                    "channelId": loginData['userId'],  # 注册生成的用户id, 用户登陆返回信息中有
                    "sections": [[{
                        "title": {"ops": [{"insert": title}]},
                        "text": {"ops": ops},
                        "id": sections_id,
                        "type": "paragraphSection",
                        "list": {"type": "none", "backgroundColor": "#009CFF", "color": "#fff", "enableVoting": True,
                                 "enableDownVoting": False}
                    }]]
                },
            "recaptchaToken": captcha_value,
            "defaults": {
                "title": title,
                "cover": {
                    "mediaType": "image",
                    "originalImageUrl": "https://img.playbuzz.com/image/upload/v1485701643/rrptnddw80syrlipfm4r.jpg",
                    "width": 1297,
                    "height": 688,
                    "isAnimated": False,
                    "url": "https://img.playbuzz.com/image/upload/c_crop,h_688,w_1297,x_15,y_0/v1485701643/rrptnddw80syrlipfm4r.jpg",
                    "selected": {"x": 15, "y": 0, "x2": 1312, "y2": 688, "w": 1297, "h": 688}},
                "socialThumbnail": {
                    "mediaType": "image",
                    "originalImageUrl": "https://img.playbuzz.com/image/upload/v1485701643/rrptnddw80syrlipfm4r.jpg",
                    "width": 1297,
                    "height": 688,
                    "isAnimated": False,
                    "url": "https://img.playbuzz.com/image/upload/v1485701643/rrptnddw80syrlipfm4r.jpg",
                    "selected": {"x": 15, "y": 0, "x2": 1312, "y2": 688, "w": 1297, "h": 688}
                },
                "thumbnail": {
                    "mediaType": "image",
                    "originalImageUrl": "https://img.playbuzz.com/image/upload/v1485701643/rrptnddw80syrlipfm4r.jpg",
                    "width": 1297,
                    "height": 688,
                    "isAnimated": False,
                    "url": "https://img.playbuzz.com/image/upload/v1485701643/rrptnddw80syrlipfm4r.jpg",
                    "selected": {"x": 15, "y": 0, "x2": 1312, "y2": 688, "w": 1297, "h": 688}
                }
            }
        }
    except Exception as e:
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "注册数据生成中出现异常..."
        g_var.logger.info("注册数据生成中出现异常...")
        g_var.logger.info(e)
        return -1
    return article_data

class PlaybuzzCom(object):
    def __init__(self, assignment_num):
        self.assignment_num = assignment_num  # 分配任务的数量
        self.now_count = 0  # 本线程执行总数
        self.success_count = 0  # 本线程执行成功数
        self.register_success_count = 0  # start方法中register成功数
        self.login_and_post_success_count = 0  # start方法中login_and_post成功数
        self.failed_count = 0  # 本线程执行失败数
        self.captcha_err_count = 0  # 当前验证码识别连续错误次数

    def __monitor_status(self):
        if g_var.SPIDER_STATUS == 3 or self.failed_count > g_var.ERR_COUNT:
            g_var.logger.error("g_var.SPIDER_STATUS=3 or self.failed_count > g_var.ERR_COUNT，本线程将停止运行")
            g_var.logger.info("self.failed_count=" + str(self.failed_count))
            return -1
        return 0

    def __register_one(self, present_website, email_info, googlekey):
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
        url_register_one = 'https://login.ex.co/api/signup'

        headers = generate_headers(0)
        headers['Referer'] = 'https://login.ex.co/signup'
        if headers == -1:
            g_var.logger.info("获取headers失败...")
            return -1

        captcha_value = google_captcha("", googlekey, url_register_one)
        if captcha_value == -1:
            return -2
        registerData = generate_register_data(email_info, captcha_value)

        g_var.logger.info("提交注册中...")
        html = requestsW.post(url_register_one, proxies=ip_proxy("en"), json=registerData, headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html

        if '"success":true' not in html.text:
            g_var.logger.info('注册失败。。。')
            g_var.logger.info(html.text)
            return -2
        accessToken = re.findall('accessToken":"(.*?)"}}', html.text)[0]
        userId = re.findall('"UserId":"(.*?)",', html.text)[0]
        headers = generate_headers(1, accessToken)
        if headers == -1:
            g_var.logger.info("获取第二步注册验证的headers失败...")
            return -1

        company = generate_random_string(10, 12)
        data = {
            "company": company,
            "industryType": 'Freelancer',
            "companySize": "",
            "userIntent": ""
        }
        url_register_two = 'https://login.ex.co/api/additional-data'
        g_var.logger.info("第二步提交注册中...")
        html = requestsW.post(url_register_two, proxies=ip_proxy("en"), json=data, headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html
        if html.text != '{"success":true}':
            g_var.logger.info('第二步注册失败。。。')
            g_var.logger.info(html.text)
            return -2
        # 将注册的账户写入数据库
        try:
            sql = "INSERT INTO " + present_website + "(username, password, mail, cookie, userId) VALUES('" + \
                  registerData['firstName'] + "', '" + registerData['password'] + "', '" + email_info[0] + "', '" + accessToken + "', '" + str(
                userId) + "');"
            last_row_id = MysqlHandler().insert(sql)
            g_var.logger.info(last_row_id)
            if last_row_id != -1:
                g_var.logger.info('注册成功！' + registerData['firstName'])
                registerData["id"] = last_row_id
                registerData["cookie"] = accessToken
                registerData["userId"] = str(userId)
                return registerData
            else:
                g_var.ERR_CODE = 2004
                g_var.ERR_MSG = "数据库插入用户注册数据失败..."
                g_var.logger.error("数据库插入用户注册数据失败...")
                return 0
        except Exception as e:
            g_var.logger.info(e)
            g_var.ERR_CODE = 2004
            g_var.ERR_MSG = "数据库插入用户注册数据异常..."
            g_var.logger.error("数据库插入用户注册数据异常...")
            return 0

    def __login(self, present_website, VPN, userInfo, googlekey):
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
            g_var.logger.info('login, cookie....')
            # userInfo[5]保存cookie值，如果cookie不为空，则使用cookie
            loginData = {
                'id': userInfo[0],
                'firstName': userInfo[1],
                'password': userInfo[2],
                'cookie': userInfo[5],
                'userId': userInfo[6],
            }
            return loginData

        g_var.logger.info('login, no cookie....')
        url_login = 'https://login.ex.co/api/login'
        # cookie为空，使用账号密码登录
        headers = generate_headers(0)
        headers['Referer'] = 'https://login.ex.co/login'
        if headers == -1:
            g_var.logger.info("获取headers失败...")
            return -1
        captcha_value = google_captcha('', googlekey, url_login)
        if captcha_value == -1:
            return -2
        loginData = {
            "email": userInfo[3],
            "password": userInfo[2],
            "loginType": "Email",
            "captchaResponse": captcha_value,
        }
        g_var.logger.info("登录中...")
        html = requestsW.post(url_login, proxies=ip_proxy("en"), json=loginData, headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html
        if '"response":"success"' not in html.text:
            g_var.logger.info('登录失败。。。')
            g_var.logger.info(html.text)
            return -2
        accessToken = re.findall('"accessToken":"(.*?)"}', html.text)[0]
        try:
            # 获取cookie，保存到数据库。
            sql = "UPDATE " + present_website + " SET cookie='" + accessToken + "' WHERE id=" + str(userInfo[0]) + ";"
            status = MysqlHandler().update(sql)
            if status == 0:
                g_var.logger.info("update cookie OK")
            else:
                g_var.ERR_CODE = 2004
                g_var.ERR_MSG = "数据库更新cookie错误..."
                g_var.logger.error("数据库更新cookie错误...")
                return 0
        except Exception as e:
            g_var.logger.info(e)
            g_var.ERR_CODE = 2004
            g_var.ERR_MSG = "数据库更新cookie异常..."
            g_var.logger.error("数据库更新cookie异常...")
            return 0
        loginData = {
            'id': userInfo[0],
            'firstName': userInfo[1],
            'password': userInfo[2],
            'cookie': accessToken,
            'userId': userInfo[6],
        }
        return loginData

    def __postMessage(self, loginData, present_website, googlekey):
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
                -4:cookie失效
        """
        g_var.logger.info('post article......')
        item_id = str(uuid.uuid4())
        sections_id = str(uuid.uuid4())
        g_var.logger.info('正在获取headers。。。')
        headers = generate_headers(2, loginData['cookie'], item_id)
        if headers == -1 or loginData['cookie']=="":
            g_var.logger.info("获取headers失败...")
            return -1
        captcha_url = 'https://app.ex.co/create/new/preview'
        captcha_value = google_captcha('', googlekey, captcha_url)
        if captcha_value == -1:
            return -2
        title, ops = get_article()
        if title == -1 or ops == -1:
            g_var.logger.info("未能获取对应文章格式内容...")
            return -1
        article_data = generate_post_article_data(loginData, item_id, sections_id, captcha_value, title, ops)
        g_var.logger.info("文章发送中...")
        url = 'https://editor.ex.co/item/publish'
        res = requestsW.post(url, proxies=ip_proxy("en"), json=article_data, headers=headers, timeout=g_var.TIMEOUT)
        if res == -1:
            return res

        # cookie失效判断
        cookie_prove = '401 - "Failed to authenticate token"'
        if cookie_prove == res.text:
            g_var.logger.info('cookie 失效 ......')
            # 如果cookie失效，将该cookie从数据库中清除，并重新从数据库中获取登录账号密码
            sql = "UPDATE " + present_website + " SET cookie='' WHERE id=" + str(loginData['id']) + ";"
            status = MysqlHandler().update(sql)
            if status == 0:
                g_var.logger.info("cookie失效，清除cookie update OK")
                return -4
            else:
                g_var.logger.error("数据库清除cookie错误!")
                return 1

        res_article = re.findall('"item":\{"id":"(.*?)","tags"', res.text)
        if not res_article:
            g_var.ERR_CODE = 5000
            g_var.ERR_MSG = "文章发送失败，IP异常等原因..."
            g_var.logger.info('文章发送失败，IP异常等原因...')
            return -1
        try:
            url = 'https://app.ex.co/stories/item/' + item_id
            sql = "INSERT INTO playbuzz_com_article(url, keyword, user_id) VALUES('" + url + "', '" + title + "', '" + str(loginData["id"]) + "');"
            last_row_id = MysqlHandler().insert(sql)
            g_var.logger.info(last_row_id)
            if last_row_id != -1:
                g_var.logger.info('文章成功！' + loginData['firstName'])
                return 0
            else:
                g_var.ERR_CODE = 2004
                g_var.ERR_MSG = "数据库插入用户注册数据失败..."
                g_var.logger.error("数据库插入用户注册数据失败...")
                return -3
        except Exception as e:
            g_var.logger.info(e)
            g_var.ERR_CODE = 2004
            g_var.ERR_MSG = "数据库插入用户注册数据异常..."
            g_var.logger.error("数据库插入用户注册数据异常...")
            return -3

    def registers(self, present_website, VPN):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1
            # 获取邮箱
            email_info = get_email(present_website)
            if email_info == -1:
                self.failed_count = self.failed_count + 1
                continue
            googlekey = get_googlekey()
            if googlekey == -1:
                g_var.ERR_CODE = 2001
                g_var.ERR_MSG = g_var.ERR_MSG + "无法获取googleKey值..."
                g_var.logger.info("获取googlekey值失败...")
                continue
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(present_website, email_info, googlekey)
                if registerData == -1:
                    g_var.ERR_CODE = 3003
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif registerData == -2:
                    g_var.logger.info("注册失败，请排查！")
                    continue
                elif registerData == 0:
                    # 注册成功，但存库失败
                    g_var.logger.info("注册成功,但存库失败！")
                    break
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

    def loginAndPostMessage(self, present_website, VPN):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1

            # 从数据库中获取用户信息
            userInfo = generate_login_data(present_website)
            g_var.logger.info(userInfo)
            if userInfo == None:
                g_var.ERR_CODE = 2003
                g_var.ERR_MSG = g_var.ERR_MSG + "无法获取正常用户!"
                g_var.logger.error("数据库中获取用户失败，本线程停止！")
                return -1
            # 1、登录
            login_signal = 0
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                googlekey = get_googlekey()
                if googlekey == -1:
                    g_var.ERR_CODE = 2001
                    g_var.ERR_MSG = g_var.ERR_MSG + "无法获取googleKey值..."
                    g_var.logger.info("获取googlekey值失败...")
                    continue
                loginData = self.__login(present_website, VPN, userInfo, googlekey)
                if loginData == -1:
                    # 代理问题，更换代理
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif loginData == -2:
                    # 账号异常，跳出本循环
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                elif loginData == 0:
                    # cookie存库失败
                    g_var.logger.info("cookie存库失败！")
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                else:
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("login:连续登录失败！程序停止")
                break
            if login_signal == 1:
                continue

            # 2、发文章
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                time.sleep(g_var.SLEEP_TIME)
                retry_count = retry_count + 1
                status = self.__postMessage(loginData, present_website, googlekey)
                if status == 0:  # 发文章成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    break
                elif status == -1:
                    # 返回值为-1，更换代理
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == -2:
                    # 返回值为-1，某些必须停止的错误，程序停止
                    self.failed_count = self.failed_count + 1
                    g_var.SPIDER_STATUS = 3
                    break
                elif status == -3:
                    # 返回值为-1，数据库错误
                    self.failed_count = self.failed_count + 1
                    break
                elif status == -4:
                    # cookie失效，结束此次发送
                    self.failed_count = self.failed_count + 1
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功发送" + str(self.success_count) + "篇文章")

    def start(self, present_website, VPN):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1

            # 获取邮箱
            email_info = get_email(present_website)
            if email_info == -1:
                self.failed_count = self.failed_count + 1
                continue
            googlekey = get_googlekey()
            if googlekey == -1:
                g_var.ERR_CODE = 2001
                g_var.ERR_MSG = g_var.ERR_MSG + "无法获取googleKey值..."
                g_var.logger.info("获取googlekey值失败...")
                continue
            retry_count = 0
            register_signal = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(present_website, email_info, googlekey)
                if registerData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif registerData == -2:
                    g_var.logger.info("注册失败，请排查！")
                    continue
                elif registerData == 0:
                    # 注册成功，但存库失败
                    g_var.logger.info("注册成功,但存库失败！")
                    register_signal = 1
                    break
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
                register_signal = 1
                break

            if register_signal == 1:
                continue

            # 2、发文章
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                time.sleep(g_var.SLEEP_TIME)
                retry_count = retry_count + 1
                status = self.__postMessage(registerData, present_website, googlekey)
                if status == 0:  # 发文章成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    break
                elif status == -1:
                    # 返回值为-1，更换代理
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == -2:
                    # 返回值为-1，某些必须停止的错误，程序停止
                    self.failed_count = self.failed_count + 1
                    g_var.SPIDER_STATUS = 3
                    break
                elif status == -3:
                    # 返回值为-1，数据库错误
                    self.failed_count = self.failed_count + 1
                    continue
                elif status == -4:
                    # cookie失效，结束此次发送
                    self.failed_count = self.failed_count + 1
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功注册账户并发送文章" + str(self.success_count) + "篇。")
