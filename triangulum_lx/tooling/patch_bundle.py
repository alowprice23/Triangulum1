"""
Patch bundle management for Triangulum.

Serializes patches into a verifiable and revertible format.
"""

import os
import json
import hashlib
import tarfile
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
import logging

# Setup logging
logger = logging.getLogger("triangulum.patch_bundle")


class PatchBundle:
    """
    Represents a bundle of patch information that can be applied, verified and reverted.
    
    A patch bundle includes:
    - The patch diff
    - A manifest with metadata
    - A SHA-256 signature for integrity
    """
    
    def __init__(self, 
                bug_id: str, 
                patch_diff: str, 
                repo_root: Union[str, Path] = ".",
                label: str = "patch"):
        """
        Initialize a new patch bundle.
        
        Args:
            bug_id: Unique identifier for the bug
            patch_diff: The patch diff content
            repo_root: Root directory of the repository
            label: Label for the bundle (e.g., "cycle_1", "final")
        """
        self.bug_id = bug_id
        self.patch_diff = patch_diff
        self.repo_root = Path(repo_root)
        self.label = label
        self.created_at = datetime.now().isoformat()
        self.bundle_path = None
        
        # Generate SHA-256 hash of the patch
        self.patch_hash = hashlib.sha256(patch_diff.encode()).hexdigest()
    
    def get_manifest(self) -> Dict[str, Any]:
        """
        Generate the manifest for this patch bundle.
        
        Returns:
            Dict with patch bundle metadata
        """
        return {
            "bug_id": self.bug_id,
            "label": self.label,
            "created_at": self.created_at,
            "patch_hash": self.patch_hash,
            "file_count": self._count_affected_files(),
            "version": "1.0.0"
        }
    
    def _count_affected_files(self) -> int:
        """Count how many files are affected by this patch."""
        file_count = 0
        for line in self.patch_diff.split("\n"):
            if line.startswith("+++ ") or line.startswith("--- "):
                if not line.endswith("/dev/null"):
                    file_count += 1
        return file_count // 2  # Each file appears twice (--- and +++)
    
    def create(self) -> Path:
        """
        Create the patch bundle file.
        
        Returns:
            Path to the created bundle file
        """
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)
            
            # Write patch diff to file
            patch_path = temp_path / "patch.diff"
            with open(patch_path, 'w') as f:
                f.write(self.patch_diff)
            
            # Write manifest to file
            manifest_path = temp_path / "manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(self.get_manifest(), f, indent=2)
            
            # Create bundle filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bundle_name = f"patch_{self.bug_id}_{self.label}_{timestamp}.tar.gz"
            bundle_path = Path(f"patches/{bundle_name}")
            bundle_path.parent.mkdir(exist_ok=True, parents=True)
            
            # Create tar archive
            with tarfile.open(bundle_path, "w:gz") as tar:
                tar.add(patch_path, arcname=patch_path.name)
                tar.add(manifest_path, arcname=manifest_path.name)
            
            self.bundle_path = bundle_path
            logger.info(f"Created patch bundle: {bundle_path}")
            
            return bundle_path
    
    @classmethod
    def from_bundle(cls, bundle_path: Union[str, Path]) -> 'PatchBundle':
        """
        Load a patch bundle from file.
        
        Args:
            bundle_path: Path to the bundle file
            
        Returns:
            PatchBundle instance
        """
        bundle_path = Path(bundle_path)
        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle file not found: {bundle_path}")
        
        # Extract files from tar
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)
            
            with tarfile.open(bundle_path, "r:gz") as tar:
                tar.extractall(path=temp_path)
            
            # Read manifest
            manifest_path = temp_path / "manifest.json"
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Read patch diff
            patch_path = temp_path / "patch.diff"
            with open(patch_path, 'r') as f:
                patch_diff = f.read()
            
            # Create bundle object
            bundle = cls(
                bug_id=manifest["bug_id"],
                patch_diff=patch_diff,
                label=manifest["label"]
            )
            bundle.created_at = manifest["created_at"]
            bundle.patch_hash = manifest["patch_hash"]
            bundle.bundle_path = bundle_path
            
            return bundle
    
    def verify_integrity(self) -> bool:
        """
        Verify the integrity of the patch bundle.
        
        Returns:
            bool: True if the patch hash matches
        """
        computed_hash = hashlib.sha256(self.patch_diff.encode()).hexdigest()
        return computed_hash == self.patch_hash
    
    def apply(self) -> bool:
        """
        Apply the patch to the repository.
        
        Returns:
            bool: True if the patch was applied successfully
        """
        try:
            # Use git apply to apply the patch
            result = subprocess.run(
                ["git", "apply"], 
                input=self.patch_diff,
                text=True,
                capture_output=True,
                cwd=self.repo_root
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to apply patch: {result.stderr}")
                return False
                
            logger.info(f"Successfully applied patch for bug {self.bug_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying patch: {e}")
            return False
    
    def revert(self) -> bool:
        """
        Revert the patch from the repository.
        
        Returns:
            bool: True if the patch was reverted successfully
        """
        try:
            # Use git apply -R to revert the patch
            result = subprocess.run(
                ["git", "apply", "-R"], 
                input=self.patch_diff,
                text=True,
                capture_output=True,
                cwd=self.repo_root
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to revert patch: {result.stderr}")
                return False
                
            logger.info(f"Successfully reverted patch for bug {self.bug_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error reverting patch: {e}")
            return False


def create_bundle(patch_diff: str, 
                 bug_id: str, 
                 repo_root: str = ".", 
                 label: str = "cycle_final") -> Path:
    """
    Create a new patch bundle.
    
    Args:
        patch_diff: The patch diff content
        bug_id: Unique identifier for the bug
        repo_root: Root directory of the repository
        label: Label for the bundle
        
    Returns:
        Path to the created bundle file
    """
    bundle = PatchBundle(bug_id, patch_diff, repo_root, label)
    return bundle.create()


def apply_bundle(bundle_path: Union[str, Path]) -> Tuple[bool, Optional[PatchBundle]]:
    """
    Apply a patch bundle.
    
    Args:
        bundle_path: Path to the bundle file
        
    Returns:
        Tuple of (success, bundle)
    """
    try:
        bundle = PatchBundle.from_bundle(bundle_path)
        
        # Verify integrity
        if not bundle.verify_integrity():
            logger.error("Bundle integrity check failed")
            return False, None
            
        # Apply patch
        if bundle.apply():
            return True, bundle
        else:
            return False, bundle
            
    except Exception as e:
        logger.error(f"Error applying bundle: {e}")
        return False, None


def revert_bundle(bundle_path: Union[str, Path]) -> bool:
    """
    Revert a patch bundle.
    
    Args:
        bundle_path: Path to the bundle file
        
    Returns:
        bool: True if reversion was successful
    """
    try:
        bundle = PatchBundle.from_bundle(bundle_path)
        return bundle.revert()
            
    except Exception as e:
        logger.error(f"Error reverting bundle: {e}")
        return False
