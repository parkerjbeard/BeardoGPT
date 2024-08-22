from typing import Optional, List, Dict, Any
import os
import time
import json
from openai import OpenAI
from utils.logger import logger
from app.assistants.assistant_factory import AssistantFactory
from app.config.config_manager import ConfigManager

class AssistantManager:
    def __init__(self, config_manager: ConfigManager):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._assistant_cache = {}
        self.config_manager = config_manager

    # Assistant management
    async def list_assistants(self) -> Dict[str, str]:
        response = self.client.beta.assistants.list()
        return {assistant.name: assistant.id for assistant in response.data}

    def retrieve_assistant(self, assistant_id: str) -> Any:
        if assistant_id not in self._assistant_cache:
            self._assistant_cache[assistant_id] = self.client.beta.assistants.retrieve(assistant_id)
        return self._assistant_cache[assistant_id]

    async def create_assistant(self, name: str, instructions: str, tools: List[Dict[str, Any]], model: str) -> Any:
        return self.client.beta.assistants.create(
            name=name,
            instructions=instructions,
            tools=tools,
            model=model
        )

    async def create_or_get_assistant(self, name: str) -> str:
        assistants = await self.list_assistants()
        assistant_id = assistants.get(name)

        if assistant_id:
            return assistant_id

        tools, model = AssistantFactory.get_tools_for_assistant(name)
        instructions = AssistantFactory.get_assistant_instructions(name)

        assistant = await self.create_assistant(
            name=name,
            instructions=instructions,
            tools=tools,
            model=model
        )
        return assistant.id

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

    # Thread management
    async def create_thread(self) -> Any:
        return self.client.beta.threads.create()

    async def create_message(self, thread_id: str, role: str, content: str) -> Any:
        return self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content
        )

    async def list_messages(self, thread_id: str, order: str = "asc", after: Optional[str] = None, limit: Optional[int] = None) -> Any:
        params = {
            "thread_id": thread_id,
            "order": order,
        }
        if after:
            params["after"] = after
        if limit:
            params["limit"] = limit
        response = self.client.beta.threads.messages.list(**params)
        logger.debug(f"List messages response: {response}")
        return response

    # Run management
    async def create_run(self, thread_id: str, assistant_id: str, instructions: Optional[str] = None) -> Any:
        assistant = self.retrieve_assistant(assistant_id)
        run_params = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "tools": assistant.tools,  # Include the assistant's tools in each run
        }
        if instructions:
            run_params["instructions"] = instructions
        return self.client.beta.threads.runs.create(**run_params)

    async def list_runs(self, thread_id: str) -> Any:
        return self.client.beta.threads.runs.list(thread_id=thread_id)

    def wait_on_run(self, thread_id: str, run_id: str) -> Any:
        while True:
            try:
                run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
                if run.status in ["completed", "requires_action"]:
                    return run
                elif run.status in ["failed", "cancelled", "expired"]:
                    logger.error(f"Run failed with status: {run.status}")
                    raise Exception(f"Run failed with status: {run.status}")
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error retrieving run status: {str(e)}")
                raise

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
        logger.debug(f"Messages: {messages}")
        assistant_messages = []
        for message in messages.data:
            logger.debug(f"Checking message - Role: {message.role}, Run ID: {message.run_id}")
            if message.role == "assistant" and message.run_id == run_id:
                if message.content and len(message.content) > 0:
                    assistant_messages.append(message.content[0].text.value)
        if not assistant_messages:
            logger.warning(f"No assistant response found for run_id: {run_id}")
            return None
        return "\n".join(assistant_messages) 

    async def create_thread_and_run(self, assistant_id: str, user_input: str) -> tuple:
        thread = await self.create_thread()
        run = await self.submit_message(assistant_id, thread.id, user_input)
        return thread, run

    async def handle_tool_call(self, run: Any) -> Any:
        return run.required_action.submit_tool_outputs.tool_calls[0]

    # Structured completion
    async def create_structured_completion(self, messages: list, assistant_name: str, function_name: str) -> dict:
        json_schema = AssistantFactory.get_json_schema(assistant_name, function_name)
        response = self.client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": f"{assistant_name}_{function_name}_schema",
                    "schema": json_schema
                }
            }
        )
        return json.loads(response.choices[0].message.content)

    async def get_assistant_id_by_name(self, name: str) -> Optional[str]:
        assistants = await self.list_assistants()
        assistant_names = self.config_manager.get_assistant_names()
        for category, assistant_name in assistant_names.items():
            if assistant_name == name:
                return assistants.get(name)
        return None