import requests
from requests import RequestException


class EosApiException(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class NodeException(EosApiException):
    def __init__(self, msg: str, resp: requests.Response):
        super().__init__(msg)
        self.resp = resp


class TransactionException(EosApiException):
    def __init__(self, msg, resp: requests.Response):
        super().__init__(msg)
        self.resp = resp
