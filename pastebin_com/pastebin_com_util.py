import re
import threading
import time

import requests

from project_utils.project_util import generate_login_data, MysqlHandler, get_Session, get_email, \
    generate_random_string, identify_captcha_1, EmailVerify, account_activation, get_new_link
from project_utils import g_var


# @#$ 3、本处定义小项目通用的函数
def get_csrf_token(Session, headers, update_url, cookie):

    res = Session.get(update_url, headers=headers, cookies=cookie)
    g_var.logger.info(res.text)

    if res == -1:
        return -1
    else:
        csrf_token = re.findall('type="hidden" name="csrf_token" value="(.*?)"', res.text)
        if not csrf_token:
            g_var.logger.info("页面错误"+res.text)
            return -2
        else:
            g_var.logger.info("csrf_token"+csrf_token[0])
            return csrf_token[0]


# @#$ 4、定义对象，需要实现__register_one、login、__postMessage三个功能
# 每个函数都有指定的传入传出参数
class PastebinCom(object):
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
        username = generate_random_string(15, 20)
        password = generate_random_string(10, 15)
        g_var.logger.info("username:"+username)
        g_var.logger.info("password:"+password)

        # 图片验证码获取，识别
        captcha_url = "https://pastebin.com/etc/captcha/random.php"

        captcha_code = identify_captcha_1(Session, captcha_url, present_website)
        if captcha_code == -1:
            g_var.logger.info("代理连续错误")
            return -1
        elif captcha_code == -2:
            g_var.logger.info("识别验证码失败")
            return -2
        g_var.logger.info("captcha_code:" + captcha_code)

        registerData = {
            'user_notifications': '1',
            'submit_hidden': 'submit_hidden',
            'user_name': username,
            'user_email': email_and_passwd[0],
            'user_password': password,
            'user_terms': 'on',
            'captcha_solution': captcha_code,
            'submit': 'Create My Account',
        }

        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://pastebin.com',
            'referer': 'https://pastebin.com/signup',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36',
        }
        url = "https://pastebin.com/signup.php"
        result = Session.post(url, headers=headers, data=registerData, timeout=g_var.TIMEOUT)
        if result == -1:
            g_var.logger.error("提交注册信息超时")
            return -1

        success_signal = "Please click on the activation link to activate your account."
        if success_signal in result.text:
            g_var.logger.info("注册成功！" + result.text)
        else:
            email_used_signal = "The email address you picked is already in use"
            if email_used_signal in result.text:
                g_var.logger.info("邮箱已经被注册！" + result.text)
            return 0  # 跳出循环更换邮箱

        re_text = '(https://pastebin.com/activate_account.php\?.*?)"'
        email_verify_obj = EmailVerify(email_and_passwd[0], email_and_passwd[1], re_text)
        verify_url = account_activation(Session, email_verify_obj)
        if verify_url == -1:
            g_var.logger.info("2分钟内未收到激活邮件，激活失败！")
            resend_url = "https://pastebin.com/resend.php"
            headers = {
                ':authority': 'pastebin.com',
                ':method': 'POST',
                ':path': '/resend.php',
                ':scheme': 'https',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'cache-control': 'max-age=0',
                'content-type': 'application/x-www-form-urlencoded',
                'cookie': '__cfduid=d4e164af370e44d4de219e208cd6779061589887894; PHPSESSID=8ehi7ipdvopsmtqq9oaf1uk000; _ga=GA1.2.65423653.1589887895; _gid=GA1.2.805292117.1589887895; refit=L3Byb2ZpbGU%3D; _gat_UA-58643-34=1',
                'origin': 'https://pastebin.com',
                'referer': 'https://pastebin.com/resend.php?e=3',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
            }
            resendData = {

            }
            result = Session.post(resend_url, headers=headers, data=resendData, timeout=g_var.TIMEOUT)
            if result == -1:
                g_var.logger.error("提交重新激活超时")
                return -1
            verify_url = account_activation(Session, email_verify_obj)
            if verify_url == -1:
                g_var.logger.error("又没激活成功")
                return 0
        g_var.logger.info("verify_url" + verify_url)

        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36',
        }
        result = Session.get(url=verify_url, headers=headers, timeout=g_var.TIMEOUT)
        if result == -1:
            g_var.logger.error("访问激活链接超时")
            return -1

        # 获取cookie
        cookie = str(Session.cookies.get_dict())

        sql = "INSERT INTO " + present_website + "(username, password, mail, status, cookie) VALUES('" + username + \
              "', '" + password + "', '" + email_and_passwd[0] + "', '" + str(0) + "', \"" + cookie + "\");"
        last_row_id = MysqlHandler().insert(sql)
        if last_row_id != -1:
            registerData = dict()
            registerData["id"] = last_row_id
            registerData['username'] = username
            registerData['password'] = password
            registerData['email'] = email_and_passwd[0]
            registerData['cookie'] = cookie
            return registerData
        else:
            g_var.logger.error("数据库插入用户注册数据失败")
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
            sql = "UPDATE %s SET cookie='%s' WHERE id=%s ;" % (pastebin_com, save_cookies, user_id)
            status = MysqlHandler().update(sql)
            if status == 0:
                g_var.logger.info("cookie失效，清除cookie update OK")
                return {"error": -2}
            else:
                g_var.logger.error("数据库清除cookie错误!")
                return {"error": 1}    
        """
        user_id = userInfo[0]
        username = userInfo[1]
        password = userInfo[2]
        email = userInfo[3]
        cookie = userInfo[5]

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
        else:
            # cookie为空，使用账号密码登录
            login_url = "https://pastebin.com/login"
            data = {
                'submit_hidden': 'submit_hidden',
                'user_name': username,
                'user_password': password,
                'submit': 'Login',
            }

            headers = {
                'origin': 'https://pastebin.com',
                'referer': 'https://pastebin.com/login'
            }

            g_var.logger.info("账号登录中...")
            result = Session.post(login_url, data=data, headers=headers, timeout=g_var.TIMEOUT)
            if result == -1:
                g_var.logger.error("代理出错，登录超时")
                return -1

            login_success_signal = "this is your personal Pastebin"
            if login_success_signal in result.text:
                g_var.logger.info("login success!")
                cookie = str(Session.cookies.get_dict())
                sql = "UPDATE " + present_website + " SET cookie=\"" + cookie + "\" WHERE id=" + str(userInfo[0]) + ";"
                status = MysqlHandler().update(sql)
                if status == 0:
                    g_var.logger.info("update cookie OK")
                else:
                    g_var.logger.error("数据库更新cookie错误!")
                    return -2

                loginData = {
                    'id': user_id,
                    'username': username,
                    'password': password,
                    'email': email,
                    'cookie': cookie
                }
                return loginData
            else:
                g_var.logger.info("login fail!")
                g_var.logger.info(result.text)
                return 0

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
    
    def send_profile(self, Session, loginData: dict):
        """
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
        """
        update_url = 'https://pastebin.com/profile.php'
        headers = {
            'origin': 'https://pastebin.com',
            'referer': 'https://pastebin.com/profile.php',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
        }

        csrf_token = get_csrf_token(Session, headers, update_url, cookie=loginData['cookie'])
        if csrf_token == -1:
            return -1
        elif csrf_token == 0:
            return 0

        link = get_new_link()
        data = {
            'submit_hidden': 'submit_hidden',
            'csrf_token': csrf_token,
            'user_email': loginData["email"],
            'user_website': link,
            'user_location': '',
            'submit': 'Update Profile',
        }

        g_var.logger.info("提交个人资料中...")
        result = Session.post(update_url, data=data, headers=headers, timeout=g_var.TIMEOUT)
        if result == -1:
            g_var.logger.error("提交个人资料超时")
            return -1

        update_success_signal = "Your profile has been updated!"
        if update_success_signal in result.text:
            # 如果cookie失效，将该cookie从数据库中清除，并重新从数据库中获取登录账号密码
            g_var.logger.info("提交个人资料成功")
            return 'ok'
        else:
            cookie_failure_signal = "To login you can use any of these social media accounts"
            if cookie_failure_signal in result.text:
                g_var.logger.info("cookie过期，提交个人资料失败"+result.text)
                return 1

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
            #email_and_passwd = get_email(present_website)
            email_and_passwd = ['soathayxau@hotmail.com', '9gd31CIB']
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
                status = self.send_profile(Session, loginData)
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
