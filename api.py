from secrets import token_hex
from typing import Literal, Any
from urllib.parse import urlparse

import requests
from lxml import html

import login


def login_verify(student_id: int, password: str, service: str = '') -> tuple[bool, Any]:
    """
    登陆验证
    调用统一验证平台的接口进行登陆验证

    :param student_id: 学号
    :param password: 登陆密码
    :param service: 访问的服务

	:return (是否成功, 返回结果)
    """
    res = login.login(student_id, password, service)
    return res[0] != res[1] and type(res[0]) == str, res


class Captcha:
    """统一验证平台的验证码api"""

    def __init__(self):
        self.uid = token_hex(16)
        response = requests.get(f'https://cas.gnnu.edu.cn/lyuapServer/kaptcha?id={self.uid}')
        data = response.json()
        self._img = data['content']
        self.time = data['timeout']

    @property
    def img(self):
        """返回验证码图片的base64"""
        return self._img

    def verify(self, captcha: str) -> bool:
        """验证输入的验证码是否正确"""
        res = login.try_login(0, '', captcha, self.uid)
        return res != ('CODEFALSE', 'CODEFALSE')


class Student:
    """所有学生相关的数据"""

    def __init__(self, student_id: int, password: str):
        self._student_id = student_id
        while True:
            is_ok, res = login_verify(student_id, password, 'https://jwgl.gnnu.edu.cn/')
            if not is_ok:
                raise ValueError(res[1])

            CASTGC, ticket = res
            self._cookie = login.get_cookies(ticket, CASTGC)
            response = requests.get('https://jwgl.gnnu.edu.cn/sso/lyiotlogin',
                                    cookies=self._cookie,
                                    allow_redirects=False)
            if urlparse(response.headers.get('Location')).netloc == 'jwgl.gnnu.edu.cn':
                break
        c = requests.get(response.headers.get('Location'), cookies=self._cookie, allow_redirects=False).cookies
        self._cookie.clear('jwgl.gnnu.edu.cn', '/sso', 'JSESSIONID')
        self._cookie.update(c)
        self._info = {}

    def _get_basic_info(self):
        response = requests.get(
            'https://jwgl.gnnu.edu.cn/xtgl/index_cxYhxxIndex.html?xt=jw&localeKey=zh_CN',
            cookies=self._cookie,
        )
        tree = html.fromstring(response.content.decode('utf-8'))
        self._info['name'], self._info['identity'] = tuple(tree.xpath('//h4/text()')[0].split('\xa0\xa0'))
        self._info['college'], self._info['class'] = tuple(tree.xpath('//p/text()')[0].split(' '))
        self._info['avatar'] = 'https://jwgl.gnnu.edu.cn' + tree.xpath('//img/@src')[0]

    def _get_student_info(self):
        response = requests.get(
            'https://jwgl.gnnu.edu.cn/xsxxxggl/xsgrxxwh_cxXsgrxx.html',
            params={
                'gnmkdm': 'N100801',
                'layout': 'default',
            },
            cookies=self._cookie,
        )
        tree = html.fromstring(response.content.decode('utf-8'))
        self.set_name(tree.xpath('//*[@id="col_xm"]/p/text()')[0].strip())
        self.set_gender(tree.xpath('//*[@id="col_xbm"]/p/text()')[0].strip())
        self.set_document({
            'type': tree.xpath('//*[@id="col_zjlxm"]/p/text()')[0].strip(),
            'id': tree.xpath('//*[@id="col_zjhm"]/p/text()')[0].strip(),
        })
        self.set_birthday(tree.xpath('//*[@id="col_csrq"]/p/text()')[0].strip())
        self.set_people(tree.xpath('//*[@id="col_mzm"]/p/text()')[0].strip())
        self.set_political_status(tree.xpath('//*[@id="col_zzmmm"]/p/text()')[0].strip())
        self.set_college(tree.xpath('//*[@id="col_jg_id"]/p/text()')[0].strip())
        self.set_major(tree.xpath('//*[@id="col_zyh_id"]/p/text()')[0].strip()[:-6])
        self.set_class(tree.xpath('//*[@id="col_bh_id"]/p/text()')[0].strip())
        self.set_address(tree.xpath('//*[@id="col_txdz"]/p/text()')[0].strip())
        self.set_enrollment_year(tree.xpath('//*[@id="col_zsnddm"]/p/text()')[0].strip()[:4])

    @property  # 学号
    def student_id(self) -> str:
        return str(self._student_id)

    @property  # 姓名
    def name(self) -> str:
        if 'name' in self._info:
            return self._info['name']
        self._get_basic_info()
        return self._info['name']

    def set_name(self, name: str) -> str:
        self._info['name'] = name
        return name

    @property  # 身份
    def identity(self) -> str:
        if 'identity' in self._info:
            return self._info['identity']
        self._get_basic_info()
        return self._info['identity']

    def set_identity(self, identity: str) -> str:
        self._info['identity'] = identity
        return identity

    @property  # 学院
    def college(self) -> str:
        if 'college' in self._info:
            return self._info['college']
        self._get_basic_info()
        return self._info['college']

    def set_college(self, college: str) -> str:
        self._info['college'] = college
        return college

    @property  # 班级
    def class_(self) -> str:
        if 'class' in self._info:
            return self._info['class']
        self._get_basic_info()
        return self._info['class']

    def set_class(self, class_: str) -> str:
        self._info['class'] = class_
        return class_

    @property  # 照片
    def avatar(self) -> str:
        if 'avatar' in self._info:
            return self._info['avatar']
        self._get_basic_info()
        return self._info['avatar']

    def set_avatar(self, avatar: str) -> str:
        self._info['avatar'] = avatar
        return avatar

    @property  # 辅导员
    def instructor(self) -> str:
        if 'instructor' in self._info:
            return self._info['instructor']
        self.get_class_schedule(int(self.enrollment_year), 1)
        return self._info['instructor']

    def set_instructor(self, instructor: str) -> str:
        self._info['instructor'] = instructor
        return instructor

    @property  # 专业
    def major(self) -> str:
        if 'major' in self._info:
            return self._info['major']
        self._get_student_info()
        return self._info['major']

    def set_major(self, major: str) -> str:
        self._info['major'] = major
        return major

    @property  # 性别
    def gender(self) -> str:
        if 'gender' in self._info:
            return self._info['gender']
        self._get_student_info()
        return self._info['gender']

    def set_gender(self, gender: str) -> str:
        self._info['gender'] = gender
        return gender

    @property  # 证件
    def document(self) -> str:
        if 'document' in self._info:
            return self._info['document']
        self._get_student_info()
        return self._info['document']

    def set_document(self, document: dict[str, str]) -> dict[str, str]:
        self._info['document'] = document
        return document

    @property  # 出生日期
    def birthday(self) -> str:
        if 'birthday' in self._info:
            return self._info['birthday']
        self._get_student_info()
        return self._info['birthday']

    def set_birthday(self, birthday: str) -> str:
        self._info['birthday'] = birthday
        return birthday

    @property  # 民族
    def people(self) -> str:
        if 'people' in self._info:
            return self._info['people']
        self._get_student_info()
        return self._info['people']

    def set_people(self, people: str) -> str:
        self._info['people'] = people
        return people

    @property  # 政治面貌
    def political_status(self) -> str:
        if 'political_status' in self._info:
            return self._info['political_status']
        self._get_student_info()
        return self._info['political_status']

    def set_political_status(self, political_status: str) -> str:
        self._info['political_status'] = political_status
        return political_status

    @property  # 联系地址
    def address(self) -> str:
        if 'address' in self._info:
            return self._info['address']
        self._get_student_info()
        return self._info['address']

    def set_address(self, address: str) -> str:
        self._info['address'] = address
        return address

    @property  # 入学年份
    def enrollment_year(self) -> str:
        if 'enrollment_year' in self._info:
            return self._info['enrollment_year']
        self._get_student_info()
        return self._info['enrollment_year']

    def set_enrollment_year(self, enrollment_year: str) -> str:
        self._info['enrollment_year'] = enrollment_year
        return enrollment_year

    @property  # 课表
    def class_schedule(self) -> dict[str, dict[Literal[1, 2], dict[str, list[dict[str, Any]]]]]:
        if 'class_schedule' in self._info:
            return self._info['class_schedule']
        self._get_class_schedule(2026, 2)
        return self._info['class_schedule']

    def get_class_schedule(self, year: int, term: int, week: int = 0):
        """
        获取课表

        :param year: 学年
        :param term: 学期（1或2）
        :param week: 周（为0返回整学期课表）
        """
        if 'class_schedule' in self._info:
            if year in self._info['class_schedule'] and term in self._info['class_schedule'][year]:
                return self._info['class_schedule'][year][term]
        response = requests.post(
            f'https://jwgl.gnnu.edu.cn/kbcx/{'xskbcx_cxXsgrkb' if week == 0 else 'xskbcxMobile_cxXsKb'}.html',
            params={
                'gnmkdm': 'N2151' if week == 0 else 'N2154',
            },
            cookies=self._cookie,
            data={
                'xnm': year,
                'xqm': 3 if term == 1 else 12,
                'kzlx': 'ck',
                'xsdm': '',
                'kclbdm': '',
            } if week == 0 else {
                'xnm': year,
                'xqm': 3 if term == 1 else 12,
                'zs': week,
                'doType': 'app',
                'kblx': 1,
                'xh': '',
            }
        )
        json = response.json()
        return self.set_class_schedule(year, term, self.parse_class_schedule(json))

    def set_class_schedule(self, year: int, term: int, data: dict[str, list[dict[str, Any]]]):
        """设置课表"""
        if 'class_schedule' not in self._info:
            self._info['class_schedule'] = {}
        if year not in self._info['class_schedule']:
            self._info['class_schedule'][year] = {}
        self._info['class_schedule'][year][term] = data
        return data

    def parse_class_schedule(self, json: dict) -> dict[str, list[dict[str, Any]]]:
        """解析课表"""
        self.set_name(json['xsxx']['XM'])
        self.set_college(json['xsxx']['ZYMC'])
        self.set_class(json['xsxx']['BJMC'])
        self.set_instructor(json['xsxx']['JSXM'])
        classes: list[dict] = json['kbList']

        def parse_class(class_: dict):
            return {
                'name': class_['kcmc'],
                'position': class_['cdmc'],
                'teacher': class_['xm'].split(','),
                'time': {
                    'week': class_['zcd'],
                    'day': class_['xqjmc'],
                    'time': tuple(map(int, class_['jcs'].split('-'))),
                },
                'class': class_['jxbzc'].split(';'),
                'build': class_['lh'],
                'nature': class_['kcxz'],
                'type': class_['kclb'],
                'exam': class_['khfsmc'],
                'campus': class_['xqmc'],
                'credit': float(class_['xf']),
            }

        res = {}
        for class_ in map(parse_class, classes):
            class_name = class_['name']
            del class_['name']
            if class_name not in res:
                res[class_name] = [class_]
            else:
                res[class_name].append(class_)
        return res

    def get_timetable(self, year: int, term: int) -> list[dict[str, str]]:
        """获取时间表"""
        if 'timetable' in self._info:
            return self._info['timetable']
        response = requests.post(
            'https://jwgl.gnnu.edu.cn/kbcx/xskbcx_cxRjc.html',
            params={'gnmkdm': 'N2151'},
            data={
                'xnm': year,
                'xqm': 3 if term == 1 else 12,
                'xqh_id': 1,
            },
            cookies=self._cookie,
        )
        return list(map(lambda x: {'start': x['qssj'], 'end': x['jssj']}, response.json()))

    def get_course(self, year: int, term: int, class_name: str) -> list[dict[str, Any]]:
        """获取课程信息"""
        class_schedule = self.get_class_schedule(year, term)
        if class_name not in class_schedule:
            return []
        return class_schedule[class_name]

    @property
    def this_week(self) -> int:
        """获取当前周"""
        if 'this_week' in self._info:
            return self._info['this_week']
        response = requests.get(
            'https://jwgl.gnnu.edu.cn/kbcx/xskbcxZccx_cxXskbcxIndex.html',
            params={'gnmkdm': 'N2154', 'layout': 'default'},
            cookies=self._cookie,
        )
        tree = html.fromstring(response.text)
        this_week = int(tree.xpath('//*[@id="zs"]/option[@selected="selected"]/text()')[0].split('(')[0])
        self.set_this_week(this_week)
        return self._info['this_week']

    def set_this_week(self, this_week: int) -> int:
        self._info['this_week'] = this_week
        return this_week

    def get_all_info(self) -> dict[str, str]:
        return {
            'student_id': self.student_id,
            'name': self.name,
            'identity': self.identity,
            'college': self.college,
            'class': self.class_,
            'avatar': self.avatar,
            'instructor': self.instructor,
            'major': self.major,
            'gender': self.gender,
            'document': self.document,
            'birthday': self.birthday,
            'people': self.people,
            'political_status': self.political_status,
            'address': self.address,
            'enrollment_year': self.enrollment_year,
        }
