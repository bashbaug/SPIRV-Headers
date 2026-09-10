#!/usr/bin/env python3

# TODO Copyright

"""
Look up the symbols added by a SPIR-V version or by a SPIR-V extension.

The type of the source is inferred unless it is specified: a source beginning
with SPV_ is an extension, and anything else is a version, such as 1.4.

A symbol is added by a source if the source adds it directly, which is uncommon,
or if it is enabled by a capability that the source adds, which is more common.
"""

import argparse
import sys

from spirv_lookup import (DEFAULT_GRAMMAR, INSTRUCTION_KIND,
                          capabilities_by_name, enum_operand_kinds,
                          enumerant_value, is_capability_kind, load_grammar,
                          symbol_version)

# The names of SPIR-V extensions begin with this prefix.
EXTENSION_PREFIX = 'SPV_'

# The types of source that can be looked up, and the type that infers which of
# them a source is.
EXTENSION_TYPE = 'extension'
VERSION_TYPE = 'version'
INFERRED_TYPE = 'inferred'


def infer_type(source):
    """
    Return whether a source is a SPIR-V extension or a SPIR-V version.
    """
    if source.startswith(EXTENSION_PREFIX):
        return EXTENSION_TYPE
    return VERSION_TYPE


def grammar_versions(grammar):
    """
    Return the sorted list of SPIR-V versions that add capabilities in a grammar.
    """
    versions = {
        symbol_version(capability)
        for capability in capabilities_by_name(grammar).values()
    }
    return sorted(version for version in versions if version is not None)


def added_by_source(entry, source_type, source):
    """
    Return whether a SPIR-V version or a SPIR-V extension adds a symbol directly.
    """
    if source_type == VERSION_TYPE:
        return symbol_version(entry) == source
    return source in entry.get('extensions', [])


def find_capabilities(grammar, source_type, source):
    """
    Return the capabilities added by a SPIR-V version or by a SPIR-V extension.
    """
    return [
        capability
        for capability in capabilities_by_name(grammar).values()
        if added_by_source(capability, source_type, source)
    ]


def enabling_capabilities(entry, added_capabilities):
    """
    Return the capabilities that enable an instruction or an enumerant and that
    are in a set of capabilities.
    """
    return [
        capability for capability in entry.get('capabilities', [])
        if capability in added_capabilities
    ]


def find_symbols(grammar, source_type, source, added_capabilities):
    """
    Return the list of (kind, name, value, enabling capabilities) tuples for the
    symbols added by a SPIR-V version or by a SPIR-V extension.  The enabling
    capabilities are the capabilities added by the source that enable the symbol,
    and are empty when the source adds the symbol directly.
    """
    matches = []
    for instruction in grammar.get('instructions', []):
        enabling = []
        if not added_by_source(instruction, source_type, source):
            enabling = enabling_capabilities(instruction, added_capabilities)
            if not enabling:
                continue
        matches.append((INSTRUCTION_KIND, instruction['opname'],
                        instruction['opcode'], enabling))

    for operand_kind in enum_operand_kinds(grammar):
        for enumerant in operand_kind['enumerants']:
            enabling = []
            if not added_by_source(enumerant, source_type, source):
                # Nothing enables a capability, so a capability is only added by
                # a source directly.
                if is_capability_kind(operand_kind):
                    continue
                enabling = enabling_capabilities(enumerant, added_capabilities)
                if not enabling:
                    continue
            value = enumerant_value(enumerant)
            if operand_kind['category'] == 'BitEnum':
                value = '{:#06x}'.format(value)
            matches.append((operand_kind['kind'], enumerant['enumerant'], value,
                            enabling))
    return matches


def print_symbols(matches):
    """
    Print the symbols added by a source, grouped by kind.  A symbol with no
    enabling capabilities is added by the source directly.
    """
    printed_kind = None
    for kind, name, value, enabling in matches:
        if kind != printed_kind:
            printed_kind = kind
            print('  {}:'.format(kind))
        line = '    {} = {}'.format(name, value)
        if enabling:
            line += ' (enabled by {} {})'.format(
                'capability' if len(enabling) == 1 else 'capabilities',
                ', '.join(enabling))
        print(line)


def main():
    parser = argparse.ArgumentParser(
        description='Look up the symbols added by a SPIR-V version or by a '
        'SPIR-V extension.')

    parser.add_argument('--grammar',
                        metavar='<path>',
                        type=str,
                        default=DEFAULT_GRAMMAR,
                        help='input JSON grammar file (default: %(default)s)')
    parser.add_argument('--type',
                        metavar='<type>',
                        choices=(EXTENSION_TYPE, VERSION_TYPE, INFERRED_TYPE),
                        default=INFERRED_TYPE,
                        help='type of the source to look up: %(choices)s '
                        '(default: %(default)s)')
    parser.add_argument('source',
                        metavar='<source>',
                        type=str,
                        help='the SPIR-V version or extension to look up, such '
                        'as 1.4 or {}KHR_ray_query'.format(EXTENSION_PREFIX))
    args = parser.parse_args()

    grammar_json = load_grammar(args.grammar)
    if grammar_json is None:
        return 1
    print('Looking up symbols in file: {}'.format(args.grammar), flush=True)

    source_type = args.type
    if source_type == INFERRED_TYPE:
        source_type = infer_type(args.source)

    description = 'SPIR-V {} {}'.format(source_type, args.source)
    added_capabilities = {
        capability['enumerant']
        for capability in find_capabilities(grammar_json, source_type,
                                           args.source)
    }
    matches = find_symbols(grammar_json, source_type, args.source,
                           added_capabilities)
    if not matches:
        print('Found no symbols added by {}.'.format(description),
              file=sys.stderr)
        if source_type == VERSION_TYPE:
            print('The versions in this grammar are: {}'.format(', '.join(
                grammar_versions(grammar_json))), file=sys.stderr)
        return 1

    print('Symbols added by {}:'.format(description))
    print_symbols(matches)
    return 0


if __name__ == '__main__':
    sys.exit(main())
