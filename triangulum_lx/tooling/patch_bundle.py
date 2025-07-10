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

from triangulum_lx.tooling.fs_ops import atomic_write, atomic_rename
from triangulum_lx.core.fs_state import FileSystemStateCache

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
                label: str = "patch",
                fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize a new patch bundle.
        
        Args:
            bug_id: Unique identifier for the bug
            patch_diff: The patch diff content
            repo_root: Root directory of the repository
            label: Label for the bundle (e.g., "cycle_1", "final")
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.bug_id = bug_id
        self.patch_diff = patch_diff
        self.repo_root = Path(repo_root)
        self.label = label
        self.created_at = datetime.now().isoformat()
        self.bundle_path = None
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
        
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
            atomic_write(patch_path, self.patch_diff.encode('utf-8'))
            # No fs_cache invalidation for temp files needed here.
            
            # Write manifest to file
            manifest_path = temp_path / "manifest.json"
            manifest_content = json.dumps(self.get_manifest(), indent=2)
            atomic_write(manifest_path, manifest_content.encode('utf-8'))
            
            # Create bundle filename (final path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bundle_name = f"patch_{self.bug_id}_{self.label}_{timestamp}.tar.gz"
            final_bundle_path = self.repo_root / "patches" / bundle_name # Ensure it's within repo_root if "patches" is relative
            final_bundle_path.parent.mkdir(exist_ok=True, parents=True) # Ensure target dir exists

            # Create tar archive in a temporary location first
            temp_tar_path = temp_path / bundle_name
            with tarfile.open(temp_tar_path, "w:gz") as tar:
                tar.add(patch_path, arcname=patch_path.name)
                tar.add(manifest_path, arcname=manifest_path.name)
            
            # Atomically move the temporary tarball to its final destination
            atomic_rename(str(temp_tar_path), str(final_bundle_path))
            self.fs_cache.invalidate(str(final_bundle_path))
            
            self.bundle_path = final_bundle_path
            logger.info(f"Created patch bundle: {final_bundle_path}")

            return final_bundle_path
    
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
            self._invalidate_cache_for_patch_files()
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
            self._invalidate_cache_for_patch_files()
            return True
            
        except Exception as e:
            logger.error(f"Error reverting patch: {e}")
            return False

    def _invalidate_cache_for_patch_files(self):
        """Invalidates cache for files mentioned in the patch diff."""
        # Basic diff parsing to find affected files
        # This is a simplified parser. A more robust one would handle various diff formats.
        affected_files_relative = set()
        # current_file = None # Not needed with this simplified parsing
        for line in self.patch_diff.splitlines():
            if line.startswith('--- a/'):
                path_str = line[len('--- a/'):].strip()
                if path_str != 'dev/null': # Corrected: no leading slash
                    affected_files_relative.add(path_str)
            elif line.startswith('+++ b/'):
                path_str = line[len('+++ b/'):].strip()
                if path_str != 'dev/null': # Corrected: no leading slash
                    affected_files_relative.add(path_str)

        for rel_path in affected_files_relative:
            # Ensure rel_path is not empty and is a valid relative path component
            if not rel_path or rel_path.startswith('/'):
                logger.warning(f"Skipping invalid relative path from diff: '{rel_path}'")
                continue
            try:
                abs_path = self.repo_root.joinpath(rel_path).resolve()
                 # Check if the resolved path is within the intended repo_root to avoid .. issues
                if self.repo_root.resolve() in abs_path.parents or self.repo_root.resolve() == abs_path:
                    logger.debug(f"Invalidating cache for patched file: {abs_path}")
                    self.fs_cache.invalidate(str(abs_path))
                else:
                    logger.warning(f"Skipping cache invalidation for path outside repo_root: {abs_path} (derived from {rel_path})")
            except Exception as e:
                logger.error(f"Error resolving or invalidating path {rel_path} (abs: {abs_path if 'abs_path' in locals() else 'unresolved'}): {e}")


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
