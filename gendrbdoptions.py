#!/usr/bin/env python2
import argparse
import sys
import subprocess
import xml.etree.ElementTree as ET


"""
This script translates xml output from drbdsetup options to JSON
"""


_CategoryNamespaces = {
    'new-peer': "DrbdOptions/Net",
    'disk-options': "DrbdOptions/Disk",
    'resource-options': "DrbdOptions/Resource",
    'peer-device-options': "DrbdOptions/PeerDevice"
}

_ObjectCategories = {
    "controller": ['disk-options', 'resource-options', 'new-peer', 'peer-device-options'],
    "resource-definition": ['disk-options', 'resource-options', 'new-peer', 'peer-device-options'],
    "volume-definition": ['disk-options'],  # TODO add volume connection -> 'peer-device-options'
    "rsc-conn": ['peer-device-options', 'new-peer']
}


def get_drbd_setup_xml(from_file):
    drbdsetup_cmd = ['/usr/sbin/drbdsetup', 'xml-help']
    opts = ['disk-options', 'peer-device-options', 'resource-options', 'new-peer']
    try:
        xml_opts = [subprocess.check_output(drbdsetup_cmd + [x]) for x in opts]
    except OSError as oe:
        sys.stderr.write("Unable to execute drbdsetup: {cmd}\nUsing local file {f}\n".format(
            cmd=" ".join(drbdsetup_cmd),
            f=from_file)
        )
        with open(from_file) as f:
            return f.read()

    return '<root>\n' + "".join(xml_opts) + '</root>'


def parse_drbd_setup_xml(xmlout):
    root = ET.fromstring(xmlout)

    objects = {k: [] for k in _ObjectCategories.keys()}
    properties = {}
    for command in root:
        cmd_name = command.attrib['name']
        cmd_namespace = _CategoryNamespaces[cmd_name]

        cmd_properties = {}
        for option in command.findall('option'):
            option_name = option.attrib['name']
            if option_name not in ['set-defaults', '_name']:
                cmd_properties[option_name] = convert_option(cmd_namespace, option_name, option)

        for obj, categories in _ObjectCategories.items():
            if cmd_name in categories:
                objects[obj].extend(cmd_properties.keys())
        properties.update(cmd_properties)

    return {
        "objects": objects,
        "properties": properties
    }


def convert_option(cmd_namespace, option_name, option):
    option_type = option.attrib['type']

    prop = {
        'internal': True,
        'key': cmd_namespace + '/' + option_name,
        'drbd_option_name': option_name
    }

    if option_type == 'string':
        prop_type = option_type
    elif option_type == 'boolean':
        prop_type = option_type
        prop['default'] = True if option.find('default').text == 'yes' else False
    elif option_type == 'handler':
        prop_type = 'symbol'
        prop['values'] = [h.text for h in option.findall('handler')]
    elif option_type == 'numeric':
        for v in ('unit_prefix', 'unit'):
            val = option.find(v)
            if val is not None:
                prop[v] = val.text
        for v in ['min', 'max', 'default']:
            val = option.find(v)
            if val is not None:
                prop[v] = int(val.text)
        prop_type = 'range' if 'min' in prop.keys() else 'numeric'
    elif option_type == 'numeric-or-symbol':
        prop_type = option_type
        prop['values'] = [h.text for h in option.findall('symbol')]
        prop['min'] = option.find('min').text
        prop['max'] = option.find('max').text
    else:
        raise RuntimeError('Unknown option type ' + option_type)

    prop['type'] = prop_type

    return prop


def gendrbd(output_target):
    xml = get_drbd_setup_xml('drbdsetup.xml')
    props = parse_drbd_setup_xml(xml)
    import json

    with open(output_target, 'wt') as f:
        f.write(json.dumps(props, f, indent=2))

    return 0


def main():
    parser = argparse.ArgumentParser(description="generates prepared code containing drbd options")
    parser.add_argument("drbdoptions")

    args = parser.parse_args()

    sys.exit(gendrbd(args.drbdoptions))


if __name__ == '__main__':
    main()
