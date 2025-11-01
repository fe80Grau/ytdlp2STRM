"""
Custom sanitize function that preserves non-English characters (Chinese, Japanese, Korean, etc.)
while only removing characters that are actually problematic for filesystems.
"""
import re
import unicodedata

def sanitize(filename, max_length=255):
    """
    Sanitize filename while preserving Unicode characters (Chinese, Japanese, Korean, etc.)
    
    Only removes/replaces characters that are actually problematic for filesystems:
    - Windows: < > : " / \\ | ? *
    - Control characters (0x00-0x1F)
    - Leading/trailing dots and spaces
    
    Args:
        filename: The filename to sanitize
        max_length: Maximum filename length (default 255)
    
    Returns:
        Sanitized filename that preserves Unicode characters
    """
    if not filename:
        return "unnamed"
    
    # Normalize Unicode (NFC form - canonical composition)
    filename = unicodedata.normalize('NFC', filename)
    
    # Replace problematic filesystem characters with safe alternatives
    # Windows forbidden characters: < > : " / \ | ? *
    replacements = {
        '<': '＜',   # Fullwidth less-than
        '>': '＞',   # Fullwidth greater-than
        ':': '：',   # Fullwidth colon
        '"': '＂',   # Fullwidth quotation mark
        '/': '／',   # Fullwidth solidus
        '\\': '＼',  # Fullwidth reverse solidus
        '|': '｜',   # Fullwidth vertical line
        '?': '？',   # Fullwidth question mark
        '*': '＊',   # Fullwidth asterisk
    }
    
    for char, replacement in replacements.items():
        filename = filename.replace(char, replacement)
    
    # Remove control characters (0x00-0x1F and 0x7F-0x9F)
    filename = ''.join(char for char in filename if ord(char) >= 32 and not (127 <= ord(char) <= 159))
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    
    # Ensure filename is not empty after sanitization
    if not filename:
        return "unnamed"
    
    # Truncate to max_length while trying to preserve complete characters
    if len(filename.encode('utf-8')) > max_length:
        # Truncate by bytes, then decode back
        encoded = filename.encode('utf-8')[:max_length]
        # Try to decode, ignoring errors at the end if we cut in the middle of a character
        try:
            filename = encoded.decode('utf-8')
        except UnicodeDecodeError:
            # If we cut in the middle of a multi-byte character, trim back
            for i in range(1, 5):  # UTF-8 characters are max 4 bytes
                try:
                    filename = encoded[:-i].decode('utf-8')
                    break
                except UnicodeDecodeError:
                    continue
    
    # Final check: remove trailing dots and spaces again
    filename = filename.strip('. ')
    
    return filename if filename else "unnamed"


def sanitize_path(path):
    """
    Sanitize a full path, processing each component separately
    
    Args:
        path: Full path to sanitize
    
    Returns:
        Sanitized path with each component processed
    """
    if not path:
        return ""
    
    # Split path into components
    parts = path.replace('\\', '/').split('/')
    
    # Sanitize each part (except drive letter on Windows)
    sanitized_parts = []
    for i, part in enumerate(parts):
        # Preserve drive letters (C:, D:, etc.) and UNC paths (\\server\share)
        if i == 0 and (part.endswith(':') or not part):
            sanitized_parts.append(part)
        else:
            sanitized_parts.append(sanitize(part))
    
    # Reconstruct path with original separator
    if '\\' in path:
        return '\\'.join(sanitized_parts)
    else:
        return '/'.join(sanitized_parts)
