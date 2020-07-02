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
		res = subprocess.check_output(["which", "%s"% cmd]).
                        decode(sys.stdout.encoding).strip()
		return res

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


class DAOSPool(DAOSEnv):
	def __init__(self, env, client_config_file, scm_size, nvme_size, agg_mode):
		DAOSEnv.__init__(self, env)
		self.client_config = os.getcwd() + "/" + client_config_file
		self.scm_size = scm_size
		self.nvme_size = nvme_size
		self.agg_mode = agg_mode
		
	def create_pool(self):
		print ("\n****Creating Pool for this object\n")
		cmd = self.dmg +" -o " + self.client_config 
        cmd += " pool create -s="+ self.scm_size +" -n="+self.nvme_size
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
		print ("****SUCCESS: Pool created\n")
		print ("UUID: "+ self.pool_uuid +" replicas: "+ str(self.replicas))
		

	def destroy_pool(self):
		print ("\n****Destroy pool " + self.pool_uuid + "\n"); 
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

class DAOSRunner(DAOSPool):
	def __init__(self, env, client_config, jobs, iosize, scm_size,
                 nvme_size, agg_mode):

		DAOSPool.__init__(self, env, client_config, scm_size, nvme_size,
                            agg_mode)
		self.jobs	= jobs
		self.iosize	= iosize

	def start_agent(self):
		cmd = self.daos_agent + " -o " + self.client_config
		args = shlex.split(cmd)
		proc = subprocess.Popen(args)
		self.agent_pid = proc.pid
		print ("\n****Start daos agent PID\n", self.agent_pid)
		time.sleep(3) # sleep a bit for pretty print

	def stop_agent(self):
		try:
			val = self.agent_pid
		except AttributeError:
			print ("ERROR: No Known agent running for this object")
			self.agent_pid = None
			return
	
		if not self.agent_pid is None:
			cmd = "kill -9 " + str(self.agent_pid)
			print ("\n****Stopping daos_agent pid",
				str(self.agent_pid)+"\n")
			args = shlex.split(cmd)
			res = subprocess.check_output(args)
			print (res.decode(sys.stdout.encoding).strip())
		else:
			print ("ERROR: No known agent running for this test object")

	def create_container(self, cont_uuid, fstype, cont_chunk, cont_sys):
		print("****Creating a new container\n")
		if cont_uuid is None:
			cont_uuid = uuid.uuid1()
		if cont_sys is None:
			cont_sys = "daos_server"
		if fstype is None:
			fstype = "POSIX"

		self.cont_uuid = str(cont_uuid)
		self.cont_sys  = cont_sys
		self.fstype    = fstype

	
		cmd = self.daos	+ " cont create --pool=" + self.pool_uuid + " --svc="
		cmd += self.replicas + " --sys-name="+ cont_sys + " --cont="
		cmd += self.cont_uuid + " --type="+ fstype

		if not cont_chunk is None:
			cmd += "--chunk-size="+ cont_chunk	

		args = shlex.split(cmd)
		try:
			res = subprocess.check_output(args)
		except subprocess.CalledProcessError as error:
			print("Could not create container -- failure")
			exit()

		print (res.decode(sys.stdout.encoding).strip())
		

	def destroy_container(self):
		try:
			val = self.cont_uuid;
		except AttributeError:
			print ("ERROR: No container to destroy for this runner object")
			self.cont_uuid = None;
			return;
		print("****Destroying container ID: ", self.cont_uuid)
		if not self.cont_uuid is None:
			cmd = self.daos + " cont destroy --cont="+ self.cont_uuid
			cmd += " --svc=" + self.replicas + " --pool=" + self.pool_uuid
			args = shlex.split(cmd)
			try:
				res = subprocess.check_output(args)
			except subprocess.CalledProcessError as error:
				print("Coud not destroy container", self.cont_uuid);
				return

			print (res.decode(sys.stdout.encoding).strip())
		else:
			print ("ERROR: No container created for this object");
		return
					
def main():
	obj1 = DAOSRunner("env-daos-vish", "daos.yml", 1, 4096, "4G",
                        "40G", "disabled")

	obj1.start_agent()	
	if obj1.create_pool() is -1:
		exit()

	# Using all defaults for  cont_uuid, fstype, cont_chunk, cont_sys
	obj1.create_container(None, None, None, None)
	obj1.destroy_container()
	
	obj1.destroy_pool()
	obj1.stop_agent()
	
if __name__ == "__main__":
	main() 
