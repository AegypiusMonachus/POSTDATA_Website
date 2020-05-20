import sys
import random
from http import cookiejar
import urllib.request
import urllib.parse


sys.path.append('../')
from crunchyroll_com.crunchyroll_com_util import TIMEOUT
from crunchyroll_com.crunchyroll_com_util import load_image, connect_database, generate_headers, generate_random_string


def generate_random_theme():
    list = ["Blue", "Green", "Grey", "Orange", "White", "Beans", "Bug", "Butterfly", "Cheese", "Chips", "Clover",
            "Fire", "Gargoyle", "GreenTomatoes", "Ireland", "Mountains", "Rosebud", "SaltnPepper", "Sunrise", "Sunset"]
    theme_digit = random.randint(0, len(list)-1)
    return list[theme_digit]


def generate_register_data(captcha_code:str):
    # 生成注册数据返回，并存入数据库
    # 只需生成用户名
    username = generate_random_string(8, 12)
    password = generate_random_string(10, 16)
    theme = generate_random_theme()

    postData = {
        'form': 'form.register',
        'name': username,
        'password': password,
        'mail': username+"@mail.nu",
        'site': username+".mee.nu",
        'sitename': username,
        'theme': theme,
        'captcha': captcha_code,
        'terms_ok': '1',
        'age_ok': '1',
        'register': 'register',
    }

    return postData


def register(register_num):

    # 通过CookieHandler创建opener
    cookie = cookiejar.CookieJar()
    handler = urllib.request.HTTPCookieProcessor(cookie)
    opener = urllib.request.build_opener(handler)

    count = 0
    for i in range(0, register_num):
        # 获取验证码
        url_image = 'http://mee.nu/captcha/'

        try_times = 0
        while try_times < 3:
            try:
                print("获取验证码，尝试第", try_times + 1, "次")
                picture = opener.open(url_image, timeout=TIMEOUT).read()
                try_times = 4
            except:
                try_times = try_times + 1
        if try_times == 3:
            print("get captcha timeout!")

        file = open('./image/chaptcha.png', 'wb')
        file.write(picture)
        file.close()

        # 识别验证码
        captcha_code = load_image()
        print(captcha_code)

        headers = generate_headers(0)
        postData = generate_register_data(captcha_code)

        url_register = 'https://mee.nu/'
        fdata = urllib.parse.urlencode(postData).encode(encoding='UTF8')
        req = urllib.request.Request(url_register, headers=headers, data=fdata)

        # 注册成功，将数据保存到数据库
        # result中包含"Thank you for registering"，则表示注册成功

        try_times = 0
        while try_times < 3:
            try:
                print("提交注册中，尝试第", try_times + 1, "次")
                response = opener.open(req, timeout=TIMEOUT)
                try_times = 4
            except:
                try_times = try_times + 1
        if try_times == 3:
            print("register timeout!")

        result = response.read().decode("utf-8")
        sucsess_sign = "Thank you for registering"
        if sucsess_sign in result:
            db = connect_database()
            cursor = db.cursor()
            sql = "INSERT INTO mee_nu(username, password, mail, status) VALUES('" + postData['name'] + \
                  "', '" + postData['password'] + "', '" + postData['mail'] + "', '" + str(0) + "');"
            try:
                cursor.execute(sql)
                db.commit()
                count = count + 1
            except Exception as e:
                print("db error,", e)
                db.rollback()
        else:
            print("register fail!")
    print("注册成功：%d，失败：%d" % (count, register_num-count))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("参数错误！")
    else:
        register_num = int(sys.argv[1])   #注册新账号数量，0则不注册
        register(register_num)

