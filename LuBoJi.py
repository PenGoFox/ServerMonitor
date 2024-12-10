# 录播姬

import requests
from base64 import b64encode

class LuBoJi:
    def __init__(self, url:str, username:str, password:str):
        self._url = url
        self._username = username
        self._password = password

        self._auth = b64encode(f"{username}:{password}".encode()).decode()
        self._headers = {
            "accept": "text/plain",
            "Authorization": f"Basic {self._auth}"
        }

    def testLogin(self):
        res = requests.get(self._url, headers=self._headers)
        return res.status_code == 200

    def getRoomList(self):
        api = "/api/room"
        res = requests.get(self._url + api, headers=self._headers)
        if res.status_code != 200:
            return None
        return res.json()

    def getRoomMessage(self, roomId):
        api = f"/api/room/{roomId}"
        res = requests.get(self._url + api, headers=self._headers)
        if res.status_code != 200:
            return None
        return res.json()
