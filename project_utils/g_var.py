import threading
import platform

# @#$ 1、本文件定义整个大项目可能用到的全局变量
# 命令行参数
INTERFACE_HOST = ""        # 中控host
UUID = ""
ALL_COUNT = 0              # 任务分配数量

# 接口下发的全局配置参数
SQL_CONFIG = {}             # SQL参数
TIMEOUT = 99
SEND_STATUS_INTERVAL = 10   # 向中控发送状态间隔
VERIFY_URL1 = ""            # 普通打码平台Url
VERIFY_KEY1 = ""            # 普通打码平台Key
VERIFY_URL2 = ""            # 谷歌验证打码平台Url
VERIFY_KEY2 = ""            # 谷歌验证打码平台Key
EMAIL_INTERVAL_TIME = 0
EMAIL_TIME = 0
CPU_MAX = 0                 # CPU最大允许占用率
RAM_MAX = 0                 # 内存最大允许占用率
THREAD_COUNT = 1            # 线程数

# 爬虫状态信息
NOW_COUNT = 0               # 所有线程进行次数
SUCCESS_COUNT = 0           # 所有线程成功次数
FAILED_COUNT = 0            # 所有线程失败次数
SPIDER_STATUS = 1           # 整个项目的状态，1等待中 2进行中 3已结束（最后一条状态）

# 报错信息
ERR_COUNT = 0               # 最大允许连续错误次数
ERR_CODE = 0                # 错误码
ERR_MSG = ""                # 错误信息
PROXY_ERR_MAX = 100         # 代理最大错误次数
PROXY_ERR_COUNT = 0         # 当前所有线程所有代理连续错误次数
CAPTCHA_ERR_MAX = 100       # 当前所有线程所有验证码连续错误次数
CAPTCHA_ERR_COUNT = 0       # 当前所有线程验证码连续错误次数

# 日志打印对象
logger = ""                 # 在util.get_global_params被创建
# mysql操作对象
mysql_handler = ""          # 在util.get_global_params被创建

# 全局锁
login_data_config_lock = threading.Lock()
login_data_g_var_lock = threading.Lock()
insert_article_lock = threading.Lock()
task_dispatch_lock = threading.Lock()

RETRY_COUNT_MAX = ERR_COUNT         # 最大重试次数,在get_global_params中被赋值
DEFAULT_RETRIES = 20                # requests重试请求次数
USER_ID = -1                        # 当前使用账户ID
REMAIN_TASK_COUNT = ALL_COUNT       # 当前剩余任务数量，在get_global_params中被赋值
SLEEP_TIME = 5                      # try-except报错后挂起时间

if platform.platform()[0:7] == 'Windows':
    ENV_DIR = "."
elif platform.platform()[0:5] == 'Linux':
    ENV_DIR = "/home/web_python/project/SendArticle"
else:
    ENV_DIR = "."
