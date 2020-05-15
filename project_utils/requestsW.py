import requests
from requests.exceptions import ConnectTimeout, ReadTimeout, ConnectionError
from project_utils import g_var
from project_utils.g_var import PROXY_ERR_MAX

#封装requests库 自动换ip


class Session(requests.Session):
    def __init__(self):
        super().__init__()
    def get(self, url, **kwargs):
        i = 1
        if "timeout" not in kwargs:
            kwargs["timeout"]=g_var.TIMEOUT

        while i < PROXY_ERR_MAX:

            if "proxies" in kwargs or self.proxies!={}:
                g_var.logger.info("ip重试%s次," % i)
                kwargs["proxies"] = ip_proxy("en")
            i += 1
            try:
                return super().get(url, **kwargs)
            except (ConnectTimeout, ReadTimeout):
                pass
            except (ConnectionError):
                pass
                # print(e)
            except Exception as e:
                g_var.logger.info("未知错误"+ str(e))
        return -1
    def post(self, url, data=None, json=None, **kwargs):
        i = 1
        if "timeout" not in kwargs:
            kwargs["timeout"]=g_var.TIMEOUT
        while i < PROXY_ERR_MAX:
            if "proxies" in kwargs or self.proxies!={}:
                g_var.logger.info("ip重试%s次," % i)
                kwargs["proxies"] = ip_proxy("en")
            i += 1
            try:
                return super().post(url, data=data, json=json, **kwargs)
            except (ConnectTimeout, ReadTimeout):
                pass
            except (ConnectionError)as e:
                pass
                # print(e)
            except Exception as e:
                g_var.logger.info("未知错误"+str(e) )
        return -1



def session():
    return Session()


#requests.exceptions.SSLError: SOCKSHTTPSConnectionPool(host='www.goole.com', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLError(1, '[SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error (_ssl.c:1108)')))
#requests.exceptions.ConnectionError: SOCKSHTTPSConnectionPool(host='www.youtube.com', port=443): Max retries exceeded with url: / (Caused by ProtocolError('Connection aborted.', ConnectionResetError(54, 'Connection reset by peer')))

def get(url, **kwargs):
    i=1
    if "timeout" not in kwargs:
        kwargs["timeout"] = g_var.TIMEOUT
    while i<PROXY_ERR_MAX:
        i += 1
        if i!=0 and "proxies" in kwargs:
            g_var.logger.info("ip重试%s次:" % i)
            kwargs["proxies"]=ip_proxy("en")
        try:
            return requests.get(url, **kwargs)
        except (ConnectTimeout,ReadTimeout):
            pass
        except (ConnectionError)as e:
            pass
        except Exception as e:
            g_var.logger.info("未知错误"+str(e))
    return -1



def post(url, data=None, json=None, **kwargs):
    i=1
    if "timeout" not in kwargs:
        kwargs["timeout"] = g_var.TIMEOUT
    while i<PROXY_ERR_MAX:
        if i!=0 and "proxies" in kwargs:
            g_var.logger.info("ip重试%s次:" % i)
            kwargs["proxies"]=ip_proxy("en")
        i += 1
        try:
            return requests.post(url, data=data, json=json, **kwargs)
        except (ConnectTimeout,ReadTimeout):
            pass
        except (ConnectionError)as e:
            pass
            # print(e)
        except Exception as e:
            g_var.logger.info("未知错误"+str(e))
    return -1


def put(url, data=None, **kwargs):
    i=1
    if "timeout" not in kwargs:
        kwargs["timeout"] = g_var.TIMEOUT
    while i<PROXY_ERR_MAX:
        if i!=0 and "proxies" in kwargs:
            g_var.logger.info("ip重试%s次:" % i)
            kwargs["proxies"]=ip_proxy("en")
        i += 1
        try:
            return requests.put(url, data=data, **kwargs)
        except (ConnectTimeout,ReadTimeout):
            pass
        except (ConnectionError)as e:
            pass
        except Exception as e:
            g_var.logger.info("未知错误"+str(e))
    return -1


def ip_proxy(vpn: str):
    """
    获取代理
    Args:
        vpn:网站vpn访问类型
    Returns:
        成功返回Session对象
        错误返回{"error": -1}
    """
    get_article_interface_url = g_var.INTERFACE_HOST + "/v1/get/ip/?vpn=" + vpn
    try:
        # proxy = requests.get(url=get_article_interface_url, timeout=g_var.TIMEOUT).text
        headers = {
            'Connection': 'close',
        }
        requests.adapters.DEFAULT_RETRIES = g_var.DEFAULT_RETRIES
        with requests.get(url=get_article_interface_url, headers=headers, timeout=g_var.TIMEOUT) as r:
            proxy = r.text
    except:
        g_var.ERR_CODE = 2001
        g_var.ERR_MSG = g_var.ERR_MSG + "无法获取proxy!"
        g_var.logger.error("无法获取proxy!")
        return {"error": -1}

    if vpn == "ch":
        proxy_list = proxy.split("|_|")
        # 代理服务器
        proxyHost = "http-dyn.abuyun.com"
        proxyPort = "9020"
        # 代理隧道验证信息
        proxyUser = proxy_list[0]
        proxyPass = proxy_list[1]

        proxyMeta = "http://%(user)s:%(pass)s@%(host)s:%(port)s" % {
            "host": proxyHost,
            "port": proxyPort,
            "user": proxyUser,
            "pass": proxyPass,
        }
        proxies = {
            "http": proxyMeta,
            "https": proxyMeta,
        }
    elif vpn == "en":
        proxy = proxy.strip()
        proxies = {
            "http": proxy,
            "https": proxy,
        }
        if "socks5" in proxies["https"]:
            proxies["https"]=proxies["https"].replace("socks5","socks5h")
    return proxies