#!/usr/bin/python
# -*- encoding: UTF-8 -*-
import re
import config
import string
import requests
import subprocess
from bs4 import BeautifulSoup

class Crawler():


    def __init__(self):
        self.baseUrl = 'http://gsmis.graduate.buaa.edu.cn'
        self.loginUrl = 'http://gsmis.graduate.buaa.edu.cn/gsmis/indexAction.do'
        self.imageUrl = self.baseUrl + '/gsmis/Image.do'
        
        self.all_courses_cache = 'all_courses.html'
        # 使用代理
        proxies = {
            'http': 'http://218.202.111.10:80',
            'http': 'http://111.11.122.7:80'
        }

        self.cookies = ''
        self.session = requests.Session()
        #self.session.proxies.update(proxies)

        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, sdch",
            "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6",
            "Connection": "keep-alive",
            "Host": "gsmis.graduate.buaa.edu.cn",
            "User-Agent": "Mozilla/5.0(X11;Linuxx86_64) AppleWebKit/537.36(KHTML, like Gecko) Ubuntu Chromium/51.0.2704.79 Chrome/51.0.2704.79 Safari/537.36"
        }

    def __del__(self):
        pass

    # 获取验证码
    def get_verify_code(self):
        res = self.session.get(url=self.imageUrl, headers=self.headers)
        with open('verify.jpg', 'wb') as f:
            f.write(res.content)

        # 保存此次访问验证码对应的cookie
        self.cookies = res.cookies

        # 使用tesseract来识别验证码, 并保存到verify.txt中
        p = subprocess.Popen(['tesseract', 'verify.jpg', 'verify'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()

        # 返回验证码
        with open('verify.txt', 'r') as f:
            return f.read()

    # 过滤验证码
    def filter_verify_code(self, verifyCode):
        # 找出被错误识别为字母的数字

        if len(verifyCode) < 4:
            return verifyCode

        alpha_digit_map = {
                'B': '8',
                'D': '0',
                'E': '6',
                'g': '9',
                'i': '1',
                'I': '1',
                'j': '1',
                'J': '1',
                'm': '11',
                'M': '11',
                'o': '0',
                'O': '0',
                'q': '9',
                'Q': '0',
                's': '5',
                'S': '5',
                'z': '2',
                'Z': '2',
                }

        # 将错误识别的字母替换为相似的数字
        verifyCode.translate(alpha_digit_map)

        # 使用正则表达式匹配4位数字
        regx = re.compile('(\d{4})')
        code = regx.match(verifyCode)
        if not code :
            raise TypeError("请检查帐号密码是否正确!")
        return code.group()

    # 直到登录成功为止
    def login(self):

        while True:
            # 获取验证码
            verifyCode = self.get_verify_code()

            verifyCode = verifyCode.strip()
            punctuation = string.punctuation + '‘’'
            for cha in punctuation:
                verifyCode = verifyCode.replace(cha, '')
            verifyCode = verifyCode.strip()

            # 验证码始终是四位数，因此过滤掉不符合条件的结果
            # 使用正则表达式来提取4位数字
            if len(self.filter_verify_code(verifyCode)) == 4:
                print('验证码 =', verifyCode)
                break


        data = {
            "id" : config.username,
            "password" : config.password,
            "checkcode" : verifyCode
        }

        self.session.cookies.update(self.cookies)

        response = self.session.post(url=self.loginUrl, data=data, headers=self.headers)
        if response.text.find('您的位置') != -1:
            print('登录成功')
        elif response.text.find('密码错误') != -1:
            print('没用户名或者密码错误！，请检查您的配置')
        else:
            self.login()
    ## 获得课程表信息
    def getCourseArrange(self):
        ## 服务器端在这里做了一些py交易
        self.todoUrl = self.baseUrl + '/gsmis/toModule.do?prefix=/py&page=/pySelectCourses.do?do=xsXuanKe'
        resp = self.session.get(url = self.todoUrl , headers = self.headers)
        ##选课URL
        self.xkUrl = self.baseUrl + '/gsmis/py/pyYiXuanKeCheng.do'
        resp = self.session.get(url = self.xkUrl, headers = self.headers)
        #with open("xk.htm","w") as wt:    
        #   wt.write(resp.text)
        soup = BeautifulSoup(resp.text)
        table_tags = soup.find_all("table")
        target = table_tags[2]
        trs = target.find_all("tr")
        course_bucket = dict()
        course_db = self.generateCourseDataBase()
        for i in range(1, len(trs) - 1):
            tr = trs[i]
            if len(tr) > 5:
                tds = tr.find_all("td")
                course_num = tds[1].string.strip()
                course_name = tds[2].string.strip()
                minus_idx = course_name.index('-')
                course_name = course_name[:minus_idx]
                print('课程号',course_num,'-名称', course_name)
                # 按照 周几-上课时间-课程信息 来组织数据
                self.__addCourseToBucket(course_bucket, course_db[course_name])
        for i in course_bucket:
            lst = course_bucket[i]    
            course_bucket[i] = sorted(lst, key = lambda k: int(k['classes'][:k['classes'].index('节')]))
        #print(str(course_bucket))
        return course_bucket
        
    ####获得所有课程的信息
    #   将取到的原始数据保存到 all_courses_cache所指向的文件中
    #   由于每年的课程信息会变，用来更新数据        
    #
    def updateAllCoursesInfo(self):
        allCoursesInfoUrl = self.baseUrl + '/gsmis/xw/kcbQueryAction.do'
        data = {
            'zdnf':target.year,
            'kkjj':target.kkjj,
            'jiaoshi_id': '',
            'kkyx': ''       
        }
        resp = self.session.get(url=allCoursesInfoUrl, data=data, headers = self.headers)
        fout = open(self.all_courses_cache, 'w')
        fout.write(resp)
        fout.close()
        
    ## 从all_courses_cache中读取原始数据并分解，得到包含所有课程信息的dict
    # course_database (dict) 的结构
        # key是课程名，方便查找， 因为会有课程在不同周安排的上课时间不同，
        # 造成一个课程名对应的信息有多条，所以value是一个列表
    # {name : (索引，方便查找)， 
    #   [{
    #    name: _name, (课程名称)
    #    period: _period (e.g. ？周-？周)
    #    classes: ( e.g. ?节-?节)
    #    room: (e.g. M201)
    #    },...] #这里是个列表，需要注意
    #
    #
    def generateCourseDataBase(self):
        with open(self.all_courses_cache, "r") as f:
            content = f.read()
        soup = BeautifulSoup(content, "lxml")
        table = soup.select("table#Table6")[0]
        trs = table.select("tr")
        courses_data = dict()
        n = 0
        for i in range(1, len(trs)):
            tr = trs[i]
            tds = tr.find_all("td")
            day_courses = self.__wrapTheCourseData(tds, courses_data)
            n += len(day_courses)
        print(len(courses_data), n)
        return courses_data
        
    # 周天转换，方便后续代码编写
    def __dayTransform(self, day):
        if '星期一' == day:
            return 1
        elif '星期二' == day:
            return 2
        elif '星期三' == day:
            return 3
        elif '星期四' == day:
            return 4
        elif '星期五' == day:
            return 5         
        elif '星期六' == day:
            return 6         
        else:
            return 7         
##
# 对all_courses_file中表格每个tr数据拆分生成课程信息
# 组织成course_db需要的结构
    def __wrapTheCourseData(self, tds, res):
        raw = tds[1].contents
        print("courses count a day :",int(len(raw)/2))
        day = self.__dayTransform(tds[0].contents[0])
        for i in range(0, len(raw), 2):
            # course data        
            data = raw[i]
            right_bookmark_idx = data.index('》')
            course_name = data[1:right_bookmark_idx]
            zhou_pos = data.rindex('周')
            course_period = data[right_bookmark_idx+1: zhou_pos+1]
            course_classes = data[zhou_pos + 1 : data.index(' ')]
            course_room = data[data.index(' '):]
            if course_name in res :
                list_wrap = res[course_name]
            else:
                list_wrap = list() 
            dict_data = dict()
            dict_data['name'] = course_name
            dict_data['day'] = day
            dict_data['period'] = course_period
            dict_data['classes'] = course_classes
            dict_data['room'] = course_room
            list_wrap.append(dict_data)
            res[course_name] = list_wrap
        return res
##
# 为了方便课程表输出，bucket采用了不同于course_db的组织方式:
        #如下：
        #{day:[课程信息]}
        #day表示周几，value表示对应的课程列表，
    def __addCourseToBucket(self, bucket, course_data): 
        for data in course_data:  # data is course-data
            day = data['day']
            day_lst = dict()
            if day in bucket:
                day_lst = bucket[day]
            cls_lst = list()
            if data['classes'] in day_lst:
                cls_lst = day_lst[data['classes']]
            cls_lst.append(data)
            day_lst[data['classes']] = cls_lst
            bucket[day] = day_lst
            
    def generateCourseScheduleData(self):
        course_db = self.generateCourseDataBase()
        with open("table.html","r") as wt:    
            content = wt.read()
        soup = BeautifulSoup(content, 'lxml')
        target = soup.find("table")
        trs = target.find_all("tr")
        course_bucket = dict()
        for i in range(1, len(trs) - 1):
            tr = trs[i]
            if len(tr) > 5: # 去掉无效行
                tds = tr.find_all("td")
                course_num = tds[1].string.strip()
                course_name = tds[2].string.strip()
                minus_idx = course_name.index('-')
                if '班' in course_name != -1:
                    course_name = course_name[:minus_idx]+course_name[minus_idx+1:]
                else:
                    course_name = course_name[:minus_idx]
                print("课程号",course_num,"-名称", course_name)
                # 按照 周几-上课时间-课程信息 来组织数据
                self.__addCourseToBucket(course_bucket, course_db[course_name])
        
        for i in course_bucket:
          dictionary = course_bucket[i]
          course_bucket[i] = sorted(dictionary.items(), key = lambda k: int(k[0][:k[0].index('节')]))
        #print(str(course_bucket))
        return course_bucket
    ##
    # 将bucket中的信息输出成html表格            
    def getHtmlFormatSchedule(self):
        course_bucket = self.generateCourseScheduleData()
        print(str(course_bucket))
        htm_res = open(config.target, "w")
        htm_res.write("<table border='1'>")
        htm_res.write("<tr>")
        htm_res.write('<tr style="font-size:8pt;"><td>星期｜节次</td><td align="Center">第一节</td><td align="Center">第二节</td><td align="Center">第三节</td><td align="Center">第四节</td><td align="Center">第五节</td><td>第六节</td><td align="Center">第七节</td><td align="Center">第八节</td><td align="Center">第九节</td><td align="Center">第十节</td><td align="Center">第十一节</td><td align="Center">第十二节</td></tr>')
        htm_res.write("</tr>")
        for i in course_bucket:
            htm_res.write('<td>'+ str(i) +'</td>')
            day_list = course_bucket[i] # day_list is a list which contains several tuples
            cur = 1
            for tp in day_list: 
                cls_str = tp[0]
                beg = int(cls_str[:cls_str.index('节')])
                end = int(cls_str[cls_str.index('-') + 1 : cls_str.rindex('节')])
                print(beg, end)
                while cur < beg:
                    htm_res.write('<td></td>')
                    cur += 1
                htm_res.write('<td colspan=' + str(end - beg + 1) + '>')
                for c in tp[1]:
                    htm_res.write('《' + c['name'] + '》<br>' + c['period'] + '<br>' + c['room'] + '<br>')
                htm_res.write('</td>')
                cur = end+1;
            while cur <= 12:
                htm_res.write('<td></td>')
                cur += 1
            htm_res.write('</tr>')
        htm_res.write("</table>")
        htm_res.close()
        
def main():
    crawler = Crawler()
    crawler.updateAllCoursesInfo()
    crawler.getHtmlFormatSchedule()

if __name__ == "__main__":
    main()
