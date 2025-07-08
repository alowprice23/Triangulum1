"""
Linear Temporal Logic (LTL) specifications for Triangulum system properties.
These properties are used for formal verification of the system's behavior.

We use the following temporal operators:
- G: Globally (always)
- F: Finally (eventually)
- X: Next
- U: Until
"""

from enum import Enum
import re
from typing import List, Dict, Any, Callable

from ..core.state import Phase


class LTLOperator(Enum):
    """LTL operators used in formulas."""
    GLOBALLY = "G"     # Always
    FINALLY = "F"      # Eventually
    NEXT = "X"         # Next
    UNTIL = "U"        # Until
    AND = "&&"         # Logical AND
    OR = "||"          # Logical OR
    IMPLIES = "->"     # Implication
    NOT = "!"          # Negation


class LTLFormula:
    """
    Represents an LTL formula for system verification.
    
    This class allows for construction and evaluation of LTL formulas
    against system execution traces.
    """
    
    def __init__(self, formula_str: str, description: str = ""):
        self.formula_str = formula_str
        self.description = description
        self._validate_formula()
    
    def _validate_formula(self) -> None:
        """Validate the formula string for correct syntax."""
        # Ensure all operators are valid
        pattern = r'[GFX]|&&|\|\||\->|\!'
        operators = re.findall(pattern, self.formula_str)
        for op in operators:
            try:
                # Try to convert to enum
                if op in ["G", "F", "X"]:
                    LTLOperator(op)
                elif op == "&&":
                    LTLOperator.AND
                elif op == "||":
                    LTLOperator.OR
                elif op == "->":
                    LTLOperator.IMPLIES
                elif op == "!":
                    LTLOperator.NOT
            except ValueError:
                raise ValueError(f"Invalid operator in LTL formula: {op}")
    
    def evaluate(self, trace: List[Dict[str, Any]], 
                state_predicates: Dict[str, Callable]) -> bool:
        """
        Evaluate the formula against an execution trace.
        
        Args:
            trace: List of system states (dictionaries)
            state_predicates: Dictionary mapping predicate names to functions
                that evaluate a state and return True/False
        
        Returns:
            bool: True if the formula is satisfied by the trace
        """
        # This is a simplified implementation
        # In a real system, this would use a proper LTL model checker
        
        # For demonstration, we'll implement a basic evaluation for some common patterns
        
        # Safety property example: G(condition)
        if self.formula_str.startswith("G(") and self.formula_str.endswith(")"):
            # Extract the condition
            condition = self.formula_str[2:-1]
            
            # Check if condition holds in all states
            for state in trace:
                if not self._evaluate_condition(condition, state, state_predicates):
                    return False
            return True
        
        # Liveness property example: F(condition)
        elif self.formula_str.startswith("F(") and self.formula_str.endswith(")"):
            # Extract the condition
            condition = self.formula_str[2:-1]
            
            # Check if condition holds in at least one state
            for state in trace:
                if self._evaluate_condition(condition, state, state_predicates):
                    return True
            return False
        
        # Response property example: G(trigger -> F(response))
        elif "G(" in self.formula_str and "->" in self.formula_str and "F(" in self.formula_str:
            # This is a simplified check for response properties
            # In a real implementation, you would use a proper LTL model checker
            
            # For each state where trigger is true,
            # check if response becomes true in some future state
            for i, state in enumerate(trace):
                # Extract trigger and response conditions
                match = re.search(r'G\(\s*([^-]+)\s*->\s*F\(\s*([^)]+)\s*\)\s*\)', self.formula_str)
                if not match:
                    return False
                
                trigger, response = match.groups()
                
                if self._evaluate_condition(trigger, state, state_predicates):
                    # Trigger is true, now check if response becomes true in future
                    response_found = False
                    for future_state in trace[i:]:
                        if self._evaluate_condition(response, future_state, state_predicates):
                            response_found = True
                            break
                    
                    if not response_found:
                        return False
            
            return True
        
        # Default case - not implemented
        return False
    
    def _evaluate_condition(self, condition: str, state: Dict[str, Any], 
                           predicates: Dict[str, Callable]) -> bool:
        """
        Evaluate a simple condition against a system state.
        
        Args:
            condition: String condition (a predicate name)
            state: System state dictionary
            predicates: Dictionary mapping predicate names to functions
        
        Returns:
            bool: Result of evaluating the condition
        """
        # Handle basic boolean operators
        if "&&" in condition:
            parts = condition.split("&&")
            return all(self._evaluate_condition(part.strip(), state, predicates) 
                      for part in parts)
        
        if "||" in condition:
            parts = condition.split("||")
            return any(self._evaluate_condition(part.strip(), state, predicates) 
                      for part in parts)
        
        if condition.startswith("!"):
            return not self._evaluate_condition(condition[1:].strip(), state, predicates)
        
        # Look for predicate in the dictionary
        predicate_name = condition.strip()
        if predicate_name in predicates:
            return predicates[predicate_name](state)
        
        # Fallback - try to interpret as a direct reference to state
        try:
            # Split by dots to handle nested access
            parts = predicate_name.split('.')
            value = state
            for part in parts:
                value = value[part]
            
            return bool(value)
        except (KeyError, TypeError):
            return False


# Define common system predicates
def bug_in_phase(state, phase: Phase):
    """Check if a bug is in the given phase."""
    return state.get('phase') == phase

def agent_free_count(state, min_count: int):
    """Check if there are at least min_count free agents."""
    return state.get('free_agents', 0) >= min_count

def entropy_below_threshold(state, threshold: float):
    """Check if entropy is below threshold."""
    return state.get('entropy_bits', float('inf')) < threshold


# Define core Triangulum LTL properties
triangulum_properties = [
    LTLFormula(
        "G(bug_wait && agents_available -> F(bug_repro))",
        "Fairness: If a bug is waiting and agents are available, it will eventually move to REPRO phase"
    ),
    
    LTLFormula(
        "G(bug_repro -> F(bug_patch))",
        "Progress: A bug in REPRO will eventually move to PATCH phase"
    ),
    
    LTLFormula(
        "G(bug_verify && second_attempt -> F(bug_done))",
        "Deterministic completion: A bug in VERIFY on second attempt will eventually be DONE"
    ),
    
    LTLFormula(
        "G(bug_done -> G(bug_done))",
        "Stability: Once a bug is DONE, it stays DONE"
    ),
    
    LTLFormula(
        "G(entropy_exceeded -> F(all_bugs_done || some_bug_escalated))",
        "Entropy bound: If entropy budget is exceeded, either all bugs will be fixed or some will be escalated"
    )
]


# Predicate mapping for evaluating properties
predicate_mapping = {
    "bug_wait": lambda state: bug_in_phase(state, Phase.WAIT),
    "bug_repro": lambda state: bug_in_phase(state, Phase.REPRO),
    "bug_patch": lambda state: bug_in_phase(state, Phase.PATCH),
    "bug_verify": lambda state: bug_in_phase(state, Phase.VERIFY),
    "bug_done": lambda state: bug_in_phase(state, Phase.DONE),
    "bug_escalated": lambda state: bug_in_phase(state, Phase.ESCALATE),
    "agents_available": lambda state: agent_free_count(state, 3),
    "second_attempt": lambda state: state.get('attempts', 0) == 1,
    "entropy_exceeded": lambda state: state.get('entropy_bits', 0) >= state.get('entropy_threshold', 3.32),
    "all_bugs_done": lambda state: all(b.get('phase') == Phase.DONE for b in state.get('bugs', [])),
    "some_bug_escalated": lambda state: any(b.get('phase') == Phase.ESCALATE for b in state.get('bugs', []))
}
