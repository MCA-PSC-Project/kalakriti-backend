from datetime import datetime, timedelta
from flask_restful import Resource
from flask import abort, current_app as app, request
import psycopg2
import app.app_globals as app_globals
import app.otp as otp

class GetMobileOtp(Resource):
    def post(self):
        data = request.get_json()
        mobile_no = data.get("mobile_no", None)
        if not mobile_no:
            abort(400, 'Bad Request')
            
        generated_motp=otp.generate_motp()
        app.logger.debug("generated otp= %s", generated_motp)
        now_plus_10_mins = datetime.now() + timedelta(minutes = 10)
        
        UPSERT_MOBILE_OTP = '''INSERT INTO mobile_otp(mobile_no, otp, expiry_at)
        VALUES(%s, %s, %s)
        ON CONFLICT (mobile_no)
        DO UPDATE set otp = %s, expiry_at = %s'''
        try:
            cursor = app_globals.get_cursor()
            cursor.execute(UPSERT_MOBILE_OTP, (mobile_no, generated_motp, now_plus_10_mins,
                                            generated_motp, now_plus_10_mins,))
        except (Exception, psycopg2.Error) as err:
            app.logger.debug(err)
            abort(400, 'Bad Request')
        finally:
            cursor.close()
        return 'Otp has been sent successfully', 200
        
class MobileOtpLogin(Resource):
    def post(self):
        pass