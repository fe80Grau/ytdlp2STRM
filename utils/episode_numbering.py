import os
import re
from datetime import datetime

def get_next_episode_number(folder_path: str, year: int) -> str:
    """
    Get the next episode number for the given year by scanning existing files
    and finding the highest episode number.
    
    Args:
        folder_path: The folder to scan for existing episodes
        year: The year to look for (e.g. 2025)
        
    Returns:
        A two-digit string episode number (e.g. "01", "02", etc)
    """
    pattern = rf"S{year}E(\d+)"
    max_episode = 0
    
    # Walk through all files in the directory
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".strm"):
                match = re.search(pattern, file)
                if match:
                    episode_num = int(match.group(1))
                    max_episode = max(max_episode, episode_num)
    
    # Return next episode number as 2-digit string
    return f"{max_episode + 1:02d}"

def format_episode_title(title: str, folder_path: str) -> str:
    """
    Format a title with the season/episode prefix
    
    Args:
        title: The original title
        folder_path: Path to check for existing episode numbers
        
    Returns:
        The formatted title with S{year}E{XX} prefix
    """
    current_year = datetime.now().year
    next_episode = get_next_episode_number(folder_path, current_year)
    return f"S{current_year}E{next_episode} - {title}"
