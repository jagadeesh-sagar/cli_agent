from .base import BaseProvider
import anthropic
from dotenv import load_dotenv
import logging

from prompts import get_system_prompt
from config import cfg

load_dotenv()
logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    '''
    Anthropic claude api structure class
    
    '''

    def __init__(self):
        self.client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY from env

    def send(self, messages, tools):
        try:
            response=self.client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            system=[{"type": "text", "text": get_system_prompt(), "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            tools=tools
            )     
            return response  
             
        except Exception as e:

            logger.error(f'API Call as Failed :{str(e)}')
            raise RuntimeError(f"API call failed: {str(e)}")
       
    def has_tool_calls(self, response)->bool:
        '''
        used to check the whether agent has tools 
        '''
        
        if response.stop_reason=='tool_use':
            return True
        return False
    
    def get_tool_calls(self, response):
        '''
        handle multi tool calls
        '''
        tool_use_block=[b for b in response.content if b.type=='tool_use'] # helps in handling multi tool calls
        return tool_use_block

    def format_tool_result(self, tool,result):
        '''
        converts the tool results back to claude api structure
        '''
       
        tool_format={
                "type":"tool_result",
                "tool_use_id":tool.id,
                "content":result,
        }
        return tool_format
        
    def get_text(self, response):
        return response.content[0].text
    
    def append_assistant_message(self,messages,response):
        
        messages.append({
        "role":"assistant",
        "content":response.content
             })
        
    def append_tool_results(self,messages,tool_results):

        messages.append({
        "role":"user",
        "content":tool_results
          })
        
    def user_shutdown_message(self,messages,content):
        messages.append({
        'role':'user',
        'content':content})