from abc import ABC,abstractmethod

class BaseProvider(ABC):
    '''
    this base cls is used for modular design 
    '''
    @abstractmethod
    def send(self, messages, tools):
        pass

    @abstractmethod
    def has_tool_calls(self, response):
        pass

    @abstractmethod
    def get_tool_calls(self, response):
        pass

    @abstractmethod
    def format_tool_result(self, results):
        pass

    @abstractmethod
    def get_text(self, response):
        pass
    
    @abstractmethod
    def append_assistant_message(self, response):
        pass

    @abstractmethod
    def append_tool_results(self, messages, tool_results):
        pass

    @abstractmethod
    def user_shutdown_message(self, messages, content):
        pass

    # @abstractmethod
    # def usage(self, response):
    #     pass