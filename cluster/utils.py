import os
import bz2
import time

from project.utils import StringIO, SSHClient, SFTPClient

from models import Credential
from data.models import JobTemplate


def get_ssh_connection_obj(obj):
    if isinstance(obj, Credential):
        try:
            return obj.get_ssh_connection()
        except:  # sometimes this times out
            return obj.get_ssh_connection()
    elif isinstance(obj, SSHClient):
        return obj
    else:
        raise TypeError


def get_sftp_connection_obj(obj):
    if isinstance(obj, Credential):
        try:
            return obj.get_sftp_connection()
        except:  # sometimes this times out
            return obj.get_sftp_connection()
    elif isinstance(obj, SFTPClient):
        return obj
    else:
        raise TypeError


def get_credentials_from_request(request):
    creds = []
    usercreds = request.user.credentials.all()
    for key in request.POST:
        if set(key).intersection("@:-") and request.POST[key] == "on":
            username, hostname = key.split('@')
            hostname, port = hostname.split(':')
            port, id_ = port.split('-')
            try:
                cred = usercreds.get(
                            id=id_,
                            username=username,
                            cluster__hostname=hostname,
                            cluster__port=int(port))
                creds.append(cred)
            except Exception as e:
                pass
    return creds


def _make_folders(ssh):
    folder = 'chemtools/done/'
    _, _, testerr2 = ssh.exec_command("mkdir -p %s" % folder)
    testerr2 = testerr2.readlines()
    if testerr2:
        return testerr2[0]
    return None


def add_fileparser(ssh, sftp):
    with sftp.open("chemtools/fileparser.py", 'w') as f:
        with open("chemtools/fileparser.py", 'r') as f2:
            f.write(f2.read())

    command = "python chemtools/fileparser.py -"
    _, stdout, stderr = ssh.exec_command(command)

    err = stderr.read()
    if "No module named argparse" in err:
        import argparse
        with sftp.open("chemtools/argparse.py", 'w') as f:
            with open(argparse.__file__.rstrip('c'), 'r') as f2:
                f.write(f2.read())
        _, stdout, stderr = ssh.exec_command(command)
        err = stderr.read()
        if err:
            return err
    return None


def _run_job(ssh, sftp, gjfstring, jobstring=None, **kwargs):
    try:
        error = _make_folders(ssh)
        if error:
            return None, "folder - " + error

        name = kwargs.get("name", "chemtoolsjob")
        gjfname = "chemtools/%s.gjf" % name
        jobname = "chemtools/%s.job" % name

        f = sftp.open(gjfname, 'w')
        f.write(gjfstring)
        f.close()

        if jobstring is None:
            jobstring = JobTemplate.render(internal=True, **kwargs)
        f2 = sftp.open(jobname, 'w')
        f2.write(jobstring)
        f2.close()

        # TODO: Make this safer
        s = "cd chemtools; qsub " + "%s.job" % name
        _, stdout, stderr = ssh.exec_command(s)
        stderr = stderr.readlines()
        if stderr:
            return None, "qsub - " + stderr[0]

        jobid = stdout.readlines()[0].split(".")[0]
    except Exception as e:
        return None, str(e)
    return jobid, None


def _get_columns(lines):
    toprow = [x.strip() for x in lines[2].strip().split() if x]

    bottomrow = [x.strip() for x in lines[3].strip().split() if x]
    bottomrow.remove("Job")
    idx = bottomrow.index("ID")
    bottomrow[idx] = "Job " + bottomrow[idx]

    timeidx = bottomrow.index("Time")
    timeidx2 = bottomrow.index("Time", timeidx + 1)
    memidx = bottomrow.index("Memory")
    idxes = [timeidx, timeidx2, memidx]
    order = sorted(idxes)
    argorder = [order.index(x) for x in idxes]

    for i, x in enumerate(idxes):
        bottomrow[x] = ' '.join([toprow[argorder[i]], bottomrow[x]])
    return bottomrow


def _get_jobs(cred, cluster, i, results):
    wantedcols = ["Job ID", "Username", "Jobname", "Req'd Memory",
                "Req'd Time", 'Elap Time', 'S']
    try:
        ssh = cred.get_ssh_connection()

        with ssh:
            # TODO: Make this safer
            _, stdout, stderr = ssh.exec_command("qstat -u %s" % cred.username)
            # seems to need this slight delay to display the jobs
            stderr.readlines()

            jobs = []
            lines = stdout.readlines()

            cols = _get_columns(lines[:5])
            colsidx = []
            for x in wantedcols:
                try:
                    colsidx.append(cols.index(x))
                except IndexError:
                    pass

            for job in lines[5:]:
                t = job.split()
                # empty line implies a split in the table
                # this is seen on blacklight with the "Total cpus requested
                # from running jobs" line at the end.
                if t == []:
                    break

                temp = []
                for idx in colsidx:
                    temp.append(t[idx])
                temp[0] = temp[0].split('.')[0]
                jobs.append(temp)
        results[i] = {"name": cluster, "columns": wantedcols, "jobs": jobs}
    except Exception as e:
        results[i] = {"name": cluster, "columns": wantedcols, "jobs": []}
