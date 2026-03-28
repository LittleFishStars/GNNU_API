import re
import base64
from typing import Tuple, Union
import requests
import io
from secrets import token_hex
from urllib.parse import quote
from pytesseract import image_to_string, pytesseract
from PIL import Image
from requests.cookies import RequestsCookieJar

from encode import encode_password, get_loginUserToken


def _get_headers():
    return {
        'X-Requested-With': 'XMLHttpRequest',
        'loginUserToken': get_loginUserToken(),
        'loginToken': 'loginToken',
        'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
        'Host': 'cas.gnnu.edu.cn',
        'Connection': 'keep-alive',
    }


def get_login(student_id: int, password: str, CAPTCHA: str, uid: str, service: str = "") -> Tuple[Union[str, int], str]:
    url = "https://cas.gnnu.edu.cn/lyuapServer/v1/tickets"
    params = {
        "username": student_id,
        "password": encode_password(password),
        "service": quote(service),
        "code": CAPTCHA,
        "id": uid,
        "loginType": "",
        "otpcode": "",
    }
    response = requests.post(url, data=params, headers=_get_headers())
    data = response.json()
    try:
        success = data["meta"]["success"]
        if not success:
            return data["meta"]["statusCode"], data["meta"]["message"]
        return data["data"]["code"], data["data"]["code"]
    except KeyError:
        return data["tgt"], data["ticket"]


def get_CAPTCHA() -> Tuple[str, str]:
    uid = token_hex(16)
    response = requests.get(f"https://cas.gnnu.edu.cn/lyuapServer/kaptcha?id={uid}", headers=_get_headers())

    data = response.json()
    base64_data = re.sub('^data:image/.+;base64,', '', data['content'])
    missing_padding = len(base64_data) % 4
    if missing_padding != 0:
        base64_data += '=' * (4 - missing_padding)
    image_data = base64.b64decode(base64_data)
    pytesseract.tesseract_cmd = r'D:\Programs\Tesseract-OCR\tesseract.exe'
    CAPTCHA = image_to_string(Image.open(io.BytesIO(image_data)).convert('L').point(lambda i: 0 if i < 200 else 255))
    return data["uid"], "".join(CAPTCHA.split())[:4]


def login(student_id: int, password: str, service: str = "") -> Tuple[Union[str, int], str]:
    uid, CAPTCHA = get_CAPTCHA()
    res = get_login(student_id, password, CAPTCHA, uid, service)
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
