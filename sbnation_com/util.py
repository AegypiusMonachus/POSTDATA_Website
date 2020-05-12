import random
import string

# 生成用户名或密码
def create_user(min,max):
    user_size = random.randint(min,max)
    random_str = ""
    num = string.ascii_letters + string.digits
    for i in range(user_size):
        random_str += random.choice(num)
    return random_str

# 生成boundary
def create_boundary():
    boundary = ""
    num = string.ascii_letters + string.digits
    for i in range(16):
        boundary += random.choice(num)
    return boundary

if __name__ == '__main__':
    res = create_user(8, 12)
    print(res)