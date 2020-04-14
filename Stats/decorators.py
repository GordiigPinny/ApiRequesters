import timeit
from django.conf import settings
from .mixins import CollectStatsMixin


def collect_request_stats_decorator(app_id=settings.APP_ID, app_secret=settings.APP_SECRET, another_stats_funcs=[]):
    def decorator(func):
        def wrappe(self: CollectStatsMixin, request, *args, **kwargs):
            token = self.app_access_token
            start_time = timeit.default_timer()
            response = func(self, request, *args, **kwargs)
            additional_kwargs_for_stats_funcs = []
            if isinstance(response, tuple):
                additional_kwargs_for_stats_funcs = response[1]
                response = response[0]
            process_time = timeit.default_timer() - start_time
            self.collect_request_stats(app_token=token, process_time=process_time, endpoint=app_id,
                                       request=request, response=response)

            for stat_func, func_kwargs in zip(another_stats_funcs, additional_kwargs_for_stats_funcs):
                func_kwargs['app_token'] = token
                stat_func(self, **func_kwargs)
            return response
        return wrappe
    return decorator
