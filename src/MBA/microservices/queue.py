"""
Simple in-memory queue for job processing.

Thread-safe job queue implementation for microservices mode.

Module Input:
    - Job objects for enqueueing
    - Worker requests for jobs

Module Output:
    - Job objects for processing
    - Queue statistics
    - Completion signals
"""
import threading
from dataclasses import dataclass
from pathlib import Path
from queue import Queue, Empty
from typing import Optional, List

from ..core.logging_config import get_logger
from ..core.exceptions import QueueError

logger = get_logger(__name__)


@dataclass
class Job:
    """
    Represents a file upload job.
    
    Encapsulates all information needed to upload a file to S3.
    
    Attributes:
        path (Path): Local file path to upload
        scope (str): Data scope ('mba' or 'policy')
        s3_key (str): Target S3 object key
        bucket (str): Target S3 bucket name
    """
    path: Path          # Local file path
    scope: str          # "mba" or "policy"
    s3_key: str        # Target S3 key
    bucket: str        # Target S3 bucket
    
    def __str__(self) -> str:
        return f"Job(file={self.path.name}, bucket={self.bucket}, key={self.s3_key})"


class JobQueue:
    """
    Thread-safe in-memory job queue.
    
    Implements a producer-consumer queue pattern for distributing
    upload jobs across multiple workers.
    
    Attributes:
        _queue (Queue): Internal thread-safe queue
        _lock (threading.Lock): Synchronization for statistics
        _processed_count (int): Successfully processed jobs
        _failed_count (int): Failed job count
    """
    
    def __init__(self, maxsize: int = 0):
        """
        Initialize job queue.
        
        Args:
            maxsize: Maximum queue size (0 for unlimited)
        """
        self._queue = Queue(maxsize=maxsize)
        self._lock = threading.Lock()
        self._processed_count = 0
        self._failed_count = 0
        
    def put(self, job: Job) -> None:
        """
        Add job to queue.
        
        Args:
            job (Job): Job to enqueue
            
        Side Effects:
            - Adds job to internal queue
            - Logs enqueue operation
        """
        logger.debug(f"Enqueueing job: {job}")
        self._queue.put(job)
        
    def get(self, timeout: Optional[float] = None) -> Optional[Job]:
        """
        Get job from queue with optional timeout.
        
        Args:
            timeout (Optional[float]): Wait timeout in seconds
            
        Returns:
            Optional[Job]: Job if available, None on timeout
            
        Blocking Behavior:
            - timeout=None: Block until job available
            - timeout=0: Non-blocking
            - timeout>0: Wait up to timeout seconds
        """
        try:
            job = self._queue.get(timeout=timeout)
            logger.debug(f"Dequeued job: {job}")
            return job
        except Empty:
            return None
            
    def task_done(self) -> None:
        """Mark task as done."""
        self._queue.task_done()
        with self._lock:
            self._processed_count += 1
            
    def mark_failed(self) -> None:
        """Mark task as failed."""
        with self._lock:
            self._failed_count += 1
            
    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
        
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
        
    def stats(self) -> dict:
        """
        Get queue statistics.
        
        Returns:
            dict: Statistics containing:
                - queued (int): Current queue size
                - processed (int): Completed jobs
                - failed (int): Failed jobs
                - total (int): Sum of all categories
                
        Thread Safety:
            Uses lock for consistent snapshot
        """
        with self._lock:
            return {
                "queued": self.size(),
                "processed": self._processed_count,
                "failed": self._failed_count,
                "total": self._processed_count + self._failed_count + self.size()
            }
    
    def join(self) -> None:
        """Block until all tasks are done."""
        self._queue.join()


# Global queue instance for microservices
job_queue = JobQueue()