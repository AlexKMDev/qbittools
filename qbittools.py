#!/usr/bin/env python3

import argparse, logging, sys, pkgutil, collections, os, configparser
import ipaddress, urllib
from typing import NamedTuple
import pathlib3x as pathlib

if getattr(sys, 'oxidized', False):
    os.environ['PYOXIDIZER'] = '1'

import qbittorrentapi
import commands.add, commands.export, commands.reannounce, commands.update_passkey, commands.tagging, commands.upgrade, commands.unpause, commands.mover, commands.orphaned

class QbitConfig(NamedTuple):
    host: str
    port: str
    username: str
    save_path: pathlib.Path

logger = logging.getLogger(__name__)
config = None

def add_default_args(parser):
    parser.add_argument('-C', '--config', metavar='~/.config/qBittorrent/qBittorrent.conf', default='~/.config/qBittorrent/qBittorrent.conf', help='path to qBittorrent config', required=False)
    parser.add_argument('-s', '--server', metavar='127.0.0.1:8080', help='qBittorrent host', required=False)
    parser.add_argument('-p', '--port', metavar='12345', help='qBittorrent port, deprecated flag', required=False)
    parser.add_argument('-U', '--username', metavar='username', required=False)
    parser.add_argument('-P', '--password', metavar='password', required=False)
    parser.add_argument('-k', '--disable-ssl-verify', help='disable SSL certificate verification when connecting to qBittorrent host', required=False, action='store_true')

def qbit_client(args):
    global config

    if args.port:
        logger.warning('Using deprecated -p/--port flag, it will be removed in future releases!')

    # if user didn't provide arguments try to get them from env variables
    if args.server is None:
        args.server = os.environ.get('QBITTOOLS_SERVER')

    if args.username is None:
        args.username = os.environ.get('QBITTOOLS_USER')

    if args.password is None:
        args.password = os.environ.get('QBITTOOLS_PASSWORD')

    # if user didn't provide environment variables try to parse values from the config
    if args.server is None:
        config = config_values(args.config)

        if config.host is not None and config.port is not None:
            url = urllib.parse.urlparse(config.host)

            if url.hostname is not None:
                url._replace(netloc=url.hostname + ':' + config.port)
                args.server = url.geturl()

    if args.username is None:
        config = config_values(args.config)
        args.username = config.username
    
    # if there is no qbittorrent instance data provided
    if args.server is None:
        logger.error('Unable to get qBittorrent host automatically, specify config file or host manually, see help with -h')
        sys.exit(1)

    client = qbittorrentapi.Client(host=args.server, username=args.username, password=args.password, VERIFY_WEBUI_CERTIFICATE=args.disable_ssl_verify)

    try:
        client.auth_log_in()

        if config is None:
            config = QbitConfig(None, None, None, None)

        if config.save_path is None and client.application.preferences.save_path is not None:
            config = QbitConfig(config.host, config.port, config.username, pathlib.Path(client.application.preferences.save_path))
        else:
            logger.warning('Unable to get default save path!')
    except qbittorrentapi.LoginFailed as e:
        logger.error(e)
    return client

def config_values(path):
    config = configparser.ConfigParser()
    config.read(pathlib.Path(path).expanduser())

    if not 'Preferences' in config:
        return QbitConfig(None, None, None, None)

    preferences = config['Preferences']
    host = preferences.get('webui\\address')

    if host is not None:
        try:
            host = ipaddress.ip_address(host)
            host = 'http://' + host
        except ValueError as e:
            host = 'http://127.0.0.1'

    port = preferences.get('webui\\port')
    user = preferences.get('webui\\username')
    save_path = preferences.get('downloads\\savepath')

    if save_path is not None:
        save_path = pathlib.Path(save_path)

    return QbitConfig(host, port, user, save_path)

def main():
    global config

    logging.getLogger("filelock").setLevel(logging.ERROR) # supress lock messages
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s', datefmt='%I:%M:%S %p')

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    for cmd in ['add', 'export', 'reannounce', 'update_passkey', 'tagging', 'upgrade', 'unpause', 'mover', 'orphaned']:
        mod = getattr(globals()['commands'], cmd)
        getattr(mod, 'add_arguments')(subparsers)

    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit()

    mod = getattr(globals()['commands'], args.command)
    cmd = getattr(mod, '__init__')(args, logger)

if __name__ == "__main__":
    main()
