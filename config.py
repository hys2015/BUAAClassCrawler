#-*- encoding: utf-8 -*-

##账号和密码, 需要为http://gsmis.graduate.buaa.edu.cn/gsmis/main.do的账号与密码
#e.g.:
#username = r"SY16xxxxx"
#password = r"********"
username = r""
password = r""

##
# 年份与学期
year = r"2016"
# 1 or 2
kkjj = r"1"

##
#输出课表的名称，必须为html格式
target = r"schedule.html"

def main():
    print(username)
    print(password)
	
if __name__ == "__main__":
	main()

