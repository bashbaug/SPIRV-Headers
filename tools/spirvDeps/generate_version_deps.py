#!/usr/bin/env python3

# TODO Copyright

import json

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate GraphViz DOT file from a JSON grammar')

    parser.add_argument('--grammar', metavar='<path>',
                        type=str, required=True,
                        help='input JSON grammar file')
    parser.add_argument('--spirv-version', metavar='<version>',
                        type=str, required=True,
                        help='SPIR-V version to report')
    args = parser.parse_args()

    with open(args.grammar) as json_file:
        grammar_json = json.loads(json_file.read())
        #print(json.dumps(grammar_json, indent=2))
        #print(grammar_json.keys())
        print('SPIR-V features that require version %s:'%(args.spirv_version))
        for operand_kind in grammar_json['operand_kinds']:
            if not 'enumerants' in operand_kind:
                continue
            for enumerant in operand_kind['enumerants']:
                if 'version' in enumerant and enumerant['version'] == args.spirv_version:
                    print('  Operand kind %s: %s'%(operand_kind['kind'], enumerant['enumerant']))
                    print('    Requires Capabilities: %s'%(enumerant['capabilities'])) if 'capabilities' in enumerant else None

if __name__ == '__main__':
    main()
