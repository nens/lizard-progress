# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""
Helper functions to auto-fill inspections of a review project.


A user can define its own filler as csv-file, in which he/she declares a set of
rules. Rules are defined on the rows and must consist of 5 columns:

 Hoofdcode | Karakteresering 1 | Karakterisering 2 | Ingrijp | Waarschuwing

 translated to ribx-tags:

    A     |       B           |       C           |   D     |       D

The first row of the filler csv-file is its header and will be skipped.
See the tests/test_met_files/filter for examples of fillers.


The function build_rule_tree() is the main function of this file, which builds
a rule-tree based on a set of rules. This rule-tree can be used by the
reviewproject to auto-fill its inspections.

An rule-tree is dict of (4) nested dicts to efficiently find the rule which is
applicable to a specific inspection (ZC). Each branch (from the root till the
leaf) is a specific rule defined in the filler csv-file. The leaf node of the
tree defines what action/function must be applied to the inspection.
If an inspection does not contain a branch in the rule-tree, no rules are
applicable to this inspection and thus it can be skipped.
"""

import itertools
import csv


def parse_insp_filler(inspection_filler,
                      delimiter=str(',')):
    """Read in the inspection_filler and create and a list of flat rules

    Inspection filter generates a set of rules.

    :arg
        inspection_filter (file object): a csv file with rules for
            filtering.
        delimiter (str): one-character string used to separate fields.
    :return
        list of flat rules.
    """
    reader = csv.reader(inspection_filler, delimiter=delimiter)
    # Skip header
    reader.next()

    inspection_rules = {}
    flat_rules = []
    for rule in reader:
        assert(len(rule) == 5)
        flat_rules += list(_flatten_rule(rule, ','))

    return flat_rules


def build_rule_tree(rules):
    """Build a rule tree of a list of (flat) rules

    :arg
        rules (list): flattened rules, see _flatten_rule()"""
    result = {}

    for rule in rules:
        assert(len(rule) == 5)
        hoofd_key = rule[0]
        kar1_key = rule[1]
        kar2_key = rule[2]
        waarschuwing = rule[3]
        ingrijp = rule[4]
        # Check if the branch exists, if not create it.
        if not hoofd_key in result:
            result[hoofd_key] = {}
        if not kar1_key in result[hoofd_key]:
            result[hoofd_key][kar1_key] = {}
        if not kar2_key in result[hoofd_key][kar1_key]:
            result[hoofd_key][kar1_key][kar2_key] = {}
        # Add rule to tree, potentially combine it if it already contains
        # some rules in this branch
        new_rule = {
            waarschuwing: 'waarschuwing',
            ingrijp: 'ingrijp'
        }
        old_rules = result[hoofd_key][kar1_key][kar2_key]
        new_rule.update(old_rules)
        result[hoofd_key][kar1_key][kar2_key] = new_rule
    return result


def apply_rules(rule_tree, reviews):
    """Apply the inspection_filter on the reviews.

    Auto-fills any inspections with a review if one of the rules inside
    the filter applies. None-empty inspections are ignored.

    Currently the filter only applies to inspections of pipes (ZC).
    """
    rules = self.parse_ins_filter()
    rule_tree = self.build_rule_tree(rules)
    for pipe in reviews['pipes']:
        for zc in pipe['ZC']:
            _apply_rule(rule_tree, zc)


def _flatten_rule(rule, delimiter=str(',')):
    """Return an iterator which generates new flattened rules.

    I.e. the rule:
        [A, [B, C], D]
        ---(flatten)-->
        [A, B, D],
        [A, C, D]

    :arg
        rules (list of strings): the rules to be flattened.
    :return a list of flattened rules.
    """
    assert(len(rule) == 5)
    # split the rules on delimiter and remove trailing whitespaces
    bags = [[unstripped.strip() for unstripped in unflat.split(',')] for unflat in rule]

    return list(itertools.product(*bags))


def _apply_rule(rule_tree, zc):
    """Checks if one of the rules applies to this inspection (ZC)

    Applies the first found rule if it does.
    Ignores inspections which already have a 'Herstelmaatregel'.

    :arg
        rule_tree (dict)
        zc (json)
    :return
        inspection element with applied rules (if any).
    """
    if zc['Herstelmaatregel'] != '':
        return zc
    hoofdcode = zc['A']
    karakt1 = zc['B']
    karakt2 = zc['C']
    kwant = zc['D']
    if (hoofdcode in rule_tree and
            karakt1 in rule_tree[hoofdcode] and
            karakt2 in rule_tree[hoofdcode][karakt1] and
            kwant in rule_tree[hoofdcode][karakt1][karakt2]):
        applicable_rule = rule_tree[hoofdcode][karakt1][karakt2][kwant]
        # TODO: let the rule be a function instead of a string and apply
        # the function.

        zc['Herstelmaatregel'] = applicable_rule
    return zc
