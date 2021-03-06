import json
import os
import threading
from redis import StrictRedis, exceptions


class StatsRequestsQueue:
    """
    Очередь неудачных запросов (наполняется из PyBreaker)
    """
    def __init__(self):
        redis_url = os.getenv('REDIS_URL', 'localhost')
        if redis_url == 'localhost':
            self.r = StrictRedis(db=1)
        else:
            self.r = StrictRedis.from_url(redis_url)
        self.is_collecting = True
        self.lock_mod = threading.Lock()
        self.lock_len = threading.Lock()
        self.lock_tmp = threading.Lock()

    def __push(self, data):
        with self.lock_mod:
            try:
                self.r.lpush('requests', json.dumps(data))
                self.is_collecting = True
            except exceptions.RedisError:
                pass

    def __pop(self):
        with self.lock_mod:
            try:
                json_str = self.r.lpop('requests').decode('utf-8')
                return json.loads(json_str)
            except exceptions.RedisError:
                return {'type': 'None'}

    def __len__(self):
        with self.lock_len:
            return self.r.llen('requests')

    def add_requests_stat(self, method, user_id, endpoint, process_time, status_code, request_dt, token):
        data = {
            'type': 'request',
            'method': method,
            'user_id': user_id,
            'endpoint': endpoint,
            'process_time': process_time,
            'status_code': status_code,
            'request_dt': request_dt if isinstance(request_dt, str) else request_dt.isoformat(),
            'token': token
        }
        self.__push(data)

    def add_place_stat(self, action, place_id, user_id, action_dt, token):
        data = {
            'type': 'place',
            'action': action,
            'user_id': user_id,
            'place_id': place_id,
            'action_dt': action_dt if isinstance(action_dt, str) else action_dt.isoformat(),
            'token': token
        }
        self.__push(data)

    def add_accept_stat(self, action, place_id, user_id, action_dt, token):
        data = {
            'type': 'accept',
            'action': action,
            'user_id': user_id,
            'place_id': place_id,
            'action_dt': action_dt if isinstance(action_dt, str) else action_dt.isoformat(),
            'token': token
        }
        self.__push(data)

    def add_rating_stat(self, old_rating, new_rating, place_id, user_id, action_dt, token):
        data = {
            'type': 'rating',
            'old_rating': old_rating,
            'new_rating': new_rating,
            'user_id': user_id,
            'place_id': place_id,
            'action_dt': action_dt if isinstance(action_dt, str) else action_dt.isoformat(),
            'token': token
        }
        self.__push(data)

    def add_pin_purchase_stat(self, pin_id, user_id, purchase_dt, token):
        data = {
            'type': 'pin_purchase',
            'user_id': user_id,
            'pin_id': pin_id,
            'purchase_dt': purchase_dt if isinstance(purchase_dt, str) else purchase_dt.isoformat(),
            'token': token
        }
        self.__push(data)

    def add_achievement_stat(self, achievement_id, user_id, achievement_dt, token):
        data = {
            'type': 'pin_purchase',
            'user_id': user_id,
            'achievement_id': achievement_id,
            'achievement_dt': achievement_dt if isinstance(achievement_dt, str) else achievement_dt.isoformat(),
            'token': token
        }
        self.__push(data)

    def fire(self):
        from .StatsRequester import StatsRequester
        with self.lock_tmp:
            if not self.is_collecting:
                return

        with self.lock_mod:
            print('=== Start to fire queue ===')
            self.is_collecting = False
            r = StatsRequester()
            while len(self) > 0 and not self.is_collecting:
                print('=== Fire ===')
                try:
                    req_json = self.r.lpop('requests').decode('utf-8')
                    req_json = json.loads(req_json)
                except exceptions.RedisError:
                    req_json = {'type': 'None'}
                req_type = req_json.pop('type')
                if req_type == 'request':
                    r.create_request_statistics(**req_json)
                elif req_type == 'place':
                    r.create_place_statistics(**req_json)
                elif req_type == 'accept':
                    r.create_accept_statistics(**req_json)
                elif req_type == 'rating':
                    r.create_rating_statistics(**req_json)
                elif req_type == 'pin_purchase':
                    r.create_pin_purchase_statistics(**req_json)
                elif req_type == 'achievement':
                    r.create_achievement_statistics(**req_json)
            print('=== END FIRING ===')
