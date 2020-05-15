import email
import imaplib
import json
import logging
import re
import sys
import time
from logging import handlers

from project_utils.project_util import generate_random_string, ip_proxy, get_new_article, MysqlHandler, \
    identify_captcha_1, get_Session, google_captcha, EmailVerify, account_activation, test_email_available
from project_utils import g_var

import requests
from requests.adapters import HTTPAdapter

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


def get_global_params(present_website: str):
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
        url = g_var.INTERFACE_HOST + "/v1/get/config/?UUID=" + g_var.UUID
        print(url)
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
            #g_var.logger = Logger(g_var.ENV_DIR + '/logs/' + present_website + '_' + g_var.UUID + '.log',
            #                      level='info').logger  # 实例化一个logger对象
    except:
        # 若程序启动没有获取到配置，则直接停止运行
        g_var.logger.error("【3001】 获取不到参数")
        exit()


def get_email(present_website: str):
    """
    从接口获取邮箱和密码
    Args:
        present_website:网站名
    Returns:
        成功返回邮箱账号和密码
        失败返回-1
    """
    get_email_interface_url = g_var.INTERFACE_HOST + "/v1/get/email/?url=" + present_website
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
                return -1

            # 验证邮箱是否可用
            status = test_email_available(email_and_passwd[0], email_and_passwd[1])
            if status == 0:
                return email_and_passwd
            else:
                continue
        except:
            g_var.SPIDER_STATUS = 3
            g_var.ERR_CODE = 3005
            g_var.ERR_MSG = g_var.ERR_MSG + "无法从接口获取email!"
            return -1
    if retry_count == g_var.RETRY_COUNT_MAX:
        g_var.SPIDER_STATUS = 3
        g_var.ERR_CODE = 3005
        g_var.ERR_MSG = g_var.ERR_MSG + "邮箱库中无可用email!"
        return -1
g_var.logger = Logger('test.log', level='info').logger  # 实例化一个logger对象

g_var.INTERFACE_HOST = "http://192.168.31.234:8080"
g_var.UUID = "1383838438"
get_global_params("scoop_it")


Session = get_Session("en")
url = "https://www.scoop.it/subscribe?&token=&sn=&showForm=true"
# headers = {
#     'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36',
# }
# html = Session.get(url, headers=headers, timeout=g_var.TIMEOUT).text
# print(html)

FullName = generate_random_string(15, 20)
password = generate_random_string(10, 15)
email_and_passwd = get_email("scoop_it")


# googlekey="6LevIjoUAAAAAEJnsStYfxxf5CEQgST01NxAwH8v"
# pageurl="https://www.scoop.it/subscribe?&token=&sn=&showForm=true"
# recaptcha_value = google_captcha(Session, googlekey, pageurl)
recaptcha_value = input("请输入验证码：")

registerData = {
    'jsDetectedTimeZone': 'Asia/Shanghai',
    'pc': '',
    'displayName': FullName,
    'shortName': FullName,
    'email': email_and_passwd[0],
    'password': password,
    'avatar': '',
    'upload-image-original-url': '',
    'job': 'My personal brand or blog',
    'g-recaptcha-response': recaptcha_value,
    'subscribe': ''
}

headers = {
    'Host': 'www.scoop.it',
    'content-type': 'application/x-www-form-urlencoded',
    'cookie': '_ga=GA1.2.414277657.1585813236; _hjid=71bda9cf-284f-49bd-931e-3909f2e82cf8; hubspotutk=adc7e4c18bdd1122f5e358e6c2daa434; _fbp=fb.1.1585813242887.314114715; __stripe_mid=0506e052-8f80-46aa-a04b-efa62be2df71; messagesUtk=beaaffd5ab3d4039b7e27015e4203fda; hp=1; _gid=GA1.2.436170571.1589264042; uvts=8d14b4da-1ae4-49b3-5fc2-0082043ecd0c; __hssrc=1; userId=d6f2cd50-3faa-4f28-96df-29b6e14a0ea8; __hstc=3002351.adc7e4c18bdd1122f5e358e6c2daa434.1585813237927.1589436452898.1589447890146.13; _gat=1; __hssc=3002351.6.1589447890146',
    'origin': 'https://www.scoop.it',
    'referer': 'https://www.scoop.it/subscribe?&token=&sn=&showForm=true',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
}

html = Session.post(url, headers=headers, data=registerData, timeout=g_var.TIMEOUT, verify=False).text


re_text = '(https://www.scoop.it/confirm\?.*?)" '
email_verify_obj = EmailVerify(email_and_passwd[0], email_and_passwd[1], re_text)
verify_url = account_activation(email_verify_obj)
print(verify_url)

"""
# 获取验证码
url_image = 'http://mee.nu/captcha/'

picture = Session.get(url_image, timeout=g_var.TIMEOUT).content

with open(g_var.ENV_DIR+'/captcha/'+present_website+'/'+threading.currentThread().name+'.png', 'wb') as file:
    file.write(picture)

# 识别验证码
captcha_code = identify_captcha_1(present_website)
if captcha_code == "-1":
    g_var.logger.info("识别验证码失败")
    return -1
g_var.logger.info("captcha_code:" + captcha_code)

headers = generate_headers(0)
if headers == {"error": -1}:
    g_var.logger.info("获取headers失败")
    return -1
registerData = generate_register_data(present_website, captcha_code)
if registerData == {"error": -1}:
    g_var.logger.info("获取注册邮箱失败")
    return -1

url_register = 'https://mee.nu/'
try:
    g_var.logger.info("提交注册中...")
    html = Session.post(url_register, headers=headers, data=registerData, timeout=g_var.TIMEOUT).text
    self.proxy_err_count = 0
except:
    g_var.logger.error("提交注册信息超时")
    self.proxy_err_count = self.proxy_err_count + 1
    return -1

# result中包含"Thank you for registering"，则表示注册成功。注册成功，将数据保存到数据库
sucsess_sign = "Thank you for registering"
if sucsess_sign in html:
    self.captcha_err_count = 0
    sql = "INSERT INTO mee_nu(username, password, mail, status) VALUES('" + registerData['name'] + \
          "', '" + registerData['password'] + "', '" + registerData['mail'] + "', '" + str(0) + "');"
    last_row_id = MysqlHandler().insert(sql)
    if last_row_id != -1:
        registerData["user_id"] = last_row_id
        return registerData
    else:
        g_var.logger.error("数据库插入失败")
        return -1
else:
    g_var.logger.info("验证码错误或邮箱名重复!")
    self.captcha_err_count = self.captcha_err_count + 1
    return -1
"""