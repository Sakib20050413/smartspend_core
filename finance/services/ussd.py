from django.core.cache import cache
import uuid

class USSDSessionManager:
    """
    Manages USSD session state using Redis.
    SEC-5: Session expiry, strict state management for USSD interactions.
    """
    TIMEOUT_SECONDS = 120 # 2 minutes expiry for USSD sessions

    @staticmethod
    def _get_key(session_id: str) -> str:
        return f"ussd_session_{session_id}"

    @classmethod
    def create_session(cls, msisdn: str) -> dict:
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "msisdn": msisdn,
            "state": "MAIN_MENU",
            "data": {}
        }
        cache.set(cls._get_key(session_id), session_data, timeout=cls.TIMEOUT_SECONDS)
        return session_data

    @classmethod
    def get_session(cls, session_id: str) -> dict:
        return cache.get(cls._get_key(session_id))

    @classmethod
    def update_session(cls, session_id: str, new_state: str, extra_data: dict = None):
        session_data = cls.get_session(session_id)
        if not session_data:
            raise ValueError("Session expired or invalid")
            
        session_data["state"] = new_state
        if extra_data:
            session_data["data"].update(extra_data)
            
        cache.set(cls._get_key(session_id), session_data, timeout=cls.TIMEOUT_SECONDS)
        return session_data

    @classmethod
    def handle_input(cls, session_id: str, user_input: str) -> str:
        """
        Process the user input based on the current session state.
        Returns the next USSD menu text.
        """
        session = cls.get_session(session_id)
        if not session:
            return "Session expired. Please dial again."
            
        state = session['state']
        
        if state == "MAIN_MENU":
            if user_input == "1":
                cls.update_session(session_id, "SEND_MONEY_AMOUNT")
                return "Enter Amount:"
            elif user_input == "2":
                return "Your balance is 500 BDT." # Mocked
            else:
                return "Invalid choice.\n1. Send Money\n2. Check Balance"
                
        elif state == "SEND_MONEY_AMOUNT":
            cls.update_session(session_id, "SEND_MONEY_PIN", {"amount": user_input})
            return "Enter PIN:"
            
        elif state == "SEND_MONEY_PIN":
            # SEC-5: PIN Verification would happen here before triggering transfer
            amount = session['data'].get('amount')
            cache.delete(cls._get_key(session_id)) # Destroy session on completion
            return f"Success! Sent {amount} BDT."
            
        return "Unknown Error."
