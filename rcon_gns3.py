#!/usr/bin/python
#
# Copyright (C) 2018 Andras Dosztal
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
Remote console for GNS3

It's very lightweight and useful in a group project where most of the
computers don't have enough resources to run virtualized devices.
"""

from __future__ import print_function
from time import sleep
import json
import os
import sys
import urllib2

def load_config():
    """
    (Re)loads the config file.
    """

    with open("config.json") as config_file:
        config_json = json.load(config_file)
        return config_json


def write_config(new_config):
    """
    Writes the modified settings to the config file
    """
    with open("config.json", "w") as config_file:
        json.dump(new_config, config_file, indent=4, sort_keys=True)
        return


def get_project(gns3_ip, gns3_port):
    """
    Gets all projects from the GNS3 server using GNS3 API. Quits on error.
    """

    url = "http://%s:%s/v2/projects" % (gns3_ip, gns3_port)

    try:
        response = urllib2.urlopen(url)
        gns3_projects = response.read()
        gns3_projects_json = json.loads(gns3_projects)
        return gns3_projects_json
    except urllib2.URLError as err:
        print("Error when connecting to GNS3 server:", err.reason)
        raw_input("Press Enter to quit.")
        quit()


def find_project_id(projects_json, gns3_project_name):
    """
    Returns the Project ID of the name project name we provided.
    """

    for project in projects_json:
        if project["name"] == gns3_project_name:
            project_id = project["project_id"]
            break

    if project_id:
        return project_id
    else:
        raw_input("Error: Unknown project. Press Enter to quit.")
        quit()


def get_nodes(gns3_ip, gns3_port, gns3_project_id):
    """
    Gets the nodes of the selected project from the GNS3 server using
    GNS3 API and returns the list of those. Quits on error.
    """

    url = "http://%s:%s/v2/projects/%s/nodes" % (gns3_ip, gns3_port, gns3_project_id)

    try:
        response = urllib2.urlopen(url)
        gns3_nodes = response.read()
        gns3_nodes_json = json.loads(gns3_nodes)
        return gns3_nodes_json

    except urllib2.URLError as err:
        print("Error when connecting to GNS3 server:", err.reason)
        raw_input("Press Enter to quit.")
        quit()


def parse_nodes(nodes_json):
    """
    Filters the node list in two ways:

    1) Removes all nodes without console. Keeps the following node types:
       dynamips, docker, iou, qemu

    2) Removes unnecessary information (e.g. ports, node position, etc.) and keeps
       only the following fields:
        - "name" - The node's name
        - "console" - TCP port
        - "console_host" - IP address of the GNS3 server running the node
        - "console type" - telnet / vnc

    Returns a list of the nodes with lists from the properties above.
    """

    parsed_nodes_list = []
    for node in nodes_json:
        node_type = node["node_type"]
        if "dynamips" in node_type or "docker" in node_type or "iou" in node_type \
        or "qemu" in node_type or "ethernet_switch" in node_type:
            parsed_nodes_list.append([node["name"], node["console_host"], \
                                      node["console"], node["console_type"]])

    if parsed_nodes_list:
        return parsed_nodes_list
    else:
        raw_input("Error: There are no applicable nodes in the project! Press Enter to continue.")


def console_connect():
    """
    This function does the primary job: initiating telnet/vnc sessions
    to the selected nodes.
    """

    config = load_config()
    config_ip = config["server"]["ip"]
    config_port = config["server"]["port"]
    config_project_name = config["project"]
    config_console_telnet = config["console"]["telnet_selected"]
    config_console_vnc = config["console"]["vnc_selected"]

    node_menu = True
    while node_menu:
        # Get a list of nodes of the selected project
        projects = get_project(config_ip, config_port)
        project_id = find_project_id(projects, config_project_name)
        nodes_list = get_nodes(config_ip, config_port, project_id)
        parsed_nodes = parse_nodes(nodes_list)

        # Print nodes, asks for user input
        if parsed_nodes:
            os.system("cls" if os.name == "nt" else "clear")
            print (
                """Remote Console for GNS3\n"""
                """=======================\n\n"""
                """Choose an option:""")
            i = 1
            for parsed_node in parsed_nodes:
                print("%d) %s" % (i, parsed_node[0]))
                i += 1
            print("%d) Open all consoles" % i)
            i += 1
            print("%d) Return to main menu" % i)
            i += 1
            print("%d) Exit\n" % i)
            node_choice = raw_input("Enter your choice: ")

            # The try below checks input value; if it's not a number then sets the value
            # so high that it will always be out of range
            try:
                node_choice = int(node_choice)
            except ValueError as err:
                node_choice = 9999
                raw_input("Error: %s\nPress Enter to try again." % err)
            else:
                if node_choice > i: # Higher number was entered than the available options
                    raw_input("Wrong selection. Press Enter to try again.")
                elif node_choice == i: # Last option is always exiting
                    quit()
                elif node_choice == i-1: # Going back to the main menu
                    node_menu = False
                elif node_choice == i-2: # Opening all nodes
                    for node in parsed_nodes:
                        if node[3] == "telnet":
                            if config_console_telnet == "Custom":
                                console_cmd = config["console"]["telnet_custom"].replace("%d", node[0])
                                console_cmd = console_cmd.replace("%h", node[1])
                                console_cmd = console_cmd.replace("%p", str(node[2]))
                            else:
                                # The following command selects the telnet command from the
                                # predefined list, then replaces the %s variables with the
                                # name, ip, and port values. Then the command is executed.
                                console_cmd = TELNET_CMD[config_console_telnet].replace("%d", node[0])
                                console_cmd = console_cmd.replace("%h", node[1])
                                console_cmd = console_cmd.replace("%p", str(node[2]))
                        elif node[3] == "vnc":
                            if config_console_vnc == "Custom":
                                console_cmd = config["console"]["vnc_custom"].replace("%h", node[1])
                                console_cmd = console_cmd.replace("%p", str(node[2]))
                            else:
                                console_cmd = VNC_CMD[config_console_vnc].replace("%h", node[1])
                                console_cmd = console_cmd.replace("%p", str(node[2]))
                        os.system(console_cmd)
                        sleep(0.333)
                else: # Opening the selected node
                    selected_node = node_choice-1 # List count starts from zero; our list from 1

                    # Checks if the node required telnet or VNCm then, as above, replaces the
                    # %d/%h/%p variables witn the name, ip, and port values.
                    # Then the command is executed.
                    if parsed_nodes[selected_node][3] == "telnet":
                        console_cmd = TELNET_CMD[config_console_telnet].replace("%d", parsed_nodes[selected_node][0])
                        console_cmd = console_cmd.replace("%h", parsed_nodes[selected_node][1])
                        console_cmd = console_cmd.replace("%p", str(parsed_nodes[selected_node][2]))
                        os.system(console_cmd)
                    elif parsed_nodes[selected_node][3] == "vnc":
                        console_cmd = VNC_CMD[config_console_vnc].replace("%h", parsed_nodes[selected_node][1])
                        console_cmd = console_cmd.replace("%p", str(parsed_nodes[selected_node][2]))
                        os.system(console_cmd)
    return


def switch_project(gns3_ip, gns3_port):
    """
    If the group leader loads a new project, users can switch here.
    """

    i = 0
    menu_projects = True
    projects = get_project(gns3_ip, gns3_port) # Retrieves all projects

    while menu_projects:
        os.system("cls" if os.name == "nt" else "clear")
        print (
            """Remote Console for GNS3\n"""
            """=======================\n\n"""
            """Available projects:""")
        for project in projects:
            # Printing the projects' names
            i += 1
            print("%d) %s" % (i, project["name"]))
        project_choice = raw_input("\nEnter your choice: ")
        try:
            project_choice = int(project_choice)
        except ValueError as err:
            raw_input("Error: %s \nPress Enter to continue." % err)
        else:
            # Replacing the project name in the config file
            config = load_config()
            config["project"] = projects[project_choice-1]["name"]
            write_config(config)
            return


def set_server(old_ip, old_port):
    """
    Setting new GNS3 IP address and port.
    """

    server_menu = True
    while server_menu:
        # Asking for user input
        os.system("cls" if os.name == "nt" else "clear")
        print (
            """Remote Console for GNS3\n"""
            """=======================\n\n""")
        new_ip = raw_input("Enter the GNS3 server IP [%s]: " % old_ip)
        new_port = raw_input("Enter the GNS3 server IP [%s]: " % old_port)

        # Input checking, if nothing is entered, the old values will be used
        if not new_ip:
            new_ip = old_ip
        if not new_port:
            new_port = old_port

        # Validation by making an API call
        url = "http://%s:%s/v2/projects" % (new_ip, new_port)

        try:
            response = urllib2.urlopen(url)
        except urllib2.URLError as err:
            err_message = "Error when connecting to GNS3 server: %s)" % err.reason
            raw_input("%s\nPress Enter to try again." % err_message)
        else:
            # Replacing the server settings in the config file
            config = load_config()
            config["server"]["ip"] = new_ip
            config["server"]["port"] = new_port
            write_config(config)
            return


def set_telnet():
    """
    Changing the Telnet client.
    """
    config = load_config()
    config_console_telnet = config["console"]["telnet_selected"]
    config_custom_cmd = config["console"]["telnet_custom"]
    telnet_menu = True
    telnet_new = None
    telnet_custom_new = None

    while telnet_menu:
        telnet_menu = False
        os.system("cls" if os.name == "nt" else "clear")
        print(
            """Remote Console for GNS3\n"""
            """=======================\n\n"""
            """Choose an option:\n""")
        if sys.platform.startswith("win"):
            print(
                """1) Putty\n"""
                """2) MobaXterm\n"""
                """3) Royal TS\n"""
                """4) SuperPutty\n"""
                """5) SecureCRT\n"""
                """6) SecureCRT (personal profile)\n"""
                """7) TeraTerm Pro\n"""
                """8) Telnet\n"""
                """9) Xshell 4\n"""
                """10) Xshell 5\n"""
                """11) ZOC 6\n"""
                """12) Custom [%s]\n"""
                """13) Return to main menu\n""" % config_custom_cmd)

            telnet_choice = raw_input("Enter your choice [%s]: " % config_console_telnet)

            if not telnet_choice:
                telnet_choice = "13"

            if telnet_choice == "1":
                telnet_new = "Putty"
            elif telnet_choice == "2":
                telnet_new = "MobaXterm"
            elif telnet_choice == "3":
                telnet_new = "Royal TS"
            elif telnet_choice == "4":
                telnet_new = "SuperPutty"
            elif telnet_choice == "5":
                telnet_new = "SecureCRT"
            elif telnet_choice == "6":
                telnet_new = "SecureCRT (personal profile)"
            elif telnet_choice == "7":
                telnet_new = "TeraTerm Pro"
            elif telnet_choice == "8":
                telnet_new = "Telnet"
            elif telnet_choice == "9":
                telnet_new = "Xshell 4"
            elif telnet_choice == "10":
                telnet_new = "Xshell 5"
            elif telnet_choice == "11":
                telnet_new = "ZOC 6"
            elif telnet_choice == "12":
                telnet_custom_new = raw_input("Enter the custom command: ")
                telnet_new = "Custom"
            elif telnet_choice == "13":
                telnet_menu = False
            else:
                telnet_menu = True
                raw_input("Error: Wrong selection. Press Enter to continue.")
            # I know this was awful but python dictionaries are
            # unordered and this is a static list.

        else:
            print(
                """1) Xterm\n"""
                """2) Putty\n"""
                """3) Gnome Terminal\n"""
                """4) Xfce4 Terminal\n"""
                """5) ROXTerm\n"""
                """6) KDE Konsole\n"""
                """7) SecureCRT\n"""
                """8) Mate Terminal\n"""
                """9) urxvt\n"""
                """10) Custom [%s]\n"""
                """11) Return to main menu\n""" % config_custom_cmd)
            telnet_choice = raw_input("Enter your choice [%s]: " % config_console_telnet)

            if not telnet_choice:
                telnet_choice = "11"

            if telnet_choice == "1":
                telnet_new = "Xterm"
            elif telnet_choice == "2":
                telnet_new = "Putty"
            elif telnet_choice == "3":
                telnet_new = "Gnome Terminal"
            elif telnet_choice == "4":
                telnet_new = "Xfce4 Terminal"
            elif telnet_choice == "5":
                telnet_new = "ROXTerm"
            elif telnet_choice == "6":
                telnet_new = "KDE Konsole"
            elif telnet_choice == "7":
                telnet_new = "SecureCRT"
            elif telnet_choice == "8":
                telnet_new = "Mate Terminal"
            elif telnet_choice == "9":
                telnet_new = "urxvt"
            elif telnet_choice == "10":
                telnet_custom_new = raw_input("Enter the custom command: ")
                telnet_new = "Custom"
            elif telnet_choice == "11":
                telnet_menu = False
            else:
                telnet_menu = True
                raw_input("Error: Wrong selection. Press Enter to continue.")
    if telnet_new:
        config["console"]["telnet_selected"] = telnet_new
        if telnet_custom_new:
            config["console"]["telnet_custom"] = telnet_custom_new
        write_config(config)
    return


def set_vnc():
    """
    Changing the VNC client.
    """
    config = load_config()
    config_console_vnc = config["console"]["vnc_selected"]
    config_custom_cmd = config["console"]["vnc_custom"]
    vnc_menu = True
    vnc_new = None
    vnc_custom_new = None

    while vnc_menu:
        vnc_menu = False
        os.system("cls" if os.name == "nt" else "clear")
        print(
            """Remote Console for GNS3\n"""
            """=======================\n\n"""
            """Choose an option:\n""")
        if sys.platform.startswith("win"):
            print(
                """1) TightVNC\n"""
                """2) UltraVNC\n"""
                """3) Custom [%s]\n"""
                """4) Return to main menu\n""" % config_custom_cmd)

            vnc_choice = raw_input("Enter your choice [%s]: " % config_console_vnc)

            if not vnc_choice:
                vnc_choice = "4"

            if vnc_choice == "1":
                vnc_new = "TightVNC"
            elif vnc_choice == "2":
                vnc_new = "UltraVNC"
            elif vnc_choice == "3":
                vnc_custom_new = raw_input("Enter the custom command: ")
                vnc_new = "Custom"
            elif vnc_choice == "4":
                vnc_menu = False
            else:
                vnc_menu = True
                raw_input("Error: Wrong selection. Press Enter to continue.")

        else:
            print(
                """1) TightVNC\n"""
                """2) vinagre\n"""
                """3) gvncviewer\n"""
                """4) Custom [%s]\n"""
                """5) Return to main menu\n""" % config_custom_cmd)
            vnc_choice = raw_input("Enter your choice [%s]: " % config_console_vnc)

            if not vnc_choice:
                vnc_choice = "5"

            if vnc_choice == "1":
                vnc_new = "TightVNC"
            elif vnc_choice == "2":
                vnc_new = "vinagre"
            elif vnc_choice == "3":
                vnc_new = "gvncviewer"
            elif vnc_choice == "4":
                vnc_custom_new = raw_input("Enter the custom command: ")
                vnc_new = "Custom"
            elif vnc_choice == "5":
                vnc_menu = False
            else:
                vnc_menu = True
                raw_input("Error: Wrong selection. Press Enter to continue.")
    if vnc_new:
        config["console"]["vnc_selected"] = vnc_new
        if vnc_custom_new:
            config["console"]["vnc_custom"] = vnc_custom_new
        write_config(config)
    return


def main():
    """
    Main menu.
    """

    main_menu = True
    while main_menu:
        # (Re)loading config from file
        config = load_config()
        config_ip = config["server"]["ip"]
        config_port = config["server"]["port"]
        config_project_name = config["project"]
        config_console_telnet = config["console"]["telnet_selected"]
        config_console_vnc = config["console"]["vnc_selected"]

        # Printing menu that displays the current settings too
        os.system("cls" if os.name == "nt" else "clear")
        print(
            """Remote Console for GNS3\n"""
            """=======================\n\n"""
            """Choose an option:\n"""
            """1) Connect to nodes in current project\n"""
            """2) Set GNS3 server [%s:%s]\n"""
            """3) Switch project [%s]\n"""
            """4) Set Telnet client [%s]\n"""
            """5) Set VNC client [%s]\n"""
            """6) Exit\n""" \
                % (config_ip, config_port, config_project_name, \
                   config_console_telnet, config_console_vnc))
        main_choice = raw_input("Enter your choice: ")

        # Evaluating user choice
        if main_choice == "1":
            console_connect()
        elif main_choice == "2":
            switch_project(config_ip, config_port)
        elif main_choice == "3":
            set_server(config_ip, config_port)
        elif main_choice == "4":
            set_telnet()
        elif main_choice == "5":
            set_vnc()
        elif main_choice == "6":
            main_menu = False
        else:
            raw_input("Error: Wrong selection. Press Enter to continue.")

if sys.platform.startswith("win"):
    userprofile = os.path.expandvars("%USERPROFILE%")
    if "PROGRAMFILES(X86)" in os.environ:
        # windows 64-bit
        program_files = os.environ["PROGRAMFILES"]
        program_files_x86 = os.environ["PROGRAMFILES(X86)"]
    else:
        # windows 32-bit
        program_files_x86 = program_files = os.environ["PROGRAMFILES"]

    TELNET_CMD = {'Putty': 'putty.exe -telnet %h %p -wt "%d" -gns3 5 -skin 4',
                  'MobaXterm': r'"{}\Mobatek\MobaXterm Personal Edition\MobaXterm.exe" -newtab "telnet %h %p"'.format(program_files_x86),
                  'Royal TS': '{}\code4ward.net\Royal TS V3\RTS3App.exe /connectadhoc:%h /adhoctype:terminal /p:IsTelnetConnection="true" /p:ConnectionType="telnet;Telnet Connection" /p:Port="%p" /p:Name="%d"'.format(program_files),
                  'SuperPutty': r'SuperPutty.exe -telnet "%h -P %p -wt \"%d\""',
                  'SecureCRT': r'"{}\VanDyke Software\SecureCRT\SecureCRT.exe" /N "%d" /T /TELNET %h %p'.format(program_files),
                  'SecureCRT (personal profile)': r'"{}\AppData\Local\VanDyke Software\SecureCRT\SecureCRT.exe" /T /N "%d" /TELNET %h %p'.format(userprofile),
                  'TeraTerm Pro': r'"{}\teraterm\ttermpro.exe" /W="%d" /M="ttstart.macro" /T=1 %h %p'.format(program_files_x86),
                  'Telnet': 'cmd /C telnet %h %p',
                  'Xshell 4': r'"{}\NetSarang\Xshell 4\xshell.exe" -url telnet://%h:%p'.format(program_files_x86),
                  'Xshell 5': r'"{}\NetSarang\Xshell 5\xshell.exe" -url telnet://%h:%p -newtab %d'.format(program_files_x86),
                  'ZOC 6': r'"{}\ZOC6\zoc.exe" "/TELNET:%h:%p" /TABBED "/TITLE:%d"'.format(program_files_x86)}

    VNC_CMD = {'TightVNC': 'tvnviewer.exe %h:%p',
               'UltraVNC': 'C:\\Program Files\\uvnc bvba\\UltraVNC\\vncviewer.exe %h:%p'
    }

else:
    devnull = ' >/dev/null 2>/dev/null &'
    TELNET_CMD = {'Xterm': 'xterm -T "%d" -e "telnet %h %p"' + devnull,
                  'Putty': 'putty -telnet %h %p -title "%d" -sl 2500 -fg SALMON1 -bg BLACK' + devnull,
                  'Gnome Terminal': 'gnome-terminal -t "%d" -e "telnet %h %p"' + devnull,
                  'Xfce4 Terminal': 'xfce4-terminal --tab -T "%d" -e "telnet %h %p"' + devnull,
                  'ROXTerm': 'roxterm -n "%d" --tab -e "telnet %h %p"' + devnull,
                  'KDE Konsole': 'konsole --new-tab -p tabtitle="%d" -e "telnet %h %p"' + devnull,
                  'SecureCRT': 'SecureCRT /T /N "%d"  /TELNET %h %p' + devnull,
                  'Mate Terminal': 'mate-terminal --tab -e "telnet %h %p"  -t "%d"' + devnull,
                  'urxvt': 'urxvt -title %d -e telnet %h %p' + devnull}

    VNC_CMD = {"TightVNC": 'vncviewer %h:%p' + devnull,
               "Vinagre": 'vinagre %h:%p' + devnull,
               "gvncviewer": 'gvncviewer %h:%p' + devnull}


if __name__ == "__main__":
    main()
