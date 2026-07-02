"""jobrunner — a small in-process background-job scheduler.

Jobs carry an integer priority (lower value runs sooner) and are dispatched
to a pool of worker threads.  Contract:

* Among jobs of equal priority, dispatch follows submission order.
* A job whose callable raises is retried, and once ``max_attempts`` total
  attempts have been used it is marked ``failed`` with the error preserved.
* ``shutdown()`` performs a graceful drain: every job submitted before the
  call runs to completion before shutdown returns.
"""
import heapq
import itertools
import threading
import time

DEFAULT_PRIORITY = 5


class Job:
    """A unit of work, tracked queued -> running -> done | failed."""

    _ids = itertools.count(1)

    def __init__(self, fn, args=(), priority=DEFAULT_PRIORITY, max_attempts=3):
        self.id = next(Job._ids)
        self.fn = fn
        self.args = tuple(args)
        self.priority = priority
        self.max_attempts = max_attempts
        self.attempts = 0
        self.state = "queued"
        self.result = None
        self.error = None
        self.enqueued_at = time.monotonic()

    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.enqueued_at > other.enqueued_at

    def __repr__(self):
        return f"<Job {self.id} p{self.priority} {self.state}>"


class Scheduler:
    """Dispatches queued jobs to ``workers`` daemon threads by priority."""

    def __init__(self, workers=2):
        self._heap = []
        self._cv = threading.Condition()
        self._stop = False
        self.jobs = {}
        self._threads = []
        for i in range(workers):
            t = threading.Thread(target=self._worker_loop,
                                 name=f"worker-{i}", daemon=True)
            t.start()
            self._threads.append(t)

    def submit(self, fn, *args, priority=DEFAULT_PRIORITY, max_attempts=3):
        """Queue ``fn(*args)`` and return its Job handle."""
        job = Job(fn, args, priority=priority, max_attempts=max_attempts)
        with self._cv:
            if self._stop:
                raise RuntimeError("scheduler is shut down")
            heapq.heappush(self._heap, job)
            self.jobs[job.id] = job
            self._cv.notify()
        return job

    def pending(self):
        """Number of jobs queued but not yet picked up by a worker."""
        with self._cv:
            return len(self._heap)

    def _next_job(self):
        with self._cv:
            while not self._heap and not self._stop:
                self._cv.wait(timeout=0.05)
            if self._stop:
                return None
            return heapq.heappop(self._heap)

    def _worker_loop(self):
        while True:
            job = self._next_job()
            if job is None:
                return
            self._execute(job)

    def _execute(self, job):
        job.state = "running"
        job.attempts += 1
        try:
            job.result = job.fn(*job.args)
        except Exception as exc:
            job.error = repr(exc)
            if job.attempts < job.max_attempts:
                self.submit(job.fn, *job.args, priority=job.priority,
                            max_attempts=job.max_attempts)
            else:
                job.state = "failed"
            return
        job.state = "done"

    def shutdown(self):
        """Graceful drain: every submitted job runs to completion, the
        workers stop, and only then does shutdown return."""
        with self._cv:
            self._stop = True
            self._cv.notify_all()
        for t in self._threads:
            t.join()


def _demo():
    sched = Scheduler(workers=2)
    seen = []
    seen_lock = threading.Lock()

    def record(tag):
        with seen_lock:
            seen.append(tag)
        return tag

    jobs = [sched.submit(record, f"job-{i}", priority=(i % 3) + 1)
            for i in range(8)]
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if all(j.state == "done" for j in jobs):
            break
        time.sleep(0.01)
    assert all(j.state == "done" for j in jobs), [j.state for j in jobs]
    assert sorted(seen) == sorted(f"job-{i}" for i in range(8))
    assert all(jobs[i].result == f"job-{i}" for i in range(8))
    assert sched.pending() == 0
    sched.shutdown()
    print("OK")


if __name__ == "__main__":
    _demo()
