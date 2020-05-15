import re
import time

import requests
from requests.adapters import HTTPAdapter

from project_utils.project_util import generate_login_data, ip_proxy, get_new_article, MysqlHandler, get_Session, \
    get_email, get_user_agent, google_captcha, EmailVerify, get_new_title_and_link
from project_utils import g_var, project_util, requestsW


# @#$ 3、本处定义小项目通用的函数

# @#$ 4、定义对象，需要实现__register_one、__login、__postMessage三个功能
# 每个函数都有指定的传入传出参数
class DiigoCom(object):
    def __init__(self, assignment_num):
        self.assignment_num = assignment_num  # 分配任务的数量
        self.now_count = 0  # 本线程执行总数
        self.success_count = 0  # 本线程执行成功数
        self.register_success_count = 0  # start方法中register成功数
        self.login_and_post_success_count = 0  # start方法中login_and_post成功数
        self.failed_count = 0  # 本线程执行失败数
        self.proxy_err_count = 0  # 本线程代理连接连续失败数
        self.captcha_err_count = 0  # 当前验证码识别连续错误次数
        self.headers = {"User-Agent": get_user_agent()}

    def __monitor_status(self):
        if g_var.SPIDER_STATUS == 3 or self.failed_count > g_var.ERR_COUNT:
            g_var.logger.error("g_var.SPIDER_STATUS=3 or self.failed_count > g_var.ERR_COUNT，本线程将停止运行")
            g_var.logger.info("self.failed_count=" + str(self.failed_count))
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
                        registerData["id"] = last_row_id
                        return registerData
                    else:
                        g_var.logger.error("数据库插入用户注册数据失败")
                        return 0
            注册失败返回状态码
            0：更换email 返回0 或其他错误，但是激活失败或插入数据库失败
            -1:表示requests请求页面失败，需要更换代理
            -2:注册失败，可能是邮箱密码不符合要求、或ip被封等原因，需要排查
        """

        user = project_util.generate_random_string(12, 16)
        pwd = project_util.generate_random_string(10, 12)
        email_list = email_and_passwd
        if email_list == -1:
            g_var.SPIDER_STATUS = 2
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|NO email"
            g_var.logger.info("NO email")
            return 0

        verify_email = Session.get("https://www.diigo.com/user_mana2/check_email?email=" + email_list[0],
                                   timeout=g_var.TIMEOUT,
                                   headers=self.headers, proxies=Session.proxies)  # 验证邮箱是否可用

        verify_user = Session.get("https://www.diigo.com/user_mana2/check_name?username=" + user, headers=self.headers,
                                  timeout=g_var.TIMEOUT,
                                  proxies=Session.proxies)  # 验证用户是否可用

        if not verify_user.text == verify_email.text == "1":
            g_var.SPIDER_STATUS = 2
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|账号密码或邮箱已经被注册"
            g_var.logger.info("账号密码或邮箱已经被注册")
            return 0

        # time.sleep(3)

        google_captchas = google_captcha("", "6Ld23sMSAAAAALfyXkI9d0nHmzOH9jZZNuh66nql",
                                         "https://www.diigo.com/sign-up?plan=free")
        if google_captchas == -1:
            g_var.SPIDER_STATUS = 2
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|谷歌打码失败"
            g_var.logger.info("谷歌打码失败")
            return -2

        res = requestsW.get("https://www.diigo.com/", headers=self.headers, proxies=Session.proxies)  # 打开首页
        if res == -1: return res
        cookies = res.cookies.get_dict()
        i = 0
        while i < g_var.ERR_COUNT:
            i += 1
            try:
                Session.proxies = ip_proxy()
                res = requests.get("https://www.diigo.com/sign-up?plan=free", headers=self.headers, cookies=cookies,
                                   proxies=Session.proxies, verify=False)
                user_input = re.search('id="username" name="(\w{32})">', res.text)
                email_input = re.search('id=\'email\' name="(\w{32})">', res.text)
                pwd_input = re.search('id=\'password\' name="(\w{32})"', res.text)
                if not user_input and email_input and pwd_input:  # TODO 获取不到参数
                    return "注册无法打开网页"
                else:
                    user_input = user_input.group(1)
                    email_input = email_input.group(1)
                    pwd_input = pwd_input.group(1)
                data = {
                    "plan": "free",
                    "g-recaptcha-response": google_captchas,
                    user_input: user,
                    email_input: email_and_passwd[0],
                    pwd_input: pwd,
                }
                self.headers["X-Requested-With"] = "XMLHttpRequest"
                self.headers["Referer"] = "https://www.diigo.com/sign-up?plan=free"
                self.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

                res = requests.post("https://www.diigo.com/user_mana2/register_2", headers=self.headers,
                                    cookies=cookies,
                                    data=data, proxies=Session.proxies, verify=False)
                print(res.json())
                if project_util.dictExistValue(res.json(), "status"):
                    if res.json()["status"] == 1:
                        cookies.update(res.cookies.get_dict())
                        savec = cookies
                        res = requestsW.post("https://www.diigo.com/user_mana2/resend_verify", cookies=cookies,
                                             headers=self.headers, data={"email": email_and_passwd[0]},
                                             proxies=Session.proxies)
                        print("重新发送邮箱:", res.text)

                        emailinfo = EmailVerify(email_and_passwd[0], email_and_passwd[1],
                                                'href="(https://www.diigo.com/user_mana2/register_verify/\w{32})"').execute_Start()
                        print("这里是邮箱参数:", emailinfo)
                        if emailinfo["data"] != -1:
                            Session = requestsW.session()
                            res = Session.get(emailinfo["data"], headers=self.headers, proxies=Session.proxies,
                                              cookies=cookies)
                            sql = """INSERT INTO %s (username, password, mail, status, cookie) VALUES("%s", "%s", "%s", "%s", "%s");""" % (
                                "diigo_com", user, pwd, email_and_passwd[0], 0, savec)
                            g_var.logger.info(sql)
                            last_row_id = MysqlHandler().insert(sql)

                            if last_row_id != -1:
                                registerData = {
                                    "username": user,
                                    "password": pwd,
                                    "email": email_and_passwd[0],
                                    "cookie": savec,
                                }
                                registerData["id"] = int(last_row_id)
                                return registerData
                            return {"user": user, "pwd": pwd, "email": email_and_passwd[0],
                                    "cookies": Session.cookies.get_dict()}
                            # if project_util.dictExistValue(res.cookies.get_dict(),"diigoandlogincookie"):  # 注册成功并登陆cookie
                            #     saveCookie = str(Session.cookies.get_dict())
                            #     # print({"user": user, "pwd": pwd, "email": email_and_passwd[0], "cookies": saveCookie})
                            #     return {"user": user, "pwd": pwd, "email": email_and_passwd[0], "cookies": saveCookie}
                    elif res.json()["status"] == -2:
                        if "captcha error" in res.json()["status"]:
                            g_var.SPIDER_STATUS = 2
                            g_var.ERR_MSG = g_var.ERR_MSG + "|_|谷歌打码失败"
                            g_var.logger.info("谷歌打码失败")
                            return -2
                return -2

            except Exception as e:
                res = requestsW.get("https://www.diigo.com/", headers=self.headers, proxies=Session.proxies,
                                    verify=False)  # 打开首页
                cookies = res.cookies.get_dict()
                g_var.logger.info(e)
                g_var.logger.info("正在换ip", e)
        return 0

    def login(self, Session, present_website: str, VPN, userInfo):
        """
        登录
        根据用户信息userInfo中是否包含cookie
        1、有cookie直接构造loginData返回，跳过登录流程
        2、没有cookie，需要post登录请求，获取到cookie，再构造loginData返回
        Args:
            Session：Session对象
            present_website：当前网站名，用于数据库表名
            VPN：使用国内or国外代理
            userInfo：用户信息  userInfo[0]:id [1]:username [2]passwod [3]:emial [4]:status [5]cookie

        Mysql Update:
                        # 如果cookie失效，将该cookie从数据库中清除，并重新从数据库中获取登录账号密码
                sql = "UPDATE 网站名 SET cookie='' WHERE id=" + str(loginData['id']) + ";"
                status = MysqlHandler().update(sql)
                if status == 0:
                    g_var.logger.info("cookie失效，清除cookie update OK")
                    return {"error": -2}
                else:
                    g_var.logger.error("数据库清除cookie错误!")
                    return {"error": 1}

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
        user_id = userInfo[0]
        username = userInfo[1]
        password = userInfo[2]
        if userInfo[5] != None and userInfo[5] != "":
            # userInfo[5]保存cookie值，如果cookie不为空，则使用cookie
            g_var.logger.info("返回cookie" + userInfo[5])
            cookie = userInfo[5]
            loginData = {
                'id': user_id,
                'username': username,
                'password': password,
                'cookie': str(cookie),
            }
            return loginData
        else:
            google_captchas = google_captcha("", "6Ld23sMSAAAAALfyXkI9d0nHmzOH9jZZNuh66nql",
                                             "https://www.diigo.com/sign-in?referInfo=https%3A%2F%2Fwww.diigo.com")
            if google_captchas == -1:
                return "谷歌打码失败"
            i = 0
            while i < g_var.ERR_COUNT:
                i += 1
                try:
                    Session.proxies = ip_proxy()
                    res = requests.get("https://www.diigo.com/sign-in?referInfo=https%3A%2F%2Fwww.diigo.com",
                                       headers=self.headers, proxies=Session.proxies)
                    login_token = re.search('name="loginToken" value="(\w{32})"', res.text)
                    if login_token:
                        login_token = login_token.group(1)
                        print(login_token)
                    else:
                        return "为获取登陆cookie"
                    cookies = res.cookies.get_dict()
                    if res == -1: return res
                    data = {
                        "referInfo": "https://www.diigo.com",
                        "loginToken": login_token,
                        "username": username,
                        "password": password,
                        "g-recaptcha-response": google_captchas,
                        "recaptcha": "v2",
                    }
                    self.headers["X-Requested-With"] = "XMLHttpRequest"
                    self.headers["Referer"] = "https://www.diigo.com/sign-in?referInfo=https%3A%2F%2Fwww.diigo.com"
                    self.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
                    g_var.logger.info("正在登录中")
                    res = requests.post("https://www.diigo.com/sign-in", headers=self.headers, data=data,
                                        cookies=cookies,
                                        proxies=Session.proxies)
                    g_var.logger.info("登录结束")
                    g_var.logger.info(res.text)
                    if not '"status":1' in res.text:
                        return -2
                    else:
                        break

                except Exception as e:
                    g_var.logger.info("正在换ip" + str(e))

            save_cookies = str(res.cookies.get_dict())
            if "diigoandlogincookie" in save_cookies:
                sql = "UPDATE %s SET cookie=\"%s\" WHERE id=%s ;" % (present_website, save_cookies, user_id)
                g_var.logger.info(sql)
                status = MysqlHandler().update(sql)
                if status == 0:
                    g_var.logger.info("cookie失效，清除cookie update OK")
                    return {
                        'id': user_id,
                        'username': username,
                        'password': password,
                        'cookie': save_cookies,
                    }
                else:
                    g_var.logger.error("数据库清除cookie错误!")
                    return {"error": 1}

            else:
                return -1

            pass

    def __postMessage(self, Session, loginData: dict, present_website):
        """
        发文章
        Args:
            Session：Session对象
            loginData：用户信息，包括id,username,password,cookie
            present_website：当前网站名，用于数据库表名
        Returns:
            成功返回状态值：0
            失败返回状态值：
                1:表示账号密码失效，密码被改或账号被网站删除
                -1:连续代理错误，停止程序
                -2:页面发生改变，获取不到页面上的一些token值
                -3:数据库插入更新等错误
                -4：cookie过期
        """
        if loginData["cookie"] != "":
            Session.cookies = loginData["cookie"]
        title_link = get_new_title_and_link()
        postUrl = title_link[1]
        users = loginData["username"]
        # Sesstion.cookies=cookies
        self.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        self.headers["Referer"] = "https://www.diigo.com/user/t3wjogvjklzwh3zi"
        self.headers["Origin"] = "https://www.diigo.com"
        # res=requests.post("https://superio.diigo.com/fetch_meta",headers=headers,data={"url":postUrl},verify=False)
        # print(res.text)
        # if not project_util.dictExistValue(res.json(),"title"):
        #     return "请求失败"

        self.headers["X-Requested-With"] = "XMLHttpRequest"
        # res=Sesstion.get("https://www.diigo.com/tag_mana2/load_recommended_tags",params={"title":res.json()["title"],"url":postUrl},headers=headers,cookies=cookies,verify=False)
        # if not project_util.dictExistValue(res.json(),"tags"):
        #     return "提交网站有问题"

        data = {
            "title": title_link[0],
            "tags": title_link[0],
            "description": title_link[0],
            "unread": False,
            "private": False,
            "url": postUrl,
            "lists": "",
            "groups": "",
        }

        res = requestsW.post("https://www.diigo.com/item/save/bookmark", cookies=eval(loginData["cookie"]),
                             headers=self.headers, data=data)
        if res == -1: return res
        g_var.logger.info(res.text)
        g_var.logger.info(loginData)
        if project_util.dictExistValue(res.json(), "items"):
            res_url = "https://www.diigo.com/user/" + users
            sql = "INSERT INTO %s_article(url, keyword, user_id) VALUES('%s', '%s', '%s');" % (
            present_website, res_url, title_link[0], loginData["id"])
            if g_var.insert_article_lock.acquire():
                last_row_id = MysqlHandler().insert(sql)
                if last_row_id == -1:
                    return -1
                g_var.insert_article_lock.release()
            return 0
        else:
            return -1
            # return -4

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
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
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
                    g_var.logger.info("网站内运行错误")
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
                else:
                    self.failed_count = 0
                    self.proxy_err_count = 0
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
                if status == 0:  # 发文章成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    self.proxy_err_count = 0
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
                    self.failed_count = self.failed_count + 1
                elif status == -4:
                    sql = "UPDATE %s SET cookie=null WHERE id=%s ;" % (present_website, loginData["id"])
                    g_var.logger.info(sql)
                    status = MysqlHandler().update(sql)
                    if status != 0:
                        g_var.logger.error("数据库清除cookie错误!")
                        return {"error": 1}
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续发文章出错，程序停止"
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
            retry_count = 0
            email_and_passwd = get_email(present_website)
            if email_and_passwd == -1:
                retry_count = g_var.RETRY_COUNT_MAX
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|没有邮箱了"
                g_var.logger.error("没有邮箱了")
                continue
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(Session, present_website, email_and_passwd)
                if registerData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
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
                    email_and_passwd = get_email(present_website)
                    if email_and_passwd == -1:
                        retry_count = g_var.RETRY_COUNT_MAX
                        g_var.ERR_MSG = g_var.ERR_MSG + "|_|没有邮箱了"
                        g_var.logger.error("没有邮箱了")
                        continue
                    retry_count = 0
                else:
                    # 注册成功
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("start:连续注册失败！程序停止")
                break

            # 2、登录
            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue
            # 构造一个userInfo
            g_var.logger.info(registerData)
            userInfo = [int(registerData['id']), registerData['username'], registerData['password'],
                        registerData['email'], 0, str(registerData['cookie'])]

            login_signal = 0  # 记录状态，成功为0，失败为1
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1

                loginData = self.login(Session, present_website, VPN, userInfo)
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
                else:
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续登录出错，程序停止"
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
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == -2:
                    # 某些必须停止的错误，程序停止
                    self.failed_count = self.failed_count + 1
                    g_var.SPIDER_STATUS = 3
                    break
                elif status == -3:
                    self.failed_count = self.failed_count + 1
                elif status == -4:
                    sql = "UPDATE %s SET cookie=null WHERE id=%s ;" % (present_website, loginData["id"])
                    g_var.logger.info(sql)
                    status = MysqlHandler().update(sql)
                    if status != 0:
                        g_var.logger.error("数据库清除cookie错误!")
                        return {"error": 1}
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续发文章出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功注册账户并发送文章" + str(self.success_count) + "篇")
