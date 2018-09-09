#!/usr/bin/env python3

import os
import argparse
import yaml

from configparser import ConfigParser

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
    """ Reads in task files to build variables list """
    pass


def read_defaults(role):
    """ Read the defaults file for the role to check if it's filled out """
    pass


def write_template(template_file, path):
    """ Writes out a template file for a role """
    pass


if __name__ == "__main__":
    pass
