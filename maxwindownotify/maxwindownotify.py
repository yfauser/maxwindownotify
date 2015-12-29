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

from netaddr import IPNetwork
import socket
import sys
import base64
from io import BytesIO
import binascii
import random
import time
import argparse
import logging
from notifier_modules.pushover_notifier import Notifier
import requests
import json
from collections import OrderedDict
from collections import namedtuple


class Session:
    def __init__(self, debug=False, verify=False, suppress_warnings=False):
        self._debug = debug
        self._verify = verify
        self._suppress_warnings = suppress_warnings
        self._session = requests.Session()
        self._session.verify = self._verify

        # if debug then enable underlying httplib debugging
        if self._debug:
            import httplib
            httplib.HTTPConnection.debuglevel = 1

        # if suppress_warnings then disable any InsecureRequestWarnings caused by self signed certs
        if self._suppress_warnings:
            requests.packages.urllib3.disable_warnings()

    def do_request(self, method, url, data=None, headers=None, params=None):
            """
            Handle API requests / responses transport
            :param method: HTTP method to use as string
            :param data: Any data to be send in the request
            :param headers: Any headers as PyDict
            :param params: Any query parameters as PyDict
            :return: response as Ordered Dict with Status Code and Body
            """

            if data:
                if headers:
                    headers.update({'Content-Type': 'application/json'})
                else:
                    headers = {'Content-Type': 'application/json'}

            try:
                response = self._session.request(method, url, headers=headers, params=params, data=data)
            except requests.exceptions.RequestException as e:
                return OrderedDict([('status', 'connection exception'), ('body', e)])

            response_content = response.content

            if response.status_code in [200]:
                if 'Content-Type' in response.headers:
                    if response.headers['Content-Type'].find('application/json') != -1:
                        response_content = json.loads(response.content,
                                                      object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))

            return OrderedDict([('status', response.status_code), ('body', response_content)])


class MaxConnection:
    def __init__(self, discover_ip_subnet='192.168.178.0/24', echo_port=23272, cube_port=62910):
        """
        Max CUBE discovery and connection handling object
        :param discover_ip_subnet: Subnet to send the Max CUBE discover Broadcast to
        :param echo_port: UDP port number for discover broadcast
        :param cube_port: TCP port for the connection to Max CUBE
        """
        self.discover_ip_range = discover_ip_subnet
        self.echo_port = echo_port
        self.cube_port = cube_port
        self.cube_data, self.cube_ip = self.discover_cube()

    def discover_cube(self):
        """
        Discover the MAX CUBE on the network
        :return: Tuple,
        [0] contains a dict with the CUBE details like verion, etc.,
        [1] contains the IP of the discovered Max CUBE
        """
        subnet_broadcast = str(IPNetwork(self.discover_ip_range).broadcast)
        subnet_host_list = IPNetwork(self.discover_ip_range).iter_hosts()
        cube_data_dict, cube_ip = self._disc_cube_bcast(subnet_broadcast)

        if not cube_ip:
            logging.log(logging.WARNING, 'Could not find MAX Cube on the network through broadcast discovery, '
                                         'retrying with ip range tcp scan, this may take a while')
            cube_ip = self._disc_cube_ucast(subnet_host_list)

        if not cube_ip:
            logging.log(logging.ERROR, 'Could not find any MAX Cube on the network')
            sys.exit()

        return cube_data_dict, cube_ip

    def _disc_cube_bcast(self, subnet_broadcast):
        udp_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        udp_send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
        udp_send_socket.settimeout(5)
        udp_recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        udp_recv_socket.bind(('', self.echo_port))
        udp_recv_socket.settimeout(5)

        hello_data = '6551334d61782a002a2a2a2a2a2a2a2a2a2a49'.decode('hex')

        try:
            udp_send_socket.sendto(hello_data, (subnet_broadcast, self.echo_port))
        except (socket.timeout, socket.error) as e:
            logging.log(logging.ERROR, 'Could not send UDP discover brodcast, socket error is: {}'.format(e))
            return None, None

        cube_data = None
        cube_ip = None

        while True:
            try:
                recv_data, recvaddr = udp_recv_socket.recvfrom(4096)
                if recv_data != hello_data:
                    cube_data, cube_ip = recv_data, recvaddr[0]
                    break
            except (socket.timeout, socket.error) as e:
                udp_send_socket.close()
                udp_recv_socket.close()
                logging.log(logging.ERROR, 'No MAX Cube reacted to our subnet broadcast, socket error is: {}'.format(e))
                return None, None

        cube_data_dict = {}
        if cube_data:
            cube_data_dict.update({'generic_reponse': cube_data[:8]})
            cube_data_dict.update({'serial_number': cube_data[9:18]})
            cube_data_dict.update({'firmware_version': cube_data[-2:]})

        udp_send_socket.close()
        udp_recv_socket.close()

        return cube_data_dict, cube_ip

    def _disc_cube_ucast(self, ip_range_list):
        for ip in ip_range_list:
            if self._test_connect_to_cube(str(ip)):
                return str(ip)

        return None

    def _test_connect_to_cube(self, ip):
        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.settimeout(0.5)
            tcp_socket.connect((ip, self.cube_port))
            tcp_socket.close()
            return True
        except (socket.timeout, socket.error) as e:
            tcp_socket.close()
            return None

    def _get_cube_data(self):
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(3)

        try:
            tcp_socket.connect((self.cube_ip, self.cube_port))
        except (socket.timeout, socket.error) as e:
            logging.log(logging.ERROR, 'Could not open TCP connection to MAX Cube, socket error is: {}'.format(e))
            tcp_socket.close()
            return None

        received_data = b''
        logging.log(logging.INFO, 'connecting to MAX Cube to retrieve data')
        while True:
            try:
                received_data += tcp_socket.recv(100000)
            except (socket.timeout, socket.error):
                tcp_socket.close()
                break

        tcp_socket.close()

        return received_data

    def _read_cube_data_lines(self, cube_data):
        m_line_dict = {}
        l_line_dict = {}

        for line in cube_data.split(b'\r\n'):
            if line[:2] == b'M:':
                m_line_dict = self._decode_m_line(line)
            if line[:2] == b'L:':
                l_line_dict = self._decode_l_line(line)
            if not line:
                break

        return m_line_dict, l_line_dict

    @staticmethod
    def _decode_m_line(m_line):
        encoded = m_line.strip().split(b',', 2)[2]
        decoded = BytesIO(base64.decodestring(encoded))

        data = {}
        decoded.read(2)     # This drops the first 2 bytes
        data['room_count'] = ord(decoded.read(1))

        data['rooms'] = {}
        for i in range(data['room_count']):
            room = {'id': ord(decoded.read(1)), 'name_len': ord(decoded.read(1))}
            room['name'] = decoded.read(room['name_len'])
            room['rf_address'] = binascii.b2a_hex(decoded.read(3))
            data['rooms'][room['id']] = room

        data['devices_count'] = ord(decoded.read(1))
        data['devices'] = []
        for i in range(data['devices_count']):
            device = {'type': ord(decoded.read(1)), 'rf_address': binascii.b2a_hex(decoded.read(3)),
                      'serial': decoded.read(10), 'name_len': ord(decoded.read(1))}
            device['name'] = decoded.read(device['name_len'])
            device['room_id'] = ord(decoded.read(1))
            data['devices'].append(device)

        decoded.read(1)     # This drops the last bytes

        return data

    @staticmethod
    def _decode_l_line(l_line):
        encoded = l_line.strip()[2:]
        decoded = BytesIO(base64.decodestring(encoded))
        data = {}
        while True:
            device = {}
            try:
                device['len'] = ord(decoded.read(1))
            except TypeError:
                break
            device['rf_address'] = binascii.b2a_hex(decoded.read(3))
            decoded.read(1)  # Drop unknown byte
            device['flags_1'] = ord(decoded.read(1))
            device['flags_2'] = ord(decoded.read(1))
            if device['len'] > 6:
                decoded.read(device['len'] - 6)  # Drop the data, those are all not Window Switches
            data[device['rf_address']] = device
        return data

    def window_switch_status(self, simulation_mode=False):
        """
        Get the current status of all window sensors the Max CUBE knows about
        :param simulation_mode: If simulation mode is set to 'true',
        each call will randomly alter one of the windows to be 'open'
        :return: a dict with all windows sensors and their status
        """
        windows_switch_dict = {}

        cube_data = self._get_cube_data()

        if not cube_data:
            logging.log(logging.ERROR, 'Did not receive data from MAX Cube')
            return None

        rooms_and_devices, device_statis = self._read_cube_data_lines(cube_data)

        for device in rooms_and_devices['devices']:
            if device['type'] == 4:
                windows_switch_dict.update({device['rf_address']: {'rf_address': device['rf_address'],
                                                                   'name': device['name'],
                                                                   'status': 'closed'}})
        for device in device_statis:
            if device in [rf_addr for rf_addr in windows_switch_dict]:
                if device_statis[device]['flags_2'] & 2 == 2:
                    windows_switch_dict[device]['status'] = 'open'
                else:
                    windows_switch_dict[device]['status'] = 'closed'

        if simulation_mode:
            windows_switch_dict[random.choice([item for item in windows_switch_dict])]['status'] = 'open'

        return windows_switch_dict


class OpenWeatherMap:
    def __init__(self, appkey, apiurl='http://api.openweathermap.org/data/2.5/weather', debug=False):
        """
        Object handling the session with the Open Weather Map API to retrieve the temperature of a location
        :param appkey: The APPID key for the OpenWeatherMap API.
        See openweathermap.org to register and get the APPID Key
        :param apiurl: The URL to retrieve the temperature, defaults to 'http://api.openweathermap.org/data/2.5/weather'
        :param debug: sends HTTPLIB debug output to stdout if set to 'True'
        """
        self.appkey = appkey
        self.apiurl = apiurl
        self._session = Session(debug=debug)

    def get_current_temperature(self, city, units='metric'):
        """
        retrieves the current temperature of a location
        :param city: The City name, code or ID as known in Open Weather Map
        :param units: The measurement unit, defaults to 'metric'.
        Can also be set to 'kelvin' or 'imperial' for fahrenheit
        :return: returns the temperature of the location as float, or None if an error occurred.
        """
        params = {'q': city, 'APPID': self.appkey, 'units': units}
        response = self._session.do_request('GET', self.apiurl, params=params)

        try:
            temperature = response['body'].main.temp
            return temperature
        except (TypeError, AttributeError):
            logging.log(logging.ERROR, 'current temperature for {} not received, status code was {}, response body '
                                       'was {}'.format(city, response['status'], response['body']))
            return None


def main():
    parser = argparse.ArgumentParser(description="This deamon polls the MAX Cube for all window status. "
                                                 "If a window is open longer than twice the poll interval a "
                                                 "notification will be sent using the notifier plugin",
                                     epilog="As an alternative to the commandline, params can be placed in a file, "
                                            "one per line, and specified on the commandline like "
                                            "'%(prog)s @params.conf'.",
                                     fromfile_prefix_chars='@')
    parser.add_argument("-i",
                        "--interval",
                        help="polling interval in minutes (default 30 minutes)",
                        default=30)
    parser.add_argument("-n",
                        "--network",
                        help="Network Address to send search broadcast for MAX Cube (default 192.168.178.0/24)",
                        default='192.168.178.0/24')
    parser.add_argument("-c",
                        "--city",
                        help="the city name or code in OpenWeatherMap to retrieve the outside temperature from "
                             "(default Munich, Germany)",
                        default="munich,DE")
    parser.add_argument("-t",
                        "--threshold",
                        help="the temperature threshold for suppressing notifications (default: 12C)",
                        type=float,
                        default=12)
    parser.add_argument("-k",
                        "--owmappid",
                        help="the API Key (APPID) to authenticate with Open Weather Map",
                        required=True)
    parser.add_argument("-s",
                        "--simulation",
                        help="randomly simulate open windows",
                        action="store_true")
    parser.add_argument("-u",
                        "--user",
                        help="the username (or user key) used for the notifier module")
    parser.add_argument("-p",
                        "--token",
                        help="the password (or app token) used for the notifier module")
    parser.add_argument("-v",
                        "--verbose",
                        help="increase output verbosity",
                        action="store_true")
    args = parser.parse_args()

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING

    last_window_status = None
    logging.basicConfig(format="%(asctime)-15s %(levelname)s: %(message)s", level=loglevel)
    notifier_log_http = False
    if loglevel == logging.DEBUG:
        notifier_log_http = True
    if args.user and args.token:
        notify = Notifier(user=args.user, token=args.token, debug=notifier_log_http)
    else:
        notify = Notifier()

    temperature = OpenWeatherMap(args.owmappid)

    logging.log(logging.INFO, 'searching for MAX Cube in the network')
    max_cube = MaxConnection(discover_ip_subnet=args.network)

    while True:
        skip_run = False
        window_status = max_cube.window_switch_status(args.simulation)
        logging.log(logging.INFO, 'current window data: {}'.format(window_status))
        outside_temperature = temperature.get_current_temperature(args.city)
        logging.log(logging.INFO, 'current temperature in {}: {}'.format(args.city, outside_temperature))

        if not window_status:
            skip_run = True
            logging.log(logging.INFO, 'did not receive any data from MAX Cube, skipping this cycle')
        elif not outside_temperature:
            skip_run = True
            logging.log(logging.INFO, 'did not receive any temperature data, skipping this cycle')
        elif not outside_temperature <= args.threshold:
            skip_run = True
            logging.log(logging.INFO, 'current outside temperature above threshold of {}, skipping this '
                                      'cycle'.format(args.threshold))

        if not last_window_status and window_status:
            last_window_status = window_status

        if not skip_run:
            for rf_addr in window_status:
                if window_status[rf_addr]['status'] == 'open':
                    if window_status[rf_addr]['status'] == last_window_status[rf_addr]['status']:
                        logging.log(logging.INFO, 'sending notify because of open window')
                        notify.send_msg('{} was open for more than {} minutes, and the temperature '
                                        'in {} is {}'.format(window_status[rf_addr]['name'],
                                                             args.interval, args.city, outside_temperature))
        last_window_status = window_status
        logging.log(logging.INFO, 'sleeping for {} minutes'.format(args.interval))
        time.sleep(int(args.interval)*60)


if __name__ == '__main__':
    main()
