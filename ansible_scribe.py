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


user_home = os.path.expanduser("~")
config_dir = os.path.join(user_home, ".config/ansible-scribe")
global_config = os.path.join(config_dir, "global.conf")
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
settings["playbooks_dir"] = conf["paths"]["playbooks"]
settings["output_dir"] = conf["paths"]["output"]
settings["license"] = conf["metadata"]["license"]
settings["author"] = conf["metadata"]["author"]
settings["bio"] = conf["metadata"]["bio"]
settings["company"] = conf["metadata"]["company"]
settings["ci_type"] = conf["ci"]["type"]


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
        role_settings["requirements"] = conf["config"]["requirements"]
        role_settings["outside_deps"] = conf["config"]["outside_deps"]
        role_settings["galaxy_tags"] = conf["config"]["galaxy_tags"]
        role_settings["playbook"] = conf["config"]["playbook"]

        # dependencies = ()
        playbooks_dir = settings["playbooks_dir"]
        playbook = role_settings["playbook"]
        if playbook:
            playbook_file = os.path.join(playbooks_dir, playbook)
            with open(playbook_file, "r") as p:
                try:
                    data = yaml.safe_load(p)
                    print(data)
                except yaml.YAMLError as exc:
                    print(exc)

        pforms = {}
        for platform in conf["platforms"]:
            for (key, value) in platform.items():
                if key in pforms:
                    pforms[key].append(value)
                else:
                    pforms[key] = [value]
        role_settings["platforms"] = pforms

    return role_settings


def create_output_dir():
    """ Create the output dir if it doesn't exist """
    output_dir = settings["output_dir"]
    try:
        os.makedirs(output_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def get_templates_path():
    """ Find out where the templates are so we can load them later """
    script_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    templates = os.path.join(script_path, "templates")
    return templates


def get_task_files(role):
    """ Function to grab all the tasks files we will need """
    task_files = ()
    tasks_dir = os.join.path(settings["roles_path"], role, "tasks")
    for fn in os.listdir(tasks_dir):
        if fn.endswith(".yaml") or fn.endswith(".yml"):
            task_files.append(fn)
    return task_files


def read_tasks(role):
    """ Reads in task files to build variables list and task list """
    task_names = ()
    role_vars = ()
    task_files = get_task_files()
    for fn in task_files:
        with open(fn, "r") as f:
            try:
                data = yaml.safe_load(f)
                print(data)
            except yaml.YAMLError as exc:
                print(exc)

    return task_names, role_vars


def read_defaults(role):
    """ Read the defaults file for the role to check if it's filled out """
    roles = settings["roles_path"]
    defaults_dir = os.path.join(roles, role, "defaults")
    defaults = os.path.join(defaults_dir, "defaults.yml")
    with open(defaults, "r+") as d:
        data = yaml.safe_load(d)
        print(data)


def write_license(role):
    """ Write out a license file for a role """
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
        role_license = os.path.join(settings["roles_path"], role, license)
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
    branch = role_settings["branch"]
    platforms = role_settings["platforms"]
    galaxy_tags = role_settings["galaxy_tags"]
    outside_deps = role_settings["outside_deps"]
    description = role_settings["description"]
    issue_tracker = role_settings["issue_tracker"]
    min_ansible_version = role_settings["min_ansible_version"]
    min_container_version = role_settings["min_container_version"]
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
        meta = os.path.join(settings["roles_path"], role, "meta", "main.yml")
    else:
        meta = os.path.join(settings["output_dir"], "meta.yml")
    with open(meta, "wb") as m:
        m.write(data)


def write_readme(role):
    """ Write out a new readme file """
    role_settings = read_config(role)
    author = settings["author"]
    bio = settings["bio"]
    license = settings["license"]
    description = role_settings["description"]
    requirements = role_settings["requirements"]
    playbook = role_settings["playbook"]
    templates = get_templates_path()
    task_names, role_vars = read_tasks(role)

    template_loader = FileSystemLoader(searchpath=templates)
    template_env = Environment(loader=template_loader)
    template = template_env.get_template("readme.j2")
    data = template.render(
        role_name=role,
        desc=description,
        reqs=requirements,
        variables=role_vars,
        # deps=dependencies,
        example_playbook=playbook,
        lic=license,
        name=author,
        author_bio=bio,
    )

    if overwrite:
        readme = os.path.join(settings["roles_path"], role, "README.md")
    else:
        readme = os.path.join(settings["output_dir"], "readme.md")
    with open(readme, "wb") as r:
        r.write(data)


def write_ci_file(ci_type, role):
    """ Touch the correct CI file type """
    if ci_type == "gitlab":
        ci_file = "gitlab-ci.yml"
    elif ci_type == "travis":
        ci_file = ".travis.yml"

    ci = os.path.join(settings["roles_path"], role, ci_file)

    try:
        open(ci, "x")
    except FileExistsError:
        pass


if __name__ == "__main__":
    roles = ()
    for fn in os.listdir(settings[config_dir]):
        if fn != "global.conf":
            f = os.path.splitext(fn)[0]
            roles.append(f)
    # try:
    #     settings["output_dir"]
    # except NameError:
    #     pass
    # else:
    #     create_output_dir(settings["output_dir"])

    for i in roles:
        read_config(i)
