#!/usr/bin/env python3

"""
FM-ENH-005: Results Analysis Script
Parses Locust CSV/JSON output and generates comprehensive performance report

Usage:
    python3 analyze_results.py <results_directory>
    python3 analyze_results.py ./results
"""

import argparse
import csv
import json
import os
import sys
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available, charts will not be generated")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available, using basic CSV parsing")


class PerformanceAnalyzer:
    """Analyzes performance test results and generates reports"""
    
    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_dir = self.results_dir / f"analysis_{self.timestamp}"
        self.report_dir.mkdir(exist_ok=True)
        
        # Test configurations
        self.test_configs = {
            "sustained": {
                "description": "Sustained baseline load (4 hours) - Memory leaks, connection stability",
                "users": 5,
                "duration": "4h",
                "target_rps": 1.2
            },
            "peak": {
                "description": "Peak load (1 hour) - p95 latency <300ms validation",
                "users": 50,
                "duration": "1h",
                "target_rps": 35.0
            },
            "spike": {
                "description": "Spike/Burst (5 minutes) - Aurora auto-scaling, no dropped requests",
                "users": 200,
                "duration": "5m",
                "target_rps": 166.0
            },
            "crdt_stress": {
                "description": "CRDT Stress (10 minutes) - Zero data loss, 1000+ concurrent conflicts",
                "users": 1000,
                "duration": "10m",
                "target_rps": 50.0
            }
        }
        
        # Acceptance criteria
        self.acceptance_criteria = {
            "p95_latency_ms": 300,
            "error_rate_percent": 5.0,
            "memory_limit_mb": 512,
            "crdt_data_loss": 0
        }
    
    def analyze_results_directory(self) -> Dict:
        """Analyze all test results in the directory"""
        print(f"Analyzing results in: {self.results_dir}")
        
        results = {}
        test_dirs = [d for d in self.results_dir.iterdir() if d.is_dir() and not d.name.startswith("analysis_")]
        
        for test_dir in test_dirs:
            test_name = test_dir.name.split('_')[0]  # Extract test name from directory
            if test_name in self.test_configs:
                print(f"Analyzing {test_name} test...")
                results[test_name] = self.analyze_single_test(test_dir, test_name)
        
        return results
    
    def analyze_single_test(self, test_dir: Path, test_name: str) -> Dict:
        """Analyze results from a single test"""
        results = {
            "test_name": test_name,
            "test_dir": str(test_dir),
            "config": self.test_configs[test_name],
            "locust_results": None,
            "memory_stats": None,
            "profiling_data": None,
            "acceptance_status": {},
            "metrics": {},
            "errors": []
        }
        
        try:
            # Analyze Locust results
            results["locust_results"] = self.analyze_locust_results(test_dir, test_name)
            
            # Analyze memory statistics
            results["memory_stats"] = self.analyze_memory_stats(test_dir)
            
            # Analyze profiling data
            results["profiling_data"] = self.analyze_profiling_data(test_dir, test_name)
            
            # Calculate metrics
            results["metrics"] = self.calculate_test_metrics(results)
            
            # Validate acceptance criteria
            results["acceptance_status"] = self.validate_acceptance_criteria(results)
            
        except Exception as e:
            results["errors"].append(f"Analysis error: {str(e)}")
            print(f"Error analyzing {test_name}: {e}")
        
        return results
    
    def analyze_locust_results(self, test_dir: Path, test_name: str) -> Dict:
        """Analyze Locust CSV results"""
        csv_files = list(test_dir.glob("*.csv"))
        if not csv_files:
            return {"error": "No CSV files found"}
        
        # Find the main stats CSV file
        stats_file = None
        for csv_file in csv_files:
            if not csv_file.name.startswith("exceptions") and not csv_file.name.startswith("failures"):
                stats_file = csv_file
                break
        
        if not stats_file:
            return {"error": "No stats CSV file found"}
        
        if PANDAS_AVAILABLE:
            return self.analyze_locust_with_pandas(stats_file)
        else:
            return self.analyze_locust_basic(stats_file)
    
    def analyze_locust_with_pandas(self, csv_file: Path) -> Dict:
        """Analyze Locust results using pandas"""
        try:
            df = pd.read_csv(csv_file)
            
            # Filter out aggregate rows
            df = df[df['Type'] != 'Aggregated']
            
            # Calculate metrics
            total_requests = df['Request Count'].sum()
            total_failures = df['Failure Count'].sum()
            avg_response_time = df['Average Response Time'].mean()
            
            # Calculate percentiles from response time data
            response_times = []
            for _, row in df.iterrows():
                response_times.extend([row['Average Response Time']] * int(row['Request Count']))
            
            if response_times:
                p50 = statistics.median(response_times)
                p95 = self.percentile(response_times, 95)
                p99 = self.percentile(response_times, 99)
                max_response_time = max(response_times)
            else:
                p50 = p95 = p99 = max_response_time = 0
            
            return {
                "total_requests": total_requests,
                "total_failures": total_failures,
                "success_rate": ((total_requests - total_failures) / total_requests * 100) if total_requests > 0 else 0,
                "avg_response_time_ms": avg_response_time,
                "p50_response_time_ms": p50,
                "p95_response_time_ms": p95,
                "p99_response_time_ms": p99,
                "max_response_time_ms": max_response_time,
                "requests_per_second": df['Requests/s'].mean() if 'Requests/s' in df.columns else 0
            }
        except Exception as e:
            return {"error": f"Pandas analysis failed: {str(e)}"}
    
    def analyze_locust_basic(self, csv_file: Path) -> Dict:
        """Basic Locust analysis without pandas"""
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Filter out aggregate rows
            rows = [row for row in rows if row.get('Type', '') != 'Aggregated']
            
            total_requests = sum(int(row.get('Request Count', 0)) for row in rows)
            total_failures = sum(int(row.get('Failure Count', 0)) for row in rows)
            
            # Calculate average response time
            response_times = []
            for row in rows:
                try:
                    response_times.extend([float(row.get('Average Response Time', 0))] * int(row.get('Request Count', 0)))
                except (ValueError, TypeError):
                    continue
            
            avg_response_time = statistics.mean(response_times) if response_times else 0
            p50 = statistics.median(response_times) if response_times else 0
            p95 = self.percentile(response_times, 95) if response_times else 0
            p99 = self.percentile(response_times, 99) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            
            return {
                "total_requests": total_requests,
                "total_failures": total_failures,
                "success_rate": ((total_requests - total_failures) / total_requests * 100) if total_requests > 0 else 0,
                "avg_response_time_ms": avg_response_time,
                "p50_response_time_ms": p50,
                "p95_response_time_ms": p95,
                "p99_response_time_ms": p99,
                "max_response_time_ms": max_response_time,
                "requests_per_second": 0  # Would need more complex calculation
            }
        except Exception as e:
            return {"error": f"Basic analysis failed: {str(e)}"}
    
    def analyze_memory_stats(self, test_dir: Path) -> Dict:
        """Analyze memory statistics from Go service"""
        memory_file = test_dir / "final_memory_stats.json"
        if not memory_file.exists():
            return {"error": "No memory stats file found"}
        
        try:
            with open(memory_file, 'r') as f:
                memory_data = json.load(f)
            
            return {
                "heap_alloc_mb": memory_data.get("heap_alloc_mb", 0),
                "heap_sys_mb": memory_data.get("heap_sys_mb", 0),
                "num_goroutines": memory_data.get("num_goroutines", 0),
                "num_gc": memory_data.get("num_gc", 0),
                "gc_cpu_fraction": memory_data.get("gc_cpu_fraction", 0),
                "timestamp": memory_data.get("timestamp", "")
            }
        except Exception as e:
            return {"error": f"Memory analysis failed: {str(e)}"}
    
    def analyze_profiling_data(self, test_dir: Path, test_name: str) -> Dict:
        """Analyze Go service profiling data"""
        profiles_dir = test_dir / "profiles"
        if not profiles_dir.exists():
            return {"error": "No profiling data found"}
        
        profiling_data = {
            "heap_profiles": [],
            "cpu_profiles": [],
            "memory_monitoring": None,
            "summary_files": []
        }
        
        # Find profiling files
        profiling_data["heap_profiles"] = list(profiles_dir.glob(f"*{test_name}*heap*.prof"))
        profiling_data["cpu_profiles"] = list(profiles_dir.glob(f"*{test_name}*cpu*.prof"))
        profiling_data["summary_files"] = list(profiles_dir.glob(f"*{test_name}*summary*.md"))
        
        # Find memory monitoring CSV
        memory_csv = list(profiles_dir.glob(f"*{test_name}*monitor*.csv"))
        if memory_csv:
            profiling_data["memory_monitoring"] = str(memory_csv[0])
        
        return profiling_data
    
    def calculate_test_metrics(self, test_results: Dict) -> Dict:
        """Calculate comprehensive test metrics"""
        metrics = {}
        
        # Locust metrics
        if test_results["locust_results"] and "error" not in test_results["locust_results"]:
            locust = test_results["locust_results"]
            metrics.update({
                "requests_per_second": locust.get("requests_per_second", 0),
                "success_rate_percent": locust.get("success_rate", 0),
                "error_rate_percent": 100 - locust.get("success_rate", 0),
                "avg_latency_ms": locust.get("avg_response_time_ms", 0),
                "p95_latency_ms": locust.get("p95_response_time_ms", 0),
                "p99_latency_ms": locust.get("p99_response_time_ms", 0)
            })
        
        # Memory metrics
        if test_results["memory_stats"] and "error" not in test_results["memory_stats"]:
            memory = test_results["memory_stats"]
            metrics.update({
                "final_heap_mb": memory.get("heap_alloc_mb", 0),
                "final_goroutines": memory.get("num_goroutines", 0),
                "gc_count": memory.get("num_gc", 0)
            })
        
        return metrics
    
    def validate_acceptance_criteria(self, test_results: Dict) -> Dict:
        """Validate acceptance criteria for the test"""
        status = {}
        metrics = test_results["metrics"]
        
        # P95 latency < 300ms
        p95_latency = metrics.get("p95_latency_ms", 0)
        status["p95_latency"] = {
            "requirement": "≤ 300ms",
            "actual": f"{p95_latency:.1f}ms",
            "passed": p95_latency <= self.acceptance_criteria["p95_latency_ms"],
            "test_name": test_results["test_name"]
        }
        
        # Error rate < 5%
        error_rate = metrics.get("error_rate_percent", 100)
        status["error_rate"] = {
            "requirement": "≤ 5%",
            "actual": f"{error_rate:.1f}%",
            "passed": error_rate <= self.acceptance_criteria["error_rate_percent"],
            "test_name": test_results["test_name"]
        }
        
        # Memory < 512MB
        memory_mb = metrics.get("final_heap_mb", 0)
        status["memory_usage"] = {
            "requirement": "< 512MB",
            "actual": f"{memory_mb:.1f}MB",
            "passed": memory_mb < self.acceptance_criteria["memory_limit_mb"],
            "test_name": test_results["test_name"]
        }
        
        # Overall status
        status["overall_passed"] = all(criteria["passed"] for criteria in status.values() if isinstance(criteria, dict) and "passed" in criteria)
        
        return status
    
    def percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a list of numbers"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        lower = int(index)
        upper = min(lower + 1, len(sorted_data) - 1)
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight
    
    def generate_charts(self, results: Dict):
        """Generate performance charts"""
        if not MATPLOTLIB_AVAILABLE:
            print("Skipping chart generation - matplotlib not available")
            return
        
        print("Generating performance charts...")
        
        # Latency comparison chart
        self.generate_latency_chart(results)
        
        # Memory usage chart
        self.generate_memory_chart(results)
        
        # Success rate chart
        self.generate_success_rate_chart(results)
        
        print(f"Charts saved in: {self.report_dir}")
    
    def generate_latency_chart(self, results: Dict):
        """Generate latency comparison chart"""
        test_names = []
        p95_latencies = []
        p99_latencies = []
        
        for test_name, test_data in results.items():
            if test_data["locust_results"] and "error" not in test_data["locust_results"]:
                test_names.append(test_name.replace("_", " ").title())
                p95_latencies.append(test_data["locust_results"]["p95_response_time_ms"])
                p99_latencies.append(test_data["locust_results"]["p99_response_time_ms"])
        
        if not test_names:
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        x = range(len(test_names))
        width = 0.35
        
        bars1 = ax.bar([i - width/2 for i in x], p95_latencies, width, label='P95 Latency', color='skyblue')
        bars2 = ax.bar([i + width/2 for i in x], p99_latencies, width, label='P99 Latency', color='lightcoral')
        
        # Add 300ms requirement line
        ax.axhline(y=300, color='red', linestyle='--', alpha=0.7, label='300ms Requirement')
        
        ax.set_xlabel('Test Scenarios')
        ax.set_ylabel('Latency (ms)')
        ax.set_title('P95 and P99 Latency by Test Scenario')
        ax.set_xticks(x)
        ax.set_xticklabels(test_names, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar in bars1 + bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}ms', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(self.report_dir / 'latency_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_memory_chart(self, results: Dict):
        """Generate memory usage chart"""
        test_names = []
        memory_usage = []
        
        for test_name, test_data in results.items():
            if test_data["memory_stats"] and "error" not in test_data["memory_stats"]:
                test_names.append(test_name.replace("_", " ").title())
                memory_usage.append(test_data["memory_stats"]["heap_alloc_mb"])
        
        if not test_names:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(test_names, memory_usage, color='lightgreen')
        
        # Add 512MB limit line
        ax.axhline(y=512, color='red', linestyle='--', alpha=0.7, label='512MB Limit')
        
        ax.set_xlabel('Test Scenarios')
        ax.set_ylabel('Memory Usage (MB)')
        ax.set_title('Go Service Memory Usage by Test Scenario')
        ax.set_xticklabels(test_names, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}MB', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(self.report_dir / 'memory_usage.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_success_rate_chart(self, results: Dict):
        """Generate success rate chart"""
        test_names = []
        success_rates = []
        
        for test_name, test_data in results.items():
            if test_data["locust_results"] and "error" not in test_data["locust_results"]:
                test_names.append(test_name.replace("_", " ").title())
                success_rates.append(test_data["locust_results"]["success_rate"])
        
        if not test_names:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(test_names, success_rates, color='lightblue')
        
        # Add 95% success rate line
        ax.axhline(y=95, color='red', linestyle='--', alpha=0.7, label='95% Success Rate')
        
        ax.set_xlabel('Test Scenarios')
        ax.set_ylabel('Success Rate (%)')
        ax.set_title('Request Success Rate by Test Scenario')
        ax.set_xticklabels(test_names, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(self.report_dir / 'success_rate.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_markdown_report(self, results: Dict):
        """Generate comprehensive markdown report"""
        report_file = self.report_dir / "performance_analysis_report.md"
        
        with open(report_file, 'w') as f:
            f.write(self.generate_report_content(results))
        
        print(f"Performance report generated: {report_file}")
    
    def generate_report_content(self, results: Dict) -> str:
        """Generate the content of the performance report"""
        content = []
        
        # Header
        content.append("# FM-ENH-005: Performance Analysis Report")
        content.append("")
        content.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"**Analysis Timestamp:** {self.timestamp}")
        content.append("")
        content.append("## Executive Summary")
        content.append("")
        
        # Overall status
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get("acceptance_status", {}).get("overall_passed", False))
        
        if passed_tests == total_tests:
            content.append("✅ **ALL TESTS PASSED** - All acceptance criteria met")
        else:
            content.append(f"❌ **{total_tests - passed_tests}/{total_tests} TESTS FAILED** - Some acceptance criteria not met")
        
        content.append("")
        content.append(f"- **Total Tests:** {total_tests}")
        content.append(f"- **Passed Tests:** {passed_tests}")
        content.append(f"- **Failed Tests:** {total_tests - passed_tests}")
        content.append("")
        
        # Test Summary Table
        content.append("## Test Summary")
        content.append("")
        content.append("| Test | Description | Users | Duration | Status | P95 Latency | Memory | Success Rate |")
        content.append("|------|-------------|-------|----------|--------|-------------|--------|--------------|")
        
        for test_name, test_data in results.items():
            config = test_data["config"]
            status = test_data["acceptance_status"]
            
            status_icon = "✅" if status.get("overall_passed", False) else "❌"
            p95_latency = f"{test_data['metrics'].get('p95_latency_ms', 0):.1f}ms"
            memory = f"{test_data['metrics'].get('final_heap_mb', 0):.1f}MB"
            success_rate = f"{test_data['metrics'].get('success_rate_percent', 0):.1f}%"
            
            content.append(f"| {test_name} | {config['description'][:50]}... | {config['users']} | {config['duration']} | {status_icon} | {p95_latency} | {memory} | {success_rate} |")
        
        content.append("")
        
        # Acceptance Criteria Validation
        content.append("## Acceptance Criteria Validation")
        content.append("")
        
        for criterion, limit in self.acceptance_criteria.items():
            content.append(f"### {criterion.replace('_', ' ').title()}")
            content.append("")
            
            criterion_passed = 0
            criterion_total = 0
            
            for test_name, test_data in results.items():
                criterion_total += 1
                if test_data["acceptance_status"].get(criterion.replace("_", " "), {}).get("passed", False):
                    criterion_passed += 1
            
            status_icon = "✅" if criterion_passed == criterion_total else "❌"
            content.append(f"{status_icon} **{criterion_passed}/{criterion_total} tests passed**")
            content.append("")
            
            # Detailed results
            for test_name, test_data in results.items():
                criterion_status = test_data["acceptance_status"].get(criterion.replace("_", " "), {})
                if criterion_status:
                    passed_icon = "✅" if criterion_status.get("passed", False) else "❌"
                    requirement = criterion_status.get("requirement", "N/A")
                    actual = criterion_status.get("actual", "N/A")
                    content.append(f"- {passed_icon} **{test_name}:** {actual} (requirement: {requirement})")
            
            content.append("")
        
        # Detailed Test Results
        content.append("## Detailed Test Results")
        content.append("")
        
        for test_name, test_data in results.items():
            content.append(f"### {test_name.replace('_', ' ').title()}")
            content.append("")
            
            config = test_data["config"]
            content.append(f"**Description:** {config['description']}")
            content.append(f"**Users:** {config['users']}")
            content.append(f"**Duration:** {config['duration']}")
            content.append("")
            
            # Metrics
            metrics = test_data["metrics"]
            if metrics:
                content.append("**Performance Metrics:**")
                content.append(f"- Requests/Second: {metrics.get('requests_per_second', 0):.1f}")
                content.append(f"- Success Rate: {metrics.get('success_rate_percent', 0):.1f}%")
                content.append(f"- Average Latency: {metrics.get('avg_latency_ms', 0):.1f}ms")
                content.append(f"- P95 Latency: {metrics.get('p95_latency_ms', 0):.1f}ms")
                content.append(f"- P99 Latency: {metrics.get('p99_latency_ms', 0):.1f}ms")
                content.append(f"- Final Memory: {metrics.get('final_heap_mb', 0):.1f}MB")
                content.append(f"- Goroutines: {metrics.get('final_goroutines', 0)}")
                content.append("")
            
            # Errors
            if test_data["errors"]:
                content.append("**Errors:**")
                for error in test_data["errors"]:
                    content.append(f"- {error}")
                content.append("")
        
        # Charts section
        if MATPLOTLIB_AVAILABLE:
            content.append("## Performance Charts")
            content.append("")
            content.append("![Latency Comparison](latency_comparison.png)")
            content.append("")
            content.append("![Memory Usage](memory_usage.png)")
            content.append("")
            content.append("![Success Rate](success_rate.png)")
            content.append("")
        
        # Recommendations
        content.append("## Recommendations")
        content.append("")
        
        failed_tests = [name for name, data in results.items() if not data["acceptance_status"].get("overall_passed", False)]
        
        if not failed_tests:
            content.append("✅ All tests passed! The system meets all performance requirements for 100k req/day.")
            content.append("")
            content.append("**Next Steps:**")
            content.append("- Monitor performance in production")
            content.append("- Set up automated performance regression testing")
            content.append("- Consider implementing Aurora PostgreSQL for production scaling")
        else:
            content.append("❌ Some tests failed. Recommendations:")
            content.append("")
            
            for test_name in failed_tests:
                test_data = results[test_name]
                content.append(f"### {test_name.replace('_', ' ').title()}")
                content.append("")
                
                status = test_data["acceptance_status"]
                if not status.get("p95_latency", {}).get("passed", False):
                    content.append("- **Latency Issue:** Optimize database queries, implement caching, or scale resources")
                
                if not status.get("memory_usage", {}).get("passed", False):
                    content.append("- **Memory Issue:** Review memory leaks, optimize data structures, or increase memory limits")
                
                if not status.get("error_rate", {}).get("passed", False):
                    content.append("- **Error Rate Issue:** Review error handling, improve service reliability")
                
                content.append("")
        
        # Aurora Considerations
        content.append("## Aurora PostgreSQL Considerations")
        content.append("")
        content.append("For production deployment at 100k req/day scale:")
        content.append("")
        content.append("### Auto-Scaling Configuration")
        content.append("- **Min ACU:** 2 (baseline performance)")
        content.append("- **Max ACU:** 16 (peak load handling)")
        content.append("- **Target CPU:** 70% (trigger scaling)")
        content.append("- **Scale Cooldown:** 5 minutes")
        content.append("")
        content.append("### Expected Scaling Behavior")
        content.append("- **Sustained Load:** 2-4 ACU (baseline + buffer)")
        content.append("- **Peak Load:** 8-12 ACU (business hours)")
        content.append("- **Spike Load:** 12-16 ACU (traffic bursts)")
        content.append("")
        content.append("### Monitoring Requirements")
        content.append("- Track ACU scaling events")
        content.append("- Monitor scaling latency (should be < 1 minute)")
        content.append("- Alert on scaling failures")
        content.append("")
        
        # Technical Details
        content.append("## Technical Details")
        content.append("")
        content.append("### Test Environment")
        content.append(f"- **Results Directory:** {self.results_dir}")
        content.append(f"- **Analysis Timestamp:** {self.timestamp}")
        content.append(f"- **Total Tests Analyzed:** {len(results)}")
        content.append("")
        
        # Files Generated
        content.append("### Files Generated")
        content.append("")
        content.append("- `performance_analysis_report.md` - This comprehensive report")
        if MATPLOTLIB_AVAILABLE:
            content.append("- `latency_comparison.png` - Latency comparison chart")
            content.append("- `memory_usage.png` - Memory usage chart")
            content.append("- `success_rate.png` - Success rate chart")
        content.append("")
        
        return "\n".join(content)
    
    def run_analysis(self):
        """Run complete analysis"""
        print("Starting performance analysis...")
        
        # Analyze results
        results = self.analyze_results_directory()
        
        if not results:
            print("No test results found to analyze")
            return
        
        print(f"Analyzed {len(results)} test results")
        
        # Generate charts
        self.generate_charts(results)
        
        # Generate report
        self.generate_markdown_report(results)
        
        # Print summary
        self.print_analysis_summary(results)
        
        print(f"\nAnalysis complete! Report saved in: {self.report_dir}")
    
    def print_analysis_summary(self, results: Dict):
        """Print analysis summary to console"""
        print("\n" + "="*80)
        print("PERFORMANCE ANALYSIS SUMMARY")
        print("="*80)
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get("acceptance_status", {}).get("overall_passed", False))
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed Tests: {passed_tests}")
        print(f"Failed Tests: {total_tests - passed_tests}")
        print("")
        
        for test_name, test_data in results.items():
            status = test_data["acceptance_status"]
            status_icon = "✅" if status.get("overall_passed", False) else "❌"
            
            print(f"{status_icon} {test_name}:")
            
            # Key metrics
            metrics = test_data["metrics"]
            if metrics:
                print(f"   P95 Latency: {metrics.get('p95_latency_ms', 0):.1f}ms")
                print(f"   Memory: {metrics.get('final_heap_mb', 0):.1f}MB")
                print(f"   Success Rate: {metrics.get('success_rate_percent', 0):.1f}%")
            
            # Failed criteria
            failed_criteria = []
            for criterion, status_data in status.items():
                if isinstance(status_data, dict) and not status_data.get("passed", False):
                    failed_criteria.append(criterion)
            
            if failed_criteria:
                print(f"   Failed: {', '.join(failed_criteria)}")
            
            print("")


def main():
    parser = argparse.ArgumentParser(description="Analyze FM-ENH-005 performance test results")
    parser.add_argument("results_dir", help="Directory containing test results")
    parser.add_argument("--output", "-o", help="Output directory for analysis (default: results_dir/analysis_TIMESTAMP)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.results_dir):
        print(f"Error: Results directory '{args.results_dir}' does not exist")
        sys.exit(1)
    
    analyzer = PerformanceAnalyzer(args.results_dir)
    analyzer.run_analysis()


if __name__ == "__main__":
    main()
