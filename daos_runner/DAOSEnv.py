#! /usr/bin/python3.6
import os, sys, subprocess
import pprint, shlex, time, uuid
from envbash import load_envbash
from pathlib import Path
from subprocess import Popen,PIPE

class DAOSEnv:
	def set_environ(self):
		print ("\n\n");
		print ("DAOS Test Environment")
		print ("----------------------")
		print ("\u0332".join("Loading env file "),self.env)
		load_envbash(self.env, override=True, remove=True)

	def get_tool_path(self, cmd):
		res = subprocess.check_output(["which", "%s"% cmd])
		return res.decode(sys.stdout.encoding).strip()

	def get_test_tools(self):
		self.fio = self.get_tool_path("fio")
		self.fio_plugin = self.get_tool_path("daos_fio_async")
		self.daos = self.get_tool_path("daos")
		self.dmg  = self.get_tool_path("dmg")
		self.daos_perf = self.get_tool_path("daos_perf")
		self.mpirun = self.get_tool_path("mpirun")
		self.daos_agent = self.get_tool_path("daos_agent")
		print ("\n\n")
		print ("\u0332".join("Test Tools:"))
		print ("FIO: %s"% self.fio)
		print ("FIO_plugin: %s"% self.fio_plugin)
		print ("DAOS tool: %s"% self.daos)
		print ("DMG tool: %s"% self.dmg)
		print ("DAOS agent: %s"% self.daos_agent)
		print ("mpirun: %s"% self.mpirun)
		print ("*******************************************\n\n")

	def __init__(self, env):
		self.env = os.getcwd() + "/" + env
		self.set_environ()
		self.get_test_tools()
