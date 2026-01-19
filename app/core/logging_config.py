"""
Centralized logging configuration for the Nutrivo application.
"""
import logging
import sys

# Create a formatter with a consistent format
FORMATTER = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: The name of the logger (typically __name__)
        
    Returns:
        A configured Logger instance
    """
    logger = logging.getLogger(name)
    
    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(FORMATTER)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


# Create a root application logger
def setup_logging(level: int = logging.INFO) -> None:
    """
    Setup the root logging configuration for the application.
    
    Args:
        level: The logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
