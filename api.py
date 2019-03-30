import requests


class Api:
    def __init__(self, url):
        self.url = url

    def get_tracks(self, day=1):
        return self._make_request(day=day).get("tracks")

    def _make_request(self, day):
        r = requests.get(self.url, params={'day': day})

        return r.json()
