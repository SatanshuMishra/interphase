import os
import tempfile


def created_mode():
    mask = os.umask(0)
    os.umask(mask)
    return 0o666 & ~mask


def kept_mode(target):
    try:
        return os.stat(target).st_mode & 0o7777
    except FileNotFoundError:
        return created_mode()


def replace(path, data):
    target = os.path.realpath(path)
    mode = kept_mode(target)
    descriptor, temporary = tempfile.mkstemp(
        prefix="." + os.path.basename(target) + ".", suffix=".tmp", dir=os.path.dirname(target)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        if os.path.lexists(temporary):
            os.remove(temporary)
        raise
