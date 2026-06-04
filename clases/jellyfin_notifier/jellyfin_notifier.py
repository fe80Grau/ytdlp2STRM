"""
Jellyfin/Emby Library Scanner Notifier
Notifies Jellyfin or Emby to scan a specific library when new content is added
"""

import requests
from clases.log import log as l

class JellyfinNotifier:
    def __init__(self, config):
        """
        Initialize the notifier with configuration
        
        Args:
            config (dict): Configuration dictionary containing:
                - jellyfin_integration (str): "True" or "False" to enable/disable integration
                - jellyfin_base_url (str): Base URL of Jellyfin/Emby server
                - jellyfin_api_key (str): API key for authentication
                - jellyfin_library_name (str): Name of the library to scan
        """
        # Convert string "True"/"False" to boolean
        integration_value = config.get('jellyfin_integration', 'False')
        self.enabled = str(integration_value).lower() == 'true'
        
        self.base_url = config.get('jellyfin_base_url', '').rstrip('/')
        self.api_key = config.get('jellyfin_api_key', '')
        self.library_name = config.get('jellyfin_library_name', '')
        self.server_type = 'jellyfin'  # Default to jellyfin, can be 'emby'
        
        # Validate configuration
        if self.enabled:
            if not self.base_url:
                l.log("jellyfin_notifier", "Warning: jellyfin_integration enabled but jellyfin_base_url is empty")
                self.enabled = False
            elif not self.api_key:
                l.log("jellyfin_notifier", "Warning: jellyfin_integration enabled but jellyfin_api_key is empty")
                self.enabled = False
            elif not self.library_name:
                l.log("jellyfin_notifier", "Warning: jellyfin_integration enabled but jellyfin_library_name is empty")
                self.enabled = False
            else:
                # Detect if it's Emby based on URL
                if 'emby' in self.base_url.lower():
                    self.server_type = 'emby'
                l.log("jellyfin_notifier", f"{self.server_type.capitalize()} integration enabled for library: {self.library_name}")
    
    def get_library_id(self):
        """
        Get the Emby/Jellyfin ItemId for the configured library name.

        Returns:
            str or None: The library's ItemId (e.g. "12345"), or None if the
                library is not configured / has no ItemId. We deliberately
                never return the library name as a fallback because callers
                use the result to build API URLs.
        """
        if not self.enabled:
            return None

        try:
            # Endpoint is the same for both Jellyfin and Emby
            url = f"{self.base_url}/Library/VirtualFolders"
            headers = {
                'X-Emby-Token': self.api_key
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            libraries = response.json()

            for library in libraries:
                if library.get('Name', '').lower() == self.library_name.lower():
                    item_id = library.get('ItemId')
                    if item_id:
                        return item_id
                    l.log(
                        "jellyfin_notifier",
                        f"Library '{self.library_name}' has no ItemId, cannot refresh",
                    )
                    return None

            l.log("jellyfin_notifier", f"Library '{self.library_name}' not found in Emby/Jellyfin")
            return None

        except requests.exceptions.RequestException as e:
            l.log("jellyfin_notifier", f"Error getting library ID: {e}")
            return None
        except Exception as e:
            l.log("jellyfin_notifier", f"Unexpected error getting library ID: {e}")
            return None

    def scan_library(self):
        """
        Trigger a refresh of the configured library ONLY.

        Bug fix: the previous implementation always called ``POST /Library/Refresh``
        with empty params, which restarts validation from item #1 on the whole
        server. When a cron job calls this every 2-4 hours, the main library
        scan never finishes and the dashboard becomes slow.

        The fix refreshes only the configured library (e.g. "Youtube" or
        "Twitch") via ``POST /Items/{Id}/Refresh`` with conservative params
        (no metadata re-extraction, no image re-extraction). If the library
        cannot be found in Emby/Jellyfin, we skip the refresh instead of
        falling back to a full server scan.

        Returns:
            bool: True if the library refresh was triggered, False otherwise
                  (including when the library is not configured in Emby).
        """
        if not self.enabled:
            return False

        try:
            library_id = self.get_library_id()

            if not library_id:
                # Library missing or misconfigured. Do NOT fall back to a full
                # server scan — that was the original bug.
                l.log(
                    "jellyfin_notifier",
                    f"Library '{self.library_name}' not found, skipping refresh "
                    f"(no full-scan fallback to avoid stalling other libraries)",
                )
                return False

            # Refresh only the specific library (CollectionFolder).
            # Endpoint: POST /Items/{Id}/Refresh where {Id} is the library's ItemId.
            url = f"{self.base_url}/Items/{library_id}/Refresh"
            headers = {
                'X-Emby-Token': self.api_key,
            }
            # Conservative params: pick up new/changed files, do not re-extract
            # metadata or images. This is the lightest possible refresh.
            params = {
                'Recursive': 'true',
                'MetadataRefreshMode': 'Default',
                'ImageRefreshMode': 'None',
                'ReplaceAllMetadata': 'false',
                'ReplaceAllImages': 'false',
            }

            response = requests.post(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            l.log(
                "jellyfin_notifier",
                f"Library refresh triggered for '{self.library_name}' (ItemId={library_id})",
            )
            return True

        except requests.exceptions.RequestException as e:
            l.log("jellyfin_notifier", f"Error triggering library scan: {e}")
            return False
        except Exception as e:
            l.log("jellyfin_notifier", f"Unexpected error triggering library scan: {e}")
            return False
    
    def notify_new_content(self, content_path=None):
        """
        Notify Jellyfin/Emby about new content
        This is a convenience method that triggers a library scan
        
        Args:
            content_path (str, optional): Path to the new content (for logging purposes)
        
        Returns:
            bool: True if notification was successful, False otherwise
        """
        if not self.enabled:
            return False
        
        if content_path:
            l.log("jellyfin_notifier", f"New content added: {content_path}")
        
        return self.scan_library()


# Convenience function for quick usage
def notify_jellyfin(config, content_path=None):
    """
    Quick function to notify Jellyfin/Emby about new content
    
    Args:
        config (dict): Configuration dictionary
        content_path (str, optional): Path to the new content
    
    Returns:
        bool: True if notification was successful, False otherwise
    """
    notifier = JellyfinNotifier(config)
    return notifier.notify_new_content(content_path)
