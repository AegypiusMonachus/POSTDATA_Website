import json
import time
import threading
import sys
sys.path.append('./')                 # 在SendArticle目录执行
sys.path.append('/home/web_python/project/SendArticle')

import psutil
from playbuzz_com.playbuzz_com_util import PlaybuzzCom
from project_utils.project_util import get_command_line_arguments, get_global_params, send_spider_status, \
    send_spider_block_status, MysqlHandler
from project_utils import g_var


if __name__ == "__main__":

    present_website = "playbuzz_com"
    VPN = "en"

    # 获取命令行传入参数
    args = get_command_line_arguments()
    g_var.ALL_COUNT = int(args.count)
    g_var.INTERFACE_HOST = args.host
    g_var.UUID = args.uuid

    # 获取配置参数
    get_global_params(present_website)

    # 检查cpu和内存状态
    while psutil.virtual_memory().percent > g_var.RAM_MAX or psutil.cpu_percent(None) > g_var.CPU_MAX:
        g_var.logger.info("cpu或内存不足，挂起"+str(g_var.SEND_STATUS_INTERVAL)+"s")
        g_var.SPIDER_STATUS = 1
        close_signal = send_spider_block_status()
        if close_signal == 1:
            quit()
        time.sleep(g_var.SEND_STATUS_INTERVAL)

    # 开始执行程序
    g_var.SPIDER_STATUS = 2

    # 考虑平均分配不是正好分的情况:例如94个任务分配给10个线程，先94/10取整，每个线程9个任务，剩余4个任务给前4个线程每个加1个任务
    EACH_THREAD_ASSIGNMENT_NUM = int(g_var.ALL_COUNT / g_var.THREAD_COUNT)  # 每个线程分配的基本任务数量
    ADD_ONE_ASSIGNMENT_THREAD_NUM = g_var.ALL_COUNT % g_var.THREAD_COUNT    # 需要增加一个任务的线程个数
    REMAIN_THREAD_NUM = g_var.THREAD_COUNT - ADD_ONE_ASSIGNMENT_THREAD_NUM  # 剩余不用增加任务的线程个数
    g_var.logger.info("EACH_THREAD_ASSIGNMENT_NUM" + str(EACH_THREAD_ASSIGNMENT_NUM))

    # 创建一个对象列表
    obj_list = []
    for i in range(0, ADD_ONE_ASSIGNMENT_THREAD_NUM):
        obj_list.append(PlaybuzzCom(EACH_THREAD_ASSIGNMENT_NUM + 1))
    if EACH_THREAD_ASSIGNMENT_NUM != 0:
        for i in range(0, REMAIN_THREAD_NUM):
            obj_list.append(PlaybuzzCom(EACH_THREAD_ASSIGNMENT_NUM))

    # 为每个对象开一个线程，加入到线程列表中统一管理
    t_list = []
    for i in range(0, len(obj_list)):
        t = threading.Thread(target=obj_list[i].start, args=(present_website, VPN))
        t_list.append(t)

    # 线程开始执行
    for i in range(0, len(t_list)):
        t_list[i].setDaemon(True)
        t_list[i].start()

    # 定时发送状态
    close_send_status_signal = 0  # 发送消息的循环要等所有线程停止才能跳出循环
    wait_signal = 0

    while g_var.SPIDER_STATUS != 3 or close_send_status_signal != 1:
        close_send_status_signal, wait_signal = send_spider_status(obj_list, t_list)
        time.sleep(g_var.SEND_STATUS_INTERVAL)

    if wait_signal == 0:
        # 等待所有线程结束
        g_var.logger.info("等待所有线程结束")
        for i in range(0, len(t_list)):
            t_list[i].join()
    elif wait_signal == 1:
        # 不等待其他线程结束，直接停止
        g_var.logger.info("不等待其他线程结束，直接停止")

    MysqlHandler().dbclose()     # 关闭数据库
    g_var.logger.info("主线程结束！共计完成" + str(g_var.SUCCESS_COUNT) + "个\n\n\n\n\n")
