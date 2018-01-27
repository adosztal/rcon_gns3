#!/usr/bin/python

"""
Remote console for GNS3

It's useful when
"""

from __future__ import print_function
from time import sleep
import json
import urllib2
import os


def load_config():
    """
    (Re)loads the config file.
    """

    with open("config.json") as config_file:
        config_json = json.load(config_file)
        return config_json


def write_config(new_config):
    """
    Writes new settings to the config file
    """
    with open("config.json", "w") as config_file:
        json.dump(new_config, config_file)
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
        print("Error: Unknown project.")
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

    devnull = ' >/dev/null 2>/dev/null &'

    telnet_cmd = {"Xterm": 'xterm -T "%s" -e "telnet %s %s"' + devnull,
                  "Putty": 'putty -title "%s" -telnet %s %s -sl 2500 -fg SALMON1 -bg BLACK' + devnull,
                  "Gnome Terminal": 'gnome-terminal -t "%s" -e "telnet %s %s"' + devnull,
                  "Xfce4 Terminal": 'xfce4-terminal --tab -T "%s" -e "telnet %s %s"' + devnull,
                  "ROXTerm": 'roxterm -n "%s" --tab -e "telnet %s %s"' + devnull,
                  "KDE Konsole": 'konsole --new-tab -p tabtitle="%s" -e "telnet %s %s"' + devnull,
                  "SecureCRT": 'SecureCRT /T /N "%s"  /TELNET %s %s' + devnull,
                  "Mate Terminal": 'mate-terminal --tab -e "telnet %s %s" -t "%s"' + devnull,
                  "Custom": '%s' + devnull % config["console"]["telnet_custom"]}

    vnc_cmd = {
        "TightVNC": 'vncviewer %s:%s' + devnull,
        "Vinagre": 'vinagre %s:%s' + devnull,
        "gvncviewer": 'gvncviewer %s:%s' + devnull,
        "Custom" : '%s >/dev/null 2>/dev/null &' % config["console"]["vnc_custom"]
    }

    node_menu = True
    while node_menu:
        # Get a list of nodes of the selected project
        projects = get_project(config_ip, config_port)
        project_id = find_project_id(projects, config_project_name)
        nodes_list = get_nodes(config_ip, config_port, project_id)
        parsed_nodes = parse_nodes(nodes_list)

        # Print nodes
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
            try:
                node_choice = int(node_choice)
            except ValueError as err:
                node_choice = 9999
                raw_input("Error: %s\nWrong selection. Press Enter to try again." % err)
            else:
                if node_choice > i:
                    raw_input("Wrong selection. Press Enter to try again.")
                elif node_choice == i:
                    quit()
                elif node_choice == i-1: # Going back to the main menu
                    node_menu = False
                elif node_choice == i-2: # Opening all nodes
                    for node in parsed_nodes:
                        print(node)
                        if node[3] == "telnet":
                            console_cmd = telnet_cmd[config_console_telnet] % \
                                                (node[0], \
                                                node[1], \
                                                node[2])
                            os.system(console_cmd)
                        elif node[3] == "vnc":
                            console_cmd = vnc_cmd[config_console_vnc] % ( \
                                                node[1], \
                                                node[2])
                            os.system(console_cmd)
                        sleep(0.333)
                else: # Opening the selected node
                    selected_node = node_choice-1
                    if parsed_nodes[selected_node][3] == "telnet":
                        console_cmd = telnet_cmd[config_console_telnet] % \
                                            (parsed_nodes[selected_node][0], \
                                            parsed_nodes[selected_node][1], \
                                            parsed_nodes[selected_node][2])
                        os.system(console_cmd)
                    elif parsed_nodes[selected_node][3] == "vnc":
                        console_cmd = vnc_cmd[config_console_vnc] % ( \
                                            parsed_nodes[selected_node][1], \
                                            parsed_nodes[selected_node][2])
                        os.system(console_cmd)
        return


def switch_project(gns3_ip, gns3_port):
    """
    If the group leader loads a new project, users can switch here.
    """

    i = 0
    projects = get_project(gns3_ip, gns3_port)
    os.system("cls" if os.name == "nt" else "clear")
    print (
        """Remote Console for GNS3\n"""
        """=======================\n\n"""
        """Available projects:""")
    for project in projects:
        i += 1
        print("%d) %s" % (i, project["name"]))
    project_choice = raw_input("\nEnter your choice: ")
    try:
        project_choice = int(project_choice)
    except ValueError as err:
        raw_input("Error: %s \nPress Enter to continue." % err)
    else:
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
        os.system("cls" if os.name == "nt" else "clear")
        print (
            """Remote Console for GNS3\n"""
            """=======================\n\n""")
        new_ip = raw_input("Enter the GNS3 server IP [%s]: " % old_ip)
        new_port = raw_input("Enter the GNS3 server IP [%s]: " % old_port)

        # Input checking
        if not new_ip:
            new_ip = old_ip
        if not new_port:
            new_port = old_port

        # Validation
        url = "http://%s:%s/v2/projects" % (new_ip, new_port)

        try:
            response = urllib2.urlopen(url)
        except urllib2.URLError as err:
            err_message = "Error when connecting to GNS3 server: %s)" % err.reason
            raw_input("%s\nPress Enter to try again." % err_message)
        else:
            config = load_config()
            config["server"]["ip"] = new_ip
            config["server"]["port"] = new_port
            write_config(config)
            return


def set_telnet(old_telnet):
    """
    Changing the Telnet client.
    """
    pass


def set_vnc(old_vnc):
    """
    Changing the VNC client.
    """
    pass


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
            """2) Switch project [%s]\n"""
            """3) Set GNS3 server [%s:%s]\n"""
            """4) Set Telnet client [%s]\n"""
            """5) Set VNC client [%s]\n"""
            """6) Exit\n""" \
                % (config_project_name, config_ip, config_port, \
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
            set_telnet(config_console_telnet)
        elif main_choice == "5":
            set_vnc(config_console_vnc)
        elif main_choice == "6":
            main_menu = False
        else:
            raw_input("Error: Wrong selection. Press Enter to continue.")


if __name__ == "__main__":
    main()
