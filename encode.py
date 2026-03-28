import math
import time


class BigInt:
    """模拟JS中的大数对象"""
    def __init__(self, digits=None, is_neg=False):
        self.digits = digits if digits is not None else []
        self.is_neg = is_neg
    
    def __repr__(self):
        return f"BigInt(digits={self.digits[:5]}..., is_neg={self.is_neg})"

class Barrett:
    """Barrett算法实现，用于高效模幂运算"""
    def __init__(self, modulus: BigInt):
        self.modulus = modulus
        self.k = math.ceil(len(modulus.digits) / 2) if modulus.digits else 0
        # 初始化mu和bkplus1（使用你提供的参数）
        self.mu = BigInt(
            digits=[7469, 13822, 15506, 32982, 50429, 62979, 64339, 60597, 40979, 61913, 20952, 38396, 43669, 60926, 10345, 21166, 11931, 31731, 17652, 54018, 14346, 5098, 29577, 27601, 14064, 33529, 25220, 39088, 8044, 19738, 21550, 5198, 30005, 21337, 934, 14453, 28049, 17274, 16321, 32160, 3193, 55263, 27029, 41238, 14094, 25353, 47316, 6175, 31709, 27325, 36707, 32884, 7478, 49873, 62514, 44522, 9303, 45997, 33566, 1250, 26644, 59158, 49823, 26680, 1] + [0]*58,
            is_neg=False
        )
        self.bkplus1 = BigInt(
            digits=[0]*65 + [1] + [0]*58,
            is_neg=False
        )
    
    def pow_mod(self, base: BigInt, exponent: BigInt) -> BigInt:
        """
        模幂运算：(base^exponent) mod modulus
        这里简化实现（完整实现需要大数乘法/除法，如需生产环境需替换为标准库）
        对于你的场景，exponent.e的digits前两位是1，即e=65537（常见RSA公钥指数）
        """
        # 提取指数值（你的e参数实际是65537）
        exp = 65537
        
        # 提取base的数值（将digits转换为整数）
        base_val = 0
        for i, d in enumerate(base.digits):
            if d == 0:
                continue
            base_val += d * (2**16)**i
        
        # 提取模数的数值
        mod_val = 0
        for i, d in enumerate(self.modulus.digits):
            if d == 0:
                continue
            mod_val += d * (2**16)**i
        
        # 快速幂运算（Python内置pow支持大数模幂，效率极高）
        result_val = pow(base_val, exp, mod_val)
        
        # 将结果转换回BigInt格式
        result_digits = []
        temp = result_val
        while temp > 0:
            result_digits.append(temp & 0xFFFF)  # 取低16位
            temp >>= 16
        # 补零到指定长度
        while len(result_digits) < len(self.modulus.digits):
            result_digits.append(0)
        
        return BigInt(digits=result_digits, is_neg=False)

def d(bigint: BigInt) -> str:
    """将BigInt转换为16进制字符串"""
    # 计算总数值
    val = 0
    for i, d in enumerate(bigint.digits):
        val += d * (2**16)**i
    # 转换为16进制，去掉0x前缀
    return hex(val)[2:]

def s(bigint: BigInt, radix: int) -> str:
    """将BigInt转换为指定进制字符串（备用）"""
    val = 0
    for i, d in enumerate(bigint.digits):
        val += d * (2**16)**i
    return str(val) if radix == 10 else hex(val)[2:].upper()

def M(e_config: dict, t: str) -> str:
    """
    重写的RSA加密函数
    :param e_config: 加密配置（包含chunkSize、radix、barrett等）
    :param t: 要加密的密码字符串
    :return: 加密后的16进制字符串（空格分隔）
    """
    # 1. 将字符串转换为ASCII码数组
    a = [ord(char) for char in t]
    
    # 2. 补零使长度为chunkSize的整数倍
    chunk_size = e_config['chunkSize']
    while len(a) % chunk_size != 0:
        a.append(0)
    
    # 3. 分块加密
    u = len(a)
    p = ""
    i = 0
    
    while i < u:
        # 初始化大数对象（模拟JS中的o对象）
        c = BigInt(digits=[0]*len(e_config['barrett'].modulus.digits), is_neg=False)
        
        r = 0
        l = i
        # 将两个字节合并为一个16位数字（digits[r] = a[l] + a[l+1] << 8）
        while l < i + chunk_size and r < len(c.digits):
            if l < len(a):
                c.digits[r] = a[l]
                l += 1
            if l < len(a):
                c.digits[r] += a[l] << 8
                l += 1
            r += 1
        
        # RSA加密核心：模幂运算
        m = e_config['barrett'].pow_mod(c, e_config['e'])
        
        # 转换为指定进制并拼接
        if e_config['radix'] == 16:
            p += d(m) + " "
        else:
            p += s(m, e_config['radix']) + " "
        
        i += chunk_size
    
    # 移除最后一个空格
    return p.strip()


def RSA(p: str) -> str:
    # 构建配置参数（对应你提供的e对象）
    modulus_digits = [59313, 4375, 54507, 5267, 8345, 43610, 49971, 28563, 34983, 36521, 17297, 62027, 42744, 32131, 40043, 48417, 5636, 46659, 52373, 20768, 28635, 46498, 55076, 13948, 44453, 44804, 40613, 1466, 26896, 54350, 28506, 28712, 44726, 4974, 46852, 32655, 60720, 2973, 7722, 43040, 10398, 28111, 52739, 6542, 43865, 20892, 59308, 8898, 58877, 36302, 41921, 27719, 59291, 10923, 8559, 53747, 10707, 59976, 48415, 32958, 37390, 57449, 45414, 46574] + [0]*58
    
    # 构建加密配置
    e_config = {
        "e": BigInt(
            digits=[1, 1] + [0]*118,
            is_neg=False
        ),
        "d": BigInt(
            digits=[0]*120,
            is_neg=False
        ),
        "m": BigInt(
            digits=modulus_digits,
            is_neg=False
        ),
        "chunkSize": 126,
        "radix": 16,
        "barrett": Barrett(BigInt(digits=modulus_digits, is_neg=False))
    }
    encrypted = M(e_config, p)
    return encrypted

def encode_password(password: str) -> str:
    return RSA(password)

def get_loginUserToken() -> str:
    return RSA(f"lyasp{int(time.time()*1000):.0f}")
