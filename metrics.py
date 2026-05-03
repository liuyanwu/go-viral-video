"""
Pipeline metrics collection and reporting.

Tracks execution statistics including processing times per stage,
success/failure rates, and error counts. Useful for monitoring
pipeline performance and identifying bottlenecks.

Usage:
    from metrics import metrics
    
    # Record a pipeline run
    metrics.record_run(success=True, duration=45.2)
    
    # Record stage timing
    metrics.record_stage("download", 5.1)
    
    # Get summary
    print(metrics.get_summary())
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from utils.logger import setup_logger

logger = setup_logger("Metrics")

@dataclass
class PipelineMetrics:
    """Collects and reports pipeline execution metrics."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_processing_time: float = 0.0
    stage_times: Dict[str, list] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    def record_run(self, success: bool, duration: float):
        self.total_runs += 1
        if success:
            self.successful_runs += 1
        else:
            self.failed_runs += 1
        self.total_processing_time += duration
    
    def record_stage(self, stage: str, duration: float):
        if stage not in self.stage_times:
            self.stage_times[stage] = []
        self.stage_times[stage].append(duration)
    
    def record_error(self, error_type: str):
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        avg_time = self.total_processing_time / max(self.total_runs, 1)
        success_rate = self.successful_runs / max(self.total_runs, 1) * 100
        return {
            "total_runs": self.total_runs,
            "success_rate": f"{success_rate:.1f}%",
            "avg_processing_time": f"{avg_time:.1f}s",
            "stage_avg_times": {
                stage: f"{sum(times)/len(times):.1f}s"
                for stage, times in self.stage_times.items()
            },
            "error_counts": dict(self.error_counts),
        }
    
    def reset(self):
        self.__init__()

metrics = PipelineMetrics()
