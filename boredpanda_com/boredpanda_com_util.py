import email
import imaplib
import re
import time

from project_utils.project_util import generate_login_data, MysqlHandler, get_Session, get_email, ip_proxy,get_user_agent,get_new_title_and_link
from project_utils import g_var, requestsW


# @#$ 3、本处定义小项目通用的函数

# @#$ 4、定义对象，需要实现__register_one、login、__postMessage三个功能
# 每个函数都有指定的传入传出参数
class BoredpandaCom(object):
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
        注册一个账户,需要实现注册、激活、并将注册数据存入数据库的功能
        Args:
            Session：Session对象
            present_website：当前网站名，用于数据库表名
            email_and_passwd：邮箱账户和密码，email_and_passwd[0]是邮箱，[1]是密码
        Returns:
            注册成功返回注册数据字典对象registerData，需要包含id, username, password, email, cookie(在访问激活链接时能取到，\
            取不到返回空)
                user_id这样获取：（示例）
                    # 将注册的账户写入数据库（sql自己写，这边只是个示例）
                    sql = "INSERT INTO "+present_website+"(username, password, mail, status, cookie) VALUES('" + \
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
        """
        email = email_and_passwd[0]
        emailpwd = email_and_passwd[1]
        Session = requestsW.Session()
        Session.proxies = ip_proxy()
        headers = {
            "User-Agent": get_user_agent()}
        # headers["x-requested-with"] = "XMLHttpRequest"
        headers["referer"] = "https://www.boredpanda.com/add-new-post/"
        headers["content-type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        user = email.split("@")[0]
        pwd = emailpwd
        data = {
            "action": "contribution_signup",
            "user_email": email,
            "user_full_name": user,
            "user_pass": pwd,
            "redirect": "https://www.boredpanda.com/add-new-post/"
        }
        res = Session.post("https://www.boredpanda.com/blog/wp-admin/admin-ajax.php", proxies=Session.proxies,
                           data=data)
        if 'user_id' not in res.text:
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|发送邮箱,注册失败"
            g_var.logger.info("|_|发送邮箱,注册失败")
            return 0
        # TODO 邮箱新方法
        res = EmailVerify(username=email, password=emailpwd,
                          re_text='Click .{0,50} href="(http://\w{5,15}.ct.sendgrid.net/ls/click\?upn=.{300,600})">here</a>').execute_Start()
        if res == -1:
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|邮箱激活失败"
            g_var.logger.info("|_|邮箱激活失败")
            return 0
        res = Session.get(res["data"], headers=headers)
        if "boredpanda_auth" not in Session.cookies.get_dict():
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|邮箱获取链接后,请求失败"
            g_var.logger.info("|_|邮箱获取链接后,请求失败")
            return 0

        sql = """INSERT INTO %s (username, password, mail, status, cookie) VALUES("%s", "%s", "%s", "%s", "%s");""" % (
            present_website, user, pwd, email_and_passwd[0], 0,str(Session.cookies.get_dict()))
        g_var.logger.info(sql)
        last_row_id = MysqlHandler().insert(sql)
        if last_row_id==-1:
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|数据库插入失败"
            g_var.logger.info("|_|数据库插入失败")
            return 0


        tlList=get_new_title_and_link()
        title,url=tlList[0],tlList[1]
        data = {
            "action": "save_settings_form",
            "settingsDisplay": title,
            "settingsWebsite": url,
            "settingsFacebook": url,
            "settingsTwitter": url,
            "settingsFlickr": url,
            "settingsSlack": "",
            "settingsBio": title,
            "settingsAdminBox": ""
        }

        res = Session.post("https://www.boredpanda.com/blog/wp-admin/admin-ajax.php", proxies=Session.proxies,
                           headers=headers, data=data)
        success = 0
        if "success" not in res.text:
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|修改个人链接,请求失败"
            g_var.logger.info("|_|修改个人链接,请求失败")
            return 0


        data = {
            "action": "save_privacy_settings_form",
            "allowContactMe": "true",
            "ninjaPanda": "false",
        }
        # proxies=ip_proxy()
        res = Session.post("https://www.boredpanda.com/blog/wp-admin/admin-ajax.php", headers=headers,
                           proxies=Session.proxies, data=data)
        if "success" not in res.text:
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|允许个人资料访问,请求失败"
            g_var.logger.info("|_|允许个人资料访问,请求失败")
            return 0

        sql = "INSERT INTO %s_article(url, keyword, user_id) VALUES('%s', '%s', '%s');" % (
            present_website, "https://www.boredpanda.com/author/%s/" % user, title, last_row_id)
        if g_var.insert_article_lock.acquire():
            last_row_id = MysqlHandler().insert(sql)
            if last_row_id == -1:
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|MYSQL插入文章失败"
                g_var.logger.info("|_|MYSQL插入文章失败")
                return 0



    def login(self, Session, present_website: str, VPN, userInfo):
        """
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
            sql = "UPDATE %s SET cookie='%s' WHERE id=%s ;" % (boredpanda_com, save_cookies, user_id)
            status = MysqlHandler().update(sql)
            if status == 0:
                g_var.logger.info("cookie失效，清除cookie update OK")
                return {"error": -2}
            else:
                g_var.logger.error("数据库清除cookie错误!")
                return {"error": 1}    
        """

        if userInfo[5] != None and userInfo[5] != "":
            # userInfo[5]保存cookie值，如果cookie不为空，则使用cookie
            g_var.logger.info("返回cookie" + userInfo[5])
            user_id = userInfo[0]
            username = userInfo[1]
            password = userInfo[2]
            email = userInfo[3]
            cookie = userInfo[5]
            loginData = {
                'id': user_id,
                'username': username,
                'password': password,
                'email': email,
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
            loginData：用户信息，包括user_id,username,password,email,cookie
            present_website：当前网站名，用于数据库表名
        Returns:
            成功返回:"ok"
            失败返回状态值：
                1:跳出循环，重新取号
                0:cookie失效，将cookie清空，跳出循环重新取号
                -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
                -2:本次出错，继续循环
        """
        pass
    
    def __send_profile(self, Session, loginData: dict):
        """
        发个人简介
        Args:
            Session：Session对象
            loginData：用户信息，包括user_id,username,password,email,cookie
        Returns:
            成功返回:0
            失败返回状态值：
                1:cookie失效，将cookie清空，跳出循环重新取号
                -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
                -2:本次出错，继续循环
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
                    # 代理问题，更换代理
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
                    # 代理问题，更换代理
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
                if status == 0:  # 发个人简介成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    break
                elif status == -1:
                    # 代理问题，更换代理
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == -2:
                    self.failed_count = self.failed_count + 1
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
                    # 代理问题，更换代理
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


class EmailVerify(object):
    """
    邮箱验证，从注册邮箱中获取链接，访问链接，激活邮箱
    初始化后调用execute_Start  错:返回 -1 更换邮箱
    """

    def __init__(self, username, password, re_text):
        """
        :param username: 邮箱账号
        :param password: 邮箱密码
        :param re_text: 获取参数正则
        """
        self.username = username
        self.password = password
        self.re_text = re_text
        self.server = imaplib.IMAP4_SSL(host='imap-mail.outlook.com', port="993")
        self.server.login(username, password)
        self.inbox_unread = 0
        self.junk_unread = 0

    def get_mail(self, filename):
        # 邮箱中的文件夹，默认为'INBOX'
        inbox = self.server.select(filename)
        # 搜索匹配的邮件，第一个参数是字符集，None默认就是ASCII编码，第二个参数是查询条件，这里的ALL就是查找全部
        typ, data = self.server.search(None, "ALL")
        # 邮件列表,使用空格分割得到邮件索引
        msgList = data[0].split()
        # 最新邮件，第0封邮件为最早的一封邮件
        msgFirstTen = []
        if len(msgList) <= 10:
            msgFirstTen = msgList[::-1]
        else:
            msgFirstTen = msgList[-1:-11:-1]
        msgLen = len(msgFirstTen)
        i = 0
        for eachEmail in msgFirstTen:
            i += 1
            typ, datas = self.server.fetch(eachEmail, '(RFC822)')
            text = datas[0][1]
            texts = str(text, errors='replace')
            message = email.message_from_string(texts)
            result = self.parseBody(message)
            if result:
                return result
            if i == msgLen:
                return ''

    def parseBody(self, message):
        """ 解析邮件/信体 """
        # 循环信件中的每一个mime的数据块
        res_text = ''
        for part in message.walk():
            # 这里要判断是否是multipart，是的话，里面的数据是一个message 列表
            if not part.is_multipart():
                charset = part.get_charset()
                contenttype = part.get_content_type()
                name = part.get_param("name")  # 如果是附件，这里就会取出附件的文件名
                if name:
                    return ''
                    # 下面的三行代码只是为了解码象=?gbk?Q?=CF=E0=C6=AC.rar?=这样的文件名
                    # fh = email.header.Header(name)
                    # fdh = email.header.decode_header(fh)
                    # fname = dh[0][0]
                    # print('附件名:', fname)
                else:
                    # 文本内容
                    res = part.get_payload(decode=True)  # 解码出文本内容，直接输出来就可以了。
                    try:
                        res = res.decode(encoding='utf-8')
                    except:
                        return ""
                    res_text = res
        result = re.findall(self.re_text, res_text)
        if result:
            return result[0]
        else:
            return ''

    def UnseenEmailCount(self):
        try:
            inbox_x, inbox_y = self.server.status('INBOX', '(MESSAGES UNSEEN)')
            junk_x, junk_y = self.server.status('junk', '(MESSAGES UNSEEN)')
            inbox_unseen = int(re.search('UNSEEN\s+(\d+)', str(inbox_y[0])).group(1))
            junk_unseen = int(re.search('UNSEEN\s+(\d+)', str(junk_y[0])).group(1))
            filename_list = []
            # if self.inbox_unread == inbox_unseen and self.junk_unread == junk_unseen:
            #     self.inbox_unread = inbox_unseen
            #     self.junk_unread = junk_unseen
            #     return 0, 0, filename_list
            if self.junk_unread != junk_unseen:
                self.junk_unread = junk_unseen
                filename_list.append('junk')
            if self.inbox_unread != inbox_unseen:
                self.inbox_unread = inbox_unseen
                filename_list.append('INBOX')
            self.inbox_unread = inbox_unseen
            self.junk_unread = junk_unseen
            return inbox_unseen, junk_unseen, filename_list
        except:
            return 1, 1, ['junk','INBOX']

    def Start(self):
        result = {}
        inbox_unseen, junk_unseen, filename_list = self.UnseenEmailCount()
        if inbox_unseen == 0 and junk_unseen == 0:
            result['msg'] = 'Read Failed'
            result['data'] = ''
            return result
        else:
            for filename in filename_list:
                # 依次检查INBOX、JUNK文件夹，有新邮件就返回
                msg = self.get_mail(filename)
                if msg != "":
                    result['msg'] = 'Read Successfully'
                    result['data'] = msg
                    return result
            result['msg'] = 'Read Failed'
            result['data'] = ''
            return result

    def execute_Start(self):
        read_times = 0
        while read_times < 60:
            read_times += 1
            g_var.logger.info("正在检查邮箱%s,user:%s,pwd:%s" % (read_times, self.username, self.password))
            res = self.Start()
            if res['msg'] == 'Read Successfully':
                return res
            time.sleep(2)
        return -1