import os
import glob
import ast
import _ast
import copreus

version = copreus.version


def get_drivers(baseclasses=["ADriver", "AEPaper", "ARotaryEncoder"]):
    """Get all classes and their modules that are silbilings of baseclasses.adriver.ADriver."""

    def extract_class_info(class_entry, filename, package, child_of):
        result = {
            "name": class_entry.name,
            "path": filename,
            "module": package + "." + filename[:-3].split('/')[-1],
            "bases": []
        }
        for b in class_entry.bases:
            result["bases"].append(b.id)

        found = False
        for co in child_of:
            if co in result["bases"]:
                found = True
                break
        if not found:
            result = None

        return result

    path = os.path.abspath(os.path.dirname(__file__))
    files = glob.glob(path + "/*.py")
    class_list = {}
    for filename in files:
        with open(filename, 'r') as myfile:
            sourcecode = myfile.read()
        tree = ast.parse(sourcecode)
        classes = [cls for cls in tree.body if isinstance(cls, _ast.ClassDef)]
        for c in classes:
            ci = extract_class_info(c, filename, 'copreus.drivers', child_of=baseclasses)
            if ci:
                class_list[ci["name"].upper()] = ci

    return class_list
