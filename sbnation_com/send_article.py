import requests
import json
import re

from requests_toolbelt.multipart.encoder import MultipartEncoder
from util import create_boundary, create_user

# 获取session_id
def get_session_id():
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
    }
    url = 'https://auth.voxmedia.com/login?return_to=https://www.sbnation.com/'
    res = requests.get(url, headers=headers, verify=False)
    str_session = res.headers['Set-Cookie']
    if not str_session:
        print('获取Set-Cookie值失败。。。')
        return -1
    list_session = str_session.split(';')
    if not list_session:
        print('获取_session_id值失败。。。')
        return -1
    return list_session[0]

# 获取超链接和标题
def get_title_link():
    url = 'http://192.168.31.234:8080/v1/get/title_or_link/'
    res = requests.get(url, verify=False)
    if not res.text:
        print('标题和链接获取失败。。。')
        return -1
    title_link = res.text.split('|_|')
    return title_link

def login():
    session_id = get_session_id()
    if session_id == -1:
        print('未得到session_id值。。。')
        return -1
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Host': 'auth.voxmedia.com',
        'Origin': 'https://auth.voxmedia.com',
        'Referer': 'https://auth.voxmedia.com/login?return_to=https://www.sbnation.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
        'Cookie': session_id,
        'X-Requested-With': 'XMLHttpRequest',
    }
    data = {
        'username': 'WtcAIT1vqQ',
        'password': 'QCLNte8VSk',
        'remember_me': 'false',
        'g-recaptcha-response': '',
    }
    url = 'https://auth.voxmedia.com/chorus_auth/initiate_password_auth.json'
    res = requests.post(url, data=data, headers=headers, verify=False)
    res_data = json.loads(res.text)
    if res_data['logged_in']:
        print('登陆成功。。。')
        session_id_article = re.findall('_session_id=(.*?);', res.headers['Set-Cookie'])
        authenticity_token, session_id = get_authenticity_token(session_id_article[0], data['username'])
        if authenticity_token == -1 or session_id == -1:
            print('未获取到authenticity_token或者session_id值。。。')
            return -1
        res_send = send_article(session_id, authenticity_token, data['username'])
        if res_send == -1:
            print('个人资料页网址修改失败。。。')
        return 0
    print('登陆失败。。。')
    return -1

# 获取authenticity_token用于修改个人网址
def get_authenticity_token(session_id_article, name):
    headers = {
        'Host': 'www.sbnation.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Referer': 'https://www.sbnation.com/users/'+name,
        'Cookie': '_session_id='+session_id_article,
    }
    url = 'https://www.sbnation.com/users/'+name+'/edit_profile'
    res = requests.get(url, headers=headers, verify=False)
    token_list = re.findall('name="authenticity_token" value="(.*?)" />', res.text)
    if not token_list:
        print('获取authenticity_token失败。。。')
        return -1, -1
    session_list = re.findall('_session_id=(.*?);', res.headers['Set-Cookie'])
    if not session_list:
        print('获取session_id失败。。。')
        return -1, -1
    return token_list[0], session_list[0]

# 修改个人资料页中的个人网址
def send_article(session_id_article, authenticity_token, name):
    headers = {
        'Host': 'www.sbnation.com',
        'Origin': 'https://www.sbnation.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Referer': 'https://www.sbnation.com/users/'+name+'/edit_profile',
        'Cookie': '_session_id='+session_id_article,
    }
    title_link = get_title_link()
    print(title_link)
    if title_link == -1:
        print('未获取到标题和链接。。。')
        return -1
    multipart_encoder = MultipartEncoder(
        fields={
            'utf8': '✓',
            '_method': 'patch',
            'authenticity_token': authenticity_token,
            'profile_image[filename]': ('', '', 'application/octet-stream'),
            'profile_image[filename_cache]': '',
            'network_membership[bio]': '',
            'network_membership[signature]': '',
            'network_membership[public_email]': '',
            'network_membership[website_name]': title_link[0],
            'network_membership[website_url]': title_link[1],
            'network_membership[facebook_page_url]': '',
            'network_membership[facebook_page_url]': '',
            'network_membership[network_membership_items_attributes][0][key]': 'MLB',
            'network_membership[network_membership_items_attributes][0][value]': '',
            'network_membership[network_membership_items_attributes][1][key]': 'NFL',
            'network_membership[network_membership_items_attributes][1][value]': '',
            'network_membership[network_membership_items_attributes][2][key]': 'NBA',
            'network_membership[network_membership_items_attributes][2][value]': '',
            'network_membership[network_membership_items_attributes][3][key]': 'NHL',
            'network_membership[network_membership_items_attributes][3][value]': '',
            'network_membership[network_membership_items_attributes][4][key]': 'NCAAF',
            'network_membership[network_membership_items_attributes][4][value]': '',
            'network_membership[network_membership_items_attributes][5][key]': 'NCAAB',
            'network_membership[network_membership_items_attributes][5][value]': '',
            'network_membership[network_membership_items_attributes][6][key]': 'MMA',
            'network_membership[network_membership_items_attributes][6][value]': '',
            'network_membership[network_membership_items_attributes][7][key]': 'Golf',
            'network_membership[network_membership_items_attributes][7][value]': '',
            'network_membership[network_membership_items_attributes][8][key]': 'NASCAR',
            'network_membership[network_membership_items_attributes][8][value]': '',
            'network_membership[network_membership_items_attributes][9][key]': 'Boxing',
            'network_membership[network_membership_items_attributes][9][value]': '',
            'network_membership[network_membership_items_attributes][10][key]': 'Soccer',
            'network_membership[network_membership_items_attributes][10][value]': '',
            'network_membership[network_membership_items_attributes][11][key]': 'MLS',
            'network_membership[network_membership_items_attributes][11][value]': '',
            'network_membership[network_membership_items_attributes][12][key]': 'EPL',
            'network_membership[network_membership_items_attributes][12][value]': '',
            'network_membership[network_membership_items_attributes][13][key]': 'Football League Championship',
            'network_membership[network_membership_items_attributes][13][value]': '',
            'network_membership[network_membership_items_attributes][14][key]': 'FIFA',
            'network_membership[network_membership_items_attributes][14][value]': '',
            'network_membership[network_membership_items_attributes][15][key]': 'Bundesliga',
            'network_membership[network_membership_items_attributes][15][value]': '',
            'network_membership[network_membership_items_attributes][16][key]': 'Serie A',
            'network_membership[network_membership_items_attributes][16][value]': '',
            'network_membership[network_membership_items_attributes][17][key]': 'La Liga',
            'network_membership[network_membership_items_attributes][17][value]': '',
            'network_membership[network_membership_items_attributes][18][key]': 'Cycling',
            'network_membership[network_membership_items_attributes][18][value]': '',
            'network_membership[network_membership_items_attributes][19][key]': 'Tennis',
            'network_membership[network_membership_items_attributes][19][value]': '',
            'network_membership[network_membership_items_attributes][20][key]': 'General',
            'network_membership[network_membership_items_attributes][20][value]': '',
            'commit': 'Update',
        },
        boundary='----WebKitFormBoundary' + create_boundary(),
    )
    headers['Content-Type'] = multipart_encoder.content_type

    url = 'https://www.sbnation.com/users/'+name+'/update_profile'
    res = requests.post(url, data=multipart_encoder, headers=headers, verify=False)
    print(res.status_code)
    if res.status_code != 200:
        print('修改个人资料页的网址失败。。。')
        return -1
    return 0

if __name__ == '__main__':
    login()
    # get_session_id()
    # get_title_link()