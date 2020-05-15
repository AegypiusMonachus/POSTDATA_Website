import re
import json
import string
import sys
import random
import threading
import time

import email
import imaplib
import requests
from requests.adapters import HTTPAdapter

from requests_toolbelt.multipart.encoder import MultipartEncoder


from project_utils.project_util import generate_random_string, ip_proxy, get_new_article, MysqlHandler, \
    get_Session, google_captcha, get_email, generate_login_data, get_user_agent
from project_utils import g_var



def generate_headers(signal: int, cookie=""):

    try:
        # user_agent = requests.get(url=g_var.INTERFACE_HOST + "/v1/get/user_agent/", timeout=g_var.TIMEOUT).text
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
        #使用固定header
        headers = {
            'Host': 'knowyourmeme.com',
            'Origin': 'https://knowyourmeme.com',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Referer': 'https://knowyourmeme.com/login',
        }
    elif signal == 1:
        g_var.logger.info(cookie)
        #添加cookie
        headers = {
            'Host': 'knowyourmeme.com',
            'Origin': 'https://knowyourmeme.com',
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Referer': 'https://knowyourmeme.com/memes/new',
            'Cookie': cookie,
        }
    return headers


def generate_random_theme() -> str:
    list = ["Blue", "Green", "Grey", "Orange", "White", "Beans", "Bug", "Butterfly", "Cheese", "Chips", "Clover",
            "Fire", "Gargoyle", "GreenTomatoes", "Ireland", "Mountains", "Rosebud", "SaltnPepper", "Sunrise", "Sunset"]
    theme_digit = random.randint(0, len(list)-1)
    return list[theme_digit]


def generate_register_data(present_website: str, captcha_code: str) -> dict:
    # 生成注册数据返回，并存入数据库
    # 只需生成用户名
    username: str = generate_random_string(8, 12)
    password: str = generate_random_string(10, 16)
    theme: str = generate_random_theme()
    # mail: str = get_email(present_website)
    # if mail == "-1":
    #     return {"error": -1}
    mail: str = username + "@mail.com"

    registerData: dict = {
        'form': 'form.register',
        'name': username,
        'password': password,
        'mail': mail,
        'site': username+".mee.nu",
        'sitename': username,
        'theme': theme,
        'captcha': captcha_code,
        'terms_ok': '1',
        'age_ok': '1',
        'register': 'register',
    }

    return registerData


def generate_new_article_data() -> dict:

    # 这边连续获取失败就报3004错误
    article = get_new_article()
    if article == -1:
        return {"error": -1}

    articleData = {
        'post': '-1',
        'form': 'post',
        'editor': 'innova',
        'title': article[0],
        'category': 'Example',
        'status': 'Publish',
        'text': article[1],
        'more': '',
        'show.html': '1',
        'show.bbcode': '1',
        'show.smilies': '1',
        'allow.comments': '1',
        'allow.pings': '1',
        'type': 'Post',
        'sticky': '0',
        'date': '',
        'path': '',
        'Save': 'Save'
    }
    return articleData


def get_article_url(Session, username: str):
    # 获取新文章的id
    # http://q4aswgg92.mee.nu/ GET
    url_article = "http://" + username + ".mee.nu/"
    #reponse = urllib.request.urlopen(url=url_article)
    # html = requests.get(url_article).text
    try:
        g_var.logger.info("获取新文章")
        html = Session.get(url=url_article, timeout=g_var.TIMEOUT).text
    except:
        g_var.logger.info("获取新文章超时")
        return -1

    #get_article_list_code = reponse.read().decode()
    pattern = '<a href="(.*?)">Add Comment</a>'
    article_url = re.search(pattern, html)
    # http://q4aswgg92.mee.nu/25132876
    article_url = url_article + article_url.groups()[0]
    return article_url


# 获取_know_your_meme_session值
def get_know_your_meme_session(Session, url):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Host': 'knowyourmeme.com',
        'Referer': 'https://knowyourmeme.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
    }

    try:
        g_var.logger.info("获取_know_your_meme_session值")
        res = Session.get(url, headers=headers, timeout=g_var.TIMEOUT)
    except:
        g_var.logger.info("获取_know_your_meme_session超时")
        return -1, -1, -1

    if res.status_code != 200:
        g_var.logger.info('网页打开失败...')
        return -1, -1, -1
    # data-sitekey="6LcODxcTAAAAAHCbB6GzPdQij8_hq7qcaVcM94FP"
    # 用于Google人机身份验证
    sitekey_list = re.findall('data-sitekey="(.*?)"', res.text)
    if not sitekey_list:
        g_var.logger.info('获取data-sitekey值失败...')
        return -1, -1, -1
    # 用于注册时headers头的使用
    session_list = re.findall('_know_your_meme_session=(.*?);', res.headers['Set-Cookie'])
    if not session_list:
        g_var.logger.info('获取_know_your_meme_session值失败...')
        return -1, -1, -1
    # 获取authenticity_token值，用于注册时   真实性令牌   的验证
    token_list = re.findall('name="authenticity_token" type="hidden" value="(.*?)" />', res.text)
    if not token_list:
        g_var.logger.info('获取authenticity_token值失败...')
        return -1, -1, -1
    return sitekey_list[0], session_list[0], token_list[0]


def create_user(min, max):
    user_size = random.randint(min, max)
    random_str = ""
    num = string.ascii_letters + string.digits
    for i in range(user_size):
        random_str += random.choice(num)
    return random_str


# 生成boundary
def create_boundary():
    boundary = ""
    num = string.ascii_letters + string.digits
    for i in range(16):
        boundary += random.choice(num)
    return boundary


def get_authenticity_token(Session, url, cookie=""):
    # 从页面获取authenticity_token值，用于登录和发文章
    headers = {
        'Host': 'knowyourmeme.com',
        'User-Agent': get_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Referer': 'https://knowyourmeme.com/',
    }
    if cookie != "":
        headers["Cookie"] = cookie

    try:
        g_var.logger.info("获取_know_your_meme_session值")
        res = Session.get(url, headers=headers, timeout=g_var.TIMEOUT)
    except:
        g_var.logger.info("获取_know_your_meme_session超时")
        return -1

    g_var.logger.info(res.status_code)
    # g_var.logger.info(res.text)
    token = re.findall('name="authenticity_token" type="hidden" value="(.*?)"', res.text)
    if not token:
        g_var.logger.info('页面获取错误，找不到authenticity_token值...')
        g_var.ERR_CODE = 5000
        g_var.ERR_MSG = g_var.ERR_MSG + '页面获取错误，找不到authenticity_token值...'
        g_var.SPIDER_STATUS = 3
        return -2
    return token[0]


# 新文章url
def get_new_article_url(Session, know_your_meme_session, name):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Host': 'knowyourmeme.com',
        'Referer': 'https://knowyourmeme.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
        'Cookie': know_your_meme_session,
    }
    url = 'https://knowyourmeme.com/memes/all'
    try:
        g_var.logger.info("获取新文章url")
        res = Session.get(url, headers=headers, timeout=g_var.TIMEOUT)
    except:
        g_var.logger.info("获取新文章url超时")
        return 1

    pattern = '<a href="(.*?)" class="photo"><img alt="'+name+'" data-src='
    new_article_url = re.findall(pattern, res.text)
    if not new_article_url:
        g_var.logger.info('新文章发布失败，无法获取新文章url...')
        return -1
    article_url = 'https://knowyourmeme.com' + new_article_url[0]
    return article_url


# 获取用于修改个人资料的authenticity_token值
def edit_personal_authenticity_token(Session):
    # Cookie: __gads=ID=a4b6a409e536a08c:T=1587883317:S=ALNI_MaJll1lLYW7w9FEejD70LKvI4E3JA; _cb_ls=1; _cb=C5SuZqCWrcClDrPo_H; _y=b53841a5-6657-487F-C872-C41D03F62FFB; _shopify_y=b53841a5-6657-487F-C872-C41D03F62FFB; _ga=GA1.2.1200379136.1587883294; _gid=GA1.2.421516754.1587883294; _ntv_uid=dadce36d-9df2-4b99-9e49-d18de8d92f28; ntv_as_us_privacy=1---; _hjid=127652a0-63a5-49ea-ac7d-6d46ffe930bf; __qca=P0-2004391680-1587883295182; _cmpQcif3pcsupported=1; _cb_svref=null; _s=ba8fb234-C7E2-4994-E5F3-50A54ED6117D; _shopify_s=ba8fb234-C7E2-4994-E5F3-50A54ED6117D; _know_your_meme_session=BAh7CkkiD3Nlc3Npb25faWQGOgZFVEkiJTBhMGVkYTExYThiNjUyMzhmNmZhY2NjNThiMmM1NDY4BjsAVEkiEF9jc3JmX3Rva2VuBjsARkkiMTdvRWgxUkxyVVJzaWlFZHZkem81V3c0dDdvRXBSVmxRazg4T00vZG9aVkU9BjsARkkiCnRva2VuBjsARkkiG2oxSjlnX0FsRTJjcUIycXpjVmJpU0EGOwBUSSIQc3ViY3VsdHVyZXMGOwBGVEkiCW5zZncGOwBGRg%3D%3D--461d390965689e4d665e591dae6fe8906f576801; _chartbeat2=.1587524033173.1587974578864.110011.BseweHBWNFC9B9oM8FCLB-4dCrZSuz.11; kym-as={%22name%22:%22c%22%2C%22expires%22:%222020-04-27T08:33:03.677Z%22}; AMP_TOKEN=%24RETRIEVING; _chartbeat5=1006,394,%2Fusers%2Fw0ufa8ajg,https%3A%2F%2Fknowyourmeme.com%2Fusers%2Fw0ufa8ajg%2Fedit,Bsg5G6VWvK8DT2VpDzY-r_DqHvw8,,c,CMZU8tcQnWJbIu8pB9qRf7C9WIFw,knowyourmeme.com,
    headers = {
        'Host': 'knowyourmeme.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Referer': 'https://knowyourmeme.com/users/w0ufa8ajg',
        'Cookie': '',
    }
    url = 'https://knowyourmeme.com/users/w0ufa8ajg/edit'
    res = Session.get(url, headers=headers, timeout=g_var.TIMEOUT)
    token_list = re.findall('name="authenticity_token" type="hidden" value="(.*?)" /></div>', res.text)
    if not token_list:
        g_var.logger.info('获取修改个人资料的authenticity_token失败。。。')
        return -1
    return token_list[0]


def get_picture():
    # 发文章需要一张图片,从接口获取一张图片, 并下载图片
    url = 'http://192.168.31.234:8080/v1/get/pic/'
    res = requests.get(url)
    picture = res.text.strip()
    if not picture:
        g_var.logger.info('图片链接获取失败。。。')
        return -1
    try:
        response = requests.get(picture)
        img = response.content
        with open(g_var.ENV_DIR + '/captcha/knowyourmeme_com/' + threading.currentThread().name + '.jpg', 'wb') as f:
            f.write(img)
    except Exception as e:
        g_var.logger.info(e)
        g_var.logger.info('图片下载失败。。。')
        return -1
    return 0


def get_link():
    # 从接口获取一个超链接
    url = 'http://192.168.31.234:8080/v1/get/link/'
    res = requests.get(url)
    link = res.text.strip()
    if not link:
        g_var.logger.info('获取链接失败。。。')
        return -1
    return link


def get_article():
    # 从接口获取一篇文章
    res = requests.get('http://192.168.31.234:8080/v1/get/article/')
    article = res.text.split('|_|')
    if not article:
        g_var.logger.info('获取文章失败。。。')
        return -1, -1
    title = article[0]
    text_content = article[1]
    content = re.sub(r'<.*?>', '',re.sub('<a href="(.*?)" target="_blank">([\s\S]*?)</a>', "|_|[md5url]|_|", text_content))
    final_content = content.split('|_|')
    a_list = re.findall('<a href="(.*?)" target="_blank">([\s\S]*?)</a>', text_content)
    a_res = []
    # 获取超链接及相对应的文本内容
    for a in a_list:
        a = list(a)
        a_sub = re.sub(r'<.{0,5}>', '', a[1])
        a_split = a_sub.split()
        a[1] = a_split[0]
        a_res.append(a)
    ops = []
    l = len(final_content)
    z = 0
    for s in range(l):
        if final_content[s] != '[md5url]':
            ops.append(final_content[s])
        else:
            link = '\n"{0}":{1}\n'.format(a_res[z][1], a_res[z][0])
            z += 1
            ops.append(link)
    body = ''.join(ops)
    if not body:
        g_var.logger.info('文章正文获取失败。。。')
        return -1, -1
    return title, body


def account_activation(Session, email_and_passwd, email_verify_obj, headers):
    """
    注册成功后去邮箱激活账户
    Args:
        Session：Session对象
        email_and_passwd：邮箱账户和密码的列表，email_and_passwd[0]表示邮箱，[1]表示密码
        email_verify_obj：邮箱验证对象
        headers
    Returns:
        邮箱可用返回0，不可用返回-1
    """
    res_email = email_verify_obj.execute_Start(email_and_passwd[0], email_and_passwd[1])
    g_var.logger.info(res_email)

    if res_email['msg'] != 'Read Successfully':
        g_var.logger.info('邮箱验证路由获取失败。。。')
        return -1

    verify_url = res_email['data']
    # headers = {
    #     'Host': 'knowyourmeme.com',
    #     'Connection': 'keep-alive',
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
    #     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    # }
    result = Session.get(verify_url, headers=headers)
    prove = 'Invalid activation code or user previously activated.'
    if prove in result.text:
        g_var.logger.info('新注册账号未通过验证。。。')
        return -1
    g_var.logger.info('新注册账号通过验证，接下来自由使用。。。')
    return result

# 修改个人资料页的个人网址
def edit_personal_website(Session, know_your_meme_session, authenticity_token, name):
    headers = {
        'Host': 'knowyourmeme.com',
        'Origin': 'https://knowyourmeme.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36',
        'Referer': 'https://knowyourmeme.com/users/'+name.lower()+'/edit',
        'Cookie': know_your_meme_session,
    }
    link = get_link()
    if link == -1:
        g_var.logger.info('链接无法获取到...')
        return -1
    data = {
        'utf8': '✓',
        '_method': 'put',
        'authenticity_token': authenticity_token,
        'profile[email]': 'soaneatqapc@hotmail.com',
        'profile[first_name]': '',
        'profile[last_name]': '',
        'profile[location]': '',
        'profile[website]': link,
        'profile[about_me]': '',
        'profile[deviantart_profile]': '',
        'profile[instagram_profile]': '',
        'profile[reddit_profile]': '',
        'profile[steam_profile]': '',
        'profile[tumblr_profile]': '',
        'profile[twitter_profile]': '',
        'profile[youtube_profile]': '',
        'commit': 'Submit',
    }
    url = 'https://knowyourmeme.com/users/'+name.lower()


    g_var.logger.info("提交个人资料中...")
    result = Session.post(url, data=data, headers=headers, timeout=g_var.TIMEOUT)
    if result == -1:
        g_var.logger.error("提交注册信息超时")
        return -1

    if link not in result.text:
        g_var.logger.info('修改个人资料页的网址失败...')
        return -1
    return link


class HotmailVerification(object):
    # 微软邮箱激活验证
    host = 'imap-mail.outlook.com'
    port = 993

    def __init__(self):
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
            texts = text.decode("utf8", "ignore")
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
                    # g_var.logger.info('附件名:', fname)
                else:
                    # 文本内容
                    res = part.get_payload(decode=True)  # 解码出文本内容，直接输出来就可以了。
                    res = res.decode("utf8", "ignore")
                    res_content = re.findall('https://knowyourmeme.com/(.*?)</a>', res)
                    if res_content:
                        res_text = res_content[0]
                        break
        if res_text:
            return res_text
        else:
            return ''

    def UnreadEmailCount(self):
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

    def Start(self, username, password):
        self.server = imaplib.IMAP4_SSL(host=self.host, port=self.port)
        self.server.login(username, password)
        result = {}
        inbox_unseen, junk_unseen, filename_list = self.UnreadEmailCount()
        if inbox_unseen == 0 and junk_unseen == 0 and filename_list == []:
            result['msg'] = 'Read Failed'
            result['data'] = ''
            return result
        else:
            for i in filename_list:
                filename = i
                msg = self.get_mail(filename)
                if msg:
                    result['msg'] = 'Read Successfully'
                    result['data'] = 'https://knowyourmeme.com/'+msg
                    return result

    def execute_Start(self, username, password):
        read_times = 0
        while True:
            res = self.Start(username, password)
            if res['data']:
                return res
            if read_times == 10:
                res['msg'] = 'Mail Read Failed'
                res['data'] = ''
                return res
            read_times += 1
            time.sleep(5)


class KnowyourmemeCom(object):
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
        注册一个账户
        Args:
            Session：Session对象
            present_website：当前网站名，用于数据库表名
            email_and_passwd：邮箱账户和密码，email_and_passwd[0]是邮箱，[1]是密码
        Returns:
            注册成功返回注册数据registerData
            注册失败返回状态码
            0：某些报错需要跳出循环，更换邮箱
            -1:连续代理错误，停止程序
            -2:注册失败，可能是邮箱密码不符合要求等原因，邮箱可以继续使用，不跳出循环
        """

        # 获取页面上的session值
        url = 'https://knowyourmeme.com/signup'
        sitekey_value, session_value, authenticity_token = get_know_your_meme_session(Session, url)
        if sitekey_value == -1 or session_value == -1 or authenticity_token == -1:
            g_var.logger.info("获取sitekey_value or session_value or authenticity_token失败")
            return -1

        # 获取谷歌验证key
        recaptcha_value = google_captcha(Session, sitekey_value, url)
        g_var.logger.info(recaptcha_value)

        headers = {
            'Host': 'knowyourmeme.com',
            'Origin': 'https://knowyourmeme.com',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Referer': 'https://knowyourmeme.com/signup',
            'Cookie': '_know_your_meme_session=' + session_value,
        }

        # 提交注册
        name = create_user(8, 12)
        psd = create_user(10, 14)
        registerData = {
            'utf8': '✓',
            'authenticity_token': authenticity_token,
            'user[login]': name,
            'user[email]': email_and_passwd[0],
            'user[password]': psd,
            'user[password_confirmation]': psd,
            'user[terms_of_service]': '0',
            'user[terms_of_service]': '1',
            'g-recaptcha-response': recaptcha_value,
            'commit': 'Submit',
        }
        g_var.logger.info(registerData)

        g_var.logger.info("提交注册中...")
        result = Session.post(url, data=registerData, headers=headers, timeout=g_var.TIMEOUT)
        if result == -1:
            g_var.logger.error("提交注册信息超时")
            return -1

        # 检测注册是否成功，看页面是否包含"Not Yet Activated"
        first_prove = 'Not Yet Activated'
        if first_prove not in result.text:
            g_var.logger.info('注册失败。。。')
            g_var.logger.info(result.text)
            return -2

        # 新注册账号使用注册邮箱进行激活：
        email_verify_obj = HotmailVerification()
        second_prove = account_activation(Session, email_and_passwd, email_verify_obj, headers)
        if second_prove == -1:
            g_var.logger.info('激活失败。。。')
            return 0
        else:
            # 将注册的账户写入数据库
            sql = "INSERT INTO "+present_website+"(username, password, mail, status) VALUES('" + name + \
                  "', '" + psd + "', '" + email_and_passwd[0] + "', '" + str(0) + "');"
            last_row_id = MysqlHandler().insert(sql)
            if last_row_id != -1:
                g_var.logger.info('注册激活成功！'+name)
                registerData["user_id"] = last_row_id
                return registerData
            else:
                g_var.logger.error("数据库插入用户注册数据失败")
                return 0

    def __login(self, Session, present_website: str, VPN, userInfo):
        """
        登录
        根据用户信息userInfo中是否包含cookie
        1、有cookie直接构造loginData返回，跳过登录流程
        2、没有cookie，需要post登录请求，获取到cookie，再构造loginData返回
        Args:
            Session：Session对象
            present_website：当前网站名，用于数据库表名
            VPN：使用国内or国外代理
            userInfo：用户信息
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
                -1:连续代理错误，停止程序
                -2:页面发生改变，获取不到页面上的一些token值
                -3:数据库插入更新等错误
        """

        if userInfo[5] != None and userInfo[5] != "":
            # userInfo[5]保存cookie值，如果cookie不为空，则使用cookie
            g_var.logger.info("返回cookie" + userInfo[5])
            user_id = userInfo[0]
            username = userInfo[1]
            password = userInfo[2]
            cookie = userInfo[5]
            loginData = {
                'id': user_id,
                'username': username,
                'password': password,
                'cookie': cookie,
            }
            return loginData
        else:
            # cookie为空，使用账号密码登录
            url = 'https://knowyourmeme.com/login'
            authenticity_token = get_authenticity_token(Session, url)
            if authenticity_token == -1:
                # 重新获取代理
                return -1
            elif authenticity_token == -2:
                # authenticity_token获取异常，退出程序
                return -2
            else:
                data = {
                    'utf8': '✓',
                    'authenticity_token': authenticity_token,
                    'session[login]': userInfo[1],
                    'session[password]': userInfo[2],
                    'session[remember_me]': '0',
                    'commit': 'Login',
                }

                url = 'https://knowyourmeme.com/sessions'
                headers = -1
                while headers == -1:
                    headers = generate_headers(0)
                    if headers == -1:
                        self.failed_count = self.failed_count + 1
                        time.sleep(g_var.SLEEP_TIME)

                g_var.logger.info("账号登录中...")
                result = Session.post(url, data=data, headers=headers, timeout=g_var.TIMEOUT)
                g_var.logger.info(result.status_code)
                if result == -1:
                    g_var.logger.error("登录超时")
                    return -1

                login_fail_signal = 'login failed'
                if login_fail_signal in result.text:
                    g_var.logger.info('使用当前账号密码登录失败。。。')
                    # 如果登录失败将数据库中的status改为异常
                    sql = "UPDATE"+present_website+"SET status=1 WHERE id=" + str(userInfo[0]) + ";"
                    MysqlHandler().update(sql)
                    return 1

                session_list = re.findall('_know_your_meme_session=(.*?);', result.headers['Set-Cookie'])
                if not session_list:
                    g_var.logger.info('登录页面异常，找不到_know_your_meme_session')
                    return -2

                # 获取cookie，保存到数据库。
                cookie = '_know_your_meme_session='+session_list[0]
                sql = "UPDATE "+present_website+" SET cookie='" + cookie + "' WHERE id=" + str(userInfo[0]) + ";"
                status = MysqlHandler().update(sql)
                if status == 0:
                    g_var.logger.info("update cookie OK")
                else:
                    g_var.logger.error("数据库更新cookie错误!")
                    return 1

                user_id = userInfo[0]
                username = userInfo[1]
                password = userInfo[2]

                loginData = {
                    'id': user_id,
                    'username': username,
                    'password': password,
                    'cookie': cookie
                }
                return loginData

    def __postMessage(self, Session, loginData: dict, present_website):
        """
        发文章
        Args:
            Session：Session对象
            loginData：用户信息，包括user_id,username,password,cookie
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
        # 发送文章，文章标题不可重复，文章发布间隔为15分钟（目前看出应该是同一IP下，而不是一个账号下发布文章间隔）
        res_picture = get_picture()
        if res_picture == -1:
            g_var.logger.info('无法获取图片...')
            return -1

        link = get_link()
        if link == -1:
            g_var.logger.info('无法获取链接...')
            return -1

        title, body = get_article()
        if body == -1:
            g_var.logger.info('无法获取文章正文...')
            return -1

        name = create_user(8, 12)
        g_var.logger.info('name:'+name)

        url = "https://knowyourmeme.com/memes/new"
        authenticity_token = get_authenticity_token(Session, url, loginData["cookie"])
        if authenticity_token == -1:
            # 重新获取代理
            return -1
        elif authenticity_token == -2:
            # authenticity_token获取异常，退出程序
            return -2
        # g_var.logger.info(title)
        # 用于设置entry[other_resource_title]值：一个大写字母
        a_str = string.ascii_uppercase
        multipart_encoder = MultipartEncoder(
            fields={
                'utf8': '✓',
                'authenticity_token': authenticity_token,
                'entry[name]': name,
                'entry[icon]': (threading.currentThread().name+'.jpg', open(g_var.ENV_DIR + '/captcha/knowyourmeme_com/'+threading.currentThread().name+'.jpg', 'rb'), 'image/jpeg'),
                'entry[category_id]': '60',
                'entry[entry_type_ids][]': '',
                'entry[entry_type_ids][]': '78',
                'entry[tag_list]': '',
                'entry[origin]': '',
                'entry[year]': '',
                'entry[origin_date(2i)]': '',
                'entry[origin_date(3i)]': '',
                'entry[origin_date(1i)]': '',
                'entry[nsfw]': '0',
                'queries': '',
                'geo': '',
                'time': 'all',
                'entry[generator_link]': link,
                'entry[facebook_link]': link,
                'entry[reddit_link]': link,
                'entry[twitter_link]': link,
                'entry[wikipedia_link]': link,
                'entry[urban_dictionary_link]': link,
                'entry[dramatica_link]': link,
                'entry[other_resource_title]': random.choice(a_str),
                'entry[other_resource_url]': link,
                'url': link,
                'entry[body]': body,
                'commit': 'loading...',
            },
            boundary='----WebKitFormBoundary' + create_boundary(),
        )

        headers = -1
        while headers == -1:
            headers = generate_headers(1, loginData['cookie'])
            if headers == -1:
                self.failed_count = self.failed_count + 1
                time.sleep(g_var.SLEEP_TIME)

        headers['Content-Type'] = multipart_encoder.content_type
        url = 'https://knowyourmeme.com/memes'

        g_var.logger.info("文章发送中...")
        result = Session.post(url, data=multipart_encoder, headers=headers, timeout=g_var.TIMEOUT)
        if result == -1:
            g_var.logger.error("文章发送超时")
            return -1

        g_var.logger.info(result.text)
        cookie_failure_signal = "Please login to access this page. "
        if cookie_failure_signal in result.text:
            # 如果cookie失效，将该cookie从数据库中清除，并重新从数据库中获取登录账号密码
            sql = "UPDATE "+present_website+" SET cookie='' WHERE id=" + str(loginData['id']) + ";"
            status = MysqlHandler().update(sql)
            if status == 0:
                g_var.logger.info("cookie失效，清除cookie update OK")
                return -1
            else:
                g_var.logger.error("数据库清除cookie错误!")
                return 1

        prove = 'Failed to create new entry.'
        if prove in result.text:
            g_var.logger.info('文章发送失败...')
            return 1
        new_article_url = get_new_article_url(Session, loginData["cookie"], name)
        g_var.logger.info(new_article_url)
        if new_article_url == -1:
            g_var.logger.info('新文章发送失败...')
            return 1
        else:
            # 将文章链接、标题、用户存入article表
            sql = "INSERT INTO "+present_website+"_article(url, keyword, user_id) VALUES('" + new_article_url + "', '" \
                  + name + "', '" + str(loginData['id']) + "');"

            if g_var.insert_article_lock.acquire():
                last_row_id = MysqlHandler().insert(sql)
                g_var.insert_article_lock.release()

            if last_row_id != -1:
                g_var.logger.info("insert article OK")
            else:
                g_var.logger.error("数据库插入文章错误!")
                return -3

        personal_link = edit_personal_website(Session, loginData["cookie"], authenticity_token, loginData["username"])
        g_var.logger.info(personal_link)
        if personal_link == -1:
            g_var.logger.info('未能成功修改个人资料页的网址...')
        return 0

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

            # 获取邮箱
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
                    proxies = ip_proxy(VPN)
                    if proxies == {"error": -1}:
                        g_var.logger.info("获取代理错误")
                        self.failed_count = self.failed_count + 1
                    Session.proxies = proxies
                elif registerData == 0:
                    # 注册成功，但激活失败
                    g_var.logger.info("注册成功,但激活失败！")
                    break
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

                loginData = self.__login(Session, present_website, VPN, userInfo)
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
                    break
                elif status == -1:
                    # 返回值为-1，更换代理
                    g_var.ERR_MSG = g_var.ERR_MSG + "|_|代理连续错误"
                    g_var.logger.info("代理错误")
                    retry_count = g_var.RETRY_COUNT_MAX
                elif status == -2:
                    # 返回值为-2，某些必须停止的错误，程序停止
                    self.failed_count = self.failed_count + 1
                    g_var.SPIDER_STATUS = 3
                    break
                elif status == -3:
                    self.failed_count = self.failed_count + 1
                elif status == -4:
                    # 返回值为-4，cookie过期，重新取值
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
                elif registerData == 0:
                    # 注册成功，但激活失败
                    g_var.logger.info("注册成功,但激活失败！")
                    break
                else:
                    # 注册成功
                    self.failed_count = 0
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续注册出错，程序停止"
                g_var.logger.error("连续注册失败！程序停止")
                break

            # 2、登录
            Session = get_Session(VPN)
            if Session == -1:
                self.failed_count = self.failed_count + 1
                continue

            # 构造一个userInfo
            userInfo: tuple = (registerData['user_id'], registerData['user[login]'], registerData['user[password]'],
                               registerData['user[email]'], '0', "")

            login_signal = 0   # 记录状态，成功为0，失败为1
            retry_count = 0
            while retry_count < g_var.RETRY_COUNT_MAX:
                retry_count = retry_count + 1

                loginData = self.__login(Session, present_website, VPN, userInfo)
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
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续登录失败！程序停止"
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
                    # 返回值为-4，cookie过期，重新取值
                    break
            if retry_count == g_var.RETRY_COUNT_MAX:
                # 连续出错说明发生了一些问题，需要停止程序
                g_var.SPIDER_STATUS = 3
                g_var.ERR_MSG = g_var.ERR_MSG + "|_|连续发文章出错，程序停止"
                g_var.logger.error("连续发文章出错，程序停止")
                break
        g_var.logger.info("成功注册账户并发送文章" + str(self.success_count) + "篇")
