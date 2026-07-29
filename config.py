import openai
import tenacity
from loguru import logger
import sys

# Remove default handler and add stderr sink suitable for piping
logger.remove()
logger.add(sys.stderr, backtrace=True, diagnose=True)

def excepthook_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.opt(exception=(exc_type, exc_value, exc_traceback)).critical("Uncaught exception")

sys.excepthook = excepthook_handler

provider_tantrums = (
    openai.NotFoundError, 
    openai.InternalServerError, 
    openai.BadRequestError, 
    tenacity.RetryError
)
