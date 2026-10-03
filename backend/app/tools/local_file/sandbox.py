import os
import logging
from pathlib import Path
from typing import List
from app.core.config import settings

logger = logging.getLogger(__name__)

class SecurityException(Exception):
    """Exception raised for security violations like path traversal."""
    pass

class FileSandbox:
    """Provides sandboxed file system access checking allowed roots."""
    
    def __init__(self):
        self.allowed_roots: List[Path] = []
        self._load_allowed_roots()
        
    def _load_allowed_roots(self) -> None:
        """Loads and resolves allowed root directories from configuration."""
        roots_str = settings.FILE_AGENT_ALLOWED_ROOTS
        if not roots_str:
            logger.warning("FILE_AGENT_ALLOWED_ROOTS is empty. File Agent will not be able to access any files.")
            return
            
        for root in roots_str.split(","):
            root = root.strip()
            if not root:
                continue
            
            try:
                # Resolve to absolute path, resolving symlinks to prevent escapes
                resolved_path = Path(root).resolve()
                if resolved_path.exists() and resolved_path.is_dir():
                    self.allowed_roots.append(resolved_path)
                else:
                    logger.warning(f"Configured allowed root does not exist or is not a directory: {root}")
            except Exception as e:
                logger.error(f"Failed to resolve allowed root {root}: {e}")
                
    def is_path_allowed(self, target_path: str | Path) -> bool:
        """
        Checks if a target path is allowed within the configured roots.
        Prevents path traversal, absolute path escapes, and symlink escapes.
        """
        if not self.allowed_roots:
            return False
            
        try:
            # Resolve the target path fully
            # resolve() handles converting to absolute and resolving symlinks.
            # If the file doesn't exist yet, resolve() might not resolve symlinks fully on some OS,
            # but strict=True will raise an error if it doesn't exist.
            # We want to allow reading, so it should exist.
            resolved_target = Path(target_path).resolve(strict=False)
            
            # Check if it falls under any allowed root
            for root in self.allowed_roots:
                try:
                    # relative_to throws ValueError if not a subpath
                    resolved_target.relative_to(root)
                    
                    # Also check for obvious secrets
                    name_lower = resolved_target.name.lower()
                    if name_lower in ['.env', 'credentials.json', 'token.json', 'client_secret.json']:
                        logger.warning(f"Blocked access to potential secrets file: {resolved_target}")
                        return False
                        
                    return True
                except ValueError:
                    continue
                    
            return False
        except Exception as e:
            logger.error(f"Error checking path {target_path}: {e}")
            return False

    def get_safe_path(self, target_path: str | Path) -> Path:
        """
        Returns the resolved safe Path if allowed, else raises SecurityException.
        """
        if not self.is_path_allowed(target_path):
            raise SecurityException(f"Access to path '{target_path}' is denied by the sandbox policy.")
        return Path(target_path).resolve()

sandbox = FileSandbox()
