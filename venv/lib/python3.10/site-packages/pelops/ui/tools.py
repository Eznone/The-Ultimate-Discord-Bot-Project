import shlex

# getch taken from http://code.activestate.com/recipes/134892/
# licensed under the PSF-licencse: https://docs.python.org/3/license.html
# the concrete license version is not provided by the source above


class _Getch:
    """Gets a single character from standard input.  Does not echo to the screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()


getch = _Getch()


def more(text):
    _MAX_LINES = 35
    TEXT = "   --- Press ENTER to continue / ESC to abort ---"
    max_lines = _MAX_LINES
    lines = text.split("\n")
    i = 0
    for line in lines:
        print(line)
        i += 1
        if i == max_lines:
            i = 0
            print(TEXT, end='\r')
            while True:
                ch = getch()
                if ord(ch) == 27:
                    print(" " * len(TEXT), end='\r')
                    return  # ESC
                elif ord(ch) == 32:
                    max_lines = 1  # SPACE - single line feed
                    break
                elif ord(ch) == 13:
                    max_lines = _MAX_LINES  # ENTER - feed max lines
                    break
            print(" " * len(TEXT), end='\r')


def get_yes_no():
    txt = "continue (y/n):"
    while True:
        print(txt)
        ch = getch()
        if ch == "y" or ch == "Y":
            return "y"
        elif ch == "n" or ch == "N":
            return "n"
        print("unexpected character '{}'".format(ch))


def parse(arg):
    return tuple(map(str, shlex.split(arg)))
