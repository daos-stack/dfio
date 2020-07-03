#! /usr/bin/python3.6
import os, sys, subprocess
import pprint, shlex, time, uuid
from pathlib import Path
from subprocess import Popen,PIPE
from DAOSEnv import DAOSEnv

class DAOSPool(DAOSEnv):
	def __init__(self, env, client_config_file, scm_size, nvme_size, agg_mode):
		DAOSEnv.__init__(self, env)
		self.client_config = os.getcwd() + "/" + client_config_file
		self.scm_size = scm_size
		self.nvme_size = nvme_size
		self.agg_mode = agg_mode
		
	def create_pool(self):
		print ("\n****Creating Pool for this object")
		cmd = self.dmg +" -o " + self.client_config
		cmd += " pool create -s="+ self.scm_size + " -n="
		cmd += self.nvme_size
		args = shlex.split(cmd)
		try:
			res = subprocess.check_output(args)
		except subprocess.CalledProcessError as error:
			print("Could not create pool -- failure")
			exit();
			
		columns = res.decode(sys.stdout.encoding).strip().split()
		for column in columns:
			index = columns.index(column) + 1
			if column.upper() == "UUID:":
				self.pool_uuid = columns[index].rstrip(',')
			if column.lower() == "replicas:":
				self.replicas = columns[index].rstrip(',')
		print ("****SUCCESS: Pool created")
		print ("UUID: "+ self.pool_uuid +" replicas: "+ str(self.replicas))
		

	def destroy_pool(self):
		print ("\n****Destroy pool " + self.pool_uuid); 
		try:
			val = self.pool_uuid
		except AttributeError:
			print ("ERROR: No pool created for this object\n")
			return
	
		cmd = self.dmg +" -o " + self.client_config
		cmd +=" pool destroy --pool="+self.pool_uuid

		stream = os.popen(cmd)
		pool_output = stream.read()
		print (pool_output)

	def get_pool_uuid(self):
		try:
			val = self.pool_uuid
		except AttributeError:
			print ("ERROR: No Pool created")
			return

		return self.pool_uuid

	def get_replicas(self):
		try:
			val = self.replicas
		except AttributeError:
			print ("ERROR: No pool created")
			return

		return self.replicas
