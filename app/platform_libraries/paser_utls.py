# -*- coding: utf-8 -*-
""" Tools for parsing data to Python objects.
"""

try:
    import common_utils
    log = common_utils.create_logger(log_name='ParsingUtils')
except Exception as e:
    import pyutils
    log = pyutils.PrintLogging(name='ParsingUtils')


# mdstat Parser - RnD

class MDInfo(dict):

    def __init__(self):
        self.update({
            'name': None,
            'personalities': None,
            'devices': [],
            'blocks': None,
            'totalDevicesInRAID': 0,
            'totalDevicesInUse': 0,
            'statusMessage': None,
            'progress': None
        })

class MDStat(dict): # {"md_name": MDIfo}

    def get_indexes(self):
        return [int(n[2:]) for n in self]

    ''' Fellow https://confluence.wdmv.wdc.com/pages/viewpage.action?pageId=91198954 '''
    def get_defined_state(self, md_name):
        md = self.get(md_name)
        if not md: return 'damaged'
        elif md['totalDevicesInRAID'] > md['totalDevicesInUse']: return 'degraded'
        elif md['statusMessage']:
            if 'recovery' in md['statusMessage']: return 'recovery'
            elif 'resync' in md['statusMessage']: return 'resync'
            elif 'reshape' in md['statusMessage']: return 'reshape'
        else: return 'clean'


def parse_mdstat(output_in_lines, ignored=[]):
    mdstat = MDStat()
    current_md = None
    for line in output_in_lines:
        line = line.strip()
        if line.startswith('md'):
            current_md = MDInfo()
            mdstat_raid_line_parser(current_md, line)
            if current_md['name'] in ignored: # ignore this md
                current_md = None
                continue
            mdstat[current_md['name']] = current_md
        elif current_md:
            if 'blocks' in line: mdstat_block_line_parser(current_md, line)
            elif line.startswith('['): mdstat_state_detail_parser(current_md, line)
        elif not line:
            current_md = None
    return mdstat

def mdstat_raid_line_parser(update_md, line):
    values = line.split(' ')
    update_md['name'] = values[0]
    update_md['personalities'] = values[3]
    for v in values[4:]:
        name, sub = v.split('[', 1)
        update_md['devices'].append({
            'nodeName': name,
            'roleNumber': int(sub.split(']', 1)[0])
        })

def mdstat_block_line_parser(update_md, line):
    values = line.split(' ')
    update_md['blocks'] = int(values[0])
    total = values[-2][1:-1].split('/')
    update_md['totalDevicesInRAID'] = int(total[0])
    update_md['totalDevicesInUse'] = int(total[1])

def mdstat_state_detail_parser(update_md, line):
    update_md['statusMessage'] = line
    for value in line.split(' '):
        if '%' in value: update_md['progress'] = value
    if not update_md['progress']: raise AssertionError('Not found progress message')

# mdstat Parser - RnD

class MDADM(dict):

    def __init__(self):
        return self.update({
            'information': {},
            'raidDevices': [],
            'path': None
        })

    def get_name(self):
        return self['path'].rsplit('/', 1).pop()

    def get_id(self):
        return int(self.get_name()[2:])

def parse_mdadm(output_in_lines):
    mdstat = MDADM()
    for line in output_in_lines:
        line = line.strip()
        if ' : ' in line:
            values = line.split(' : ')
            mdstat['information'][values[0]] = values[1]
        elif line.startswith('/dev'):
            values = line.split(':')
            mdstat['path'] = values[0]
        elif '/dev' in line: # need to check the content of other states, e.g. creating raid
            mdstat['raidDevices'].append(line[line.index('/dev'):])
    return mdstat

# SMART Parser - RnD

class SMART(dict):

    def __init__(self):
        self.update({
            'information': {}, # e.g. 'Device Model': 'WDC WD80EFBX-68AZZN0'
            'vendorSmartAttributes': {} # e.g. 'Raw_Read_Error_Rate': {'VALUE': 100}
        })

    @classmethod
    def get_vendor_from_model(cls, model):
        if model.lower().startswith("wdc"): return "WD"
        elif model.lower().startswith("hgst"): return "HGST"
        elif model.lower().startswith("st"): return "Seagate"
        elif model.lower().startswith("samsung"): return "SAMSUNG"
        elif model.lower().startswith("hitachi"): return "Hitachi"
        elif model.lower().startswith("hdt"): return "Hitachi"
        elif model.lower().startswith("toshiba"): return "Toshiba"
        else: return "unknown"

    def get_vendor(self):
        return self.get_vendor_from_model(self['information']['Device Model'])

    def get_capacity(self):
        return int(self['information']['User Capacity'].split(' ')[0].replace(',', ''))

def parse_smart(output_in_lines):
    smart = SMART()
    section = None
    for line in output_in_lines:
        line = line.strip()
        if not section: # match a section to parse text
            if line.startswith('=== START OF INFORMATION SECTION ==='):
                section = 1
            elif line.startswith('ID# ATTRIBUTE_NAME"'):
                section = 2
            else:
                continue
        else:
            if not line: # end of a section
                section = None
            # parse the line in a section and update to SMART object
            if section == 1 and ':' in line:
                k, v = [l.strip() for l in line.split(':', 1)]
                smart['information'][k] = v
            elif section == 2:
                values = line.strip().split()
                if len(values) != 10:
                    log.warning('Unexpected line: ' + line)
                    continue
                value_dict = {}
                for idx, key in enumerate(["id", "attribute", "flag", "value", "worst", "threshold", \
                        "type", "updated", "when_failed", "raw_value"]):
                    value_dict[key] = int(values[idx]) if values[idx].isdigit() else values[idx]
                smart['vendorSmartAttributes'][value_dict['attribute']] = value_dict
    return smart
