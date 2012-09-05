from __future__ import with_statement
from fabric.api import local
import os
from fabric.api import *
from fabric.contrib.console import confirm

env.hosts = ['somethingloc.al']
local_project_path = '/home/devasia/pyserver/somethinglocal'
production_project_path = '/srv/webapp/mysite'
solr_schema_path = '/opt/apache-solr-3.6.0/example/solr/conf'


def restart_supervisor():
    sudo("supervisorctl reload")


def remote_source_update():
    with cd(production_project_path):
        run("git pull")


def push_code():
    local("git push origin master", capture=False)
    remote_source_update()
    restart_supervisor()


def commit_deploy(commit_message):
    local('git add --all && git commit -a -m "%s"' % commit_message,
          capture=False)
    local("git push origin master", capture=False)
    remote_source_update()
    restart_supervisor()


def run_remote_test(app):
    with cd(production_project_path):
        run("python manage.py test %s" % app)


def rebuild_schema():
    with cd(production_project_path):
        run("python manage.py build_solr_schema >> solr_schema.xml")
        run("rm %s/schema.xml" % solr_schema_path)
        run("mv solr_schema.xml %s" % solr_schema_path)
    restart_supervisor()


def rebuild_index():
    with cd(production_project_path):
        run("python manage.py rebuild_index")
