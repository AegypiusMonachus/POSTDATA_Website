import email
import json
import random
import re
import sys
import threading
import time
import imaplib

import requests
from requests.adapters import HTTPAdapter
import argparse
import MySQLdb
import functools
import logging
from logging import handlers

from project_utils import g_var
from project_utils import requestsW


# @#$ 2、本文件定义整个大项目可能用到的通用的函数
class Logger(object):
    """
    日志打印类
    """
    # 日志级别关系映射
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL
    }

    def __init__(self, filename, level='info', when='D', backCount=3,
                 fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'):
        self.logger = logging.getLogger(filename)
        # 设置日志格式
        format_str = logging.Formatter(fmt)
        # 设置日志级别
        self.logger.setLevel(self.level_relations.get(level))
        # 往屏幕上输出
        sh = logging.StreamHandler()
        # 设置屏幕上显示的格式
        sh.setFormatter(format_str)
        # 往文件里写入#指定间隔时间自动生成文件的处理器
        th = handlers.TimedRotatingFileHandler(filename=filename, when=when, backupCount=backCount, encoding='utf-8')
        # 实例化TimedRotatingFileHandler
        # interval是时间间隔，backupCount是备份文件的个数，如果超过这个个数，就会自动删除，when是间隔的时间单位，单位有以下几种：
        # S 秒 M 分 H 小时 D 天 W 每星期（interval==0时代表星期一） midnight 每天凌晨

        # 设置文件里写入的格式
        th.setFormatter(format_str)
        # 把对象加到logger里
        # 如果要关闭logger，只需注释掉以下两个
        self.logger.addHandler(sh)
        self.logger.addHandler(th)


class MysqlHandler(object):
    """
    数据库操作类
    """
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(MysqlHandler, "_instance"):
            with MysqlHandler._instance_lock:
                if not hasattr(MysqlHandler, "_instance"):
                    MysqlHandler._instance = object.__new__(cls)
        return MysqlHandler._instance

    def startDB(self):
        # 读写分离
        self.db = MySQLdb.connect(host=g_var.SQL_CONFIG["host"], port=g_var.SQL_CONFIG["port"],
                                  user=g_var.SQL_CONFIG["user"], password=g_var.SQL_CONFIG["pass"],
                                  db=g_var.SQL_CONFIG["database"], charset='utf8')
        self.cursor = self.db.cursor()  # 创建游标

        self.dbinsert = MySQLdb.connect(host=g_var.SQL_CONFIG["host"], port=g_var.SQL_CONFIG["port"],
                                        user=g_var.SQL_CONFIG["user"], password=g_var.SQL_CONFIG["pass"],
                                        db=g_var.SQL_CONFIG["database"], charset='utf8')
        self.cursorinsert = self.dbinsert.cursor()  # 创建游标

    def insert(self, sql):
        try:
            g_var.logger.info(sql)
            self.cursorinsert.execute(sql)  # 执行sql
            self.dbinsert.commit()  # 手动提交
            g_var.logger.info("cursorinsert.lastrowid:" + str(self.cursorinsert.lastrowid))
            return self.cursorinsert.lastrowid
        except Exception as e:
            self.dbinsert.rollback()  # 事务回滚
            g_var.logger.error("数据库插入数据错误!")
            g_var.ERR_CODE = 2004
            g_var.ERR_MSG = g_var.ERR_MSG + "数据库插入数据错误!"
            return -1

    def select(self, sql):
        try:
            g_var.logger.info(sql)
            self.cursor.execute(sql)  # 执行sql
            return self.cursor.fetchone()
        except Exception as e:
            self.db.rollback()  # 事务回滚
            g_var.logger.error("数据库查询数据错误!")
            g_var.ERR_CODE = 2004
            g_var.ERR_MSG = g_var.ERR_MSG + "数据库查询数据错误!"
            return -1

    def update(self, sql):
        try:
            g_var.logger.info(sql)
            self.cursorinsert.execute(sql)  # 执行sql
            self.dbinsert.commit()  # 手动提交
            g_var.logger.info("update status OK")
            return 0
        except Exception as e:
            self.dbinsert.rollback()  # 事务回滚
            g_var.logger.error("数据库更新数据发生错误")
            g_var.ERR_CODE = 2004
            g_var.ERR_MSG = g_var.ERR_MSG + "数据库更新数据发生错误!"
            return -1

    def dbclose(self):
        self.cursor.close()
        self.db.close()
        self.cursorinsert.close()
        self.dbinsert.close()


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
                    res_text += res
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


def account_activation(Session, email_verify_obj):
    """
    注册成功后去邮箱激活账户
    Args:
        email_and_passwd：邮箱账户和密码的列表，email_and_passwd[0]表示邮箱，[1]表示密码
        email_verify_obj：邮箱验证对象
    Returns:
        未收到激活邮件返回-1
        收到返回激活邮件中的激活链接verify_url
    """
    res_email = email_verify_obj.execute_Start()
    g_var.logger.info(res_email)

    if res_email != -1:
        if res_email['msg'] != 'Read Successfully':
            g_var.logger.info('邮箱验证路由获取失败。。。')
            return -1
        else:
            return res_email['data']
    else:
        return -1


# 日志打印装饰器
def log(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        g_var.logger.info('call %s():' % func.__name__)
        return func(*args, **kw)

    return wrapper


def get_Session(VPN: str):
    """
    获取Session对象
    Args:
        VPN:网站vpn访问类型
    Returns:
        成功返回Session对象
        错误返回-1
    """
    Session = requestsW.Session()

    # 获取代理设置
    proxies = ip_proxy(VPN)
    if proxies == {"error": -1}:
        return -1
    Session.proxies = proxies
    # 设置最大重试次数
    Session.mount('http://', HTTPAdapter(max_retries=1))
    Session.mount('https://', HTTPAdapter(max_retries=1))
    return Session


def ip_proxy(vpn: str="en"):
    """
    获取代理
    Args:
        vpn:网站vpn访问类型
    Returns:
        成功返回Session对象
        错误返回{"error": -1}
    """
    get_proxy_interface_url = g_var.INTERFACE_HOST + "/v1/get/ip/?vpn=" + vpn
    try:
        # proxy = requests.get(url=get_proxy_interface_url, timeout=g_var.TIMEOUT).text
        headers = {
            'Connection': 'close',
        }
        requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
        with requests.get(url=get_proxy_interface_url, headers=headers, timeout=g_var.TIMEOUT) as r:
            proxy = r.text
    except:
        g_var.ERR_CODE = 2001
        g_var.ERR_MSG = g_var.ERR_MSG + "无法获取proxy!"
        g_var.logger.error("无法获取proxy!")
        return {"error": -1}

    if vpn == "ch":
        proxy_list = proxy.split("|_|")
        # 代理服务器
        proxyHost = "http-dyn.abuyun.com"
        proxyPort = "9020"
        # 代理隧道验证信息
        proxyUser = proxy_list[0]
        proxyPass = proxy_list[1]

        proxyMeta = "http://%(user)s:%(pass)s@%(host)s:%(port)s" % {
            "host": proxyHost,
            "port": proxyPort,
            "user": proxyUser,
            "pass": proxyPass,
        }
        proxies = {
            "http": proxyMeta,
            "https": proxyMeta,
        }
    elif vpn == "en":
        proxy = proxy.strip()
        proxies = {
            "http": proxy,
            "https": proxy,
        }
        if "socks5" in proxies["https"]:
            proxies["https"]=proxies["https"].replace("socks5","socks5h")
    return proxies


def generate_random_string(min: int, max: int,
                           seed: str = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") -> str:
    """
    生成随机字符串
    Args:
        min：最小长度
        max：最大长度
        seed: 要生成随机字符串的种子
    Returns:
        返回随机字符串random_str
    """
    random_str = []
    name_digit = random.randint(min, max)
    for i in range(name_digit):
        random_str.append(random.choice(seed))
    random_str = ''.join(random_str)
    return random_str


def generate_login_data(present_website: str, path="") -> list:
    """
    获取登录数据
    定义一个id的全局变量，初始值为-1，如果为-1，就去读一下config.json，获取id值。之后所有登录都是对这个id操作，而不用再去读config.json
    Args:
        present_website:网站名
    Returns:
        成功返回数据库中返回的账户信息
    """
    if path == "":
        path = g_var.ENV_DIR + '/' + present_website + '/config.json'

    if g_var.USER_ID == -1:
        # 如果g_var.USER_ID == -1，就让第一个线程去config.json中读取id值到全局变量g_var.USER_ID中
        if g_var.login_data_config_lock.acquire():
            if g_var.USER_ID == -1:
                with open(path, encoding='utf-8') as f:
                    data = json.load(f)
                g_var.USER_ID = data["currentId"]
            g_var.login_data_config_lock.release()

    # 从全局变量g_var.USER_ID获取上一个被使用的id，并用这个id去数据库取下一个可用id，在最后主线程结束时，将g_var.USER_ID保存到config.json中
    if g_var.login_data_g_var_lock.acquire():
        sql = "SELECT * FROM " + present_website + " AS m WHERE m.`id` > " + str(
            g_var.USER_ID) + " and m.`status` = 0 ORDER BY m.`id` LIMIT 0, 1;"
        userInfo = MysqlHandler().select(sql)
        g_var.logger.info("logindata:" + str(userInfo))

        # 如果userInfo == None，再从头开始取数据
        if userInfo == None:
            g_var.USER_ID = 0
            sql = "SELECT * FROM " + present_website + " AS m WHERE m.`id` > " + str(
                g_var.USER_ID) + " and m.`status` = 0 ORDER BY m.`id` LIMIT 0, 1;"
            userInfo = MysqlHandler().select(sql)
            g_var.logger.info(userInfo)
            # 如果再次取还是为空，则说明数据库中没有可用账号
            if userInfo == None:
                g_var.logger.error("当前数据库账号池为空，或所有账号状态异常")
                g_var.ERR_CODE = 2003
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "数据库中没有可用用户，请先注册后再启动本程序！"
                # 数据库中没有可用用户，则停止程序
                g_var.SPIDER_STATUS = 3
            else:
                g_var.USER_ID = userInfo[0]
        else:
            g_var.USER_ID = userInfo[0]

        g_var.login_data_g_var_lock.release()
        return userInfo


def get_email(present_website: str):
    """
    从接口获取邮箱和密码
    Args:
        present_website:网站名
    Returns:
        成功返回邮箱账号和密码 email_and_passwd[0]:user email_and_passwd[1]:pwd
        失败返回-1
    """
    get_email_interface_url = g_var.INTERFACE_HOST + "/v1/get/email/?url=" + present_website
    g_var.logger.info(get_email_interface_url)
    retry_count = 0
    while retry_count < g_var.RETRY_COUNT_MAX:
        retry_count = retry_count + 1
        time.sleep(g_var.SLEEP_TIME)
        try:
            # 获取邮箱
            headers = {
                'Connection': 'close',
            }
            requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
            res = requests.get(url=get_email_interface_url, headers=headers, timeout=15).text
            email_and_passwd = res.strip().split('|_|')
            g_var.logger.info(email_and_passwd)

            if len(email_and_passwd) == 1:
                g_var.SPIDER_STATUS = 3
                g_var.ERR_CODE = 3005
                g_var.ERR_MSG = g_var.ERR_MSG + "No more mail!"
                g_var.logger.error("No more mail!")
                return -1

            # 验证邮箱是否可用
            status = test_email_available(email_and_passwd[0], email_and_passwd[1])
            if status == 0:
                return email_and_passwd
            else:
                g_var.logger.info('此邮箱号不可用...')
                continue
        except:
            g_var.SPIDER_STATUS = 3
            g_var.ERR_CODE = 3005
            g_var.ERR_MSG = g_var.ERR_MSG + "无法从接口获取email!"
            g_var.logger.error("无法从接口获取email!")
            return -1
    if retry_count == g_var.RETRY_COUNT_MAX:
        g_var.SPIDER_STATUS = 3
        g_var.ERR_CODE = 3005
        g_var.ERR_MSG = g_var.ERR_MSG + "邮箱库中无可用email!"
        g_var.logger.error("邮箱库中无可用email!")
        return -1


def test_email_available(username, password):
    """
    测试邮箱是否可用
    Args:
        username:邮箱账户
        password：邮箱密码
    Returns:
        邮箱可用返回0，不可用返回-1
    """
    try:
        host = 'imap-mail.outlook.com'
        port = "993"
        server = imaplib.IMAP4_SSL(host=host, port=port)
        server.login(username, password)
        return 0
    except Exception as e:
        # g_var.logger.info(e)
        requests.get(g_var.INTERFACE_HOST + "/v1/get/email_discard/?email=" + username)
        return -1


def get_global_params(present_website: str,Debug=False):
    """
    获取全局参数
    Args:
        present_website:网站名
    """
    try:
        # r = requests.get(url=g_var.INTERFACE_HOST + "/v1/get/config/")
        headers = {
            'Connection': 'close',
        }
        requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
        with requests.get(url=g_var.INTERFACE_HOST + "/v1/get/config/?UUID=" + g_var.UUID, headers=headers,
                          timeout=g_var.TIMEOUT) as r:
            if int(r.status_code / 100) == 4:
                g_var.logger.error("【3001】 获取不到参数", r.status_code)
                sys.exit(0)
            global_config = json.loads(r.text)

            sql_host = global_config["sql_host"]
            sql_port = int(global_config["sql_port"])
            sql_user = global_config["sql_user"]
            sql_pass = global_config["sql_pass"]
            sql_database = global_config["sql_database"]
            g_var.SQL_CONFIG = {"host": sql_host, "port": sql_port, "user": sql_user, "pass": sql_pass,
                                "database": sql_database}
            g_var.TIMEOUT = global_config["timeout"]
            g_var.ERR_COUNT = global_config["err_count"]
            g_var.PROXY_ERR_MAX = global_config["proxy_err_count"]
            g_var.SEND_STATUS_INTERVAL = global_config["send_status"]
            g_var.VERIFY_URL1 = global_config["verify_url1"]
            g_var.VERIFY_KEY1 = global_config["verify_key1"]
            g_var.VERIFY_URL2 = global_config["verify_url2"]
            g_var.VERIFY_KEY2 = global_config["verify_key2"]
            g_var.EMAIL_INTERVAL_TIME = global_config["email_interval_time"]
            g_var.EMAIL_TIME = global_config["email_time"]
            g_var.CPU_MAX = global_config["cpu_max"]
            g_var.RAM_MAX = global_config["ram_max"]
            g_var.THREAD_COUNT = global_config["thread_count"]
            g_var.CAPTCHA_ERR_MAX = global_config["verify_err_count"]
            g_var.RETRY_COUNT_MAX = g_var.ERR_COUNT
            g_var.REMAIN_TASK_COUNT = g_var.ALL_COUNT
            MysqlHandler().startDB()
            # MysqlHandler() = MysqlHandler()  # 实例化一个mysql_handler对象
            if Debug:
                g_var.logger = Logger('./' + present_website + '_' + g_var.UUID + '.log',
                                      level='info').logger  # 实例化一个logger对象
            else:
                g_var.logger = Logger(g_var.ENV_DIR + '/logs/' + present_website + '_' + g_var.UUID + '.log',
                                  level='info').logger  # 实例化一个logger对象
    except Exception as e:
        # 若程序启动没有获取到配置，则直接停止运行
        g_var.logger.error("【3001】 获取不到参数")
        exit()


def get_command_line_arguments():
    """
    命令行传入参数
    """
    parser = argparse.ArgumentParser(description='mee_nu argparse')
    parser.add_argument('--count', help='count，必要参数，注册账户数量', required=True)
    parser.add_argument('--host', help='host，必要参数，服务器host', required=True)
    parser.add_argument('--uuid', help='uuid，必要参数，线程uuid', required=True)
    args = parser.parse_args()
    return args


def get_new_article():
    """
    从接口获取新文章
    """
    get_article_interface_url = g_var.INTERFACE_HOST + "/v1/get/article/"
    retry_count = 0
    while retry_count < g_var.RETRY_COUNT_MAX:
        retry_count = retry_count + 1
        try:
            # article = requests.get(url=get_article_interface_url, timeout=g_var.TIMEOUT).text
            headers = {
                'Connection': 'close',
            }
            requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
            with requests.get(url=get_article_interface_url, headers=headers,
                              timeout=g_var.TIMEOUT) as r:
                article = r.text
            break
        except:
            time.sleep(g_var.SLEEP_TIME)
            pass
    if retry_count == g_var.RETRY_COUNT_MAX:
        g_var.logger.error("获取文章、标题、链接、关键词失败")
        g_var.ERR_CODE = 3004
        g_var.ERR_MSG = g_var.ERR_MSG + "获取文章、标题、链接、关键词失败!"
        g_var.SPIDER_STATUS = 3
        return -1
    article_split = article.split("|_|")
    return article_split


def get_user_agent()->str:
    """
    从接口获取user_agent
    """
    headers = {
        'Connection': 'close',
    }
    requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
    with requests.get(url=g_var.INTERFACE_HOST + "/v1/get/user_agent/", headers=headers, timeout=g_var.TIMEOUT) as r:
        user_agent = r.text
    return user_agent


def get_new_link():
    """
    从接口获取超链接
    """
    get_link_url = g_var.INTERFACE_HOST + "/v1/get/link/"
    retry_count = 0
    while retry_count < g_var.RETRY_COUNT_MAX:
        retry_count = retry_count + 1
        try:
            headers = {
                'Connection': 'close',
            }
            requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
            with requests.get(url=get_link_url, headers=headers, timeout=g_var.TIMEOUT) as r:
                link = r.text
            break
        except:
            time.sleep(g_var.SLEEP_TIME)
            pass
    if retry_count == g_var.RETRY_COUNT_MAX:
        g_var.logger.error("无法从接口获取超链接！")
        g_var.ERR_CODE = 3004
        g_var.ERR_MSG = g_var.ERR_MSG + "无法从接口获取超链接！"
        g_var.SPIDER_STATUS = 3
        return -1

    return link

def get_text():
    """
    从接口获取纯文本
    """
    get_text_url = g_var.INTERFACE_HOST + "/v1/get/article_txt/"
    retry_count = 0
    while retry_count < g_var.RETRY_COUNT_MAX:
        retry_count = retry_count + 1
        try:
            headers = {
                'Connection': 'close',
            }
            requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
            with requests.get(url=get_text_url, headers=headers, timeout=g_var.TIMEOUT) as r:
                wenben = r.text
            break
        except:
            time.sleep(g_var.SLEEP_TIME)
            pass
    if retry_count == g_var.RETRY_COUNT_MAX:
        g_var.logger.error("无法从接口获取纯文本！")
        g_var.ERR_CODE = 3004
        g_var.ERR_MSG = g_var.ERR_MSG + "无法从接口获取纯文本！"
        g_var.SPIDER_STATUS = 3
        return -1

    return wenben

def get_keyword():
    """
    从接口获取关键字
    """
    get_keyword_url = g_var.INTERFACE_HOST + "/v1/get/keyword/"
    retry_count = 0
    while retry_count < g_var.RETRY_COUNT_MAX:
        retry_count = retry_count + 1
        try:
            headers = {
                'Connection': 'close',
            }
            requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
            with requests.get(url=get_keyword_url, headers=headers, timeout=g_var.TIMEOUT) as r:
                keyword = r.text
            break
        except:
            time.sleep(g_var.SLEEP_TIME)
            pass
    if retry_count == g_var.RETRY_COUNT_MAX:
        g_var.logger.error("无法从接口获取关键字！")
        g_var.ERR_CODE = 3004
        g_var.ERR_MSG = g_var.ERR_MSG + "无法从接口获取关键字！"
        g_var.SPIDER_STATUS = 3
        return -1

    return keyword

def get_new_title_and_link():
    # 从接口获取超链接和标题
    #return [0] title ,[1]link
    get_link_url = g_var.INTERFACE_HOST + "/v1/get/title_or_link/"
    retry_count = 0
    while retry_count < g_var.RETRY_COUNT_MAX:
        retry_count = retry_count + 1
        try:
            headers = {
                'Connection': 'close',
            }
            requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
            with requests.get(url=get_link_url, headers=headers, timeout=g_var.TIMEOUT) as r:
                titleAndLink = r.text.split('|_|')
        except:
            time.sleep(g_var.SLEEP_TIME)
            pass
        if len(titleAndLink) == 2:
            break
    if retry_count == g_var.RETRY_COUNT_MAX:
        g_var.logger.error("无法从接口获取超链接！")
        g_var.ERR_CODE = 3004
        g_var.ERR_MSG = g_var.ERR_MSG + "无法从接口获取超链接！"
        g_var.SPIDER_STATUS = 3
        return -1

    return titleAndLink


def identify_captcha_1(Session, captcha_url: str, present_website: str):
    """
    下载识别字母和数字的验证码
    :param
        Session:Session
        present_website:当前网站名
    :return:
        验证码识别结果
        -1: session代理连续错误
        -2: 接口返回数据错误
    """
    captcha = Session.get(captcha_url, timeout=g_var.TIMEOUT).content
    if captcha == -1:
        return -1

    print("写入图片")
    with open(g_var.ENV_DIR + '/captcha/' + present_website + '/' + threading.currentThread().name + '.png',
              'wb') as file:
        file.write(captcha)
    time.sleep(1)
    print("读取图片")
    with open(g_var.ENV_DIR + '/captcha/' + present_website + '/' + threading.currentThread().name + '.png',
              'rb') as file:
        file_data = {
            "key": (None, g_var.VERIFY_KEY1),
            'file': ('chaptcha.png', file)
        }
        url_answer = g_var.VERIFY_URL1 + "/in.php"
        try:
            res = requests.post(url=url_answer, files=file_data, timeout=g_var.TIMEOUT).text
        except:
            g_var.ERR_CODE = 2001
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "无法连接验证码识别接口"
            g_var.logger.error("无法连接验证码识别接口")
            return -2
        if len(res.split("|")) < 2:
            g_var.logger.info(res)
            return -2
        id_code = res.split("|")[1]

        url_code = g_var.VERIFY_URL1 + "/res.php?key=" + g_var.VERIFY_KEY1 + "&action=get&id=" + id_code
        try:
            headers = {
                'Connection': 'close',
            }
            requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
            with requests.get(url=url_code, headers=headers, timeout=g_var.TIMEOUT) as r:
                text = r.text
                if text != -1:
                    return text.split("|")[1]
                else:
                    return -2
        except:
            g_var.ERR_CODE = 2001
            g_var.ERR_MSG = g_var.ERR_MSG + "|_|" + "无法获取验证码识别结果!"
            g_var.logger.error("无法获取验证码识别结果!")
            return -2


def google_captcha(Session, googlekey, pageurl):
    """
    谷歌人机验证
    :param Session: Session对象
    :param googlekey: googlekey
    :param pageurl: 页面url
    :return: 谷歌人机验证结果
    """
    data = {
        'key': g_var.VERIFY_KEY2,
        'method': 'userrecaptcha',
        'googlekey': googlekey,
        'pageurl': pageurl,
    }
    url_captcha = g_var.VERIFY_URL2 + '/in.php'
    try:
        res = requests.get(url_captcha, params=data)
    except:
        g_var.logger.info("打码平台请求失败")
        return -1
    if "|" not in res.text:
        g_var.logger.info("谷歌验证出现问题" + str(res.text))
        return -1
    id_code = res.text.split("|")[1]
    url_code = g_var.VERIFY_URL2 + "/res.php?key=" + g_var.VERIFY_KEY2 + "&action=get&id=" + id_code
    while True:
        try:
            r = requestsW.get(url_code, timeout=g_var.TIMEOUT)
        except:
            g_var.logger.info("打码平台请求成功，查询可用key值失败")
            return -1
        if r != -1:
            if r.text == "CAPCHA_NOT_READY":
                g_var.logger.info("谷歌人机验证，等待15s"+r.text)
                time.sleep(15)
            else:
                if "|" in r.text:
                    g_var.logger.info("谷歌人机验证，成功:" + r.text.split("|")[1])
                    return r.text.split("|")[1]
                else:
                    g_var.logger.info("谷歌人机验证，出现问题:" + r.text)
                    return -1
        else:
            return -1


def task_dispatch():
    # 每有一个线程来请求，查看剩余需要完成的任务的数量,需要加锁使用本函数
    # 如果大于0，则给该线程一个任务
    # 如果没有任务了，就让该线程挂起
    # 如果给某个线程分配的任务中途退出了，则任务要打回，在该线程中g_var.REMAIN_TASK_COUNT+1
    if g_var.REMAIN_TASK_COUNT > 0:
        g_var.REMAIN_TASK_COUNT = g_var.REMAIN_TASK_COUNT - 1
        return 0
    else:
        return -1


def send_spider_block_status():
    """
    启动任务阻塞时，向中控发送消息
    """
    g_var.ERR_MSG = "CPU或内存不足，等待执行"
    status_data = {
        "uuid": g_var.UUID,
        "err_code": int(g_var.ERR_CODE),
        "err_msg": g_var.ERR_MSG,
        "all_count": g_var.ALL_COUNT,
        "now_count": g_var.NOW_COUNT,
        "success_count": g_var.SUCCESS_COUNT,
        "failed_count": 0,
        "status": "1"
    }

    post_status_url = g_var.INTERFACE_HOST + "/v1/post/status/"
    try:
        headers = {
            'Connection': 'close',
        }
        requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
        r = requests.post(url=post_status_url, json=status_data, headers=headers, timeout=g_var.TIMEOUT)
        g_var.ERR_MSG = ""  # 错误消息发送给中控后清空
        g_var.ERR_CODE = 0
        # 当r.status_code==400时，中控下发停止命令，停止程序运行
        if r.status_code == 400:
            g_var.logger.info(r.text)
            g_var.logger.error("中控下发停止命令，程序将被中止")
            g_var.ERR_MSG = "中控下发停止命令，程序将被中止"
            g_var.SPIDER_STATUS = 3
            # 发送最后一条消息
            status_data = {
                "uuid": g_var.UUID,
                "err_code": int(g_var.ERR_CODE),
                "err_msg": g_var.ERR_MSG,
                "all_count": g_var.ALL_COUNT,
                "now_count": g_var.NOW_COUNT,
                "success_count": g_var.SUCCESS_COUNT,
                "failed_count": 0,
                "status": str(g_var.SPIDER_STATUS)
            }
            r = requests.post(url=post_status_url, json=status_data, headers=headers, timeout=g_var.TIMEOUT)
    except:
        # 若服务器没有响应，则停止程序
        # g_var.logger.error("中控失去响应，程序将被中止")
        # g_var.SPIDER_STATUS = 3     # 将所有线程停止
        g_var.logger.error("中控响应丢包")

    if g_var.SPIDER_STATUS == 3:
        return 1
    else:
        return 0


def send_spider_status(obj_list: list, t_list: list):
    """
    定时向中控发送消息
    :param obj_list: 对象列表
    :param t_list: 线程列表
    :return:返回两个值，
        close_send_status_signal：是否停止发送状态信号 0代表不停止继续发送，1代表停止
        wait_signal：等待信号 0代表需要等待所有线程结束，1代表不等待直接结束
    """
    g_var.NOW_COUNT = 0
    g_var.SUCCESS_COUNT = 0
    g_var.FAILED_COUNT = 0

    g_var.PROXY_ERR_COUNT = 0
    g_var.CAPTCHA_ERR_COUNT = 0

    for obj in obj_list:
        # 统计通用参数
        g_var.NOW_COUNT = g_var.NOW_COUNT + obj.now_count
        g_var.SUCCESS_COUNT = g_var.SUCCESS_COUNT + obj.success_count

        # 统计需要暂停程序的报错参数
        g_var.CAPTCHA_ERR_COUNT = g_var.CAPTCHA_ERR_COUNT + obj.captcha_err_count  # 2、验证码连续无法正确识别
        g_var.FAILED_COUNT = g_var.FAILED_COUNT + obj.failed_count           # 3、其他错误连续错误次数

    if g_var.CAPTCHA_ERR_COUNT > g_var.CAPTCHA_ERR_MAX:
        g_var.logger.error("验证码连续识别错误次数过多！")
        g_var.ERR_CODE = "3002"
        g_var.ERR_MSG = "验证码连续识别错误次数过多！"
        g_var.SPIDER_STATUS = 3  # 将所有线程停止

    if g_var.FAILED_COUNT > g_var.ERR_COUNT:
        g_var.logger.error("其他错误连续错误次数过多！")
        g_var.ERR_CODE = "3005"
        g_var.ERR_MSG = "其他错误连续错误次数过多！"
        g_var.SPIDER_STATUS = 3  # 将所有线程停止

    if g_var.SUCCESS_COUNT == g_var.ALL_COUNT:  # 所有任务完成，停止本线程
        g_var.SPIDER_STATUS = 3

    # 检测所有线程，等到所有线程停后，再向中控发送SPIDER_STATUS == 3的消息，告知已经停止

    alive_count = 0
    for t in t_list:
        if t.isAlive():
            alive_count = alive_count + 1
    if alive_count == 0:  # 如果没有存活的线程，停止程序
        g_var.logger.info("所有线程都已结束，程序停止！")
        spider_status = 3
        g_var.SPIDER_STATUS = 3
    else:
        g_var.logger.info("alive_count=" + str(alive_count))
        spider_status = 2

    status_data = {
        "uuid": g_var.UUID,
        "err_code": int(g_var.ERR_CODE),
        "err_msg": g_var.ERR_MSG,
        "all_count": g_var.ALL_COUNT,
        "now_count": g_var.NOW_COUNT,
        "success_count": g_var.SUCCESS_COUNT,
        "failed_count": g_var.FAILED_COUNT,
        "status": str(spider_status)
    }

    post_status_url = g_var.INTERFACE_HOST + "/v1/post/status/"
    try:
        headers = {
            'Connection': 'close',
        }
        requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
        r = requests.post(url=post_status_url, json=status_data, headers=headers, timeout=g_var.TIMEOUT)
        g_var.ERR_MSG = ""  # 错误消息发送给中控后清空
        g_var.ERR_CODE = 0
        if r.status_code == 400:
            # 当r.status_code==400时，中控下发停止命令，停止程序运行
            g_var.SPIDER_STATUS = 3  # 将所有线程停止
            spider_status = 3
            status_data = {
                "uuid": g_var.UUID,
                "err_code": int(g_var.ERR_CODE),
                "err_msg": g_var.ERR_MSG,
                "all_count": g_var.ALL_COUNT,
                "now_count": g_var.NOW_COUNT,
                "success_count": g_var.SUCCESS_COUNT,
                "failed_count": g_var.FAILED_COUNT,
                "status": str(spider_status)
            }
            # 向中控发送最后一条信息，告知程序即将停止
            r = requests.post(url=post_status_url, json=status_data, headers=headers, timeout=g_var.TIMEOUT)
            g_var.logger.error("中控下发停止命令，正在停止线程")
            return 1, 1

    except Exception as e:
        g_var.logger.error(e)
        # 若服务器没有响应，则停止程序
        # g_var.logger.error("中控失去响应，程序将被中止")
        # g_var.SPIDER_STATUS = 3     # 将所有线程停止
        g_var.logger.error("中控响应丢包")

    if spider_status == 3:
        return 1, 0
    else:
        return 0, 0


def dictExistValue(d: dict, *args) -> bool:
    """
    判断字典中是否有value值  data={"path":{"url":"123"}}   dictExistValue(data,"path","url")
    :param d: dict
    :param args:  str
    :return:
    """
    if d:
        if not isinstance(d, dict):
            return False
        for v in args:
            if v in d:
                d = d[v]
            else:
                return False
        return True
    else:
        return False