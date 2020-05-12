import re
import sys
import json
import time
import base64

import requests
from requests.adapters import HTTPAdapter
from lxml import etree

sys.path.append('../')
from mee_nu.mee_nu_util import TIMEOUT
from mee_nu.mee_nu_util import connect_database, generate_headers


def generate_headers(signal: int, postData: dict={}) -> dict:
    if signal == 0:
        #使用固定header
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
        }
    elif signal == 1:
        #添加cookie
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
            'cookie': postData['cookie'],
        }
    return headers


def load_image() -> str:
    file_data = {
        "key":(None, "qwfffffff888"),
        'file': ('chaptcha.png', open('./image/chaptcha.png', 'rb'))
    }
    url_answer = 'http://89.248.174.24/in.php'
    res = requests.post(url_answer, files=file_data,verify=False).text
    id_code = res.split("|")[1]
    url_code = "http://89.248.174.24/res.php?key=qwfffffff888&action=get&id="+id_code
    r = requests.get(url_code,verify=False).text
    return r.split("|")[1]


def load_image_lianzhong():
    with open('./image/chaptcha.jpg', 'rb') as f:  # 以二进制读取图片
        data = f.read()
        encodestr = base64.b64encode(data)  # 得到 byte 编码的数据

    file_data = {
        "softwareId": 18960,
        "softwareSecret": "nCqJbiZERXsY4WqNFbli3bx4QWIjt0NI5XRWRANA",
        "username": "kk355332",
        "password": "19131421a.",
        "captchaData": encodestr,
        "captchaType": 1008,
        "captchaMinLength": 6,
        "captchaMaxLength": 8,
        "workerTipsId": 0
    }

    url_lianzhong = "https://v2-api.jsdama.com/upload"
    res = requests.post(url_lianzhong, files=file_data,verify=False).text
    print(res)

def generate_login_data() -> list:
    # 获取登录数据
    db = connect_database()
    cursor = db.cursor()

    # 从config.json中读取上一次使用的账号，然后从数据库中取出最近一个能够使用的账号
    with open('./config.json', encoding='utf-8') as f:
        data = json.load(f)
    current_id = data["currentId"]

    # 按id顺序读取，提取状态正常的账号，成功后记录当前id到config.json中
    sql = "SELECT * FROM mee_nu AS m WHERE m.`id` > " + str(current_id) + " and m.`status` = 0 ORDER BY m.`id` LIMIT 0, 1;"
    cursor.execute(sql)
    userInfo = cursor.fetchone()
    print(userInfo)

    if userInfo == None:
        current_id = 0
        sql = "SELECT * FROM mee_nu AS m WHERE m.`id` > " + str(current_id) + " and m.`status` = 0 ORDER BY m.`id` LIMIT 0, 1;"
        cursor.execute(sql)
        userInfo = cursor.fetchone()
        print(userInfo)
        if userInfo == None:
            print("当前数据库账号池为空，或全部状态异常")

    return userInfo


def generate_new_article_data() -> dict:
    #$$$接口传入文章

    article= """
    文章3|_|sdfsdfsdfsd[wplink][mainlink]"""

    article = article.replace("[wplink]", "https:/www.taobao.com")
    article = article.replace("[mainlink]", "https://www.baidu.com")
    article_list = article.split("|_|")

    articleData = {
        'post': '-1',
        'form': 'post',
        'editor': 'innova',
        'title': article_list[0],
        'category': 'Example',
        'status': 'Publish',
        'text': article_list[1],
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


def get_article_url(username: str) -> str:
    # 获取新文章的id
    # http://q4aswgg92.mee.nu/ GET
    url_article = "http://" + username + ".mee.nu/"
    reponse = urllib.request.urlopen(url=url_article)
    get_article_list_code = reponse.read().decode()
    pattern = '<a href="(.*?)">Add Comment</a>'
    article_url = re.search(pattern, get_article_list_code)
    # http://q4aswgg92.mee.nu/25132876
    article_url = url_article + article_url.groups()[0]
    return article_url


def login(Session) -> dict:

    headers = generate_headers(0)
    userInfo = generate_login_data()   # 这边写一个通用函数，传入数据表名作为参数

    if userInfo == None:
        print("数据库中获取用户失败！")
    else:
        if userInfo[5] != None and userInfo[5] != "":
            # userInfo[5]保存cookie值，如果cookie不为空，则直接使用cookie，不用再做登录操作
            print("使用cookie登录", userInfo[5])
            user_id = userInfo[0]
            username = userInfo[1]
            website_cookie = userInfo[5]
            loginData = {
                'id': user_id,
                'name': username,
                'cookie': website_cookie
            }
            return loginData

        else:
            # cookie为空，则使用账号密码登录，登录成功后还要将cookie保存到数据库
            user_id = userInfo[0]
            username = userInfo[1]
            password = userInfo[2]

            # login
            loginData: dict = {
                'returnto': '',
                'op': "userlogin",
                'unickname': username,
                'upasswd': password,
                'userlogin': "Log In",
            }

            url_login = "https://slashdot.org/my/login"

            print("使用账号密码登录中...")
            content = Session.post(url_login, headers=headers, data=loginData, timeout=15).content

            # @@@分析返回判断依据
            login_fail_signal = "Login failed."
            if login_fail_signal in content:
                # 登录失败，将数据库中的status改为异常
                db = connect_database()
                cursor = db.cursor()
                sql = "UPDATE mee_nu SET status=1 WHERE id=" + str(user_id) + ";"
                try:
                    cursor.execute(sql)
                    db.commit()
                    print("update status OK")
                    # 登陆失败只返回user_id，长度为1
                    loginData = {
                        'id': user_id
                    }
                except:
                    db.rollback()
            else:
                # 登录成功，则返回id和username给下一步发新文章
                user_id = userInfo[0]
                loginData = {
                    'id': user_id,
                    'name': loginData['name']
                }
            return loginData


def postMessage(Session, loginData: dict):

    # 返回cookie来发文章
    # cookie加在header中，伪装登录
    # 如果有cookie，但是cookie不可用，将该cookie从数据库中清除，并重新从数据库中获取登录账号密码
    # 根据loginData的长度，长度为2表示账号密码登录，长度为3表示cookie登录
    if len(loginData) == 1:
        print("账号密码异常！！")
        current_id = {"currentId": loginData["id"]}
        with open('./config.json', 'w') as f:
            json.dump(current_id, f)
        return
    elif len(loginData) == 2:
        print("账号密码登录")
        headers = generate_headers(0)
    elif len(loginData) == 3:
        print("cookie登录")
        headers = generate_headers(1, loginData)

    # 首先打开文章提交页面，需要在该页面获取reskey、send_type等几个参数
    url_submit = "https://slashdot.org/submit"       # 文章提交页
    content = Session.get(url_submit, headers=headers).content

    # postData: dict = {
    #     'op': "comments_precheck"
    # }
    # s = Session.post(url_preview, headers=headers, data=postData)

    # 获取reskey和send_type等值
    html = etree.HTML(content)
    reskey = html.xpath("//form[@id='slashstoryform']/input[1]/@value")[0]
    send_type = html.xpath("//form[@id='slashstoryform']/input[2]/@value")[0]
    article_id = html.xpath("//form[@id='slashstoryform']/input[3]/@value")[0]
    session = html.xpath("//form[@id='slashstoryform']/input[4]/@value")[0]
    state = html.xpath("//form[@id='slashstoryform']/input[5]/@value")[0]
    # 文章接口获取文章
    articleData = generate_new_article_data()
    title = "beautiful"  # @@@接口获取数据
    introtext = "nicenice"  # @@@接口获取数据
    url = "https://www.zhihu.com"  # @@@接口获取数据
    op = "edit_preview"

    postData: dict = {
        'reskey': reskey,
        'type': send_type,
        'id': article_id,
        'session': session,
        'state': state,
        'title': title,
        'introtext': introtext,
        'url': url,
        'op': op
    }
    # 首先提交数据进行文章预览
    url_preview = "https://slashdot.org/ajax.pl"  # 提交文章时ajax发送的目的地址
    s = Session.post(url_preview, headers=headers, data=postData, timeout=15)

    # 在文章预览页获取验证码
    hcanswer_url = "https:" + s.text[s.text.find("capt-img") + 17:s.text.find("verification") - 38]
    print("获取验证码中...")
    picture = Session.get(hcanswer_url, timeout=15).content
    with open('./image/chaptcha.png', 'wb') as file:
        file.write(picture)

    # 识别验证码@@@
    # hcanswer = load_image()
    hcanswer = input("验证码：")  # json中获取验证码地址下载下来先手动填写，再调用api识别，看能否上传成功

    # 在文章预览页需要获取url_id参数，因此要再get请求一次
    url_submission = "https://slashdot.org/submission"
    content = Session.get(url_submission, headers=headers).content
    html = etree.HTML(content)
    url_id = html.xpath("//form[@id='slashstoryform']/input[6]/@value")[0]

    # 加入url_id等参数后再次提交post表单，发送文章
    op = "edit_save"
    submit_time = int(time.time() * 1000)
    postData: dict = {
        'reskey': reskey,
        'type': send_type,
        'id': article_id,
        'session': session,
        'state': state,
        'title': title,
        'introtext': introtext,
        'url': url,
        'url_id': url_id,
        'hcanswer': hcanswer,
        'submit_time': submit_time,
        'op': op
    }
    print(postData)
    s = Session.post(url_preview, headers=headers, data=postData)
    print(s.text)


def loginAndPostMessage(article_num: int):
    # 登录并发送文章
    for i in range(0, article_num):
        s = requests.Session()
        s.mount('http://', HTTPAdapter(max_retries=3))
        s.mount('https://', HTTPAdapter(max_retries=3))

        loginData = login(s)
        postMessage(s, loginData)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("参数错误！")
    else:
        article_num = int(sys.argv[1])    #发表文章数量
        loginAndPostMessage(article_num)

    #load_image_lianzhong()


