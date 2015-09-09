#!/usr/bin/python
# -*- coding: utf-8 -*-
#  copyright 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import time
import string
from stat import ST_SIZE, ST_MTIME
from subprocess import call
import re
import sys
from .freeradiusparser.freeradiusparser import ClientConfParser, UserConfParser
from .crontabparser.cronjobparser import CronJobParser, CronJob
import crypt
import random
from os import urandom
import fileinput
import socket
from subprocess import Popen, PIPE

DATABASE = "privacyidea"
DBUSER = "privacyidea"
POOL = "./0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
CRONTAB = "/etc/crontab"
CRON_USER = "privacyidea"
RESTORE_CMD = "pi-manage.py backup restore %s"
DEFAULT_CONFIG = "/etc/privacyidea/pi.cfg"
BACKUP_DIR = "/var/lib/privacyidea/backup"
BACKUP_CMD = "pi-manage.py backup create -d %s" % BACKUP_DIR


def generate_password(size=6, characters=string.ascii_lowercase +
                      string.ascii_uppercase + string.digits):
    return ''.join(urandom.choice(characters) for _x in range(size))


class Backup(object):
    
    def __init__(self,
                 config_dir="/etc/privacyidea/backup",
                 data_dir="/var/lib/privacyidea/backup"):
        self.data_dir = data_dir
        self.CP = CronJobParser()

    def backup_now(self, password=None):
        '''
        Create a backup of the system right now
        The current backup will contain the
        encryption key. This will be encrypted with
        the password.
        '''
        call(BACKUP_CMD, shell=True)
        
    def restore_backup(self, bfile, password=None):
        '''
        Restore the backup file.
        
        :param bfile: the tgz file name without the path
        :type bfile: string
        '''
        call(RESTORE_CMD % BACKUP_DIR + "/" + bfile, shell=True)
    
    def get_cronjobs(self):
        '''
        Parse the cronjob and return the backup times
        '''
        return self.CP.cronjobs
    
    def add_backup_time(self, dc):
        '''
        Add a backup time to the cronjobs
        
        :param dc: Date component of minute, hour, dom, month, dow
        :type dc: list
        '''
        self.CP.cronjobs.append(CronJob(BACKUP_CMD, dc[0], user=CRON_USER,
                                     hour=dc[1], dom=dc[2], month=dc[3],
                                     dow=dc[4]))
        self.CP.save(CRONTAB)
        
    def get_backups(self):
        '''
        List the available backups in the self.data_dir
        
        :return: dict of backups. Key is the filename, and
                 "size" and "time"
        '''
        backups = {}
        try:
            allfiles = os.listdir(self.data_dir)
        except OSError:
            return backups
        
        for f in allfiles:
            if f.startswith("privacyidea-backup"):
                st = os.stat(self.data_dir + "/" + f)
                size = "%iMB" % (int(st[ST_SIZE]) / (1024 * 1024))
                mtime = time.asctime(time.localtime(st[ST_MTIME]))
                backups[f] = {"size": size,
                              "time": mtime}
        return backups
    
    def del_backup_time(self, hour, minute, month, dom, dow):
        '''
        Delete a backup time from the cronjob
        '''
        jobs_num = len(self.CP.cronjobs)
        i = jobs_num - 1
        while i >= 0:
            cronjob = self.CP.cronjobs[i]
            if (cronjob.hour == hour and
                cronjob.minute == minute and
                cronjob.dom == dom and
                cronjob.month == month and
                cronjob.dow == dow and
                cronjob.user == CRON_USER):
                self.CP.cronjobs.pop(i)
            i -= 1
            
        if len(self.CP.cronjobs) != jobs_num:
            self.CP.save(CRONTAB)


class PrivacyIDEAConfig(object):
    
    ini_template = """import logging
# The realm, where users are allowed to login as administrators
SUPERUSER_REALM = ["super"]
# Your database
#SQLALCHEMY_DATABASE_URI = 'sqlite:////etc/privacyidea/data.sqlite'
# This is used to encrypt the auth_token
#SECRET_KEY = 't0p s3cr3t'
# This is used to encrypt the admin passwords
#PI_PEPPER = "Never know..."
# This is used to encrypt the token data and token passwords
PI_ENCFILE = '/etc/privacyidea/enckey'
# This is used to sign the audit log
#PI_AUDIT_MODULE = 'privacyidea.lib.auditmodules.base'
PI_AUDIT_KEY_PRIVATE = '/etc/privacyidea/private.pem'
PI_AUDIT_KEY_PUBLIC = '/etc/privacyidea/public.pem'
PI_PEPPER = 'zzsWra6vnoYFrlVXJM3DlgPO'
SECRET_KEY = 'sfYF0kW6MsZmmg9dBlf5XMWE'
SQLALCHEMY_DATABASE_URI = 'mysql://pi:P4yvb3d1Thw_@localhost/pi'
PI_LOGFILE = "/var/log/privacyidea/privacyidea.log"
PI_LOGLEVEL = logging.DEBUG
PI_LOGCONFIG = "/etc/privacyidea/logging.cfg"
"""
    
    def __init__(self, file="/etc/privacyidea/pi.cfg", init=False):
        self.file = file
        if init:
            # get the default values
            self.initialize()
        else:
            # read the file
            f = open(self.file)
            content = f.read()
            self._content_to_config(content)
            f.close()

    def _content_to_config(self, content):
        self.config = {}
        for l in content.split("\n"):
            if not l.startswith("import") and not l.startswith("#"):
                try:
                    k, v = l.split("=", 2)
                    self.config[k.strip()] = v.strip().strip("'")
                except Exception:
                    pass

    def initialize(self):
        """
        Initialize the ini file
        """
        content = self.ini_template
        self._content_to_config(content)

    def save(self):
        f = open(self.file, 'wb')
        f.write("import logging\n")
        for k, v in self.config.items():
            if k in ["PI_LOGLEVEL", "SUPERUSER_REALM"]:
                f.write("%s = %s\n" % (k, v))
            else:
                f.write("%s = '%s'\n" % (k, v))
        f.close()
        print "Config file %s saved." % self.file

    def get_keyfile(self):
        return self.config.get("PI_ENCFILE")

    def get_superusers(self):
        realm_string = self.config.get("SUPERUSER_REALM", "[]")
        # convert the string to a list
        return eval(realm_string)

    def set_superusers(self, realms):
        """
        This sets the superuser realms. A list of known realms is provided.

        :param realms: List of the realms of superusers
        :type realms: list
        :return: None
        """
        self.config["SUPERUSER_REALM"] = "%s" % realms

    def get_loglevel(self):
        return self.config.get("PI_LOGLEVEL")
    
    def set_loglevel(self, level):
        if level not in ["logging.DEBUG", "logging.INFO", "logging.WARN",
                         "logging.ERROR"]:
            raise Exception("Invalid loglevel specified")
        self.config["PI_LOGLEVEL"] = level

    def create_audit_keys(self):
        # We can not use the RawConfigParser, since it does not
        # replace the (here)s statement
        private = self.config.get("PI_AUDIT_KEY_PRIVATE")
        public = self.config.get("PI_AUDIT_KEY_PUBLIC")

        print "Create private key %s" % private
        r = call("openssl genrsa -out %s 2048" % private,
                 shell=True)
        if r == 0:
            print "create private key: %s" % private

        print "Create public key %s" % public
        r = call("openssl rsa -in %s -pubout -out %s" % (private, public),
                 shell=True)
        if r == 0:
            print "written public key: %s" % private
            return True, private
        
        return False, private
    
    def create_encryption_key(self):
        # We can not use the RawConfigParser, since it does not
        # replace the (here)s statement
        enckey = self.config.get("PI_ENCFILE")

        r = call("dd if=/dev/urandom of='%s' bs=1 count=96" % enckey,
                 shell=True)
        if r == 0:
            print "written enckey: %s" % enckey
            return True, enckey
        return False, enckey


class FreeRADIUSConfig(object):
       
    def __init__(self, client="/etc/freeradius/clients.conf"):
        '''
        Clients are always kept persistent on the file system
        :param client: clients.conf file.
        '''
        # clients
        self.ccp = ClientConfParser(infile=client)
        self.config_path = os.path.dirname(client)
        self.dir_enabled = self.config_path + "/sites-enabled"
        self.dir_available = self.config_path + "/sites-available"
        
    def clients_get(self):
        clients = self.ccp.get_dict()
        return clients
    
    def client_add(self, client=None):
        '''
        :param client: dictionary with a key as the client name and attributes
        :type client: dict
        '''
        if client:
            clients = self.clients_get()
            for client, attributes in client.iteritems():
                clients[client] = attributes
            
            self.ccp.save(clients)
        
    def client_delete(self, clientname=None):
        '''
        :param clientname: name of the client to be deleted
        :type clientname: string
        '''
        if clientname:
            clients = self.clients_get()
            clients.pop(clientname, None)
            self.ccp.save(clients)

    def set_module_perl(self):
        '''
        Set the perl module
        '''
        f = open(self.config_path + "/modules/perl", "w")
        f.write("""perl {
        module = /usr/share/privacyidea/freeradius/privacyidea_radius.pm
}
        """)
        
    def enable_sites(self, sites):
        """
        :param sites: list of activated links
        :type sitess: list
        """
        if not os.path.exists(self.dir_enabled):
            os.mkdir(self.dir_enabled)

        active_list = os.listdir(self.dir_enabled)
        # deactivate site
        for site in active_list:
            if site not in sites:
                # disable site
                os.unlink(self.dir_enabled +
                          "/" + site)
        # activate site
        for site in sites:
            # enable site
            if not os.path.exists(self.dir_enabled +
                                  "/" + site):
                os.symlink(self.dir_available +
                           "/" + site,
                           self.dir_enabled +
                           "/" + site)
    
    def get_sites(self):
        '''
        returns the contents of /etc/freeradius/sites-available
        '''
        ret = []
        file_list = os.listdir(self.dir_available)
        active_list = os.listdir(self.dir_enabled)
        for k in file_list:
            if k in active_list:
                ret.append((k, "", 1))
            else:
                ret.append((k, "", 0))
        return ret
        
#
#  users:
#     DEFAULT Auth-Type := perl
#
#
#
