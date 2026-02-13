from abc import ABC, abstractmethod

class BaseAPI(ABC):
    """所有 API 组件的抽象基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("enabled", False)

    @abstractmethod
    def get_data(self, *args, **kwargs):
        """核心数据获取接口，子类必须实现"""
        pass

    @property
    def name(self):
        """组件名称，默认使用类名"""
        return self.__class__.__name__
