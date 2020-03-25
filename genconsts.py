#!/usr/bin/env python2
from __future__ import print_function

import argparse
import datetime
import json
import os
import sys
import subprocess

basename = os.path.basename(sys.argv[0])
now = datetime.datetime.utcnow()
hdr = 'This file was autogenerated by %s' % basename
license_text = """
LINSTOR - management of distributed storage/DRBD9 resources
Copyright (C) 2017 - %s  LINBIT HA-Solutions GmbH
All Rights Reserved.
Author: %s

  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.""" % (
    now.year, ', '.join(['Robert Altnoeder', 'Roland Kammerer', 'Gabor Hernadi', 'Rene Peinthor']))


def get_native_java_type(type_str):
    """
    Return the native java type.

    :param str type_str:
    :return:
    """
    if type_str == 'BOR':
        return 'long'
    elif type_str == 'BAND':
        return 'long'
    if type_str == 'string':
        return 'String'
    elif type_str == 'bool':
        return 'boolean'
    elif type_str == 'int':
        return 'int'
    elif type_str == 'long':
        return 'long'

    raise NotImplementedError()


def java(consts, outdir):
    indent = ' ' * 4

    license_hdr = ''
    for l in license_text.split('\n'):
        license_hdr += (' * ' + l).rstrip() + '\n'

    with open(os.path.join(outdir, "ApiConsts.java"), "w+") as outfile:
        outfile.write('/*\n * %s\n%s */\n' % (hdr, license_hdr) + '\n')

        outfile.write('package com.linbit.linstor.api;\n\n')
        outfile.write('@SuppressWarnings({"checkstyle:magicnumber", "checkstyle:constantname"})\n')
        outfile.write('public class ApiConsts\n{\n')

        nl, w = '', 0
        for e in consts:
            w += 1
            if w > 1:
                nl = '\n'

            if 'blockcomment' in e:
                c = e['blockcomment'].replace('\n', '\n' + indent + ' * ')
                outfile.write('%s%s/*\n %s* %s\n %s*/\n' % (nl, indent, indent, c, indent))
                continue

            _type = e['type']
            if _type == 'enum':
                enum_type = e['enumtype']
                native_type = get_native_java_type(enum_type)
                outfile.write('%spublic enum %s\n%s{\n' % (indent, e['name'], indent))
                enum_strs = []
                for enum_entry in e['values']:
                    enum_value = '"%s"' % enum_entry['value'] if enum_type == 'string' else enum_entry['value']
                    enum_strs.append('%s%s(%s)' % (indent * 2, enum_entry['name'], str(enum_value)))
                outfile.write(",\n".join(enum_strs) + ';\n\n')

                outfile.write("%sprivate final %s enumValue;\n" % (indent * 2, native_type))
                outfile.write("%s%s(final %s val) { enumValue=val; }\n" % (indent * 2, e['name'], native_type))
                outfile.write("%spublic %s getValue() { return enumValue; }\n" % (indent * 2, native_type))

                outfile.write('%s}\n' % indent)
            else:
                value = e['value']
                native_type = get_native_java_type(_type)

                if native_type is None:
                    raise RuntimeError("Type '{t}' not handled.".format(t=_type))

                if _type == 'BOR':
                    value = ' | '.join([str(x) for x in value])
                elif _type == 'BAND':
                    value = ' & '.join([str(x) for x in value])
                elif _type == 'string':
                    value = '"%s"' % value

                if 'comment' in e:
                    outfile.write("%s// %s\n" % (indent, e['comment']))
                c = "%spublic static final %s %s = %s;" % (indent, native_type, e['name'], value)
                outfile.write(c + '\n')

        outfile.write('\n    private ApiConsts()\n    {\n    }\n')
        outfile.write('}\n')


def strip_l(value):
    return value[:-1] if str(value).endswith('L') and str(value).startswith('0x') else value


def get_native_python_type(type_str):
    """

    :param str type_str:
    :return:
    :rtype: str
    """
    if type_str == 'BOR':
        return 'long'
    elif type_str == 'BAND':
        return 'long'
    elif type_str == 'string':
        return 'str'
    elif type_str == 'bool':
        return 'bool'
    elif type_str == 'int':
        return 'int'
    elif type_str == 'long':
        return 'long'

    raise NotImplementedError()


def python(consts, outdir):
    with open(os.path.join(outdir, "sharedconsts.py"), "w+") as outfile:
        outfile.write('# %s\n' % hdr)
        outfile.write('# '.join([l.strip() + '\n' for l in license_text.split('\n')]) + '\n')
        outfile.write("""import sys
if sys.version_info > (3,):
    long = int

from enum import Enum

""")

        store_mask = True
        masks = []
        indent = ' ' * 4
        nl, w = '', 0
        for e in consts:
            w += 1
            nl = '\n' if w > 1 else ''

            if 'blockcomment' in e:
                c = e['blockcomment'].replace('\n', '\n# ')
                if 'Special answer message content types' in c:
                    store_mask = False
                outfile.write('\n%s# ## %s ###\n' % (nl, c))
                continue

            _type = e['type']
            if _type == 'enum':
                outfile.write('class %s(Enum):\n' % (e['name']))
                for enum_entry in e['values']:
                    fmt_str = '%s%s = "%s"' if e['enumtype'] == 'string' else '%s%s = %s'
                    outfile.write(fmt_str % (indent, enum_entry['name'], enum_entry['value']) + '\n')
            else:
                value = e['value']

                if _type in ['long', 'BOR', 'BAND']:
                    if isinstance(value, list):
                        value = [strip_l(x) for x in value]
                    else:
                        value = strip_l(value)

                native_type = get_native_python_type(_type)

                if _type == 'BOR':
                    value = ' | '.join([str(x) for x in value])
                elif _type == 'BAND':
                    value = ' & '.join([str(x) for x in value])
                elif _type == 'string':
                    value = "'%s'" % value

                if store_mask:
                    masks.append(e['name'])

                assert(native_type is not None)
                if 'comment' in e:
                    outfile.write("# %s\n" % (e['comment']))
                c = "%s = %s(%s)" % (e['name'], native_type, value)
                outfile.write(c + '\n')

        outfile.write('\n\nif __name__ == "__main__":\n')
        outfile.write(' ' * 4 + 'MAP_MASK = {\n')
        outfile.write(',\n'.join([' ' * 8 + "'" + mask + "': " + mask for mask in masks]) + '\n')
        outfile.write(' ' * 4 + '}\n')
        outfile.write("""    TYPE_MASKS = [
        0xC000000000000000,  # TYPE
        0x0000000003000000,  # OPERATION
        0x00000000003C0000,  # OBJECT
        0xC00000000000FFFF   # ACTION
    ]

    for num_str in sys.argv[1:]:
        num = long(num_str)
        mask = []
        for type_mask in TYPE_MASKS:
            for key, mask_value in MAP_MASK.items():
                if num & type_mask == mask_value:
                    mask.append(key)
        print(num_str + " = " + " | ". join(mask))
""")


def to_camel_case(snake_str):
    components = snake_str.split('_')  # split by underscore and .title() items
    return ''.join(x.title() for x in components)


def golang(consts, outdir):
    apiconsts_path = os.path.join(outdir, "apiconsts.go")
    files_written = [apiconsts_path]
    with open(apiconsts_path, "w+") as outfile:
        outfile.write('// %s\n\n' % hdr)
        outfile.write('// '.join([l.strip() + '\n' for l in license_text.split('\n')]) + '\n')

        outfile.write('package linstor\n')

        store_mask = True
        masks = []
        nl, w = '', 0
        translated = {}

        for e in consts:
            w += 1
            nl = '\n' if w > 1 else ''

            if 'blockcomment' in e:
                c = e['blockcomment'].replace('\n', '\n// ')
                if 'Special answer message content types' in c:
                    store_mask = False
                outfile.write('%s// ## %s ###\n' % (nl, c))
                continue

            _type = e['type']

            if _type == 'enum':
                package_name = e['name'].lower()
                enum_type_name = e['name']
                outfile.write('// enum generated in package -> "golinstor/{p}"\n'.format(p=package_name))
                subpkg = os.path.join(outdir, package_name)
                os.makedirs(subpkg, exist_ok=True)
                subpkg_file_path = os.path.join(subpkg, package_name + '.go')
                files_written.append(subpkg_file_path)
                with open(subpkg_file_path, "w+") as subfile:
                    subfile.write("package {p}\n\n".format(p=package_name))

                    subfile.write("type {p} {t}\n\n".format(p=enum_type_name, t=e['enumtype']))
                    subfile.write("const (\n")
                    for enum_entry in e['values']:
                        enum_name = to_camel_case(enum_entry['name'])
                        enum_value = '"%s"' % enum_entry['value'] if e['enumtype'] == 'string' else enum_entry['value']
                        outfile.write('// {p}.{en} = {v}\n'.format(
                            p=package_name, en=enum_name, v=enum_value))
                        subfile.write("    {en} {t} = {v}\n".format(
                            en=enum_name, t=enum_type_name, v=enum_value))
                    subfile.write(")\n")
            else:
                value = e['value']
                if _type in ['long', 'BOR', 'BAND']:
                    if isinstance(value, list):
                        value = [strip_l(x) for x in value]
                    else:
                        value = strip_l(value)

                if _type == 'BOR':
                    value = [translated.get(v, v) for v in value]
                    value = ' | '.join([str(x) for x in value])
                    value = '(%s)' % value
                elif _type == 'BAND':
                    value = [translated.get(v, v) for v in value]
                    value = ' & '.join([str(x) for x in value])
                    value = '(%s)' % value
                elif _type == 'string':
                    value = '"%s"' % value

                if store_mask:
                    masks.append(e['name'])

                if 'comment' in e:
                    outfile.write("// %s\n" % (e['comment']))
                var = snake_to_camel(e['name'])
                translated[e['name']] = var
                c = "const %s = %s" % (var, value)
                outfile.write(c + '\n')

    # gofmt files
    for filepath in files_written:
        print('gofmt file ' + filepath)
        subprocess.check_call(['gofmt', '-w', filepath])


def snake_to_camel(name):
    return "".join(w.lower().title() for w in name.split("_"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("language", choices=['java', 'python', 'golang'])
    parser.add_argument("outdir", default=".")

    args = parser.parse_args()

    script_path = os.path.dirname(os.path.abspath(__file__))
    f = os.path.join(script_path, 'consts.json')
    with open(f) as consts_file:
        try:
            consts = json.load(consts_file)
        except Exception as e:
            print('The input file (%s) is not valid, better luck next time...\n' % f, file=sys.stderr)
            print('Error: %s...\n' % e, file=sys.stderr)
            sys.exit(1)

    if args.language == 'java':
        java(consts, args.outdir)
    elif args.language == 'python':
        python(consts, args.outdir)
    elif args.language == 'golang':
        golang(consts, args.outdir)


if __name__ == "__main__":
    main()
