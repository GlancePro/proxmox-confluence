import logging
from contextlib import closing
import json

from requests import Session
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, Timeout, RetryError
from settings import (CONFL_URL, PAGE_TITLE, PAGEID,
                      CONFL_USER, CONFL_PASS)

logger = logging.getLogger(__name__)


class ConfluenceClient(object):

    # http session
    _session = None

    # http timeouts, sec
    conn_timeout = 5
    read_timeout = 15

    # http headers
    HEADERS = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    def __init__(self):
        self.setup_session()

    def setup_session(self):
        """setup http session"""

        adapter = HTTPAdapter(max_retries=10,
                              pool_block=False)
        session = Session()
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        session.verify = False
        self._session = session

    @staticmethod
    def request_data(page_version, table):
        params = {
            "id": PAGEID,
            "type": "page",
            "title": PAGE_TITLE,
            "body": {"storage": {"value": table,
                                 "representation": "wiki"}
                     },
            "version": {"number": page_version}
        }
        return json.dumps(params, ensure_ascii=False)

    def _request(self, method='GET',
                 max_retries=3, data=None):
        attempt = 0
        timeouts = (self.conn_timeout, self.read_timeout)
        while attempt < max_retries:
            try:  # fetch response
                request = getattr(self._session, method.lower())
                with closing(request(url=CONFL_URL,
                                     data=data,
                                     headers=self.HEADERS,
                                     auth=(CONFL_USER, CONFL_PASS),
                                     timeout=timeouts)) as response:
                    if response.status_code == 200:
                        logger.debug('successfully posted the article')
                        return response.content

                    response.raise_for_status()

            except (ConnectionError,
                    Timeout, RetryError):
                pass

            except Exception as e:
                logger.error('"{}" ("{}") while "{}" response'.format(e, type(e), method))

            attempt += 1

    def _current_page_version(self):
        content = self._request()
        if content is not None:
            content = json.loads(content)
            return content['version']['number']

    def put_results(self, results):
        page_version = self._current_page_version()
        logger.debug('current page version: {}'.format(page_version))
        if page_version:
            data = self.request_data(page_version=page_version+1,
                                     table=results)
            self._request(method='PUT',
                          data=data)
        else:
            logger.error('could not get page version')

    def close(self):
        if self._session is not None:
            self._session.close()
