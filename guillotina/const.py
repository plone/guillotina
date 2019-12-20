import string


# base root object
ROOT_ID = "0" * 32

# object to reassign parent id to when you are deleting
TRASHED_ID = "D" * 32


VALID_ID_CHARACTERS = list(string.digits + string.ascii_lowercase + ".-_@$^()+ =")
