import base64
import io
import re
from secrets import token_hex
from typing import Tuple, Union
from urllib.parse import quote

import requests
from PIL import Image
from pytesseract import image_to_string, pytesseract
from requests.cookies import RequestsCookieJar

from encode import encode_password, get_loginUserToken

tesseract_cmd_path = r'D:\Programs\Tesseract-OCR\tesseract.exe'


def _get_headers():
    return {
        'X-Requested-With': 'XMLHttpRequest',
        'loginUserToken': get_loginUserToken(),
        'loginToken': 'loginToken',
        'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
        'Host': 'cas.gnnu.edu.cn',
        'Connection': 'keep-alive',
    }


def try_login(student_id: int, password: str, CAPTCHA: str, uid: str, service: str = "") -> Tuple[Union[str, int], str]:
    response = requests.post(
        "https://cas.gnnu.edu.cn/lyuapServer/v1/tickets",
        data={
            "username": student_id,
            "password": encode_password(password),
            "service": quote(service),
            "code": CAPTCHA,
            "id": uid,
            "loginType": "",
            "otpcode": "",
        },
        headers=_get_headers()
    )
    data = response.json()
    try:
        success = data["meta"]["success"]
        if not success:
            return data["meta"]["statusCode"], data["meta"]["message"]
        return data["data"]["code"], data["data"]["code"]
    except KeyError:
        return data["tgt"], data["ticket"]


def recognize_captcha(img: str) -> str:
    image_data = base64.b64decode(img)
    pytesseract.tesseract_cmd = tesseract_cmd_path
    captcha = image_to_string(Image.open(io.BytesIO(image_data)).convert('L').point(lambda i: 0 if i < 200 else 255))
    return captcha


def get_captcha() -> Tuple[str, str]:
    uid = token_hex(16)
    response = requests.get(f"https://cas.gnnu.edu.cn/lyuapServer/kaptcha?id={uid}", headers=_get_headers())

    data = response.json()
    base64_data = re.sub('^data:image/.+;base64,', '', data['content'])
    missing_padding = len(base64_data) % 4
    if missing_padding != 0:
        base64_data += '=' * (4 - missing_padding)
    captcha = recognize_captcha(base64_data)
    return data["uid"], "".join(captcha.split())[:4]


def login(student_id: int, password: str, service: str = "") -> Tuple[Union[str, int], str]:
    uid, captcha = get_captcha()
    res = try_login(student_id, password, captcha, uid, service)
    if res == ("CODEFALSE", "CODEFALSE"):
        return login(student_id, password, service)
    return res


def get_cookies(ticket: str, CASTGC: str) -> RequestsCookieJar:
    verify_url = f"https://jwgl.gnnu.edu.cn/sso/lyiotlogin?ticket={ticket}"
    response = requests.get(verify_url, allow_redirects=False)
    cookies = response.cookies
    cookies.set(
        'CASTGC', CASTGC,
        domain='cas.gnnu.edu.cn',
        path='/',
    )
    return cookies
