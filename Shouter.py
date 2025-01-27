from serverchan_sdk import sc_send
from Logger import *

class Shouter:
    def __init__(self, sendKey:str):
        self._sendKey = sendKey
        self._logger = getLogger()

    def send(self, title:str, desc:str, short:str = None, tags:str = None):
        toSend = {
            "title": title,
            "desc": desc,
            "short": short,
            "tags": tags
        }

        try:
            response = sc_send(self._sendKey, toSend["title"], toSend["desc"], toSend)
            if "code" in response and response['code'] == 0:
                self._logger.debug(response)
                return True
            else:
                self._logger.error(response)
                return False
        except Exception as e:
            self._logger.error(e)
            return False
