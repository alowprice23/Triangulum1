import math

def score(bug):
    """Calculate priority score based on severity and age.
    
    Formula: prio = 0.7 * (s/5) + 0.3 * min(1, age/50)
    Where:
    - s is severity (1-5)
    - age is ticks since arrival
    
    This ensures after 50 ticks, even low-severity bugs get processed.
    """
    severity = getattr(bug, 'severity', 3)  # Default to medium severity
    age = getattr(bug, 'age_ticks', 0)      # Ticks since arrival
    
    severity_component = 0.7 * (severity / 5)
    age_component = 0.3 * min(1, age / 50)
    
    return severity_component + age_component

def prioritize_bugs(bugs):
    """Sort bugs by priority score (highest first)."""
    return sorted(bugs, key=score, reverse=True)
