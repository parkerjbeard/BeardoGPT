import sys
import os
import time
import logging

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import asyncio
from app.slack_bot import process_message_event
from app.services.travel.travel_planner import TravelPlanner
from app.assistants.assistant_manager import AssistantManager
from app.assistants.dispatcher import Dispatcher
from app.assistants.classifier import Classifier
from utils.logger import logger

# Set console handler to DEBUG level
for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setLevel(logging.DEBUG)

class MockSlackSay:
    async def __call__(self, *args, **kwargs):
        logger.debug(f"MockSlackSay called with args: {args}, kwargs: {kwargs}")
        if args:
            text = args[0]
        else:
            text = kwargs.get('text', '')
        channel = kwargs.get('channel', 'test_channel')
        print(f"Assistant: {text}")

async def interactive_test():
    logger.debug("Starting interactive_test")
    start_time = time.time()

    logger.debug("Initializing components...")
    travel_planner = TravelPlanner()
    assistant_manager = AssistantManager()
    dispatcher = Dispatcher()
    classifier = Classifier(assistant_manager)
    slack_say = MockSlackSay()
    logger.debug(f"Components initialized in {time.time() - start_time:.2f} seconds")

    print("\nWelcome to the interactive assistant test!")
    print("Type your messages as if you were chatting in Slack.")
    print("Type 'exit' to end the test.")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break

        # Create a sample Slack message event
        event = {
            "text": user_input,
            "user": "U123456",
            "channel": "C789012"
        }

        # Process the message event
        logger.debug("\nProcessing message event...")
        process_start_time = time.time()
        try:
            await process_message_event(event, slack_say, travel_planner, assistant_manager, dispatcher)
            logger.debug(f"Message processed in {time.time() - process_start_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)

    logger.debug(f"\nInteractive test completed in {time.time() - start_time:.2f} seconds")

async def main():
    logger.debug("Starting main function")
    await interactive_test()
    logger.debug("Main function completed")

if __name__ == "__main__":
    logger.debug("Script started")
    asyncio.run(main())
    logger.debug("Script completed")