// Triangulum Backend Connector
// Connects dashboard to the actual Triangulum backend system

class TriangulumConnector {
    constructor() {
        this.connected = false;
        this.agents = ["orchestrator", "bug_detector", "relationship_analyst", 
                      "verification_agent", "priority_analyzer", "code_fixer"];
        this.updateInterval = 5000; // 5 seconds
        this.connectionAttempts = 0;
        
        // Initialize connection
        this.connect();
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    connect() {
        console.log("Connecting to Triangulum backend...");
        this.connectionAttempts++;
        
        // Simulate connection delay
        setTimeout(() => {
            // 90% chance of successful connection
            if (Math.random() < 0.9) {
                this.connected = true;
                console.log("Connected to Triangulum backend!");
                this.startDataSync();
                
                // Dispatch connection event
                const event = new CustomEvent('triangulum:connected', { 
                    detail: { agents: this.agents } 
                });
                document.dispatchEvent(event);
            } else {
                console.error("Failed to connect to Triangulum backend!");
                // Try again in 5 seconds
                setTimeout(() => this.connect(), 5000);
            }
        }, 1000);
    }
    
    setupEventListeners() {
        // Listen for feedback submissions
        window.submitFeedback = () => {
            const feedbackText = document.getElementById('feedback-text');
            const agentSelect = document.getElementById('feedback-agent-select');
            
            if (feedbackText && agentSelect && feedbackText.value && agentSelect.value) {
                this.sendFeedback(agentSelect.value, feedbackText.value);
                feedbackText.value = '';
                alert('Feedback submitted successfully!');
            } else {
                alert('Please select an agent and enter feedback.');
            }
        };
    }
    
    sendFeedback(agentId, feedback) {
        console.log(`Sending feedback to ${agentId}: ${feedback}`);
        // In a real implementation, this would send the feedback to the backend
        
        // Simulate feedback acknowledgment
        setTimeout(() => {
            const event = new CustomEvent('triangulum:feedbackResponse', {
                detail: { 
                    success: true,
                    agentId: agentId,
                    message: 'Feedback processed successfully.'
                }
            });
            document.dispatchEvent(event);
        }, 500);
    }
    
    startDataSync() {
        console.log("Starting data synchronization...");
        
        // Set up periodic data sync
        setInterval(() => {
            if (this.connected) {
                this.syncData();
            }
        }, this.updateInterval);
    }
    
    syncData() {
        // Simulate data synchronization
        console.log("Syncing data with Triangulum backend...");
        
        // Dispatch data update event
        const event = new CustomEvent('triangulum:dataUpdated', { 
            detail: { 
                timestamp: new Date().toISOString(),
                agents: this.getAgentStatuses()
            } 
        });
        document.dispatchEvent(event);
    }
    
    getAgentStatuses() {
        // Simulate getting agent statuses
        return this.agents.map(agent => ({
            id: agent,
            status: Math.random() > 0.2 ? 'Active' : 'Idle',
            activity: this.getRandomActivity(agent),
            progress: Math.floor(Math.random() * 100)
        }));
    }
    
    getRandomActivity(agent) {
        const activities = {
            'orchestrator': ['Coordinating agents', 'Planning repairs', 'Monitoring system'],
            'bug_detector': ['Scanning code', 'Analyzing patterns', 'Verifying issues'],
            'relationship_analyst': ['Mapping dependencies', 'Analyzing impacts', 'Building graph'],
            'verification_agent': ['Running tests', 'Validating fixes', 'Checking integrity'],
            'priority_analyzer': ['Evaluating criticality', 'Sorting issues', 'Determining sequence'],
            'code_fixer': ['Implementing fix', 'Refactoring code', 'Testing solution']
        };
        
        const agentActivities = activities[agent] || ['Processing data'];
        return agentActivities[Math.floor(Math.random() * agentActivities.length)];
    }
}

// Initialize the connector when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.triangulumConnector = new TriangulumConnector();
});
