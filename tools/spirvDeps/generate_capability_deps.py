#!/usr/bin/env python3

# TODO Copyright

"""Generates a GraphViz DOT file from a SPIR-V JSON grammar file"""

import json

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate GraphViz DOT file from a JSON grammar')

    parser.add_argument('--grammar', metavar='<path>',
                        type=str, required=True,
                        help='input JSON grammar file')
    args = parser.parse_args()

    with open(args.grammar) as json_file:
        grammar_json = json.loads(json_file.read())
        #print(json.dumps(grammar_json, indent=2))
        #print(grammar_json.keys())
        print('digraph SPIRV_Capabilities {')
        print('rankdir="LR"')
        for operand_kind in grammar_json['operand_kinds']:
            if operand_kind['kind'] == 'Capability':
                for cap in operand_kind['enumerants']:
                    if 'capabilities' in cap:
                        for dep in cap['capabilities']:
                            print('%s -> %s;'%(cap['enumerant'], dep))
                    else:
                        print('%s'%(cap['enumerant']))
        print('}')

if __name__ == '__main__':
    main()
