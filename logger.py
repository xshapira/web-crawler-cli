import logging


def setup_logger(name):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s]: %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
    )
    return logging.getLogger(name)
