# Triangulum-FixWurx Evaluation Plan

## Executive Summary

This plan outlines a systematic approach to use the incomplete FixWurx project as a controlled test environment for evaluating and improving Triangulum's capabilities as an agentic repair system. Rather than merely attempting to fix FixWurx, the primary goal is to gather comprehensive data about Triangulum's strengths, limitations, and potential areas for enhancement.

**Key Principle:** Every outcome—successful repairs, partial improvements, or failures—provides valuable data that can be used to enhance Triangulum's capabilities.

## Objective

Use the FixWurx codebase (approximately 80% complete) as a controlled test environment to systematically evaluate and improve Triangulum's capabilities as an agentic repair system, focusing on data collection rather than repair success.

## Execution Plan

### Phase 1: Baseline Assessment (Day 1)

**Actions:**
1. Create a snapshot of FixWurx current state
2. Run Triangulum dependency graph builder on FixWurx
3. Extract relationship data between components
4. Generate bug detection report
5. Document all identified issues and missing connections

**Data Collection:**
- Complete component inventory
- Dependency graph visualization
- Comprehensive bug report
- Missing functionality assessment
- Agent activation patterns during analysis

**Implementation:**
```python
# Create snapshot of current FixWurx state
snapshot_directory = "../FixWurx_snapshot"
triangulum_folder_healer.create_snapshot("../FixWurx", snapshot_directory)

# Run dependency graph analysis
from triangulum_lx.tooling.dependency_graph import DependencyGraphBuilder
builder = DependencyGraphBuilder(cache_dir="./cache")
graph = builder.build_graph("../FixWurx")

# Run bug detection
from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent
bug_detector = BugDetectorAgent()
bugs_report = bug_detector.detect_bugs_in_folder("../FixWurx", recursive=True)

# Save all results to assessment directory
assessment_dir = "./fixwurx_assessment"
os.makedirs(assessment_dir, exist_ok=True)
```

### Phase 2: Repair Strategy (Day 2)

**Actions:**
1. Run Triangulum strategy formulation on FixWurx issues
2. Generate prioritized repair sequence
3. Document repair approach for each component
4. Identify inter-component dependencies in repair plan
5. Set specific success criteria for each repair

**Data Collection:**
- Prioritized issue list with reasoning
- Repair strategy document
- Component dependency mapping
- Agent collaboration patterns
- Decision points with supporting evidence

**Implementation:**
```python
# Generate repair strategy
from triangulum_lx.agents.priority_analyzer_agent import PriorityAnalyzerAgent
priority_analyzer = PriorityAnalyzerAgent()
prioritized_issues = priority_analyzer.analyze_priorities(
    folder_path="../FixWurx", 
    bugs_by_file=bugs_report["bugs_by_file"],
    relationships=graph.to_dict()
)

# Generate repair sequence
from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent
orchestrator = OrchestratorAgent()
repair_plan = orchestrator.generate_repair_plan(prioritized_issues)

# Save repair strategy to strategy directory
strategy_dir = "./fixwurx_strategy"
os.makedirs(strategy_dir, exist_ok=True)
```

### Phase 3: Implementation (Days 3-4)

**Actions:**
1. Execute automated repairs using Triangulum
2. Track every code modification with before/after snapshots
3. Document all agent communications during repair
4. Record progress metrics every hour
5. Save all intermediate states of FixWurx

**Data Collection:**
- Code diff for every change
- Agent activation sequence logs
- Time spent per repair type
- Success/failure rate by issue type
- Error handling patterns

**Implementation:**
```python
# Execute repairs with detailed logging
from triangulum_lx.tooling.repair import RepairTool
repair_tool = RepairTool(
    logging_level="DEBUG",
    save_intermediate_states=True,
    intermediate_states_dir="./fixwurx_intermediate_states"
)

# Create communication logger
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus
message_bus = EnhancedMessageBus(log_to_file=True, log_file="./fixwurx_communication.log")

# Run automated repair sequence
for issue in repair_plan["repair_sequence"]:
    # Track before state
    before_snapshot = repair_tool.snapshot_file(issue["file_path"])
    
    # Execute repair
    repair_result = repair_tool.repair_issue(issue)
    
    # Track after state
    after_snapshot = repair_tool.snapshot_file(issue["file_path"])
    
    # Save diff and results
    repair_tool.save_diff(before_snapshot, after_snapshot, f"./repairs/{issue['id']}_diff.txt")
    repair_tool.save_result(repair_result, f"./repairs/{issue['id']}_result.json")
```

### Phase 4: Verification (Day 5)

**Actions:**
1. Run Triangulum verification on all repairs
2. Execute any available test suites
3. Attempt to run core FixWurx functionality
4. Document functionality improvements
5. Identify remaining issues

**Data Collection:**
- Test results for each repair
- Functional vs non-functional components
- Self-verification accuracy metrics
- False positive/negative rate
- Remaining issue inventory

**Implementation:**
```python
# Run verification agent
from triangulum_lx.agents.verification_agent import VerificationAgent
verification_agent = VerificationAgent()

# Verify each repair
verification_results = {}
for repair_id in repairs_performed:
    repair_info = repair_tool.get_repair_info(repair_id)
    verification_result = verification_agent.verify_repair(repair_info)
    verification_results[repair_id] = verification_result

# Run available tests
import subprocess
test_results = {}
for test_file in find_test_files("../FixWurx"):
    result = subprocess.run(
        [sys.executable, "-m", "unittest", test_file],
        capture_output=True, 
        text=True
    )
    test_results[test_file] = {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

# Try to run FixWurx
try:
    subprocess.run(
        [sys.executable, "../FixWurx/main.py"],
        timeout=60,
        capture_output=True,
        text=True
    )
except Exception as e:
    print(f"FixWurx execution error: {e}")
```

### Phase 5: Capability Analysis (Day 6-7)

**Actions:**
1. Analyze repair success/failure patterns
2. Identify Triangulum strengths and weaknesses
3. Map repair techniques to success rates
4. Document agent effectiveness by task type
5. Create Triangulum enhancement recommendations

**Data Collection:**
- Success pattern analysis
- Capability gap assessment
- Agent effectiveness matrix
- Enhancement priority list
- Performance metrics summary

**Implementation:**
```python
# Analyze success patterns
successful_repairs = [r for r in verification_results.values() if r["success"]]
failed_repairs = [r for r in verification_results.values() if not r["success"]]

# Calculate success rates by issue type
success_by_type = {}
for issue_type in set(r["issue_type"] for r in repair_plan["repair_sequence"]):
    type_repairs = [r for r in verification_results.values() if r["issue_type"] == issue_type]
    type_successes = [r for r in type_repairs if r["success"]]
    success_by_type[issue_type] = len(type_successes) / len(type_repairs) if type_repairs else 0

# Calculate agent effectiveness
agent_effectiveness = {}
for agent_name in ["bug_detector", "relationship_analyst", "orchestrator", "verification"]:
    agent_effectiveness[agent_name] = analyze_agent_effectiveness(agent_name, message_bus.get_logs())

# Generate enhancement recommendations
enhancement_recommendations = generate_enhancement_recommendations(
    success_by_type, 
    agent_effectiveness,
    failed_repairs
)
```

## Success Criteria

1. **Data Completeness:** Collected comprehensive data on all Triangulum operations
2. **Pattern Identification:** Identified clear patterns in repair success/failure
3. **Capability Mapping:** Created detailed map of current Triangulum capabilities
4. **Enhancement Roadmap:** Developed specific, actionable improvement recommendations
5. **Knowledge Transfer:** Documented all findings for future Triangulum development

## Governance Rules

1. No deviations from the established phases without approval
2. Data collection takes priority over repair success
3. All observations must be documented, especially unexpected behaviors
4. Progress updates required at the end of each phase
5. No intervention in Triangulum's operations except to collect data

## Deliverables

1. **FixWurx Assessment Report:** Complete analysis of FixWurx initial state
2. **Repair Strategy Document:** Triangulum's approach to fixing FixWurx
3. **Repair Implementation Log:** Detailed record of all repair attempts
4. **Verification Results:** Outcomes of all verification activities
5. **Triangulum Capability Report:** Analysis of strengths, weaknesses and recommendations

## Tools Required

1. **Code Snapshot Tool:** For creating before/after snapshots of code changes
   ```python
   def create_snapshot(directory, output_path):
       # Implementation details...
   ```

2. **Agent Communication Logger:** For recording inter-agent messages
   ```python
   class AgentCommunicationLogger:
       def __init__(self, log_file):
           self.log_file = log_file
           # Implementation details...
   ```

3. **Repair Attempt Tracker:** For monitoring repair attempts and outcomes
   ```python
   class RepairTracker:
       def __init__(self, output_directory):
           self.output_directory = output_directory
           # Implementation details...
   ```

4. **Automated Test Runner:** For verifying repairs through testing
   ```python
   class TestRunner:
       def __init__(self, test_directory):
           self.test_directory = test_directory
           # Implementation details...
   ```

5. **Data Analysis Framework:** For analyzing repair patterns and agent effectiveness
   ```python
   class RepairAnalyzer:
       def __init__(self, repair_data, verification_data):
           self.repair_data = repair_data
           self.verification_data = verification_data
           # Implementation details...
   ```

## Data Collection Framework

```python
class TriangulumDataCollector:
    def __init__(self, base_directory):
        self.base_directory = base_directory
        self.agent_data = {}
        self.repair_data = {}
        self.verification_data = {}
        # Initialize collectors for each data type
        
    def collect_agent_activation(self, agent_id, timestamp, context):
        # Record when an agent is activated
        
    def collect_agent_communication(self, sender, recipient, message_type, content):
        # Record inter-agent communication
        
    def collect_repair_attempt(self, repair_id, file_path, issue_type, before_state, after_state):
        # Record repair attempts
        
    def collect_verification_result(self, repair_id, success, error_message, test_results):
        # Record verification outcomes
        
    def analyze_data(self):
        # Analyze collected data to identify patterns
        
    def generate_report(self, output_path):
        # Generate comprehensive report from collected data
```

## Expected Results

This evaluation will produce a comprehensive dataset showing:

1. Which types of code issues Triangulum handles well
2. Which types of code issues Triangulum struggles with
3. How Triangulum's different agents work together in real-world scenarios
4. What specific enhancements would most improve Triangulum's capabilities

Most importantly, this approach ensures that both success and failure are equally valuable outcomes, as both provide critical data for improving Triangulum.
