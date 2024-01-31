import pathlib
import sys
import plugins.teams.graphrequests as graph_requests
import tomllib
import json
import threading

_GRAPH_V1_ENDPOINT = 'https://graph.microsoft.com/v1.0'
_GRAPH_BETA_ENDPOINT = 'https://graph.microsoft.com/beta'


class Plugin(threading.Thread):
    def __init__(self, plugin_directory: pathlib.Path):
        super().__init__()
        self.__plugin_directory = plugin_directory
        self.__cache_path = plugin_directory.joinpath('cache.json')

        with open(plugin_directory.joinpath('config.toml'), 'rb') as file:
            config = tomllib.load(file)

        self.__tenant_id = config['tenant_id']
        self.__client_id = config['client_id']
        self.__people_list = config['people_list']
        self.__people_user_info_list = config['people_user_info_list']
        self.__people_site_lists = f'{_GRAPH_V1_ENDPOINT}/sites/{config["people_site"]}/lists'

        self.__graph_requests = None
        self.__statuses = None
        self.__stop_signal = threading.Event()

    def get_exports(self):
        return {
            'teams_statuses': self.__get_statuses,
        }

    def __cache_write(self, new_refresh_token):
        with open(self.__cache_path, 'w', encoding='utf-8') as file:
            json.dump({'refresh_token': new_refresh_token}, file)

    def __get_statuses(self):
        while self.__statuses is None:
            self.__stop_signal.wait(1)
        return self.__statuses

    def __get_user_list(self):
        response = self.__graph_requests.get(
            f'{self.__people_site_lists}/{self.__people_list}/items?expand=fields&$top=999'
        )

        lookup_id_users = {
            list_item['fields']['NameLookupId']:
                {
                    'business_unit': list_item['fields']['BU'],
                    'market_team': list_item['fields'].get('Market_x0020_Team', None),
                }
            for list_item in response.json()['value']
        }

        response = self.__graph_requests.get(
            f'{self.__people_site_lists}/{self.__people_user_info_list}/items?'
            f'$select=fields&expand=fields(select=username,id)&$top=999'
        )

        for item in response.json()['value']:
            lookup_id = item['fields']['id']
            if lookup_id in lookup_id_users.keys():
                lookup_id_users[lookup_id]['username'] = item['fields']['UserName']

        users = {}

        done = False
        user_iter = iter(lookup_id_users.items())
        while done is False and not self.__stop_signal.is_set():
            batched_requests = []
            try:
                for i in range(20):
                    lookup_id, user = next(user_iter)
                    if 'username' in user:
                        username = user['username']
                        batched_requests.append({
                            'id': lookup_id,
                            'method': 'GET',
                            'url': f'/users/{username}?$select=id,displayName'
                        })
            except StopIteration:
                done = True

            if len(batched_requests) > 0:
                response = self.__graph_requests.post(
                    url=f'{_GRAPH_V1_ENDPOINT}/$batch',
                    json={
                        'requests': batched_requests,
                    },
                )

                for user_response in response.json()['responses']:
                    user_id = user_response['body']['id']
                    users[user_id] = lookup_id_users[user_response['id']]
                    users[user_id]['name'] = user_response['body']['displayName']
        return users

    def __get_presences(self, user_list):
        statuses = {
            ('Available', 'Available', False): 'available',  # green tick
            ('Available', 'Available', True): 'available',  # hollow green tick
            ('Away', 'Away', False): 'away',  # yellow
            ('Away', 'Away', True): 'ooo',  # OOO
            ('AvailableIdle', 'Inactive', False): 'away',  # yellow
            ('AvailableIdle', 'Inactive', True): 'ooo',  # OOO
            ('BeRightBack', 'BeRightBack', False): 'away',  # yellow
            ('BeRightBack', 'BeRightBack', True): 'ooo',  # OOO
            ('Busy', 'Busy', False): 'busy',  # red
            ('Busy', 'Busy', True): 'busy',  # hollow red
            ('Busy', 'InAMeeting', False): 'busy',  # red
            ('Busy', 'InAMeeting', True): 'ooo',  # OOO
            ('Busy', 'InACall', False): 'busy',  # red
            ('Busy', 'InACall', True): 'busy',  # hollow red
            ('Busy', 'InAConferenceCall', False): 'busy',  # red
            ('Busy', 'InAConferenceCall', True): 'busy',  # hollow red
            ('BusyIdle', 'Busy', False): 'busy',  # red
            ('BusyIdle', 'Busy', True): 'busy',  # hollow red
            ('DoNotDisturb', 'DoNotDisturb', False): 'dnd',  # dnd
            ('DoNotDisturb', 'DoNotDisturb', True): 'dnd',  # hollow dnd
            ('DoNotDisturb', 'Presenting', False): 'dnd',  # dnd
            ('DoNotDisturb', 'Presenting', True): 'dnd',  # hollow dnd
            ('Away', 'OutOfOffice', False): 'ooo',  # OOO
            ('Away', 'OutOfOffice', True): 'ooo',  # OOO
            ('Offline', 'Offline', False): 'offline',  # offline
            ('Offline', 'Offline', True): 'ooo',  # OOO
            ('Offline', 'OffWork', False): 'offline',  # offline
            ('Offline', 'OffWork', True): 'ooo',  # OOO
            ('PresenceUnknown', 'PresenceUnknown', False): None,  # people that have left the company
            ('PresenceUnknown', 'PresenceUnknown', True): None,  # people that have left the company
        }

        response = self.__graph_requests.post(
            url=f'{_GRAPH_BETA_ENDPOINT}/communications/getPresencesByUserId',
            json={
                'ids': list(user_list.keys()),
            },
        )

        for presence in response.json()['value']:
            out_of_office = False
            out_of_office_settings = presence['outOfOfficeSettings']
            if out_of_office_settings is not None and 'isOutOfOffice' in out_of_office_settings:
                out_of_office = out_of_office_settings['isOutOfOffice']

            try:
                status = statuses[(presence['availability'], presence['activity'], out_of_office)]
            except KeyError as exception:
                print('Status not found:', exception, file=sys.stderr)
            else:
                if presence['id'] in user_list and status is not None:
                    user_list[presence['id']]['status'] = status

    def run(self) -> None:
        try:
            with open(self.__cache_path, 'r', encoding='utf-8') as file:
                refresh_token = json.load(file)['refresh_token']
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            refresh_token = None

        while not self.__stop_signal.is_set():
            try:
                self.__graph_requests = graph_requests.GraphRequests(
                    self.__tenant_id,
                    self.__client_id,
                    self.__cache_write,
                    refresh_token,
                )
            except graph_requests.RequestException as exception:
                print('Request exception while authenticating:', exception, file=sys.stderr)
            else:
                break

        while not self.__stop_signal.is_set():
            try:
                users = self.__get_user_list()
            except graph_requests.RequestException as exception:
                print('Request exception while getting user list:', exception, file=sys.stderr)
            else:
                break

        while not self.__stop_signal.is_set():
            try:
                self.__get_presences(users)
            except graph_requests.RequestException as exception:
                print('Request exception while getting user presences:', exception, file=sys.stderr)
            else:
                # remove users that don't have a status
                users = {user_id: user_info for user_id, user_info in users.items() if 'status' in user_info}

                self.__statuses = list(users.values())

            self.__stop_signal.wait(1)

    def stop(self):
        self.__stop_signal.set()
        if self.is_alive():
            self.join()
