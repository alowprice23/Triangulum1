"""
Entropy explainer for Triangulum system.

Translates abstract entropy values into human-readable explanations.
"""

from typing import Dict, Any, Optional
import math


def humanise(bits: float) -> str:
    """
    Translate entropy bits into human-readable explanations.
    
    Args:
        bits: Entropy value in bits
        
    Returns:
        str: Human-readable explanation of the entropy value
    """
    if bits <= 0.5:
        return "One hypothesis left → expect PASS next cycle."
    if bits <= 1.5:
        return "A couple hypotheses remain; likely to finish soon."
    if bits <= 3:
        return "Still broad; at least 3 more cycles expected."
    return "Large hypothesis space; consider refining scope."


def get_entropy_status(current: float, threshold: float) -> Dict[str, Any]:
    """
    Get a complete entropy status report.
    
    Args:
        current: Current entropy in bits
        threshold: Entropy threshold for resolution
        
    Returns:
        Dict with entropy status information
    """
    remaining = max(0, threshold - current)
    percentage = min(100, (current / threshold) * 100) if threshold > 0 else 0
    
    status = {
        "current_bits": current,
        "threshold_bits": threshold,
        "remaining_bits": remaining,
        "percentage_complete": percentage,
        "explanation": humanise(remaining),
    }
    
    # Add expected cycles remaining
    if remaining <= 0:
        status["cycles_remaining"] = 0
        status["status"] = "COMPLETE"
    else:
        # Assuming 1 bit per verification cycle
        status["cycles_remaining"] = math.ceil(remaining)
        if percentage >= 75:
            status["status"] = "NEAR_COMPLETE"
        elif percentage >= 50:
            status["status"] = "PROGRESSING"
        else:
            status["status"] = "EARLY_STAGE"
    
    return status


def explain_verification_result(result: bool, attempt: int, 
                               current_bits: float) -> str:
    """
    Explain a verification result in terms of entropy.
    
    Args:
        result: True if verification succeeded, False if failed
        attempt: Which attempt this is (0=first, 1=second)
        current_bits: Current entropy in bits
        
    Returns:
        str: Human-readable explanation of the verification result
    """
    if attempt == 0 and not result:
        return (
            f"First verification failed as expected. This gives us 1 bit of "
            f"information, bringing our entropy to {current_bits + 1:.2f} bits. "
            f"The system is working correctly."
        )
    elif attempt == 0 and result:
        return (
            f"First verification unexpectedly passed! This is unusual but good. "
            f"We've solved the bug without needing a second attempt."
        )
    elif attempt == 1 and result:
        return (
            f"Second verification passed as expected. The bug is now fixed, "
            f"and we've accumulated {current_bits:.2f} bits of entropy."
        )
    else:  # attempt == 1 and not result
        return (
            f"Second verification failed unexpectedly. This is concerning "
            f"and may indicate we've exceeded our entropy budget or there's "
            f"a deeper issue with the bug. Consider escalating this bug."
        )


def format_entropy_chart(current: float, threshold: float, width: int = 50) -> str:
    """
    Create a text-based chart showing entropy progress.
    
    Args:
        current: Current entropy in bits
        threshold: Entropy threshold for resolution
        width: Width of the chart in characters
        
    Returns:
        str: ASCII chart showing entropy progress
    """
    percentage = min(1.0, current / threshold) if threshold > 0 else 0
    filled_width = int(width * percentage)
    empty_width = width - filled_width
    
    bar = '[' + '=' * filled_width + ' ' * empty_width + ']'
    percent_str = f"{percentage * 100:.1f}%"
    
    chart = f"{bar} {percent_str}\n"
    chart += f"Entropy: {current:.2f}/{threshold:.2f} bits"
    
    return chart
