import random
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.models import OTP, User

class OTPService:
    @staticmethod
    def generate_otp() -> str:
        return str(random.randint(100000, 999999))

    @staticmethod
    def send_otp(phone_number: str, code: str):
        # TODO: Integrate Twilio, SNS, or MSG91 here
        print(f"========================================")
        print(f" [SMS MOCK] To: {phone_number} | Code: {code}")
        print(f"========================================")
        return True

    @staticmethod
    def create_and_send(session: Session, phone_number: str):
        # 1. Generate
        code = OTPService.generate_otp()
        expires = datetime.utcnow() + timedelta(minutes=10)
        
        # 2. Save to DB
        otp_entry = OTP(phone_number=phone_number, code=code, expires_at=expires)
        session.add(otp_entry)
        session.commit()
        
        # 3. Send
        OTPService.send_otp(phone_number, code)
        return True

    @staticmethod
    def verify_otp(session: Session, phone_number: str, code: str) -> bool:
        # Find valid, unused OTP
        statement = select(OTP).where(
            OTP.phone_number == phone_number,
            OTP.code == code,
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        )
        otp_entry = session.exec(statement).first()
        
        if otp_entry:
            otp_entry.is_used = True
            session.add(otp_entry)
            session.commit()
            return True
        return False