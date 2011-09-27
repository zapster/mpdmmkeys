#! /usr/bin/env python
"""
Licence:
========
    Lightweight MPD client enabling GNOME MultiMediaKeys
    Copyright (C) 2011  Josef Eisl <free-software@zapster.cc>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import os, sys
import logging
import argparse
import ConfigParser

import dbus
import gobject

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

from mpd import (MPDClient, CommandError)
from socket import error as SocketError

class MediaKeyHandler(object):
    def __init__(self, client):
        self.client = client;
        self.app = 'mpdmmkeys'
        self.bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
        self.bus_object = self.bus.get_object(
            'org.gnome.SettingsDaemon', '/org/gnome/SettingsDaemon/MediaKeys')
 
        self.bus_object.GrabMediaPlayerKeys(
            self.app, 0, dbus_interface='org.gnome.SettingsDaemon.MediaKeys')
 
        self.bus_object.connect_to_signal(
            'MediaPlayerKeyPressed', self.handle_mediakey) 
 
 
    def handle_mediakey(self, application, *mmkeys):
        #for key in mmkeys:
        #    logging.warning(application + ' - ' + key)
       
        if application != self.app:
            return

        for key in mmkeys:
            if key == 'Play':
                logging.info('mmkey play')
                
                if self.client.status()['state'] == 'play':
                    self.client.pause()
                else:
                    self.client.play()

            elif key == 'Stop':
                logging.info('mmkey stop')
                self.client.stop()
            elif key == 'Next':
                logging.info('mmkey next')
                self.client.next()
            elif key == 'Previous':
                logging.info('mmkey previous')
                self.client.previous()
 
def main():
    configfiles=[os.path.dirname(os.path.realpath(__file__)) + '/mpdmmkeys.cfg', 
                 os.path.expanduser('~/mpdmmkeys/mpdmmkeys.cfg')]
    # configuration object 
    config = ConfigParser.ConfigParser()
    # adding default/commandline values
    config.add_section('mpd')
    config.set('mpd', 'host', 'localhost')
    config.set('mpd', 'port', '6600')
    
    # commandline parser
    parser = argparse.ArgumentParser(description='mpdmmkeys is a '
        'lightweight MPD client which allows you to control MPD using '
        'MultiMediaKeys.',
        epilog='NOTE: Default parameters are overwritten by configuration ' 
        'file options. Default config files are ' + str(configfiles) + 
        '. Configuration file options are overwritten by commandline options.')
    parser.add_argument('--host', metavar='HOST', type=str, 
                        help='mpd ip/hostname')
    parser.add_argument('--port', metavar='PORT', type=int, 
                        help='mpd port')
    parser.add_argument('--password', metavar='PASSWORD', type=str, 
                        help='mpd password')
    parser.add_argument('--config', metavar='CONFIGFILE', type=str, 
                        help='overwrite default config files')
    parser.add_argument('-v', '--verbose', metavar='V', type=int, default=0,
                        help='verbosity level 0-2 (default: 0)')

    args = parser.parse_args()
    
    # set verbosity level
    if args.verbose == 0:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose == 1:
        logging.getLogger().setLevel(logging.WARNING)
    elif args.verbose == 2:
        logging.getLogger().setLevel(logging.INFO)

    # looking for configfiles
    if args.config:
        config.read(args.config)
        logging.info('Read configuration file: ' + args.config)
    else: 
        read_files = config.read(configfiles)
        logging.info('Read configuration file(s): ' + str(read_files))
    
    # using commandline parameters if specified
    if args.host:
        config.set('mpd', 'host', args.host)
    if args.port:
        config.set('mpd', 'port', args.port)
    if args.password:
        config.set('mpd', 'password', args.password)
    
    # print out config 
    logging.info('Configuration option "host": ' + config.get('mpd', 'host'))
    logging.info('Configuration option "port": ' + config.get('mpd', 'port'))
    logging.info('Configuration option "password": ' + config.get('mpd', 'password'))

    # start mpd stuff
    client = MPDClient()
    
    # connect to mpd 
    try:
        client.connect(host = config.get('mpd', 'host'), 
                       port = config.get('mpd', 'port'))
    except SocketError:
        logging.error('fail to connect MPD server.')
        sys.exit(1)

    logging.info('Connected to mpd!')

    # send password if specified
    if config.has_option('mpd', 'password'):
        try:
            client.password(config.get('mpd', 'password'))
        except CommandError:
            logging.error('Error trying to pass auth.')
            client.disconnect()
            sys.exit(2)
        logging.info('Mpd password auth!')
    
    # check if we can get status infos
    try:
        client.status()
    except CommandError as e:
        logging.error('MPD CommandError: ' + str(e))
        sys.exit(4)
    
    # install dbus handler and start main loop
    try:
        mediakeyhandler = MediaKeyHandler(client)
        loop = gobject.MainLoop()
        loop.run() 
    except dbus.DBusException as e:
        logging.exception('Cannot load MediaKeyHandler (DBus error): ' + e)
    except KeyboardInterrupt:
        logging.info('KeyboardInterrupt!')

    client.disconnect()
    sys.exit(0)

# Script starts here
if __name__ == '__main__':
    main()
