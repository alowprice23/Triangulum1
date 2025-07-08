#!/usr/bin/env python3
"""
Token Processing Visualizer

This module provides detailed visualization of token-level processing
during LLM operations, including confidence scoring, attention patterns,
and processing time metrics.
"""

import os
import time
import json
import logging
import datetime
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenProcessingVisualizer:
    """
    Visualizer for token-level processing during LLM operations.
    
    Provides detailed visualization of token generation, confidence scores,
    attention patterns, and processing time metrics to enhance transparency
    into the internal LLM reasoning process.
    """
    
    def __init__(self, 
                 output_dir: str = "./token_visualization",
                 update_interval: float = 0.5,
                 max_tokens_per_chart: int = 50,
                 save_raw_data: bool = True):
        """
        Initialize the token processing visualizer.
        
        Args:
            output_dir: Directory to store visualization outputs
            update_interval: How frequently to update visualizations (seconds)
            max_tokens_per_chart: Maximum number of tokens to show in a single chart
            save_raw_data: Whether to save raw token data in JSON format
        """
        self.output_dir = output_dir
        self.update_interval = update_interval
        self.max_tokens_per_chart = max_tokens_per_chart
        self.save_raw_data = save_raw_data
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "data"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "charts"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "attention"), exist_ok=True)
        
        # Store active processing sessions
        self.sessions = {}  # session_id -> session data
        
        # Store token data
        self.token_data = {}  # session_id -> list of token data
        
        # Timestamp of last visualization update
        self.last_update = time.time()
        
        # Store HTML templates
        self.main_template = ""
        self.session_template = ""
        
        # Load templates and create main HTML
        self._load_templates()
        self._create_main_html()
        
        logger.info(f"Token Processing Visualizer initialized with output_dir={output_dir}")
    
    def _load_templates(self):
        """Load HTML templates from strings."""
        self.main_template = """<!DOCTYPE html>
<html>
<head>
    <title>LLM Token Processing Visualization</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f2f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background-color: #001529; color: white; padding: 15px 20px; border-radius: 6px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .title { font-size: 24px; font-weight: bold; }
        .timestamp { font-size: 14px; color: #d9d9d9; }
        .session-container { background-color: white; border-radius: 6px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .session-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #f0f0f0; }
        .session-title { font-size: 18px; font-weight: bold; color: #333; }
        .session-meta { font-size: 14px; color: #666; }
        .token-text { font-family: 'Courier New', monospace; margin-bottom: 15px; padding: 15px; background-color: #f9f9f9; border-radius: 4px; line-height: 1.5; white-space: pre-wrap; }
        .token { display: inline-block; padding: 2px 4px; margin: 2px; border-radius: 3px; }
        .confidence-high { background-color: rgba(82, 196, 26, 0.2); }
        .confidence-medium { background-color: rgba(250, 173, 20, 0.2); }
        .confidence-low { background-color: rgba(245, 34, 45, 0.2); }
        .chart-container { margin-top: 20px; margin-bottom: 20px; }
        .chart-container img { max-width: 100%; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .chart-title { font-size: 16px; font-weight: bold; margin-bottom: 10px; color: #333; }
        .nav { display: flex; gap: 10px; margin-bottom: 20px; }
        .nav-item { padding: 8px 16px; background-color: white; border-radius: 4px; cursor: pointer; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .nav-item:hover { background-color: #e6f7ff; }
        .session-list { margin-bottom: 20px; }
        .session-item { padding: 10px 15px; background-color: white; margin-bottom: 10px; border-radius: 4px; cursor: pointer; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .session-item:hover { background-color: #e6f7ff; }
        .session-item-header { display: flex; justify-content: space-between; align-items: center; }
        .session-item-title { font-weight: bold; color: #333; }
        .session-item-timestamp { font-size: 12px; color: #999; }
        .session-item-description { margin-top: 5px; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">LLM Token Processing Visualization</div>
            <div class="timestamp">Last updated: <span id="update-time">{{last_updated}}</span></div>
        </div>
        <div class="nav">
            <div class="nav-item" onclick="location.reload()">Refresh</div>
            <div class="nav-item" onclick="window.open('data/all_sessions.json', '_blank')">View Raw Data</div>
        </div>
        <div class="session-list">
            <h2>Processing Sessions</h2>
            <div id="session-list-content">{{session_list}}</div>
        </div>
        <div id="session-visualizations">{{session_visualizations}}</div>
    </div>
    <script>
        setInterval(() => { location.reload(); }, 2000);
    </script>
</body>
</html>
"""
        self.session_template = """<!DOCTYPE html>
<html>
<head>
    <title>Token Processing Session</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f2f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background-color: #001529; color: white; padding: 15px 20px; border-radius: 6px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .title { font-size: 24px; font-weight: bold; }
        .timestamp { font-size: 14px; color: #d9d9d9; }
        .session-container { background-color: white; border-radius: 6px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .session-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #f0f0f0; }
        .session-title { font-size: 18px; font-weight: bold; color: #333; }
        .session-meta { font-size: 14px; color: #666; }
        .token-text { font-family: 'Courier New', monospace; margin-bottom: 15px; padding: 15px; background-color: #f9f9f9; border-radius: 4px; line-height: 1.5; white-space: pre-wrap; }
        .token { display: inline-block; padding: 2px 4px; margin: 2px; border-radius: 3px; }
        .confidence-high { background-color: rgba(82, 196, 26, 0.2); }
        .confidence-medium { background-color: rgba(250, 173, 20, 0.2); }
        .confidence-low { background-color: rgba(245, 34, 45, 0.2); }
        .chart-container { margin-top: 20px; margin-bottom: 20px; }
        .chart-container img { max-width: 100%; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .chart-title { font-size: 16px; font-weight: bold; margin-bottom: 10px; color: #333; }
        .nav { display: flex; gap: 10px; margin-bottom: 20px; }
        .nav-item { padding: 8px 16px; background-color: white; border-radius: 4px; cursor: pointer; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .nav-item:hover { background-color: #e6f7ff; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">Token Processing Session</div>
            <div class="timestamp">Last updated: {{last_updated}}</div>
        </div>
        <div class="nav">
            <div class="nav-item" onclick="location.href='token_processing.html'">Back to All Sessions</div>
            <div class="nav-item" onclick="location.reload()">Refresh</div>
            <div class="nav-item" onclick="window.open('data/session_{{session_id}}.json', '_blank')">View Raw Data</div>
        </div>
        <div class="session-container">
            <div class="session-header">
                <div class="session-title">{{agent_id}} - {{status}}</div>
                <div class="session-meta">Started: {{start_time}} | Ended: {{end_time}}</div>
            </div>
            <div class="session-meta">
                <p>Description: {{description}}</p>
                <p>Tokens: {{token_count}} | Avg. Confidence: {{avg_confidence}}% | Avg. Processing Time: {{avg_processing_time}}ms</p>
            </div>
            <div class="token-text">{{token_html}}</div>
            {{confidence_chart}}
            {{processing_chart}}
            {{attention_charts}}
        </div>
    </div>
    <script>
        if ("{{status}}" === "active") { setInterval(() => { location.reload(); }, 2000); }
    </script>
</body>
</html>
"""

    def _create_main_html(self):
        """Create the main visualization HTML file."""
        output_path = os.path.join(self.output_dir, "token_processing.html")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html_content = self.main_template.replace("{{last_updated}}", current_time)
        html_content = html_content.replace("{{session_list}}", "<p>No active sessions</p>")
        html_content = html_content.replace("{{session_visualizations}}", "")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Token processing visualization HTML created at {output_path}")

    def start_processing_session(self, 
                                agent_id: str, 
                                description: Optional[str] = None) -> str:
        """
        Start a new token processing session.
        
        Args:
            agent_id: ID of the agent starting the session
            description: Optional description of the processing session
        
        Returns:
            session_id: ID of the created session
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "agent_id": agent_id,
            "description": description or f"Processing session by {agent_id}",
            "start_time": datetime.datetime.now().isoformat(),
            "end_time": None,
            "status": "active",
            "token_count": 0,
            "average_confidence": 0.0,
            "average_processing_time": 0.0
        }
        self.token_data[session_id] = []
        logger.info(f"Started token processing session {session_id} for agent {agent_id}")
        self.update_visualizations()
        return session_id

    def add_token(self, 
                 session_id: str, 
                 token: str, 
                 confidence: float,
                 processing_time_ms: float,
                 attention_weights: Optional[List[float]] = None,
                 metadata: Optional[Dict] = None):
        """
        Add a token to a processing session.
        """
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found. Creating new session.")
            session_id = self.start_processing_session("unknown")
        
        token_data = {
            "token": token,
            "confidence": confidence,
            "processing_time_ms": processing_time_ms,
            "timestamp": datetime.datetime.now().isoformat(),
            "index": len(self.token_data[session_id]),
            "attention_weights": attention_weights,
            "metadata": metadata or {}
        }
        self.token_data[session_id].append(token_data)
        
        session = self.sessions[session_id]
        session["token_count"] = len(self.token_data[session_id])
        confidence_sum = sum(t["confidence"] for t in self.token_data[session_id])
        session["average_confidence"] = confidence_sum / session["token_count"]
        processing_time_sum = sum(t["processing_time_ms"] for t in self.token_data[session_id])
        session["average_processing_time"] = processing_time_sum / session["token_count"]
        
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_visualizations()
            self.last_update = current_time

    def add_attention_pattern(self, 
                             session_id: str, 
                             attention_matrix: List[List[float]],
                             token_indices: Optional[List[int]] = None,
                             description: Optional[str] = None):
        """
        Add an attention pattern to a processing session.
        """
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found. Creating new session.")
            session_id = self.start_processing_session("unknown")
        
        tokens = self.token_data[session_id]
        token_texts = [tokens[i]["token"] for i in range(min(len(tokens), 20))]
        
        pattern_id = str(uuid.uuid4())
        attention_data = {
            "pattern_id": pattern_id,
            "session_id": session_id,
            "attention_matrix": attention_matrix,
            "token_texts": token_texts,
            "description": description or "Attention pattern",
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        attention_dir = os.path.join(self.output_dir, "attention")
        attention_path = os.path.join(attention_dir, f"attention_{pattern_id}.json")
        with open(attention_path, 'w', encoding='utf-8') as f:
            json.dump(attention_data, f, indent=2)
        
        self._visualize_attention_pattern(attention_data)
        
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_visualizations()
            self.last_update = current_time

    def end_processing_session(self, session_id: str):
        """
        End a token processing session.
        """
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found.")
            return
        
        self.sessions[session_id]["end_time"] = datetime.datetime.now().isoformat()
        self.sessions[session_id]["status"] = "completed"
        self.update_visualizations()
        logger.info(f"Ended token processing session {session_id}")

    def update_visualizations(self):
        """Update all token processing visualizations."""
        try:
            self._update_main_visualization()
            for session_id in self.sessions:
                self._update_session_visualization(session_id)
            
            if self.save_raw_data:
                data_path = os.path.join(self.output_dir, "data", "all_sessions.json")
                with open(data_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "sessions": self.sessions,
                        "token_data": self.token_data,
                        "last_updated": datetime.datetime.now().isoformat()
                    }, f, indent=2)
            
            logger.debug("Token processing visualizations updated")
        except Exception as e:
            logger.error(f"Error updating token processing visualizations: {e}")

    def _update_main_visualization(self):
        """Update the main visualization HTML file."""
        session_list_html = ""
        if not self.sessions:
            session_list_html = "<p>No active sessions</p>"
        else:
            for session_id, session in sorted(self.sessions.items(), key=lambda x: x[1]["start_time"], reverse=True):
                start_time = datetime.datetime.fromisoformat(session["start_time"]).strftime("%H:%M:%S")
                status_class = "active" if session["status"] == "active" else "completed"
                session_list_html += f"""
                <div class="session-item" onclick="location.href='session_{session_id}.html'">
                    <div class="session-item-header">
                        <div class="session-item-title">{session["agent_id"]}</div>
                        <div class="session-item-timestamp">{start_time} - {status_class}</div>
                    </div>
                    <div class="session-item-description">{session["description"]}</div>
                </div>
                """
        
        session_viz_html = ""
        # Determine which sessions to display on the main page
        active_sessions = [s_id for s_id, s in self.sessions.items() if s["status"] == "active"]
        
        if active_sessions:
            # If there are active sessions, show the 3 most recent ones
            recent_sessions_to_display = sorted(active_sessions, 
                                                key=lambda s_id: self.sessions[s_id]["start_time"], 
                                                reverse=True)[:3]
        else:
            # Otherwise, show the 3 most recent completed sessions
            completed_sessions = [s_id for s_id, s in self.sessions.items() if s["status"] == "completed"]
            recent_sessions_to_display = sorted(completed_sessions, 
                                                key=lambda s_id: self.sessions[s_id].get("end_time") or self.sessions[s_id]["start_time"], 
                                                reverse=True)[:3]

        for session_id in recent_sessions_to_display:
            session = self.sessions[session_id]
            tokens = self.token_data[session_id]
            recent_tokens = tokens[-10:]
            
            token_html = ""
            for token_data in recent_tokens:
                confidence = token_data["confidence"]
                confidence_class = "confidence-high" if confidence >= 80 else "confidence-medium" if confidence >= 50 else "confidence-low"
                token_html += f'<span class="token {confidence_class}" title="Confidence: {confidence:.1f}%, Time: {token_data["processing_time_ms"]:.1f}ms">{token_data["token"]}</span>'
            
            start_time_str = datetime.datetime.fromisoformat(session["start_time"]).strftime("%Y-%m-%d %H:%M:%S")
            end_time_str = "Active" if not session["end_time"] else datetime.datetime.fromisoformat(session["end_time"]).strftime("%Y-%m-%d %H:%M:%S")
            
            confidence_chart_html = ""
            chart_path = os.path.join("charts", f"confidence_{session_id}.png")
            if os.path.exists(os.path.join(self.output_dir, chart_path)):
                confidence_chart_html = f'<div class="chart-container"><div class="chart-title">Token Confidence</div><img src="{chart_path}?t={int(time.time())}" alt="Confidence chart"></div>'
            
            processing_chart_html = ""
            chart_path = os.path.join("charts", f"processing_{session_id}.png")
            if os.path.exists(os.path.join(self.output_dir, chart_path)):
                processing_chart_html = f'<div class="chart-container"><div class="chart-title">Processing Time (ms)</div><img src="{chart_path}?t={int(time.time())}" alt="Processing time chart"></div>'
            
            session_viz_html += f"""
            <div class="session-container">
                <div class="session-header">
                    <div class="session-title">{session["agent_id"]} - {session["status"].capitalize()}</div>
                    <div class="session-meta">Started: {start_time_str} | Ended: {end_time_str}</div>
                </div>
                <div class="session-meta">
                    <p>Description: {session["description"]}</p>
                    <p>Tokens: {session["token_count"]} | Avg. Confidence: {session["average_confidence"]:.1f}% | Avg. Processing Time: {session["average_processing_time"]:.1f}ms</p>
                </div>
                <div class="token-text">{token_html}</div>
                {confidence_chart_html}
                {processing_chart_html}
                <p><a href="session_{session_id}.html">View full session details</a></p>
            </div>
            """
        
        main_html_path = os.path.join(self.output_dir, "token_processing.html")
        html = self.main_template.replace("{{last_updated}}", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        html = html.replace("{{session_list}}", session_list_html)
        html = html.replace("{{session_visualizations}}", session_viz_html)
        with open(main_html_path, 'w', encoding='utf-8') as f:
            f.write(html)

    def _update_session_visualization(self, session_id: str):
        """
        Update visualization for a specific session.
        """
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        tokens = self.token_data[session_id]
        if not tokens:
            return
        
        self._create_confidence_chart(session_id, tokens)
        self._create_processing_time_chart(session_id, tokens)
        
        token_html = ""
        for token_data in tokens:
            confidence = token_data["confidence"]
            confidence_class = "confidence-high" if confidence >= 80 else "confidence-medium" if confidence >= 50 else "confidence-low"
            token_html += f'<span class="token {confidence_class}" title="Confidence: {confidence:.1f}%, Time: {token_data["processing_time_ms"]:.1f}ms">{token_data["token"]}</span>'
        
        start_time_str = datetime.datetime.fromisoformat(session["start_time"]).strftime("%Y-%m-%d %H:%M:%S")
        end_time_str = "Active" if not session["end_time"] else datetime.datetime.fromisoformat(session["end_time"]).strftime("%Y-%m-%d %H:%M:%S")
        
        confidence_chart_html = ""
        chart_path = os.path.join("charts", f"confidence_{session_id}.png")
        if os.path.exists(os.path.join(self.output_dir, chart_path)):
            confidence_chart_html = f'<div class="chart-container"><div class="chart-title">Token Confidence</div><img src="{chart_path}?t={int(time.time())}" alt="Confidence chart"></div>'
        
        processing_chart_html = ""
        chart_path = os.path.join("charts", f"processing_{session_id}.png")
        if os.path.exists(os.path.join(self.output_dir, chart_path)):
            processing_chart_html = f'<div class="chart-container"><div class="chart-title">Processing Time (ms)</div><img src="{chart_path}?t={int(time.time())}" alt="Processing time chart"></div>'
        
        attention_charts_html = ""
        attention_dir = os.path.join(self.output_dir, "attention")
        attention_files = [f for f in os.listdir(attention_dir) if f.startswith(f"attention_") and f.endswith(".png") and f"_{session_id}_" in f]
        attention_files.sort(key=lambda f: os.path.getctime(os.path.join(attention_dir, f)), reverse=True)
        for pattern_file in attention_files[:3]:
            chart_path = os.path.join("attention", pattern_file)
            attention_charts_html += f'<div class="chart-container"><div class="chart-title">Attention Pattern</div><img src="{chart_path}?t={int(time.time())}" alt="Attention pattern"></div>'
        
        html = self.session_template.replace("{{last_updated}}", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        html = html.replace("{{session_id}}", session_id)
        html = html.replace("{{agent_id}}", session["agent_id"])
        html = html.replace("{{status}}", session["status"])
        html = html.replace("{{start_time}}", start_time_str)
        html = html.replace("{{end_time}}", end_time_str)
        html = html.replace("{{description}}", session["description"])
        html = html.replace("{{token_count}}", str(session["token_count"]))
        html = html.replace("{{avg_confidence}}", f"{session['average_confidence']:.1f}")
        html = html.replace("{{avg_processing_time}}", f"{session['average_processing_time']:.1f}")
        html = html.replace("{{token_html}}", token_html)
        html = html.replace("{{confidence_chart}}", confidence_chart_html)
        html = html.replace("{{processing_chart}}", processing_chart_html)
        html = html.replace("{{attention_charts}}", attention_charts_html)
        
        output_path = os.path.join(self.output_dir, f"session_{session_id}.html")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        if self.save_raw_data:
            data_path = os.path.join(self.output_dir, "data", f"session_{session_id}.json")
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump({"session": session, "tokens": tokens, "last_updated": datetime.datetime.now().isoformat()}, f, indent=2)

    def _create_confidence_chart(self, session_id: str, tokens: List[Dict]):
        """
        Create a confidence chart for a session.
        """
        try:
            plt.figure(figsize=(12, 6))
            indices = list(range(len(tokens)))
            confidences = [t["confidence"] for t in tokens]
            bars = plt.bar(indices, confidences, width=0.8, alpha=0.7)
            for i, bar in enumerate(bars):
                if confidences[i] >= 80: bar.set_color('#52c41a')
                elif confidences[i] >= 50: bar.set_color('#faad14')
                else: bar.set_color('#f5222d')
            
            max_visible_tokens = min(len(tokens), self.max_tokens_per_chart)
            if len(tokens) > max_visible_tokens:
                start_idx = len(tokens) - max_visible_tokens
                indices = indices[-max_visible_tokens:]
                confidences = confidences[-max_visible_tokens:]
                tokens = tokens[-max_visible_tokens:]
                plt.xlim(start_idx - 0.5, len(tokens) + start_idx - 0.5)
            
            for i, token_data in enumerate(tokens):
                token_text = token_data["token"]
                if len(token_text) > 10: token_text = token_text[:7] + "..."
                plt.text(indices[i], confidences[i] + 2, token_text, ha='center', va='bottom', rotation=45, fontsize=8, color='#333333')
            
            plt.title("Token Confidence Scores", fontsize=16)
            plt.ylabel("Confidence (%)", fontsize=12)
            plt.xlabel("Token Index", fontsize=12)
            plt.ylim(0, 105)
            plt.grid(axis='y', linestyle='--', alpha=0.3)
            plt.tight_layout()
            
            chart_path = os.path.join(self.output_dir, "charts", f"confidence_{session_id}.png")
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()
        except Exception as e:
            logger.error(f"Error creating confidence chart for session {session_id}: {e}")

    def _create_processing_time_chart(self, session_id: str, tokens: List[Dict]):
        """
        Create a processing time chart for a session.
        """
        try:
            plt.figure(figsize=(12, 6))
            indices = list(range(len(tokens)))
            processing_times = [t["processing_time_ms"] for t in tokens]
            plt.plot(indices, processing_times, marker='o', linestyle='-', color='#1890ff', markersize=4, alpha=0.7)
            
            window_size = min(5, len(processing_times))
            if window_size > 1:
                moving_avg = np.convolve(processing_times, np.ones(window_size)/window_size, mode='valid')
                ma_indices = indices[window_size-1:]
                plt.plot(ma_indices, moving_avg, linestyle='-', color='#722ed1', linewidth=2, label=f'{window_size}-token Moving Average')
            
            max_visible_tokens = min(len(tokens), self.max_tokens_per_chart)
            if len(tokens) > max_visible_tokens:
                start_idx = len(tokens) - max_visible_tokens
                plt.xlim(start_idx - 0.5, len(tokens) + start_idx - 0.5)
            
            plt.title("Token Processing Time", fontsize=16)
            plt.ylabel("Processing Time (ms)", fontsize=12)
            plt.xlabel("Token Index", fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.3)
            if window_size > 1: plt.legend()
            plt.tight_layout()
            
            chart_path = os.path.join(self.output_dir, "charts", f"processing_{session_id}.png")
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()
        except Exception as e:
            logger.error(f"Error creating processing time chart for session {session_id}: {e}")

    def _visualize_attention_pattern(self, attention_data: Dict):
        """
        Visualize attention pattern.
        """
        try:
            pattern_id = attention_data["pattern_id"]
            session_id = attention_data["session_id"]
            attention_matrix = attention_data["attention_matrix"]
            token_texts = attention_data["token_texts"]
            
            if not attention_matrix or not isinstance(attention_matrix, list):
                logger.warning(f"Invalid attention matrix for pattern {pattern_id}")
                return
            
            plt.figure(figsize=(12, 10))
            attention_array = np.array(attention_matrix)
            
            max_tokens = min(20, len(token_texts))
            if len(token_texts) > max_tokens:
                token_texts = token_texts[-max_tokens:]
                attention_array = attention_array[-max_tokens:, -max_tokens:]
            
            display_tokens = [t[:7] + "..." if len(t) > 10 else t for t in token_texts]
            
            colors = [(0.0, 0.0, 0.8), (1.0, 1.0, 1.0), (0.8, 0.0, 0.0)]
            cmap = LinearSegmentedColormap.from_list('attention_cmap', colors, N=100)
            
            plt.imshow(attention_array, cmap=cmap, aspect='auto', vmin=0, vmax=1)
            cbar = plt.colorbar()
            cbar.set_label('Attention Weight', rotation=270, labelpad=15)
            
            plt.xticks(range(len(display_tokens)), display_tokens, rotation=45, ha='right')
            plt.yticks(range(len(display_tokens)), display_tokens)
            
            plt.title(f"Attention Pattern - {attention_data.get('description', 'Unnamed')}", fontsize=16)
            plt.xlabel("Token (Target)", fontsize=12)
            plt.ylabel("Token (Source)", fontsize=12)
            plt.tight_layout()
            
            chart_path = os.path.join(self.output_dir, "attention", f"attention_{pattern_id}_{session_id}.png")
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()
        except Exception as e:
            logger.error(f"Error creating attention visualization: {e}")
