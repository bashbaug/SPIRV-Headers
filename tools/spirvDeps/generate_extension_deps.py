#!/usr/bin/env python3

# TODO Copyright

import json

def main():
    import argparse
    parser = argparse.ArgumentParser(description='TODO')

    parser.add_argument('--grammar', metavar='<path>',
                        type=str, required=True,
                        help='input JSON grammar file')
    args = parser.parse_args()

    with open(args.grammar) as json_file:
        grammar_json = json.loads(json_file.read())

    #print(json.dumps(grammar_json, indent=2))
    #print(grammar_json.keys())

    # Collect the list of extension capabilities
    extension_caps = set()
    for operand_kind in grammar_json['operand_kinds']:
        if operand_kind['kind'] == 'Capability':
            for cap in operand_kind['enumerants']:
                if 'extensions' in cap:
                    extension_caps.add(cap['enumerant'])
    #print(extension_caps)

    # Collect the list of instructions added by extensions
    extension_ops = set()
    for instruction in grammar_json['instructions']:
        if 'capabilities' in instruction:
            for dep in instruction['capabilities']:
                if dep in extension_caps:
                    extension_ops.add(instruction['opname'])
    #print(extension_ops)

    # Find operand types that are interesting
    core_op_types = set()
    extension_op_types = set()
    for instruction in grammar_json['instructions']:
        if not 'operands' in instruction:
            #print(instruction['opname'])
            continue
        if instruction['opname'] in extension_ops:
            for op in instruction['operands']:
                if not op['kind'] in extension_op_types:
                    print('Extension instruction %s uses op type %s;'%(instruction['opname'], op['kind']))
                extension_op_types.add(op['kind'])
        else:
            for op in instruction['operands']:
                if not op['kind'] in core_op_types:
                    print('Core instruction %s uses op type %s;'%(instruction['opname'], op['kind']))
                core_op_types.add(op['kind'])
    extension_op_types = extension_op_types - core_op_types
    print(extension_op_types)

if __name__ == '__main__':
    main()
