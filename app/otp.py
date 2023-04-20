import math
import random
import string
from time import sleep
import pyotp
import qrcode


def generate_alpha_numeric_otp(otp_length=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=otp_length))


def generate_motp(otp_length=6):
    digits = "0123456789"
    otp = ""
    for i in range(otp_length):
        otp += digits[math.floor(random.random() * 10)]
    return otp


def generate_totp_secret_key():
    # generate random PyOTP secret key
    key = pyotp.random_base32()
    # print(key)
    return key


def generate_totp_key_with_uri(name, issuer_name):
    # generate random PyOTP secret key
    totp_secret_key = pyotp.random_base32()
    # print(key)
    provisioning_uri = pyotp.totp.TOTP(totp_secret_key).provisioning_uri(
        name=name, issuer_name=issuer_name
    )
    # print(provisioning_uri)
    return totp_secret_key, provisioning_uri


def generate_totp(key):
    # generating TOTP codes with provided secret
    # totp = pyotp.TOTP("base32secretkey")
    totp = pyotp.TOTP(key, interval=30)
    return totp.now()


def verify_totp(otp_secret_key, user_provided_key):
    # verifying TOTP codes with PyOTP
    # print(totp.verify("492039"))
    totp = pyotp.TOTP(otp_secret_key, interval=30)
    return totp.verify(user_provided_key)


def generate_qr_code(text, path):
    qrcode.make(text).save(path)


if __name__ == "__main__":
    totp_secret_key = generate_totp_secret_key()
    print(totp_secret_key)
    generated_totp = generate_totp(totp_secret_key)
    print(generated_totp)
    sleep(35)
    # is_verified = verify_totp(totp_secret_key, "123456")
    is_verified = verify_totp(totp_secret_key, generated_totp)
    print(is_verified)
    provisioning_uri = pyotp.totp.TOTP(totp_secret_key).provisioning_uri(
        name="customer", issuer_name="Kalakriti"
    )
    print(provisioning_uri)
    generate_qr_code(provisioning_uri, "sample.png")
