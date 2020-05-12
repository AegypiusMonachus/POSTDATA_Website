import sys
sys.path.append('../')
from crunchyroll_com.register import register
from crunchyroll_com.send_article import loginAndPostMessage

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("参数错误！")
    else:
        register_num = int(sys.argv[1])   #注册新账号数量，0则不注册
        article_num = int(sys.argv[2])    #发表文章数量
        register(register_num)            # register将注册数据存入数据库
        loginAndPostMessage(article_num)  # login和postMessage去数据库读取账户信息