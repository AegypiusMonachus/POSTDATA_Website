import time
import requests
import uuid
import re

from project_utils import requestsW

from project_utils.project_util import generate_login_data, MysqlHandler, google_captcha, get_new_link, generate_random_string, ip_proxy, get_keyword, get_text
from project_utils import g_var

def generate_headers(signal):
    try:
        headers = {
            'Connection': 'close',
        }
        requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
        with requests.get(url=g_var.INTERFACE_HOST + "/v1/get/user_agent/", headers=headers,
                          timeout=g_var.TIMEOUT) as r:
            user_agent = r.text
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 2005
        g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "user_agent获取失败!"
        g_var.logger.error("user_agent获取失败!")
        return -1
    if signal == 0:
        # 使用固定header
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'referer': 'https://unsplash.com/',
            'user-agent': user_agent,
        }
    return headers

# 获取注册所需authenticity_token、cookie值
def get_authenticity_token(headers):
    try:
        url = 'https://unsplash.com/join'
        res = requestsW.get(url, proxies=ip_proxy("en"), headers=headers)
        if res == -1:
            return -1, -1
        authenticity_token = re.findall('name="authenticity_token" value="(.*?)" />', res.text)
        if not authenticity_token:
            g_var.logger.info('未获取到authenticity_token、cookie值...')
            return -2, -2
        cookie = res.cookies.get_dict()
        return authenticity_token[0], cookie
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取authenticity_token、cookie值出现异常..."
        g_var.logger.info("获取authenticity_token、cookie值出现异常...")
        return -2, -2

# 获取修改个人资料所需的authenticity_token, cookie值
def get_profile_cookie(userData, headers):
    try:
        u = uuid.uuid4()
        url = 'https://unsplash.com/account'
        del headers['referer']
        headers['referer'] = 'https://unsplash.com/@'+ userData['username']
        c = eval(userData['cookie'])
        headers['cookie'] = 'ugid=' + c['ugid'] + '; uuid=' + str(u) + '; auth_user_id=' + c['auth_user_id'] + '; un_sesh='+ c['un_sesh']
        res = requestsW.get(url, proxies=ip_proxy("en"), headers=headers)
        if res == -1:
            return -1, -1
        authenticity_token = re.findall('name="authenticity_token" value="(.*?)" />', res.text)
        if len(authenticity_token) != 2:
            g_var.logger.info('未获取到个人资料所需的authenticity_token, cookie值...')
            return -2, -2
        cookie = res.cookies.get_dict()
        return authenticity_token[-1], cookie
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取个人资料所需的authenticity_token, cookie值出现异常..."
        g_var.logger.info("获取个人资料所需的authenticity_token, cookie值出现异常...")
        return -2, -2

class UnsplashCom(object):
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

    def __register_one(self, present_website):
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
        g_var.logger.info('register ...')
        headers = generate_headers(0)
        if headers == -1:
            return -1
        g_var.logger.info('authenticity_token, cookie...')
        authenticity_token, cookie = get_authenticity_token(headers)
        if authenticity_token == -1 or cookie == -1:
            return -1
        elif authenticity_token == -2 or cookie == -2:
            return -2
        u = uuid.uuid4()
        headers['content-type'] = 'application/x-www-form-urlencoded'
        headers['origin'] = 'https://unsplash.com'
        headers['referer'] = 'https://unsplash.com/join'
        headers['cookie'] = 'ugid=' + cookie['ugid'] + '; uuid=' + str(u) + '; un_sesh=' + cookie['un_sesh']
        googleKey = '6Lf3Om8UAAAAADFWLvq5hvCv2gGk-QQ2E441cMZ0'
        captcha_value = google_captcha('', googleKey, 'https://unsplash.com/join')
        if captcha_value == -1:
            return -2
        char = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        first_name = generate_random_string(8, 10, char)
        last_name = generate_random_string(8, 10, char)
        username = generate_random_string(8, 10)
        password = generate_random_string(10, 14)
        email = username + '@hotmail.com'
        data = {
            'utf8': '✓',
            'authenticity_token': authenticity_token,
            'user[first_name]': first_name,
            'user[last_name]': last_name,
            'user[email]': email,
            'user[username]': username,
            'user[password]': password,
            'after_authorization_action': '',
            'after_authorization_object_id': '',
            'g-recaptcha-response': captcha_value,
        }
        g_var.logger.info('提交注册信息...')
        register_url = 'https://unsplash.com/join'
        html = requestsW.post(register_url, proxies=ip_proxy("en"), data=data, headers=headers, allow_redirects=False)
        if html == -1:
            return -1
        try:
            register_cookie = html.cookies.get_dict()
        except Exception as e:
            g_var.logger.info(e)
            g_var.logger.info('注册失败，返回响应值失败。。。')
            g_var.logger.info(html.headers)
            return -2
        if len(register_cookie) != 3:
            g_var.logger.info('注册失败。。。')
            g_var.logger.info(html.headers)
            return -2
        try:
            sql = "INSERT INTO " + present_website + "(username, password, mail) VALUES('" + \
                  email + "', '" + password + "', '" + email + "');"
            last_row_id = MysqlHandler().insert(sql)
            g_var.logger.info(last_row_id)
            if last_row_id != -1:
                g_var.logger.info('注册成功！' + username)
                userData = {
                    'id': last_row_id,
                    'first_name': first_name,
                    'last_name': last_name,
                    'username': username,
                    'email': email,
                    'cookie': str(register_cookie),
                }
                return userData
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
            sql = "UPDATE %s SET cookie='%s' WHERE id=%s ;" % (unsplash_com, save_cookies, user_id)
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
    
    def __send_profile(self, userData):
        """
        发个人简介
        Args:
            Session：Session对象
            loginData：用户信息，包括user_id,username,password,email,cookie
        Returns:
            成功返回:0
            失败返回状态值：
                1:数据库存储失败
                -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
                -2:本次出错，继续循环
        """
        g_var.logger.info('send_profile...')
        headers = generate_headers(0)
        if headers == -1:
            return -1
        new_link = get_new_link()
        if new_link == -1:
            return -1
        wenben = get_text()
        if wenben == -1:
            return -1
        bio = wenben[:240]
        keyword = get_keyword()
        if keyword == -1:
            return -1
        authenticity_token, cookie = get_profile_cookie(userData, headers)
        if authenticity_token == -1 or cookie == -1:
            return -1
        if authenticity_token == -2 or cookie == -2:
            return -2
        u = uuid.uuid4()
        c = eval(userData['cookie'])
        headers['content-type'] = 'application/x-www-form-urlencoded'
        headers['origin'] = 'https://unsplash.com'
        headers['referer'] = 'https://unsplash.com/account'
        headers['cookie'] = 'ugid=' + cookie['ugid'] + '; uuid=' + str(u) + '; auth_user_id=' + c['auth_user_id'] + '; un_sesh='+ cookie['un_sesh']
        profile_data = {
            'utf8': '✓',
            '_method': 'put',
            'authenticity_token': authenticity_token,
            'user[first_name]': userData['first_name'],
            'user[last_name]': userData['last_name'],
            'user[email]': userData['email'],
            'user[username]': userData['username'],
            'user[url]': new_link,
            'user[location]': '',
            'user[instagram_username]': '',
            'user[twitter_account_attributes][id]': '',
            'user[twitter_account_attributes][username]': '',
            'user[bio]': bio,
            'user[user_tags_set][custom_tags]': keyword,
            'user[allow_messages]': '0',
            'user[allow_messages]': '1',
            'commit': 'Update account',
        }
        g_var.logger.info('提交个人资料信息...')
        profile_url = 'https://unsplash.com/account'
        html = requestsW.post(profile_url, proxies=ip_proxy("en"), data=profile_data, headers=headers)
        if html == -1:
            return -1
        if new_link not in html.text:
            g_var.logger.info('个人资料修改失败。。。')
            g_var.logger.info(html.status_code)
            return -2
        try:
            url = 'https://unsplash.com/@' + userData['username'].lower()
            sql = "INSERT INTO unsplash_com_article(url, keyword, user_id) VALUES('" + url + "', '"  + keyword + "', '" + str(userData["id"]) + "');"
            last_row_id = MysqlHandler().insert(sql)
            g_var.logger.info(last_row_id)
            if last_row_id != -1:
                g_var.logger.info('链接发送成功！' + userData['username'])
                return 0
            else:
                g_var.ERR_CODE = 2004
                g_var.ERR_MSG = "数据库插入用户注册数据失败..."
                g_var.logger.error("数据库插入用户注册数据失败...")
                return 1
        except Exception as e:
            g_var.logger.info(e)
            g_var.ERR_CODE = 2004
            g_var.ERR_MSG = "数据库插入用户注册数据异常..."
            g_var.logger.error("数据库插入用户注册数据异常...")
            return 1

    def registers(self, present_website, VPN):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(present_website)
                if registerData == 0:
                    g_var.logger.info("注册成功，但数据库存储失败！")
                    self.failed_count = self.failed_count + 1
                    register_signal = 1
                    continue
                elif registerData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理连续错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif registerData == -2:
                    g_var.logger.info("注册失败，可能是密码不符合要求等原因，不跳出循环")
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
    
    def registerAndSendProfile(self, present_website, VPN):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1
            retry_count = 0
            register_signal = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                userData = self.__register_one(present_website)
                if userData == 0:
                    g_var.logger.info("注册成功，但数据库存储失败！")
                    self.failed_count = self.failed_count + 1
                    register_signal = 1
                    continue
                elif userData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif userData == -2:
                    g_var.logger.info("注册失败，可能是密码不符合要求等原因，不跳出循环")
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
                
            # 2、发个人简介
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                time.sleep(g_var.SLEEP_TIME)
                retry_count = retry_count + 1
                status = self.__send_profile(userData)
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
                    continue
                elif status == 1:
                    g_var.logger.info("获取authenticity_token和session_id值失败；链接发布成功，但数据存储失败！")
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
