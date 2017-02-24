#!/usr/bin/python
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '1.0'}

DOCUMENTATION = '''
---
module: ce_netstream_template
version_added: "2.3"
short_description: Manages NetStream template configuration.
description:
    - Manages NetStream template configuration on CloudEngine switches.
author:
    - wangdezhuang (@CloudEngine-Ansible)
options:
    state:
        description:
            - Specify desired state of the resource.
        required: false
        default: present
        choices: ['present', 'absent']
    type:
        description:
            - Configure the type of netstream record.
        required: true
        choices: ['ip', 'vxlan']
    record_name:
        description:
            - Configure the name of netstream record.
              The value is a string of 1 to 32 case-insensitive characters.
        required: false
        default: null
    match:
        description:
            - Configure flexible flow statistics template keywords.
        required: false
        default: null
        choices: ['destination-address', 'destination-port', 'tos', 'protocol', 'source-address', 'source-port']
    collect_counter:
        description:
            - Configure the number of packets and bytes that are included in the flexible flow statistics sent to NSC.
        required: false
        default: null
        choices: ['bytes', 'packets']
    collect_interface:
        description:
            - Configure the input or output interface that are included in the flexible flow statistics sent to NSC.
        required: false
        default: null
        choices: ['input', 'output']
    description:
        description:
            - Configure the description of netstream record.
              The value is a string of 1 to 80 case-insensitive characters.
        required: false
        default: null
'''

EXAMPLES = '''
# config ipv4 netstream record
- ce_netstream_template:
    state:  present
    type:  ip
    record_name:  test
    username: "{{ un }}"
    password: "{{ pwd }}"
    host: "{{ inventory_hostname }}"
# undo ipv4 netstream record
- ce_netstream_template:
    state:  absent
    type:  ip
    record_name:  test
    username: "{{ un }}"
    password: "{{ pwd }}"
    host: "{{ inventory_hostname }}"
# config ipv4 netstream record collect_counter
- ce_netstream_template:
    state:  present
    type:  ip
    record_name:  test
    collect_counter:  bytes
    username: "{{ un }}"
    password: "{{ pwd }}"
    host: "{{ inventory_hostname }}"
# undo ipv4 netstream record collect_counter
- ce_netstream_template:
    state:  absent
    type:  ip
    record_name:  test
    collect_counter:  bytes
    username: "{{ un }}"
    password: "{{ pwd }}"
    host: "{{ inventory_hostname }}"
'''

RETURN = '''
changed:
    description: check to see if a change was made on the device
    returned: always
    type: boolean
    sample: true
proposed:
    description: k/v pairs of parameters passed into module
    returned: always
    type: dict
    sample: {"record_name": "test",
             "type": "ip",
             "state": "present"}
existing:
    description:
        - k/v pairs of existing aaa server
    type: dict
    sample: {}
end_state:
    description: k/v pairs of aaa params after module execution
    returned: always
    type: dict
    sample: {"record_name": "test",
             "type": "ip"}
updates:
    description: command sent to the device
    returned: always
    type: list
    sample: ["netstream record test ip"]
'''

import re
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ce import get_config, load_config
from ansible.module_utils.ce import ce_argument_spec


class NetstreamTemplate(object):
    """ Manages netstream template configuration """

    def __init__(self, **kwargs):
        """ Netstream template module init """

        # module
        argument_spec = kwargs["argument_spec"]
        self.spec = argument_spec
        self.module = AnsibleModule(argument_spec=self.spec, supports_check_mode=True)

        # netstream config
        self.netstream_cfg = None

        # module args
        self.state = self.module.params['state'] or None
        self.type = self.module.params['type'] or None
        self.record_name = self.module.params['record_name'] or None
        self.match = self.module.params['match'] or None
        self.collect_counter = self.module.params['collect_counter'] or None
        self.collect_interface = self.module.params['collect_interface'] or None
        self.description = self.module.params['description'] or None

        # state
        self.changed = False
        self.updates_cmd = list()
        self.results = dict()
        self.proposed = dict()
        self.existing = dict()
        self.end_state = dict()

    def cli_load_config(self, commands):
        """ Cli load configuration """

        if not self.module.check_mode:
            load_config(self.module, commands)

    def cli_get_netstream_config(self):
        """ Cli get netstream configuration """

        if self.type == "ip":
            cmd = "netstream record %s ip" % self.record_name
        else:
            cmd = "netstream record %s vxlan inner-ip" % self.record_name
        flags = list()
        regular = "| section include %s" % cmd
        flags.append(regular)
        self.netstream_cfg = get_config(self.module, flags)

    def check_args(self):
        """ Check module args """

        if not self.type or not self.record_name:
            self.module.fail_json(
                msg='Error: Please input type and record_name.')

        if self.record_name:
            if len(self.record_name) < 1 or len(self.record_name) > 32:
                self.module.fail_json(
                    msg='Error: The len of record_name is out of [1 - 32].')

        if self.description:
            if len(self.description) < 1 or len(self.description) > 80:
                self.module.fail_json(
                    msg='Error: The len of description is out of [1 - 80].')

    def get_proposed(self):
        """ Get module proposed """

        self.proposed["state"] = self.state

        if self.type:
            self.proposed["type"] = self.type
        if self.record_name:
            self.proposed["record_name"] = self.record_name
        if self.match:
            self.proposed["match"] = self.match
        if self.collect_counter:
            self.proposed["collect_counter"] = self.collect_counter
        if self.collect_interface:
            self.proposed["collect_interface"] = self.collect_interface
        if self.description:
            self.proposed["description"] = self.description

    def get_existing(self):
        """ Get existing configuration """

        self.cli_get_netstream_config()

        if self.netstream_cfg:
            self.existing["type"] = self.type
            self.existing["record_name"] = self.record_name

            if self.description:
                tmp_value = re.findall(r'description (.*)', self.netstream_cfg)
                if tmp_value:
                    self.existing["description"] = tmp_value[0]

            if self.match:
                if self.type == "ip":
                    tmp_value = re.findall(r'match ip (.*)', self.netstream_cfg)
                else:
                    tmp_value = re.findall(r'match inner-ip (.*)', self.netstream_cfg)

                if tmp_value:
                    self.existing["match"] = tmp_value

            if self.collect_counter:
                tmp_value = re.findall(r'collect counter (.*)', self.netstream_cfg)
                if tmp_value:
                    self.existing["collect_counter"] = tmp_value

            if self.collect_interface:
                tmp_value = re.findall(r'collect interface (.*)', self.netstream_cfg)
                if tmp_value:
                    self.existing["collect_interface"] = tmp_value

    def get_end_state(self):
        """ Get end state """

        self.cli_get_netstream_config()

        if self.netstream_cfg:
            self.end_state["type"] = self.type
            self.end_state["record_name"] = self.record_name

            if self.description:
                tmp_value = re.findall(r'description (.*)', self.netstream_cfg)
                if tmp_value:
                    self.end_state["description"] = tmp_value[0]

            if self.match:
                if self.type == "ip":
                    tmp_value = re.findall(r'match ip (.*)', self.netstream_cfg)
                else:
                    tmp_value = re.findall(r'match inner-ip (.*)', self.netstream_cfg)

                if tmp_value:
                    self.end_state["match"] = tmp_value

            if self.collect_counter:
                tmp_value = re.findall(r'collect counter (.*)', self.netstream_cfg)
                if tmp_value:
                    self.end_state["collect_counter"] = tmp_value

            if self.collect_interface:
                tmp_value = re.findall(r'collect interface (.*)', self.netstream_cfg)
                if tmp_value:
                    self.end_state["collect_interface"] = tmp_value

    def present_netstream(self):
        """ Present netstream configuration """

        cmds = list()
        need_create_record = False

        if self.type == "ip":
            cmd = "netstream record %s ip" % self.record_name
        else:
            cmd = "netstream record %s vxlan inner-ip" % self.record_name
        cmds.append(cmd)

        if not self.netstream_cfg:
            self.updates_cmd.append(cmd)
            need_create_record = True

        if self.description:
            cmd = "description %s" % self.description
            if not self.netstream_cfg or cmd not in self.netstream_cfg:
                cmds.append(cmd)
                self.updates_cmd.append(cmd)

        if self.match:
            if self.type == "ip":
                cmd = "match ip %s" % self.match
                cfg = "match ip"
            else:
                cmd = "match inner-ip %s" % self.match
                cfg = "match inner-ip"

            if not self.netstream_cfg or cfg not in self.netstream_cfg or self.match != self.existing["match"][0]:
                cmds.append(cmd)
                self.updates_cmd.append(cmd)

        if self.collect_counter:
            cmd = "collect counter %s" % self.collect_counter
            if not self.netstream_cfg or cmd not in self.netstream_cfg:
                cmds.append(cmd)
                self.updates_cmd.append(cmd)

        if self.collect_interface:
            cmd = "collect interface %s" % self.collect_interface
            if not self.netstream_cfg or cmd not in self.netstream_cfg:
                cmds.append(cmd)
                self.updates_cmd.append(cmd)

        if not need_create_record and len(cmds) == 1:
            if self.type == "ip":
                cmd = "netstream record %s ip" % self.record_name
            else:
                cmd = "netstream record %s vxlan inner-ip" % self.record_name
            cmds.remove(cmd)

        if cmds:
            self.cli_load_config(cmds)
            self.changed = True

    def absent_netstream(self):
        """ Absent netstream configuration """

        cmds = list()
        absent_netstream_attr = False

        if not self.netstream_cfg:
            return

        if self.description or self.match or self.collect_counter or self.collect_interface:
            absent_netstream_attr = True

        if absent_netstream_attr:
            if self.type == "ip":
                cmd = "netstream record %s ip" % self.record_name
            else:
                cmd = "netstream record %s vxlan inner-ip" % self.record_name

            cmds.append(cmd)

            if self.description:
                cfg = "description %s" % self.description
                if self.netstream_cfg and cfg in self.netstream_cfg:
                    cmd = "undo description %s" % self.description
                    cmds.append(cmd)
                    self.updates_cmd.append(cmd)

            if self.match:
                if self.type == "ip":
                    cfg = "match ip %s" % self.match
                else:
                    cfg = "match inner-ip %s" % self.match
                if self.netstream_cfg and cfg in self.netstream_cfg:
                    if self.type == "ip":
                        cmd = "undo match ip %s" % self.match
                    else:
                        cmd = "undo match inner-ip %s" % self.match
                    cmds.append(cmd)
                    self.updates_cmd.append(cmd)

            if self.collect_counter:
                cfg = "collect counter %s" % self.collect_counter
                if self.netstream_cfg and cfg in self.netstream_cfg:
                    cmd = "undo collect counter %s" % self.collect_counter
                    cmds.append(cmd)
                    self.updates_cmd.append(cmd)

            if self.collect_interface:
                cfg = "collect interface %s" % self.collect_interface
                if self.netstream_cfg and cfg in self.netstream_cfg:
                    cmd = "undo collect interface %s" % self.collect_interface
                    cmds.append(cmd)
                    self.updates_cmd.append(cmd)

            if len(cmds) > 1:
                self.cli_load_config(cmds)
                self.changed = True

        else:
            if self.type == "ip":
                cmd = "undo netstream record %s ip" % self.record_name
            else:
                cmd = "undo netstream record %s vxlan inner-ip" % self.record_name

            cmds.append(cmd)
            self.updates_cmd.append(cmd)

            self.cli_load_config(cmds)
            self.changed = True

    def work(self):
        """ Work function """

        self.check_args()
        self.get_proposed()
        self.get_existing()

        if self.state == "present":
            self.present_netstream()
        else:
            self.absent_netstream()

        self.get_end_state()

        self.results['changed'] = self.changed
        self.results['proposed'] = self.proposed
        self.results['existing'] = self.existing
        self.results['end_state'] = self.end_state
        self.results['updates'] = self.updates_cmd

        self.module.exit_json(**self.results)


def main():
    """ Module main """

    argument_spec = dict(
        state=dict(choices=['present', 'absent'], default='present'),
        type=dict(choices=['ip', 'vxlan'], required=True),
        record_name=dict(type='str'),
        match=dict(choices=['destination-address', 'destination-port',
                            'tos', 'protocol', 'source-address', 'source-port']),
        collect_counter=dict(choices=['bytes', 'packets']),
        collect_interface=dict(choices=['input', 'output']),
        description=dict(type='str')
    )
    argument_spec.update(ce_argument_spec)
    module = NetstreamTemplate(argument_spec=argument_spec)
    module.work()


if __name__ == '__main__':
    main()
