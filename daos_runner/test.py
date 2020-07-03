#! /usr/bin/python3.6
from DAOSRunner import DAOSRunner
from DAOSPool	import DAOSPool
from DAOSEnv	import DAOSEnv


def main():
	obj1 = DAOSRunner("test_files/env-daos-vish", "test_files/daos.yml", 1, 4096, "4G",
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
