#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2015 Yves Fauser. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
# to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions
# of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
# TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

__author__ = 'yfauser'

import httplib
import urllib
import argparse
import logging
import sys
import time

class Notifier:
    def __init__(self, user=None, token=None, debug=False):
        """
        Notifier Object
        :param user: The user key as generated when registering to Pushover service
        :param token: The App Token as generated when creating the app in the Pushover service
        :param debug: If set to 'True', sends detailed HTTP Log to stdout
        """
        self._debug = debug
        self._user = user
        self._token = token

        if not self._user or not self._token:
            logging.log(logging.ERROR, 'This nofifier module needs a user key and app token to be set')
            sys.exit('exiting because of missing user key and app token in notifier')

        # if debug then enable underlying httplib debugging
        if self._debug:
            httplib.HTTPConnection.debuglevel = 1

    def send_msg(self, message):
        """
        sends a notification (message) to Pushover app
        :param message: The notification (message) text
        :return: Tuple;
        [0] contains the HTTP return code like '200'
        [1] contains the return code reason, like 'OK' for a '200'
        Returns None if an error occured
        """
        session = httplib.HTTPSConnection("api.pushover.net:443")
        session.request("POST", "/1/messages.json", urllib.urlencode({"token": self._token,
                                                                      "user": self._user,
                                                                      "message": str(message)}),
                        {"Content-type": "application/x-www-form-urlencoded"})
        try:
            time.sleep(1)
            response = session.getresponse()
        except httplib.ResponseNotReady as e:
            logging.log(logging.WARNING, 'HTTPLib issue when retrieving response from Pushover Service: {}'.format(e))
            session.close()
            return None

        if response.status not in [200]:
            logging.log(logging.ERROR, 'received bad status code for Pushover service, '
                                       'response was: {}, {}'.format(response.status, response.reason))
            return None

        session.close()

        return response.status, response.reason


def main(args, loglevel):
    logging.basicConfig(format="%(asctime)-15s %(levelname)s: %(message)s", level=loglevel)

    http_debug = False
    if loglevel == logging.DEBUG:
        http_debug = True

    notify = Notifier(args.user_key, args.app_token, debug=http_debug)
    notify.send_msg(args.message)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="This notifier will send messages using the Pushover Andriod App",
                                     epilog="As an alternative to the commandline, params can be placed in a file, "
                                            "one per line, and specified on the commandline like "
                                            "'%(prog)s @params.conf'.",
                                     fromfile_prefix_chars='@')
    parser.add_argument("message",
                        help="message to be send")
    parser.add_argument("-a",
                        "--app_token",
                        help="App token for Pushover Service",
                        required=True)
    parser.add_argument("-u",
                        "--user_key",
                        help="user key to send notifications to",
                        required=True)
    parser.add_argument("-v",
                        "--verbose",
                        help="increase output verbosity",
                        action="store_true")
    args = parser.parse_args()

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING

    main(args, loglevel)
