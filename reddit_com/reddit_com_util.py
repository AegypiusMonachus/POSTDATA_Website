import re
import json
import sys
import random
import threading
import time

import requests
from requests.adapters import HTTPAdapter

from project_utils.project_util import generate_login_data, ip_proxy, get_new_article, MysqlHandler
from project_utils import g_var, project_util


# @#$ 3、本处定义小项目通用的函数

# @#$ 4、定义对象，需要实现__register_one、__login、__postMessage三个功能
class RedditCom(object):
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
            g_var.logger.info("self.failed_count=" + str(self.failed_count))
            return -1
        return 0

    # -1 换代理 返回 1
    def __register_one(self, Session, present_website: str):  # user,pass,
        try:
            headers = {}
            headers['Connection'] = 'close'
            headers['user_agent'] = project_util.get_user_agent()
            res = Session.get("https://www.reddit.com/register/?actionSource=header_signup", headers=headers,
                               timeout=g_var.TIMEOUT)
            re_res = re.search('<input type="hidden" name="csrf_token" value="(.*?)">', res.text)
            if re_res.group():
                csrf_token = re_res.group(1)
            else:
                g_var.ERR_CODE = "2001"
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|没有获取到token"
                g_var.logger.error("没有获取到token")
                return -1
            google_code = project_util.google_captcha(requests.session(), "6LeTnxkTAAAAAN9QEuDZRpn90WwKk_R1TRW_g-JC",
                                                      "https://www.reddit.com")
            if len(google_code) < 5:
                g_var.ERR_CODE = "2010"
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|"
                g_var.logger.error("没有获取到谷歌验证码")
            user = project_util.generate_random_string(6, 12)
            pwd = project_util.generate_random_string(10, 16)
            email = user + "@hotmail.com"
            data = {
                "csrf_token": csrf_token,
                "g-recaptcha-response": google_code,
                "dest": "https://www.reddit.com",
                "password": pwd,
                "username": user,
                "email": email,
            }
            # headers["content-type"]="application/x-www-form-urlencoded"

            res = Session.post("https://www.reddit.com/register", headers=headers, data=data, timeout=g_var.TIMEOUT)
            # if res.json():#成功结果:{"dest": "https://www.reddit.com"}
            if self.__dictExistValue(res.json(), "dest"):
                self.captcha_err_count = 0
                sql = "INSERT INTO reddit_com(username, password, mail, status) VALUES('" + user + \
                      "', '" + pwd + "', '" + email + "', '" + str(0) + "');"
                print("正在进入sql:", sql)
                last_row_id = MysqlHandler().insert(sql)
                if last_row_id != -1:
                    userId = last_row_id
                    return {'user_id': userId, 'name': user, 'password': pwd, 'mail': email}
                else:
                    g_var.logger.error("数据库插入失败")
                    return -1
            else:
                g_var.logger.info("验证码错误或邮箱名重复!result:", res.text)
                self.captcha_err_count = self.captcha_err_count + 1
                return -1
        except Exception as e:
            g_var.ERR_CODE = "2100"
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|"+"ip出现问题 请求失败"
            g_var.logger.info("未知错误:", e)
            return -1

    def __login(self, Session, VPN, userInfo) -> dict:
        try :
            # 从传入的userInfo中判断是否包含cookie，有cookie直接跳过登录流程，
            # 没有cookie或cookie过期再执行登录流程

            # 判断用户信息中是否包含cookie
            if userInfo[5] != None and userInfo[5] != "":
                print("正在获取cookie")
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
                print("用账号密码登录中")
                # cookie为空，使用账号密码登录
                user_id = userInfo[0]
                username = userInfo[1]
                password = userInfo[2]

                res = Session.get("https://www.reddit.com/register/?actionSource=header_signup",
                                  timeout=g_var.TIMEOUT)
                re_res = re.search('<input type="hidden" name="csrf_token" value="(.*?)">', res.text)
                if re_res.group():
                    csrf_token = re_res.group(1)
                else:
                    g_var.logger.info("注册未获取到token",re_res)
                    return {"error": -1}
                # res.headers["content-type"]="application/x-www-form-urlencoded"
                data = {
                    "csrf_token": csrf_token,
                    "otp": "",
                    "dest": "https://www.reddit.com",
                    "password": password,
                    "username": username,
                }
                print("正在提交参数",data)
                print(data)
                retry_count = 0
                while retry_count < g_var.RETRY_COUNT_MAX:
                    retry_count = retry_count + 1
                    try:
                        g_var.logger.info("使用账号密码登录...")
                        res = Session.post("https://www.reddit.com/login", data=data,  timeout=g_var.TIMEOUT)
                        # print("登录text",res.text)
                        cookie = res.cookies.get_dict()
                        print("这里是cookie",cookie)
                        self.proxy_err_count = 0
                        break
                    except Exception as e:

                        g_var.logger.error("账号密码登录超时:",e)
                        self.proxy_err_count = self.proxy_err_count + 1
                        time.sleep(g_var.SLEEP_TIME)
                        proxies = ip_proxy(VPN)
                        Session.proxies = proxies
                        continue
                if retry_count == g_var.RETRY_COUNT_MAX:
                    g_var.SPIDER_STATUS = 3
                    g_var.logger.error("连续登录失败！程序停止")
                    return {"error": -1}

                if not self.__dictExistValue(cookie, "reddit_session"):
                    # 如果登录失败将数据库中的status改为异常 TODO t注释
                    # sql = "UPDATE reddit_com SET status=1 WHERE id=" + str(user_id) + ";"
                    # MysqlHandler().update(sql)

                    return {"error": 1}  # 账号异常，重新取号登录
                else:
                    print("正在存入cookie")
                    # 如果登录成功，则返回id和username给下一步发新文章
                    user_id = userInfo[0]
                    # 长度为2，使用账号密码登录的loginData
                    sql = "UPDATE reddit_com SET cookie=\"" + str(cookie) + "\" WHERE id=" + str(
                        user_id) + ";"
                    status = MysqlHandler().update(sql)
                    if status == 0:
                        g_var.logger.info("update cookie OK")
                    else:
                        g_var.logger.error("数据库更新cookie错误!")
                        return {"error": 1}
                    loginData = {
                        'id': user_id,
                        'name': username
                    }
                return loginData
        except Exception as e:
            g_var.ERR_CODE = "2100"
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|"+"ip出现问题 请求失败"
            g_var.logger.error("登录错误:",e)
            return {"error": 1}



    def __postMessage(self, Session, loginData: dict) -> dict:
        # 根据loginData的长度，长度为2表示账号密码登录，长度为3表示cookie登录
        #             loginData = {
        #         'id': user_id,
        #         'name': username,
        #         'cookie': Cookie
        #     }

        #
        try:
            headers = {"user-agent": project_util.get_user_agent(), "content-type": "application/json; charset=UTF-8"}

            article = project_util.get_new_article()
            articleR = self.__article_sumbit(article[1])
            if article == {"error": -1}:
                # 获取不到文章，程序停止
                g_var.SPIDER_STATUS = 3
                return {"error": -1}
            else:
                if len(loginData) == 2:
                    print("11111111111",loginData)
                    res_accessToken = Session.get("https://www.reddit.com/user/%s/submit" % loginData["name"],
                                                  headers=headers,
                                                   timeout=g_var.TIMEOUT)
                else:
                    res_accessToken = Session.get("https://www.reddit.com/user/%s/submit" % loginData["name"],
                                                  cookies=eval(loginData["cookie"]),
                                                  headers=headers,
                                                   timeout=g_var.TIMEOUT)

                re_res = re.search('{"accessToken":"(.{18,64})",', res_accessToken.text)
                if re_res.group():

                    accessToken = re_res.group(1)
                else:
                    g_var.logger.error("发送文章token 错误")
                    return {"error": -1}

                contentData = {"sr": "u_" + loginData["name"],
                               "api_type": "json",
                               "show_error_list": "true",
                               "title": "woaini" + article[0],
                               "spoiler": "true",
                               "nsfw": "false",
                               "kind": "self",
                               "original_content": "true",
                               "submit_type": "profile",
                               "post_to_twitter": "false",
                               "sendreplies": "true",
                               "richtext_json": articleR,
                               # "text":articleList[1],
                               "validate_on_submit": "true"}
                headers["content-type"] = "application/x-www-form-urlencoded"
                headers["authorization"] = "Bearer " + accessToken
                if len(loginData) == 2:
                    res = Session.post(
                        "https://oauth.reddit.com/api/submit?resubmit=true&redditWebClient=desktop2x&app=desktop2x-client-production&rtj=only&raw_json=1&gilding_detail=1" %
                        loginData["name"], data=contentData,
                        headers=headers,
                         timeout=g_var.TIMEOUT)
                else:
                    res = Session.post("https://oauth.reddit.com/api/submit?resubmit=true&redditWebClient=desktop2x&app=desktop2x-client-production&rtj=only&raw_json=1&gilding_detail=1",
                                       data=contentData, cookies=eval(loginData["cookie"]),
                        headers=headers, timeout=g_var.TIMEOUT)
                if self.__dictExistValue(res.json(), "json", "data", "url"):
                    resultUrl = res.json()["json"]["data"]["url"]

                    # 将文章链接、标题、用户存入article表
                    sql = "INSERT INTO reddit_com_article(url, keyword, user_id) VALUES('" + resultUrl + "', '" + article[
                        0] + "', '" + str(loginData['id']) + "');"
                    if g_var.insert_article_lock.acquire():
                        last_row_id = MysqlHandler().insert(sql)
                        g_var.insert_article_lock.release()
                    status = MysqlHandler().update(sql)
                    return {"ok": 0}
                else:
                    g_var.logger.error("文章发送失败！\n" + res.text)
                    g_var.ERR_CODE = 5000
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "文章发送失败，未知错误!"
                    return {"error": 1}
        except Exception as e:
            g_var.ERR_CODE = "2100"
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|"+"ip出现问题 请求失败"
            g_var.logger.error("发送文章错误！\n" ,e)
            return {"error": 1}

    def __article_sumbit(self, content: str):

        # (e:text,t:文本),(e:link,t:文本,u:url)

        rList = []

        def _ahref(matched):
            intStr = matched.group("ahref")  # 123
            addedValue = intStr  # 234
            addedValueStr = "|1_1|" + addedValue + "|1_1|"
            return addedValueStr

        hrefCut = re.sub("(?P<ahref><a href=.*?</a>)", _ahref, content)  # 拿出指定标签并替换其它内容
        hrefList = hrefCut.split("|1_1|")
        for s in hrefList:
            if "<a href" in s:
                href = re.search("href=\"(?P<href>.*?)\"", s).group("href")
                text = re.search("<a href=.*?>(?P<text>.*?)</a>", s)
                if text:
                    text2 = re.sub("<.*?>", "", text.group("text"))
                    one = {"e": "link", "t": text2, "u": href}
                    rList.append(one)
                else:
                    text = re.sub("<.*?>", "", s)
                    one = {"e": "text", "t": text, }
                    rList.append(one)
            else:
                text = re.sub("<.*?>", "", s)
                one = {"e": "text", "t": text, }
                rList.append(one)

        # "l": 3,

        return json.dumps({"document": [{"e": "par", "c": rList}]}, ensure_ascii=False)

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
            Session.proxies = {
                "http": proxies,
                "https": proxies,
            }
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

            # 1、登录
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                # 从数据库中获取用户信息
                userInfo = generate_login_data("reddit_com")
                if userInfo == None:
                    g_var.logger.error("数据库中获取用户失败，本线程停止！")
                    return {"error": -1}
                else:
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
                        continue
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

                if registerData != -1:  # 说明注册成功
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
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                # 构造一个userInfo
                userInfo: tuple = (registerData['user_id'], registerData['name'], registerData['password'],
                                   registerData['mail'], '0', "")

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
                    continue
                else:
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                g_var.SPIDER_STATUS = 3
                g_var.logger.error("start:连续登录失败！程序停止")
                break

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

    def __dictExistValue(self, d: dict, *args) -> bool:
        if not isinstance(d, dict):
            return False
        for v in args:
            if v in d:
                d = d[v]
            else:
                return False
        return True
