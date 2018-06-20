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
with the tag <Herstelregel> and the action code ('Waarschuwing' or 'Ingrijp')
as content.

"""

ACTION_CODES = {'warn': 'Waarschuwing',
                'intervene': 'Ingrijp'}

import re
import pandas as pd
import operator


def _eval(val, op, thr):

    ops = {'<': operator.lt,
           '<=': operator.le,
           '==': operator.eq,
           '=': operator.eq,
           '>=': operator.ge,
           '>': operator.gt,
           None: operator.eq,
           'or': operator.or_,
           'in': operator.contains}

    _val = val
    _thr = thr

    try:
        _val = float(val)
        _thr = float(thr)
    except ValueError:
        pass

    try:
        if op == 'in':
            # contains reverses the operands
            res = bool(ops[op](_thr, _val))
        else:
            res = bool(ops[op](_val, _thr))

    except TypeError:
        res = False

    return res


def _parse_content(s):
    if not s or not str(s).strip():
        return None, None

    oper = '=='
    # Get rid of conjunctions
    val = str(s).strip()\
                .replace('en', ',')\
                .replace('of', ',')

    # special case: any content should trigger
    if 'alle' in val or val == '*':
        val = '*'
        oper = 'or'
        return val, oper

    # Looks like a list
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

    return val, oper


def _is_xml_element(s):
    """ Returns True if input has the form <tag>content</tag>, content may be empty.
        Used to separate tags from content in the input filter file.
    """
    if s:
        return re.search(r'<([^>]+)>[\s\S]*?</\1>', s) is not None
    else:
        return False


def _parse_tag(tag):
    """ Transforms a tag to a string, removing <, >, />, e. g. <A> </A> -> A, but also A -> A.
    This allows tags of the form 'A' etc. to be used in the filter file.
    """
    if '<' not in tag:
        return {'tag': tag, 'content': ''}
    else:
        sres = re.search(r'<(?P<tag>[^>]+)>(?P<content>[\s\S]*?)</\1>', tag)
        return {'tag': sres.group('tag'), 'content': sres.group('content')}


class Field(object):
    """Represents a GWSW-ribx field (which in fact is a XML element) with its tag and content,
    e. g. <A>1</A> will be represented by an instance of Field with .tag = 'A' and .content = '1'.

    """

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
                            (str(self.content) if self.content else ''),
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
        return bool(self.tag) and not bool(self.content)

    def is_valid(self):
        # In general, tag may have value=None and non-unique tags
        return self.is_complete() or self.is_empty() or self.is_trigger()


class Observation(object):
    """Represents an observation as a set of Field instances.

    """

    def __init__(self, *args, **kwargs):
        self.fields  = []
        if args:
            self.fields = args[0]

    def __str__(self):
        return ' '.join([str(f) for f in self.fields if not f.is_empty()])

    def __contains__(self, field):
        return field.is_empty() or self.get(field.tag) == field

    def is_valid(self):
        # Observation must contain only tags with values
        all_fields_valid = all([f.is_complete() or f.is_empty() for f in self.fields])

        # TODO: check tag uniqueness
        return all_fields_valid

    def add_field(self, f):
        if f.is_valid():
            self.fields.append(f)

    def get(self, tag):
        """Returns field with the given tag if such a field exists in the observation,
        otherwise returns None."""
        try:
            return [f for f in self.fields if f.tag == tag][0]
        except IndexError:
            return None


class ObservationMask(Observation):
    """Represents an observation mask: a set of Field instances to filter observations containig the
    same elements as the mask. The only difference to Observation is that ObservationMask must
    contain exactly one field with empty content. When testing an observation, its element with the
    same tag as the empty element of the mask will be tested against the threshold values ('Waarschuwing', 'Ingrijp').
    """

    def is_valid(self):
        # mask is valid if all fields are complete or empty and there is exactly one trigger field
        return all(list(map(Field.is_valid, self.fields))) and bool(self.get_trigger_field())

    def __eq__(self, other):
        return all([myf == otherf for (myf, otherf) in zip(self.fields, other.fields)])

    def get_trigger_field(self):
        triggers = [f for f in self.fields if f.is_trigger()]
        return triggers[0] if len(triggers) == 1 else False

    def applies_to(self, obs):
        # checks if all non-trigger fields of the mask appear (with the same value) in the observation
        # and the trigger tag appears in the observation
        res = all([mf in obs for mf in self.fields if not mf.is_trigger()]) \
            and \
            self.get_trigger_field().tag in [f.tag for f in obs.fields]
        return res

    def __str__(self):
        return super(ObservationMask, self).__str__()


class Rule(object):
    """Implements a single filter rule."""

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

    def apply_to(self, observation):
        if not self.mask.is_valid():
            return 'Invalid mask.'

        if self.mask.applies_to(observation):

            val = observation.get(self.mask.get_trigger_field().tag).content
            res = _eval(val, self.interveneOperator, self.interveneThreshold)
            if res:
                return ACTION_CODES.keys()[1]

            val = observation.get(self.mask.get_trigger_field().tag).content
            res = _eval(val, self.warnOperator, self.warnThreshold)
            if res:
                return ACTION_CODES.keys()[0]

            return ''
        else:
            return 'Mask does not match observation'

    def __str__(self):
        return(' '.join((str(self.mask),
                         ', warning:', self.warnOperator or '', str(self.warnThreshold) or '-',
                         ', intervention:', self.interveneOperator or '', str(self.interveneThreshold) or '-')))


class FilterTable(object):
    """Implements a set of filter rules."""

    def __init__(self, rules=[], csvfile=None):
        self.rules = rules

        if csvfile:
            self.parse(csvfile)

    def add_rule(self, rule):
        if rule.is_valid():
            self.rules.append(rule)

    def test_observation(self, observation):
        res = None
        for r in self.rules:
            res = r.apply_to(observation)
            if res in ACTION_CODES.keys():
                break
        return res

    def apply_to_reviews(self, dic):
        """ Applies rules to a dictionary with reviews (uploadservice review json). """

        import logging
        logger = logging.getLogger(__name__)

        pipe_idx = 0
        for pipe in dic['pipes']:

            if 'ZC' in pipe:

                zc_idx = 0

                for zc in pipe['ZC']:

                    if 'Herstelmaatregel' in zc and zc['Herstelmaatregel'] != '':
                        continue

                    obs = Observation()
                    for k in zc.keys():
                        obs.add_field(Field(k, zc.get(k)))

                    res = self.test_observation(obs)
                    if res in ACTION_CODES.keys():
                        dic['pipes'][pipe_idx]['ZC'][zc_idx]['Herstelmaatregel'] = ACTION_CODES[res]

                    logger.debug(obs)
                    logger.debug(res)
                    zc_idx += 1

            pipe_idx += 1

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

    def __init__(self, filterfile_in):
        self.filterFile = filterfile_in
        self.filterTable = FilterTable()
        self.filterTable.create_from_excel(filterfile_in)

    def run(self, json_in):
        json_out = self.filterTable.apply_to_reviews(json_in)
        return json_out

    def count_rules(self):
        return len([r for r in self.filterTable.rules if r.is_valid()])


if __name__ == '__main__':

    f = '/tmp/filter_complete_valid.xlsx'

    ar = AutoReviewer(f)
    print(ar.count_rules())
    
    o2 = Observation([Field('A', 'BAA'), Field('B', 'Z'), Field('D', '10')])
    o3 = Observation([Field('A', 'BAF'), Field('B', 'E'), Field('C', 'Z')])

    res = ar.filterTable.test_observation(o2)
    print(res)
    res = ar.filterTable.test_observation(o3)
    print(res)
