import re
import json
import sys
import random
import threading
import time
import email
import imaplib
from email.header import Header

import requests
from requests.adapters import HTTPAdapter

from project_utils.project_util import generate_login_data, ip_proxy, MysqlHandler, get_email, generate_random_string, get_new_link
from project_utils import g_var


def generate_headers(signal, loginData = None):
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
            'Host': 'www.wattpad.com',
            'Origin': 'https://www.wattpad.com',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Referer': 'https://www.wattpad.com/login',
        }
    elif signal == 1:
        headers = {
            'Host': 'www.wattpad.com',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'User-Agent': user_agent,
            'Content-Type': 'application/json',
            'Origin': 'https://www.wattpad.com',
            'Referer': 'https://www.wattpad.com/user/' + loginData['name'],
            'X-Requested-With': 'XMLHttpRequest',
            'Authorization': 'IwKhVmNM7VXhnsVb0BabhS',
            'Cookie': 'token=' + loginData['token'],
        }

    return headers

def generate_register_data(present_website, email_info):
    # 生成注册数据返回，并存入数据库
    try:
        username = generate_random_string(8, 12)
        password = generate_random_string(10, 14)
        registerData = {
            'signup-from': 'new_landing_undefined',
            'form-type': '',
            'username': username,
            'email': email_info[0],
            'password': password,
            'month': '05',
            'day': '21',
            'year': '1999',
        }
    except:
        g_var.logger.info("注册数据生成中出现异常...")
        return -1

    return registerData

# 邮箱读取数据(url)
class MyEmail(object):

    def __init__(self,username,password):
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
            msgFirstTen = msgList
        else:
            msgFirstTen = msgList[:-11:-1]
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

    def parseBody(self,message):
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
                    res = res.decode(encoding='utf-8')
                    res_text += res

        result = re.findall('This is me!: (.*?)\n', res_text)
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
            if self.inbox_unread == inbox_unseen and self.junk_unread == junk_unseen:
                self.inbox_unread = inbox_unseen
                self.junk_unread = junk_unseen
                return 0, 0, filename_list
            if self.junk_unread < junk_unseen:
                self.junk_unread = junk_unseen
                filename_list.append('junk')
            if self.inbox_unread < inbox_unseen:
                self.inbox_unread = inbox_unseen
                filename_list.append('INBOX')
            return inbox_unseen, junk_unseen, filename_list
        except:
            return 0, 0, []

    def Start(self):
        result = {}
        inbox_unseen, junk_unseen, filename_list=self.UnseenEmailCount()
        if inbox_unseen==0 and junk_unseen==0 and filename_list == []:
            result['msg'] = 'Read Failed'
            result['data'] = ''
            return result
        else:
            for i in filename_list:
                filename = i
                msg=self.get_mail(filename)
                if msg:
                    result['msg'] = 'Read Successfully'
                    result['data'] = msg
                    return result

    def execute_Start(self):
        read_times = 0
        while True:
            res = self.Start()
            if res['data']:
                return res
            if read_times == 30:
                res['msg'] = 'Mail Read Failed'
                res['data'] = ''
                return res
            read_times += 1
            time.sleep(2)

# 读取邮件，获取验证url
def get_verify_url(email_info):
    try:
        mye = MyEmail(email_info[0], email_info[1])
        verify_url = mye.execute_Start()
        if not verify_url['data']:
            g_var.logger.info("邮件的url读取失败...")
            return -1
        url = verify_url['data']
        return url
    except:
        g_var.logger.info("读取邮件中url出现异常...")
        return -1


class WattpadCom(object):
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

    def __register_one(self, Session, present_website):

        g_var.logger.info("register...")
        if headers == -1:
            g_var.logger.info("获取注册headers失败...")
            return -1

        email_info = get_email(present_website)
        g_var.logger.info(email_info)
        if email_info == -1:
            g_var.logger.info("获取邮箱号失败...")
            return -1

        registerData = generate_register_data(present_website, email_info)
        g_var.logger.info(registerData)
        if registerData == -1:
            g_var.logger.info("未获取到可用邮箱号或生成正确注册数据...")
            return -1

        url_register = 'https://www.wattpad.com/signup?nextUrl=/home'
        try:
            g_var.logger.info("提交注册中...")
            html = Session.post(url_register, data=registerData, headers=headers, timeout=g_var.TIMEOUT).text
            self.proxy_err_count = 0
        except Exception as e:
            g_var.logger.info(e)
            g_var.logger.error("提交注册信息超时")
            self.proxy_err_count = self.proxy_err_count + 1
            return -1

        # 注册成功与否验证
        prove_info = 'Hi @'+registerData['username']
        if prove_info not in html:
            self.failed_count += 1
            g_var.logger.info(html)
            g_var.logger.info("邮箱名已注册或者IP被封等原因...")
            return -1

        del headers['Origin']
        del headers['Content-Type']
        del headers['Referer']
        time.sleep(5)
        verify_url = get_verify_url(email_info)
        if verify_url == -1:
            g_var.logger.info("未读取到邮箱验证的url...")
            return -1
        try:
            g_var.logger.info("邮件的url正在验证中...")
            html = Session.get(url=verify_url, headers=headers, timeout=g_var.TIMEOUT)
            self.proxy_err_count = 0
        except:
            g_var.logger.error("邮件的url验证超时...")
            self.proxy_err_count = self.proxy_err_count + 1
            return -1
        if html.status_code == 200:
            sql = "INSERT INTO wattpad_com(username, password, mail, status) VALUES('" + registerData['username'] + \
                  "', '" + registerData['password'] + "', '" + registerData['email'] + "', '" + str(0) + "');"
            last_row_id = MysqlHandler().insert(sql)
            if last_row_id != -1:
                registerData["user_id"] = last_row_id
                return registerData
            else:
                g_var.logger.error("数据库插入失败")
                return -1
        else:
            self.failed_count += 1
            g_var.logger.error("邮箱验证失败！\n")
            return -1

    def __login(self, Session, VPN, userInfo):
        # 使用账号密码登录
        user_id = userInfo[0]
        username = userInfo[1]
        password = userInfo[2]
        loginData = {
            'username': userInfo[1],
            'password': userInfo[2],
        }

        retry_count = 0
        while retry_count < g_var.RETRY_COUNT_MAX:
            retry_count = retry_count + 1
            url_login = 'https://www.wattpad.com/login?nextUrl=/home'
            try:
                g_var.logger.info("使用账号密码登录...")
                headers = generate_headers(0)
                if headers == -1:
                    return -1
                html = Session.post(url_login, headers=headers, data=loginData, timeout=g_var.TIMEOUT)
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
            return -1

        if html.status_code != 200:
            # 如果登录失败将数据库中的status改为异常
            sql = "UPDATE wattpad_com SET status=1 WHERE id=" + str(user_id) + ";"
            MysqlHandler().update(sql)
            return 1  # 账号异常，重新取号登录

        token_list = re.findall('token=(.*?);', html.headers['Set-Cookie'])
        # 如果登录成功，则返回token_list和username给下一步发新文章
        loginSuccessData = {
            'id': user_id,
            'name': loginData['username'],
            'token': token_list[0],
        }
        return loginSuccessData

    def __postMessage(self, Session, loginData):

        headers = generate_headers(1, loginData)
        if headers == -1:
            return -1
        link = get_new_link()
        if link == -1:
            # 获取不到链接，程序停止
            g_var.SPIDER_STATUS = 3
            return -1

        url_putLink = 'https://www.wattpad.com/api/v3/users/' + loginData['name']
        linkData = {
            'website': link,
        }
        try:
            g_var.logger.info("发送链接中...")
            html = Session.put(url_putLink, headers=headers, json=linkData, timeout=g_var.TIMEOUT)
        except:
            g_var.logger.error("发链接超时!")
            return 1
        if html.status_code == 200:
            g_var.logger.info("链接发送成功！" + loginData["name"])
            url = 'https://www.wattpad.com/user/' + loginData["name"]
            # 将链接、用户存入wattpad_com_article表
            sql = "INSERT INTO wattpad_com_article(url, user_id) VALUES('" + url + "', '"  + str(loginData['id']) + "');"
            if g_var.insert_article_lock.acquire():
                last_row_id = MysqlHandler().insert(sql)
                g_var.insert_article_lock.release()
            if last_row_id != -1:
                g_var.logger.info("insert article OK")
            else:
                g_var.logger.error("数据库插入链接错误!")
                return 1
            return 0
        else:
            g_var.logger.error("链接发送失败！\n" + html)
            g_var.ERR_CODE = 5000
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "链接发送失败，未知错误!"
            return 1

    def registers(self, present_website, VPN):
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
                g_var.logger.info('in register......')
                retry_count = retry_count + 1
                registerData = self.__register_one(Session, present_website)
                if registerData != -1:
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

    def loginAndPostMessage(self, present_website, VPN):
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
                userInfo = generate_login_data(present_website)
                g_var.logger.error('...userInfo...')
                g_var.logger.error(userInfo)
                if userInfo == None:
                    g_var.logger.error("数据库中获取用户失败，本线程停止！")
                    return {"error": -1}
                else:
                    loginData = self.__login(Session, VPN, userInfo)
                    if loginData == -1:
                        # 登录报错，停止运行\
                        g_var.logger.error("登录出错，更换代理。。。")
                        g_var.ERR_MSG = "登录出错"
                        self.failed_count = self.failed_count + 1
                        time.sleep(g_var.SLEEP_TIME)
                        proxies = ip_proxy(VPN)
                        Session.proxies = proxies
                        continue
                    elif loginData == 1:
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

            # 2、发链接
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                status = self.__postMessage(Session, loginData)
                if status == 0:  # 发链接成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
                elif status == 1:
                    self.failed_count = self.failed_count + 1
                    self.proxy_err_count = self.proxy_err_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    # g_var.logger.info("proxies"+str(proxies))
                elif status == -1:
                    # 获取不到链接，程序停止
                    self.failed_count = self.failed_count + 1
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = "连续发文章出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功发送" + str(self.success_count) + "个链接")

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
                    self.failed_count = 0
                    break
                else:
                    # 失败更换代理
                    g_var.logger.info("注册失败" + str(registerData))
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    self.failed_count = self.failed_count + 1
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
                userInfo = (registerData['user_id'], registerData['username'], registerData['password'])
                loginData = self.__login(Session, VPN, userInfo)
                if loginData == -1:
                    # 登录报错，停止运行
                    g_var.ERR_MSG = "登录出错"
                    self.failed_count = self.failed_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                    continue
                elif loginData == 1:
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

            # 3、发链接
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                status = self.__postMessage(Session, loginData)
                if status == 0:  # 发链接成功
                    self.success_count = self.success_count + 1
                    self.failed_count = 0
                    self.proxy_err_count = 0
                    break
                elif status == 1:
                    self.failed_count = self.failed_count + 1
                    self.proxy_err_count = self.proxy_err_count + 1
                    time.sleep(g_var.SLEEP_TIME)
                    proxies = ip_proxy(VPN)
                    Session.proxies = proxies
                elif status == -1:
                    # 获取不到链接，程序停止
                    self.failed_count = self.failed_count + 1
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = "连续发链接出错，程序停止"
                g_var.logger.error("连续发链接出错，程序停止")
                break
        g_var.logger.info("成功注册账户并发送链接" + str(self.success_count) + "个。")
