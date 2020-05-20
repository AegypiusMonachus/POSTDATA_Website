import email
import imaplib
import re
import time

import requests

from project_utils.project_util import EmailVerify, account_activation, get_Session, get_global_params, Logger
from project_utils import g_var


class EmailVerify(object):
    """
    邮箱验证，从注册邮箱中获取链接，访问链接，激活邮箱
    初始化后调用execute_Start  错:返回 -1 更换邮箱
    """

    def __init__(self, username, password, re_text):
        """
        :param username: 邮箱账号
        :param password: 邮箱密码
        :param re_text: 获取参数正则
        """
        self.username = username
        self.password = password
        self.re_text = re_text
        self.server = imaplib.IMAP4_SSL(host='imap-mail.outlook.com', port="993")
        self.server.login(username, password)
        self.inbox_unread = 0
        self.junk_unread = 0

    def get_mail(self, filename):
        # 邮箱中的文件夹，默认为'INBOX'
        inbox = self.server.select(filename)
        # 搜索匹配的邮件，第一个参数是字符集，None默认就是ASCII编码，第二个参数是查询条件，这里的ALL就是查找全部
        typ, data = self.server.search(None, "ALL")
        # 邮件列表,使用空格分割得到邮件索引
        msgList = data[0].split()
        # 最新邮件，第0封邮件为最早的一封邮件
        msgFirstTen = []
        if len(msgList) <= 10:
            msgFirstTen = msgList[::-1]
        else:
            msgFirstTen = msgList[-1:-11:-1]
        msgLen = len(msgFirstTen)
        i = 0
        for eachEmail in msgFirstTen:
            i += 1
            typ, datas = self.server.fetch(eachEmail, '(RFC822)')
            text = datas[0][1]
            texts = str(text, errors='replace')
            message = email.message_from_string(texts)
            result = self.parseBody(message)
            if result:
                return result
            if i == msgLen:
                return ''

    def parseBody(self, message):
        """ 解析邮件/信体 """
        # 循环信件中的每一个mime的数据块
        res_text = ''
        for part in message.walk():
            # 这里要判断是否是multipart，是的话，里面的数据是一个message 列表
            if not part.is_multipart():
                charset = part.get_charset()
                contenttype = part.get_content_type()
                name = part.get_param("name")  # 如果是附件，这里就会取出附件的文件名
                if name:
                    return ''
                    # 下面的三行代码只是为了解码象=?gbk?Q?=CF=E0=C6=AC.rar?=这样的文件名
                    # fh = email.header.Header(name)
                    # fdh = email.header.decode_header(fh)
                    # fname = dh[0][0]
                    # print('附件名:', fname)
                else:
                    # 文本内容
                    res = part.get_payload(decode=True)  # 解码出文本内容，直接输出来就可以了。
                    try:
                        res = res.decode(encoding='utf-8')
                    except:
                        return ""
                    res_text += res
        result = re.findall(self.re_text, res_text)
        if result:
            return result[0]
        else:
            return ''

    def UnseenEmailCount(self):
        try:
            inbox_x, inbox_y = self.server.status('INBOX', '(MESSAGES UNSEEN)')
            junk_x, junk_y = self.server.status('junk', '(MESSAGES UNSEEN)')
            inbox_unseen = int(re.search('UNSEEN\s+(\d+)', str(inbox_y[0])).group(1))
            junk_unseen = int(re.search('UNSEEN\s+(\d+)', str(junk_y[0])).group(1))
            filename_list = []
            if self.inbox_unread == inbox_unseen and self.junk_unread == junk_unseen:
                self.inbox_unread = inbox_unseen
                self.junk_unread = junk_unseen
                return 0, 0, filename_list
            if self.junk_unread < junk_unseen:
                self.junk_unread = junk_unseen
                filename_list.append('junk')
            if self.inbox_unread < inbox_unseen:
                self.inbox_unread = inbox_unseen
                filename_list.append('INBOX')
            return inbox_unseen, junk_unseen, filename_list
        except:
            return 0, 0, []

    def Start(self):
        result = {}
        inbox_unseen, junk_unseen, filename_list = self.UnseenEmailCount()
        if inbox_unseen == 0 and junk_unseen == 0 and filename_list == []:
            result['msg'] = 'Read Failed'
            result['data'] = ''
            return result
        else:
            for filename in filename_list:
                # 依次检查INBOX、JUNK文件夹，有新邮件就返回
                msg = self.get_mail(filename)
                if msg != "":
                    result['msg'] = 'Read Successfully'
                    result['data'] = msg
                    return result
            result['msg'] = 'Read Failed'
            result['data'] = ''
            return result

    def execute_Start(self):
        read_times = 0
        while read_times < 60:
            read_times += 1
            g_var.logger.info("正在检查邮箱%s,user:%s,pwd:%s" % (read_times, self.username, self.password))
            res = self.Start()
            if res['msg'] == 'Read Successfully':
                return res
            time.sleep(2)
        return -1

present_website = "pastebin_com"
g_var.logger = Logger('./' + present_website + '_' + g_var.UUID + '.log', level='info').logger
email_and_passwd = ['seaseaftepy@hotmail.com', '2KW43PFV']

Session = requests.Session()
re_text = '(https://pastebin.com/activate_account.php\?.*?)"'
email_verify_obj = EmailVerify(email_and_passwd[0], email_and_passwd[1], re_text)
verify_url = account_activation(Session, email_verify_obj)
print(verify_url)
