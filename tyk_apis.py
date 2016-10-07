import requests
import json

TYK_API_URL = 'http://tyk.docker:8080/tyk/'


class TYKAPI:
    def __init__(self, tyk_api_url=None, secret=None):
        self.tyk_auth_header = {
            'X-Tyk-Authorization': secret,
        }
        self.tyk_api_url = tyk_api_url if not tyk_api_url  else TYK_API_URL

    def create_api(self, name, slug, listen_path, target_url):
        with open('tyk_apis.json', 'r') as f:
            api = json.load(f).get("create_api")
            api_str = json.dumps(api)\
                .replace("api_name", name)\
                .replace("api_slug", slug)\
                .replace("api_listen", listen_path)\
                .replace("api_target", target_url)
            resp = requests.post(self.tyk_api_url + 'apis/', json=api_str, headers=self.tyk_auth_header)
            print "result " + resp.text
            # TODO: add result handle

ta = TYKAPI()
ta.create_api("aa", "bb")