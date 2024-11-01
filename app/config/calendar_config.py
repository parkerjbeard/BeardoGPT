from app.config.base_config import BaseConfig

class CalendarConfig(BaseConfig):
    SYSTEM_MESSAGE = """You are a calendar assistant parsing calendar requests. 
    When extracting information, follow these rules:
    1. For dates and times, use ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
    2. If a specific time is not mentioned, use 00:00:00 as the default time.
    3. If the information is not provided, leave the field empty.
    4. Always include all fields in the output, even if they are empty.
    5. Use the chat history as context to infer any missing information.
    6. For event IDs, if not explicitly mentioned, use 'NULL' as the value.
    7. For time zones, if not explicitly mentioned, use 'NULL' as the value."""

    CATEGORY = "calendar"
    ASSISTANT_NAME = "CalendarAssistant"
    CATEGORY_DESCRIPTION = "Messages about appointments, meetings, or time-specific events that don't involve sending emails."
    FUNCTIONS = ["check_available_slots", "create_event", "update_event", "delete_event"]

    FUNCTION_PARAMS = {
        "check_available_slots": ["start_date", "end_date", "duration", "timezone"],
        "create_event": ["summary", "start_time", "end_time", "description", "location", "timezone"],
        "update_event": ["event_id", "summary", "start_time", "end_time"],
        "delete_event": ["event_id"],
    }

    def get_messages(self, history_context: str, user_input: str, function_name: str) -> list:
        required_params = self.FUNCTION_PARAMS.get(function_name, [])
        param_instructions = f"\nRequired parameters for {function_name}: {', '.join(required_params)}"
        
        return [
            {"role": "system", "content": self.SYSTEM_MESSAGE + param_instructions},
            {"role": "user", "content": f"Chat history:\n{history_context}\n\nParse the following calendar request for {function_name}, using the chat history as context:\n\n{user_input}"}
        ]