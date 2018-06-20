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
import json


def _parse_content(s):
    if str(s).strip() == '' or s is None:
        return None, None

    # Get rid of conjunctions
    val = str(s).strip()\
                .replace('en', ',')\
                .replace('of', ',')
    oper = None

    # special case: any content should trigger
    if 'alle' in val:
        val = 'not None'
        oper = 'is'
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
            if op == '=':
                oper = '=='
            val = val.replace(op, '').strip()
            break

    # if no operator specified for a single value, use '=='
    if val and (oper is None):
        oper = '=='
    return val, oper


def _is_xml_element(s):
    """ Returns True if input has the form <tag>content</tag>, content may be empty
    args:
       s: string
    returns: Boolean
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

        self.content, oper = _parse_content(value)

        try:
            dummy = float(self.content)
            self.numeric = True
        except (ValueError, TypeError):
            self.numeric = False

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
            return set(l1).intersection(l2)
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
        return all([mf in obs for mf in self.fields if not mf.is_trigger()]) \
            and \
            self.get_trigger_field().tag in [f.tag for f in obs.fields]

    def __str__(self):
        return super(ObservationMask, self).__str__()


class Rule(object):
    """Implements a single filter rule. (== one row in the imported file)"""

    def __init__(self, mask, warn=None, intervene=None):

        self.mask = mask
        self.warnThreshold = warn
        self.interveneThreshold = intervene
        self.warnOperator = None
        self.interveneOperator = None

        self.warnExpr = None
        self.interveneExpr = None

        if self.is_valid():
            self.create()

    def is_valid(self):
        return (self.warnThreshold is not None or self.interveneThreshold is not None) and \
            self.mask.is_valid()

    def apply_to(self, observation):
        if not self.mask.is_valid():
            return 'Invalid mask.'

        if self.mask.applies_to(observation):
            if self.interveneOperator and\
               self.interveneExpr(observation.get(self.mask.get_trigger_field().tag).content):
                    return ACTION_CODES.keys()[1]
            elif self.warnOperator:
                if self.warnExpr(
                        observation.get(self.mask.get_trigger_field().tag).content):
                    return ACTION_CODES.keys()[0]
            else:
                return 'Not triggered'
        else:
            return 'Mask does not match'

    def set_warn(self, s):
        self.warnThreshold, self.warnOperator = _parse_content(s)
        if self.mask.get_trigger_field().numeric:
            self.warnExpr = lambda x: eval(str(x) + self.warnOperator + str(self.warnThreshold))
        else:
            q2 = '' if isinstance(self.warnThreshold, list) else '\''
            self.warnExpr = lambda x: eval('\'' + str(x) + '\'' +
                                           self.warnOperator + q2 + str(self.warnThreshold) + q2)

    def set_intervene(self, s):
        self.interveneThreshold, self.interveneOperator = _parse_content(s)
        if self.mask.get_trigger_field().numeric:
            self.interveneExpr = lambda x: eval(str(x) + self.interveneOperator + str(self.interveneThreshold))
        else:
            q2 = '' if isinstance(self.interveneThreshold, list) else '\''
            self.interveneExpr = lambda x: eval('\'' + str(x) + '\'' +
                                                self.interveneOperator + q2 + str(self.interveneThreshold) + q2)

    def create(self):
        self.set_warn(self.warnThreshold)
        self.set_intervene(self.interveneThreshold)

    def __str__(self):
        return(''.join((str(self.mask),
                        ', warning: ', self.warnOperator or '', str(self.warnThreshold) or '-',
                        ', intervention: ', self.interveneOperator or '', str(self.interveneThreshold) or '-')))


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
        for r in self.rules:
            res = r.apply_to(observation)
            if res in ACTION_CODES.keys():
                return res

    def apply_to_reviews(self, dic):

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

                    zc_idx += 1

            pipe_idx += 1

        return dic

    def create_from_excel(self, f):
        names = ['HoofdcodeTag', 'HoofdcodeVal',
                 'Kar1Tag', 'Kar1Val',
                 'Kar2Tag', 'Kar2Val', 'Kwant1',
                 'Omtrek', 'Waarschuwing', 'Ingrijp']

        df = None
        try:
            df = pd.read_excel(f, index_col=None)
        except TypeError:
            # pandas<=
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


if __name__ == '__main__':

    o2 = Observation([Field('A', 'BAO'), Field('B', 'C'), Field('G', '0')])
    r1o1 = Observation([Field('A', 'BAA'), Field('D', '6')])
    f = '/tmp/filter_complete_valid.xlsx'

    ar = AutoReviewer(f)

    res = 'not ready'
    with open('/tmp/review_uncompleted.json') as f:
        data = json.load(f)
        res = ar.run(data)
    print(res)
    # print(ar.filterTable.test_observation(r1o1))
