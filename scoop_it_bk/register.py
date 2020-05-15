import random
import sys

import requests
from lxml import etree


def generate_random_string(min: int, max: int) -> str:
    seed = "abcdefghijklmnopqrstuvwxyz"
    random_str = []
    name_digit = random.randint(min, max)
    for i in range(name_digit):
        random_str.append(random.choice(seed))
    random_str = ''.join(random_str)
    return random_str


def generate_random_phoneNum() -> str:
    seed = "0123456789"
    random_str = []
    for i in range(8):
        random_str.append(random.choice(seed))
    random_str = "86158" + ''.join(random_str)
    return random_str


def generate_random_jobTitle() -> str:
    list = ["CEO", "CFO", "CIO", "VPIT", "EVPIT", "DirectorIT", "ManagerIT", "EVPBS", "DirectorBS",
            "Rockstar", "Roadie", "BSManager", "Grunt", "smarty_pants", "fancy_pants", "consultant", "lazy", "pissoff"]
    jobTitle_digit = random.randint(0, len(list) - 1)
    return list[jobTitle_digit]


def generate_random_company_size() -> str:
    list = ["XXXL", "XXL", "XL", "L", "M", "S", "XS", "TINY", "NA"]
    size_digit = random.randint(0, len(list) - 1)
    return list[size_digit]


def generate_random_company_name() -> str:
    seed = "abcdefghijklmnopqrstuvwxyz"
    random_str = []
    name_digit = random.randint(40)
    for i in range(name_digit):
        random_str.append(random.choice(seed))
    random_str = ''.join(random_str)
    return random_str


def generate_random_country() -> str:
    list = ["USA", "NA", "AFG", "ALB", "DZA", "ASM", "AND", "AGO", "AIA", "ATA", "ATG", "ARG", "ARM",
            "ABW", "AUS", "AUT", "AZE", "BHS", "BHR", "BGD", "BRB", "BLR", "BEL", "BLZ", "BEN", "BMU",
            "BTN", "BOL", "BIH", "BWA", "BVT", "BRA", "IOT", "BRN", "BGR", "BFA", "BDI", "KHM", "CMR",
            "CAN", "CPV", "CYM", "CAF", "TCD", "CHL", "CHN", "CXR", "CCK", "COP", "COM", "COG", "COK",
            "CRI", "CIV", "HRV", "CUB", "CYP", "CZE", "DNK", "DJI", "DMA", "DOM", "TMP", "ECU", "EGY",
            "SLV", "GNQ", "ERI", "EST", "ETH", "FLK", "FRO", "FJI", "FIN", "FRA", "GUF", "PYF", "ATF",
            "GAB", "GMB", "GEO", "DEU", "GHA", "GIB", "GBR", "GRC", "GRL", "GRD", "GLP", "GUM", "GTM",
            "GIN", "GNB", "GUY", "HTI", "HMD", "HND", "HKG", "HUN", "ISL", "IND", "IDN", "IRN", "IRQ",
            "IRL", "ISR", "ITA", "JAM", "JPN", "JOR", "KAZ", "KEN", "KIR", "RKS", "KWT", "KGZ", "LAO",
            "LVA", "LBN", "LSO", "LBR", "LBY", "LIE", "LTU", "LUX", "MAC", "MKG", "MDG", "MWI", "MYS",
            "MDV", "MLI", "MLT", "MHL", "MTQ", "MRT", "MUS", "MYT", "FXX", "MEX", "FSM", "MDA", "MCO",
            "MNG", "MSR", "MAR", "MOZ", "MMR", "NAM", "NRU", "NPL", "NLD", "ANT", "NCL", "NZL", "NIC",
            "NER", "NGA", "NIU", "NFK", "PRK", "MNP", "NOR", "OMN", "PAK", "PLW", "PAL", "PAN", "PNG",
            "PRY", "PER", "PHL", "PCN", "POL", "PRT", "PRI", "QAT", "REU", "ROM", "RUS", "RWA", "SHN",
            "KNA", "LCA", "SPM", "VCT", "WSM", "SMR", "STP", "SAU", "SEN", "YUG", "SYC", "SLE", "SGP",
            "SVK", "SVN", "SLB", "SOM", "ZAF", "SGS", "KOR", "ESP", "LKA", "SDN", "SUR", "SJM", "SWZ",
            "SWE", "CHE", "SYR", "TWN", "TJK", "TZA", "THA", "COD", "TGO", "TKL", "TON", "TTO", "TUN",
            "TUR", "TKM", "TCA", "TUV", "UGA", "UKR", "ARE", "UMI", "URY", "UZB", "VUT", "VAT", "VEN",
            "VNM", "VIR", "VGB", "WLF", "ESH", "YEM", "ZAR", "ZMB", "ZWE"]


def generate_register_data() -> dict:
    # 生成注册数据返回，并存入数据库
    # 只需生成用户名
    username: str = generate_random_string(12, 16)
    password: str = generate_random_string(12, 16)
    email: str = ""  #@@@email接口

    registerData: dict = {
        'jsDetectedTimeZone': 'Asia/Shanghai',
        'pc':'',
        'displayName': username,
        'shortName': username,
        'email': email,
        'password': password,
        'avatar': "",
        'upload-image-original-url': "",
        'job': "My personal brand or blog",
        'g-recaptcha-response': "",#@@@谷歌接口
        'subscribe': ""
    }

    return registerData


headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'content-type': 'application/x-www-form-urlencoded',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
}


def register(register_num: int):
    count = 0  # 注册成功计数
    for i in range(0, register_num):
        session = requests.Session()

        url_register = "https://www.scoop.it/subscribe?&token=&sn=&showForm=true"
        registerData: dict = generate_register_data()

        resp = session.post(url_register, headers=headers, data=registerData)
        print(resp.text)
        #@@@跳转邮箱验证


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("参数错误！")
    else:
        register_num = int(sys.argv[1])   #注册新账号数量，0则不注册
        register(register_num)