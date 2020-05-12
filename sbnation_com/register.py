import requests
import time
import json

from sbnation_com.util import create_user

# 获取session_id
def get_session_id():
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
    }
    url = 'https://auth.voxmedia.com/signup?return_to=https://www.sbnation.com/'
    res = requests.get(url, headers=headers, verify=False)
    str_session = res.headers['Set-Cookie']
    if not str_session:
        print('获取Set-Cookie值失败。。。')
        return -1
    list_session = str_session.split(';')
    if not list_session:
        print('获取_session_id值失败。。。')
        return -1
    return list_session[0]

# 人机身份验证码识别
def get_captcha():
    print("谷歌人机识别，等待30s")
    data = {
        'key': 'cb02438b4c9a94f746aa7bbd9477a834',
        'method': 'userrecaptcha',
        'googlekey': '6LefyhkTAAAAANpeEKwwgimNneiKWXRQtEqFZbat',
        'pageurl': 'https://auth.voxmedia.com/signup?return_to=https://www.sbnation.com/',
    }
    url_captcha = 'https://2captcha.com/in.php'
    res = requests.get(url_captcha, params=data, verify=False)
    id_code = res.text.split("|")[1]
    while True:
        time.sleep(30)
        url_code = "https://2captcha.com/res.php?key=cb02438b4c9a94f746aa7bbd9477a834&action=get&id=" + id_code
        r = requests.get(url_code, verify=False)
        code_list = r.text.split("|")
        if len(code_list) != 2:
            pass
        else:
            break
    return code_list[1]

def register():
    recaptcha_response = get_captcha()
    print(recaptcha_response)
    session_id = get_session_id()
    if session_id == -1:
        print('未获取到_session_id值。。。')
        return -1
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://auth.voxmedia.com',
        'referer': 'https://auth.voxmedia.com/signup?return_to=https://www.sbnation.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        'cookie': session_id,
    }
    username = create_user(8, 12)
    password = create_user(10, 14)
    email = username + '@hotmail.com'
    data = {
        'g-recaptcha-response': recaptcha_response,
        'user[username]': username,
        'user[password]': password,
        'user[email]': email,
        'user[newsletter]': 'false',
        'community_id': '671',
    }
    print(data)

    url = 'https://auth.voxmedia.com/chorus_auth/register.json'
    res = requests.post(url, data=data, headers=headers, verify=False)
    print(res.status_code)
    print(res.text)
    res_data = json.loads(res.text)
    if res_data['success']:
        print('注册成功。。。')
        return 0
    print('注册失败。。。')
    return -1


if __name__ == '__main__':
    register()
    # get_session_id()