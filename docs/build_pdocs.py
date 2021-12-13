import pathlib

import pdoc
import re
import os
import shutil
from pygments import highlight as pyg_highlight
from pygments.lexers import python as python_lexer
from pygments.formatters import html

import os

# theme from https://www.designbombs.com/freebie/prism/

def get_tags(s, tag, replace_tag=None):
	s_tag = f'<{tag} '
	e_tag = f'</{tag}>'
	_, s = s.split(s_tag)
	s, _ = s.split(e_tag)

	if not replace_tag:
		replace_tag = tag

	s = f'{s_tag.replace(tag, replace_tag)}{s}{e_tag.replace(tag, replace_tag)}'

	return s

t_p = pathlib.Path('website/source/templates')

# pdoc.render_helpers.lexer = python.Python3Lexer()
# pdoc.render_helpers.formatter = html.HtmlFormatter(cssstyles='material', noclasses=True)

from markupsafe import Markup

def _highlight(src):
	lexer = python_lexer.Python3Lexer()
	formatter = html.HtmlFormatter(style='material', noclasses=True)
	output = pyg_highlight(src, lexer, formatter)
	return Markup(output)

pdoc.render.env.filters['highlight'] = _highlight
pdoc.render.configure(template_directory=t_p)
p  = pdoc.pdoc('LineDream')

root = None
if not root:
	root = os.getenv('linedream_site', None) or 'http://localhost:63342/LineDream/docs/website/build/'



nav = get_tags(p, 'nav', 'div')
nav = nav.replace('<h2>API Documentation</h2>', '<h3>Table of Contents</h3>')
docs = get_tags(p, 'main', 'div')

for template_name, html_str in [
	('doc_nav.html', nav),
	('doc_main.html', docs),
]:
	with open(f'website/source/templates/{template_name}', 'w') as f:
		f.write(html_str)


from jinja2 import Environment, PackageLoader, FileSystemLoader, select_autoescape
env = Environment(
    loader = PackageLoader('website', 'source/templates'),
    # loader = FileSystemLoader(t_path),
    autoescape=select_autoescape()
)



os.makedirs('website/build', exist_ok=True)

pages = [
	('', 'index.html'), # landing page
	('documentation', 'documentation.html'),
]

for path, template in pages:

	template_obj = env.get_template(template)

	f_name = 'index.html'
	if path:
		f_name = f'{path}/{f_name}'
		os.makedirs(f'website/build/{path}', exist_ok=True)

	with open(f'website/build/{f_name}', 'w') as f:
		f.write(template_obj.render({
			'url_root':root
		}))

# move css into the folder

folders_to_copy = [
	('website/source/css/', 'website/build/css/'),
	('website/source/static/', 'website/build/static/'),
	('website/build/css/', 'website/build/documentation/css/')	# TEMP COPY FOR EASE OF DEVELOPMENT

]

for source_dir, target_dir in folders_to_copy:

	file_names = os.listdir(source_dir)

	os.makedirs(target_dir, exist_ok=True)

	for file_name in file_names:

		original_file = pathlib.Path(source_dir, file_name)

		new_path = pathlib.Path(target_dir, file_name)

		if original_file.is_file():
			shutil.copy2(original_file, new_path)
		else:
			os.makedirs(new_path, exist_ok=True)



tut_page = 'Tutorial'
links = []

s = 'website/source/tutorial'
file_names = os.listdir(s)
	# os.makedirs(target_dir, exist_ok=True)

for file_name in file_names:
	rst_stuff = pathlib.Path(s, file_name).read_text()
	o = pdoc.markdown2.markdown(rst_stuff)

	os.makedirs(target_dir, exist_ok=True)
