from sbnation_com.sbnation_com_util import SbnationCom
from project_utils import g_var, requestsW
from project_utils.project_util import get_command_line_arguments, get_global_params, generate_login_data


if __name__ == '__main__':
    present_website = "sbnation_com"
    VPN = "en"
    uuid = "1234567890"
    host = "http://192.168.31.234:8080"
    count = 1
    # 获取命令行传入参数
    # args = get_command_line_arguments()
    g_var.ALL_COUNT = count
    g_var.INTERFACE_HOST = host
    g_var.UUID = uuid
    # 获取配置参数
    get_global_params(present_website,True)
    #注册测试
    # SbnationCom(1).registers(present_website,VPN)

    ##登录测试
    # s = requestsW.session()
    # userInfo = generate_login_data(present_website,"网站json/config.json")#网站下json绝对路径
    # loginData = SbnationCom(3).login(s, present_website, VPN, userInfo)

    ##发送文章测试
    # userInfo = generate_login_data(present_website,"D:\SendArticle\sbnation_com\config.json")#网站下json绝对路径
    SbnationCom(1).registerAndSendProfile(present_website,VPN)
