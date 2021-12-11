import pathlib

import pdoc
import re
import os
import shutil

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

p  = pdoc.pdoc('LineDream',  )

nav = get_tags(p, 'nav', 'div')
nav = nav.replace('<h2>API Documentation</h2>', '<h3>Table of Contents</h3>')
docs = get_tags(p, 'main', 'div')

for template_name, html_str in [
	('doc_nav.html', nav),
	('doc_main.html', docs),
]:
	with open(f'website/templates/{template_name}', 'w') as f:
		f.write(html_str)


from jinja2 import Environment, PackageLoader, FileSystemLoader, select_autoescape
env = Environment(
    loader = PackageLoader('website', 'templates'),
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
		f.write(template_obj.render())

# move css into the folder

folders_to_copy = [
	('website/css/', 'website/build/css/'),
	('website/static/', 'website/build/static/')
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

