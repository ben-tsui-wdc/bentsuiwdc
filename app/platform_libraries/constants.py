""" Constants variables of automation framework.
"""


class GetableCollection(object):
    @classmethod
    def has_key(cls, key, case_sensitive=False):
        if not case_sensitive:
            key = key.upper()
        return key in dir(cls)

    @classmethod
    def get(cls, key, default=None, case_sensitive=False):
        if not case_sensitive:
            key = key.upper()
        return getattr(cls, key, default)


# Currently INVENTORY_SERVER_TW ip is sevtw-inventory-server.hgst.com:8010/InventoryServer
INVENTORY_SERVER_TW = 'http://sevtw-inventory-server.hgst.com:8010/InventoryServer'
# Currently LOGSTASH_SERVER_TW ip is 10.92.234.101:8000
LOGSTASH_SERVER_TW = 'http://10.92.234.101:8000'

FILESERVER_TW_CORPORATE = 'fileserver.hgst.com'
FILESERVER_TW_MVWARRIOR = '10.200.141.26'

SSH_KEY = '/root/app/platform_libraries/ssh_cert/id_ecdsa'


class Kamino(GetableCollection):
    ADB_PORT = '5555'
    MOUNT_PATH = '/mnt/media_rw/'
    USER_ROOT_PATH = '/data/wd/diskVolume0/restsdk/userRoots/'

    class MimeType(GetableCollection):
        FOLDER = 'application/x.wd.dir'


class KDP(GetableCollection):
    USER_ROOT_PATH = '/data/wd/diskVolume0/userStorage'  # Since RestSDK #2.11.0-1863, revise for Live File System
    APP_ROOT_PATH = '/data/wd/diskVolume0/kdpappmgr/appStore'
    MOUNT_PATH = '/mnt/USB/'
    SHARES_PATH = '/shares/'
    SMB_CONF_PATH = '/etc/samba/smb.conf'
    SHADOW_CONF_PATH = '/etc/shadow'
    GROUP_CONF_PATH = '/etc/group'
    PASSWD_CONF_PATH = '/etc/passwd'
    SMB_PASSWD_CONF_PATH = '/etc/samba/smbpasswd'

    DEFAULT_BUCKET_ID_V2 = {
        "monarch2": {
            "dev1": "67009d90-b48f-11ed-943a-89e50809092e",
            "qa1": "de070800-b54f-11ed-b009-f943b1ab94b7",
        },
        "pelican2": {
            "dev1": "08cdd0b0-b49b-11ed-9cb2-27684d58fd26",
            "qa1": "80e89cc0-b6d9-11ed-9697-1b5df4de8143",
        },
        "yodaplus2": {
            "dev1": "26a8f480-b49f-11ed-84f5-15629f4b0d80",
            "qa1": "fa926510-b6d9-11ed-9697-1b5df4de8143",
        },
        "monarch": {
            "dev1": "a0c98890-b4a1-11ed-84f5-15629f4b0d80",
            "qa1": "1b79e2d0-b54f-11ed-b009-f943b1ab94b7",
        },
        "pelican": {
            "dev1": "0f27b060-b4ab-11ed-963d-6d8b79dbc130",
            "qa1": "2990ec50-b6db-11ed-9697-1b5df4de8143",
        },
        "yodaplus": {
            "dev1": "c574d910-b4ab-11ed-963d-6d8b79dbc130",
            "qa1": "b8751f90-b6db-11ed-9697-1b5df4de8143",
        }
    }

    SPECIAL_BUCKET_ID_V2 = {
        "monarch2": {
            "dev1": "24cc4220-e4ab-11ed-963b-dddf07c291e5",
        },
        "pelican2": {
            "dev1": "8cfbdbd0-e4ab-11ed-963b-dddf07c291e5",
        },
        "yodaplus2": {
            "dev1": "fd05a6e0-e4ab-11ed-963b-dddf07c291e5",
        },
        "monarch": {
            "dev1": "a0c69c10-e4a9-11ed-963b-dddf07c291e5",
        },
        "pelican": {
            "dev1": "0e0c3e10-e4aa-11ed-963b-dddf07c291e5",
        },
        "yodaplus": {
            "dev1": "856ed580-e4aa-11ed-963b-dddf07c291e5",
        }
    }

    DEFAULT_BUCKET_V2_START_VERSION = {
        "monarch2": "8.0.0-245",
        "pelican2": "8.0.0-245",
        "yodaplus2": "8.0.0-245",
        "monarch": "7.16.0-220",
        "pelican": "7.16.0-220",
        "yodaplus": "7.16.0-220"
    }

    DEFAULT_BUCKET_ID = {
        "monarch2": {
            "ota_default_bucket_dev1": "c8efa8f0-a2d7-11eb-8a73-9346ee0341a1",
            "ota_default_bucket_qa1": "591978b0-a3e2-11eb-93e4-6b32b36aeb9c",
        },
        "pelican2": {
            "ota_default_bucket_dev1": "78632ae0-a2d9-11eb-8920-97ececed63c1",
            "ota_default_bucket_qa1": "2a611040-a3e3-11eb-93e4-6b32b36aeb9c",
        },
        "yodaplus2": {
            "ota_default_bucket_dev1": "e5f300b0-ba50-11eb-86f5-b70fa1017eba",
            "ota_default_bucket_qa1": "7fa77b30-ba4e-11eb-9965-93a1794a6758",
        }
    }
    MIGRATION_BUCKET_ID = {
        'monarch2': 'd1e61630-91b4-11eb-91dc-334e6404ab35',
        'pelican2': '2fe5f5c0-91b5-11eb-91dc-334e6404ab35',
        'yodaplus2': '7af06650-ba4f-11eb-9965-93a1794a6758'
    }
    DATA_VOLUME_PATH = {
        'monarch2': '/data/wd/diskVolume0',
        'pelican2': '/data/wd/diskVolume0',
        'yodaplus2': '/data/wd/diskVolume0',
        'rocket': '/Volume1',
        'drax': '/Volume1'
    }

    LOG_EVENT_URL = {
        'monarch2_qa1': 'https://staging-gateway.dev.wdckeystone.com/logreceiver/receiver/v1/http/3068b0f2-9f4e-41c0-b842-2200930eb689',
        'pelican2_qa1': 'https://staging-gateway.dev.wdckeystone.com/logreceiver/receiver/v1/http/3068b0f2-9f4e-41c0-b842-2200930eb689',
        'yodaplus2_qa1': 'https://staging-gateway.dev.wdckeystone.com/logreceiver/receiver/v1/http/3068b0f2-9f4e-41c0-b842-2200930eb689',
    }

    LOG_UPLOAD_URL = {
        'monarch2_qa1': 'https://staging-gateway.dev.wdckeystone.com/logreceiver/receiver/v1/http/3a82fdad-363f-4397-a971-811231b1c22d',
        'pelican2_qa1': 'https://staging-gateway.dev.wdckeystone.com/logreceiver/receiver/v1/http/1eab85b3-bd60-4e0c-b47e-c59664b37391',
        'yodaplus2_qa1': 'https://staging-gateway.dev.wdckeystone.com/logreceiver/receiver/v1/http/83339a7c-b22c-43ac-ba52-729ed58a08b3',
    }
    # led power duty rate
    PWM_DUTY_RATE_PATH = {
        'monarch2': '/sys/devices/platform/980070d0.pwm/dutyRate3',
        'pelican2': '/sys/devices/platform/980070d0.pwm/dutyRate0',
        'yodaplus2': '/sys/devices/platform/980070d0.pwm/dutyRate1',
    }
    

    class SystemLog(GetableCollection):
        AnalyticPublic = "/var/log/analyticpublic.log"
        AnalyticPrivate = "/var/log/analyticprivate.log"


class Test(GetableCollection):
    PASSED = 'PASSED'
    FAILED = 'FAILED'
    SKIPPED = 'SKIPPED'
    NOTEXCUTED = 'NOTEXCUTED'


class GlobalConfigService(GetableCollection):
    DEV1 = 'https://dev1.wdtest1.com'
    DEV1_V2 = 'https://dev1-config.wdtest1.com'
    DEV2 = 'http://dev2-config.remotewd1.com'
    QA1 = 'https://qa1.wdtest1.com'
    QA1_V2 = 'https://qa1-config.wdtest1.com'
    QA2 = 'http://qa2-config.remotewd1.com'
    PROD = 'https://config.mycloud.com'
    PROD_V2 = 'https://ibiconfig.mycloud.com'
    BETA = 'https://betamch-config2.mycloud.com'

    @classmethod
    def get(cls, key, default=None, version=None, case_sensitive=False):
        if version:
            key = key + '_' + version
        return super(GlobalConfigService, cls).get(key, default, case_sensitive)


class ClientID(GetableCollection):

    class DEV1(GetableCollection):
        AUTOMATION = "automation"
        ADMIN = "XqjXLxCuyonffQMawad72CMKHDDoRHUl" # deprecated
        MOBILE_APP = "apUETfOvu3cMATAn6ITVhTtYz5zFIdaN"

    class DEV2(GetableCollection):
        MOBILE_APP = "U565nA5QOg6xpDwGM2iat1Pyjo4pNQZq"

    class QA1(GetableCollection):
        AUTOMATION = "automation"
        ADMIN = "5QFotlSvxKgaHzwPZRtrrL7djt1RSgIb" # deprecated
        MOBILE_APP = "S9iny0HblP9NFfXAFUORozxvSmrWgF17"

    class QA2(GetableCollection):
        MOBILE_APP = "WTv9VgVTd77BUjVyCLn6YSlTvkIngs8W"

    class PROD(GetableCollection):
        AUTOMATION = "ota_management"
        ADMIN = "9wHbY7khMK7kGbE8kBYJkPsF5W84gchg"
        MOBILE_APP = "56pjpE1J4c6ZyATz3sYP8cMT47CZd6rk"
        RSDK_TEST = "rsdk_test"


class ClientSecret(GetableCollection):

    class DEV1(GetableCollection):
        AUTOMATION = "f*(d9Dzh5@MxwK&u"
        ADMIN = "975w-RcuXiGQ7u62b6X1jMsI_J_EOxhlGa7m8uXyHmfKO823QIblP0hdt5iRPcD7" # deprecated
        MOBILE_APP = "aza8-nw1RReYNg8eGLD4LVjj_feYeFxbhlioWlyHe-AdwgJf2wjtHtySQW7t0yB6"

    class DEV2(GetableCollection):
        MOBILE_APP = "pAeaefGhVR5iSsa5sxLJsG1_6cs1qpNpcE4zf4VW_AgTswZWs3qLs8hoqzl8MwxJ"

    class QA1(GetableCollection):
        AUTOMATION = "QEA64Za93rJR8rdhgndtG374"
        ADMIN = "SfRMT8AWWjoGbR9qdvRzBqI7HkOvpK9CyLndqVB-tNETZ1yhcISxl-QNjUJ9y1a5" # deprecated
        MOBILE_APP = "4r5vtJZaGcM7d7o6FyDGkKCY7lYHmVyniB3xS0Z6hzv3uAKaaOEysBfVwbevfN1a"

    class QA2(GetableCollection):
        MOBILE_APP = "zZmQBHPQTIsjC7jLFo4eCBC3RqWulPLP5b3YIJKDemBwZvCWXkDvh7l2THtKfVqy"

    class PROD(GetableCollection):
        AUTOMATION = "n8ZDA]pm9azuo2hnR^[FPyzBv=7]8eUU"
        ADMIN = "8PBjBR68GEVajin-2qXYGRzgfZNV8E74lJc_-Dg-W1YPc4ayh8lG0O4Sksf3QhS7"
        MOBILE_APP = "yvjwlbIHLbFazC_dah3UPiFqg746W58lwKn04nnv0u5Tk2-hrMCyjpuNmWD1CcvY"
        RSDK_TEST = "Dpb;FCtRz3J6)tLtUA,w6;4crVMUX?2w"


class Godzilla(GetableCollection):
    USER_ROOT_PATH = '/mnt/HD/HD_a2/restsdk-data/userRoots/'
    MOUNT_PATH = '/mnt/USB/'
    RESTSDK_CONFIG_PATH = '/usr/local/modules/restsdk/etc/restsdk-server.toml'
    # Device information
    DEVICE_INFO = {
        "PR2100": {
            'platform': 'Intel',
            'name': "BryceCanyon",
            'disk': 2,
            'raid': ['jbod', 'spanning', 'raid0', 'raid1'],
            "ota_default_bucket_dev1": "25ad58b0-caf0-11e9-a793-7d6245c495eb",
            "ota_default_bucket_qa1": "4e91aeb0-e577-11e9-ae34-0720faebcf80",
            "ota_default_bucket_prod": "e290c220-d1cd-11ea-9fec-7bc9107f16ae",
            "ota_special_bucket_qa1": "9fab3390-6342-11ea-b352-29935ff01f3b",
            "ota_default_bucket_v2_start_version": "5.17.107",
            "ota_default_bucket_v2_dev1": "75c13ca0-b3ee-11ed-af82-5118b3e57328",
            "ota_special_bucket_v2_dev1": "15870a00-e4ad-11ed-963b-dddf07c291e5",
            "ota_default_bucket_v2_qa1": "1c1a5780-b6ce-11ed-8d19-ddcdeb3ffbed",
            "ota_special_bucket_v2_qa1": "bfb7d020-c998-11ed-a999-b357abf00bc3",
            "os3_fw_name": "PR2100",
            "ota_name": "bbcl"
        },
        "PR4100": {
            'platform': 'Intel',
            'name': "BlackCanyon",
            'disk': 4,
            'raid': ['jbod', 'spanning', 'raid0', 'raid1', 'raid5', 'raid10'],
            "ota_default_bucket_dev1": "1e4f47b0-e574-11e9-bf8c-fb439b9c1485",
            "ota_default_bucket_qa1": "92771f20-e577-11e9-ae34-0720faebcf80",
            "ota_default_bucket_prod": "4fcf1120-d1ce-11ea-9fec-7bc9107f16ae",
            "ota_special_bucket_qa1": "806a4bf0-6343-11ea-b352-29935ff01f3b",
            "ota_default_bucket_v2_start_version": "5.17.107",
            "ota_default_bucket_v2_dev1": "8841b680-b3d4-11ed-af14-4d0cae512157",
            "ota_special_bucket_v2_dev1": "b2af1580-e4ac-11ed-963b-dddf07c291e5",
            "ota_default_bucket_v2_qa1": "79940c90-b6cd-11ed-8d19-ddcdeb3ffbed",
            "ota_special_bucket_v2_qa1": "6434f0c0-c993-11ed-bc6f-f5175d2ba537",
            "os3_fw_name": "PR4100",
            "ota_name": "bnfa"
        },
        "EX2100": {
            'platform': 'Arm',
            'name': "Yosemite",
            'disk': 2,
            'raid': ['jbod', 'spanning', 'raid0', 'raid1'],
            "ota_default_bucket_dev1": "86eb6790-cb2e-11ea-b4e3-a361ec6fffa2",
            "ota_default_bucket_qa1": "d30ab260-cb2a-11ea-bf94-8df94358c6de",
            "ota_default_bucket_prod": "",
            "ota_special_bucket_qa1": "aa190670-fe35-11ea-a8aa-c96349570e60",
            "ota_default_bucket_v2_start_version": "5.00.194",
            "ota_default_bucket_v2_dev1": "254c83f0-b3fe-11ed-bc31-c3cdb0af50d1",
            "ota_special_bucket_v2_dev1": "62e38b90-e4b0-11ed-963b-dddf07c291e5",
            "ota_default_bucket_v2_qa1": "c5176f10-b6d5-11ed-aa65-f9afe65e2111",
            "ota_special_bucket_v2_qa1": "133085c0-c9a4-11ed-83ea-750bee114a0c",
            "os3_fw_name": "EX2100",
            "ota_name": "bwaz"
        },
        "EX4100": {
            'platform': 'Arm',
            'name': "Yellowstone",
            'disk': 4,
            'raid': ['jbod', 'spanning', 'raid0', 'raid1', 'raid5', 'raid10'],
            "ota_default_bucket_dev1": "ed039a90-46b6-11ea-9350-bfe689106738",
            "ota_default_bucket_qa1": "0ae75f10-6345-11ea-b352-29935ff01f3b",
            "ota_default_bucket_prod": "2c899130-d1cf-11ea-9fec-7bc9107f16ae",
            "ota_special_bucket_qa1": "3f04bdb0-6345-11ea-b352-29935ff01f3b",
            "ota_default_bucket_v2_start_version": "5.00.194",
            "ota_default_bucket_v2_dev1": "1484c420-b3f8-11ed-bc31-c3cdb0af50d1",
            "ota_special_bucket_v2_dev1": "a463a6b0-e4ae-11ed-963b-dddf07c291e5",
            "ota_default_bucket_v2_qa1": "d4decf80-b6d3-11ed-aa65-f9afe65e2111",
            "ota_special_bucket_v2_qa1": "d1a91f00-c9a2-11ed-83ea-750bee114a0c",
            "os3_fw_name": "EX4100",
            "ota_name": "bwze"
        },
        "Mirror": {
            'platform': 'Arm',
            'name': "GrandTeton",
            'disk': 2,
            'raid': ['jbod', 'spanning', 'raid0', 'raid1'],
            "ota_default_bucket_dev1": "a1d50340-46b8-11ea-9350-bfe689106738",
            "ota_default_bucket_qa1": "6e3cb660-6344-11ea-b352-29935ff01f3b",
            "ota_default_bucket_prod": "77ccb000-d1cf-11ea-9fec-7bc9107f16ae",
            "ota_special_bucket_qa1": "a9e75ee0-6344-11ea-b352-29935ff01f3b",
            "ota_default_bucket_v2_start_version": "5.00.194",
            "ota_default_bucket_v2_dev1": "f3435c20-b3f9-11ed-bc31-c3cdb0af50d1",
            "ota_special_bucket_v2_dev1": "2f682ec0-e4af-11ed-963b-dddf07c291e5",
            "ota_default_bucket_v2_qa1": "6014a0c0-b6d4-11ed-aa65-f9afe65e2111",
            "ota_special_bucket_v2_qa1": "35ab3ba0-c9a3-11ed-83ea-750bee114a0c",
            "os3_fw_name": "BWVZ",
            "ota_name": "bwvz"
        },
        "EX2Ultra": {
            'platform': 'Arm',
            'name': "RangerPeak",
            'disk': 2,
            'raid': ['jbod', 'spanning', 'raid0', 'raid1'],
            "ota_default_bucket_dev1": "ad03ac40-46b7-11ea-9350-bfe689106738",
            "ota_default_bucket_qa1": "cd393ae0-6343-11ea-b352-29935ff01f3b",
            "ota_default_bucket_prod": "c6e97c00-d1ce-11ea-9fec-7bc9107f16ae",
            "ota_special_bucket_qa1": "0b681d40-6344-11ea-b352-29935ff01f3b",
            "ota_default_bucket_v2_start_version": "5.00.194",
            "ota_default_bucket_v2_dev1": "356f0b70-b3f6-11ed-bc31-c3cdb0af50d1",
            "ota_special_bucket_v2_dev1": "3825b0b0-e4ae-11ed-963b-dddf07c291e5",
            "ota_default_bucket_v2_qa1": "c8a1aea0-b6d2-11ed-aa65-f9afe65e2111",
            "ota_special_bucket_v2_qa1": "4114cef0-c99b-11ed-aa9d-2d7c292ba00e",
            "os3_fw_name": "BVBZ",
            "ota_name": "bvbz"
        },
        "DL2100": {
            'platform': 'Intel',
            'name': "Aurora",
            'disk': 2,
            'raid': ['jbod', 'spanning', 'raid0', 'raid1'],
            "ota_default_bucket_dev1": "6a478e70-cb2e-11ea-b4e3-a361ec6fffa2",
            "ota_default_bucket_qa1": "2d641f30-cb2b-11ea-bf94-8df94358c6de",
            "ota_default_bucket_prod": "",
            "ota_special_bucket_qa1": "9f6f1ae0-0a21-11ec-b42d-e7e94c045e69",
            "ota_default_bucket_v2_start_version": "5.00.194",
            "ota_default_bucket_v2_dev1": "419684a0-b3fb-11ed-bc31-c3cdb0af50d1",
            "ota_special_bucket_v2_dev1": "88bcaeb0-e4af-11ed-963b-dddf07c291e5",
            "ota_default_bucket_v2_qa1": "ed4e3140-b6d4-11ed-aa65-f9afe65e2111",
            "ota_special_bucket_v2_qa1": "849b35d0-c9a3-11ed-83ea-750bee114a0c",
            "os3_fw_name": "DL2100",
            "ota_name": "bbaz"
        },
        "DL4100": {
            'platform': 'Intel',
            'name': "Sprite",
            'disk': 4,
            'raid': ['jbod', 'spanning', 'raid0', 'raid1', 'raid5', 'raid10'],
            "ota_default_bucket_dev1": "521c4520-cb2e-11ea-b4e3-a361ec6fffa2",
            "ota_default_bucket_qa1": "567f3170-cb2b-11ea-bf94-8df94358c6de",
            "ota_default_bucket_prod": "",
            "ota_special_bucket_qa1": "336f22d0-0a22-11ec-b42d-e7e94c045e69",
            "ota_default_bucket_v2_start_version": "5.00.194",
            "ota_default_bucket_v2_dev1": "9d2f32c0-b3fc-11ed-bc31-c3cdb0af50d1",
            "ota_special_bucket_v2_dev1": "21baf130-e4b0-11ed-963b-dddf07c291e5",
            "ota_default_bucket_v2_qa1": "519a7640-b6d5-11ed-aa65-f9afe65e2111",
            "ota_special_bucket_v2_qa1": "cc940ba0-c9a3-11ed-83ea-750bee114a0c",
            "os3_fw_name": "DL4100",
            "ota_name": "bnez"
        },
        "Glacier": {
            'platform': 'Arm',
            'name': "Glacier",
            'disk': 1,
            'raid': ['standard'],
            "ota_default_bucket_dev1": "0a718f90-46b9-11ea-9350-bfe689106738",
            "ota_default_bucket_qa1": "6fb40610-cb2c-11ea-bf94-8df94358c6de",
            "ota_default_bucket_prod": "",
            "ota_special_bucket_qa1": "b452b630-fe36-11ea-a8aa-c96349570e60",
            "ota_default_bucket_v2_start_version": "5.17.107",
            "ota_default_bucket_v2_dev1": "4e8a2540-b3f1-11ed-af82-5118b3e57328",
            "ota_special_bucket_v2_dev1": "81897da0-e4ad-11ed-963b-dddf07c291e5",
            "ota_default_bucket_v2_qa1": "a202b560-b6d1-11ed-aa65-f9afe65e2111",
            "ota_special_bucket_v2_qa1": "c0fc2510-c99a-11ed-aa9d-2d7c292ba00e",
            "os3_fw_name": "GLCR",  # My_Cloud_GLCR_2.41.116.bin
            "ota_name": "glcr"
        },
        "Mirrorman": {
            'platform': 'Arm',
            'name': "Mirrorman",
            'disk': 1,
            'raid': ['standard'],
            "ota_default_bucket_dev1": "ec0e52f0-cb2d-11ea-b4e3-a361ec6fffa2",
            "ota_default_bucket_qa1": "bdab4860-cb2c-11ea-bf94-8df94358c6de",
            "ota_default_bucket_prod": "",
            "ota_special_bucket_qa1": "fb7465e0-fe36-11ea-a8aa-c96349570e60",
            "ota_default_bucket_v2_start_version": "5.17.107",
            "ota_default_bucket_v2_dev1": "e73633a0-b3f2-11ed-af82-5118b3e57328",
            "ota_special_bucket_v2_dev1": "d9de40d0-e4ad-11ed-963b-dddf07c291e5",
            "ota_default_bucket_v2_qa1": "3514b3d0-b6d2-11ed-aa65-f9afe65e2111",
            "ota_special_bucket_v2_qa1": "01112c90-c99b-11ed-aa9d-2d7c292ba00e",
            "os3_fw_name": "BAGX",  # WD_Cloud_BAGX_2.41.116.bin
            "ota_name": "bagx"
        }
    }

class RnD(GetableCollection):
    USER_ROOT_PATH = '/Volume1/userStorage'

    class UsbSlots(GetableCollection):
        ROCKET = 1
        DRAX = 1

    class DriveSlots(GetableCollection):
        ROCKET = 1
        DRAX = 2

    class Fans(GetableCollection):
        ROCKET = 0
        DRAX = 1

    SHARE_PATH = '/shares/'

class NasAdmin(GetableCollection):

    class Test(GetableCollection):
        IMPROPER_ID = "asdasflknfnw21"
        NOT_EXIST_ID = "d0000e00-f000-000f-0b69-60d884ab0f7b"
        NOT_EXIST_SPACE_ID = "ccaa35e0-05a0-4deb-a740-0c163f5e000d"
        NOT_EXIST_USER_ID = "6c360009-ddb8-4d8a-9b6f-2d2721e594f2"
