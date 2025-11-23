import time

import requests

RequestException = requests.RequestException


class GraphRequests:
    def __init__(self, tenant_id, client_id, cache_callback, refresh_token=None):
        self.__tenant_id = tenant_id
        self.__client_id = client_id
        self.__cache_callback = cache_callback
        self.__refresh_token = refresh_token
        if self.__refresh_token is None:
            self.__login()
        else:
            self.__new_access_token()

    def __set_refresh_token(self, refresh_token):
        self.__refresh_token = refresh_token
        self.__cache_callback(refresh_token)

    def __login(self):
        while True:
            response = requests.post(
                url=f'https://login.microsoftonline.com/{self.__tenant_id}/oauth2/v2.0/devicecode',
                timeout=5,
                data={
                    'client_id': self.__client_id,
                    'scope': 'presence.read.all sites.read.all user.readbasic.all offline_access',
                }
            )
            response.raise_for_status()
            response_json = response.json()
            expiry_time = time.monotonic() + response_json['expires_in']
            device_code = response_json['device_code']
            print(response_json['message'])

            while time.monotonic() < expiry_time:
                response = requests.post(
                    url=f'https://login.microsoftonline.com/{self.__tenant_id}/oauth2/v2.0/token',
                    timeout=5,
                    data={
                        'client_id': self.__client_id,
                        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code ',
                        'device_code': device_code,
                    }
                )
                if response.status_code == 400:
                    error = response.json().get('error', None)
                    if error == 'authorization_pending':
                        time.sleep(1)
                        continue

                    if error in ['authorization_declined', 'bad_verification_code', 'expired_token']:
                        break

                response.raise_for_status()
                response_json = response.json()
                self.__set_refresh_token(response_json['refresh_token'])
                self.__access_token = response_json['access_token']
                return

    def __new_access_token(self, retry=True):
        response = requests.post(
            url=f'https://login.microsoftonline.com/{self.__tenant_id}/oauth2/v2.0/token',
            timeout=5,
            data={
                'client_id': self.__client_id,
                'grant_type': 'refresh_token ',
                'refresh_token': self.__refresh_token,
            }
        )

        if response.status_code == 401 and retry is True:
            self.__login()
            self.__new_access_token(False)

        response.raise_for_status()
        response_json = response.json()
        self.__set_refresh_token(response_json['refresh_token'])
        self.__access_token = response_json['access_token']

    def get(self, url, params=None, **kwargs):
        return self.__request('get', url, params=params, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        return self.__request('post', url, data=data, json=json, **kwargs)

    def __request(self, method, url, retry=True, **kwargs):
        response = requests.request(
            method,
            url,
            timeout=kwargs.pop('timeout', 5),
            headers=kwargs.pop('headers', {}) | {'Authorization': f'Bearer {self.__access_token}'},
            **kwargs,
        )

        if response.status_code == 401 and retry is True:
            self.__new_access_token()
            return self.__request(method, url, retry=False, **kwargs)

        response.raise_for_status()
        return response
