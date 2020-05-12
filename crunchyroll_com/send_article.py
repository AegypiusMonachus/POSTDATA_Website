import re
import sys
import json
from http import cookiejar
import urllib.request
import urllib.parse

sys.path.append('../')
from crunchyroll_com.crunchyroll_com_util import TIMEOUT
from crunchyroll_com.crunchyroll_com_util import connect_database, generate_headers


def generate_login_data():
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


def generate_new_article_data():
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


def get_article_url(username):
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


def login(opener):

    headers = generate_headers(0)
    userInfo = generate_login_data()

    if userInfo == None:
        print("数据库中获取用户失败！")
    else:
        # userInfo[5]保存cookie值，如果cookie不为空，则使用cookie
        if userInfo[5] != None and userInfo[5] != "":
            print("返回cookie", userInfo[5])
            user_id = userInfo[0]
            username = userInfo[1]
            Cookie = userInfo[5]
            loginData = {
                'id': user_id,
                'name': username,
                'cookie': Cookie
            }
            return loginData
        #cookie为空，使用账号密码登录
        else:
            print("返回账号密码")
            user_id = userInfo[0]
            username = userInfo[1]
            password = userInfo[2]
            loginData = {
                'form': 'login',
                'redirect': '[page.redirect]',
                'magic.word': 'please',
                'name': username,
                'password': password,
                'sign_in': 'Sign In',
            }

            # 使用账号密码登录，使用opener记录cookie
            url_login = 'https://mee.nu/'

            fdata = urllib.parse.urlencode(loginData).encode(encoding='UTF8')
            req = urllib.request.Request(url_login, headers=headers, data=fdata)
            #res1=requests.post(url_login, headers=headers, data=fdata)
            #print(res1.headers)
            #print(res1.cookies)

            try_times = 0
            while try_times < 3:
                try:
                    print("使用账号密码登录，尝试第", try_times + 1, "次")
                    response = opener.open(req, timeout=TIMEOUT)
                    try_times = 4
                except:
                    try_times = try_times + 1
            if try_times == 3:
                print("login timeout!")

            result = response.read().decode("utf-8")

            login_fail_signal = "Login failed."
            if login_fail_signal in result:
                # 如果登录失败将数据库中的status改为异常
                db = connect_database()
                cursor = db.cursor()
                sql = "UPDATE mee_nu SET status=1 WHERE id=" + str(user_id) + ";"
                successOrFail = 1
                try:
                    cursor.execute(sql)
                    db.commit()
                    print("update status OK")
                    loginData = {
                        'id': user_id
                    }
                except:
                    db.rollback()
                    successOrFail = 0

                if successOrFail == 1:
                    # 如果更新成功，那么还要将id+1保存到config.json
                    current_id = {"currentId": int(user_id) + 1}
                    with open('./config.json', 'w') as f:
                        json.dump(current_id, f)
            else:
                # 如果登录成功，则返回id和username给下一步发新文章
                user_id = userInfo[0]
                loginData = {
                    'id': user_id,
                    'name': loginData['name']
                }
            return loginData


def postMessage(opener, loginData, cookie):

    # 返回cookie来发文章
    # cookie加在header中，伪装登录
    # 如果有cookie，但是cookie不可用，将该cookie从数据库中清除，并重新从数据库中获取登录账号密码
    # 根据loginData的长度，长度为2表示账号密码登录，长度为3表示cookie登录
    if len(loginData) == 1:
        print("账号密码异常")
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

    articleData = generate_new_article_data()
    url_postMessage = 'http://' + loginData['name'] + '.mee.nu/edit/entry/'

    fdata = urllib.parse.urlencode(articleData).encode(encoding='UTF8')
    req = urllib.request.Request(url_postMessage, headers=headers, data=fdata)

    try_times = 0
    while try_times < 3:
        try:
            print("发送文章中，尝试第", try_times+1, "次")
            response = opener.open(req, timeout=TIMEOUT)
            try_times = 4
        except:
            try_times = try_times+1
    if try_times == 3:
        print("sendArticle timeout!")

    result = response.read().decode("utf-8")

    cookie_failure_signal = "You are not authorised to access this page."
    if cookie_failure_signal in result:
        print("cookie失效！")
        db = connect_database()
        cursor = db.cursor()
        sql = "UPDATE mee_nu SET cookie='' WHERE id=" + str(loginData['id']) + ";"
        try:
            cursor.execute(sql)
            db.commit()
            print("clear cookie update OK")

            # 清空该id的cookie后再使用账号密码重新登录一次
            cookie = cookiejar.CookieJar()
            handler = urllib.request.HTTPCookieProcessor(cookie)
            opener = urllib.request.build_opener(handler)
            loginData = login(opener)
            postMessage(opener, loginData, cookie)
        except:
            db.rollback()
        #继续处理，将该id的cookie清空
    else:
        print("文章发送成功！", loginData["name"])
        article_url = get_article_url(loginData['name'])
        # 将当前使用id记录到json中 用with open json.dump
        current_id = {"currentId": loginData["id"]}
        with open('./config.json', 'w') as f:
            json.dump(current_id, f)

        # 将文章链接、标题、用户存入article表
        db = connect_database()
        cursor = db.cursor()
        sql = "INSERT INTO mee_nu_article(url, keyword, user_id) VALUES('" + article_url + "', '" + articleData['title'] + "', '" + str(loginData['id']) + "');"
        try:
            cursor.execute(sql)
            db.commit()
            print("update article OK")
        except:
            db.rollback()

        if len(loginData) == 2:
            # 如果使用账号密码登录文章发送成功，将cookie保存到数据库
            for item in cookie:
                cookie_values = item.value

            sql = "UPDATE mee_nu SET cookie='session_id="+cookie_values+"' WHERE id=" + str(loginData['id']) + ";"

            try:
                cursor.execute(sql)
                db.commit()
                print("update cookie OK")
            except:
                db.rollback()


def loginAndPostMessage(article_num):
    #登录并发送文章
    for i in range(0, article_num):
        cookie = cookiejar.CookieJar()
        handler = urllib.request.HTTPCookieProcessor(cookie)
        opener = urllib.request.build_opener(handler)
        loginData = login(opener)
        postMessage(opener, loginData, cookie)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("参数错误！")
    else:
        article_num = int(sys.argv[1])    #发表文章数量
        loginAndPostMessage(article_num)