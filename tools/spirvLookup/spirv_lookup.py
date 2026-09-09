#!/usr/bin/env python3

# TODO Copyright

"""
Look up information for a SPIR-V symbol in a JSON grammar file.

The symbol may be a text symbol or a numeric value.  Because a numeric value is
only unique within a single instruction or operand kind, looking up a numeric
value may report several matches.
"""

import argparse
import json
import os
import sys

# The grammar file to use when none is specified on the command line.
DEFAULT_GRAMMAR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'include', 'spirv', 'unified1', 'spirv.core.grammar.json')

# Instructions are not an operand kind, so this pseudo kind is used to look up
# instructions.  No operand kind uses this name.
INSTRUCTION_KIND = 'Instruction'

# The operand kind describing capabilities.  The capabilities of a capability are
# the capabilities it implicitly declares, not the capabilities that enable it.
CAPABILITY_KIND = 'Capability'


def parse_numeric(symbol):
    """
    Return the integer value of a numeric symbol, or None if the symbol is not
    numeric.  Both decimal and prefixed values, such as 0x3, are supported.
    """
    for base in (0, 10):
        try:
            return int(symbol, base)
        except ValueError:
            pass
    return None


def enumerant_value(enumerant):
    """
    Return the integer value of an enumerant.  Values for bit enums are encoded
    as hexadecimal strings in the grammar.
    """
    value = enumerant['value']
    return value if isinstance(value, int) else int(value, base=16)


def enum_operand_kinds(grammar):
    """
    Return the list of operand kinds with enumerants, which are the operand kinds
    that can be looked up.
    """
    return [
        operand_kind for operand_kind in grammar.get('operand_kinds', [])
        if 'enumerants' in operand_kind
    ]


def grammar_kinds(grammar):
    """
    Return the list of kinds that can be looked up in a grammar: the pseudo kind
    for instructions, plus every operand kind with enumerants.
    """
    kinds = [INSTRUCTION_KIND] if 'instructions' in grammar else []
    kinds.extend(operand_kind['kind']
                 for operand_kind in enum_operand_kinds(grammar))
    return kinds


def resolve_kind(grammar, kind):
    """
    Return the kind as it is spelled in the grammar, ignoring case, or None if
    the grammar has no such kind.
    """
    for grammar_kind in grammar_kinds(grammar):
        if grammar_kind.lower() == kind.lower():
            return grammar_kind
    return None


def matches_name(entry, key, name):
    """
    Return whether a name is the name of an instruction or an enumerant, or one
    of its aliases.
    """
    return name == entry[key] or name in entry.get('aliases', [])


def find_instructions(grammar, name, value):
    """
    Return the list of instructions matching a name or a numeric value.
    """
    matches = []
    for instruction in grammar.get('instructions', []):
        if name is not None and not matches_name(instruction, 'opname', name):
            continue
        if value is not None and instruction['opcode'] != value:
            continue
        matches.append(instruction)
    return matches


def find_enumerants(grammar, kind, name, value):
    """
    Return the list of (operand kind, enumerant) tuples matching a name or a
    numeric value.  If a kind is specified, only that operand kind is searched.
    """
    matches = []
    for operand_kind in enum_operand_kinds(grammar):
        if kind is not None and operand_kind['kind'] != kind:
            continue
        for enumerant in operand_kind['enumerants']:
            if name is not None and not matches_name(enumerant, 'enumerant',
                                                     name):
                continue
            if value is not None and enumerant_value(enumerant) != value:
                continue
            matches.append((operand_kind, enumerant))
    return matches


def load_grammar(grammar_file):
    """
    Return the parsed JSON grammar, or None if the grammar file cannot be read.
    """
    try:
        with open(grammar_file) as json_file:
            return json.loads(json_file.read())
    except OSError as error:
        print('Could not read grammar file {}: {}'.format(
            grammar_file, error.strerror), file=sys.stderr)
        return None


def print_kinds(grammar, file=sys.stdout):
    """
    Print the kinds that can be looked up in a grammar, with the category of each
    operand kind.
    """
    if 'instructions' in grammar:
        print(INSTRUCTION_KIND, file=file)
    for operand_kind in enum_operand_kinds(grammar):
        print('{} ({})'.format(operand_kind['kind'],
                               operand_kind['category']),
              file=file)


def is_capability_kind(operand_kind):
    """
    Return whether an operand kind describes capabilities.
    """
    return operand_kind['kind'].lower() == CAPABILITY_KIND.lower()


def capabilities_by_name(grammar):
    """
    Return the capability enumerants in a grammar, keyed by capability name.
    """
    for operand_kind in enum_operand_kinds(grammar):
        if is_capability_kind(operand_kind):
            return {
                enumerant['enumerant']: enumerant
                for enumerant in operand_kind['enumerants']
            }
    return {}


def symbol_version(entry):
    """
    Return the core SPIR-V version that added a symbol, or None if the symbol was
    never added to a core version of SPIR-V.
    """
    version = entry.get('version')
    return None if version in (None, 'None') else version


def symbol_sources(entry):
    """
    Return the list of sources that add a symbol: the SPIR-V version that added
    it, and any extensions that add it.
    """
    sources = []
    version = symbol_version(entry)
    if version is not None:
        sources.append('SPIR-V {}'.format(version))
    sources.extend(entry.get('extensions', []))
    return sources


def print_sources(entry):
    """
    Print when a symbol was added, on one line per kind of source.
    """
    version = symbol_version(entry)
    if version is not None:
        print('  Added in SPIR-V version: {}'.format(version))
    extensions = entry.get('extensions')
    if extensions:
        print('  Added by {}: {}'.format(
            'extension' if len(extensions) == 1 else 'extensions',
            ', '.join(extensions)))


def print_aliases(entry):
    """
    Print the other names for an instruction or an enumerant, if it has any.
    """
    aliases = entry.get('aliases')
    if not aliases:
        return
    print('  {}: {}'.format('Alias' if len(aliases) == 1 else 'Aliases',
                            ', '.join(aliases)))


def print_capabilities(grammar, entry, implicitly_declared=False):
    """
    Print the capabilities of an instruction or an enumerant, if it has any.
    Any one of the capabilities enables the symbol, except for a capability,
    which implicitly declares all of its capabilities.
    """
    capabilities = entry.get('capabilities')
    if not capabilities:
        return

    # A capability does not describe what enables it, so there are no sources to
    # print for the capabilities it implicitly declares.
    if implicitly_declared:
        print('  Implicitly declares {}: {}'.format(
            'capability' if len(capabilities) == 1 else 'capabilities',
            ', '.join(capabilities)))
        return

    if len(capabilities) == 1:
        print('  Enabled by capability:')
    else:
        print('  Enabled by any of these capabilities:')
    known_capabilities = capabilities_by_name(grammar)
    for capability in capabilities:
        # An enabling capability from another grammar is not described here.
        sources = symbol_sources(known_capabilities.get(capability, {}))
        if sources:
            print('    {} ({})'.format(capability, ', '.join(sources)))
        else:
            print('    {}'.format(capability))


def print_instruction(grammar, instruction):
    print('Instruction: {}'.format(instruction['opname']))
    print('  Opcode: {}'.format(instruction['opcode']))
    print_aliases(instruction)
    print_sources(instruction)
    print_capabilities(grammar, instruction)


def print_enumerant(grammar, operand_kind, enumerant):
    print('{} {}: {}'.format(operand_kind['category'], operand_kind['kind'],
                             enumerant['enumerant']))
    value = enumerant_value(enumerant)
    if operand_kind['category'] == 'BitEnum':
        print('  Value: {:#06x} ({})'.format(value, value))
    else:
        print('  Value: {}'.format(value))
    print_aliases(enumerant)
    print_sources(enumerant)
    print_capabilities(grammar, enumerant, is_capability_kind(operand_kind))


def main():
    parser = argparse.ArgumentParser(
        description='Look up information for a SPIR-V symbol.')

    parser.add_argument('--grammar',
                        metavar='<path>',
                        type=str,
                        default=DEFAULT_GRAMMAR,
                        help='input JSON grammar file (default: %(default)s)')
    parser.add_argument('--kind',
                        metavar='<kind>',
                        type=str,
                        default=None,
                        help='kind of the symbol to look up, either {} or an '
                        'operand kind such as Decoration (default: look up '
                        'symbols of all kinds)'.format(INSTRUCTION_KIND))
    parser.add_argument('--list-kinds',
                        action='store_true',
                        help='list the kinds in the grammar and exit')
    parser.add_argument('symbol',
                        metavar='<symbol>',
                        type=str,
                        nargs='?',
                        help='the SPIR-V symbol to look up, either a text '
                        'symbol such as OpSource or a numeric value such as 3')
    args = parser.parse_args()

    grammar_json = load_grammar(args.grammar)
    if grammar_json is None:
        return 1
    print('Looking up symbol in file: {}...'.format(args.grammar), flush=True)

    if args.list_kinds:
        print_kinds(grammar_json)
        return 0

    if args.symbol is None:
        parser.error('a symbol is required unless --list-kinds is specified')

    kind = None
    if args.kind is not None:
        kind = resolve_kind(grammar_json, args.kind)
        if kind is None:
            print('Unknown kind {}.  The kinds in this grammar are:'.format(
                args.kind), file=sys.stderr)
            print_kinds(grammar_json, file=sys.stderr)
            return 1

    value = parse_numeric(args.symbol)
    name = args.symbol if value is None else None

    instructions = []
    if kind in (None, INSTRUCTION_KIND):
        instructions = find_instructions(grammar_json, name, value)
    enumerants = []
    if kind != INSTRUCTION_KIND:
        enumerants = find_enumerants(grammar_json, kind, name, value)

    for instruction in instructions:
        print_instruction(grammar_json, instruction)
    for operand_kind, enumerant in enumerants:
        print_enumerant(grammar_json, operand_kind, enumerant)

    if not instructions and not enumerants:
        description = '' if kind is None else kind + ' '
        print('Found no {}symbol matching {}.'.format(description, args.symbol),
              file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
