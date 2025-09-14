import concurrent.futures
import threading
import requests

from allpress.util import logging

logging.getLogger(__name__)

from time import sleep

"""
Enum style class that defines load state \n
values for `HTTPRequestPoolManager`.
"""


class States:
    LOW = 0
    LIGHT = 1
    REGULAR = 2
    MODERATE = 3
    HEAVY = 4


class HTTPRequestPoolManager:

    def __init__(self, max_concurrent_requests=256):
        # Initial load state
        self.load_state = States.LOW
        # Maximum number of concurrent requests allowed
        self.max_concurrent_requests = max_concurrent_requests
        # Current number of active requests
        self.n_active_concurrent_requests = 0
        # Queue of request URLs waiting to be sent
        self._request_pool = []
        # Futures of requests currently being executed
        self._pool_futures = []
        # Flag to indicate if the pool manager should be running
        self._pool_manager_active = False
        logging.info('New HTTPRequestPoolManager instatiated.')

    """
    Returns the load of the RequestPoolManager as a State value.
    Calculated from the maximum number of allowed concurrent requests
    `self.max_concurrent_requests` divided by the total number of
    active concurrent requests by the _get_load function.
    """

    def _get_state(self):
        # Map current load percentage to one of the States
        if self._get_load() < 20.0:
            return States.LOW
        elif 20.0 < self._get_load() < 33.3:
            return States.LIGHT
        elif 33.3 < self._get_load() < 50.0:
            return States.REGULAR
        elif 50.0 < self._get_load() < 75.0:
            return States.MODERATE
        elif self._get_load() > 75.0:
            return States.HEAVY

    def _get_load(self) -> float:
        # Calculate load as a percentage of max concurrent requests
        return (self.n_active_concurrent_requests / self.max_concurrent_requests) * 100.0

    def _execute_request(self, url: str) -> requests.models.Response:
        # Send a single HTTP GET request
        try:
            response = requests.get(url)
            logging.info(f'Response from {url} received. Status code {response.status_code}')
            return response
        except Exception as error:
            # If request fails, log the error and return empty response object
            logging.error(f'Request to {url} failed with exception!; {error}.')
            logging.error(f'Generating empty response object as placeholder.')
            return requests.models.Response()

    def _execute_pool(self):
        # Main loop for processing queued requests
        pool_executor = concurrent.futures.ThreadPoolExecutor()
        while self._pool_manager_active:
            if len(self._request_pool) > 0:
                # Iterate over a copy of the pool (to allow safe removal while iterating)
                for request_url in list(self._request_pool):
                    # Low load: send immediately
                    if self._get_state() <= 1:
                        logging.info('Low request load. Sending request immediately.')
                        self.n_active_concurrent_requests += 1
                        self._request_pool.remove(request_url)
                        self._pool_futures.append(pool_executor.submit(self._execute_request, request_url))
                        logging.info(f'Request to {request_url} sent to ThreadPoolExecutor.')
                    # Light load: slight delay before sending
                    if self._get_state() == 2:
                        logging.info('Light load. Rate limiting by sleeping for 0.01 secounds')
                        sleep(0.01)
                        self.n_active_concurrent_requests += 1
                        self._request_pool.remove(request_url)
                        self._pool_futures.append(pool_executor.submit(self._execute_request, request_url))
                        logging.info(f'Request to {request_url} sent to ThreadPoolExecutor.')
                    # Moderate load: larger delay
                    if self._get_state() == 3:
                        logging.info('Moderate request load. Rate limiting by sleeping for 0.25 seconds.')
                        sleep(0.25)
                        self.n_active_concurrent_requests += 1
                        self._request_pool.remove(request_url)
                        self._pool_futures.append(pool_executor.submit(self._execute_request, request_url))
                        logging.info(f'Request to {request_url} sent to ThreadPoolExecutor.')
                    # Heavy load: throttle significantly
                    if self._get_state() == 4:
                        logging.warning('Heavy load. Throttling by half a second.')
                        sleep(0.5)
                        self.n_active_concurrent_requests += 1
                        self._request_pool.remove(request_url)
                        self._pool_futures.append(pool_executor.submit(self._execute_request, request_url))
                        logging.info(f'Request to {request_url} sent to ThreadPoolExecutor.')
            elif len(self._request_pool) == 0:
                # No more requests left; shut down the pool manager
                self._pool_manager_active = False

    def execute_request_batch(self, batch: list) -> list:
        # Entry point: submit a batch of requests
        logging.info(f'Executing request batch of {len(batch)} requests.')
        # Optimistically add all batch requests to active count
        self.n_active_concurrent_requests += len(batch)
        # Add batch requests to queue
        self._request_pool += batch
        self._pool_manager_active = True
        logging.info('Starting batch thread.')
        # Run request pool in background thread
        thread = threading.Thread(target=self._execute_pool)
        thread.start()
        thread.join()  # Wait until all requests finish

        responses = []
        # Collect all responses from futures
        for future in self._pool_futures:
            try:
                responses.append(future.result())
            except Exception as e:
                # If a future fails, log and append placeholder response
                logging.error(f'Exception in future: {e}')
                responses.append(requests.models.Response())

        # Reset for next batch
        self._pool_futures = []
        self.n_active_concurrent_requests = 0
        return responses



