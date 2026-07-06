from abc import ABC, abstractmethod


class BaseWorker(ABC):

    def __init__(self, stages):
        self.stages = stages

    @abstractmethod
    def execute(self, *args, **kwargs):
        pass