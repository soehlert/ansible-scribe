#!/usr/bin/env python3

import argparse
import datetime
import errno
import logging
import os
import sys
import yaml

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
    "-l",
    "--log-level",
    help="Set the log level. Defaults to INFO, but you may wish to bump it to WARNING",
    default="INFO",
    dest="log_level",
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

conf_file = args.conf_file
conf = ConfigObj(conf_file)

log_level = args.log_level
overwrite = args.overwrite

# Logging setup
log = logging.getLogger()  # 'root' Logger
console = logging.StreamHandler()
format_str = "%(levelname)s: %(filename)s:%(lineno)s -- %(message)s"
console.setFormatter(logging.Formatter(format_str))
log.addHandler(console)

acceptable_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ll = log_level.upper()
if ll not in acceptable_log_levels:
    log.critical("Please choose an accepted python logging level")
    sys.exit()
elif ll == "CRITICAL":
    log.setLevel(logging.CRITICAL)
elif ll == "ERROR":
    log.setLevel(logging.ERROR)
elif ll == "WARNING":
    log.setLevel(logging.WARNING)
elif ll == "DEBUG":
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

settings = {}
settings["roles_path"] = conf["Paths"]["roles"]
settings["playbooks_dir"] = conf["Paths"]["playbooks"]
settings["output_dir"] = conf["Paths"]["output"]
settings["repo_license"] = conf["Metadata"]["repo_license"]
settings["author"] = conf["Metadata"]["author"]
settings["bio"] = conf["Metadata"]["bio"]
settings["company"] = conf["Metadata"]["company"]
settings["ci_type"] = conf["CI"]["type"]


def read_config(role):
    """ Reads a config file for a role """
    role_file = "{}.conf".format(role)
    role_config = os.path.join(config_dir, role_file)
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
        role_settings["galaxy_tags"] = conf["config"]["galaxy_tags"]
        role_settings["playbook"] = conf["config"]["playbook"]

        dependencies = []
        playbooks_dir = settings["playbooks_dir"]
        playbook = role_settings["playbook"]
        if playbook:
            playbook_file = os.path.join(playbooks_dir, playbook)
            with open(playbook_file, "r") as p:
                try:
                    data = yaml.safe_load(p)
                    d = yaml.dump(data, Dumper=yaml.Dumper)
                    role_settings["example_playbook"] = d
                    roles_list = []
                    for section in data:
                        for k, v in section.items():
                            if k == "roles":
                                roles_list.append(v)
                    for roles in roles_list:
                        for role in roles:
                            if "." in role:
                                dependencies.append(role)
                except yaml.YAMLError as exc:
                    print(exc)
        role_settings["dependencies"] = dependencies

        pforms = {}
        for platform, version in conf["platforms"].items():
            if platform in pforms:
                pforms[platform].append(version)
            else:
                pforms[platform] = [version]
        role_settings["platforms"] = pforms

    return role_settings


def create_output_dir():
    """ Create the output dir if it doesn't exist """
    output_dir = settings["output_dir"]
    try:
        os.makedirs(output_dir)
        log.info("Created output directory")
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
    task_files = []
    tasks_dir = os.path.join(settings["roles_path"], role, "tasks")
    for fn in os.listdir(tasks_dir):
        if fn.endswith(".yaml") or fn.endswith(".yml"):
            full_path = os.path.join(tasks_dir, fn)
            task_files.append(full_path)

    return task_files


def read_tasks(role):
    """ Reads in task files to build variables list and task list """
    task_names = []
    role_vars = []
    task_files = get_task_files(role)
    extra_keys = [
        "name",
        "with_items",
        "command",
        "when",
        "block",
        "delegate_to",
        "rescue",
        "args",
    ]
    for fn in task_files:
        with open(fn, "r") as f:
            try:
                data = yaml.safe_load(f)
                for task in data:
                    task_names.append(task["name"])
                    for task_name, module in task.items():
                        if task_name not in extra_keys:
                            for k, v in module.items():
                                if str(v).startswith("{{") and "item" not in v:
                                    role_vars.append(v.strip("{{ ").rstrip("}"))
            except yaml.YAMLError as e:
                log.warning(e)

    return task_names, role_vars


def read_defaults(role):
    """ Read the defaults file for the role to check if it's filled out """
    roles = settings["roles_path"]
    default_vars_dict = {}
    defaults_dir = os.path.join(roles, role, "defaults")
    defaults = os.path.join(defaults_dir, "main.yml")
    with open(defaults, "r") as d:
        num_lines = sum(1 for i in d)
        if num_lines <= 2:
            log.warn("Default values are not set")
            return
    with open(defaults, "r") as d:
        data = yaml.safe_load(d)
        for key, value in data.items():
            if key in default_vars_dict:
                if value is None:
                    default_vars_dict[key] = ""
                else:
                    default_vars_dict[key] = value
            else:
                if value is None:
                    default_vars_dict[key] = ""
                else:
                    default_vars_dict[key] = value

    return default_vars_dict


def write_repo_license(role):
    """ Write out a repo_license file for a role """
    now = datetime.datetime.now()
    year = now.year
    author = settings["author"]
    repo_license = settings["repo_license"]
    repo_licensej2 = "{}.j2".format(repo_license)
    licenses = os.path.join(get_templates_path(), "licenses")

    template_loader = FileSystemLoader(searchpath=licenses)
    template_env = Environment(loader=template_loader)
    template = template_env.get_template(repo_licensej2)
    data = template.render(copyright_holder=author, year=year)

    if overwrite:
        role_repo_license = os.path.join(
            settings["roles_path"], role, repo_license.upper()
        )
    else:
        role_repo_license = os.path.join(settings["output_dir"], repo_license.upper())
    with open(role_repo_license, "w") as rl:
        rl.write(data)
        log.info("Wrote license file")


def write_meta(role):
    """ Write a meta/main.yml file for galaxy """
    role_settings = read_config(role)
    author = settings["author"]
    company = settings["company"]
    repo_license = settings["repo_license"]
    branch = role_settings["branch"]
    platforms = role_settings["platforms"]
    galaxy_tags = role_settings["galaxy_tags"]
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
        lic=repo_license,
        mav=min_ansible_version,
        mcv=min_container_version,
        gh_branch=branch,
        p=platforms,
        tags=galaxy_tags,
    )

    if overwrite:
        meta = os.path.join(settings["roles_path"], role, "meta", "main.yml")
    else:
        meta = os.path.join(settings["output_dir"], "meta.yml")
    with open(meta, "w") as m:
        m.write(data)
        log.info("Wrote meta file")


def write_readme(role):
    """ Write out a new readme file """
    role_settings = read_config(role)
    author = settings["author"]
    bio = settings["bio"]
    repo_license = settings["repo_license"]
    description = role_settings["description"]
    requirements = role_settings["requirements"]
    dependencies = role_settings["dependencies"]
    example_playbook = role_settings["example_playbook"]
    templates = get_templates_path()
    task_names, role_vars = read_tasks(role)

    if not task_names:
        log.warning(
            "No task names found. Use task names to make your code easier to follow."
        )

    template_loader = FileSystemLoader(searchpath=templates)
    template_env = Environment(loader=template_loader)
    template = template_env.get_template("readme.j2")
    data = template.render(
        role_name=role,
        desc=description,
        tasks=task_names,
        reqs=requirements,
        variables=role_vars,
        deps=dependencies,
        example_playbook=example_playbook,
        lic=repo_license,
        name=author,
        author_bio=bio,
    )

    if overwrite:
        readme = os.path.join(settings["roles_path"], role, "README.md")
    else:
        readme = os.path.join(settings["output_dir"], "readme.md")
    with open(readme, "w") as r:
        r.write(data)
        log.info("Wrote README file")


def write_defaults_file(role):
    """ Writes out any default variables that don't exist already """
    roles = settings["roles_path"]
    default_vars_dict = read_defaults(role)
    _, role_vars = read_tasks(role)
    templates = get_templates_path()
    end_vars = []
    for k, v in default_vars_dict.items():
        if not v:
            log.warning("{} does not currently have a default value".format(k))

    for var in role_vars:
        if not default_vars_dict or var not in default_vars_dict:
            end_vars.append(var.strip())
            log.warning(
                "{} does not currently have a default value".format(var.strip())
            )

    template_loader = FileSystemLoader(searchpath=templates)
    template_env = Environment(loader=template_loader)
    template = template_env.get_template("defaults.j2")
    data = template.render(
        role_name=role, defaults_dict=default_vars_dict, role_vars=end_vars
    )

    if overwrite:
        defaults_dir = os.path.join(roles, role, "defaults")
        defaults = os.path.join(defaults_dir, "main.yml")
    else:
        defaults = os.path.join(settings["output_dir"], "defaults.yml")

    with open(defaults, "w") as d:
        d.write(data)
        log.info("Wrote defaults variables file")


def write_ci_file(ci_type, role):
    """ Touch the correct CI file type """
    if ci_type == "gitlab":
        ci_file = "gitlab-ci.yml"
    elif ci_type == "travis":
        ci_file = ".travis.yml"

    if overwrite:
        ci = os.path.join(settings["roles_path"], role, ci_file)
    else:
        ci = os.path.join(settings["output_dir"], ci_file)

    try:
        open(ci, "ab", 0).close()
        log.warning("No CI file present")
        log.info("Wrote CI file")
        log.warning("You have an empty CI file, please set up CI testing")
    except OSError:
        pass


if __name__ == "__main__":
    roles = []
    for fn in os.listdir(config_dir):
        if fn != "global.conf":
            f = os.path.splitext(fn)[0]
            roles.append(f)

    try:
        settings["output_dir"]
    except NameError:
        log.debug("Could not create output directory")
        pass
    else:
        create_output_dir()

    for role in roles:
        read_config(role)
        write_repo_license(role)
        write_ci_file(settings["ci_type"], role)
        write_meta(role)
        write_readme(role)
        write_defaults_file(role)
