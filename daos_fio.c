/**
 * (C) Copyright 2020 Intel Corporation.
 *
 * GOVERNMENT LICENSE RIGHTS-OPEN SOURCE SOFTWARE
 * The Government's rights to use, modify, reproduce, release, perform, display,
 * or disclose this software are subject to the terms of the Apache License as
 * provided in Contract No. B609815.
 * Any reproduction of computer software, computer software documentation, or
 * portions thereof marked with this legend must also reproduce the markings.
 */

/*
 * Implementation of DAOS File System Fio Plugin
 */
#include <string.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <dirent.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <libgen.h>

#include <config-host.h>
#include <fio.h>
#include <optgroup.h>

#include <daos.h>
#include <daos_fs.h>
#include <gurt/common.h>
#include <gurt/hash.h>

#define ERR(MSG)							\
do {									\
	fprintf(stderr, "ERROR (%s:%d): %s",				\
		__FILE__, __LINE__, MSG);				\
	fflush(stderr);							\
	return -1;							\
} while (0)

#define DCHECK(rc, format, ...)						\
do {									\
	int _rc = (rc);							\
									\
	if (_rc < 0) {							\
		fprintf(stderr, "ERROR (%s:%d): %d: "			\
			format"\n", __FILE__, __LINE__,  _rc,		\
			##__VA_ARGS__);					\
		fflush(stderr);						\
		return -1;						\
	}								\
} while (0)

static bool daos_initialized;
static int num_threads;
static pthread_mutex_t daos_mutex = PTHREAD_MUTEX_INITIALIZER;
daos_handle_t poh, coh;
dfs_t *dfs;

struct daos_data {
	dfs_t		*dfs;
	daos_handle_t	poh, coh;
	dfs_obj_t	*obj;
	struct io_u	**io_us;
};

struct daos_fio_options {
	void		*pad;
	char		*pool;
	char		*cont;
	char		*svcl;
	daos_size_t	chsz;
};

static struct fio_option options[] = {
	{
		.name		= "daos_pool",
		.lname		= "DAOS pool uuid",
		.type		= FIO_OPT_STR_STORE,
		.off1		= offsetof(struct daos_fio_options, pool),
		.help		= "DAOS pool uuid",
		.category	= FIO_OPT_C_ENGINE,
		.group		= FIO_OPT_G_INVALID,
	},
	{
		.name           = "daos_cont",
		.lname          = "DAOS container uuid",
		.type           = FIO_OPT_STR_STORE,
		.off1           = offsetof(struct daos_fio_options, cont),
		.help           = "DAOS container uuid",
		.category	= FIO_OPT_C_ENGINE,
		.group		= FIO_OPT_G_INVALID,
	},
	{
		.name           = "daos_svcl",
		.lname          = "DAOS pool replicated service",
		.type           = FIO_OPT_STR_STORE,
		.off1           = offsetof(struct daos_fio_options, svcl),
		.help           = "DAOS SVCL",
		.category	= FIO_OPT_C_ENGINE,
		.group		= FIO_OPT_G_INVALID,
	},
	{
		.name           = "daos_chsz",
		.lname          = "DAOS chunk size in bytes",
		.type           = FIO_OPT_INT,
		.off1           = offsetof(struct daos_fio_options, chsz),
		.help           = "DAOS chunk size in bytes (default: 1MiB)",
		.def		= "1048576",
		.category	= FIO_OPT_C_ENGINE,
		.group		= FIO_OPT_G_INVALID,
	},
	{
		.name           = NULL,
	},
};

static int
daos_fio_init(struct thread_data *td)
{
	struct daos_fio_options	*eo = td->eo;
	struct daos_data	*dd;
	uuid_t			pool_uuid, co_uuid;
	d_rank_list_t		*svcl = NULL;
	daos_pool_info_t	pool_info;
	daos_cont_info_t	co_info;
	int			rc;

	pthread_mutex_lock(&daos_mutex);
	num_threads++;

	/* Allocate space for DAOS-related data */
	dd = malloc(sizeof(*dd));
	dd->dfs = NULL;
	dd->obj = NULL;
	dd->io_us = calloc(td->o.iodepth, sizeof(struct io_u *));
	if (dd->io_us == NULL)
		ERR("Failed to allocate IO queue\n");

	if (!daos_initialized) {
		if (!eo->pool || !eo->cont || !eo->svcl)
			ERR("Missing required DAOS options\n");

		rc = daos_init();
		if (rc != -DER_ALREADY && rc)
			DCHECK(rc, "Failed to initialize daos");

		rc = uuid_parse(eo->pool, pool_uuid);
		DCHECK(rc, "Failed to parse 'Pool uuid': %s", eo->pool);
		rc = uuid_parse(eo->cont, co_uuid);
		DCHECK(rc, "Failed to parse 'Cont uuid': %s", eo->cont);
		svcl = daos_rank_list_parse(eo->svcl, ":");
		if (svcl == NULL)
			ERR("Failed to allocate svcl");

		rc = daos_pool_connect(pool_uuid, NULL, svcl, DAOS_PC_RW,
				       &poh, &pool_info, NULL);
		d_rank_list_free(svcl);
		DCHECK(rc, "Failed to connect to pool");

		rc = daos_cont_open(poh, co_uuid, DAOS_COO_RW, &coh, &co_info,
				    NULL);
		DCHECK(rc, "Failed to open container");

		rc = dfs_mount(poh, coh, O_RDWR, &dfs);
		DCHECK(rc, "Failed to mount DFS namespace");
		daos_initialized = true;
	}

	dd->poh.cookie = poh.cookie;
	dd->coh.cookie = coh.cookie;
	dd->dfs = dfs;

	td->io_ops_data = dd;
	printf("[Init] pool_id=%s, container_id=%s, svcl=%s, chunk_size=%ld\n",
	       eo->pool, eo->cont, eo->svcl, eo->chsz);

	pthread_mutex_unlock(&daos_mutex);
	return 0;
}

static void
daos_fio_cleanup(struct thread_data *td)
{
	struct daos_data *dd = td->io_ops_data;

	pthread_mutex_lock(&daos_mutex);
	num_threads--;

	if (num_threads != 0) {
		free(dd->io_us);
		free(dd);
		pthread_mutex_unlock(&daos_mutex);
		return;
	}

	dfs_umount(dd->dfs);
	daos_cont_close(dd->coh, NULL);
	daos_pool_disconnect(dd->poh, NULL);
	daos_fini();
	free(dd->io_us);
	free(dd);
	daos_initialized = false;
	pthread_mutex_unlock(&daos_mutex);
}

static int
daos_fio_open(struct thread_data *td, struct fio_file *f)
{
	char *file_name = f->file_name;
	struct daos_data *dd = td->io_ops_data;
	mode_t mode = S_IFREG | S_IRWXU | S_IRWXG | S_IRWXO;
	int fd_oflag = O_CREAT | O_RDWR;
	daos_oclass_id_t oc = OC_SX;
	struct daos_fio_options *eo = td->eo;
	daos_size_t chunk_size = eo->chsz ? eo->chsz : 0;
	int rc;

	rc = dfs_open(dd->dfs, NULL, file_name, mode, fd_oflag,
		      oc, chunk_size, NULL, &dd->obj);
	DCHECK(rc, "dfs_open() failed.");

	return 0;
}

static int
daos_fio_unlink(struct thread_data *td, struct fio_file *f)
{
	char *file_name = f->file_name;
	struct daos_data *dd = td->io_ops_data;
	int rc;

	rc = dfs_remove(dd->dfs, NULL, file_name, false, NULL);
	DCHECK(rc, "dfs_remove() failed.");

	return 0;
}

static int
daos_fio_invalidate(struct thread_data *td, struct fio_file *f)
{
	return 0;
}

static int
daos_fio_queue(struct thread_data *td, struct io_u *io_u)
{
	struct daos_data *dd = td->io_ops_data;
	d_iov_t iov;
	d_sg_list_t sgl;
	daos_off_t offset = io_u->offset;
	daos_size_t ret;
	int rc;

	sgl.sg_nr = 1;
	sgl.sg_nr_out = 0;
	d_iov_set(&iov, io_u->xfer_buf, io_u->xfer_buflen);
	sgl.sg_iovs = &iov;

	switch (io_u->ddir) {
	case DDIR_WRITE:
		rc = dfs_write(dd->dfs, dd->obj, &sgl, offset, NULL);
		DCHECK(rc, "dfs_write() failed.");
		break;
	case DDIR_READ:
		rc = dfs_read(dd->dfs, dd->obj, &sgl, offset, &ret, NULL);
		DCHECK(rc, "dfs_read() failed.");
		break;
	default:
		ERR("Invalid IO type\n");
	}

	return FIO_Q_COMPLETED;
}

static int
daos_fio_get_file_size(struct thread_data *td, struct fio_file *f)
{
	char *file_name = f->file_name;
	struct daos_data *dd = td->io_ops_data;
	struct stat stbuf = {0};
	int rc;

	if (!daos_initialized)
		return 0;

	rc = dfs_stat(dd->dfs, NULL, file_name, &stbuf);
	DCHECK(rc, "dfs_stat() failed.");

	f->real_file_size = stbuf.st_size;
	return 0;
}

static int
daos_fio_close(struct thread_data *td, struct fio_file *f)
{
	struct daos_data *dd = td->io_ops_data;
	int rc;

	rc = dfs_release(dd->obj);
	DCHECK(rc, "dfs_release() Failed");

	return 0;
}

static int
daos_fio_prep(struct thread_data fio_unused *td, struct io_u *io_u)
{
	return 0;
}

struct ioengine_ops ioengine = {
	.name			= "fio_daos_dfs",
	.version		= FIO_IOOPS_VERSION,
	.flags			= FIO_DISKLESSIO | FIO_NODISKUTIL | FIO_RAWIO |
	FIO_SYNCIO,
	.init			= daos_fio_init,
	.prep			= daos_fio_prep,
	.cleanup		= daos_fio_cleanup,
	.open_file		= daos_fio_open,
	.invalidate		= daos_fio_invalidate,
	.queue			= daos_fio_queue,
	.close_file		= daos_fio_close,
	.unlink_file		= daos_fio_unlink,
	.get_file_size		= daos_fio_get_file_size,
	.option_struct_size	= sizeof(struct daos_fio_options),
	.options		= options,
};

