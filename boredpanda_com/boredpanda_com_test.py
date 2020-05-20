from boredpanda_com.boredpanda_com_dome import register_test
from boredpanda_com.boredpanda_com_util import BoredpandaCom
from project_utils import g_var, requestsW
from project_utils.project_util import get_command_line_arguments, get_global_params, generate_login_data


if __name__ == '__main__':
    present_website = "boredpanda_com"
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
    get_global_params(present_website,True)
    #注册测试
    # BoredpandaCom(3).registers(present_website,VPN)

    ##登录测试
    # s = requestsW.session()
    # userInfo = generate_login_data(present_website,"网站json/config.json")#网站下json绝对路径
    # loginData = BoredpandaCom(3).login(s, present_website, VPN, userInfo)

    ##发送文章测试
    # userInfo = generate_login_data(present_website,"网站json/config.json")#网站下json绝对路径
    # BoredpandaCom(1).loginAndPostMessage(present_website,VPN)
    print(register_test())