import sys
sys.path.append('./')
from pastebin_com.pastebin_com_util import PastebinCom
from project_utils import g_var, requestsW
from project_utils.project_util import get_command_line_arguments, get_global_params, generate_login_data, ip_proxy

if __name__ == '__main__':
    present_website = "pastebin_com"
    VPN = "en"
    uuid = "1234567890"
    host = "http://192.168.31.234:8080"
    count = 10
    # 获取命令行传入参数
    # args = get_command_line_arguments()
    g_var.ALL_COUNT = count
    g_var.INTERFACE_HOST = host
    g_var.UUID = uuid
    # 获取配置参数
    get_global_params(present_website, True)

    # 1、注册测试
    # PastebinCom(1).registers(present_website, VPN)

    # 2、登录测试
    # s = requestsW.session()
    # userInfo = generate_login_data(present_website, "D:\qianwei_gitrepo\SendArticle\pastebin_com\config.json") #网站下json绝对路径
    # loginData = PastebinCom(1).login(s, present_website, VPN, userInfo)

    # 3、发送文章测试
    s = requestsW.session()
    s.proxies = ip_proxy("en")
    userInfo = generate_login_data(present_website, "D:\qianwei_gitrepo\SendArticle\pastebin_com\config.json") #网站下json绝对路径
    loginData = {
        'id': userInfo[0],
        'username': userInfo[1],
        'password': userInfo[2],
        'email': userInfo[3],
        'cookie': eval(userInfo[5]),
    }
    PastebinCom(1).send_profile(s, loginData)
