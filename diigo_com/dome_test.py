import email
import imaplib
import re
import threading
import time

import MySQLdb
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout, ConnectionError
from project_utils import project_util, requestsW, g_var

INTERFACE_HOST="http://192.168.31.234:8080"
RETRY_COUNT_MAX=20
SLEEP_TIME=1
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36"}


# 人机身份验证码识别
def captcha() -> str:
    data = {
        'key': '8c4ea0fcb64d0d629dfb00b29573f32c',  # 密钥
        'method': 'userrecaptcha',  # 请求方法
        'googlekey': '6Ld23sMSAAAAALfyXkI9d0nHmzOH9jZZNuh66nql',  # googlekey的值
        'pageurl': 'https://www.diigo.com/sign-up?plan=free',  # 整页URL作为pageurl的值
    }
    url_captcha = 'https://2captcha.com/in.php'
    res = requests.get(url_captcha, params=data, verify=False)
    id_code = res.text.split("|")[1]
    while True:
        time.sleep(5)
        print("打码中请稍后")
        url_code = "https://2captcha.com/res.php?key=cb02438b4c9a94f746aa7bbd9477a834&action=get&id=" + id_code
        r = requests.get(url_code, verify=False)
        print(r.text)
        if r.text == "CAPCHA_NOT_READY":
            print("谷歌人机验证，等待15s"+r.text)

        else:
            if "|" in r.text:
                return r.text.split("|")[1]
            else:
                print("谷歌人机验证，出现问题:" + r.text)
                return -1


def google_captcha(Session, googlekey, pageurl):
    """
    谷歌人机验证
    :param Session: Session对象
    :param googlekey: googlekey
    :param pageurl: 页面url
    :return: 谷歌人机验证结果
    """
    data = {
        'key': 'cb02438b4c9a94f746aa7bbd9477a834',  # 密钥
        'method': 'userrecaptcha',
        'googlekey': googlekey,
        'pageurl': pageurl,
    }
    url_captcha = 'https://2captcha.com/in.php'
    res = requests.get(url_captcha, params=data)
    id_code = res.text.split("|")[1]
    while True:
        url_code = "https://2captcha.com/res.php?key=cb02438b4c9a94f746aa7bbd9477a834&action=get&id=" + id_code
        r = requests.get(url_code)
        if r.text == "CAPCHA_NOT_READY":
            print("谷歌人机验证，等待15s"+r.text)
            time.sleep(10)
        else:
            if "|" in r.text:
                return r.text.split("|")[1]
            else:
                print("谷歌验证出问题")
                return -1


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

# 获取文章
def get_new_article():
    get_article_interface_url = "http://192.168.31.234:8080" + "/v1/get/article/"
    retry_count = 0
    while retry_count < 100:
        retry_count = retry_count + 1

        # article = requests.get(url=get_article_interface_url, timeout=g_var.TIMEOUT).text
        headers = {
            'Connection': 'close',
        }
        requests.adapters.DEFAULT_RETRIES = 20
        with requests.get(url=get_article_interface_url, headers=headers,
                          timeout=10) as r:
            article = r.text
        break

    article_split = article.split("|_|")
    return article_split

#获取邮箱参数
class MyEmail(object):

    def __init__(self,username,password,re_text):
        self.re_text=re_text
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
                print(filename)
                msg=self.get_mail(filename)
                if msg:
                    result['msg'] = 'Read Successfully'
                    result['data'] = msg
                    return result

        return {'data':'','msg':'Read Failed'}

    def execute_Start(self):
        read_times = 0
        while read_times<60:
            res = self.Start()
            if "data" in res:
                if res['data']:
                    return res
            read_times += 1
            time.sleep(2)
        return -1



def get_email(present_website: str):
    """
    从接口获取邮箱和密码
    Args:
        present_website:网站名
    Returns:
        成功返回邮箱账号和密码
        失败返回-1
    """
    get_email_interface_url = INTERFACE_HOST + "/v1/get/email/?url=" + present_website
    retry_count = 0
    while retry_count < RETRY_COUNT_MAX:
        retry_count = retry_count + 1
        time.sleep(SLEEP_TIME)
        try:
            # 获取邮箱
            headers = {
                'Connection': 'close',
            }
            # requests.adapters.DEFAULT_RETRIES = DEFAULT_RETRIES
            res = requests.get(url=get_email_interface_url, headers=headers, timeout=15).text
            email_and_passwd = res.strip().split('|_|')

            if len(email_and_passwd) == 1:
                print("No more email")
                return -1

            # 验证邮箱是否可用
            status = test_email_available(email_and_passwd[0], email_and_passwd[1])
            if status == 0:
                return email_and_passwd
            else:
                print("邮箱不可用")
                continue
        except:
            print("无法从接口获取email!")
            return -1
    if retry_count == RETRY_COUNT_MAX:

        print("无可用邮箱")
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
        return -1


# 获取ip
def ip_proxy() -> dict:
    # proxies = {
    #     "http": "http://127.0.0.1:8888",
    #     "https": "https://127.0.0.1:8888",
    # }

    # proxies = {
    #     "http": "http://127.0.0.1:1087",
    #     "https": "https://127.0.0.1:1087",
    # }
    with requests.get(url="http://192.168.31.234:8080/v1/get/ip/?vpn=en", headers=headers, timeout=10) as r:
        proxies = r.text
    proxies = {
        "http": proxies,
        "https": proxies,
    }
    # print(proxies)
    return proxies


def register_one(Session=None) -> dict:
    MysqlHandler().startDB()
    if Session==None:
        Session = requests.session()
        Session.proxies = ip_proxy()
    res=requestsW.get("https://www.diigo.com/",headers=headers,proxies=ip_proxy(),verify=False)#打开首页
    cookies=res.cookies.get_dict()
    print("这里是cookies",cookies)
    str_cookies = str(res.cookies.get_dict())
    cookies = eval(str_cookies)

    user = project_util.generate_random_string(12, 16)
    pwd = project_util.generate_random_string(10, 12)

    email_and_passwd=get_email("https://www.diigo.com")
    if email_and_passwd==-1:
        return "NO email"
    else:
        print("这里是邮箱",email_and_passwd)

    verify_user = requestsW.get("https://www.diigo.com/user_mana2/check_name?username=" + user,cookies=cookies, headers=headers,proxies=Session.proxies,
                              verify=False)#验证用户是否可用
    verify_email = requestsW.get("https://www.diigo.com/user_mana2/check_email?email=" +email_and_passwd[0],cookies=cookies, headers=headers,proxies=Session.proxies,
                               verify=False)#验证邮箱是否可用
    if not verify_user.text == verify_email.text == "1":
        print("错误")
        return "账号密码或邮箱已经被注册"
    # time.sleep(3)

    google_captchas=google_captcha("","6Ld23sMSAAAAALfyXkI9d0nHmzOH9jZZNuh66nql","https://www.diigo.com/sign-up?plan=free")
    # google_captchas ="google_captchas"
    if google_captchas==-1:
        return "谷歌打码失败"

    # requestsW.get("https://www.diigo.com/interact_api/load_user_premium_info",headers=headers,cookies=cookies,proxies=Session.proxies,verify=False)#必须访问
    i=0
    while i<20:
        try:
            Session.proxies = ip_proxy()
            res = requests.get("https://www.diigo.com/sign-up?plan=free", headers=headers,cookies=cookies,proxies=Session.proxies, verify=False)
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
            headers["X-Requested-With"] = "XMLHttpRequest"
            headers["Referer"] = "https://www.diigo.com/sign-up?plan=free"
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            print("准备提交")
            print(cookies)
            res = requests.post("https://www.diigo.com/user_mana2/register_2", headers=headers,cookies=cookies, data=data,proxies=Session.proxies, verify=False)
            print(res.json())
            if project_util.dictExistValue(res.json(), "status"):
                if res.json()["status"] == 1:
                    cookies.update(res.cookies.get_dict())
                    savec=cookies
                    res = requestsW.post("https://www.diigo.com/user_mana2/resend_verify", cookies=cookies,
                                         headers=headers, data={"email": email_and_passwd[0]},
                                         proxies=Session.proxies)
                    print("重新发送邮箱:", res.text)

                    emailinfo = MyEmail(email_and_passwd[0], email_and_passwd[1],
                                        'href="(https://www.diigo.com/user_mana2/register_verify/\w{32})"').execute_Start()
                    print("这里是邮箱参数:", emailinfo)
                    if emailinfo["data"] != -1:
                        Session=requestsW.session()
                        res=Session.get(emailinfo["data"], headers=headers, proxies=Session.proxies,cookies=cookies)
                        sql="""INSERT INTO %s (username, password, mail, status, cookie) VALUES("%s", "%s", "%s", "%s", "%s");"""%("diigo_com",user,pwd,email_and_passwd[0],0,savec)
                        g_var.logger.info(sql)
                        last_row_id = MysqlHandler().insert(sql)

                        if last_row_id != -1:
                            registerData = {
                                "username": user,
                                "password": pwd,
                                "email": email_and_passwd[0],
                            }
                            registerData["user_id"] = last_row_id
                            return registerData
                        return {"user": user, "pwd": pwd, "email": email_and_passwd[0], "cookies": Session.cookies.get_dict()}
                        # if project_util.dictExistValue(res.cookies.get_dict(),"diigoandlogincookie"):  # 注册成功并登陆cookie
                        #     saveCookie = str(Session.cookies.get_dict())
                        #     # print({"user": user, "pwd": pwd, "email": email_and_passwd[0], "cookies": saveCookie})
                        #     return {"user": user, "pwd": pwd, "email": email_and_passwd[0], "cookies": saveCookie}
            return "res:" + res.text
        except (ConnectTimeout,ReadTimeout,ConnectionError) as e:
            res = requestsW.get("https://www.diigo.com/", headers=headers, proxies=Session.proxies,
                                verify=False)  # 打开首页
            cookies = res.cookies.get_dict()
            i+=1
            print(e)
            print("正在换ip",e)



def login():
    Session=requests.session()
    res=Session.get("https://www.diigo.com/sign-in?referInfo=https%3A%2F%2Fwww.diigo.com",headers=headers)
    login_token = re.search('name="loginToken" value="(\w{32})"', res.text)
    if login_token:
        login_token=login_token.group(1)
        print(login_token)
    else:
        return "为获取登陆cookie"

    google_captchas=google_captcha("","6Ld23sMSAAAAALfyXkI9d0nHmzOH9jZZNuh66nql","https://www.diigo.com/sign-in?referInfo=https%3A%2F%2Fwww.diigo.com")
    if google_captchas==-1:
        return "谷歌打码失败"
    data = {
        "referInfo": "https://www.diigo.com",
        "loginToken": login_token,
        "username":"t3wjogvjklzwh3zi",
       "password":"hujie1995",
        "g-recaptcha-response": google_captchas,
        "recaptcha":"v2",
    }
    headers["X-Requested-With"] = "XMLHttpRequest"
    headers["Referer"] = "https://www.diigo.com/sign-in?referInfo=https%3A%2F%2Fwww.diigo.com"
    headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    res = Session.post("https://www.diigo.com/sign-in", headers=headers, data=data,
                       proxies=Session.proxies, verify=False)
    print(res.text)
    save_cookies=str(res.cookies.get_dict())
    print(save_cookies)
    # print(res.text)



def send_article():
    Sesstion=requests.Session()
    Sesstion.proxies=ip_proxy()
    postUrl="https://www.taobao.com"
    users="VFxLelB2Pu4pHcp"
    cookies=eval("{'_smasher_session': '686b9ad801a5b60da6a3c17566963aa5', 'CHKIO': 'bc68a9e172ed31eefc5f8ee43525fb68', 'diigoandlogincookie': 'f1-.-vfxlelb2pu4phcp-.-20-.-0'}")
    # Sesstion.cookies=cookies
    headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    headers["Referer"] = "https://www.diigo.com/user/t3wjogvjklzwh3zi"
    headers["Origin"] = "https://www.diigo.com"
    # res=requests.post("https://superio.diigo.com/fetch_meta",headers=headers,data={"url":postUrl},verify=False)
    # print(res.text)
    # if not project_util.dictExistValue(res.json(),"title"):
    #     return "请求失败"

    headers["X-Requested-With"] = "XMLHttpRequest"
    # res=Sesstion.get("https://www.diigo.com/tag_mana2/load_recommended_tags",params={"title":res.json()["title"],"url":postUrl},headers=headers,cookies=cookies,verify=False)
    # if not project_util.dictExistValue(res.json(),"tags"):
    #     return "提交网站有问题"

    data={
        "title":"这里是淘宝网站",
        "tags":"这里是标签",
        "description":"要闻:这里是详情",
        "unread":False,
        "private":False,
        "url":postUrl,
        "lists":"",
        "groups":"",
    }

    res=Sesstion.post("https://www.diigo.com/item/save/bookmark",cookies=cookies,headers=headers,data=data,verify=False)
    print(res)
    if project_util.dictExistValue(res.json(),"items"):
        print("https://www.diigo.com/user/"+users)



# def activate():
#     Session=requests.session()
#     Session.proxies=ip_proxy()
#     res=Session.get("https://www.diigo.com/user_mana2/register_verify/899852bd9478872972e60f69d93ebafe",proxies=Session.proxies,headers=headers)
#     # print(res.text)
#     print(Session.cookies.get_dict())
#     print(res.url)
#
#     res = requests.get("https://www.diigo.com/",cookies=Session.cookies.get_dict(),
#                       proxies=Session.proxies, headers=headers,verify=False)
#
#
#     print(res.text)
#     print(res.cookies)
#     print(res.url)
#     print(Session.cookies.get_dict()["diigoandlogincookie"])






if __name__ == '__main__':
# user:t3wjogvjklzwh3zi pwd:hujie1995    email:sanooskieich@hotmail.com emailpwd:t2p34JWf
# {'CHKIO': '9546055572d497ab91b93bea2a54b634', '_smasher_session': '91c63bdcb5216935c2a685651db294af', 'diigoandlogincookie': 'f1-.-t3wjogvjklzwh3zi-.-20-.-0'}

    # rlist = []
    # for i in range(15):
    #     # try:
    r = register_one()
    #     rlist.append(r)
    #     # except Exception as e:
    #     #     print(e)
    # print(rlist)
    # login()
    # send_article()
    # print(captcha())
    # print(MyEmail("poateslyskoi@hotmail.com", "Eli78lTE",'href="(https://www.diigo.com/user_mana2/register_verify/\w{32})"').execute_Start())
    # print(activate())





