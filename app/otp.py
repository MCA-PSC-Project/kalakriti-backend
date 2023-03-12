from time import sleep
import pyotp


def generate_totp_secret_key():
    # generate random PyOTP secret key
    key = pyotp.random_base32()
    # print(key)
    return key

def generate_totp(key):
    # generating TOTP codes with provided secret
    # totp = pyotp.TOTP("base32secretkey")
    totp = pyotp.TOTP(key)
    return totp.now()


def verify_totp(otp_secret_key, user_provided_key):
    # verifying TOTP codes with PyOTP
    # print(totp.verify("492039"))
    totp = pyotp.TOTP(otp_secret_key)
    return totp.verify(user_provided_key)


totp_secret_key = generate_totp_secret_key()
print(totp_secret_key)
generated_totp = generate_totp(totp_secret_key)
print(generated_totp)
sleep(5)
is_verified = verify_totp(totp_secret_key, generated_totp)
print(is_verified)
