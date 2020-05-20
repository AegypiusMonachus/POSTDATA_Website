import json
import re
import urllib3

from project_utils import project_util, requestsW

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from project_utils.project_util import ip_proxy as uitl_ip_proxy
import requests
import socket

"""header
:authority: www.reddit.com
:method: POST
:path: /register
:scheme: https
accept: */*
accept-encoding: gzip, deflate, br
accept-language: zh-CN,zh;q=0.9
content-length: 594
content-type: application/x-www-form-urlencoded
cookie: loid=00000000006cbwd1je.2.1588212337712.Z0FBQUFBQmVxakp4R0VOQjRyaHpTemdKVUpEd2tiRjlmMDJOUVRDRzUwM2wwdjV0SEk4YkZwR3BaSmZZWFpPSFJjTTNDRFJNSnItRTNUaDhIQm1OSHVsSUJsMUYxZG0ybjhHSG9ZeHI2bnIzSjFWcGtfdjZ3WlE4cnZnY1dnWGNZYnllU3JjRGVKZHQ; d2_token=3.48fdb220891f1300d995417cfa2aed7832cd91cb6ab283f8b99c444deab24eb1.eyJhY2Nlc3NUb2tlbiI6Ii1rSlZIdklRcEEwczk5aFFDdWNfd05nVURUYkEiLCJleHBpcmVzIjoiMjAyMC0wNC0zMFQwMzowNTozNy4wMDBaIiwibG9nZ2VkT3V0Ijp0cnVlLCJzY29wZXMiOlsiKiIsImVtYWlsIl19; csv=1; edgebucket=HKZX91DNG2dmOmQfum; mnet_session_depth=1%7C1588212383595; reddaid=R7LLRL5WTHVZU5AA; __aaxsc=2; session_tracker=s4TwGDwUr8SscjUkwa.0.1588212376751.Z0FBQUFBQmVxaktZQXc4Tjk0VS1YOTdYbDVzM2JiZDdvNWRmakdHcGhudVZMcXljanEzQ1dOZkdSb0FxUURsR0Z5SlN5NnNtTkx0NGs1Z0VrbDItVUplc0JjQXl2alhIWG9qeGRuOFRaSlBXYzNJbDRXSUdzWDNHczJCOHBrTkdEM0U5bVhrUkpIYXE; session=bd725aadfd74a7b1d296be7f243a42fa85cd5a54gASVSQAAAAAAAABKmzKqXkdB16qMnmn6kX2UjAdfY3NyZnRflIwoOGY5OTRlYTA2NjFmMTYzZjI5OTAxYWZhNzU0MWVmZTE4Yjg0YmFkZJRzh5Qu
origin: https://www.reddit.com
referer: https://www.reddit.com/register/?actionSource=header_signup
sec-fetch-dest: empty
sec-fetch-mode: cors
sec-fetch-site: same-origin
user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36
"""

"""
csrf_token: 8f994ea0661f163f29901afa7541efe18b84badd
g-recaptcha-response: 03AGdBq25it1ZuJl_U8wzwGZga1XRj5qTTE6D_zo77876feUc4YExPUlDBqbyGW3iGwl2WF7KuOt1oxrc7_DfPqO1PdmbUKihJ-XzMuna1VPEh192K7Lj0f3fy7Jf0YC8s69a0JZbwEW3gRBcb47Iy7vhEfZxJB_k_XEc04SeVXTPztrw4pfldkqqXQnOoTcmgt05b4iA9ALh8vElHyTAxLZWQDb60mZNpt8dcwkx5BJgpWu_xB9ZF35G5TKGE_Hj8pxZYTy_LRuJmaQyh3GB1ZqFVdcrBOM6MhZEmbdGkIRDt1neL8gOyeGRNciERC2YbNy2yPNHJGi5gso8vNy3CbEbCzsbrDlARFMSPre1wvZKGnUFWab6LRv4rlz8a51DatdpCjTu5kGP-KJZhSPuW8I8WC3GuYDW6-A
password: hujie123
dest: https://www.reddit.com
username: 17752545955
email: 17752545955@163.com
"""

import requests
import time

headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36"}

# 人机身份验证码识别
def captcha() -> str:
    data = {
        'key': 'cb02438b4c9a94f746aa7bbd9477a834',  # 密钥
        'method': 'userrecaptcha',  # 请求方法
        'googlekey': '6LeTnxkTAAAAAN9QEuDZRpn90WwKk_R1TRW_g-JC',  # googlekey的值
        'pageurl': 'https://www.reddit.com',  # 整页URL作为pageurl的值
    }
    url_captcha = 'https://2captcha.com/in.php'
    res = requests.get(url_captcha, params=data)
    id_code = res.text.split("|")[1]
    while True:
        print("打码中请稍后")
        time.sleep(10)
        url_code = "https://2captcha.com/res.php?key=cb02438b4c9a94f746aa7bbd9477a834&action=get&id=" + id_code
        r = requests.get(url_code)
        print(r.text)
        if r.text == 'CAPCHA_NOT_READY':
            pass
        else:
            break
    return r.text.split("|")[1]

#获取文章
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

#获取ip
def ip_proxy() -> dict:
    # get_article_interface_url ="http://192.168.31.234:8080/v1/get/ip/?vpn=en"
    #
    # # proxy = requests.get(url=get_article_interface_url, timeout=g_var.TIMEOUT).text
    # headers = {
    #     'Connection': 'close',
    # }
    # requests.adapters.DEFAULT_RETRIES = 20
    # with requests.get(url=get_article_interface_url, headers=headers, timeout=10) as r:
    #     proxy = r.text
    #
    #
    # proxy = proxy.strip()
    # proxies = {
    #     "http": proxy,
    #     "https": proxy,
    # }
    # proxies = {
    #     "http": "http://127.0.0.1:8888",
    #     "https": "https://127.0.0.1:8888",
    # }

    with requests.get(url="http://192.168.31.234:8080/v1/get/ip/?vpn=en", headers=headers, timeout=10) as r:
        proxies = r.text
    proxies = {
        "http": proxies,
        "https": proxies,
    }
    return proxies




def register()->(str,str,str):
    user = project_util.generate_random_string(12, 16)
    pwd = project_util.generate_random_string(10, 12)
    email = user + "@qq.com"
    dicproxy = ip_proxy()
    s = requests.session()
    s.proxies = dicproxy
    s.headers = headers
    proxies=ip_proxy()


    res = requestsW.get("https://www.reddit.com/register/?actionSource=header_signup",proxies=proxies,headers=headers,timeout=5)
    cookies=res.cookies.get_dict()
    print(cookies)
    print("已经响应",res)
    re_res = re.search('<input type="hidden" name="csrf_token" value="(.*?)">', res.text)
    csrf_token = re_res.group(1)
    print("正在打码中")
    # g_recaptcha_response = captcha()
    g_recaptcha_response="03AGdBq24tyZjh-Ini2ud5ISBy1Eb-UYEpSKYdgxsNNLLvMRQT4VXCVW4Z1EuXrtX4GwlERbjJkS1x9cJtcPbKmGYwzvqRfajGUvFyq9CEfRSzohkPv54Lnk1BlU3OHE8suDOSrKwc90uj7TPeTL12VUhdyCk-H73quiajTYNuwd3pJm1xdWbbo4JthN8N0hvMIrsdM7_XYAclp_BN9QTWkwmhjDTpR8-CM2zWJ48JKug-9KZzaVM-Bmxzb7LVr4NcG5XozTrhsIdbS89eLSo8aoS7V-frd8Hb6xFpBpvjtsCQMnE25FoR7FqPmL2ER0bNV7QgowFX6Z8OFZ95fDDTub5S9qCQUr7Zactpz57_W38T6opn4u4swVH_EcEGUpkT1IhUgy5GVVsBgvidVR3F0j7F5tfLQ2_GKg"
    print("打印验证码:", g_recaptcha_response)


    data = {
        "csrf_token": csrf_token,
        "g-recaptcha-response": g_recaptcha_response,
        "dest": "https://www.reddit.com",
        "password": pwd,
        "username": user,
        "email": email,
    }
    # res.headers["content-type"]="application/x-www-form-urlencoded"

    res = requestsW.post("https://www.reddit.com/register",headers=headers,proxies=proxies,cookies=cookies, data=data,timeout=5)
    print(res.cookies)
    print("注册结果:", res.text)


def test()->bool:
   try:
        s = requests.session()
        dicproxy = ip_proxy()
        s.proxies = dicproxy
        # res = s.get("http://tui.ddns.net/sars/", headers=headers, timeout=5)
        res = requests.get("https://www.reddit.com/login", headers=headers,proxies=dicproxy, timeout=5)
        if res.status_code==200:
            print("成功")
            return True
        return True
   except:

       print("失败")
       return False

def login(user, pwd) -> dict:
    dicproxy = ip_proxy()
    s = requests.session()
    s.proxies = dicproxy
    s.headers = headers
    res=s.get("http://tui.ddns.net/sars/",headers=headers)
    print("已经响应", res)

    res = s.get("https://www.reddit.com/register/?actionSource=header_signup",proxies=dicproxy, verify=False,timeout=10)
    re_res = re.search('<input type="hidden" name="csrf_token" value="(.*?)">', res.text)

    csrf_token = re_res.group(1)

    data = {
        "csrf_token": csrf_token,
        "otp": "",
        "dest": "https://www.reddit.com",
        "password": pwd,
        "username": user,
    }
    # res.headers["content-type"]="application/x-www-form-urlencoded"

    res = s.post("https://www.reddit.com/login", data=data, verify=False)
    # print("登录text",res.text)

    for i in res.cookies:
        print("独立cookie", i)
    print("登录cookie", res.cookies.get_dict())
    cookie = res.cookies.get_dict()
    print(cookie)

    res = requests.get("https://www.reddit.com/", cookies=cookie, headers=headers, verify=False)
    # print(res.text)
    re_res = re.search('url":"/user/%s"'%s, res.text)
    # if re_res.group(1):
    headers["content-type"] = "application/json; charset=UTF-8"
    print("正在访问","https://www.reddit.com/user/%s/submit"%user)
    res_accessToken = requests.get("https://www.reddit.com/user/%s/submit"%user, cookies=cookie, headers=headers,
                            verify=False)
    re_res = re.search('{"accessToken":"(.{18,64})",', res_accessToken.text)
    print("accessToken", re_res.group(1))
    accessToken = re_res.group(1)
    articleList = get_new_article()
    #发文章

    print(article_test(articleList[1]))
    contentData = {"sr": "u_" + user,
                   "api_type": "json",
                   "show_error_list": "true",
                   "title": "woaini" + articleList[0],
                   "spoiler": "true",
                   "nsfw": "false",
                   "kind": "self",
                   "original_content": "true",
                   "submit_type": "profile",
                   "post_to_twitter": "false",
                   "sendreplies": "true",
                   "richtext_json": str(article_test(articleList[1])),
                   # "text":articleList[1],
                   "validate_on_submit": "true"}
    headers["content-type"] = "application/x-www-form-urlencoded"
    headers["authorization"] = "Bearer " + accessToken
    res = requests.post(
        "https://oauth.reddit.com/api/submit?resubmit=true&redditWebClient=desktop2x&app=desktop2x-client-production&rtj=only&raw_json=1&gilding_detail=1",
        data=contentData, cookies=res.cookies.get_dict(), headers=headers, verify=False)
    print(res)
    print("这里发文章结果", res.text)
    resultUrl=res.json()["json"]["data"]["url"]
    print(resultUrl)
    return res.cookies.get_dict()


# def send_article(user,pwd,cookies):

# s=requests.session()
# # s.cookies=cookies
# s.headers=headers
# ##获取xtoken
# res_x_reddit_session=s.get("https://oauth.reddit.com/user/1752545957/moderated_subreddits.json?raw_json=1&gilding_detail=1",cookies=cookies,verify=False)
# print(res_x_reddit_session.headers)


# print(res)
# print("发文章结果:",res.text)


def article_test(content: str):
    # (e:text,t:文本),(e:link,t:文本,u:url)

    rList = []

    def _ahref(matched):
        intStr = matched.group("ahref")  # 123
        addedValue = intStr  # 234
        addedValueStr = "|1_1|" + addedValue + "|1_1|"
        return addedValueStr

    hrefCut = re.sub("(?P<ahref><a href=.*?</a>)", _ahref, content)  # 拿出指定标签并替换其它内容
    hrefList = hrefCut.split("|1_1|")
    for s in hrefList:
        if "<a href" in s:
            href = re.search("href=\"(?P<href>.*?)\"", s).group("href")
            text = re.search("<a href=.*?>(?P<text>.*?)</a>", s)
            if text:
                text2 = re.sub("<.*?>", "", text.group("text"))
                one = {"e": "link", "t": text2, "u": href}
                rList.append(one)
            else:
                text = re.sub("<.*?>", "", s)
                one = {"e": "text", "t": text, }
                rList.append(one)
                # print(s)
        else:
            text = re.sub("<.*?>", "", s)
            one = {"e": "text", "t": text, }
            rList.append(one)

    # "l": 3,

    return json.dumps({"document": [{"e": "par", "c": rList}]},ensure_ascii=False)


if __name__ == '__main__':

    register()
    # cookies = login(user, pwd)
    # send_article(user,pwd,cookies)
    # print(get_new_article())

    # articleList = get_new_article()
    # article_test(articleList[1])

    # s=0
    # for i in range(30):
    #     b=test()
    #     if b:s+=1
    #
    # print(s)
