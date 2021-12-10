import pathlib

import pdoc

p  = pdoc.pdoc('LineDream')
with open('test_output.html', 'w') as f:
	f.write(p)


t_path = pathlib.Path(pathlib.Path(__file__).parent, 'templates')
print(t_path.exists())

from jinja2 import Environment, PackageLoader, FileSystemLoader, select_autoescape
env = Environment(
    loader = PackageLoader('website', 'templates'),
    # loader = FileSystemLoader(t_path),
    autoescape=select_autoescape()
)

template = env.get_template("base_template.html")


with open('index_2.html', 'w') as f:
	f.write(template.render())