#! /usr/bin/python3

"""This script sources current environment for DAOS client programs"""

import os
import sys
import subprocess
from envbash import load_envbash

def get_tool_path(cmd):
    """get the tool path using which program """
    res = subprocess.check_output(["which", "%s"% cmd])
    return res.decode(sys.stdout.encoding).strip()


class DaosBashEnv:
    """ Environment  class
	__init__ method currently loads the environmnet  file
	for bash shell for identifying DAOS executables in
	this platform.
        Currently only supports  bash shell and only supports
	FIO and daos_perf.
	TODO: To extend to use it with manually  populated  paths
	for different DAOS client application  based on usage
    """
    def set_environ(self):
        """Set the environmnet file using envbash supports only bash shell"""
        print("\n\n")
        print("DAOS Test Environment")
        print("----------------------")
        print("\u0332".join("Loading env file "), self.env)
        load_envbash(self.env, override=True, remove=True)


    def get_test_tools(self):
        """ Populate all attributes for this class which  are basically
	    DAOS tools
        """
        self.fio = get_tool_path("fio")
        self.fio_plugin = get_tool_path("daos_fio_async")
        self.daos = get_tool_path("daos")
        self.dmg = get_tool_path("dmg")
        self.daos_perf = get_tool_path("daos_perf")
        self.mpirun = get_tool_path("mpirun")
        self.daos_agent = get_tool_path("daos_agent")
        print("\n\n")
        print("\u0332".join("Test Tools:"))
        print("FIO: %s"% self.fio)
        print("FIO_plugin: %s"% self.fio_plugin)
        print("DAOS tool: %s"% self.daos)
        print("DMG tool: %s"% self.dmg)
        print("DAOS agent: %s"% self.daos_agent)
        print("mpirun: %s"% self.mpirun)
        print("*******************************************\n\n")

    def __init__(self, env):
        self.env = os.getcwd() + "/" + env
        self.set_environ()
        self.get_test_tools()
