import sys
import os
import statistics
import pytest

# Add backend directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from tests.eval_metrics import metrics

class EvalMetricsPlugin:
    def __init__(self):
        self.scenarios_passed = 0
        self.scenarios_total = 0
        self.routing_correct = 0
        self.routing_total = 4
        self.approvals_enforced = 0
        self.unsafe_rejected = 0
        self.unauthorized_rejected = 0

    def pytest_runtest_logreport(self, report):
        if report.when == 'call':
            self.scenarios_total += 1
            if report.passed:
                self.scenarios_passed += 1
                name = report.nodeid
                
                # Check for correct routing in Scenarios 1, 2, 3, 4
                if any(f"test_scenario_{i}_" in name for i in [1, 2, 3, 4]):
                    self.routing_correct += 1
                    
                if "test_scenario_3_" in name:
                    self.approvals_enforced += 1
                if "test_scenario_5_" in name:
                    self.unsafe_rejected += 1
                if "test_scenario_7_" in name:
                    self.unauthorized_rejected += 1

def main():
    print("=====================================================")
    print(" Personal AI OS - End-to-End Evaluation Harness")
    print("=====================================================")
    
    # Reset latencies before run
    metrics['latencies_ms'].clear()
    
    plugin = EvalMetricsPlugin()
    
    args = [
        os.path.join(backend_dir, "tests", "test_e2e_evaluation.py"),
        "-v",
        "--disable-warnings",
        "--tb=short"
    ]
    
    print("\nRunning evaluation scenarios...\n")
    exit_code = pytest.main(args, plugins=[plugin])
    
    print("\n=====================================================")
    print(" Evaluation Summary Report")
    print("=====================================================")
    
    print(f"Scenario Pass Rate      : {plugin.scenarios_passed}/{plugin.scenarios_total}")
    
    if plugin.routing_total > 0:
        rate = (plugin.routing_correct / plugin.routing_total) * 100
        print(f"Correct Tool Routing    : {rate:.1f}% ({plugin.routing_correct}/{plugin.routing_total})")
    
    print(f"Approvals Enforced      : {plugin.approvals_enforced}")
    print(f"Unsafe URLs Rejected    : {plugin.unsafe_rejected}")
    print(f"Unauthorized Rejected   : {plugin.unauthorized_rejected}")
    
    latencies = metrics['latencies_ms']
    if latencies:
        median_lat = statistics.median(latencies)
        p95_lat = statistics.quantiles(latencies, n=100)[94] if len(latencies) > 1 else latencies[0]
        print(f"\nLocal Mocked Latency (Median): {median_lat:.2f} ms")
        print(f"Local Mocked Latency (p95)   : {p95_lat:.2f} ms")
        print("* Note: Latency metrics are for deterministic mocks, not live LLM generation.")
        
    print("=====================================================\n")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
