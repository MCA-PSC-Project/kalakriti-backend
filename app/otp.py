import pyotp

# generating random PyOTP secret keys
key = pyotp.random_base32()
print(key)

# generating TOTP codes with provided secret
# totp = pyotp.TOTP("base32secret3232")
totp = pyotp.TOTP(key)
generated_totp = totp.now()
print(generated_totp)
# verifying TOTP codes with PyOTP
print(totp.verify("492039"))
print(totp.verify(generated_totp))
