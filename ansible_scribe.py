#!/usr/bin/env python3

import argparse
import datetime
import os
import sys
import yaml

from configparser import ConfigParser
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
conf_file = args.conf_file
conf = ConfigParser(allow_no_value=True)
conf.read([conf_file])
settings["roles_path"] = conf.get("paths", "roles")
settings["playbooks_path"] = conf.get("paths", "playbooks")
settings["output_dir"] = conf.get("paths", "output")
settings["license"] = conf.get("metadata", "license")
settings["author"] = conf.get("metadata", "author")
settings["company"] = conf.get("metadata", "company")
settings["ci_type"] = conf.get("CI", "type")


def read_config(role):
    """ Loads a config file for a role """
    suffix = ".conf"
    role_config = os.path.join(config_dir, role, suffix)
    with open(role_config, "r") as r_c:
        role_settings = {}
        conf = ConfigParser(allow_no_value=True)
        conf.read([r_c])
        role_settings["role_version"] = conf.get("versions", "role")
        role_settings["min_ansible_version"] = conf.get("versions", "ansible_min")
        role_settings["repo"] = conf.get("urls", "repo")
        role_settings["issue_tracker"] = conf.get("urls", "issue_tracker")
        role_settings["playbook"] = conf.get("config", "playbook")
        role_settings["description"] = conf.get("config", "description")
        role_settings["platforms"] = conf.get("config", "platforms")
        role_settings["outside_deps"] = conf.get("config", "dependencies")
        role_settings["galaxy_tags"] = conf.get("config", "galaxy_tags")

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
    """ Help us figure out where the script is running from so we can find
    files we need """
    script_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    templates = os.path.join(script_path, "templates")
    return templates


def write_license(license, author, path):
    """ Writes out a template file for a role """
    now = datetime.datetime.now()
    year = now.year
    licenses = os.path.join(get_templates_path(), "licenses")
    licensej2 = "{}.j2".format(license)
    template_loader = FileSystemLoader(searchpath=licenses)
    template_env = Environment(loader=template_loader)
    template = template_env.get_template(licensej2)
    data = template.render(copyright_holder=settings["author"], year=year)

    role_license = os.path.join(settings["roles_path"], licensej2)
    with open(role_license, "wb") as rl:
        rl.write(data)


if __name__ == "__main__":
    pass
