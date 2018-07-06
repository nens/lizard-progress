# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
"""
Implements classes to auto-fill a review project.

A user can define a set of rules to be applied on observations
from a reviewProject. These are passed in form of a table in a xls or a csv file,
whereby every table row defines a filter rule.

The last two columns of the file are always considered as the threshold values
for 'waarschuwing' and 'ingrijp' actions respectively. The most-right tag without
any content will be considered as the tag to be tested by the rule. All other
elements must have content (i.e. a rule can be tested on exactly one tag).

Example:
the following entry in the filter table file

Tag     | Content | Tag     | Content | Tag     | Content | Waarsch | Ingrijp |
--------+---------+---------+---------+---------+---------+---------+---------+
<A></A> | BAF     | <B></B> | E, F, G | <C></C> |         | A       | B       |

will be interpreted as:

if an observation contains all elements
<A>BAF</A>
<B>E</B> or <B>F</B> or <B>G</B>

and
the observation contains the element
<C>A</C>, then trigger a 'Waarschuwing' action
or if the observation contains the element
<C>B</C>, then trigger a 'Ingrijp' action.
Otherwise no action will be taken.

An action consists in putting an extra element into the observation
with the tag <Trigger> and the action code ('Waarschuwing' or 'Ingrijp')
as content.

"""

import re
import pandas as pd
import operator

import logging
logger = logging.getLogger(__file__)


def _eval(val, op, thr):
    """"Evaluates an expression with a binary operator.
    IN
    val: left operand
    op: binary operator
    thr: right operand
    OUT:
    evaluation result (bool)
    """
    ops = {'<': operator.lt,
           '<=': operator.le,
           '==': operator.eq,
           '=': operator.eq,
           '>=': operator.ge,
           '>': operator.gt,
           None: operator.eq,
           'or': operator.or_,
           'in': operator.contains}

    try:
        val = float(val)
        thr = float(thr)
    except (ValueError, TypeError):
        pass

    try:
        if op == 'in':
            # 'contains' reverses the operands
            res = bool(ops[op](thr, val))
        else:
            res = bool(ops[op](val, thr))
    except TypeError:
        res = False

    return res


def _parse_content(s):
    """Parses content of a table cell, returns its value and the operator in case the cell contains a condition.
    IN
    s: string
    OUT:
    val: parsed value as string
    oper: operator if cell contains a (binary) expression
    """

    if s is None or not str(s).strip():
        return None, None

    # by default we compare with ==
    oper = '=='

    # Get rid of conjunctions
    val = str(s).strip().upper()\
                        .replace('EN', ',')\
                        .replace('OF', ',')

    # special case: any content should trigger
    if 'ALLE' in val or val == '*':
        val = '*'
        oper = 'and'
        return val, oper

    # Looks like a list
    # TODO: does the comma ever appear as the decimal separator?
    for delim in [',', ';', ' ']:
        if delim in val:
            val = list(map(lambda s: s.strip(), val.split(delim)))
            oper = 'in'
            return val, oper

    # Looks like a numeral
    for op in ['>=', '<=', '<', '>', '=', '==']:
        if op in val:
            oper = op
            val = val.replace(op, '').strip()
            break

    # if no operator specified for a single value, use '=='
    if val and (oper is None):
        oper = '=='
    try:
        val = float(val)
    except ValueError:
        pass

    return val, oper


def _is_xml_element(s):
    """ Returns True if input s has the form <tag>content</tag>, content may be empty.
        Used to separate tags from content in the input filter file. """

    if s:
        return re.search(r'<([^>]+)>[\s\S]*?</\1>', s) is not None
    else:
        return False


def _parse_tag(tag):
    """ Transforms a tag to a string, removing <, >, />, e. g. <A> </A> -> A, but also A -> A.
    This allows tags of the form 'A' etc. to be used in the filter file. """

    if '<' not in tag:
        return {'tag': tag, 'content': ''}
    else:
        sres = re.search(r'<(?P<tag>[^>]+)>(?P<content>[\s\S]*?)</\1>', tag)
        return {'tag': sres.group('tag'), 'content': sres.group('content')}


class Field(object):
    """Represents a GWSW-ribx field (which in fact is a XML element) with its tag and content,
    e. g. <A>1</A> will be represented by an instance of Field with .tag = 'A' and .content = '1'. """

    def __init__(self, tag, value=None):

        if not tag:
            self.tag = None
            self.content = None
            return

        # TODO: use re
        self.tag = _parse_tag(tag)['tag']

        val, oper = _parse_content(value)

        try:
            val = float(val)
            self.numeric = True
        except (ValueError, TypeError):
            self.numeric = False

        self.content = val

    def __str__(self):
        return str(''.join(('<', self.tag, '>',
                            (str(self.content) if self.content is not None else ''),
                            '</', self.tag, '>', ('*' if self.is_trigger() else ''))))

    def __eq__(self, other):
        if not hasattr(self, 'tag') or not hasattr(other, 'tag'):
            return True

        if self.tag == other.tag:
            l1 = self.content if isinstance(self.content, list) else [self.content]
            l2 = other.content if isinstance(other.content, list) else [other.content]
            return bool(set(l1).intersection(l2)) or self.content == '*' or other.content == '*'
        else:
            return False

    def is_complete(self):
        # return True if both tag and value are set
        return bool(self.tag) and bool(self.content)

    def is_empty(self):
        return not (bool(self.tag) or bool(self.content))

    def is_trigger(self):
        res = bool(self.tag) and self.content in ['', None]
        return res

    def is_valid(self):
        # In general, tag may have value=None and non-unique tags
        return self.is_complete() or self.is_trigger()


class Observation(object):
    """Represents a single observation as a set of Field instances."""

    def __init__(self, *args, **kwargs):
        self.fields  = []
        if args:
            self.fields = args[0]

    def __str__(self):
        return ' '.join([str(f) for f in self.fields if not f.is_empty()])

    def __contains__(self, field):
        res = field.is_empty() or self.get_by_tag(field.tag) == field
        return res

    def is_valid(self):
        # Observation must contain only tags with values
        all_fields_valid = all([f.is_complete() or f.is_empty() for f in self.fields])

        # TODO: check tag uniqueness
        return all_fields_valid

    def add_field(self, f):
        if f.is_valid():
            self.fields.append(f)

    def get_by_tag(self, tag):
        """Returns field with the given tag if such a field exists in the observation,
        otherwise returns None."""
        try:
            return [f for f in self.fields if f.tag == tag][0]
        except IndexError:
            return None


class ObservationMask(Observation):
    """Represents an observation mask: a set of Field instances to filter observations containig all
    elements of the mask. The only difference to Observation is that ObservationMask must contain
    exactly one field with empty content. The tag of this field will be used to select the element
    from the tested observation to evaluate it and to trigger an autoreview ('Waarschuwing', 'Ingrijp')."""

    def is_valid(self):
        # mask is valid if all fields are complete or empty and there is exactly one trigger field
        return all(list(map(Field.is_valid, self.fields))) and bool(self.get_trigger_field())

    def __eq__(self, other):
        return all([myf == otherf for (myf, otherf) in zip(self.fields, other.fields)])

    def get_trigger_field(self):
        triggers = [f for f in self.fields if f.is_trigger()]
        return triggers[0] if len(triggers) == 1 else False

    def applies_to(self, obs):
        # checks if all non-trigger fields of the mask appear (with the same content) in the observation
        # and the trigger tag appears in the observation
        res = all([(mf in obs) for mf in self.fields if not mf.is_trigger()]) \
            and \
            self.get_trigger_field().tag in [f.tag for f in obs.fields]
        return res

    def __str__(self):
        return super(ObservationMask, self).__str__()


class Rule(object):
    """Implements a single filter rule."""

    ACTION_CODES = {'WARN': 'Waarschuwing',
                    'INTERVENE': 'Ingrijp',
                    'NOACTION': ''}
    TRIGGER_CODES = {'WARN': 'Waarschuwing',
                     'INTERVENE': 'Ingrijp'}

    MESSAGE_CODES = {'MASKINVALID': 'Invalid mask.',
                     'NORULE': 'No applicable rules.'}

    def __init__(self, mask, warn=None, intervene=None):

        self.mask = mask
        self.warnThreshold = warn
        self.interveneThreshold = intervene
        self.warnOperator = None
        self.interveneOperator = None

        self.warnExpr = None
        self.interveneExpr = None

        if warn:
            self.warnThreshold, self.warnOperator = _parse_content(warn)
        if intervene:
            self.interveneThreshold, self.interveneOperator = _parse_content(intervene)

    def is_valid(self):
        return (self.warnThreshold is not None or self.interveneThreshold is not None) and \
            self.mask.is_valid()

    def test_observation(self, observation):
        if not self.mask.is_valid():
            return 'MASKINVALID'

        if self.mask.applies_to(observation):

            val = observation.get_by_tag(self.mask.get_trigger_field().tag).content
            res = _eval(val, self.interveneOperator, self.interveneThreshold)
            if res:
                return 'INTERVENE'

            val = observation.get_by_tag(self.mask.get_trigger_field().tag).content
            res = _eval(val, self.warnOperator, self.warnThreshold)
            if res:
                return 'WARN'

            return 'NOACTION'
        else:
            return 'NORULE'

    def __str__(self):
        return(' '.join((str(self.mask),
                         Rule.TRIGGER_CODES.keys()[0], self.warnOperator or '', str(self.warnThreshold) or '-',
                         Rule.TRIGGER_CODES.keys()[1], self.interveneOperator or '',
                         str(self.interveneThreshold) or '-')))


class FilterTable(object):
    """Implements a set of filter rules."""

    def __init__(self, rules=[]):
        self.rules = rules

    def add_rule(self, rule):
        if rule.is_valid():
            self.rules.append(rule)

    def test_observation(self, observation):
        res = 'NORULE'
        for r in self.rules:
            curr = r.test_observation(observation)
            if curr in Rule.ACTION_CODES.keys():
                res = curr
                if curr in ['WARN', 'INTERVENE']:
                    return curr
        return res

    def apply_to_reviews(self, idic):
        """ Applies rules to a dictionary with reviews (uploadservice reviews json)."""

        dic = idic.copy()
        # loop through subdictionaries of different location types
        for locType in ['pipes', 'manholes']:

            loc_idx = 0

            for loc in dic[locType]:

                if 'ZC' in loc:

                    zc_idx = 0

                    for zc in loc['ZC']:

                        obs = Observation()
                        for k in zc.keys():
                            obs.add_field(Field(k, zc.get(k)))

                        res = self.test_observation(obs)
                        logger.debug(dic[locType][loc_idx]['ZC'][zc_idx])
                        logger.debug(res)
                        if bool(res) and res in Rule.TRIGGER_CODES.keys():
                            dic[locType][loc_idx]['ZC'][zc_idx]['Trigger'] = Rule.TRIGGER_CODES[res]
                        else:
                            del dic[locType][loc_idx]['ZC'][zc_idx]

                        zc_idx += 1
                else:
                    # skip locations with no observations
                    del dic[locType][loc_idx]

                loc_idx += 1

        return dic

    def create_from_excel(self, f):
        """ Creates set of rules using the input excel file.
        One row = one rule,
        the rightmost tag must contail no value and will be considered the trigger.
        """

        names = ['HoofdcodeTag', 'HoofdcodeVal',
                 'Kar1Tag', 'Kar1Val',
                 'Kar2Tag', 'Kar2Val', 'Kwant1',
                 'Omtrek', 'Waarschuwing', 'Ingrijp']

        df = None
        try:
            df = pd.read_excel(f, index_col=None)
        except TypeError:
            # pandas <= 0.22
            df = pd.read_excel(f, 0, index_col=None)

        df = df.dropna(subset=df.columns[-2:], how='all').fillna('')

        for i, r in df.iterrows():
            row = r.tolist()
            trf_pos = max([row.index(t) for t in row if str(t) and _is_xml_element(str(t))])
            flds = [Field(str(t), str(v)) for (t, v) in
                    [(row[it], row[it + 1]) for it in range(0, trf_pos - 1, 2)]
                    if str(t) and str(v)]
            flds.append(Field(str(row[trf_pos])))
            rule = Rule(ObservationMask(flds), warn=r[-2], intervene=r[-1])
            self.rules.append(rule)

    def __str__(self):
        rs = ''
        for r in self.rules:
            if r.is_valid():
                rs = '\n'.join((rs, str(r)))

        return rs


class AutoReviewer(object):

    TRIGGER_CODES = Rule.TRIGGER_CODES

    def __init__(self, filterfile_in=None):
        self.filterFile = filterfile_in
        self.filterTable = FilterTable()
        if filterfile_in:
            self.filterTable.create_from_excel(filterfile_in)
        else:
            # Default filter as discussed with Leo
            # TODO: move this somewhere else
            self.add_rule(Rule(ObservationMask([Field('A', 'BAA'), Field('D', '')]), '>=5', '>=10'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAB'), Field('B', '')]), 'B, C'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAC'), Field('B', '')]), 'A', 'B, C'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAF'), Field('B', 'E,F,G,I'), Field('C', '')]), 'A'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAF'), Field('B', 'C,D,E,F,G,H,I'),
                                                Field('C', '')]), 'B, C, D'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAF'), Field('B', '*'), Field('C', '')]), 'E, Z'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAG'), Field('D', '')]), '>=25'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAH'), Field('B', '')]), 'E, Z'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAI'), Field('B', 'A'), Field('C', '')]), 'B, C, D'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAJ'), Field('B', 'B'), Field('C', '')]), '10'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAK'), Field('B', '')]), 'A, B, C, E, F, G, H, I, J, K'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAO'), Field('G', '')]), None, '0'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BAP'), Field('G', '')]), None, '0'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BBA'), Field('B', '')]), 'A, B, C'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BBB'), Field('D', '')]), None, '>=10'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BBC'), Field('D', '')]), None, '>=10'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BBD'), Field('B', '')]), 'A, B, C, D, Z'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BBE'), Field('B', '')]), 'A, B, C, D, E, F, G, H, Z'))
            self.add_rule(Rule(ObservationMask([Field('A', 'BBF'), Field('B', '')]), 'B', 'C, D'))

    def add_rule(self, r):
        self.filterTable.add_rule(r)

    def run(self, json_in):
        json_out = self.filterTable.apply_to_reviews(json_in)
        return json_out

    def count_rules(self):
        return len([r for r in self.filterTable.rules if r.is_valid()])

    def test_observation(self, obs):
        return self.filterTable.test_observation(obs)


if __name__ == '__main__':

    import os

    f = os.path.join('/tmp',
                     'filter_complete_valid.xlsx')

    ar = AutoReviewer()

    print(ar.filterTable)

    test_cases = {
        Observation([Field('A', 'BAA'), Field('B', 'Z'), Field('D', '1')]): 'NOACTION',
        Observation([Field('A', 'BAA'), Field('B', 'Z'), Field('D', '11')]): 'INTERVENE',
        Observation([Field('A', 'BAA'), Field('B', 'Z'), Field('D', '6')]): 'WARN',
        Observation([Field('A', 'BBB'), Field('D', '6'), Field('F', '6')]): 'NOACTION',
        Observation([Field('A', 'BBB'), Field('D', '13'), Field('H', '6')]): 'INTERVENE',
        Observation([Field('A', 'BAF'), Field('B', 'I'), Field('C', 'E')]): 'WARN',
        Observation([Field('A', 'BZF'), Field('B', 'Z'), Field('C', 'Z')]): 'NORULE',
        Observation([Field('A', 'BAO'), Field('R', '0'), Field('G', '0')]): 'INTERVENE',
        Observation([Field('A', 'BAO'), Field('R', '0'), Field('G', '1')]): 'NOACTION'
    }

    print('==========')
    for obs, expected in test_cases.items():
        res = ar.filterTable.test_observation(obs)
        print(' '.join((str(obs), '->', res, '(expected:', expected, ')')))
        assert(res == expected)
