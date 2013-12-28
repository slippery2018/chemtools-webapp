import re

from constants import *

def name_expansion(string):
    braceparse = re.compile(r"""(\{[^\{\}]*\})""")
    varparse = re.compile(r"\$\w*")

    variables = {
        "SCORES":   ','.join(SCORES),
        "DCORES":   ','.join(DCORES),
        "CORES":    ','.join(CORES),
        "RGROUPS":  ','.join(RGROUPS),
        "XGROUPS":  ','.join(XGROUPS),
        "ARYL":     ','.join(ARYL),
        "ARYL0":    ','.join(ARYL0),
        "ARYL2":    ','.join(ARYL2),
    }

    def get_var(name):
        try:
            newname = name.group(0).lstrip("$")
        except AttributeError:
            newname = name.lstrip("$")

        try:
            x = variables[newname]
        except:
            try:
                int(newname)  # internal variable
                x = '$' + newname
            except:
                x = newname
        return x

    def split_molecules(string):
        count = 0
        parts = ['']
        for i, char in enumerate(string):
            if char == "," and not count:
                parts.append('')
            else:
                if char == "{":
                    count += 1
                elif char == "}":
                    count -= 1
                parts[-1] += char
        assert not count
        return parts

    def expand(items):
        swapped = [re.sub(varparse, get_var, x) for x in items]
        withbrace = swapped[1::2] # every other one has {}
        withoutbrace = swapped[::2]

        # remove {} from x and split
        cleaned = [x[1:-1].split(',') for x in withbrace]
        operations = {
            "":  lambda x: x,
            "L": lambda x: x.lower(),
            "U": lambda x: x.upper()
        }

        out = []
        for group in itertools.product(*cleaned):
            currentvalues = []
            for i, item in enumerate(group):
                if '$' in item:
                    split = item.strip('$').split('.')
                    num = int(split[0])
                    if len(split) > 1:
                        op = operations[split[1].upper()]
                    else:
                        op = operations['']
                    x = op(currentvalues[num])
                else:
                    x = group[i]
                currentvalues.append(x)
            out.append(currentvalues)

        return [''.join(sum(zip(withoutbrace, x), ()) + (swapped[-1], )) for x in out]

    braces = []
    for part in split_molecules(string):
        if set('{}').intersection(part):
            split = re.split(braceparse, part)
            braces.extend(expand(split))
        else:
            braces.append(part)
    return braces


def parse_options(parts):
    newparts = []
    varset = {'n': 1, 'm': 1, 'x': 1, 'y': 1, 'z': 1}
    for part in parts[:]:
        if part[:1] in varset:
            varset[part[:1]] = int(part[1:])
        else:
            newparts.append(part)

    if varset['n'] > 1 and varset['m'] > 1:
        raise Exception(7, "can not do N and M expansion")
    if any(value <= 0 for key, value in varset.items()):
        raise Exception(10, "all expansion values must be greater than 0")

    nm = (varset['n'], varset['m'])
    xyz = (varset['x'], varset['y'], varset['z'])
    return newparts, nm, xyz


def parse_cores(parts):
    output = [[None, []]]
    i = -1
    for part in parts:
        if part.upper() in CORES:
            i += 1
            if i == 0:
                output[i][0] = part
            else:
                output.append([part, []])
        output[i][1].append(part)
    if output[0][0] is None:
        raise Exception(1, "Bad Core Name")
    return output


def parse_name(name):
    '''Parses a molecule name and returns the edge part names.

    >>> parse_name('4a_TON_4b_4c')
    ([('TON', (('4', -1), ('a', 0), ('a', 0)), (('4', -1), ('b', 0), ('b', 0)),
    (('4', -1), ('c', 0), ('c', 0))], (0, 0), (0, 0, 0))
    '''
    parts = name.split("_")

    parts, nm, xyz = parse_options(parts)
    partsets = parse_cores(parts)

    output = []
    for num, (core, parts) in enumerate(partsets):
        i = parts.index(core)
        left = parts[:i][0] if parts[:i] else None
        right = parts[i + 1:]

        if len(right) > 1:
            middle = right[0]
            right = right[1]
        else:
            try:
                letter = right[0][0]
                if letter.lower() in ALL and letter.lower() != letter:
                    middle = letter
                    right = right[0][1:]
                else:
                    middle = None
                    right = right[0]
            except:
                middle = None
        parsedsides = tuple(parse_end_name(x) if x else None for x in (left, middle, right))

        for xside, idx, name in zip(parsedsides, [0, 1, 0], ["left", "middle", "right"]):
            if xside and xside[-1][0] in XGROUPS:
                if nm[idx] > 1:
                    raise Exception(9, "can not do nm expansion with xgroup on %s" % name)
                elif len(partsets) > 1 and name == "right" and (len(partsets) - 1) != num:
                    raise Exception(11, "can not add core to xgroup on %s" % name)

        output.append((core, parsedsides))
    if len(output) > 2 and nm[1] > 1:
        raise Exception(8, "Can not do m expansion and have multiple cores")
    return output, nm, xyz


def parse_end_name(name):
    xgroup = ''.join(XGROUPS)
    rgroup = ''.join(RGROUPS)
    aryl0 = ''.join(ARYL0)
    aryl2 = ''.join(ARYL2)
    block = xgroup + aryl0 + aryl2
    substituent = block + rgroup

    parts = []
    r = 0
    # start with -1 to add 1 later for core
    lastconnect = -1
    state = "start"
    for char in name:
        if char not in substituent and char != '-':
            raise ValueError("Bad Substituent Name: %s" % char)

    for i, char in enumerate(name):
        if char == "-":
            previous = parts[lastconnect]
            if previous[0] in aryl0 + aryl2:
                parts[lastconnect] = (previous[0], previous[1], True)
            else:
                raise ValueError("reflection only allowed for aryl groups")
            continue
        if state == "aryl0":
            if char not in block:
                raise ValueError("no rgroups allowed")
            else:
                parts.append((char, lastconnect, False))

            if char in xgroup:
                state = "end"
            elif char in aryl0:
                state = "aryl0"
            elif char in aryl2:
                state = "aryl2"
            lastconnect = len(parts) - 1

        elif state == "aryl2":
            if char not in rgroup:
                parts.append(("a", lastconnect, False))
                parts.append(("a", lastconnect, False))
                parts.append((char, lastconnect, False))
                if char in xgroup:
                    state = "end"
                elif char in aryl0:
                    state = "aryl0"
                elif char in aryl2:
                    state = "aryl2"
                lastconnect = len(parts) - 1
            else:
                if r == 0:
                    try:
                        if name[i + 1] in rgroup:
                            parts.append((char, lastconnect, False))
                            r += 1
                        else:
                            parts.append((char, lastconnect, False))
                            parts.append((char, lastconnect, False))
                            r += 2
                            state = "start"
                    except IndexError:
                        parts.append((char, lastconnect, False))
                        parts.append((char, lastconnect, False))
                        r += 2
                        state = "start"
                elif r == 1:
                    parts.append((char, lastconnect, False))
                    r += 1
                    state = "start"
                else:
                    raise ValueError("too many rgroups")
        elif state == "start":
            if char not in block:
                raise ValueError("no rgroups allowed")
            else:
                parts.append((char, lastconnect, False))
                r = 0

            if char in xgroup:
                state = "end"
            elif char in aryl0:
                state = "aryl0"
            elif char in aryl2:
                state = "aryl2"
            lastconnect = len(parts) - 1
        elif state == "end":
            raise ValueError("can not attach to end")
    if state == "aryl0":
        pass
    elif state != "end" and state != "start":
        parts.append(("a", lastconnect, False))
        parts.append(("a", lastconnect, False))
    return parts


def get_exact_name(name, spacers=False):
    output, nm, xyz = parse_name(name)
    sidefuncs = (
        lambda num: num == 0 and nm[0] == 1,
        lambda num: nm[1] == 1,
        lambda num: num == (len(output) - 1) and nm[0] == 1,
        )
    sets = []
    for num, (core, ends) in enumerate(output):
        parts = []
        for f, end in zip(sidefuncs, ends):
            endname = ''
            if end:
                # [char, conn, flip?]
                endname = ''.join([x[0] + '-' if x[2] else x[0] for x in end])

            if not endname or endname[-1] not in XGROUPS:
                if f(num):
                    endname += 'A'

            endname = endname.replace("J", "4aaA")
            if spacers:
                endname = ''.join([char + "**" if char in NEEDSPACE else char for char in endname])
            parts.append(endname)

        # only first set will have left sides
        if num == 0:
            coreset = '_'.join([parts[0], core, parts[1], parts[2]])
        else:
            coreset = '_'.join([core, parts[1], parts[2]])

        sets.append(coreset)
    return '_'.join(sets) + '_n%d_m%d' % nm + '_x%d_y%d_z%d' % xyz
