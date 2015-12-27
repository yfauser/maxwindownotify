Max Open Window Notifier
========================

This little script (daemon) will poll for the status of all window
sensors known to a MAX Cube system (http://www.eq-3.de) and check for
open windows.

It will then check the temperature at the location of your house using
Open Weather Map (http://openweathermap.org), and if the temperature is
bellow a specified threshold it will send a notification using a
notifier plugin.

Today the only available notifier plugin is using the Pushover service
(https://pushover.net) to send notifications e.g. to mobile phones.

It has been created to safe energy by reminding you to close your
windows after ventilation.

Installation
------------

Max Open Window Notifier can be installed using PIP

.. code:: bash

    sudo pip install maxwindownotify

Usage
~~~~~

You can use the CLI help function to get the details on how to start the
daemon, and what options are available:

.. code:: bash

    $ python maxwindownotify.py --help
    usage: maxwindownotify.py [-h] [-i INTERVAL] [-n NETWORK] [-c CITY]
                              [-t THRESHOLD] -k OWMAPPID [-s] [-u USER] [-p TOKEN]
                              [-v]

    This deamon polls the MAX Cube for all window status. If a window is open
    longer than twice the poll interval a notification will be sent using the
    notifier plugin

    optional arguments:
      -h, --help            show this help message and exit
      -i INTERVAL, --interval INTERVAL
                            polling interval in minutes (default 30 minutes)
      -n NETWORK, --network NETWORK
                            Network Address to send search broadcast for MAX Cube
                            (default 192.168.178.0/24)
      -c CITY, --city CITY  the city name or code in OpenWeatherMap to retrieve
                            the outside temperature from (default Munich, Germany)
      -t THRESHOLD, --threshold THRESHOLD
                            the temperature threshold for suppressing
                            notifications (default: 12C)
      -k OWMAPPID, --owmappid OWMAPPID
                            the API Key (APPID) to authenticate with Open Weather
                            Map
      -s, --simulation      randomly simulate open windows
      -u USER, --user USER  the username (or user key) used for the notifier
                            module
      -p TOKEN, --token TOKEN
                            the password (or app token) used for the notifier
                            module
      -v, --verbose         increase output verbosity

    As an alternative to the commandline, params can be placed in a file, one per
    line, and specified on the commandline like 'maxwindownotify.py @params.conf'.

Example:

.. code:: bash

    python maxwindownotify.py -k 82k4v1b99s41212e5bf5490432bb89f4 -u abcCKnM9uYhjng3kLV6czGFUsmZ76D -p ahxYZcjhXT6P5zDt265LGyuLVaDQNx -i 15 -c Berlin -t 8
