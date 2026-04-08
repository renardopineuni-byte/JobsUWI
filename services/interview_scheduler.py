from extensions import db
from models.interview_slot import InterviewSlot
from models.user import User
from datetime import datetime

class InterviewScheduler:
    
    @staticmethod
    def generateConfirmationCode(candidate_name, interviewer_name, start_time, slot_id):
        base = f"{candidate_name}{interviewer_name}{start_time}{slot_id}"
        return f"CONF-{abs(hash(base)) % 100000:05d}"
        
    @staticmethod
    def getAvailableSlots():
        return InterviewSlot.query.filter_by(reserved=False).order_by(InterviewSlot.start).all()
        
    @staticmethod
    def bookSlot(student_user, slot_id):
        slot = InterviewSlot.query.get(slot_id)
        if not slot or slot.reserved:
            return False, "That slot is no longer available.", None
            
        slot.reserved = True
        slot.student_id = student_user.id
        db.session.flush()
        
        slot.confirmationCode = InterviewScheduler.generateConfirmationCode(
            student_user.username, slot.interviewer.username, slot.start, slot.id
        )
        db.session.commit()
        return True, "Slot successfully booked.", slot

    @staticmethod
    def getStudentBookings(user_id):
        return InterviewSlot.query.filter_by(student_id=user_id, reserved=True).order_by(InterviewSlot.start).all()
        
    @staticmethod
    def getStaffBookings(staff_id):
        return InterviewSlot.query.filter_by(staff_id=staff_id, reserved=True).order_by(InterviewSlot.start).all()
        
    @staticmethod
    def addSlot(staff_id, start_time, duration):
        slot = InterviewSlot(staff_id=staff_id, start=start_time, duration=duration)
        db.session.add(slot)
        db.session.commit()
        return slot

    @staticmethod
    def cancelInterview(slot_id, student_id):
        slot = InterviewSlot.query.get_or_404(slot_id)
        if slot.student_id != student_id:
            return False
        slot.reserved = False
        slot.student_id = None
        slot.confirmationCode = None
        db.session.commit()
        return True
