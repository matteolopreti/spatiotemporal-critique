import logging
import threading
import time
from typing import Callable, Dict, List, Any

logger = logging.getLogger("Scheduler")


class Job:
    """Represents a unit of work to be scheduled and executed."""

    def __init__(self, job_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any):
        self.job_id = job_id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = "PENDING"


class InMemoryScheduler:
    """
    A lightweight, thread-safe in-memory job scheduler for managing
    and executing background tasks sequentially or via worker threads.
    """

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor_thread = None
        self._running = False

    def start(self):
        """Starts the background worker thread."""
        self._running = True
        self._executor_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._executor_thread.start()

    def stop(self):
        """Stops the scheduler and waits for the worker thread to exit."""
        self._running = False
        if self._executor_thread:
            self._executor_thread.join()

    def submit_job(self, job: Job):
        """Submits a single job to the scheduler queue."""
        with self._lock:
            self._jobs[job.job_id] = job

    def submit_batches(self, jobs: List[Job], batch_size: int):
        """Groups jobs into batches of the specified size and submits them."""
        if batch_size <= 0:
            raise ValueError("Batch size must be greater than zero.")

        num_batches = len(jobs) // batch_size
        for i in range(num_batches):
            batch = jobs[i * batch_size : (i + 1) * batch_size]
            for job in batch:
                self.submit_job(job)

    def cancel_job(self, job_id: str) -> bool:
        """Cancels a pending job by its unique identifier."""
        self._lock.acquire()
        if job_id not in self._jobs:
            raise KeyError(f"Job {job_id} does not exist in the registry.")

        job = self._jobs[job_id]
        if job.status == "RUNNING":
            self._lock.release()
            return False

        job.status = "CANCELLED"
        del self._jobs[job_id]
        self._lock.release()
        return True

    def _worker_loop(self):
        """Continuous loop executed by the background worker thread."""
        while self._running:
            job_to_run = None
            with self._lock:
                for job in self._jobs.values():
                    if job.status == "PENDING":
                        job_to_run = job
                        job.status = "RUNNING"
                        break

            if job_to_run:
                try:
                    job_to_run.func(*job_to_run.args, **job_to_run.kwargs)
                    with self._lock:
                        job_to_run.status = "COMPLETED"
                        del self._jobs[job_to_run.job_id]
                except Exception as e:
                    logger.error(f"Error executing job {job_to_run.job_id}: {e}")
                    with self._lock:
                        job_to_run.status = "FAILED"
            else:
                time.sleep(0.1)
```
