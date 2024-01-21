import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pelops.myconfigtools
from io import StringIO
import pelops.schema.abstractmicroservice
from pelops.logging.mylogger import create_logger


class TestMyConfigTools(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = {}
        cls.config["logger"] = {
            "log-level": "DEBUG",
            "log-file": "pelops.log"
        }
        cls.logger = create_logger(cls.config["logger"], "TestMyConfigTools")
        cls.logger.info("start ==============================================")

        cls.base_path = os.path.abspath(os.path.dirname(__file__))
        if not cls.base_path.endswith("/tests_unit"):
            cls.base_path += "/tests_unit"
        if not cls.base_path.endswith("/"):
            cls.base_path += "/"

        try:
            os.mkdir(cls.base_path+"TestMyConfigTools")
        except FileExistsError:
            pass

    @classmethod
    def tearDownClass(cls):
        cls.logger.info("end ================================================")

    def test_00get_entries(self):
        magic_name = "magic"
        struct = {
            magic_name: "test_1",
            "nix0": {
                magic_name: [
                    {
                        magic_name: {
                            magic_name: "test_2",
                            "nix1": "nix1"
                        },
                        "nix2": "nix2"
                    },
                    {
                        "nix3": "nix3",
                        magic_name: "test_2"
                    }
                ],
                "nix5": "nix5"
            }
        }
        result = pelops.myconfigtools._get_entries(struct, magic_name)
        self.assertEqual(len(result), 3)
        self.assertListEqual(result, ["test_1", "test_2", "test_2"])

    def test_01expand_filepathes(self):
        magic_name = "magic"
        struct = {
            magic_name: self.base_path+"test_1",
            "nix0": {
                magic_name: [
                    {
                        magic_name: {
                            magic_name: self.base_path+"test_2",
                            "nix1": "nix1"
                        },
                        "nix2": "nix2"
                    },
                    {
                        "nix3": "nix3",
                        magic_name: self.base_path+"test_2"
                    }
                ],
                "nix5": "nix5"
            }
        }
        result = pelops.myconfigtools._get_entries(struct, magic_name)
        self.assertEqual(len(result), 3)
        self.assertListEqual(result, [self.base_path+"test_1", self.base_path+"test_2", self.base_path+"test_2"])
        result = pelops.myconfigtools._expand_filepathes(result)
        self.assertEqual(len(result), 2)
        # result should look something like ['/home/user/test_1', '/home/user/test_2']
        final = []
        for r in result:
#            print(r)
            s = r.split("/")
            self.assertTrue(s[1] == "home" or s[1] == "mnt")
            final.append(s[-1])
        self.assertListEqual(final, ["test_1", "test_2"])

    def test_02get_configs(self):
        with open(self.base_path+"TestMyConfigTools/config_base.yaml", 'r') as f:
            config = pelops.myconfigtools.load(f, Loader=pelops.myconfigtools.Loader)
        entries = pelops.myconfigtools._get_entries(config, "magic")
        files = pelops.myconfigtools._expand_filepathes(entries)

        # fix broken path if "setup.py test" is used
        files2 = []
        for f in files:
            f = f.split("TestMyConfigTools")
            f = self.base_path + "TestMyConfigTools" + f[1]
            files2.append(f)
        files = files2

        self.assertListEqual(files, [self.base_path+'TestMyConfigTools/config_a.yaml',
                                     self.base_path+'TestMyConfigTools/config_b.yaml'])
        sub_configs = pelops.myconfigtools._get_configs(files)
        self.assertEqual(len(sub_configs), 2)
        self.assertListEqual(sub_configs, [{'newmagic1': 'newmagic1', 'nix1': {'nix5': {'newmagic2': 'newmagic2'}},
                                            'newmagic3': {'newmagic4': 'newmagic4'}},
                                           {'nix1': {'nix3': {'nix4': {'newmagic5': 'newmagic5'}}}}])

    def test_03deep_update(self):
        base = {
            "a": {
                "b": {
                    "c": "c"
                },
                "d": "d",
                "e:": ["f", "g"],
                "h": "h"
            }
        }
        ext = {
            "a": {
                "b": {
                    "x": "x"
                },
                "h": {
                    "x": "x"
                }
            },
            "y": {
                "z": "z",
                "0": ["1", "2"]
            }
        }
        target_full = {
            "a": {
                "b": {
                    "c": "c",
                    "x": "x"
                },
                "d": "d",
                "e:": ["f", "g"],
                "h": {
                    "x": "x"
                }
            },
            "y": {
                "z": "z",
                "0": ["1", "2"]
            }
        }
        target_leafs = {
            "a": {
                "b": {
                    "c": "c",
                    "x": "x"
                },
                "d": "d",
                "e:": ["f", "g"],
                "h": {
                    "x": "x"
                }
            }
        }

        result = pelops.myconfigtools.deep_update(base, ext, False)
        self.assertEqual(result, target_full)
        self.assertNotEqual(result, base)
        self.assertNotEqual(result, ext)

        result = pelops.myconfigtools.deep_update(base, ext, True)
        self.assertEqual(result, target_leafs)
        self.assertNotEqual(result, base)
        self.assertNotEqual(result, ext)

    def test_04read_config(self):
        target = {
            "magic": "TestMyConfigTools/config_a.yaml",
            "newmagic1": "newmagic1",
            "nix1":{
                "nix2": "nix2",
                "nix3":{
                    "nix4": {
                        "newmagic5": "newmagic5"
                    },
                    "magic": "TestMyConfigTools/config_b.yaml"
                },
                "nix5":{
                    "nix6": "nix6",
                    "magic": "TestMyConfigTools/config_a.yaml",
                    "newmagic2": "newmagic2"
                }
            }
        }

        # fix broken path if "setup.py test" is used.
        filename = self.base_path+"TestMyConfigTools/config_base.yaml"
        current_path = os.getcwd()
        if not current_path.endswith("/tests_unit"):
            filename = self.base_path + "TestMyConfigTools/config_base2.yaml"
            target["magic"] = "tests_unit/"+target["magic"]
            target["nix1"]["nix3"]["magic"] = "tests_unit/" + target["nix1"]["nix3"]["magic"]
            target["nix1"]["nix5"]["magic"] = "tests_unit/" + target["nix1"]["nix5"]["magic"]

        config = pelops.myconfigtools.read_config(filename, "magic")
        self.assertIsNotNone(config)
        self.assertEqual(config, target)

    def test_05validate_config(self):
        config = pelops.myconfigtools.read_config(self.base_path+"config_mqtt.yaml")
        schema = pelops.schema.abstractmicroservice.get_schema({})
        self.assertIsNotNone(config)
        self.assertIsNotNone(schema)
        result = pelops.myconfigtools.validate_config(config, schema)
        self.assertIsNone(result)

    def test_6dict_deepcopy_lowercase(self):
        input = {
            "A": "A",
            "B": {
                "C": "C",
                "D": "D"
            },
            "E": ["F", "G"],
            "H": [
                {
                    "I": "I",
                    "J": "J"
                },
                [
                    {"K": "K"},
                    "L"
                ]
            ]
        }
        output = {
            "a": "A",
            "b": {
                "c": "C",
                "d": "D"
            },
            "e": ["F", "G"],
            "h": [
                {
                    "i": "I",
                    "j": "J"
                },
                [
                    {"k": "K"},
                    "L"
                ]
            ]
        }
        result = pelops.myconfigtools.dict_deepcopy_lowercase(input)
        self.assertEqual(result, output)
        self.assertNotEqual(result, input)

        result["e"][0] = "U"
        input["E"][0] = "U"
        with self.assertRaises(KeyError):
            result["E"][0] = "V"
        with self.assertRaises(KeyError):
            input["e"][0] = "V"

        self.assertEqual(result["a"], input["A"])
        result["a"] = "X"
        self.assertNotEqual(result["a"], input["A"])

        self.assertEqual(result["h"][1][0]["k"], input["H"][1][0]["K"])
        result["h"][1][0]["k"] = ["X", "Y", "Z"]
        self.assertNotEqual(result["h"][1][0]["k"], input["H"][1][0]["K"])

    def test_7pyyaml_rules(self):
        input = StringIO()
        input.write("key_on_1: On\n")
        input.write("key_on_2: on\n")
        input.write("key_off_1: Off\n")
        input.write("key_off_2: off\n")
        input.write("key_yes_1: Yes\n")
        input.write("key_yes_2: yes\n")
        input.write("key_no_1: No\n")
        input.write("key_no_2: no\n")
        input.seek(0)

        output = {
            "key_on_1": "On",
            "key_on_2": "on",
            "key_off_1": "Off",
            "key_off_2": "off",
            "key_yes_1": "Yes",
            "key_yes_2": "yes",
            "key_no_1": "No",
            "key_no_2": "no",
        }

        with input as f:
            config = pelops.myconfigtools.load(f, Loader=pelops.myconfigtools.Loader)

        self.assertIsNotNone(config)
        self.assertEqual(config, output)


if __name__ == '__main__':
    unittest.main()

