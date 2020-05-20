import time
import requests
import random
import json
import re

from project_utils import requestsW

from requests_toolbelt.multipart.encoder import MultipartEncoder

from project_utils.project_util import generate_login_data, MysqlHandler, google_captcha, generate_random_string, ip_proxy, get_new_title_and_link
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
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://auth.voxmedia.com',
            'referer': 'https://auth.voxmedia.com/signup?return_to=https://www.sbnation.com/',
            'user-agent': user_agent,
            'x-requested-with': 'XMLHttpRequest',
        }
    if signal == 1:
        headers = {
            'Host': 'www.sbnation.com',
            'Origin': 'https://www.sbnation.com',
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        }
    if signal == 2:
        # 使用固定header
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Host': 'auth.voxmedia.com',
            'Origin': 'https://auth.voxmedia.com',
            'Referer': 'https://auth.voxmedia.com/login?return_to=https://www.sbnation.com/',
            'User-Agent': user_agent,
            'X-Requested-With': 'XMLHttpRequest',
        }
    return headers

# 获取session_id
def get_session_id():
    try:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
        }
        url = 'https://auth.voxmedia.com/signup?return_to=https://www.sbnation.com/'
        res = requestsW.get(url, proxies=ip_proxy("en"), headers=headers, timeout=g_var.TIMEOUT)
        if res == -1:
            return res
        str_session = res.headers['Set-Cookie']
        if not str_session:
            g_var.logger.info('获取session_id值失败。。。')
            return -2
        list_session = str_session.split(';')
        if not list_session:
            g_var.logger.info('获取_session_id值失败。。。')
            return -2
        return list_session[0]
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取session_id出现异常..."
        g_var.logger.info("获取session_id出现异常...")
        return -2

# 获取登录session_id
def get_login_session_id():
    try:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
        }
        url = 'https://auth.voxmedia.com/login?return_to=https://www.sbnation.com/'
        res = requestsW.get(url, proxies=ip_proxy("en"), headers=headers, timeout=g_var.TIMEOUT)
        if res == -1:
            return res
        str_session = res.headers['Set-Cookie']
        if not str_session:
            g_var.logger.info('获取Set-Cookie值失败。。。')
            return -2
        list_session = str_session.split(';')
        if not list_session:
            g_var.logger.info('获取_session_id值失败。。。')
            return -2
        return list_session[0]
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取session_id出现异常..."
        g_var.logger.info("获取session_id出现异常...")
        return -2

# 获取authenticity_token用于修改个人网址
def get_authenticity_token(userData):
    try:
        headers = {
            'Host': 'www.sbnation.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Referer': 'https://www.sbnation.com/users/' + userData['username'],
            'Cookie': '_session_id=' + userData['cookie'],
        }
        url = 'https://www.sbnation.com/users/' + userData['username'] +  '/edit_profile'
        res = requestsW.get(url, proxies=ip_proxy("en"), headers=headers)
        if res == -1:
            return -1, -1
        token_list = re.findall('name="authenticity_token" value="(.*?)" />', res.text)
        if not token_list:
            g_var.logger.info('获取修改个人网址的authenticity_token失败。。。')
            return -2, -2
        session_list = re.findall('_session_id=(.*?);', res.headers['Set-Cookie'])
        if not session_list:
            g_var.logger.info('获取修改个人网址的session_id失败。。。')
            return -2, -2
        return token_list[0], session_list[0]
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取authenticity_token出现异常..."
        g_var.logger.info("获取authenticity_token出现异常...")
        return -2, -2

class SbnationCom(object):
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
            0：数据库存储失败
            -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
            -2:注册失败，可能是打码出错等原因
        """
        g_var.logger.info('register......')
        headers = generate_headers(0)
        if headers == -1:
            return -1
        g_var.logger.info('session_id......')
        session_id = get_session_id()
        if session_id == -1:
            return -1
        elif session_id == -2:
            return -2
        googlekey = '6LefyhkTAAAAANpeEKwwgimNneiKWXRQtEqFZbat'
        captcha_value = google_captcha("", googlekey, 'https://auth.voxmedia.com/signup?return_to=https://www.sbnation.com/')
        if captcha_value == -1:
            return -2
        headers['cookie'] = session_id
        username = generate_random_string(8, 12)
        password = generate_random_string(10, 14)
        community_id = random.randint(210, 299)
        g_var.logger.info('community_id.....')
        g_var.logger.info(community_id)
        email = username + '@hotmail.com'
        registerData = {
            'g-recaptcha-response': captcha_value,
            'user[username]': username,
            'user[password]': password,
            'user[email]': email,
            'user[newsletter]': 'false',
            'community_id': community_id,
        }
        g_var.logger.info('开始提交注册信息...')
        url_login = 'https://auth.voxmedia.com/chorus_auth/register.json'
        html = requestsW.post(url_login, proxies=ip_proxy("en"), data=registerData, headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html
        try:
            g_var.logger.info(html.text)
            res_data = json.loads(html.text)
        except Exception as e:
            g_var.logger.info(e)
            g_var.logger.info('注册失败，返回信息解析失败。。。')
            g_var.logger.info(html.text)
            return -2
        if not res_data['success']:
            g_var.logger.info('注册失败。。。')
            g_var.logger.info(html.text)
            return -2
        try:
            sql = "INSERT INTO " + present_website + "(username, password, mail) VALUES('" + \
                  username + "', '" + password + "', '" + email + "');"
            last_row_id = MysqlHandler().insert(sql)
            g_var.logger.info(last_row_id)
            if last_row_id != -1:
                g_var.logger.info('注册成功！' + username)
                userData = {
                    'id': last_row_id,
                    'username': username,
                    'password': password,
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

    def login(self, present_website, VPN, userData):
        """
        登录
        Args:
            Session：Session对象
            present_website：当前网站名，用于数据库表名
            VPN：使用国内or国外代理
            userInfo：用户信息  userInfo[0]:id [1]:username [2]passwod [3]:emial [4]:status
        Returns:
            成功返回loginData
                loginData = {
                    'id': user_id,
                    'username': username,
                    'password': password,
                    'email': email,
                }
            失败返回状态值：
                1:表示账号密码失效，密码被改或账号被网站删除，将数据库中状态改为1，并跳出循环重新取账号
                0:跳出循环，重新取号
                -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
                -2:本次出错，不跳出循环
        Mysql Update示例:
            # 如果cookie失效，将该cookie从数据库中清除，并重新从数据库中获取登录账号密码
            sql = "UPDATE %s SET cookie='%s' WHERE id=%s ;" % (sbnation_com, save_cookies, user_id)
            status = MysqlHandler().update(sql)
            if status == 0:
                g_var.logger.info("cookie失效，清除cookie update OK")
                return {"error": -2}
            else:
                g_var.logger.error("数据库清除cookie错误!")
                return {"error": 1}    
        """
        g_var.logger.info('login ......')
        headers = generate_headers(2)
        if headers == -1:
            return -1
        login_session_id = get_login_session_id()
        headers['Cookie'] = login_session_id
        login_data = {
            'username': userData['username'],
            'password': userData['password'],
            'remember_me': 'false',
            'g-recaptcha-response': '',
        }
        login_url = 'https://auth.voxmedia.com/chorus_auth/initiate_password_auth.json'
        g_var.logger.info('登录中 ......')
        html = requestsW.post(login_url, proxies=ip_proxy("en"), data=login_data, headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html
        try:
            g_var.logger.info(html.text)
            res_data = json.loads(html.text)
        except Exception as e:
            g_var.logger.info(e)
            g_var.logger.info('登录失败，返回信息解析失败。。。')
            g_var.logger.info(html.text)
            return 1
        if not res_data['logged_in']:
            g_var.logger.info('登录失败。。。')
            g_var.logger.info(html.text)
            return 1
        session_id_article = re.findall('_session_id=(.*?);', html.headers['Set-Cookie'])
        if not session_id_article:
            return 1
        userData['cookie'] = session_id_article[0]
        return userData

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
        g_var.logger.info('send profile......')
        headers = generate_headers(1)
        if headers == -1:
            return -1
        g_var.logger.info('authenticity_token, session_id...')
        authenticity_token, session_id = get_authenticity_token(userData)
        if authenticity_token == -1 or session_id == -1:
            return -1
        elif authenticity_token == -2 or session_id == -2:
            return 1
        headers['Referer'] = 'https://www.sbnation.com/users/' + userData['username'] + '/edit_profile'
        headers['Cookie'] = '_session_id=' + session_id
        titleLink = get_new_title_and_link()
        if titleLink == -1:
            return -1
        multipart_encoder = MultipartEncoder(
            fields={
                'utf8': '✓',
                '_method': 'patch',
                'authenticity_token': authenticity_token,
                'profile_image[filename]': ('', '', 'application/octet-stream'),
                'profile_image[filename_cache]': '',
                'network_membership[bio]': '',
                'network_membership[signature]': '',
                'network_membership[public_email]': '',
                'network_membership[website_name]': titleLink[0],
                'network_membership[website_url]': titleLink[1],
                'network_membership[facebook_page_url]': '',
                'network_membership[facebook_page_url]': '',
                'network_membership[network_membership_items_attributes][0][key]': 'MLB',
                'network_membership[network_membership_items_attributes][0][value]': '',
                'network_membership[network_membership_items_attributes][1][key]': 'NFL',
                'network_membership[network_membership_items_attributes][1][value]': '',
                'network_membership[network_membership_items_attributes][2][key]': 'NBA',
                'network_membership[network_membership_items_attributes][2][value]': '',
                'network_membership[network_membership_items_attributes][3][key]': 'NHL',
                'network_membership[network_membership_items_attributes][3][value]': '',
                'network_membership[network_membership_items_attributes][4][key]': 'NCAAF',
                'network_membership[network_membership_items_attributes][4][value]': '',
                'network_membership[network_membership_items_attributes][5][key]': 'NCAAB',
                'network_membership[network_membership_items_attributes][5][value]': '',
                'network_membership[network_membership_items_attributes][6][key]': 'MMA',
                'network_membership[network_membership_items_attributes][6][value]': '',
                'network_membership[network_membership_items_attributes][7][key]': 'Golf',
                'network_membership[network_membership_items_attributes][7][value]': '',
                'network_membership[network_membership_items_attributes][8][key]': 'NASCAR',
                'network_membership[network_membership_items_attributes][8][value]': '',
                'network_membership[network_membership_items_attributes][9][key]': 'Boxing',
                'network_membership[network_membership_items_attributes][9][value]': '',
                'network_membership[network_membership_items_attributes][10][key]': 'Soccer',
                'network_membership[network_membership_items_attributes][10][value]': '',
                'network_membership[network_membership_items_attributes][11][key]': 'MLS',
                'network_membership[network_membership_items_attributes][11][value]': '',
                'network_membership[network_membership_items_attributes][12][key]': 'EPL',
                'network_membership[network_membership_items_attributes][12][value]': '',
                'network_membership[network_membership_items_attributes][13][key]': 'Football League Championship',
                'network_membership[network_membership_items_attributes][13][value]': '',
                'network_membership[network_membership_items_attributes][14][key]': 'FIFA',
                'network_membership[network_membership_items_attributes][14][value]': '',
                'network_membership[network_membership_items_attributes][15][key]': 'Bundesliga',
                'network_membership[network_membership_items_attributes][15][value]': '',
                'network_membership[network_membership_items_attributes][16][key]': 'Serie A',
                'network_membership[network_membership_items_attributes][16][value]': '',
                'network_membership[network_membership_items_attributes][17][key]': 'La Liga',
                'network_membership[network_membership_items_attributes][17][value]': '',
                'network_membership[network_membership_items_attributes][18][key]': 'Cycling',
                'network_membership[network_membership_items_attributes][18][value]': '',
                'network_membership[network_membership_items_attributes][19][key]': 'Tennis',
                'network_membership[network_membership_items_attributes][19][value]': '',
                'network_membership[network_membership_items_attributes][20][key]': 'General',
                'network_membership[network_membership_items_attributes][20][value]': '',
                'commit': 'Update',
            },
            boundary='----WebKitFormBoundary' + generate_random_string(16, 16, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        )
        headers['Content-Type'] = multipart_encoder.content_type
        g_var.logger.info("发布个人简介的链接...")
        url_link = 'https://www.sbnation.com/users/' + userData['username'] + '/update_profile'
        html = requestsW.post(url_link, proxies=ip_proxy("en"), data=multipart_encoder, headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html
        if html.status_code != 200:
            g_var.logger.info('链接发布失败。。。')
            g_var.logger.info(html.text)
            return -2
        try:
            url = 'https://www.sbnation.com/users/' + userData['username']
            sql = "INSERT INTO sbnation_com_article(url, user_id) VALUES('" + url + "', '" + str(userData["id"]) + "');"
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

    def registers(self, present_website: str, VPN: str):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                userData = self.__register_one(present_website)
                if userData == 0:
                    g_var.logger.info("注册失败，数据库存储失败！")
                    self.failed_count = self.failed_count + 1
                    register_signal = 1
                    continue
                elif userData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误！"
                    g_var.logger.info("代理错误！")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif userData == -2:
                    g_var.logger.info("注册失败，可能密码不符合要求等原因！")
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
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误！"
                    g_var.logger.info("代理错误！")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif userData == -2:
                    g_var.logger.info("注册失败，可能密码不符合要求等原因！")
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
            login_signal = 0
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                loginData = self.login(present_website, VPN, userData)
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

            # 2、发个人简介
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                time.sleep(g_var.SLEEP_TIME)
                retry_count = retry_count + 1
                status = self.__send_profile(loginData)
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
                    g_var.logger.info("获取authenticity_token和session_id值失败；链接发布成功，但数据存储失败！")
                    self.failed_count = self.failed_count + 1
                    continue
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续发链接出错，程序停止"
                g_var.logger.error("连续发链接出错，程序停止")
                break
        g_var.logger.info("成功发送" + str(self.success_count) + "则个人简介。")

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
