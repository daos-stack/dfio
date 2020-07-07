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
 * Implementation of Async DAOS File System Fio Plugin
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

#include <fio.h>
#include <optgroup.h>

#include <daos.h>
#include <daos/object.h>
#include <daos_fs.h>
#include <gurt/common.h>
#include <gurt/hash.h>

static bool		daos_initialized;
static int		num_threads;
static pthread_mutex_t	daos_mutex = PTHREAD_MUTEX_INITIALIZER;
daos_handle_t		poh;
daos_handle_t		coh;
dfs_t			*dfs;

struct daos_iou {
	struct io_u	*io_u;
	d_sg_list_t	sgl;
	d_iov_t		iov;
	daos_event_t	ev;
	bool		complete;
};

struct daos_data {
	daos_handle_t	 eqh;
	dfs_obj_t	*obj;
	struct io_u	**io_us;
	int		queued;
	int		num_ios;
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
daos_fio_global_init(struct thread_data *td)
{
	struct daos_fio_options	*eo = td->eo;
	uuid_t			pool_uuid, co_uuid;
	d_rank_list_t		*svcl = NULL;
	daos_pool_info_t	pool_info;
	daos_cont_info_t	co_info;
	int			rc = 0;

	if (!eo->pool || !eo->cont || !eo->svcl) {
		log_err("Missing required DAOS options\n");
		return EINVAL;
	}

	rc = daos_init();
	if (rc != -DER_ALREADY && rc) {
		log_err("Failed to initialize daos %d\n", rc);
		td_verror(td, EINVAL, "daos_init");
		return EINVAL;
	}

	rc = uuid_parse(eo->pool, pool_uuid);
	if (rc) {
		log_err("Failed to parse 'Pool uuid': %s\n", eo->pool);
		td_verror(td, EINVAL, "uuid_parse(eo->pool)");
		return EINVAL;
	}

	rc = uuid_parse(eo->cont, co_uuid);
	if (rc) {
		log_err("Failed to parse 'Cont uuid': %s\n", eo->cont);
		td_verror(td, EINVAL, "uuid_parse(eo->cont)");
		return EINVAL;
	}

	svcl = daos_rank_list_parse(eo->svcl, ":");
	if (svcl == NULL) {
		log_err("Failed to parse svcl\n");
		td_verror(td, EINVAL, "daos_rank_list_parse");
		return EINVAL;
	}

	rc = daos_pool_connect(pool_uuid, NULL, svcl, DAOS_PC_RW,
			&poh, &pool_info, NULL);
	d_rank_list_free(svcl);
	if (rc) {
		log_err("Failed to connect to pool %d\n", rc);
		td_verror(td, EINVAL, "daos_pool_connect");
		return EINVAL;
	}

	rc = daos_cont_open(poh, co_uuid, DAOS_COO_RW, &coh, &co_info, NULL);
	if (rc) {
		log_err("Failed to open container: %d\n", rc);
		td_verror(td, EINVAL, "daos_cont_open");
		(void) daos_pool_disconnect(poh, NULL);
		return EINVAL;
	}

	rc = dfs_mount(poh, coh, O_RDWR, &dfs);
	if (rc) {
		log_err("Failed to mount DFS namespace: %d\n", rc);
		td_verror(td, EINVAL, "dfs_mount");
		(void) daos_pool_disconnect(poh, NULL);
		(void) daos_cont_close(coh, NULL);
		return EINVAL;
	}

	log_info("[Init] pool_id=%s, container_id=%s, svcl=%s, chunk_size=%ld\n",
		 eo->pool, eo->cont, eo->svcl, eo->chsz);

	return 0;
}

static void
daos_fio_global_cleanup()
{
	int rc;

	rc = dfs_umount(dfs);
	if (rc)
		log_err("failed to umount dfs: %d\n", rc);
	rc = daos_cont_close(coh, NULL);
	if (rc)
		log_err("failed to close container: %d\n", rc);
	rc = daos_pool_disconnect(poh, NULL);
	if (rc)
		log_err("failed to disconnect pool: %d\n", rc);
	rc = daos_fini();
	if (rc)
		log_err("failed to finalize daos: %d\n", rc);
}

static int
daos_fio_setup(struct thread_data *td)
{
	return 0;
}

static int
daos_fio_init(struct thread_data *td)
{
	struct daos_data	*dd;
	int			rc = 0;

	pthread_mutex_lock(&daos_mutex);

	/* Allocate space for DAOS-related data */
	dd = malloc(sizeof(*dd));
	if (dd == NULL) {
		log_err("Failed to allocate DAOS-private data\n");
		rc = ENOMEM;
		goto out;
	}

	dd->queued	= 0;
	dd->num_ios	= td->o.iodepth;
	dd->io_us	= calloc(dd->num_ios, sizeof(struct io_u *));
	if (dd->io_us == NULL) {
		log_err("Failed to allocate IO queue\n");
		rc = ENOMEM;
		goto out;
	}

	/* initialize DAOS stack if not already up */
	if (!daos_initialized) {
		rc = daos_fio_global_init(td);
		if (rc)
			goto out;
		daos_initialized = true;
	}

	rc = daos_eq_create(&dd->eqh);
	if (rc) {
		log_err("Failed to create event queue: %d\n", rc);
		td_verror(td, EINVAL, "daos_eq_create");
		rc = EINVAL;
		goto out;
	}

	td->io_ops_data = dd;
	num_threads++;
out:
	if (rc) {
		if (dd && dd->io_us)
			free(dd->io_us);
		if (dd)
			free(dd);
		if (num_threads == 0 && daos_initialized) {
			daos_fio_global_cleanup();
			daos_initialized = false;
		}
	}
	pthread_mutex_unlock(&daos_mutex);
	return rc;
}

static void
daos_fio_cleanup(struct thread_data *td)
{
	struct daos_data	*dd = td->io_ops_data;
	int			rc;

	if (td->io_ops_data == NULL)
		return;

	rc = daos_eq_destroy(dd->eqh, DAOS_EQ_DESTROY_FORCE);
	if (rc < 0)
		log_err("failed to destroy event queue: %d\n", rc);

	free(dd->io_us);
	free(dd);

	pthread_mutex_lock(&daos_mutex);
	num_threads--;
	if (daos_initialized && num_threads == 0) {
		daos_fio_global_cleanup();
		daos_initialized = false;
	}		
	pthread_mutex_unlock(&daos_mutex);
}

static int
daos_fio_open(struct thread_data *td, struct fio_file *f)
{
	struct daos_data	*dd = td->io_ops_data;
	struct daos_fio_options	*eo = td->eo;
	int			rc;
	unsigned int		oc =
		(DAOS_OC_R1S_SPEC_RANK | (td->subjob_number << 20));

	rc = dfs_open(dfs,
		      NULL,
		      f->file_name,
		      S_IFREG | S_IRWXU | S_IRWXG | S_IRWXO,
		      O_CREAT | O_RDWR,
		      oc,
		      eo->chsz ? eo->chsz : 0,
		      NULL,
		      &dd->obj);
	if (rc) {
		log_err("Failed to open file: %d\n", rc);
		td_verror(td, rc, "dfs_open");
		return rc;
	}

	return 0;
}

static int
daos_fio_unlink(struct thread_data *td, struct fio_file *f)
{
	struct daos_data	*dd = td->io_ops_data;
	int			rc;

	rc = dfs_remove(dfs, NULL, f->file_name, false, NULL);
	if (rc) {
		log_err("Failed to remove file: %d\n", rc);
		td_verror(td, rc, "dfs_remove");
		return rc;
	}

	return 0;
}

static int
daos_fio_invalidate(struct thread_data *td, struct fio_file *f)
{
	return 0;
}

static void
daos_fio_io_u_free(struct thread_data *td, struct io_u *io_u)
{
	struct daos_iou *io = io_u->engine_data;

	if (io) {
		io_u->engine_data = NULL;
		free(io);
	}
}

static int
daos_fio_io_u_init(struct thread_data *td, struct io_u *io_u)
{
	struct daos_iou *io;

	io = malloc(sizeof(struct daos_iou));
	if (!io) {
		td_verror(td, ENOMEM, "malloc");
		return ENOMEM;
	}
	io->io_u = io_u;
	io_u->engine_data = io;
	return 0;
}

static struct io_u *
daos_fio_event(struct thread_data *td, int event)
{
	struct daos_data *dd = td->io_ops_data;

	return dd->io_us[event];
}

static int
daos_fio_getevents(struct thread_data *td, unsigned int min,
		   unsigned int max, const struct timespec *t)
{
	struct daos_data *dd = td->io_ops_data;
	daos_event_t *evp[max];
	unsigned int events = 0;
	int i;
	int rc;

	while (events < min) {
		rc = daos_eq_poll(dd->eqh, 0, DAOS_EQ_NOWAIT, max, evp);
		if (rc < 0) {
			log_err("Event poll failed: %d\n", rc);
			td_verror(td, EIO, "daos_eq_poll");
			return events;
		}

		for (i = 0; i < rc; i++) {
			struct daos_iou	*io;
			struct io_u	*io_u;

			io = container_of(evp[i], struct daos_iou, ev);
			if (io->complete)
				log_err("Completion on already completed I/O\n");

			io_u = io->io_u;
			if (io->ev.ev_error)
				io_u->error = io->ev.ev_error;
			else
				io_u->resid = 0;

			dd->io_us[events] = io_u;
			dd->queued--;
			daos_event_fini(&io->ev);
			io->complete = true;
			events++;
		}
	}

	return events;
}

static enum fio_q_status
daos_fio_queue(struct thread_data *td, struct io_u *io_u)
{
	struct daos_data *dd = td->io_ops_data;
	struct daos_iou *io = io_u->engine_data;
	daos_off_t offset = io_u->offset;
	daos_size_t ret;
	int rc;

	if (dd->queued == td->o.iodepth)
		return FIO_Q_BUSY;

	io->sgl.sg_nr = 1;
	io->sgl.sg_nr_out = 0;
	d_iov_set(&io->iov, io_u->xfer_buf, io_u->xfer_buflen);
	io->sgl.sg_iovs = &io->iov;

	io->complete = false;
	rc = daos_event_init(&io->ev, dd->eqh, NULL);
	if (rc) {
		log_err("Event init failed: %d\n", rc);
		io_u->error = rc;
		return FIO_Q_COMPLETED;
	}

	switch (io_u->ddir) {
	case DDIR_WRITE:
		rc = dfs_write(dfs, dd->obj, &io->sgl, offset, &io->ev);
		if (rc) {
			log_err("dfs_write failed: %d\n", rc);
			io_u->error = rc;
			return FIO_Q_COMPLETED;
		}
		break;
	case DDIR_READ:
		rc = dfs_read(dfs, dd->obj, &io->sgl, offset, &ret,
			      &io->ev);
		if (rc) {
			log_err("dfs_read failed: %d\n", rc);
			io_u->error = rc;
			return FIO_Q_COMPLETED;
		}
		break;
	case DDIR_SYNC:
		io_u->error = 0;
		return FIO_Q_COMPLETED;
	default:
		dprint(FD_IO, "Invalid IO type: %d\n", io_u->ddir);
		io_u->error = -DER_INVAL;
		return FIO_Q_COMPLETED;
	}

	dd->queued++;
	return FIO_Q_QUEUED;
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

	rc = dfs_stat(dfs, NULL, file_name, &stbuf);
	if (rc) {
		log_err("dfs_stat failed: %d\n", rc);
		td_verror(td, rc, "dfs_stat");
		return rc;
	}

	f->real_file_size = stbuf.st_size;
	return 0;
}

static int
daos_fio_close(struct thread_data *td, struct fio_file *f)
{
	struct daos_data *dd = td->io_ops_data;
	int rc;

	rc = dfs_release(dd->obj);
	if (rc) {
		log_err("dfs_release failed: %d\n", rc);
		td_verror(td, rc, "dfs_release");
		return rc;
	}

	return 0;
}

static int
daos_fio_prep(struct thread_data fio_unused *td, struct io_u *io_u)
{
	return 0;
}

struct ioengine_ops ioengine = {
	.name			= "fio_daos_dfs_async",
	.version		= FIO_IOOPS_VERSION,
	.flags			= FIO_DISKLESSIO | FIO_NODISKUTIL,
	.setup			= daos_fio_setup,
	.init			= daos_fio_init,
	.prep			= daos_fio_prep,
	.cleanup		= daos_fio_cleanup,
	.open_file		= daos_fio_open,
	.invalidate		= daos_fio_invalidate,
	.queue			= daos_fio_queue,
	.getevents		= daos_fio_getevents,
	.event			= daos_fio_event,
	.io_u_init		= daos_fio_io_u_init,
	.io_u_free		= daos_fio_io_u_free,
	.close_file		= daos_fio_close,
	.unlink_file		= daos_fio_unlink,
	.get_file_size		= daos_fio_get_file_size,
	.option_struct_size	= sizeof(struct daos_fio_options),
	.options		= options,
};
