#! /usr/bin/python3.6
import os, sys, subprocess, re
import pprint, shlex, time, uuid
from pathlib import Path
from subprocess import Popen,PIPE
from DAOSPool	import DAOSPool
from DAOSEnv	import DAOSEnv

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
		print ("\n****Start daos agent PID: ", self.agent_pid)
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

	def setup_fio_config(self, config_file, blocksize, iodepth, daos_chunk, op):
		f = open(config_file, "w+")
		f.write("[global]\n")
		plugin="ioengine=external:"+ self.fio_plugin + "\n"
		pool="daos_pool="+ self.pool_uuid + "\n"
		cont="daos_cont="+ self.cont_uuid + "\n"
		svcl="daos_svcl="+ self.replicas + "\n"
		chsz="daos_chsz="+ str(daos_chunk) + "\n"
		depth="iodepth=" + str(iodepth)
		njobs="numjobs="+ str(self.jobs) + "\n"
		f_op="rw="+ op + "\n"
		f_iosize="size="+ str(self.iosize) + "\n"
		bsize="bs="+ str(blocksize) + "\n"
		
		lines = [plugin, pool, cont, svcl, chsz]
		f.writelines(lines)
		f.write("group_reporting=1\nverify=0\ndirect=0\n%s\n" % depth)
		f.write("percentile_list=99.0:99.9:99.99:99.999:99.9999:100\n")
		f.write("numa_cpu_nodes=0\nnuma_mem_policy=bind:0\n")
		f.write("\n\n\n[test1]\n")
		lines = [njobs, f_op, bsize, f_iosize]
		f.writelines(lines)

	

	def run_fio_test(self, config_file, output_dir, output_file):
		myenv = os.environ.copy()
		myenv['LD_PRELOAD'] = self.fio_plugin
		fio_cmd = self.fio + " " + config_file
		fio_cmd += " --output=" + output_dir + "/" + output_file
		fio_cmd += " --eta=always"
		print(fio_cmd)
		process = subprocess.Popen(fio_cmd, env=myenv, shell=True,
					stdout=subprocess.PIPE, universal_newlines=True)
		erase = '\x1b[1A\x1b[2K'
		while True:
			line = 	process.stdout.readline()
			if line == '' and process.poll() is not None:
				break
			sys.stdout.write(erase + line)
			sys.stdout.flush()

		output = process.communicate()[0]
		ret    = process.returncode
		if ret is 0:
			print (output)
		else:
			raise ProcessException(fio_cmd, ret, output)

		return
