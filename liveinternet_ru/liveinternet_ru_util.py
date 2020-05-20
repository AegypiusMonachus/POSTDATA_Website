import time
import re
import json
import random
import requests
import email
import imaplib

from requests_toolbelt.multipart.encoder import MultipartEncoder

from project_utils import requestsW
from project_utils.project_util import generate_login_data, MysqlHandler, get_Session, get_email, google_captcha, generate_random_string, \
    ip_proxy, get_new_article
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
            "Host": "www.liveinternet.ru",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "User-Agent": user_agent,
        }
    return headers

# 获取注册第一步tok
def get_tok(url, headers):
    try:
        res = requestsW.get(url, proxies=ip_proxy("en"), headers=headers, timeout=g_var.TIMEOUT)
        if res == -1:
            return res
        tok = re.findall('<input type=hidden name=tok value=(.*?) /></form>', res.text)
        if not tok:
            g_var.logger.info("未获取到tok...")
            return -2
        return tok[0]
    except:
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取tok出现异常..."
        g_var.logger.info("获取tok出现异常...")
        return -2

# 获取邮箱验证tok
def get_tok_email(url):
    try:
        res = requestsW.get(url, proxies=ip_proxy("en"), timeout=g_var.TIMEOUT)
        if res == -1:
            return res
        tok = re.findall('<input type=hidden name=tok value=(.*?) /></form>', res.text)
        if not tok:
            g_var.logger.info("未获取到邮箱验证的tok...")
            return -2
        return tok[0]
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取邮箱验证的tok出现异常..."
        g_var.logger.info("获取邮箱验证的tok出现异常...")
        return -2

def generate_register_data(email_info, captcha_value, tok):
    # 生成注册数据返回
    try:
        password = generate_random_string(10, 14)
        data_user = {
            'email': email_info[0],
            'password1': password,
            'password2': password,
            'g-recaptcha-response': captcha_value,
            'action': 'add_step0',
            'Submit.x': '60',
            'Submit.y': '25',
            'tok': tok,
        }
    except Exception as e:
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "注册数据生成中出现异常..."
        g_var.logger.info("注册数据生成中出现异常...")
        g_var.logger.info(e)
        return -1
    return data_user

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
            msgFirstTen.reverse()
        else:
            msgFirstTen = msgList[-1:-11:-1]
        msgLen = len(msgFirstTen)
        i = 0
        for eachEmail in msgFirstTen:
            i += 1
            typ, datas = self.server.fetch(eachEmail, '(RFC822)')
            # 使用utf-8解码
            text = datas[0][1].decode('ISO-8859-1')
            result = re.search('http?://www.liveinternet.ru/journal_register.php\?(?:[-\w.=&]|(?:%[\da-fA-F]{2}))+',
                               text)
            if result:
                result = result.group()
                return result
            if i == msgLen:
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
    except Exception as e:
        g_var.logger.info(e)
        g_var.logger.info("读取邮件中url出现异常...")
        return 0

# 获取文章发布页tok值
def get_postarticle_tok(uid):
    try:
        url_tok = 'https://www.liveinternet.ru/journal_post.php?journalid=' + uid
        response = requestsW.get(url_tok, proxies=ip_proxy("en"))
        if response == -1:
            return -1
        result = re.findall('<input type=hidden name=tok value=(.*?) /></form>', response.text)
        if not result:
            g_var.logger.info("未获取到文章发布页tok...")
            return -2
        tok = result[0]
        return tok
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取文章发布页tok出现异常..."
        g_var.logger.info("获取文章发布页tok出现异常...")
        return -2

# 为文章正文编码
def get_code_content(text):
    try:
        str_text = text.encode('ascii', "xmlcharrefreplace")
        LiNewPostForm = bytes.decode(str_text)
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "文章正文编码出现异常..."
        g_var.logger.info("文章正文编码出现异常...")
        return -2
    return LiNewPostForm

# 获取新文章ID
def get_newarticle_Id(uid_upwd, title, headers):
    try:
        headers['Accept'] = '*/*'
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        headers['Cookie'] = 'bbuserid=' + uid_upwd[0]  + '; bbpassword=' + uid_upwd[1]
        headers['Origin'] = 'https://www.liveinternet.ru'
        headers['Referer'] = 'https://www.liveinternet.ru/journal_post.php?journalid=' + uid_upwd[0]
        data = {
            'postid': '0',
            'journalid': uid_upwd[0],
            'headerofpost': title,
            'message': None,
            'tags': None,
        }
        url_id = 'https://www.liveinternet.ru/journal_autosave.php?doajax=1'
        response = requestsW.post(url_id, data=data, headers=headers)
        if response == -1:
            return -1
        if 'NOAccess denied' in response.text:
            return 1
        blog_Id = re.findall('OK(.*?)\|', response.text)
        if not blog_Id:
            g_var.logger.info("获取新文章ID失败...")
            return -2
        article_Id = blog_Id[0]
        return article_Id
    except Exception as e:
        g_var.logger.info(e)
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = "获取新文章ID出现异常..."
        g_var.logger.info("获取新文章ID出现异常...")
        return -2

class LiveinternetRu(object):
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

    def __register_one(self, present_website, email_and_passwd):
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
        g_var.logger.info('register......')
        url = 'http://www.liveinternet.ru/journal_register.php'
        headers = generate_headers(0)
        if headers == -1:
            g_var.logger.info("获取headers失败...")
            return -1
        tok = get_tok(url, headers)
        if tok == -1:
            return -1
        elif tok == -2:
            return -2
        googlekey = '6Lcl3BYUAAAAAG1gTAOhNtJIeTrPn68melrC1gbV'
        captcha_value = google_captcha("", googlekey, url)
        if captcha_value == -1:
            return -2
        registerData = generate_register_data(email_and_passwd, captcha_value, tok)
        headers['Origin'] = 'http://www.liveinternet.ru'
        headers['Referer'] = 'http://www.liveinternet.ru/journal_register.php'
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        g_var.logger.info("提交注册中...")
        html = requestsW.post(url, proxies=ip_proxy("en"), data=registerData, headers=headers, timeout=g_var.TIMEOUT)
        if html == -1:
            return html
        # 第一步注册成功与否的验证
        result = re.findall(email_and_passwd[0], html.text)
        if len(result) != 2:
            g_var.logger.info("第一步注册失败...")
            g_var.logger.info(html.status_code)
            return -2
        # 邮箱验证
        time.sleep(2)
        verify_url = get_verify_url(email_and_passwd)
        if verify_url == 0:
            g_var.logger.info("未读取到邮箱验证的url...")
            return 0
        # 邮箱验证的tok获取
        email_tok = get_tok_email(verify_url)
        if email_tok == -1:
            return 0
        elif email_tok == -2:
            return 0
        id = re.findall('id=(.*?)&', verify_url)[0]
        h = re.findall('h=(.*)', verify_url)[0]
        headers['Referer'] = verify_url
        captcha_value = google_captcha("", googlekey, verify_url)
        if captcha_value == -1:
            return 0
        username = generate_random_string(10, 12, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        day = str(random.randint(1, 28))
        month = str(random.randint(1, 12))
        year = str(random.randint(1980, 2010))
        sex = ['M', 'W']
        multipart_encoder = MultipartEncoder(
            fields={
                'username': username,
                'comm': '0',
                'sexchar': random.choice(sex),
                'day': day,
                'month': month,
                'year': year,
                'city': '1870',
                'icq': '',
                'emails': '',
                'addinfo': username,
                'avatarfile': ('', '', 'application/octet-stream'),
                'g-recaptcha-response': captcha_value,
                'dailynews': '1',
                'Submit.x': '80',
                'Submit.y': '20',
                'familyname': '',
                'firstname': '',
                'password': registerData['password1'],
                'email': email_and_passwd[0],
                'passwordconfirm': registerData['password1'],
                'imagehash': '',
                'regkey': '',
                'invite_id': '0',
                'regkeynb': '',
                'url_redirect': '',
                'url2': '',
                'action': 'add_step1',
                'h': h,
                'id': id,
                'tok': email_tok,
            },
            boundary='----WebKitFormBoundary' + generate_random_string(16, 16, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        )
        headers['Content-Type'] = multipart_encoder.content_type
        g_var.logger.info("注册第二步，邮箱验证提交信息中...")
        url_email_prove = 'http://www.liveinternet.ru/journal_register.php'
        html = requestsW.post(url_email_prove, proxies=ip_proxy("en"), data= multipart_encoder, headers=headers, allow_redirects=False, timeout=g_var.TIMEOUT)
        if html == -1:
            return html
        if not html.headers.get('Set-Cookie', None):
            g_var.logger.info('第二步邮箱验证信息提交失败...')
            return 0
        # 将注册的账户写入数据库
        try:
            set_cookie = html.headers['Set-Cookie']
            user_Id = re.findall('bbuserid=(.*?);', set_cookie)
            user_password = re.findall('bbpassword=(.*?);', set_cookie)
            cookie = user_Id[0] + '|_|' + user_password[0]
            sql = "INSERT INTO " + present_website + "(username, password, mail, cookie) VALUES('" + \
                  username + "', '" + registerData['password1'] + "', '" + email_and_passwd[0] + "', '" + cookie + "');"
            last_row_id = MysqlHandler().insert(sql)
            g_var.logger.info(last_row_id)
            if last_row_id != -1:
                g_var.logger.info('注册成功！' + username)
                userData = {
                    'id': last_row_id,
                    'username': username,
                    'password': registerData['password1'],
                    'cookie': cookie,
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

    def login(self, present_website, VPN, userInfo):
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
                    'cookie': cookie,
                }
            失败返回状态值：
                1:表示账号密码失效，密码被改或账号被网站删除，将数据库中状态改为1，并跳出循环重新取账号
                0:跳出循环，重新取号
                -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
                -2:本次出错，不跳出循环
        Mysql Update示例:
            # 如果cookie失效，将该cookie从数据库中清除，并重新从数据库中获取登录账号密码
            sql = "UPDATE %s SET cookie='%s' WHERE id=%s ;" % (liveinternet_ru, save_cookies, user_id)
            status = MysqlHandler().update(sql)
            if status == 0:
                g_var.logger.info("cookie失效，清除cookie update OK")
                return {"error": -2}
            else:
                g_var.logger.error("数据库清除cookie错误!")
                return {"error": 1}    
        """
        g_var.logger.info("login ...")
        if userInfo[5] != None and userInfo[5] != "":
            # userInfo[5]保存cookie值，如果cookie不为空，则使用cookie
            g_var.logger.info("返回cookie" + userInfo[5])
            loginData = {
                'id': userInfo[0],
                'username': userInfo[1],
                'password': userInfo[2],
                'cookie': userInfo[5],
            }
            return loginData
        else:
            # cookie为空，使用账号密码登录
            url_login = 'https://www.liveinternet.ru/member.php'
            login_data = {
                's': '',
                'url': 'https://www.liveinternet.ru/journal_register.php',
                'action': 'login',
                'username': userInfo[1],
                'password': userInfo[2],
            }
            g_var.logger.info("登录中...")
            html = requestsW.post(url_login, proxies=ip_proxy("en"), data=login_data, allow_redirects=False, timeout=g_var.TIMEOUT)
            if html == -1:
                return html
            if not html.headers.get('Set-Cookie', None):
                g_var.logger.info('登陆失败......')
                return 1
            try:
                set_cookie = html.headers['Set-Cookie']
                user_Id = re.findall('bbuserid=(.*?);', set_cookie)
                user_password = re.findall('bbpassword=(.*?);', set_cookie)
                cookie = user_Id[0] + '|_|' + user_password[0]
                # 获取cookie，保存到数据库。
                sql = "UPDATE " + present_website + " SET cookie='" + cookie + "' WHERE id=" + str(userInfo[0]) + ";"
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
            userData = {
                'id': userInfo[0],
                'username': userInfo[1],
                'password': userInfo[2],
                'cookie': cookie,
            }
            return userData

    def __postMessage(self, userData, present_website):
        """
        发文章
        Args:
            Session：Session对象
            loginData：用户信息，包括user_id,username,password,cookie
            present_website：当前网站名，用于数据库表名
        Returns:
            成功返回:"ok"
            失败返回状态值：
                1:跳出循环，重新取号
                0:cookie失效，将cookie清空，跳出循环重新取号
                -1:连续代理错误或页面发生改变等取不到关键数据等，需要停止程序
                -2:本次出错，继续循环
        """
        g_var.logger.info("post article ...")
        headers = generate_headers(0)
        if headers == -1:
            g_var.logger.info("获取headers失败...")
            return -1

        g_var.logger.info("article ...")
        article = get_new_article()
        if article == -1:
            return -2
        content = get_code_content(article[1])
        if content == -2:
            return -2

        g_var.logger.info("postarticle_tok ...")
        uid_upwd = userData['cookie'].split('|_|')
        postarticle_tok = get_postarticle_tok(uid_upwd[0])
        if postarticle_tok == -1:
            return -1
        elif postarticle_tok == -2:
            return -2

        g_var.logger.info("new_article_Id ...")
        new_article_Id = get_newarticle_Id(uid_upwd, article[0], headers)
        if new_article_Id == -1:
            return -1
        elif new_article_Id == -2:
            return -2
        elif new_article_Id == 1:
            return 1
        headers['Origin'] = 'https://www.liveinternet.ru'
        headers['Referer'] = 'https://www.liveinternet.ru/journal_post.php?journalid=' + uid_upwd[0]
        headers['Cookie'] = 'bbuserid=' + uid_upwd[0] + '; bbpassword=' + uid_upwd[1]
        multipart_encoder = MultipartEncoder(
            fields={
                'action': 'newpost',
                'parsing': '',
                'journalid': uid_upwd[0],
                'backurl': '',
                'selectforum': '/journal_post.php?journalid=' + uid_upwd[0],
                'headerofpost': article[0],
                'mode': str(0),
                'status': 'Use these controls to insert vBcode',
                'LiNewPostForm': content,  # 文章内容
                'tags': article[-1],  # 标签
                'uploader_count': str(0),
                'music': '',
                'mood': '',
                'attachfile1': ("", '', 'application/octet-stream'),
                'MAX_FILE_SIZE': '',
                'nocomment': str(0),
                'commentsubscribe': 'yes',
                'parseurl': 'yes',
                'autosave_postid': new_article_Id,  # blog ID
                'close_level': str(0),
                'tok': postarticle_tok,
            },
            boundary='------WebKitFormBoundary' + generate_random_string(16, 16, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        )
        headers['Content-Type'] = multipart_encoder.content_type
        g_var.logger.info("正在发布文章 ...")
        url_article = 'https://www.liveinternet.ru/journal_addpost.php'
        html = requestsW.post(url_article, proxies=ip_proxy("en"), data=multipart_encoder, headers=headers)
        if html == -1:
            return -1
        # 发布成功与否验证
        prove = 'Вы добавили сообщение в Ваш дневник'
        if prove not in html.text:
            g_var.ERR_CODE = 5000
            g_var.ERR_MSG = "文章发送失败，IP异常等原因..."
            g_var.logger.info('文章发送失败，IP异常等原因...')
            return 0
        del headers['Origin']
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
        g_var.logger.info("正在获取新文章id ...")
        url_new_article = 'https://www.liveinternet.ru/users/' + userData['username'] + '/blog/'
        res = requestsW.get(url_new_article, proxies=ip_proxy("en"), headers=headers)
        if res == -1:
            return -1
        article_url = re.search('https://www.liveinternet.ru/users/'+ userData['username'].lower() +'/post(.*?)/', res.text)
        if not article_url:
            ('获取新发布文章url失败。。。')
            return 0
        try:
            new_article_url = article_url.group()
            sql = "INSERT INTO liveinternet_ru_article(url, keyword, user_id) VALUES('" + new_article_url + "', '" + article[0] + "', '" + str(userData["id"]) + "');"
            last_row_id = MysqlHandler().insert(sql)
            g_var.logger.info(last_row_id)
            if last_row_id != -1:
                g_var.logger.info('文章成功！' + userData['username'])
                return 'ok'
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

    def registers(self, present_website, VPN):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1
            email_and_passwd = get_email(present_website)
            if email_and_passwd == -1:
                self.failed_count = self.failed_count + 1
                continue
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                registerData = self.__register_one(present_website, email_and_passwd)
                if registerData == 0:
                    g_var.logger.info("注册失败，报错原因需要更换邮箱，跳出本循环")
                    self.failed_count = self.failed_count + 1
                    break
                elif registerData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理连续错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif registerData == -2:
                    g_var.logger.info("注册失败，可能是密码不符合要求等原因，邮箱可以继续使用，不跳出循环")
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
                g_var.ERR_MSG = g_var.ERR_MSG + "无法获取用户!"
                g_var.logger.error("数据库中获取用户失败，本线程停止！")
                return -1
            # 1、登录
            login_signal = 0
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                userData = self.login(present_website, VPN, userInfo)
                if userData == 1:
                    # 返回1表示登录失败，将数据库中的status改为异常
                    g_var.logger.info('使用当前账号密码登录失败。。。')
                    sql = "UPDATE" + present_website + "SET status=1 WHERE id=" + str(userInfo[0]) + ";"
                    status = MysqlHandler().update(sql)
                    if status == -1:
                        return -1
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                elif userData == 0:
                    g_var.logger.info("cookie失效，存入数据库失败")
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|cookie失效，存入数据库失败."
                    self.failed_count = self.failed_count + 1
                    login_signal = 1
                    break
                elif userData == -1:
                    # 代理问题，更换代理
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
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
                status = self.__postMessage(userData, present_website)
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

    def start(self, present_website, VPN):
        while self.success_count < self.assignment_num:
            # 每次循环检测当前错误状态
            if self.__monitor_status() == -1:
                break
            self.now_count = self.now_count + 1
            # 1、注册
            email_and_passwd = get_email(present_website)
            if email_and_passwd == -1:
                self.failed_count = self.failed_count + 1
                continue
            retry_count = 0
            register_signal = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1
                userData = self.__register_one(present_website, email_and_passwd)
                if userData == 0:
                    g_var.logger.info("注册失败，报错原因需要更换邮箱，跳出本循环")
                    self.failed_count += 1
                    register_signal = 1
                    break
                elif userData == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif userData == -2:
                    g_var.logger.info("注册失败，可能是密码不符合要求等原因，邮箱可以继续使用，不跳出循环")
                    self.failed_count += 1
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

            # 2、发文章
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                time.sleep(g_var.SLEEP_TIME)
                retry_count = retry_count + 1
                status = self.__postMessage(userData, present_website)
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
                    self.failed_count += 1
                    break
                elif status == 0:
                    self.failed_count += 1
                    break
                elif status == -1:
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == -2:
                    self.failed_count += 1
                    continue
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续发文章出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功注册账户并发送文章" + str(self.success_count) + "篇")
