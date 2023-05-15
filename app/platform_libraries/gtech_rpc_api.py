# -*- coding: utf-8 -*-
""" GTech RPC API libraries
"""

___author___ = 'Vance Lo <vance.lo@wdc.com>'

# std modules
import json
import time
from pprint import pformat

# platform modules
from platform_libraries.ssh_client import SSHClient
from platform_libraries import common_utils


class GrackClient(SSHClient):

    def __init__(self, *args, **kwargs):
        super(GrackClient, self).__init__(*args, **kwargs)
        self.remove_strings.append('Could not chdir to home directory /home/admin: No such file or directory')
        print 'GrackClient done'


class GTechRPCRequester(object):

    def __init__(self, uut_ip, username, password, root_password):
        self.log = common_utils.create_logger(overwrite=False)
        self.cmd_path = '/usr/sbin/gtech-rpc'
        self.grack_ssh = GrackClient(hostname=uut_ip, username=username, password=password, root_password=root_password)
        self.grack_ssh.connect()

    def send_request(self, service, method, parameters):
        s = json.dumps(parameters)
        parameters_json = s.replace('\"', '\\\"')
        cmd = '{0} {1} {2} \'{3}\''.format(self.cmd_path, service, method, parameters_json)
        result  = self.grack_ssh.sudo_execute(cmd)[1]
        response = json.loads(result)
        return response

    def run_cmd_on_grack(self, cmd):
        return self.grack_ssh.sudo_execute(cmd)

    def retry_connect_SSH(self, timeout=60, retry_timeout=70):
        start_time = time.time()
        while retry_timeout > (time.time()-start_time):
            try:
                stdout, stderr = self.grack_ssh.connect()
                return stdout, stderr
            except Exception, e:
                self.log.warning('[retry_connect] Catch Exception: {}'.format(e))
                self.grack_ssh.close()
                time.sleep(1)
        raise RuntimeError('Retry timeout for {} secs.'.format(retry_timeout))

    def error(self, message):
        """
            Save the error log and raise Exception at the same time
            :param message: The error log to be saved
        """
        self.log.error(message)
        raise RuntimeError(message)


class GTechRPCAPI(GTechRPCRequester):

    def get_available_btrfs_raid_list(self):
        """
        Returns:
            {u'data':
                [{u'_readonly': False,
                u'_referenced': True,
                u'autoRecoveryStartInterval': u'1',
                u'available': u'25706582118400',
                u'corruptiontime': u'',
                u'degraded': False,
                u'description': u'description',
                u'devicefile': u'/dev/sdd',
                u'devices': [u'/dev/sdd',
                            u'/dev/sdf',
                            u'/dev/sdg',
                            u'/dev/sdh',
                            u'/dev/sdi'],
                u'isRootDevice': False,
                u'level': u'btrfsraid6',
                u'marknewdriveashotspare': u'0',
                u'mounted': True,
                u'name': u'RAID6',
                u'numdevices': 5,
                u'percentage': 14,
                u'recoverymode': u'manual',
                u'scrubstatus': {u'bytesscrubbed': u'0.00B',
                                u'correctederrors': -1,
                                u'duration': u'',
                                u'errordetails': u'',
                                u'errors': 0,
                                u'running': False,
                                u'starttime': u'',
                                u'uncorrectableerrors': -1,
                                u'unverifiederrors': -1},
                u'size': 30005875630080,
                u'slotnumbers': [u'0', u'2', u'3', u'4', u'5'],
                u'smallestDeviceSize': u'6001175126016',
                u'state': u'rebuilding (/dev/sdd)',
                u'used': u'4.29 TB',
                u'uuid': u'8e8002a8-1d16-4b76-b160-2db90f735bba'}],
            u'total': 1}
        """
        resp = self.send_request('BtrfsRaid', 'getList', {"start":0, "limit":25, "sortfield":"name", "sortdir":"ASC"})
        print pformat(resp)
        self.log.debug(pformat(resp))
        num = resp.get('total')
        if num == 0:
            return None
        else:
            data = resp.get('data')
            return num, data

    def get_raid_candidates(self):  # not finish yet, need to support specific uuid
        resp = self.get_available_btrfs_raid_list()[1][0]
        if resp:
            return [str(item) for item in resp.get('devices')]

    def get_raid_uuid(self):
        resp = self.get_available_btrfs_raid_list()
        if resp:
            return [str(item['uuid']) for item in resp[1] if item.get('uuid')]

    def get_mounted_devices(self):
        """
        Returns:
            {u'available': 18000288350208,
            u'description': u'RAID6 (18.00 TB available)',
            u'devicefile': u'/dev/sdd',
            u'label': u'RAID6',
            u'size': 18003525378048,
            u'uuid': u'c64fa119-a4a7-4cf0-b77b-e89d9cd1f0e1'}
        """
        resp = self.send_request('BtrfsSubvolumes', 'getMountedDevices', {})
        print pformat(resp)
        self.log.debug(pformat(resp))
        if resp:
            return resp[0]
        else:
            self.log.warning('No mounted devices on Grack Platform !!!')

    def create_raid(self, raidname, raidlevel, devices):
        """
        Args:
            raidname:   raid5
            level:      btrfsraid5
            devices:    /dev/sdc,/dev/sdd,/dev/sde
        """
        self.log.info('Start to create RAID: RAID name - {0}, RAID level - {1}, RAID devices - {2}'
                      .format(raidname, raidlevel, devices))
        resp = self.send_request('BtrfsRaid', 'create', {"name":raidname, "level":raidlevel, "devices":devices})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

    def mount_raid(self, uuid):
        """
        Args:
            uuid:   751892e2-57ea-4e8a-9c0b-eb03f2fb77a4 (call the "BtrfsRaid::getList" to get RAID UUID)
        """
        self.log.info('Start to mount RAID: {}'.format(uuid))
        resp = self.send_request('BtrfsRaid', 'mountNormal', {"uuid":uuid})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

    def unmount_raid(self, uuid):
        """
        Args:
            uuid:   751892e2-57ea-4e8a-9c0b-eb03f2fb77a4 (call the "BtrfsRaid::getList" to get RAID UUID)
        """
        self.log.info('Start to umount RAID: {}'.format(uuid))
        resp = self.send_request('BtrfsRaid', 'umountByDir', {"uuid":uuid, "clearFstabEntry":True})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

    def umount_all_raid(self):
        mount_devices = self.get_mounted_devices()
        uuid_lists = [str(item['uuid']) for item in mount_devices]
        for item in uuid_lists:
            self.unmount_raid(item)
            time.sleep(5)

    def delete_raid(self, uuid):
        """
        Args:
            uuid:   751892e2-57ea-4e8a-9c0b-eb03f2fb77a4 (call the "BtrfsRaid::getList" to get RAID UUID)
        """
        self.log.info('Start to delete RAID: {}'.format(uuid))
        resp = self.send_request('BtrfsRaid', 'delete', {"uuid":uuid})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

    def shrink_drive_from_RAID_set(self, uuid, devices):
        """
        Args:
            uuid:       751892e2-57ea-4e8a-9c0b-eb03f2fb77a4 (call the "BtrfsRaid::getList" to get RAID UUID)
            devices:    /dev/sdd
        """
        self.log.info('Start to shrink RAID {} with {} drive'.format(uuid, devices))
        resp = self.send_request('BtrfsRaid', 'removeSlaves', {"uuid":uuid, "devices":devices})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

    def grow_drive_from_RAID_set(self, uuid, devices):
        """
        Args:
            uuid:       751892e2-57ea-4e8a-9c0b-eb03f2fb77a4 (call the "BtrfsRaid::getList" to get RAID UUID)
            devices:    /dev/sdd
        """
        self.log.info('Start to grow RAID {} with {} drive'.format(uuid, devices))
        resp = self.send_request('BtrfsRaid', 'add', {"uuid":uuid, "devices":devices})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

    def add_hot_spare(self, uuid, devices):
        """
        Args:
            uuid:       751892e2-57ea-4e8a-9c0b-eb03f2fb77a4 (call the "BtrfsRaid::getList" to get RAID UUID)
            devices:    /dev/sdd
        """
        self.log.info('Start to add hot spare drive {} in RAID {}'.format(devices, uuid))
        resp = self.send_request('BtrfsRaid', 'setHotSpares', {"uuid":uuid, "devices":devices})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

    def add_workspace(self, name, raidpath, permission="777", comment="auto_test"):
        """
        Args:
            name:       test (The name of the workspaces)
            devices:    /dev/sdd (The device to be used)
            permission: "700","750","755","770","775","777"
            comment:    auto_test (The comment of the workspaces)
        """
        self.log.info('Start to add workspace: {}, RAID path - {}'.format(name, raidpath))
        resp = self.send_request('Workspaces', 'set', {"sharedfolderUUID":"undefined", "name":name, "devicefile":raidpath,
                                                       "is_compressed":False, "mode":permission, "comment":comment,
                                                       "uuid":"undefined"})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

    def delete_workspace(self, subvuuid):
        self.log.info('Start to delete workspace: {}'.format(subvuuid))
        workspace_list = self.get_workspace_list()[1]
        deviceUUID = [item['deviceUUID'] for item in workspace_list if item.get('uuid') == subvuuid][0]
        shareUUID = [item['sharedfolder'].get('uuid') for item in workspace_list if item.get('uuid') == subvuuid][0]
        snapshot_num = [item['is_snapshot'] for item in workspace_list if item.get('uuid') == subvuuid][0]
        if int(snapshot_num) > 0:
            is_snapshot = True
        else:
            is_snapshot = False
        resp = self.send_request('Workspaces', 'delete',
                                 {"subvUUID":subvuuid, "deviceUUID":deviceUUID, "sharedfolderUUID":shareUUID,
                                  "recursive":False, "mounted":True, "isSnapshot":is_snapshot})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

    def get_workspace_list(self):
        """
        Returns:
             [{u'_referenced': True,
               u'_used': False,
               u'available': 48008184463360,
               u'created': u'2018-07-07 00:59:33 -0700',
               u'deviceUUID': u'41528393-30c4-47d3-ad6d-111aaf842d80',
               u'devicefile': u'/dev/sdf',
               u'flags': u'-',
               u'is_compressed': False,
               u'is_readonly': False,
               u'is_root': False,
               u'is_snapshot': u'0',
               u'mntDir': u'/media/1956b755-2f92-d348-acf1-60ccd253b109',
               u'mntentref': u'44866bac-6bbc-454a-be12-1b2351f1898f',
               u'mounted': True,
               u'name': u'dsgsd',
               u'parentId': 5,
               u'parentPath': u'',
               u'parentUuid': u'-',
               u'path': u'dsgsd',
               u'raidSize': 48009401008128,
               u'sharedfolder': {u'_used': False,
                                 u'comment': u'',
                                 u'description': u'dsgsd [on grackraid5, dsgsd/]',
                                 u'mntent': {u'devicefile': u'/dev/sdh',
                                             u'dir': u'/media/1956b755-2f92-d348-acf1-60ccd253b109',
                                             u'fsname': u'41528393-30c4-47d3-ad6d-111aaf842d80',
                                             u'opts': u'autodefrag,nospace_cache,degraded,defaults,nofail,noatime,nodiratime,metadata_ratio=8,subvol=dsgsd',
                                             u'posixacl': True,
                                             u'type': u'btrfs'},
                                 u'mntentref': u'44866bac-6bbc-454a-be12-1b2351f1898f',
                                 u'name': u'dsgsd',
                                 u'privileges': u'',
                                 u'reldirpath': u'dsgsd/',
                                 u'uuid': u'00a482e3-c1de-47c8-b290-fcced43147d1',
                                 u'volume': u'grackraid5'},
               u'snapshots': [],
               u'subvolumeID': 262,
               u'totalLimit': u'-',
               u'uuid': u'1956b755-2f92-d348-acf1-60ccd253b109',
               u'volume': u'grackraid5'}])
        """
        resp = self.send_request('Workspaces', 'getList', {"start":0, "limit":25, "sortfield":"name", "sortdir":"ASC"})
        print pformat(resp)
        self.log.debug(pformat(resp))
        num = resp.get('total')
        if num == 0:
            return None
        else:
            data = resp.get('data')
            return num, data

    def get_workspace_uuid(self):
        resp = self.get_workspace_list()
        if resp:
            workspace_list = [str(item['uuid']) for item in resp[1]]
            return workspace_list
        else:
            self.log.warning('No workspace exist !!')
            return None

    def get_disks_info(self):
        resp = self.send_request('DiskMgmt', 'getList', {"start":0, "limit":50, "sortfield":"slotnumber", "sortdir":"ASC"})
        print pformat(resp)
        self.log.debug(pformat(resp))
        num = resp.get('total')
        if num == 0:
            return None
        else:
            data = resp.get('data')
            return num, data

    def get_free_device_name_list(self):
        resp = self.get_disks_info()[1]
        device_list = [str(item['devicefile']) for item in resp if not item.get('israidset')
                       and item.get('status') == 'OK' and item.get('vendor') == 'ATA']
        OS_drive = ['/dev/sda', '/dev/sdb']
        return list(set(device_list) - set(OS_drive))  # Remove OS drive in the list

    def check_hot_spare_info(self, uuid):
        """
        Returns:
            {u'data': [{u'description': u'HGST HUS726060AL [/dev/sdg, 6.00 TB]',
                        u'devicefile': u'/dev/sdg',
                        u'hotspare': True,
                        u'serialnumber': u'K1J4JKVD',
                        u'size': u'6001175126016',
                        u'slotnumber': u'3',
                        u'vendor': u'ATA'},
                       {u'description': u'HGST HUS726060AL [/dev/sdh, 6.00 TB]',
                        u'devicefile': u'/dev/sdh',
                        u'hotspare': True,
                        u'serialnumber': u'K1J4NDND',
                        u'size': u'6001175126016',
                        u'slotnumber': u'4',
                        u'vendor': u'ATA'},
                       {u'description': u'HGST HUS726060AL [/dev/sdi, 6.00 TB]',
                        u'devicefile': u'/dev/sdi',
                        u'hotspare': False,
                        u'serialnumber': u'K1J4YZVD',
                        u'size': u'6001175126016',
                        u'slotnumber': u'5',
                        u'vendor': u'ATA'},
                       {u'description': u'HGST HUS726060AL [/dev/sdj, 6.00 TB]',
                        u'devicefile': u'/dev/sdj',
                        u'hotspare': False,
                        u'serialnumber': u'K1J4JGBD',
                        u'size': u'6001175126016',
                        u'slotnumber': u'6',
                        u'vendor': u'ATA'},
                       {u'description': u'HGST HUS726060AL [/dev/sdo, 6.00 TB]',
                        u'devicefile': u'/dev/sdo',
                        u'hotspare': False,
                        u'serialnumber': u'K1J4V6TD',
                        u'size': u'6001175126016',
                        u'slotnumber': u'11',
                        u'vendor': u'ATA'}],
             u'total': 5}
        Args:
            uuid:       751892e2-57ea-4e8a-9c0b-eb03f2fb77a4 (call the "BtrfsRaid::getList" to get RAID UUID)
        """
        resp = self.send_request('BtrfsRaid', 'getCandidates', {"uuid":uuid, "skipHotSpareDrives":False, "start":0,
                                                                "limit":25, "sortfield":"slotnumber", "sortdir":"ASC"})
        print pformat(resp)
        self.log.debug(pformat(resp))
        num = resp.get('total')
        if num == 0:
            return None
        else:
            data = resp.get('data')
            return num, data

    def reset_to_factory_settings(self):
        resp = self.send_request('SystemSnapshotsMgmt', 'rollbackToFactory', {})
        print pformat(resp)
        self.log.debug(pformat(resp))

    def add_user(self, username, comment="", email="", userpassword='Test1234', groups=[], sshpubkeys=[]):
        """
        Args:
            username:       testuser (The name of the user)
            comment:        (The comment of the user)
            email:          (The users email address)
            userpassword:   Test1234 (password with verification)
            groups:         (A list of groups which the user is a member of as an array of strings)
            sshpubkeys:     (The users SSH public keys)
        """
        resp = self.send_request('UserMgmt', 'setUser', {"edit":False, "name":username, "comment":comment, "email":email,
                                                         "password":userpassword, "shell":"/bin/dash",
                                                         "disallowusermod":False, "groups":groups, "sshpubkeys":sshpubkeys})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

    def enable_iscsi_service(self):
        resp = self.send_request('iSCSISCST', 'setSettings', {"enable":True})
        self.log.debug(pformat(resp))
        return resp

    def check_iscsi_connection_status(self):
        """
        Returns:
            {u'data': [{u'iqn': u'iqn.2018-04.grack12:winnie123',
                        u'uuid': u'af36c99f-d2e6-4183-be8a-f1ebf9fbaa45'},
                       {u'iqn': u'iqn.2018-04.grack12:winnie456',
                        u'uuid': u'0714f292-54a4-4e71-9f2d-e7680d772807'}],
             u'total': 2}
        """
        resp = self.send_request('iSCSISCST', 'getTargetList', {"start":0,"limit":25,"sortfield":"iqn","sortdir":"ASC"})
        print pformat(resp)
        self.log.debug(pformat(resp))
        num = resp.get('total')
        if num == 0:
            return None
        else:
            data = resp.get('data')
            return num, data

    def add_iscsi_connection(self, targetname, devicefile, lunsize=1000000, username='admin', password='Test12345678',
                             queuedcommands=128, initialr2t=True, immediatedata=True, headerdigest=False,
                             datadigest=False, maxconnections=1, maxrecvdatasegmentlength=1048576,
                             maxxmitdatasegmentlength=65536, maxburstlength=524288, firstburstlength=65536,
                             defaulttime2wait=0, defaulttime2retain=0, maxoutstandingr2t=1, datapduinorder=True,
                             datasequenceinorder=True, errorrecoverylevel=0, ofmarker=False, ifmarker=False,
                             ofmarkint=2048, ifmarkint=2048, rsptimeout=90, nopininterval=30, nopintimeout=30):
        """
        Args:
            targetname: unique_name (The name of the iSCSI target)
            devicefile: The device to be used. (call the " BtrfsSubvolumes:: getMountedDevices " to get devicefile)
            lunsize:    LUN Size, Units - TB. File size for the first LUN.
            username:   Optional attribute containing username for incoming user name.
            password:   Optional attribute containing user password for incoming user name. Password must be at least 12 characters.
            queuedcommands: Defines maximum number of commands queued to any session of this target. Default is 32 commands.
            initialr2t: true or false, turns on the default use of R2T;
                        if disabled, allows an initiator to start sending data to a target as if it had received an initial R2T.
                        The result function is OR.
            immediatedata:  true or false, Configure using of unsolicited data.
                            The result function is AND.
            headerdigest:   false: "None", true: "CRC-32C"
            datadigest:     false: "None", true: "CRC-32C"
            maxconnections: The maximum number of connections that can be requested or are acceptable.
                            The result function is Min.
            maxrecvdatasegmentlength:   The maximum amount of data that the target can receive in any iSCSI PDU.
                                        This is a connection- and direction- specific parameter.
                                        The actual value used for targets will be Min (This value, MaxBurstLength) for data-in and solicited data-out data.
                                        Min (This value, FirstBurstLength) for unsolicited data.
            maxxmitdatasegmentlength:   The maximum amount of data that the target can transmit in any iSCSI PDU.
                                        This is a connection- and direction- specific parameter.
                                        The actual value used for targets will be Min (This value, MaxBurstLength) for data-in and solicited data-out data.
                                        Min (This value, FirstBurstLength) for unsolicited data.
            maxburstlength: Maximum SCSI data payload in bytes for data-in or for a solicited data-out sequence.
                            The responder's number is used.
                            The result function is Min.
            firstburstlength:   Maximum SCSI payload, in bytes, of unsolicited data an initiator may send to the target.
                                Includes immediate data and a sequence of unsolicited Data-Out PDUs. Must be <= MaxBurstLength.
                                The result function is Min.
            defaulttime2wait:   Min seconds to wait before attempting connection and task allegiance reinstatement after a connection termination or a connection reset.
                                The results function is Max.
                                A value of zero means that task reassignment can be done immediately.
                                Also known as Time2Wait.
            defaulttime2retain: Max seconds that connection and task allegiance reinstatement is still possible following a connection termination or reset.
                                The results function is Min.
                                Zero means no reinstatement is possible.
                                Also known as Time2Retain.
            maxoutstandingr2t:  The maximum number of outstanding R2Ts. The responder's value is used.
                                The result function is Min.
            datapduinorder:     true or false
            datasequenceinorder:true or false
            errorrecoverylevel: Recovery levels represent a combination of recovery capabilities.
                                Each level includes all the capabilities of the lower recovery level.
                                The result function is Min.
            ofmarker:   true or false
            ifmarker:   true or false
            ofmarkint:  The interval value (in 4-byte words) for initiator-to-target markers, measured from the end of one marker to the beginning of the next.
                        The offer can have only a range; the response can have only a single value (picked from the offered range) or Reject.
            ifmarkint:  Interval value (in 4-byte words) for target-to- initiator markers.
                        The interval is measured from the end of one marker to the beginning of the next one.
                        The offer can have only a range; the response can have only a single value (picked from the offered range) or Reject.
            rsptimeout: Defines the maximum time in seconds a command can wait for response from initiator, otherwise the corresponding connection will be closed.
                        Default is 90 seconds.
            nopininterval:  Defines interval between NOP-In requests, which the target will send on idle connections to check if the initiator is still alive.
                            If there is no NOP-Out reply from the initiator in NopInTimeout seconds, the corresponding connection will be closed.
                            Default is 30 seconds. If it's set to 0, then NOP-In requests are disabled.
            nopintimeout:   Defines the maximum time in seconds a NOP-In request can wait for response from initiator, otherwise the corresponding connection will be closed.
                            Default is 30 seconds.
        """
        resp = self.send_request('iSCSISCST', 'createTargetAndLUN', {"name":targetname, "devicefile":devicefile,
                                                                     "filesize":lunsize, "username":username,
                                                                     "password":password, "queuedcommands":queuedcommands,
                                                                     "initialr2t":initialr2t, "immediatedata":immediatedata,
                                                                     "headerdigest":headerdigest, "datadigest":datadigest,
                                                                     "maxconnections":maxconnections,
                                                                     "maxrecvdatasegmentlength":maxrecvdatasegmentlength,
                                                                     "maxxmitdatasegmentlength":maxxmitdatasegmentlength,
                                                                     "maxburstlength":maxburstlength,
                                                                     "firstburstlength":firstburstlength,
                                                                     "defaulttime2wait":defaulttime2wait,
                                                                     "defaulttime2retain":defaulttime2retain,
                                                                     "maxoutstandingr2t":maxoutstandingr2t,
                                                                     "datapduinorder":datapduinorder,
                                                                     "datasequenceinorder":datasequenceinorder,
                                                                     "errorrecoverylevel":errorrecoverylevel,
                                                                     "ofmarker":ofmarker,
                                                                     "ifmarker":ifmarker, "ofmarkint":ofmarkint,
                                                                     "ifmarkint":ifmarkint,
                                                                     "rsptimeout":rsptimeout, "nopininterval":nopininterval,
                                                                     "nopintimeout":nopintimeout, "uuid":"undefined"})
        print pformat(resp)
        self.log.debug(pformat(resp))
        return resp

if __name__ == '__main__':
    gtech_obj = GTechRPCAPI(uut_ip='10.92.234.65', username='admin', password='gtech', root_password='gtech')

