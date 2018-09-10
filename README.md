Ansible Scribe

Ansible Scribe sets out to automate as much as it can with regards to getting a role well documented and ready for sharing with the Ansible community via Ansible Galaxy. It tries to push you towards a more easily usable role by others and pushes a few ideas of “best practices” on you:

1. You should be using roles and separate playbooks. This is the best way to make your code modular and reusable by others. 
2. You should have sane default variables set up to the point that anyone can use your role without having to change variables and it will still successfully run through. This means Ansible Scribe checks for missing and empty variables. 
3. You should have a license file defined. 
4. You should be using CI testing, so it checks for a CI file. 
5. You should use names for all of your tasks as it helps others (including those not as experienced in Ansible) to understand your code.

That being said, Ansible Scribe is not intended to just run and be done. It creates as much of the necessary documentation as it possibly can, but it will not do everything. You will at a minimum need to complete the variables table. You might also have to:

1. Convert the list of task names into a coherent description if you haven’t provided one (it will write the task names in a list in the README so you can make one). 
2. Fill out any other empty or incomplete portions of the README.md and meta/main.yml files. These will exist if you do not give all of the necessary information up front. Ansible Scribe will not create values for you, in that case it will just create the skeleton of those portions. 
3. Assign settings to the empty default variables in defaults/main.yml if there are any. 

### Ansible Scribe Does Not:

- Lint your code 
- Format your code 
- Make warnings for: 
  - Deprecated code 
  - Using incorrect modules 

Other tools exist for those things and Ansible Scribe follows the Unix Philosophy of doing one thing and doing it well. My aim is to take roles you have and make it as easy as possible to get them ready for pushing to Ansible Galaxy as quickly as possible.

What to set up comes from: (https://galaxy.ansible.com/docs/contributing/index.html)

### Inputs

Config file (~/.config/ansible-scribe/global.conf) has settings for:

- Roles path 
- Playbooks path 
- Inventory/inventory dir 
- License 
- Author 
- Optional contact info/bio 
- Optional company name 
- Path for files created via just make (aka no overwrite) 
- CI files you’d like 


Config file for individual role(s) (~/.config/ansible-scribe/rolename.conf)
- Associated playbook file name 
- Version number for galaxy (or just pull from git tag?) 
- Github/gitlab repo 
- Description OR it will pull the task names 
- Optional issue tracker url 
- Outside prereqs 
- Min_ansible_version 
- Platform name 
  - Version 
- Galaxy tags 

Pass it a role:

1. reads all the variables and creates a table for them in the readme.
  | Variable    | Purpose                              | Default |
  |-------------|--------------------------------------|---------|
  | apache_port | defines port for apache to listen on | 80      |
  | test        | a variable for testing               | none    |
2. Makes sure all the variables are in the defaults/main.yml file 
3. Takes task names and sets them in a list in readme.md file to give you a skeleton to build off of 
4. Reads playbook in order to 
  1. Add copy of example playbook to readme 
  2. Look for any roles that have namespace.rolename setup (adds to dependencies) 
5. Warns if you are missing CI files or have empty CI files 

### Make file:

- Make roles creates files in default file location outside of role path 
- Make overwrite creates files in role path 
- Make install creates empty config file
- Makefile dynamic targets for each role ([https://stackoverflow.com/questions/22754778/dynamic-makefile-target](https://stackoverflow.com/questions/22754778/dynamic-makefile-target)) 

### Outputs

1. README.md 
2. defaults/main.yml (if it doesn’t exist)
3. License file
4. meta/main.yml
5. CI file
6. Warnings for:
    1. CI files:
        1. None found - created empty file at $ci_file_location
        2. Found empty file
    2. Empty defaults variables
    3. No task names

### Other thoughts

- Grab all yml/yaml files under roles/$role/tasks/*
- Ignore variables like {{ item }} or {{ item.* }}
- Watch out for include/import role in playbook
