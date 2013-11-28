#!/usr/bin/env python

import math
import os
import copy


from molecule import Atom, Bond, Molecule
from utils import CORES, XGROUPS, RGROUPS, ARYL0, ARYL2, ARYL, name_expansion, KEYWORDS
try:
    from project.utils import StringIO
except ImportError:
    from cStringIO import StringIO

DATAPATH = "chemtools/data"
ALL = CORES + XGROUPS + RGROUPS + ARYL

##############################################################################

def read_data(filename):
    '''Reads basic data files.'''
    atomtypes = {'C':'4', 'N': '3', 'O': '2', 'P': '3', 'S': '2'}
    if len(filename) == 3:
        convert = {"XX": filename[1], "YY": filename[2]}
        filename = filename[0] + atomtypes[convert["XX"]] + atomtypes[convert["YY"]]
    #try to load file with lowercase name then upper
    paths = [
        os.path.join(DATAPATH, filename),
        os.path.join(DATAPATH, filename.lower()),
        os.path.join("data", filename),
        os.path.join("data", filename.lower()),
    ]
    for path in paths:
        try:
            f = open(path, "r")
            break
        except:
            pass
    else:
        raise Exception(3, "Bad Substituent Name: %s" % filename)

    atoms = []
    bonds = []
    state = 0
    for line in f:
        if line == "\n":
            state = 1
        elif state == 0:
            e, x, y, z = line.split()[-4:]
            if len(filename) == 3 and e in convert:
                e = convert[e]
            atoms.append(Atom(x, y, z, e, atoms))
        elif state == 1:
            a1, a2, t = line.split()
            bonds.append(Bond((atoms[int(a1) - 1], atoms[int(a2) - 1]), t, bonds))
    f.close()
    return atoms, bonds

##############################################################################

class GJFWriter(object):
    def __init__(self, name, keywords=None):
        self.name = name
        self.keywords = keywords if keywords is not None else KEYWORDS
        self.molecule = self.build(name)

    def load_fragments(self, coreset):
        corename, (leftparsed, middleparsed, rightparsed) = coreset
        # molecule, name, parent
        core = (Molecule(read_data(corename)), corename, corename)

        fragments = []
        for side in [middleparsed] * 2 + [rightparsed, leftparsed]:
            temp = []
            if side is not None:
                for (char, parentid, flip) in side:
                    parentid += 1  # offset for core
                    mol = Molecule(read_data(char))
                    temp.append((mol, char, parentid))
                    if flip:
                        mol.reflect_ends()
            else:
                temp.append(None)
            fragments.append(temp)
        return core, fragments

    def concatenate_fragments(self, core, fragments):
        out = [core]
        for side in fragments:
            for part in side:
                if part is not None:
                    out.append(part[0])
        return Molecule(out)

    def build(self, name):
        '''Returns a closed molecule based on the input of each of the edge names.'''
        coresets, nm, xyz = parse_name(name)

        molecules = []
        for coreset in coresets:
            core, fragments = self.load_fragments(coreset)

            ends = []
            cends = core[0].open_ends()
            #bond all of the fragments together
            for j, side in enumerate(fragments):
                if side[0] is None:
                    ends.append(cends[j])
                    continue

                this = [core] + side
                for (part, char, parentid) in side:
                    bondb = part.next_open()
                    if not parentid:
                        bonda = cends[j]
                    else:
                        c = bondb.connection()
                        #enforces lowercase to be r-group
                        if char.islower():
                            c = "+"
                        elif char.isupper():
                            c += "~"
                        bonda = this[parentid][0].next_open(c)

                    if bonda and bondb:
                        this[parentid][0].merge(bonda, bondb, part)
                    else:
                        raise Exception(6, "Part not connected")

                # find the furthest part and get its parent's next open
                if char in ARYL:
                    ends.append(part.next_open('~'))
                elif char in XGROUPS:
                    ends.append(None)
                else: # find R-Group parent
                    furthest = max(x[2] for x in side)
                    ends.append(this[furthest][0].next_open('~'))

            #merge the fragments into single molecule
            temp = self.concatenate_fragments(core[0], fragments)
            molecules.append((temp, ends))

        a, finalends = molecules[0][0].chain(molecules)

        #multiplication of molecule/chain
        a, _ = a.polymerize(finalends, nm)

        if any(xyz):
            a = a.stack(*xyz)

        a.close_ends()
        return a

    def get_gjf(self):
        starter = [
                    "%nprocshared=16",
                    "%mem=59GB",
                    "%%chk=%s.chk" % self.name,
                    "# %s geom=connectivity" % self.keywords,
                    "",
                    self.name,
                    "",
                    "0 1",
                    ""
                    ]
        string = "\n".join(starter)
        string += self.molecule.gjf
        return string

    def get_mol2(self):
        return self.molecule.mol2

    def get_png(self, size=10):
        f = StringIO()
        self.molecule.draw(size).save(f, "PNG")
        return f.getvalue()


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
                output.append([part,[]])
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

        for xside, idx, name in zip(parsedsides, [0,1,0], ["left", "middle", "right"]):
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
            if previous[0] in aryl0+aryl2:
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

def get_exact_name(name):
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
                endname = ''.join([x[0]+'-' if x[2] else x[0] for x in end])

            if not endname or endname[-1] not in XGROUPS:
                if f(num):
                    endname += 'A'
            parts.append(endname.replace("J", "4aaA"))

        # only first set will have left sides
        if num == 0:
            coreset = '_'.join([parts[0], core, parts[1], parts[2]])
        else:
            coreset = '_'.join([core, parts[1], parts[2]])

        sets.append(coreset)
    return '_'.join(sets) + '_n%d_m%d' % nm + '_x%d_y%d_z%d' % xyz


##############################################################################
# StandAlone
##############################################################################

if __name__ == "__main__":
    import argparse
    import sys

    class StandAlone(object):
        def __init__(self, args):
            self.errors = []
            self.error = args.error | args.verbose

            try:
                self.scale = args.d
            except:
                self.scale = 0

            self.args = args
            self.names = ','.join(args.names + self.convert_files(args.listfiles))
            self.longname = args.longname
            self.gjf = args.gjf
            self.mol2 = args.mol2
            self.folder = args.folder
            self.keywords = args.keywords

        def convert_files(self, filenames):
            if filenames:
                files = []
                for filename in filenames:
                    if os.path.isfile(filename):
                        with open(filename, 'r') as f:
                            files += [x.strip() for x in f if x.strip()]
                return files
            else:
                return []

        def write_files(self):
            for molecule in name_expansion(self.names):
                try:
                    out = GJFWriter(molecule, self.keywords)

                    name = molecule
                    if self.longname:
                        name = get_exact_name(name)
                    pathname = os.path.join(self.folder, name)

                    if self.gjf or not (self.mol2 or self.scale):
                        with open(pathname+".gjf", 'w') as f:
                            f.write(out.get_gjf())

                    if self.mol2:
                        with open(pathname+".mol2", 'w') as f:
                            f.write(out.get_mol2())

                    if self.scale:
                        with open(pathname+".png", 'w') as f:
                            f.write(out.get_png(self.scale))
                except Exception as e:
                    self.errors.append(e)

            if self.error:
                print "\n---- Errors ----"
                for x in self.errors:
                    if type(x) == tuple:
                        print " - ".join([str(x[0]), x[1]])
                    else:
                        print repr(x)

    parser = argparse.ArgumentParser(description="This program writes Gaussian .gjf files from molecule names.")
    parser.add_argument('names', metavar='name', type=str, nargs='*', default=list(), help='The name of the molecule to create.')
    parser.add_argument('-i', metavar='list_file', action="store", nargs='*', default=list(), dest="listfiles", type=str, help='A file with a listing of molecules to make.')
    parser.add_argument('-f', metavar='folder', action="store", default=".", dest="folder", type=str, help='A folder to output the files.')
    parser.add_argument('-k', action="store", dest="keywords", default=KEYWORDS, help="The keywords to use for the calculation. (%s by default)" % KEYWORDS)
    parser.add_argument('-d', type=int, action="store", default=0, help="Used to scale an output image. (0 by default, meaning no picture)")

    parser.add_argument('-E', action="store_true", dest="error", default=False, help='Toggles showing error messages.')
    parser.add_argument('-V', action="store_true", dest="verbose", default=False, help='Toggles showing all messages.')
    parser.add_argument('-L', action="store_true", dest="longname", default=False, help='Toggles showing the long name.')
    parser.add_argument('-G', action="store_true", dest="gjf", default=False, help='Toggles writing gjf.')
    parser.add_argument('-M', action="store_true", dest="mol2", default=False, help='Toggles writing mol2.')

    if len(sys.argv) > 1:
        args = sys.argv[1:]
    else:
        args = raw_input('Arguments: ').strip().split()
    a = StandAlone(parser.parse_args(args))
    a.write_files()