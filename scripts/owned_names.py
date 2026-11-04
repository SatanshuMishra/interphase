H11 = "h11-interphase-record"
H12 = "h12-interphase-items"
SCHEMA_SUFFIX = ".schema.json"


def schema_file(name):
    return name + SCHEMA_SUFFIX


def written_by_interphase(path):
    return "%s (written by interphase)" % path


def mismatch_lead(subject, name):
    return "%s does not match %s:" % (subject, schema_file(name))


def mismatch(subject, name, message):
    return "%s %s" % (mismatch_lead(subject, name), message)
