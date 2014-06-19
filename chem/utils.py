import time
import bz2
import zipfile
import tarfile
import re

from models import ErrorReport

from chemtools import gjfwriter
from chemtools import fileparser
from chemtools.constants import KEYWORDS
from chemtools.ml import get_properties_from_decay_with_predictions, \
                        get_naive_feature_vector, \
                        get_decay_feature_vector
from chemtools.mol_name import name_expansion, get_exact_name
from chemtools.interface import get_property_limits
from data.models import DataPoint
from cluster.interface import run_job, run_jobs
from project.utils import StringIO


def get_molecule_warnings(name):
    try:
        exact_name = get_exact_name(name)
        error = None
    except Exception as e:
        exact_name = ''
        error = str(e)
    warn = ErrorReport.objects.filter(molecule=name)
    warning = True if warn else None
    unique = not DataPoint.objects.filter(exact_name=exact_name).exists()
    return warning, error, unique


def get_multi_molecule_warnings(string):
    errors = []
    warnings = []
    uniques = []

    molecules = name_expansion(string)

    start = time.time()
    for name in molecules:
        if time.time() - start > 1:
            raise ValueError("The operation has timed out.")
        warning, error, unique = get_molecule_warnings(name)
        warnings.append(warning)
        errors.append(error)
        uniques.append(unique)
    return molecules, warnings, errors, uniques


def get_molecule_info(molecule, keywords=KEYWORDS):
    warning, error, unique = get_molecule_warnings(molecule)

    if not error:
        exactspacer = get_exact_name(molecule, spacers=True)
        exactname = exactspacer.replace('*', '')
        try:

            features = [
                        get_naive_feature_vector(exactspacer),
                        get_decay_feature_vector(exactspacer)
                    ]
            homo, lumo, gap = get_properties_from_decay_with_predictions(
                                                                features[1]
                                                                )
        except ValueError:  # multi core and other non-ML structures
            features = ['', '']
            homo, lumo, gap = None, None, None

        temp = DataPoint.objects.filter(exact_name=exactname,
                                        band_gap__isnull=False).values()
        if temp:
            datapoint = temp[0]
        else:
            datapoint = None
    else:
        exactname = ''
        exactspacer = ''
        features = ['', '']
        homo, lumo, gap = None, None, None
        datapoint = None
    limits = get_property_limits(molecule)

    a = {
        "molecule": molecule,
        "exact_name": exactname,
        "exact_name_spacers": exactspacer,
        "features": features,
        "datapoint": datapoint,
        "homo": homo,
        "lumo": lumo,
        "band_gap": gap,
        "unique": unique,
        "known_errors": warning,
        "error_message": error,
        "keywords": keywords,
        "limits": limits,
        }
    return a

def run_standard_job(credential, molecule, **kwargs):
    results = {
        "jobid": None,
        "error": None,
    }
    try:
        results["cluster"] = credential.cluster.name
        if not credential.user.is_staff:
            results["error"] = "You must be a staff user to submit a job."
            return results
    except:
        results["error"] = "Invalid credential"
        results["cluster"] = None
        return results

    try:
        keywords = kwargs.get("keywords", None)
        out = gjfwriter.GJFWriter(molecule, keywords=keywords)
    except Exception as e:
        results["error"] = str(e)
        return results

    gjf = out.get_gjf()
    results = run_job(credential, gjf, **kwargs)
    return results


def run_standard_jobs(credential, string, **kwargs):
    results = {
        "worked": [],
        "failed": [],
        "error": None,
    }
    try:
        results["cluster"] = credential.cluster.name
        if not credential.user.is_staff:
            results["error"] = "You must be a staff user to submit a job."
            return results
    except:
        results["error"] = "Invalid credential"
        results["cluster"] = None
        return results

    names = []
    gjfs = []
    for mol in name_expansion(string):
        try:
            keywords = kwargs.get("keywords", None)
            out = gjfwriter.GJFWriter(mol, keywords=keywords)
            names.append(mol)
            gjfs.append(out.get_gjf())
        except Exception as e:
            results["failed"].append((mol, str(e)))
            continue

    if names:
        temp = run_jobs(credential, names, gjfs, **kwargs)
        results["worked"] = temp["worked"]
        results["failed"].extend(temp["failed"])
        results["error"] = temp["error"]
    return results


def parse_file_list(files):
    for f in files:
        if f.name.endswith(".zip"):
            with zipfile.ZipFile(f, "r") as zfile:
                names = [x for x in zfile.namelist() if not x.endswith("/")]
                for name in names:
                    newfile = StringIO(zfile.open(name).read(), name=name)
                    yield newfile
        elif f.name.endswith(".tar.bz2") or f.name.endswith(".tar.gz"):
            end = f.name.split(".")[-1]
            with tarfile.open(fileobj=f, mode='r:' + end) as tfile:
                for name in tfile.getnames():
                    if tfile.getmember(name).isfile():
                        newfile = StringIO(tfile.extractfile(name).read(),
                                            name=name)
                        yield newfile
        else:
            yield f


def find_sets(files):
    logs = []
    datasets = []
    for f in files:
        if f.name.endswith(".log"):
            logs.append(f)
        else:
            datasets.append(f)

    logsets = {}
    for f in logs:
        nums = re.findall(r'n(\d+)', f.name)
        if not nums:
            continue
        num = nums[-1]

        name = f.name.replace(".log", '').replace("n%s" % num, '')
        if name in logsets.keys():
            logsets[name].append((num, f))
        else:
            logsets[name] = [(num, f)]
    return logsets, datasets


def convert_logs(logsets):
    converted = []
    for key in logsets:
        nvals = []
        homovals = []
        lumovals = []
        gapvals = []
        for num, log in logsets[key]:
            parser = fileparser.Log(log)

            nvals.append(num)
            homovals.append(parser["HOMO"])
            lumovals.append(parser["LUMO"])
            gapvals.append(parser["BandGap"])

        f = StringIO(name=key)
        f.write(', '.join(nvals) + '\n')
        f.write(', '.join(homovals) + '\n')
        f.write(', '.join(lumovals) + '\n')
        f.write(', '.join(gapvals) + '\n')
        f.seek(0)
        converted.append(f)
    return converted
