// Tab switching
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        // Remove active class from all tabs and containers
        document.querySelectorAll('.nav-item').forEach(navItem => {
            navItem.classList.remove('active');
        });
        document.querySelectorAll('.tab-container').forEach(container => {
            container.classList.remove('active');
        });

        // Add active class to clicked tab and corresponding container
        item.classList.add('active');
        const tabId = item.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
    });
});

function submitFeedback() {
    const agentId = document.getElementById('feedback-agent-select').value;
    const feedbackText = document.getElementById('feedback-text').value;

    if (!agentId || !feedbackText) {
        alert("Please select an agent and enter feedback.");
        return;
    }

    // Send feedback to the backend (this part requires a proper API endpoint)
    // For now, we'll just log it to the console.
    console.log(`Submitting feedback for ${agentId}: ${feedbackText}`);

    // In a real application, you would use fetch() to send this to a server endpoint
    // that calls the feedback_handler.submit_feedback() method.

    alert("Feedback submitted (logged to console).");
    document.getElementById('feedback-text').value = '';
}

// Function to load and display global progress
function loadGlobalProgress() {
    fetch('data/global_progress.json')
        .then(response => response.json())
        .then(data => {
            const globalProgressSection = document.querySelector('.global-progress');
            if (globalProgressSection) {
                const progressBar = globalProgressSection.querySelector('.progress-bar');
                const progressStats = globalProgressSection.querySelector('.progress-stats');

                if (progressBar) progressBar.style.width = `${data.percent_complete}%`;
                if (progressStats) {
                    progressStats.innerHTML = `
                        <div>Status: ${data.status}</div>
                        <div>${data.steps_completed} / ${data.total_steps} steps completed</div>
                        <div>Est. completion: ${new Date(data.estimated_completion).toLocaleTimeString()}</div>
                    `;
                }
            }
            // Update timestamp
            const updateTimeSpan = document.getElementById('update-time');
            if (updateTimeSpan) {
                 updateTimeSpan.textContent = new Date(data.last_updated).toLocaleString();
            }
        })
        .catch(error => console.error('Error loading global progress:', error));
}

// Function to load and display agent status
function loadAgentStatus() {
    fetch('data/agent_progress.json')
        .then(response => response.json())
        .then(data => {
            const agentGrid = document.querySelector('.agent-grid');
            const detailedProgressList = document.querySelector('#detailed-progress ul');
            const feedbackAgentSelect = document.getElementById('feedback-agent-select');


            if (agentGrid) {
                agentGrid.innerHTML = ''; // Clear existing agent cards
                Object.values(data).forEach(agent => {
                    const card = document.createElement('div');
                    card.className = 'agent-card';
                    card.innerHTML = `
                        <div class="agent-header">
                            <div class="agent-name">${agent.agent_id}</div>
                            <div class="agent-status ${agent.status.toLowerCase()}">${agent.status}</div>
                        </div>
                        <div class="agent-progress">
                            <div class="progress-bar-container">
                                <div class="progress-bar" style="width: ${agent.percent_complete}%"></div>
                            </div>
                        </div>
                        <div class="agent-activity">${agent.current_activity}</div>
                        <div class="agent-stats">
                            <div>Tasks: ${agent.tasks_completed}/${agent.total_tasks}</div>
                            <div>Thoughts: ${agent.thought_count}</div>
                        </div>
                    `;
                    agentGrid.appendChild(card);
                });
            }

            if (detailedProgressList) {
                 detailedProgressList.innerHTML = ''; // Clear existing items
                 Object.values(data).forEach(agent => {
                    const listItem = document.createElement('li');
                    listItem.innerHTML = `<strong>${agent.agent_id}</strong>: ${agent.current_activity}`;
                    detailedProgressList.appendChild(listItem);
                 });
            }

            if (feedbackAgentSelect) {
                feedbackAgentSelect.innerHTML = ''; // Clear existing options
                Object.keys(data).forEach(agentId => {
                    const option = document.createElement('option');
                    option.value = agentId;
                    option.textContent = agentId;
                    feedbackAgentSelect.appendChild(option);
                });
            }

        })
        .catch(error => console.error('Error loading agent progress:', error));
}


// Function to load and display timeline data
function loadTimelineData() {
    fetch('timeline/timeline_events.json')
        .then(response => response.json())
        .then(data => {
            const timelineContainer = document.querySelector('.timeline-container');
            if (timelineContainer) {
                timelineContainer.innerHTML = ''; // Clear existing static content
                data.forEach(event => {
                    const eventElement = document.createElement('div');
                    eventElement.className = 'timeline-event';

                    const eventHeader = document.createElement('div');
                    eventHeader.className = 'timeline-event-header';

                    const agentName = document.createElement('div');
                    agentName.className = 'timeline-agent';
                    agentName.textContent = event.agent_id;

                    const timestamp = document.createElement('div');
                    timestamp.className = 'timeline-timestamp';
                    // Format timestamp for display (e.g., only time part)
                    try {
                        timestamp.textContent = new Date(event.timestamp).toLocaleTimeString();
                    } catch (e) {
                        timestamp.textContent = event.timestamp; // Fallback
                    }

                    eventHeader.appendChild(agentName);
                    eventHeader.appendChild(timestamp);

                    const eventContent = document.createElement('div');
                    eventContent.className = 'timeline-content';
                    eventContent.textContent = event.content;

                    eventElement.appendChild(eventHeader);
                    eventElement.appendChild(eventContent);

                    timelineContainer.appendChild(eventElement);
                });
            }
        })
        .catch(error => console.error('Error loading timeline data:', error));
}

// Load data when the page is ready
document.addEventListener('DOMContentLoaded', () => {
    loadGlobalProgress();
    loadAgentStatus();
    loadTimelineData(); // Load timeline data

    // Optional: Refresh data periodically
    // setInterval(loadGlobalProgress, 30000); // Refresh every 30 seconds
    // setInterval(loadAgentStatus, 30000);  // Refresh every 30 seconds
    // setInterval(loadTimelineData, 30000); // Refresh timeline every 30 seconds

    // Add event listeners for refresh buttons
    const refreshProgressBtn = document.getElementById('refresh-progress');
    if (refreshProgressBtn) refreshProgressBtn.addEventListener('click', loadGlobalProgress);

    const refreshAgentsBtn = document.getElementById('refresh-agents');
    if (refreshAgentsBtn) refreshAgentsBtn.addEventListener('click', loadAgentStatus);

    const refreshTimelineBtn = document.getElementById('refresh-timeline');
    if (refreshTimelineBtn) refreshTimelineBtn.addEventListener('click', loadTimelineData);

    // For iframed content, their respective refresh buttons are inside the iframes.
    // If we wanted parent page to control iframe refresh:
    // const refreshThoughtsBtn = document.getElementById('refresh-thoughts');
    // if (refreshThoughtsBtn) refreshThoughtsBtn.addEventListener('click', () => {
    //     const iframe = document.querySelector('#thought-chains iframe');
    //     if (iframe) iframe.contentWindow.location.reload();
    // });
    // Similar for agent-network and decision-trees
});
