from app.assistants.assistant_manager import AssistantManager
from utils.slack_formatter import SlackMessageFormatter
from app.config.config_manager import ConfigManager
from app.assistants.dispatcher import Dispatcher
from app.openai_helper import OpenAIClient
from slack_bolt.async_app import AsyncApp
from app.config.settings import settings
from utils.logger import logger
import traceback
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

def create_slack_bot(config_manager: ConfigManager):
    logger.debug("Creating Slack bot")
    app = AsyncApp(
        token=settings.SLACK_BOT_TOKEN,
        signing_secret=settings.SLACK_SIGNING_SECRET,
        process_before_response=True,
        installation_store=None  # Add this for Lambda
    )

    assistant_manager = AssistantManager(config_manager)
    dispatcher = Dispatcher()

    @app.event("message")
    async def handle_message_events(event, say):
        logger.debug(f"Received message event: {event}")
        await process_message_event(event, say, dispatcher)

    @app.error
    async def global_error_handler(error, body, logger):
        logger.error(f"Global error: {error}")
        logger.error(f"Request body: {body}")

    logger.debug("Slack bot created successfully")
    return app

async def process_message_event(event, say, dispatcher):
    text = event.get("text", "")
    user = event.get("user")
    channel = event.get("channel")

    logger.debug(f"Processing message event - Text: {text}, User: {user}, Channel: {channel}")

    if not text or not user:
        logger.warning("Invalid message event: missing text or user")
        return

    try:
        openai_client = OpenAIClient()
        short_response = openai_client.generate_short_response(text)
        await say(text=short_response, channel=channel)

        logger.debug("Dispatching message")
        dispatch_result = await dispatcher.dispatch(text.lower(), user)  # Added user parameter here
        logger.debug(f"Dispatch result: {dispatch_result}")
        
        if 'error' in dispatch_result:
            logger.error(f"Error in dispatch result: {dispatch_result['error']}")
            await say(text=f"I'm sorry, but I encountered an error: {dispatch_result['error']}", channel=channel)
            return

        thread_id = dispatch_result.get('thread_id')
        run_id = dispatch_result.get('run_id')
        function_outputs = dispatch_result.get('function_outputs')
        assistant_response = dispatch_result.get('assistant_response')
        
        logger.debug(f"Thread ID: {thread_id}, Run ID: {run_id}")
        logger.debug(f"Function outputs: {function_outputs}")
        logger.debug(f"Assistant response: {assistant_response}")

        if not thread_id or not run_id:
            logger.error("Invalid dispatch result: missing thread_id or run_id")
            await say(text="I'm sorry, but I encountered an error while processing your request. Please try again later.", channel=channel)
            return

        if function_outputs:
            logger.debug(f"Sending function outputs: {function_outputs}")
            for output in function_outputs:
                if isinstance(output, dict) and 'output' in output:
                    logger.debug(f"Sending function output: {output['output']}")
                    await send_slack_response(say, output['output'], None, channel)
                else:
                    logger.error(f"Unexpected output format: {output}")

        if assistant_response:
            logger.debug(f"Sending assistant response: {assistant_response}")
            await send_slack_response(say, assistant_response, None, channel)
        else:
            logger.warning("No assistant response received")
            await say(text="I'm sorry, but I couldn't generate a response. Please try again.", channel=channel)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        await say(text=f"I'm sorry, but I encountered an error while processing your request: {str(e)}\nPlease try again later.", channel=channel)

async def send_slack_response(say, assistant_response, tool_responses, channel):
    logger.debug(f"Sending Slack response - Channel: {channel}, Response: {assistant_response}")
    
    slack_formatter = SlackMessageFormatter()
    
    try:
        formatted_message = await slack_formatter.format_message(assistant_response, channel)
        split_messages = slack_formatter.split_message(formatted_message)
        
        for message in split_messages:
            await say(**message)
    except Exception as e:
        logger.error(f"Error formatting and sending Slack message: {e}")
        # Fallback to plain text
        await say(text=assistant_response, channel=channel)
    
    if tool_responses:
        logger.debug(f"Sending tool responses: {tool_responses}")
        try:
            formatted_tool_response = await slack_formatter.format_message(str(tool_responses), channel)
            split_tool_messages = slack_formatter.split_message(formatted_tool_response)
            
            for message in split_tool_messages:
                await say(**message)
        except Exception as e:
            logger.error(f"Error formatting and sending tool response: {e}")
            # Fallback to plain text
            await say(text=str(tool_responses), channel=channel)