import logging
import queue
import threading
import time
import uuid

logger = logging.getLogger(__name__)


class BackgroundJobStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InMemoryJobStatusStore:
    def __init__(self):
        self._statuses = {}
        self._lock = threading.Lock()

    def create_job(self) -> uuid.UUID:
        job_id = uuid.uuid4()
        with self._lock:
            self._statuses[job_id] = BackgroundJobStatus.PENDING
        return job_id

    def get_status(self, job_id: uuid.UUID) -> str | None:
        with self._lock:
            return self._statuses.get(job_id)

    def set_status(self, job_id: uuid.UUID, status: str) -> None:
        with self._lock:
            self._statuses[job_id] = status

    def clear(self) -> None:
        with self._lock:
            self._statuses.clear()


class BackgroundTaskQueue:
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self._queue = queue.Queue(maxsize=capacity)

    def enqueue(self, work_item) -> None:
        if work_item is None:
            raise ValueError("work_item cannot be None")
        self._queue.put(work_item)

    def dequeue(self, timeout: float = 0.5):
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def task_done(self) -> None:
        self._queue.task_done()


class RegistrationConfirmationSender:
    def __init__(self, delay: float = 2.0):
        self.delay = delay

    def send(self, attendee_email: str) -> None:
        logger.info(f"Sending registration confirmation to {attendee_email}...")
        if "fail" in attendee_email.lower():
            raise RuntimeError(f"Simulation error: unable to send email to {attendee_email}")
        if self.delay > 0:
            time.sleep(self.delay)
        logger.info(f"Registration confirmation sent to {attendee_email}.")


class BackgroundTaskWorker:
    def __init__(self, task_queue: BackgroundTaskQueue):
        self.task_queue = task_queue
        self._stopping = threading.Event()
        self._thread = None

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._stopping.clear()
            self._thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="BackgroundTaskWorker",
            )
            self._thread.start()

    def stop(self) -> None:
        self._stopping.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stopping.is_set():
            work_item = self.task_queue.dequeue(timeout=0.5)
            if work_item is None:
                continue
            try:
                work_item(self._stopping)
            except Exception as exc:
                logger.error("A background job failed.", exc_info=exc)
            finally:
                self.task_queue.task_done()


job_status_store = InMemoryJobStatusStore()
background_task_queue = BackgroundTaskQueue(capacity=100)
confirmation_sender = RegistrationConfirmationSender()
background_worker = BackgroundTaskWorker(background_task_queue)
