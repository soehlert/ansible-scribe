#!/usr/bin/env python3

import argparse
import datetime
import errno
import os
import sys
import yaml

from builtins import FileExistsError
from configobj import ConfigObj
from jinja2 import Environment, FileSystemLoader


config_dir = os.path.expanduser("~") + "/.config/ansible-scribe"
global_config = config_dir + "/global.conf"
parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--config",
    help="Specify config file location",
    default=global_config,
    dest="conf_file",
)
parser.add_argument(
    "-o",
    "--overwrite",
    help="Overwrite the files in place in the role directory",
    default=False,
    dest="overwrite",
)
parser.add_argument(
    "--version", help="Print version", action="version", version="%(prog)s 0.1.0-alpha"
)
args, remaining_argv = parser.parse_known_args()

settings = {}
overwrite = args.overwrite
conf_file = args.conf_file
conf = ConfigObj(conf_file)
settings["roles_path"] = conf["paths"]["roles"]
settings["playbooks_path"] = conf["paths"]["playbooks"]
settings["output_dir"] = conf["paths"]["output"]
settings["license"] = conf["metadata"]["license"]
settings["author"] = conf["metadata"]["author"]
settings["bio"] = conf["metadata"]["bio"]
settings["company"] = conf["metadata"]["company"]
settings["ci_type"] = conf["ci"]["type"]


def create_output_dir(output_dir):
    """ Create the output dir if it doesn't exist """
    try:
        os.makedirs(output_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def read_config(role):
    """ Reads a config file for a role """
    suffix = ".conf"
    role_config = os.path.join(config_dir, role, suffix)
    with open(role_config, "r") as r_c:
        role_settings = {}
        conf = ConfigObj(r_c)
        role_settings["min_ansible_version"] = conf["versions"]["ansible_min"]
        role_settings["min_container_version"] = conf["versions"]["container_min"]
        role_settings["role_version"] = conf["versions"]["role"]
        role_settings["branch"] = conf["urls"]["branch"]
        role_settings["issue_tracker"] = conf["urls"]["issue_tracker"]
        role_settings["repo"] = conf["urls"]["repo"]
        role_settings["description"] = conf["config"]["description"]
        role_settings["galaxy_tags"] = conf["config"]["galaxy_tags"]
        role_settings["outside_deps"] = conf["config"]["outside_deps"]
        role_settings["playbook"] = conf["config"]["playbook"]

        pforms = {}
        for platform in conf["platforms"]:
            for (key, value) in platform.items():
                if key in pforms:
                    pforms[key].append(value)
                else:
                    pforms[key] = [value]
        role_settings["platforms"] = pforms

    return role_settings


def read_tasks(role):
    """ Reads in task files to build variables list and task list """
    pass


def read_defaults(role):
    """ Read the defaults file for the role to check if it's filled out """
    roles = settings["roles_path"]
    defaults_dir = os.path.join(roles, role, "defaults")
    defaults = os.path.join(defaults_dir, "defaults.yml")
    with open(defaults, "r+") as d:
        data = yaml.safe_load(d)
        print(data)


def get_templates_path():
    """ Find out where the templates are so we can load them later """
    script_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    templates = os.path.join(script_path, "templates")
    return templates


def write_license():
    """ Writes out a template file for a role """
    now = datetime.datetime.now()
    year = now.year
    author = settings["author"]
    license = settings["license"]
    licensej2 = "{}.j2".format(license)
    licenses = os.path.join(get_templates_path(), "licenses")

    template_loader = FileSystemLoader(searchpath=licenses)
    template_env = Environment(loader=template_loader)
    template = template_env.get_template(licensej2)
    data = template.render(copyright_holder=author, year=year)

    if overwrite:
        role_license = os.path.join(settings["roles_path"], license)
    else:
        role_license = os.path.join(settings["output_dir"], license)
    with open(role_license, "wb") as rl:
        rl.write(data)


def write_meta(role):
    """ Write a meta/main.yml file for galaxy """
    role_settings = read_config(role)
    author = settings["author"]
    company = settings["company"]
    license = settings["license"]
    description = role_settings["description"]
    issue_tracker = role_settings["issue_tracker"]
    min_ansible_version = role_settings["min_ansible_version"]
    min_container_version = role_settings["min_container_version"]
    branch = role_settings["branch"]
    platforms = role_settings["platforms"]
    galaxy_tags = role_settings["galaxy_tags"]
    outside_deps = role_settings["outside_deps"]
    templates = get_templates_path()

    template_loader = FileSystemLoader(searchpath=templates)
    template_env = Environment(loader=template_loader)
    template = template_env.get_template("meta.j2")
    data = template.render(
        role_name=role,
        name=author,
        desc=description,
        co=company,
        issue=issue_tracker,
        lic=license,
        mav=min_ansible_version,
        mcv=min_container_version,
        gh_branch=branch,
        p=platforms,
        tags=galaxy_tags,
        deps=outside_deps,
    )

    if overwrite:
        meta = os.path.join(settings["roles_path"], "meta", "main.yml")
    else:
        meta = os.path.join(settings["output_dir"], "meta.yml")
    with open(meta, "wb") as m:
        m.write(data)


def write_readme(role):
    """ Write out a new readme file """
    role_settings = read_config(role)
    print(role_settings)


def write_ci_file(ci_type, path):
    """ Touch the correct CI file type """
    if ci_type == "gitlab":
        ci_file = "gitlab-ci.yml"
    elif ci_type == "travis":
        ci_file = ".travis.yml"

    ci = os.path.join(settings["roles_path"], ci_file)

    try:
        open(ci, "x")
    except FileExistsError:
        pass


if __name__ == "__main__":
    try:
        settings["output_dir"]
    except NameError:
        pass
    else:
        create_output_dir(settings["output_dir"])

    write_ci_file()
