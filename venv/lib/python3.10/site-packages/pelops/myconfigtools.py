from pathlib import Path
import os
import jsonschema
import copy

# set of scripts for yaml/json configfile reading


def _get_entries(structure, search_key):
    """
    Search the whole json/yaml structure for keys equivalent to 'search_key'. if the value is not a list or a dict,
    add it to the result list.

    :param structure: json/yaml config structure
    :param search_key: string
    :return: list of entries
    """
    result = []

    if type(structure) == list:
        for entry in structure:
            result += _get_entries(entry, search_key)
    elif type(structure) == dict:
        for key, value in structure.items():
            if type(value) == list or type(value) == dict:
                result += _get_entries(value, search_key)
            elif key == search_key:
                result.append(value)
            else:
                continue
    return result


def _expand_filepathes(filenamelist):
    """
    Takes a list of (relative) filenames and expands them to a full path. E.g. '~/credentials.yaml' will be expanded
    to '/home/user/cerdentialy.yaml'.

    :param filenamelist: list of filenames
    :return: list of expanded filenames (unique entries)
    """
    result = []
    for filename in filenamelist:
        fn = os.path.abspath(os.path.expanduser(filename))
        if fn not in result:
            result.append(fn)
    return result


def _get_configs(filenamelist):
    """
    Takes a list of valid filenames and loads them as yaml structures.

    :param filenamelist: list of filenames
    :return: list of yaml structures
    """
    result = []
    for filename in filenamelist:
        with open(filename, 'r') as f:
            config = load(f, Loader=Loader)
            config = dict_deepcopy_lowercase(config)
            result.append(config)
    return result


def dict_deepcopy_lowercase(dict_in):
    """
    convert all keys in the dicts (and sub-dicts and sub-dicts of sub-lists) to lower case
    :param dict_in: config yaml structure
    :return: config yaml structure with lower case keys
    """
    if type(dict_in) is dict:
        dict_out = {}
        for k, v in dict_in.items():
            try:
                k = k.lower()
            except AttributeError:
                pass
            dict_out[k] = dict_deepcopy_lowercase(v)
    elif type(dict_in) is list:
        dict_out = []
        for d in dict_in:
            dict_out.append(dict_deepcopy_lowercase(d))
    else:
        dict_out = dict_in
    return dict_out


def deep_update(base, extensions, add_leafs_only=True):
    """
    merge a yaml struct (=extensions) into another yaml struct (=base). list entries yield a TypeError (except if the
    list is already in a new subtree that is not present in base at all). as this merge method advances only to
    subtrees in base if this subtree exists in extensions as well, existing lists in base will never be visited.

    e.g.
    base:
    a:
        b:
            c: c
        d: d
        e:
            -f
            -g
        h: h

    extensions:
    a:
        b:
            x: x
        h:
            x: x
    y:
        z: z
        0:
            -1
            -2


    should result in (add_leafs_only=False):
    a:
        b:
            c: c
            x: x
        d: d
        e:
            -f
            -g
        h:
            x: x
    y:
        z: z
        0:
            -1
            -2

    should result in (add_leafs_only=True):
    a:
        b:
            c: c
            x: x
        d: d
        e:
            -f
            -g
        h:
            x: x

    :param result: config yaml structure
    :param extensions: config yaml structure
    :param add_leafs_only: boolean - if True, only leafs (but no nodes or subtrees) are added
    :return: config yaml structure
    """

    def _deep_update(target, ext):
        if type(target) == dict:
            for key, value in ext.items():
                if key in target.keys():
                    if type(target[key]) == list:
                        raise TypeError("entry in extensions is of type 'list'. only dicts and leafs are allowed.")
                    elif type(target[key]) == dict:
                        # not at final destination - continue crawling tree
                        _deep_update(target[key], value)
                    else:
                        # overwrite existing key
                        target[key] = value
                else:
                    if add_leafs_only and type(value) == dict:
                        continue  # skip - not a leaf!
                    # add new key
                    target[key] = value
        else:
            raise TypeError("don't know how to handly entry '{}' of type '{}.".format(target, type(target)))

    result = copy.deepcopy(base)
    _deep_update(result, extensions)

    return result


def read_config(config_filename, credential_file_tag="credentials-file"):
    """
    read the provided file, convert it to a yaml config structure, expand the credential file entries for mqtt and
    influx db and make sure the keys are lower case.

    this method searches all keys for occurences of "credential_file_tag". every value of these entries is assumed
    to be a file name - a config yaml file containing credentials or similar stuff. These files a read, parsed and
    merged into the general config structure. Thus, the whole hierarchy has to be present in the credentials file. For
    example:

    main 'config.yaml' file:
    test:
        some-param: yadda
        subtest:
            credentials-file: credentials.yaml
            other-param: yadda

    'credentials.yaml' file:
    test:
        subtest:
            username: username
            password: secret

    merge result:
    test:
        some-param: yadda
        subtest:
            credentials-file: credentials.yaml
            other-param: yadda
            username: username
            password: secret

    If the 'magic' entry does not point to a valid yaml file, a ValueError will be raised. Only 'leafs' are used; keys
    that have a list or a dict as value will be skipped. No sanity check or key-exists check will be done - merging
    overwrites whatever is in the base config with what is in the credentials config. As a consequence, the
    "credentials-file" entry location is independent of what and where key/value pairs will be added. If more than
    one "credentials-file" is provided, the merge order is random - it is only guaranteed that they will be merged
    into the base config.

    :param config_filename: string - file name
    :param credential_file_tag: string - "magic" key name - every key with this name is assumed to be a pointer to an
    external yaml file with credentials.
    :return: config yaml structure
    """

    # load base file
    config_file = Path(config_filename)
    if not config_file.is_file():
        raise FileNotFoundError("config file '{}' not found.".format(config_filename))

    with open(config_filename, 'r') as f:
        config = load(f, Loader=Loader)
    config = dict_deepcopy_lowercase(config)

    # load addtional credential files
    credential_files = _get_entries(config, credential_file_tag)
    credential_files = _expand_filepathes(credential_files)
    credentials = _get_configs(credential_files)

    # merge
    for credential in credentials:
        config = deep_update(config, credential)

    return config


def validate_config(config, schema):
    """
    Validate the provided config with the provided schema.

    :param config: config yaml structure to be validated
    :param schema: json-schema
    :return: boolean. Result of validation.
    """

    return jsonschema.validate(config, schema)


def mask_entries(config, patterns=["credentials", "password", "user"], mask_string="*****"):
    """
    parses recursively through all entries of the provided data structure and searches for keys that have at least
    one of the provided search strings (=patterns). the value of the found key/value pairs will be replaced by
    mask_string.

    :param config: dict/list structure that will be altered
    :param patterns: list of substrings
    :param mask_string: replacement value for found key/value pairs
    """

    if type(config) is dict:
        for k, c in config.items():
            if type(c) is list or type(c) is dict:
                mask_entries(c, patterns, mask_string)
            elif type(c) is str:
                for pattern in patterns:
                    if pattern in k:
                        config[k] = mask_string
                        break
    elif type(config) is list:
        for c in config:
            mask_entries(c, patterns, mask_string)


# wrapper for yaml for project specific behavior
# this module removes yaml1.1 compliant exchange of On/Off & Yes/No with True/False.
# as soon as pyyaml supports yaml1.2 this is deprecated

from yaml import load
from yaml.resolver import Resolver
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

# remove resolver entries for On/Off/Yes/No
# (https://stackoverflow.com/questions/36463531/pyyaml-automatically-converting-certain-keys-to-boolean-values)
for ch in "OoYyNn":
    if len(Resolver.yaml_implicit_resolvers[ch]) == 1:
        del Resolver.yaml_implicit_resolvers[ch]
    else:
        Resolver.yaml_implicit_resolvers[ch] = [x for x in
                Resolver.yaml_implicit_resolvers[ch] if x[0] != 'tag:yaml.org,2002:bool']

