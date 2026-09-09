#!/usr/bin/env python3

# TODO Copyright

"""
Look up the capabilities added by a SPIR-V version or by a SPIR-V extension.

The type of the source is inferred unless it is specified: a source beginning
with SPV_ is an extension, and anything else is a version, such as 1.4.
"""

import argparse
import sys

from spirv_lookup import (DEFAULT_GRAMMAR, capabilities_by_name,
                          enumerant_value, load_grammar, symbol_version)

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
    if source.upper().startswith(EXTENSION_PREFIX):
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


def find_capabilities(grammar, source_type, source):
    """
    Return the capabilities added by a SPIR-V version or by a SPIR-V extension.
    Extensions are matched ignoring case.
    """
    matches = []
    for capability in capabilities_by_name(grammar).values():
        if source_type == VERSION_TYPE:
            added = symbol_version(capability) == source
        else:
            added = any(extension.lower() == source.lower()
                        for extension in capability.get('extensions', []))
        if added:
            matches.append(capability)
    return matches


def main():
    parser = argparse.ArgumentParser(
        description='Look up the capabilities added by a SPIR-V version or by a '
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
    print('Looking up capabilities in file: {}'.format(args.grammar),
          flush=True)

    source_type = args.type
    if source_type == INFERRED_TYPE:
        source_type = infer_type(args.source)

    description = 'SPIR-V {} {}'.format(source_type, args.source)
    capabilities = find_capabilities(grammar_json, source_type, args.source)
    if not capabilities:
        print('Found no capabilities added by {}.'.format(description),
              file=sys.stderr)
        if source_type == VERSION_TYPE:
            print('The versions in this grammar are: {}'.format(', '.join(
                grammar_versions(grammar_json))), file=sys.stderr)
        return 1

    print('Capabilities added by {}:'.format(description))
    for capability in capabilities:
        print('  {} = {}'.format(capability['enumerant'],
                                 enumerant_value(capability)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
