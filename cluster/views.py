from django.shortcuts import render, redirect
from django.template import Context
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import simplejson

from models import Job
import interface


@login_required
def job_index(request):
    return render(request, "cluster/job_index.html")

@login_required
def cluster_job_index(request, cluster):
    c = Context({
        "cluster": cluster,
        })
    return render(request, "cluster/job_index.html", c)

@login_required
def get_job_list(request):
    try:
        cluster = request.REQUEST.get("cluster", "")
        jobs = interface.get_all_jobs(request.user, cluster)
        e = None
    except Exception as e:
        jobs = []
    a = {
        "is_authenticated": request.user.is_authenticated(),
        "clusters": jobs,
    }
    return HttpResponse(simplejson.dumps(a), mimetype="application/json")

@login_required
def job_detail(request, cluster, jobid):
    e = None
    jobs = interface.get_all_jobs(request.user, cluster)[0]
    for job in jobs["jobs"]:
        if job[0] == jobid:
            break
    else:
        job = None
        e = "That job number is not running."
    c = Context({
        "job": job,
        "cluster": cluster,
        "error_message": e,
        })
    return render(request, "cluster/job_detail.html", c)

@login_required
def reset_job(request, jobid):
    """Used to restart jobs that have hit the time limit."""
    if not request.user.is_staff:
        return HttpResponse("You must be a staff user to reset a job.")

    if request.method == "POST":
        e = None
        name = Job.objects.filter(jobid=jobid).name
        njobid, e = interface.reset_output(request.user, name)
        if e is None:
            return HttpResponse("It worked. Your new job id is: %d" % njobid)
        else:
            return HttpResponse(e)

@login_required
def kill_job(request, cluster):
    if not request.user.is_staff:
        return HttpResponse("You must be a staff user to kill a job.")

    if request.method == "POST":
        jobids = []
        for key in request.POST:
            try:
                int(key)
                jobids.append(key)
            except ValueError:
                pass
        result = interface.kill_jobs(request.user, cluster, jobids)
        if result["error"] is None:
            return redirect(job_index)
        else:
            return HttpResponse(e)
    else:
        return redirect(job_index)