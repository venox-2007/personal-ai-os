import os
import logging
from pathlib import Path
from typing import List
from app.core.config import settings

logger = logging.getLogger(__name__)

class SecurityException(Exception):
    pass

class CodeSandbox:
    """Provides sandboxed file system access checking allowed roots for coding agent."""
    
    def __init__(self):
        self.allowed_roots: List[Path] = []
        self._load_allowed_roots()
        
    def _load_allowed_roots(self) -> None:
        roots_str = settings.CODING_AGENT_ALLOWED_ROOTS
        if not roots_str:
            logger.warning("CODING_AGENT_ALLOWED_ROOTS is empty. Coding Agent will not be able to access any local repositories.")
            return
            
        for root in roots_str.split(","):
            root = root.strip()
            if not root:
                continue
            
            try:
                resolved_path = Path(root).resolve()
                if resolved_path.exists() and resolved_path.is_dir():
                    self.allowed_roots.append(resolved_path)
            except Exception as e:
                logger.error(f"Failed to resolve coding allowed root {root}: {e}")
                
    def is_path_allowed(self, target_path: str | Path) -> bool:
        if not self.allowed_roots:
            return False
            
        try:
            resolved_target = Path(target_path).resolve(strict=False)
            
            for root in self.allowed_roots:
                try:
                    resolved_target.relative_to(root)
                    
                    name_lower = resolved_target.name.lower()
                    if name_lower in ['.env', 'credentials.json', 'token.json', 'client_secret.json', 'id_rsa'] or name_lower.endswith('.pem'):
                        logger.warning(f"Blocked access to potential secrets file: {resolved_target}")
                        return False
                        
                    return True
                except ValueError:
                    continue
                    
            return False
        except Exception as e:
            return False

    def get_safe_path(self, target_path: str | Path) -> Path:
        if not self.is_path_allowed(target_path):
            raise SecurityException(f"Access to path '{target_path}' is denied by the coding sandbox policy.")
        return Path(target_path).resolve()

sandbox = CodeSandbox()
