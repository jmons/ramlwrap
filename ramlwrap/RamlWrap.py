"""
Raml Wrap (also known as the Raml Rap)

    Yo Yo Yo Check it Out.

    It Validates your inputs to match that file
    and it does it whilst flirting with the style
    of the pythonese, it does it with ease
    'Cause if you want to ride like a camel,
    you need to get some RAML!

    To all my homies who made this happen
    Jamie, Natalie and the Bees
    Ron managing us with Tim's a rappin'
    you aint got nothing on old - JAY TEEEeeeeee(ssss)

This file is the prototype Raml Wrap. Its going to have a license when we pick one,
until then, let JT know how much you love it, so he bothers to release it properly.

Tweet him @jmons, and leave this message in. Feel free to extend the Rap. Perhaps
sing it and put it on youtube...
"""
import logging

from . utils.raml import raml_url_patterns
from . utils.exceptions import FatalException


logger = logging.getLogger(__name__)


def ramlwrap(file_path, function_map):
    """
    Check if the file is Raml and parse as appropriate.
    """

    try:
        # Check if file is RAML (.raml)
        if file_path.endswith(".raml"):
            patterns = raml_url_patterns(file_path, function_map)
        else:
            error_msg = "The file: '{}' does not have a .raml extension!".format(file_path)
            logger.error(error_msg)
            raise FatalException(error_msg)

    except AttributeError as error:
        error_msg = "An error occurred reading '{}': {}".format(file_path, error)
        logger.error(error_msg)
        raise FatalException(error_msg)

    return patterns
