from typing import Optional, List, Dict, Any
import os
import time
from openai import OpenAI

class AssistantManager:
    """A class to manage OpenAI assistants and threads."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Assistant management
    async def list_assistants(self) -> Dict[str, str]:
        response = self.client.beta.assistants.list()
        return {assistant.name: assistant.id for assistant in response.data}

    async def retrieve_assistant(self, assistant_id: str) -> Any:
        return self.client.beta.assistants.retrieve(assistant_id)

    async def create_assistant(self, name: str, instructions: str, tools: List[Dict[str, Any]], model: str) -> Any:
        return self.client.beta.assistants.create(
            name=name,
            instructions=instructions,
            tools=tools,
            model=model
        )

    async def update_assistant(self, assistant_id: str, name: Optional[str] = None, 
                               description: Optional[str] = None, instructions: Optional[str] = None, 
                               tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        update_fields = {k: v for k, v in locals().items() if k != 'self' and v is not None}
        del update_fields['assistant_id']
        return self.client.beta.assistants.update(assistant_id, **update_fields)

    async def delete_assistant(self, assistant_id: str) -> Any:
        return self.client.beta.assistants.delete(assistant_id)

    async def get_assistant_id_by_name(self, name: str) -> Optional[str]:
        assistants = await self.list_assistants()
        return assistants.get(name)

    # Thread and message management
    async def create_thread(self) -> Any:
        return self.client.beta.threads.create()

    async def create_message(self, thread_id: str, role: str, content: str) -> Any:
        return self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content
        )

    async def list_messages(self, thread_id: str, order: str = "asc", after: Optional[str] = None) -> Any:
        return self.client.beta.threads.messages.list(thread_id=thread_id, order=order, after=after)

    # Run management
    async def create_run(self, thread_id: str, assistant_id: str) -> Any:
        return self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

    def wait_on_run(self, thread_id: str, run_id: str) -> Any:
        run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        while run.status in ["queued", "in_progress"]:
            time.sleep(0.5)
            run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        return run

    async def submit_tool_outputs(self, thread_id: str, run_id: str, tool_outputs: List[Dict[str, Any]]) -> Any:
        return self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )

    # Conversation flow
    async def submit_message(self, assistant_id: str, thread_id: str, user_message: str) -> Any:
        await self.create_message(thread_id, "user", user_message)
        return await self.create_run(thread_id, assistant_id)

    async def get_assistant_response(self, thread_id: str, run_id: str) -> Optional[str]:
        messages = await self.list_messages(thread_id)
        for message in messages.data:
            if message.role == "assistant" and message.run_id == run_id:
                return message.content[0].text.value
        return None

    async def create_thread_and_run(self, assistant_id: str, user_input: str) -> tuple:
        thread = await self.create_thread()
        run = await self.submit_message(assistant_id, thread.id, user_input)
        return thread, run

    async def handle_tool_call(self, run: Any) -> Any:
        return run.required_action.submit_tool_outputs.tool_calls[0]