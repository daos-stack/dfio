#! /usr/bin/python3.6
from DAOSRunner import DAOSRunner
from DAOSPool	import DAOSPool
from DAOSEnv	import DAOSEnv


def main():
	# daos_env file, client config file, numjobs/processes, totalIO/(job/proc), SCM Pool size,
	# NVMe poolsize, aggregation mode
	  
	fiotest = DAOSRunner("test_files/env-daos-vish", "test_files/daos.yml", 32, "12G", "120G",
			  "500G", "disabled")

	fiotest.start_agent()	
	if fiotest.create_pool() is -1:
		exit()

	# Using all defaults for  cont_uuid, fstype, cont_chunk, cont_sys
	fiotest.create_container(None, None, None, None)
	# Create FIO config file at runtime
	# config file output, transfer-size/blocksize, numjobs, chunksize, operation
	fiotest.setup_fio_config("daos-config-rw.fio", 4096, 16, 1048576, "randwrite")
	fiotest.setup_fio_config("daos-config-rr.fio", 4096, 16, 1048576, "randread")
	# run fio - config-file, output-dir, output-file 
	fiotest.run_fio_test("daos-config-rw.fio", "sample", "randwrite-test")
	fiotest.run_fio_test("daos-config-rr.fio", "sample", "randread-test")
	fiotest.destroy_pool() # destroy pool -- encompasses destroying container.
	fiotest.stop_agent()
	
if __name__ == "__main__":
	main() 
