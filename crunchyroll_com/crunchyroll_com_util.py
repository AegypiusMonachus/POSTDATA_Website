import random
import requests
import MySQLdb

TIMEOUT = 15

DATABASE_HOST = "cdb-hb4r7l0i.bj.tencentcdb.com"
DATABASE_PORT = 10000
DATABASE_USER = "root"
DATABASE_PASSWORD = "W46j_EmFFMXBDF"
DATABASE_NAME = "web2"

# DATABASE_HOST = "localhost"
# DATABASE_PORT = 3306
# DATABASE_USER = "root"
# DATABASE_PASSWORD = "123456"
# DATABASE_NAME = "sendarticles"


def connect_database():
    db = MySQLdb.connect(host=DATABASE_HOST, port=DATABASE_PORT, user=DATABASE_USER, passwd=DATABASE_PASSWORD,
                         db=DATABASE_NAME, charset="utf8")
    return db


def load_image():
    file_data = {
        "key":(None, "qwfffffff888"),
        'file': ('chaptcha.png', open('./image/chaptcha.png', 'rb'))
    }
    url_answer = 'http://89.248.174.24/in.php'
    res = requests.post(url_answer, files=file_data).text
    id_code = res.split("|")[1]
    url_code = "http://89.248.174.24/res.php?key=qwfffffff888&action=get&id="+id_code
    r = requests.get(url_code).text
    return r.split("|")[1]


def generate_headers(signal, postData={}):
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


def generate_random_string(min, max):
    seed = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    random_str = []
    name_digit = random.randint(min, max)
    for i in range(name_digit):
        random_str.append(random.choice(seed))
    random_str = ''.join(random_str)
    return random_str